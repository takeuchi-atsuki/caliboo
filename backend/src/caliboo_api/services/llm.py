"""設定時だけ外部推論を行う境界。本文・認証情報を例外へ含めない。"""

import json
import math
import os
from dataclasses import dataclass, field
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError


class LLMError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class LLMSettings:
    model: str
    api_key: str = field(repr=False)
    timeout: float = 30


def provider_name() -> str:
    provider = os.environ.get("CALIBOO_AI_PROVIDER", "manual")
    if provider not in {"manual", "openai"}:
        raise LLMError("invalid_configuration")
    return provider


def settings() -> LLMSettings:
    model = os.environ.get("CALIBOO_AI_MODEL", "").strip()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    try:
        timeout = float(os.environ.get("CALIBOO_AI_TIMEOUT_SECONDS", "30"))
    except ValueError:
        raise LLMError("invalid_configuration") from None
    if not model or not key or not math.isfinite(timeout) or not 1 <= timeout <= 120:
        raise LLMError("invalid_configuration")
    return LLMSettings(model=model, api_key=key, timeout=timeout)


def strict_schema(schema: dict) -> dict:
    result = {}
    for key, value in schema.items():
        if key == "default":
            continue
        if isinstance(value, dict):
            value = strict_schema(value)
        elif isinstance(value, list):
            value = [strict_schema(item) if isinstance(item, dict) else item for item in value]
        result[key] = value
    if result.get("type") == "object":
        result["additionalProperties"] = False
        result["required"] = list(result.get("properties", {}))
    return result


def generate_json(instructions: str, materials: dict, output_type: type[BaseModel],
                  config: LLMSettings) -> BaseModel:
    content = json.dumps(materials, ensure_ascii=False, allow_nan=False)
    if len(content.encode("utf-8")) > 200_000:
        raise LLMError("input_too_large")
    request = Request("https://api.openai.com/v1/responses", method="POST", headers={
        "Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json",
    }, data=json.dumps({
        "model": config.model, "store": False, "max_output_tokens": 8192,
        "instructions": instructions,
        "input": [{"role": "user", "content": content}],
        "text": {"format": {
            "type": "json_schema", "name": output_type.__name__, "strict": True,
            "schema": strict_schema(output_type.model_json_schema()),
        }},
    }, ensure_ascii=False).encode("utf-8"))
    try:
        with urlopen(request, timeout=config.timeout) as response:
            raw = response.read(1_000_001)
    except (URLError, OSError):
        raise LLMError("provider_unavailable") from None
    if len(raw) > 1_000_000:
        raise LLMError("invalid_output")
    try:
        packet = json.loads(raw)
        if packet["status"] != "completed":
            raise LLMError("incomplete_output")
        contents = [part for item in packet["output"] if item["type"] == "message"
                    for part in item["content"]]
        if not contents or any(part["type"] != "output_text" for part in contents):
            raise LLMError("invalid_output")
        text = "".join(part["text"] for part in contents)
        return output_type.model_validate_json(text, strict=True)
    except (ValueError, KeyError, TypeError, ValidationError):
        raise LLMError("invalid_output") from None
