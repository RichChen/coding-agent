from pathlib import Path

from src.harness.factory import load_config


def test_nested_profile_finds_repo_dotenv(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    (tmp_path / ".env").write_text("LLM_API_KEY=from-dotenv\n", encoding="utf-8")
    nested = tmp_path / "configs" / "sprint"
    nested.mkdir(parents=True)
    (nested / "b0.yaml").write_text(
        "llm:\n  base_url: http://example\n  api_key: ${LLM_API_KEY}\n  model: m\nruntime:\n  max_steps: 1\n",
        encoding="utf-8",
    )
    loaded = load_config(nested / "b0.yaml")
    assert loaded["llm"]["api_key"] == "from-dotenv"
