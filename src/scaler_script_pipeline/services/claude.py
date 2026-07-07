from __future__ import annotations

import json
import logging
import time
from typing import TypeVar

from anthropic import Anthropic, AnthropicError
from pydantic import BaseModel, ValidationError

from scaler_script_pipeline.core.config import Settings
from scaler_script_pipeline.core.models import ClaudeError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    def generate_model(self, system: str, user: str, model_type: type[T]) -> T:
        if self.client is None:
            raise ClaudeError(
                "ANTHROPIC_API_KEY is missing. Copy .env.example to .env and set the key."
            )

        started = time.perf_counter()
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
            raise ClaudeError(f"Claude returned invalid {model_type.__name__} JSON: {exc}") from exc
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "claude.request.end model=%s response_model=%s elapsed_ms=%s response_chars=%s",
            self.settings.anthropic_model,
            model_type.__name__,
            elapsed_ms,
            len(text),
        )
        return parsed


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
