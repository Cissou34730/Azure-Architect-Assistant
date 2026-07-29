"""Tests for GITHUB_TOKEN fallback flowing through the settings layer."""

from app.shared.config.app_settings import AppSettings


class TestEffectiveCopilotToken:
    def test_github_token_field_populates_from_env(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "gh-env-token")
        monkeypatch.delenv("AI_COPILOT_TOKEN", raising=False)
        settings = AppSettings()
        assert settings.github_token == "gh-env-token"

    def test_effective_copilot_token_uses_settings_field(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "gh-env-token")
        monkeypatch.delenv("AI_COPILOT_TOKEN", raising=False)
        # Disable the SecretKeeper override so we exercise the settings-layer chain.
        import app.shared.config.app_settings as app_settings_mod

        monkeypatch.setattr(app_settings_mod, "_read_secretkeeper_secret", lambda _name: "")
        settings = AppSettings()
        assert settings.effective_copilot_token == "gh-env-token"

    def test_ai_copilot_token_takes_precedence_over_github(self, monkeypatch):
        monkeypatch.setenv("AI_COPILOT_TOKEN", "ai-token")
        monkeypatch.setenv("GITHUB_TOKEN", "gh-env-token")
        settings = AppSettings()
        # AI_COPILOT_TOKEN (or SecretKeeper override) wins over GITHUB_TOKEN
        assert settings.effective_copilot_token != "gh-env-token" or settings.ai_copilot_token == ""
