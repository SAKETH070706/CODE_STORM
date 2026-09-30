import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from core.llm_client import call_llm, _clean_and_heal_json, LLMResult

def test_json_healing_on_truncated_brace():
    truncated = '{"name": "hackathon_project", "score": 95'
    ok, parsed, err = _clean_and_heal_json(truncated)
    assert ok is True
    assert parsed["name"] == "hackathon_project"
    assert parsed["score"] == 95

def test_json_healing_with_markdown_fences():
    fenced = '```json\n{"status": "ok", "items": [1, 2, 3]}\n```'
    ok, parsed, err = _clean_and_heal_json(fenced)
    assert ok is True
    assert parsed["status"] == "ok"
    assert parsed["items"] == [1, 2, 3]

def test_json_unhealable_fails_loud():
    broken = "This is not json at all, random string"
    ok, parsed, err = _clean_and_heal_json(broken)
    assert ok is False
    assert parsed is None

@patch("groq.Groq")
def test_fallback_on_groq_429_exhaustion(mock_groq_class):
    mock_groq_instance = MagicMock()
    mock_groq_instance.chat.completions.create.side_effect = Exception("429 Too Many Requests (Rate limit reached)")
    mock_groq_class.return_value = mock_groq_instance

    with patch("google.genai.Client") as mock_gemini_class:
        mock_gemini_instance = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "Hello from Gemini fallback!"
        mock_gemini_instance.models.generate_content.return_value = mock_resp
        mock_gemini_class.return_value = mock_gemini_instance

        result = call_llm(system_prompt="Test", user_prompt="Ping")
        assert result.success is True
        assert "Gemini" in result.text
        assert "gemini" in result.provider_used

def test_service_unavailable_when_all_fail():
    with patch("groq.Groq") as mock_groq, patch("google.genai.Client") as mock_gemini:
        mock_groq.side_effect = Exception("Groq network down")
        mock_gemini.side_effect = Exception("Gemini network down")

        result = call_llm(system_prompt="Test", user_prompt="Ping")
        assert result.success is False
        assert result.error == "SERVICE_UNAVAILABLE"

@pytest.fixture(autouse=True)
def configured_mock_models(monkeypatch):
    # Unit tests do not depend on developer secrets or provider model availability.
    monkeypatch.setattr("core.llm_client.GROQ_API_KEY", "offline-test-key")
    monkeypatch.setattr("core.llm_client.GEMINI_API_KEY", "offline-test-key")
    monkeypatch.setattr("core.llm_client.GROQ_MODELS", ["mock-groq"])
    monkeypatch.setattr("core.llm_client.GEMINI_MODELS", ["mock-gemini"])


def test_gemini_system_instruction_is_separate():
    with patch("groq.Groq", side_effect=RuntimeError("offline")), patch("google.genai.Client") as client:
        client.return_value.models.generate_content.return_value.text = "ok"
        result = call_llm("policy", "untrusted content")
        assert result.success
        kwargs = client.return_value.models.generate_content.call_args.kwargs
        assert kwargs["contents"] == ["untrusted content"]
        assert kwargs["config"].system_instruction == "policy"
