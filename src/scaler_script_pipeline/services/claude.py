from __future__ import annotations

import json
import logging
import time
from typing import TypeVar

from anthropic import Anthropic, AnthropicError
from pydantic import BaseModel, ValidationError

from scaler_script_pipeline.core.config import Settings
from scaler_script_pipeline.core.models import ClaudeError
from scaler_script_pipeline.services.tracing import TraceStore, TraceTimer

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self, settings: Settings, trace_store: TraceStore | None = None) -> None:
        self.settings = settings
        self.client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self.trace_store = trace_store

    def generate_model(
        self,
        system: str,
        user: str,
        model_type: type[T],
        *,
        trace_name: str | None = None,
        trace_metadata: dict | None = None,
    ) -> T:
        if self.client is None:
            raise ClaudeError(
                "ANTHROPIC_API_KEY is missing. Copy .env.example to .env and set the key."
            )

        started = time.perf_counter()
        trace_timer = TraceTimer()
        metadata = {
            "model": self.settings.anthropic_model,
            "response_model": model_type.__name__,
            **(trace_metadata or {}),
        }
        logger.info(
            "claude.request.start model=%s response_model=%s prompt_chars=%s",
            self.settings.anthropic_model,
            model_type.__name__,
            len(system) + len(user),
        )
        try:
            response = self.client.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=5000,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"{user}\n\nReturn only valid JSON matching this schema shape:\n"
                            f"{json.dumps(model_type.model_json_schema(), indent=2)}"
                        ),
                    }
                ],
            )
        except AnthropicError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                "claude.request.error model=%s response_model=%s elapsed_ms=%s",
                self.settings.anthropic_model,
                model_type.__name__,
                elapsed_ms,
            )
            self._record_trace(
                trace_name or model_type.__name__,
                system,
                user,
                model_type,
                metadata,
                started_at=trace_timer.started_at,
                elapsed_ms=elapsed_ms,
                error=str(exc),
            )
            raise ClaudeError(f"Claude API request failed: {exc}") from exc

        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        try:
            parsed = model_type.model_validate_json(_extract_json(text))
        except (ValidationError, ValueError) as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                "claude.response.invalid response_model=%s elapsed_ms=%s response_chars=%s",
                model_type.__name__,
                elapsed_ms,
                len(text),
            )
            self._record_trace(
                trace_name or model_type.__name__,
                system,
                user,
                model_type,
                metadata,
                raw_output=text,
                started_at=trace_timer.started_at,
                elapsed_ms=elapsed_ms,
                error=str(exc),
            )
            raise ClaudeError(f"Claude returned invalid {model_type.__name__} JSON: {exc}") from exc
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "claude.request.end model=%s response_model=%s elapsed_ms=%s response_chars=%s",
            self.settings.anthropic_model,
            model_type.__name__,
            elapsed_ms,
            len(text),
        )
        self._record_trace(
            trace_name or model_type.__name__,
            system,
            user,
            model_type,
            metadata,
            raw_output=text,
            parsed_output=parsed,
            started_at=trace_timer.started_at,
            elapsed_ms=elapsed_ms,
        )
        return parsed

    def _record_trace(
        self,
        name: str,
        system: str,
        user: str,
        model_type: type[BaseModel],
        metadata: dict,
        *,
        raw_output: str | None = None,
        parsed_output: BaseModel | None = None,
        started_at: str,
        elapsed_ms: int,
        error: str | None = None,
    ) -> None:
        if not self.trace_store:
            return
        self.trace_store.record_span(
            name=name,
            kind="llm",
            metadata=metadata,
            started_at=started_at,
            elapsed_ms=elapsed_ms,
            inputs={
                "system": system,
                "user": user,
                "schema": model_type.model_json_schema(),
                "prompt_chars": len(system) + len(user),
            },
            outputs={
                "raw_text": raw_output,
                "parsed": parsed_output.model_dump(mode="json") if parsed_output else None,
                "response_chars": len(raw_output or ""),
            },
            error=error,
        )


def _extract_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()
    start = min([idx for idx in [stripped.find("{"), stripped.find("[")] if idx >= 0], default=-1)
    if start > 0:
        stripped = stripped[start:]
    return stripped
