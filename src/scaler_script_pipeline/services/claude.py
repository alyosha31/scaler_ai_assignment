from __future__ import annotations

import json
from typing import TypeVar

from anthropic import Anthropic, AnthropicError
from pydantic import BaseModel, ValidationError

from scaler_script_pipeline.core.config import Settings
from scaler_script_pipeline.core.models import ClaudeError

T = TypeVar("T", bound=BaseModel)


class ClaudeClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    def generate_model(self, system: str, user: str, model_type: type[T]) -> T:
        if self.client is None:
            raise ClaudeError(
                "ANTHROPIC_API_KEY is missing. Copy .env.example to .env and set the key."
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
            raise ClaudeError(f"Claude API request failed: {exc}") from exc

        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        try:
            return model_type.model_validate_json(_extract_json(text))
        except (ValidationError, ValueError) as exc:
            raise ClaudeError(f"Claude returned invalid {model_type.__name__} JSON: {exc}") from exc


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
