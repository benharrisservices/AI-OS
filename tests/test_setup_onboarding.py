"""Setup and onboarding tests."""

from pathlib import Path

import pytest

from ai_os.knowledge.onboarding import load_presets, validate_import
from ai_os.setup import run_setup


class TestSetup:
    def test_run_setup_returns_report(self) -> None:
        report = run_setup()
        assert len(report.steps) >= 5
        names = {s.name for s in report.steps}
        assert "python_version" in names
        assert "writable_directories" in names
        assert report.recommended_next


class TestOnboarding:
    def test_load_presets_ordered(self) -> None:
        presets = load_presets()
        assert len(presets) >= 9
        orders = [p.order for p in presets]
        assert orders == sorted(orders)
        ids = {p.id for p in presets}
        assert "ai-os-repo" in ids
        assert "exported-chats" in ids

    def test_validate_ai_os_docs(self) -> None:
        docs = Path("./docs")
        if not docs.exists():
            pytest.skip("docs/ not present")
        result = validate_import("ai-os-repo", docs)
        assert result.total_files >= 1
        assert result.preset.id == "ai-os-repo"

    def test_validate_unknown_preset(self) -> None:
        with pytest.raises(ValueError, match="Unknown preset"):
            validate_import("not-a-preset", ".")

    def test_validate_missing_path(self) -> None:
        result = validate_import("ai-os-repo", "/nonexistent/path/xyz")
        assert result.errors
        assert not result.ready
