"""Terminal prototype entry point: generate one day's meal plan for a hardcoded test
profile and print the result. No CLI parsing beyond an optional day argument -- this is
a milestone script, not the final interface.
"""
import json
import sys

from core.agent import plan_generator
from core.models import Profile
from core.types import Goal

# Error codes GenerationResult.error can carry (see core/agent/llm_adapter.py), each
# with a message a terminal user can act on.
ERROR_MESSAGES = {
    "rate_limited": "The LLM provider rate-limited the request. Wait a bit and try again.",
    "timeout": "The LLM provider timed out (or errored transiently) and retries were exhausted.",
    "api_error": "Could not reach the LLM provider (connection or setup error). Check "
    "LLM_PROVIDER and the matching API key in .env.",
    "invalid_output": "The LLM never produced a valid plan (bad tool call or output "
    "that failed PlanPropose validation), even after the forced final attempt.",
}

# Test-case profile for this prototype, hardcoded per the milestone spec.
TEST_PROFILE = Profile(
    age_years=45,
    weight_kg=100,
    height_cm=196,
    goal=Goal.WEIGHT_LOSS,
)


def main() -> None:
    day = sys.argv[1] if len(sys.argv) > 1 else "monday"

    result = plan_generator.generate_daily_plan(TEST_PROFILE, day)

    if result.error:
        message = ERROR_MESSAGES.get(result.error, result.error)
        print(f"Plan generation failed ({result.error}): {message}")
        sys.exit(1)

    assert result.plan is not None
    print(json.dumps(result.plan.model_dump(), indent=2))


if __name__ == "__main__":
    main()
