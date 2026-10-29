"""Control tools: how the agent asks the user one question or finishes a run."""

from app.agent.protocol import AskUserArgs, SubmitVerdictArgs

SUBMIT_VERDICT = "submit_verdict"
ASK_USER = "ask_user"

SPECS = [
    {
        "name": SUBMIT_VERDICT,
        "description": (
            "Finish the run with a verdict. Every reason must cite evidence_id values from tool "
            "results in THIS run. The verdict is checked by code and may be refused; if refused, "
            "fix the problem and submit again."
        ),
        "parameters": SubmitVerdictArgs.model_json_schema(),
    },
    {
        "name": ASK_USER,
        "description": (
            "Ask the user for ONE value that is missing and needed for a check (usually the "
            "consumer number). Ask in the user's language. Allowed once per run."
        ),
        "parameters": AskUserArgs.model_json_schema(),
    },
]
