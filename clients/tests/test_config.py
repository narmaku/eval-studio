"""Tests for eval-studio SDK configuration management."""

import stat
from pathlib import Path

import pytest

from eval_studio.config import EvalStudioConfig, load_config, save_config


class TestEvalStudioConfig:
    def test_defaults(self) -> None:
        cfg = EvalStudioConfig()
        assert cfg.url == "http://localhost:8000"
        assert cfg.api_key is None

    def test_constructor_params(self) -> None:
        cfg = EvalStudioConfig(url="https://prod.example.com", api_key="esk_abc")
        assert cfg.url == "https://prod.example.com"
        assert cfg.api_key == "esk_abc"

    def test_url_strips_trailing_slash(self) -> None:
        cfg = EvalStudioConfig(url="http://localhost:8000/")
        assert cfg.url == "http://localhost:8000"


class TestLoadConfigFromEnv:
    def test_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EVAL_STUDIO_URL", "https://env.example.com")
        monkeypatch.delenv("EVAL_STUDIO_API_KEY", raising=False)
        cfg = load_config()
        assert cfg.url == "https://env.example.com"

    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EVAL_STUDIO_API_KEY", "esk_envkey")
        monkeypatch.delenv("EVAL_STUDIO_URL", raising=False)
        cfg = load_config()
        assert cfg.api_key == "esk_envkey"

    def test_both_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EVAL_STUDIO_URL", "https://env.example.com")
        monkeypatch.setenv("EVAL_STUDIO_API_KEY", "esk_envkey")
        cfg = load_config()
        assert cfg.url == "https://env.example.com"
        assert cfg.api_key == "esk_envkey"


class TestLoadConfigFromFile:
    def test_config_from_toml_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EVAL_STUDIO_URL", raising=False)
        monkeypatch.delenv("EVAL_STUDIO_API_KEY", raising=False)
        config_dir = tmp_path / "eval-studio"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.toml"
        config_file.write_text('[default]\nurl = "https://file.example.com"\napi_key = "esk_filekey"\n')
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        cfg = load_config()
        assert cfg.url == "https://file.example.com"
        assert cfg.api_key == "esk_filekey"

    def test_missing_config_file_uses_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EVAL_STUDIO_URL", raising=False)
        monkeypatch.delenv("EVAL_STUDIO_API_KEY", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        cfg = load_config()
        assert cfg.url == "http://localhost:8000"
        assert cfg.api_key is None


class TestConfigPriority:
    def test_env_overrides_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_dir = tmp_path / "eval-studio"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.toml"
        config_file.write_text('[default]\nurl = "https://file.example.com"\napi_key = "esk_filekey"\n')
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.setenv("EVAL_STUDIO_URL", "https://env.example.com")
        monkeypatch.delenv("EVAL_STUDIO_API_KEY", raising=False)
        cfg = load_config()
        assert cfg.url == "https://env.example.com"
        # api_key should fall through to file value since env is not set
        assert cfg.api_key == "esk_filekey"

    def test_constructor_overrides_everything(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_dir = tmp_path / "eval-studio"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.toml"
        config_file.write_text('[default]\nurl = "https://file.example.com"\napi_key = "esk_filekey"\n')
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.setenv("EVAL_STUDIO_URL", "https://env.example.com")
        monkeypatch.setenv("EVAL_STUDIO_API_KEY", "esk_envkey")
        cfg = load_config(url="https://ctor.example.com", api_key="esk_ctorkey")
        assert cfg.url == "https://ctor.example.com"
        assert cfg.api_key == "esk_ctorkey"


class TestSaveConfig:
    def test_save_creates_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        save_config(url="https://saved.example.com", api_key="esk_saved")
        config_file = tmp_path / "eval-studio" / "config.toml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "https://saved.example.com" in content
        assert "esk_saved" in content

    def test_save_sets_permissions(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        save_config(url="https://saved.example.com", api_key="esk_saved")
        config_file = tmp_path / "eval-studio" / "config.toml"
        mode = config_file.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600

    def test_save_then_load_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.delenv("EVAL_STUDIO_URL", raising=False)
        monkeypatch.delenv("EVAL_STUDIO_API_KEY", raising=False)
        save_config(url="https://round.example.com", api_key="esk_round")
        cfg = load_config()
        assert cfg.url == "https://round.example.com"
        assert cfg.api_key == "esk_round"
