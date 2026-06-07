from unittest import TestCase

import unittest

from apex.core.level_assessment import (
    LEVELS,
    current_level,
    describe,
    gaps_to_next,
)


class LevelAssessmentTests(TestCase):
    def test_all_five_levels_defined(self):
        self.assertEqual(set(LEVELS.keys()), {1, 2, 3, 4, 5})

    def test_l1_with_only_conversational(self):
        self.assertEqual(current_level({"conversational": True}), 1)

    def test_l3_with_agent_features(self):
        features = {
            "conversational": True,
            "reasoning": True,
            "action": True,
            "verification": True,
        }
        self.assertEqual(current_level(features), 3)

    def test_l5_requires_all_features(self):
        features = {
            "conversational": True,
            "reasoning": True,
            "action": True,
            "verification": True,
            "reflection": True,
            "coordination": True,
        }
        self.assertEqual(current_level(features), 5)

    def test_missing_feature_blocks_next_level(self):
        # Has L3 but missing reflection -> stays at L3.
        features = {
            "conversational": True,
            "reasoning": True,
            "action": True,
            "verification": True,
        }
        self.assertEqual(current_level(features), 3)
        self.assertEqual(gaps_to_next(features), ["reflection"])

    def test_gaps_empty_at_top(self):
        features = {
            "conversational": True,
            "reasoning": True,
            "action": True,
            "verification": True,
            "reflection": True,
            "coordination": True,
        }
        self.assertEqual(gaps_to_next(features), [])

    def test_gaps_at_l1(self):
        self.assertEqual(
            gaps_to_next({"conversational": True}),
            ["reasoning"],
        )

    def test_describe_returns_all_levels(self):
        result = describe()
        self.assertEqual(set(result.keys()), {1, 2, 3, 4, 5})
        for description in result.values():
            self.assertIsInstance(description, str)
            self.assertGreater(len(description), 0)

    def test_empty_features_yields_level_zero(self):
        self.assertEqual(current_level({}), 0)
        self.assertEqual(gaps_to_next({}), ["conversational"])
