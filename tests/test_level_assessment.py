import unittest
from unittest import TestCase

from apex.core.level_assessment import (
    LEVELS,
    current_level,
    describe,
    gaps_to_next,
)


class LevelAssessmentTests(TestCase):
    def test_all_five_levels_defined(self):
        self.assertEqual(set(LEVELS.keys()), {1, 2, 3, 4, 5})

    def test_l1_with_only_conversational_capabilities(self):
        self.assertEqual(current_level({
            "conversation": True,
            "language_understanding": True,
            "helpful_response": True,
        }), 1)

    def test_l3_with_agent_capabilities(self):
        features = {
            "conversation": True,
            "language_understanding": True,
            "helpful_response": True,
            "reasoning": True,
            "reliability_evaluation": True,
            "hallucination_reduction": True,
            "autonomous_action": True,
            "task_execution": True,
            "plan_execution": True,
            "outcome_verification": True,
        }

        self.assertEqual(current_level(features), 3)

    def test_level_assessment_uses_objectives_capability_names(self):
        self.assertIn("organization_scale_coordination", LEVELS[5].required_capabilities)

    def test_l5_requires_all_capabilities(self):
        features = {
            capability: True
            for criterion in LEVELS.values()
            for capability in criterion.required_capabilities
        }

        self.assertEqual(current_level(features), 5)
        self.assertEqual(gaps_to_next(features), [])

    def test_missing_l4_capability_blocks_next_level(self):
        features = {
            capability: True
            for level, criterion in LEVELS.items()
            if level <= 3
            for capability in criterion.required_capabilities
        }

        self.assertEqual(current_level(features), 3)
        self.assertEqual(gaps_to_next(features), [
            "original_ideas",
            "validated_novelty",
            "invention",
            "measured_improvement",
        ])

    def test_gaps_at_l1(self):
        self.assertEqual(
            gaps_to_next({
                "conversation": True,
                "language_understanding": True,
                "helpful_response": True,
            }),
            ["reasoning", "reliability_evaluation", "hallucination_reduction"],
        )

    def test_describe_returns_all_levels(self):
        result = describe()
        self.assertEqual(set(result.keys()), {1, 2, 3, 4, 5})
        for description in result.values():
            self.assertIsInstance(description, str)
            self.assertGreater(len(description), 0)

    def test_empty_features_yields_level_zero(self):
        self.assertEqual(current_level({}), 0)
        self.assertEqual(gaps_to_next({}), ["conversation", "language_understanding", "helpful_response"])


if __name__ == "__main__":
    unittest.main()
