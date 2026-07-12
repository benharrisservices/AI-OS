"""System check tests."""

from ai_os.system_check import run_full_check


class TestSystemCheck:
    def test_full_check_runs(self) -> None:
        report = run_full_check()
        assert len(report.results) >= 8
        names = {r.name for r in report.results}
        assert "knowledge_engine" in names
        assert "integrations" in names
        assert "model_router" in names

    def test_dependencies_ok(self) -> None:
        report = run_full_check()
        dep = next(r for r in report.results if r.name == "dependencies")
        assert dep.status == "ok"
