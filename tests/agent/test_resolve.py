"""Workflow template variable resolution tests."""

from ai_os.agent.resolve import build_bindings, init_workflow_variables, resolve_value


class TestWorkflowVariables:
    def test_date_resolves_in_path(self) -> None:
        variables = init_workflow_variables({"focus": "test"})
        bindings = build_bindings(
            task_input={"focus": "test", "output_path": "./memory/briefings/morning-{{date}}.md"},
            step_outputs={},
            variables=variables,
        )
        resolved = resolve_value("{{input.output_path}}", bindings)
        assert "{{" not in resolved
        assert resolved.endswith(".md")
        assert "morning-" in resolved

    def test_slug_from_input(self) -> None:
        variables = init_workflow_variables({"destination": "San Francisco"})
        bindings = build_bindings(
            task_input={"destination": "San Francisco"},
            step_outputs={},
            variables=variables,
        )
        assert bindings["destination_slug"] == "san-francisco"
        resolved = resolve_value("./memory/travel/{{destination_slug}}.md", bindings)
        assert "san-francisco" in resolved
