<#
.SYNOPSIS
  Deploy the BillSaathi API to Azure Container Apps (Central India), one step at a time.

.EXAMPLE
  .\infra\deploy.ps1 -Step 0     # select subscription
  .\infra\deploy.ps1 -Step all   # run every step in order

  Steps: 0 subscription, 1 CLI extension + providers, 2 region check, 3 resource group + budget,
  4 container registry, 5 image build, 6 pull identity, 7 environment, 8 container app, 9 health check,
  10 model API keys as Container Apps secrets (read from api\.env, never printed).
  Every step can be re-run safely. Secret values are never printed or put in the image.
#>
param(
    [Parameter(Mandatory = $true)][string]$Step
)

$ErrorActionPreference = 'Stop'

$Subscription = 'pay-as-you-go'
$Rg = 'rg-billsaathi-cin'
$Location = 'centralindia'
$Acr = 'billsaathicin'
$CaEnv = 'cae-billsaathi'
$App = 'ca-billsaathi-api'
$Identity = 'id-billsaathi-pull'
$Image = 'billsaathi-api'
$BudgetName = 'budget-billsaathi-cin'
$BudgetAmount = 1000          # in the subscription's billing currency (INR expected)
$BudgetEmail = 'ch.bharat34@gmail.com'

$Root = Split-Path -Parent $PSScriptRoot

function Invoke-Az {
    # Run az and fail loudly; PowerShell 5.1 does not stop on native-command errors.
    & az @args
    if ($LASTEXITCODE -ne 0) { throw "az $($args -join ' ') failed with exit code $LASTEXITCODE" }
}

function Find-Az {
    # Existence check: returns az output, or nothing when the resource is not found yet.
    $ErrorActionPreference = 'Continue'
    $out = & az @args 2>$null
    if ($LASTEXITCODE -eq 0) { return $out }
}

function Get-GitTag {
    $sha = (git -C $Root rev-parse --short HEAD).Trim()
    if (git -C $Root status --porcelain) { $sha = "$sha-dirty" }  # image built from uncommitted code
    return $sha
}

function Step0 {
    Invoke-Az account set --subscription $Subscription
    Invoke-Az account show --query "{subscription:name, state:state, tenantDefault:isDefault}" -o table
}

function Step1 {
    Invoke-Az extension add --name containerapp --upgrade --only-show-errors
    foreach ($ns in 'Microsoft.App', 'Microsoft.OperationalInsights', 'Microsoft.ContainerRegistry', 'Microsoft.Consumption') {
        Invoke-Az provider register --namespace $ns --wait
        Write-Host "$ns : $(az provider show -n $ns --query registrationState -o tsv)"
    }
}

function Step2 {
    $locs = az provider show -n Microsoft.App --query "resourceTypes[?resourceType=='managedEnvironments'].locations | [0]" -o json | ConvertFrom-Json
    if ($locs -notcontains 'Central India') { throw 'Container Apps environments are not offered in Central India for this subscription' }
    Write-Host 'Container Apps environments: available in Central India'
}

function Step3 {
    Invoke-Az group create --name $Rg --location $Location --query "{name:name, location:location, state:properties.provisioningState}" -o table
    $subId = (az account show --query id -o tsv)
    $start = (Get-Date -Day 1).ToString('yyyy-MM-01T00:00:00Z')
    $body = @{
        properties = @{
            category      = 'Cost'
            amount        = $BudgetAmount
            timeGrain     = 'Monthly'
            timePeriod    = @{ startDate = $start }
            notifications = @{
                actual_80_percent = @{
                    enabled       = $true
                    operator      = 'GreaterThanOrEqualTo'
                    threshold     = 80
                    thresholdType = 'Actual'
                    contactEmails = @($BudgetEmail)
                }
            }
        }
    } | ConvertTo-Json -Depth 6
    $tmp = New-TemporaryFile
    try {
        Set-Content -Path $tmp -Value $body -Encoding ascii
        $url = "https://management.azure.com/subscriptions/$subId/resourceGroups/$Rg/providers/Microsoft.Consumption/budgets/${BudgetName}?api-version=2024-08-01"
        Invoke-Az rest --method put --url $url --body "@$tmp" --query "{name:name, amount:properties.amount, timeGrain:properties.timeGrain, alertAt:properties.notifications.actual_80_percent.threshold}" -o table
    } finally {
        Remove-Item $tmp -ErrorAction SilentlyContinue
    }
}

