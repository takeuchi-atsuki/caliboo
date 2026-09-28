"""外部ネットワークを使わずResponses APIの契約と失敗境界を検証する。"""

import json
from io import BytesIO
from urllib.error import URLError

import pytest
from pydantic import BaseModel, ConfigDict

from caliboo_api.services import llm


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


@pytest.fixture(autouse=True)
def clean_config(monkeypatch):
    for name in ("CALIBOO_AI_PROVIDER", "CALIBOO_AI_MODEL", "OPENAI_API_KEY",
                 "CALIBOO_AI_TIMEOUT_SECONDS"):
        monkeypatch.delenv(name, raising=False)


def packet(text='{"text":"回答"}', status="completed"):
    return dict(status=status, output=[dict(type="message", content=[dict(
        type="output_text", text=text)])])


def test_configuration_requires_explicit_selection_and_secrets(monkeypatch):
    assert llm.provider_name() == "manual"
    with pytest.raises(llm.LLMError, match="invalid_configuration"):
        llm.settings()
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    monkeypatch.setenv("CALIBOO_AI_MODEL", "configured-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    assert llm.provider_name() == "openai"
    assert llm.settings().model == "configured-model"
    assert "test-secret" not in repr(llm.settings())
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "unknown")
    with pytest.raises(llm.LLMError, match="invalid_configuration"):
        llm.provider_name()
    for value in ("bad", "nan", "inf", "0", "121"):
        monkeypatch.setenv("CALIBOO_AI_TIMEOUT_SECONDS", value)
        with pytest.raises(llm.LLMError, match="invalid_configuration"):
            llm.settings()


def test_request_contract(monkeypatch):
    def respond(request, timeout):
        assert request.full_url == "https://api.openai.com/v1/responses"
        assert request.get_header("Authorization") == "Bearer test-secret"
        body = json.loads(request.data)
        assert body["model"] == "configured-model"
        assert body["store"] is False
        assert "tools" not in body
        assert body["instructions"] == "instruction"
        assert body["text"]["format"]["strict"] is True
        assert body["text"]["format"]["schema"]["additionalProperties"] is False
        assert timeout == 4
        return BytesIO(json.dumps(packet(), ensure_ascii=False).encode())
    monkeypatch.setattr(llm, "urlopen", respond)
    result = llm.generate_json("instruction", {"sources": ["untrusted"]}, Output,
                               llm.LLMSettings("configured-model", "test-secret", 4))
    assert result.text == "回答"


@pytest.mark.parametrize("response", [
    packet("not json"), packet('{"text":123}'), packet('{"text":"x","extra":1}'),
    packet(status="incomplete"), {"status": "completed", "output": []},
    {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal"}]}]},
    {}, [], {"status": "completed", "output": [{"type": "message"}]},
])
def test_bad_provider_output_is_rejected(monkeypatch, response):
    monkeypatch.setattr(llm, "urlopen", lambda request, timeout: BytesIO(
        json.dumps(response).encode()))
    with pytest.raises(llm.LLMError):
        llm.generate_json("instructions", {}, Output, llm.LLMSettings("model", "secret"))


@pytest.mark.parametrize("error", [URLError("private service details"), TimeoutError("secret")])
def test_network_errors_do_not_expose_provider_details(monkeypatch, error):
    def fail(request, timeout):
        raise error
    monkeypatch.setattr(llm, "urlopen", fail)
    with pytest.raises(llm.LLMError) as caught:
        llm.generate_json("instructions", {}, Output, llm.LLMSettings("model", "secret"))
    assert str(caught.value) == "provider_unavailable"


def test_size_limits_and_strict_nested_schema(monkeypatch):
    with pytest.raises(llm.LLMError, match="input_too_large"):
        llm.generate_json("instructions", {"text": "x" * 200_001}, Output,
                          llm.LLMSettings("model", "secret"))
    monkeypatch.setattr(llm, "urlopen", lambda request, timeout: BytesIO(b"x" * 1_000_001))
    with pytest.raises(llm.LLMError, match="invalid_output"):
        llm.generate_json("instructions", {}, Output, llm.LLMSettings("model", "secret"))
    schema = llm.strict_schema({"type": "object", "properties": {"items": {
        "type": "array", "items": {"anyOf": [{"type": "object", "properties": {
            "name": {"type": "string", "default": "x"}}}, {"type": "null"}]}}}})
    inner = schema["properties"]["items"]["items"]["anyOf"][0]
    assert inner["required"] == ["name"] and inner["additionalProperties"] is False
    assert "default" not in inner["properties"]["name"]
