from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv


REQUIRED_ENV_VARS = (
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_TEMPERATURE",
    "DEEPSEEK_MAX_RETRIES",
    "DEEPSEEK_TIMEOUT_SECONDS",
)

FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(?P<body>.*?)\s*```\s*$", re.DOTALL)


class DeepSeekConfigError(RuntimeError):
    """Raised when DeepSeek environment configuration is incomplete or invalid."""


class DeepSeekResponseError(RuntimeError):
    """Raised when DeepSeek returns an unusable response."""


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    base_url: str
    model: str
    temperature: float
    max_retries: int
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "DeepSeekConfig":
        load_dotenv()

        missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
        if missing:
            joined = ", ".join(missing)
            raise DeepSeekConfigError(f"Missing required DeepSeek env vars: {joined}")

        try:
            temperature = float(os.environ["DEEPSEEK_TEMPERATURE"])
            max_retries = int(os.environ["DEEPSEEK_MAX_RETRIES"])
            timeout_seconds = float(os.environ["DEEPSEEK_TIMEOUT_SECONDS"])
        except ValueError as exc:
            raise DeepSeekConfigError(
                "DEEPSEEK_TEMPERATURE, DEEPSEEK_MAX_RETRIES, and "
                "DEEPSEEK_TIMEOUT_SECONDS must be numeric."
            ) from exc

        if max_retries < 1:
            raise DeepSeekConfigError("DEEPSEEK_MAX_RETRIES must be at least 1.")

        if timeout_seconds <= 0:
            raise DeepSeekConfigError("DEEPSEEK_TIMEOUT_SECONDS must be greater than 0.")

        return cls(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=os.environ["DEEPSEEK_BASE_URL"].rstrip("/"),
            model=os.environ["DEEPSEEK_MODEL"],
            temperature=temperature,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )


@dataclass(frozen=True)
class DeepSeekResult:
    data: dict[str, Any]
    raw_content: str
    attempts: int


def strip_markdown_fences(content: str) -> str:
    match = FENCE_RE.match(content)
    if match:
        return match.group("body").strip()
    return content.strip()


class DeepSeekClient:
    def __init__(
        self,
        config: DeepSeekConfig | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config or DeepSeekConfig.from_env()
        self.session = session or requests.Session()

    @property
    def chat_completions_url(self) -> str:
        base_url = self.config.base_url
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def translate_json(self, system_prompt: str, user_prompt: str) -> DeepSeekResult:
        last_error: Exception | None = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                raw_content = self._request_completion(system_prompt, user_prompt)
                parsed = self.parse_json_content(raw_content)
                return DeepSeekResult(data=parsed, raw_content=raw_content, attempts=attempt)
            except (requests.RequestException, DeepSeekResponseError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= self.config.max_retries:
                    break
                time.sleep(2 ** (attempt - 1))

        raise DeepSeekResponseError(
            f"DeepSeek request failed after {self.config.max_retries} attempts: {last_error}"
        ) from last_error

    def _request_completion(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        response = self.session.post(
            self.chat_completions_url,
            headers=headers,
            json=payload,
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()

        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekResponseError("DeepSeek response missing message content.") from exc

        if not isinstance(content, str) or not content.strip():
            raise DeepSeekResponseError("DeepSeek response content was empty.")

        return content

    @staticmethod
    def parse_json_content(content: str) -> dict[str, Any]:
        stripped = strip_markdown_fences(content)
        parsed = json.loads(stripped)

        if not isinstance(parsed, dict):
            raise DeepSeekResponseError("DeepSeek JSON response must be an object.")

        return parsed
