"""How a tool is defined: typed arguments, findings, and a wrapper that never raises."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from app.agent.evidence import ToolEvidence, ToolResult, make_id
from app.schemas import EvidenceCode


class ToolError(Exception):
    """An expected failure the agent should see (e.g. unknown biller_id)."""


@dataclass
class Finding:
    code: EvidenceCode
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Outcome:
    findings: list[Finding] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


class Tool:
    def __init__(
        self, name: str, description: str, args_model: type[BaseModel], fn: Callable[..., Outcome]
    ):
        self.name = name
        self.description = description
        self.args_model = args_model
        self.fn = fn

    def spec(self) -> dict[str, Any]:
        """Function-calling definition for the model (JSON Schema from the args model)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.args_model.model_json_schema(),
        }

    def __call__(self, **kwargs: Any) -> ToolResult:
        """Validate arguments, run, and wrap the outcome. Never raises."""
        try:
            args = self.args_model.model_validate(kwargs)
        except ValidationError as e:
            return self._failed(kwargs, f"invalid arguments: {e.error_count()} error(s): {e}")
        clean = args.model_dump(mode="json")
        try:
            outcome = self.fn(args)
        except ToolError as e:
            return self._failed(clean, str(e))
        except Exception as e:  # a tool bug must become "could not verify", not a crash
            return self._failed(clean, f"internal error: {type(e).__name__}")
        seen: set[EvidenceCode] = set()
        evidence = []
        for f in outcome.findings:
            if f.code in seen:
                continue
            seen.add(f.code)
            evidence.append(
                ToolEvidence(
                    evidence_id=make_id("ev", self.name, clean, f.code.value),
                    code=f.code,
                    source=self.name,
                    summary=f.summary,
                    detail=f.detail,
                )
            )
        return ToolResult(
            tool=self.name,
            call_id=make_id("call", self.name, clean),
            args=clean,
            ok=True,
            evidence=tuple(evidence),
            data=outcome.data,
        )

    def _failed(self, args: dict[str, Any], error: str) -> ToolResult:
        safe_args = {
            k: v for k, v in args.items() if isinstance(v, str | int | float | bool | None)
        }
        return ToolResult(
            tool=self.name,
            call_id=make_id("call", self.name, safe_args),
            args=safe_args,
            ok=False,
            error=error[:500],
        )


def define_tool(name: str, description: str, args_model: type[BaseModel]):
    def wrap(fn: Callable[..., Outcome]) -> Tool:
        return Tool(name, description, args_model, fn)

    return wrap


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]
