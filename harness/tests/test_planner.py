from src.runtime.planner import PlanStatus, SimplePlanner


class TestSimplePlanner:
    def test_create_plan_marks_first_step_in_progress(self):
        planner = SimplePlanner()

        plan = planner.create_plan(
            "Fix tests",
            enabled_tools=["read_file", "write_file", "run_command"],
        )

        assert plan.goal == "Fix tests"
        assert len(plan.steps) == 3
        assert plan.steps[0].status == PlanStatus.IN_PROGRESS
        assert plan.steps[1].status == PlanStatus.PENDING
        assert plan.steps[2].title == "Run a verification command or test when useful"

    def test_advance_after_turn_moves_to_next_step(self):
        plan = SimplePlanner().create_plan("Do work", enabled_tools=["write_file"])

        plan.advance_after_turn()

        assert plan.steps[0].status == PlanStatus.DONE
        assert plan.steps[1].status == PlanStatus.IN_PROGRESS

    def test_mark_done_completes_all_steps(self):
        plan = SimplePlanner().create_plan("Do work", enabled_tools=["write_file"])

        plan.mark_done()

        assert all(step.status == PlanStatus.DONE for step in plan.steps)
        assert plan.to_dict()["steps"][0]["status"] == "done"

    def test_plan_prompt_text_contains_statuses(self):
        plan = SimplePlanner().create_plan("Fix tests", enabled_tools=["read_file"])

        text = plan.to_prompt_text()

        assert "Goal: Fix tests" in text
        assert "[in_progress] 1." in text

    def test_maybe_replan_only_once_for_same_step(self):
        plan = SimplePlanner().create_plan("Fix tests", enabled_tools=["read_file"])

        assert plan.maybe_replan("tool failure") is True
        assert "Re-inspect relevant files after the tool failure" in plan.current_step_title()
        assert plan.maybe_replan("tool failure") is False

    def test_create_plan_includes_suggested_tools(self):
        plan = SimplePlanner().create_plan(
            "Fix tests",
            enabled_tools=["read_file", "write_file", "run_command"],
        )

        assert plan.steps[0].suggested_tools == ["read_file"]
        assert "write_file" in plan.steps[1].suggested_tools
        assert plan.steps[2].suggested_tools == ["run_command"]
        assert "tools: read_file" in plan.to_prompt_text()

    def test_advance_after_tools_uses_suggested_tools(self):
        plan = SimplePlanner().create_plan(
            "Fix tests",
            enabled_tools=["read_file", "write_file", "run_command"],
        )

        assert plan.advance_after_tools(["write_file"], success_count=1) is False
        assert plan.advance_after_tools(["read_file"], success_count=1) is True
        assert plan.steps[0].status == PlanStatus.DONE

    def test_advance_after_tools_requires_successful_matching_tool(self):
        plan = SimplePlanner().create_plan(
            "Fix tests",
            enabled_tools=["read_file", "write_file", "run_command"],
        )

        assert plan.advance_after_tools(["run_command"], success_count=1) is False
        assert plan.steps[0].status == PlanStatus.IN_PROGRESS
        assert plan.advance_after_tools(["read_file"], success_count=1) is True
        assert plan.steps[0].status == PlanStatus.DONE
        assert plan.steps[1].status == PlanStatus.IN_PROGRESS
