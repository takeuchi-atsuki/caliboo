"""PL-4/5/6: 実際の送信スキーマと合成HTTP応答の必須項目を照合する。"""

import json
from copy import deepcopy
from io import BytesIO

import pytest

from caliboo_api.schemas.agent_jobs import ProposalAgentResult, StrengthResult
from caliboo_api.services import llm
from caliboo_api.services.assignment_proposal.llm_provider import GeneratedProposal
from caliboo_api.services.chat_reply import StudyAnswer
from caliboo_api.services.grounded_ojt import GroundedAnswer
from caliboo_api.services.job_inference import CandidateBatch, RegeneratedProposal


EVIDENCE = {"materialId": "material:0", "quote": "根拠を照合した。"}
CANDIDATE = dict(label="根拠を確認する力", skillCode="TEST", kind="ability", confidence=80,
                 summary="根拠を照合した行動から判断した", scopeNote="合成資料の範囲",
                 evidence=[EVIDENCE], growthAction="次の共有会で試す")
PROPOSAL = dict(title="根拠を説明する練習", body="理由を2つ添える", messageForMember="試す",
                rationale="説明を練習するため", estimateMinutes=15, evidence=[EVIDENCE])
CASES = [
    (CandidateBatch, dict(candidates=[CANDIDATE], notes="観測に基づく候補")),
    (GeneratedProposal, dict(**PROPOSAL, themeKey="review", aim="説明力を伸ばす")),
    (RegeneratedProposal, PROPOSAL),
    (GroundedAnswer, dict(answer="原文を確認する", insufficientEvidence=False,
                          evidence=[dict(knowledgeId="k1", quote="手順を記録する。")])),
    (StudyAnswer, dict(answer="条件と用語を比較しましょう。")),
]
CONFIG = llm.LLMSettings("synthetic-model", "synthetic-key")


def assert_schema_keys(schema, value, root):
    if "$ref" in schema:
        definition = schema["$ref"].removeprefix("#/$defs/")
        schema = root["$defs"][definition]
    if isinstance(value, dict):
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"]) == set(value)
        for key, item in value.items():
            assert_schema_keys(schema["properties"][key], item, root)
    elif isinstance(value, list):
        assert schema["type"] == "array"
        for item in value:
            assert_schema_keys(schema["items"], item, root)
    assert "default" not in schema


def object_paths(value, path=()):
    if isinstance(value, dict):
        yield path
        for key, item in value.items():
            yield from object_paths(item, (*path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from object_paths(item, (*path, index))


def get_object(value, path):
    for key in path:
        value = value[key]
    return value


def respond_with(monkeypatch, output_type, expected, payload):
    def respond(request, timeout):
        body = json.loads(request.data)
        format_ = body["text"]["format"]
        assert format_["name"] == output_type.__name__
        assert format_["strict"] is True
        schema = format_["schema"]
        assert_schema_keys(schema, expected, schema)
        return BytesIO(json.dumps(dict(status="completed", output=[dict(
            type="message", content=[dict(type="output_text", text=json.dumps(payload))])]
        )).encode())

    monkeypatch.setattr(llm, "urlopen", respond)
    return llm.generate_json("合成検証", {}, output_type, CONFIG)


@pytest.mark.parametrize("output_type, sample", CASES, ids=[case[0].__name__ for case in CASES])
def test_provider_response_matches_strict_schema(monkeypatch, output_type, sample):
    assert respond_with(monkeypatch, output_type, sample, sample).model_dump() == sample


@pytest.mark.parametrize("output_type, sample", CASES, ids=[case[0].__name__ for case in CASES])
def test_provider_rejects_each_missing_field_and_unknown_key(monkeypatch, output_type, sample):
    # 全てのオブジェクト（候補、根拠などの入れ子も含む）の各必須キーを欠落させる。
    for path in object_paths(sample):
        for key in get_object(sample, path):
            payload = deepcopy(sample)
            del get_object(payload, path)[key]
            with pytest.raises(llm.LLMError, match="^invalid_output$"):
                respond_with(monkeypatch, output_type, sample, payload)
        payload = deepcopy(sample)
        get_object(payload, path)["unexpected"] = True
        with pytest.raises(llm.LLMError, match="^invalid_output$"):
            respond_with(monkeypatch, output_type, sample, payload)


def test_past_manual_payloads_keep_their_defaults():
    trace = dict(provider="codex_agent", model="synthetic", promptVersion="legacy")
    candidate = {key: value for key, value in CANDIDATE.items()
                 if key not in {"kind", "summary", "scopeNote"}}
    result = StrengthResult(trace=trace, candidates=[candidate], notes="旧形式")
    assert result.candidates[0].kind == "ability"
    assert result.candidates[0].summary == result.candidates[0].scopeNote == ""
    proposal = {key: value for key, value in PROPOSAL.items()
                if key not in {"messageForMember", "evidence"}}
    result = ProposalAgentResult(trace=trace, **proposal)
    assert result.messageForMember == "" and result.evidence == []
