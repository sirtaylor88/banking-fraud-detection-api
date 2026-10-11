"""Tests for models module discovery and loading."""

from pathlib import Path
from unittest.mock import patch

from src.backend.app.core.model_registry import discover_models, load_models

REGISTRY = "src.backend.app.core.model_registry"


def test_discover_models_finds_models_and_skips_excluded_dirs(
    tmp_path: Path,
) -> None:
    """Test that every models.py is found except those in excluded dirs."""
    for rel in ("models.py", "auth/models.py", "__pycache__/models.py"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).touch()

    fake_file = str(tmp_path / "core" / "model_registry.py")
    with patch(f"{REGISTRY}.__file__", fake_file):
        assert discover_models() == [
            "src.backend.app.auth.models",
            "src.backend.app.models",
        ]


def test_discover_models_finds_real_app_models() -> None:
    """Test that the auth models module is discovered in the real app."""
    assert "src.backend.app.auth.models" in discover_models()


def test_load_models_imports_modules_and_logs_failures() -> None:
    """Test that each module is imported and import errors are logged."""
    error = ImportError("boom")
    with (
        patch(f"{REGISTRY}.discover_models", return_value=["ok.models", "bad.models"]),
        patch(f"{REGISTRY}.logger") as logger,
        # * Patched last: patch() itself imports its targets via import_module.
        patch(f"{REGISTRY}.importlib.import_module", side_effect=[None, error]) as imp,
    ):
        load_models()

    assert [c.args[0] for c in imp.call_args_list] == ["ok.models", "bad.models"]
    logger.error.assert_called_once_with("Failed to import module bad.models: boom")