function Step4 {
    $exists = Find-Az acr show --name $Acr --resource-group $Rg --query name -o tsv
    if (-not $exists) {
        $check = az acr check-name --name $Acr -o json | ConvertFrom-Json
        if (-not $check.nameAvailable) { throw "Registry name '$Acr' is taken: $($check.message). Choose another name." }
        Invoke-Az acr create --name $Acr --resource-group $Rg --location $Location --sku Basic --admin-enabled false --only-show-errors -o none
    }
    $arm = Find-Az acr config authentication-as-arm show --registry $Acr --query status -o tsv --only-show-errors
    if ($arm -ne 'enabled') { Invoke-Az acr config authentication-as-arm update --registry $Acr --status enabled -o none --only-show-errors }
    Invoke-Az acr show --name $Acr --query "{name:name, sku:sku.name, loginServer:loginServer, adminUser:adminUserEnabled}" -o table
}

function Step5 {
    $tag = Get-GitTag
    Write-Host "Building $Image`:$tag in Azure from $Root\api (respects api\.dockerignore)"
    # Queue without streaming: the CLI crashes printing build logs to a non-UTF-8 pipe on Windows.
    Invoke-Az acr build --registry $Acr --image "${Image}:$tag" --build-arg "GIT_SHA=$tag" `
        --no-wait --only-show-errors -o none "$Root\api"
    # --no-wait does not return the run id; the newest run is the one just queued (single deployer).
    $runId = az acr task list-runs --registry $Acr --top 1 --query "[0].runId" -o tsv --only-show-errors
    Write-Host "Queued run $runId; waiting for it to finish..."
    $deadline = (Get-Date).AddMinutes(15)
    do {
        Start-Sleep -Seconds 10
        $status = az acr task show-run --registry $Acr --run-id $runId --query status -o tsv --only-show-errors
        Write-Host "  $(Get-Date -Format HH:mm:ss) $status"
    } while ($status -in 'Queued', 'Started', 'Running' -and (Get-Date) -lt $deadline)
    if ($status -ne 'Succeeded') {
        throw "Build run $runId ended as '$status'. See logs in a terminal: az acr task logs --registry $Acr --run-id $runId"
    }
    Invoke-Az acr repository show-tags --name $Acr --repository $Image -o table
}

function Step6 {
    $id = Find-Az identity show --name $Identity --resource-group $Rg --query id -o tsv
    if (-not $id) { Invoke-Az identity create --name $Identity --resource-group $Rg --location $Location -o none }
    $principal = az identity show --name $Identity --resource-group $Rg --query principalId -o tsv
    $acrId = az acr show --name $Acr --query id -o tsv
    # Count in PowerShell: az.cmd goes through cmd.exe, which breaks on "(" in --query values.
    $has = @(az role assignment list --assignee $principal --scope $acrId --role AcrPull --query "[].id" -o tsv --only-show-errors)
    if ($has.Count -eq 0 -or -not $has[0]) {
        Invoke-Az role assignment create --assignee-object-id $principal --assignee-principal-type ServicePrincipal --role AcrPull --scope $acrId -o none
    }
    Invoke-Az role assignment list --assignee $principal --scope $acrId --query "[].{role:roleDefinitionName, scope:scope}" -o table
}

function Step7 {
    $exists = Find-Az containerapp env show --name $CaEnv --resource-group $Rg --query name -o tsv
    if (-not $exists) {
        Invoke-Az containerapp env create --name $CaEnv --resource-group $Rg --location $Location --only-show-errors -o none
    }
    Invoke-Az containerapp env show --name $CaEnv --resource-group $Rg --query "{name:name, location:location, state:properties.provisioningState}" -o table
}

function Step8 {
    $tag = Get-GitTag
    $imageRef = "$Acr.azurecr.io/${Image}:$tag"
    $idId = az identity show --name $Identity --resource-group $Rg --query id -o tsv
    $exists = Find-Az containerapp show --name $App --resource-group $Rg --query name -o tsv
    if (-not $exists) {
        Invoke-Az containerapp create --name $App --resource-group $Rg --environment $CaEnv `
            --image $imageRef --registry-server "$Acr.azurecr.io" --registry-identity $idId `
            --user-assigned $idId --ingress external --target-port 8000 `
            --min-replicas 0 --max-replicas 1 --cpu 0.5 --memory 1.0Gi `
            --env-vars APP_ENV=prod "GIT_SHA=$tag" --only-show-errors -o none
    } else {
        Invoke-Az containerapp update --name $App --resource-group $Rg --image $imageRef `
            --set-env-vars APP_ENV=prod "GIT_SHA=$tag" --only-show-errors -o none
    }
    Invoke-Az containerapp show --name $App --resource-group $Rg --query "{name:name, fqdn:properties.configuration.ingress.fqdn, image:properties.template.containers[0].image, state:properties.runningStatus}" -o table
}

