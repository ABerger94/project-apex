import unittest

from apex.objectives import AGI_LEVELS, TARGET_AGI_LEVEL, objective_directive, target_level


class ObjectiveTests(unittest.TestCase):
    def test_hardcoded_levels_are_complete_and_ordered(self):
        self.assertEqual([level.level for level in AGI_LEVELS], [1, 2, 3, 4, 5])
        self.assertEqual(AGI_LEVELS[0].name, "Conversational AI/Chatbots")
        self.assertEqual(AGI_LEVELS[-1].name, "Organizers")

    def test_target_is_level_5_organizer(self):
        self.assertEqual(TARGET_AGI_LEVEL, 5)
        self.assertEqual(target_level().name, "Organizers")
        self.assertIn("entire organizations", target_level().description)

    def test_directive_names_all_levels(self):
        directive = objective_directive()
        for level in AGI_LEVELS:
            self.assertIn(f"L{level.level} {level.name}", directive)
        self.assertIn("Reach and act as a Level 5 AGI Organizer", directive)


if __name__ == "__main__":
    unittest.main()