function Step9 {
    $fqdn = az containerapp show --name $App --resource-group $Rg --query properties.configuration.ingress.fqdn -o tsv
    $url = "https://$fqdn/api/v1/health"
    Write-Host "GET $url (first call may take ~20 s while the app scales up from zero)"
    Invoke-RestMethod -Uri $url -TimeoutSec 90 | ConvertTo-Json
}

function Step10 {
    # Model API keys become Container Apps secrets, read from api\.env. They are never printed,
    # never in the image or repo, and never passed to Invoke-Az (which echoes its arguments on error).
    $vals = @{}
    Get-Content (Join-Path $Root 'api\.env') | ForEach-Object {
        if ($_ -match '^\s*(META_API_KEY|META_API_BASE_URL|BASETEN_API_KEY)\s*=\s*(.+?)\s*$') { $vals[$matches[1]] = $matches[2] }
    }
    if (-not $vals['META_API_KEY'] -or -not $vals['META_API_BASE_URL']) { throw 'META_API_KEY and META_API_BASE_URL must be set in api\.env' }
    $secrets = @("meta-api-key=$($vals['META_API_KEY'])")
    $envs = @('META_API_KEY=secretref:meta-api-key', "META_API_BASE_URL=$($vals['META_API_BASE_URL'])")
    if ($vals['BASETEN_API_KEY']) {
        $secrets += "baseten-api-key=$($vals['BASETEN_API_KEY'])"
        $envs += 'BASETEN_API_KEY=secretref:baseten-api-key'
    }
    & az containerapp secret set --name $App --resource-group $Rg --secrets @secrets --only-show-errors -o none
    if ($LASTEXITCODE -ne 0) { throw 'setting Container Apps secrets failed (values not shown)' }
    Invoke-Az containerapp update --name $App --resource-group $Rg --set-env-vars @envs --only-show-errors -o none
    Write-Host 'Secrets now set (names only):'
    Invoke-Az containerapp secret list --name $App --resource-group $Rg --query '[].name' -o tsv
}

$steps = @{ '0' = 'Step0'; '1' = 'Step1'; '2' = 'Step2'; '3' = 'Step3'; '4' = 'Step4'; '5' = 'Step5'; '6' = 'Step6'; '7' = 'Step7'; '8' = 'Step8'; '9' = 'Step9'; '10' = 'Step10' }
$order = if ($Step -eq 'all') { 0..10 | ForEach-Object { "$_" } } else { @($Step) }
foreach ($s in $order) {
    if (-not $steps.ContainsKey($s)) { throw "Unknown step '$s' (use 0-9 or all)" }
    Write-Host "=== Step $s ===" -ForegroundColor Cyan
    & $steps[$s]
}
