import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.profile_additions import (
    addition_conflicts,
    configure_profile_addition_repository,
    format_additions,
    delete_addition,
    list_addition_records,
    load_additions,
    preview_addition,
    save_addition,
    update_addition,
)
from backend.app.schemas import ProfileAddition


class ProfileAdditionTests(unittest.TestCase):
    def tearDown(self) -> None:
        configure_profile_addition_repository(None)

    def test_preview_preserves_experience_and_falls_back_to_user_words(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = preview_addition(
                "Regarding Experience 2: Initial Interest in Public Health, what did you do?",
                "I interviewed a local nurse and compared her answers with my reading.",
            )
        self.assertEqual(result.experience_number, 2)
        self.assertEqual(result.experience_title, "Initial Interest in Public Health")
        self.assertIn("interviewed a local nurse", result.action)

    def test_confirmed_additions_are_saved_deduplicated_and_formatted(self) -> None:
        addition = ProfileAddition(
            experience_number=2,
            experience_title="Initial Interest in Public Health",
            action="Interviewed a nurse.",
            outcome="Compared perspectives.",
            reflection="Learned to test assumptions.",
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "backend.app.profile_additions.ADDITIONS_DIR", Path(directory)
        ):
            save_addition("profile-id", addition)
            save_addition("profile-id", addition)
            self.assertEqual(len(load_additions("profile-id")), 1)
            record = list_addition_records("profile-id")[0]
            updated = update_addition(
                "profile-id",
                record.id,
                addition.model_copy(update={"reflection": "Updated reflection."}),
            )
            self.assertEqual(updated.reflection, "Updated reflection.")
            context = format_additions("profile-id")
            self.assertTrue(delete_addition("profile-id", record.id))
            self.assertEqual(load_additions("profile-id"), [])
        self.assertIn("Experience 2: Initial Interest in Public Health", context)
        self.assertIn("Interviewed a nurse", context)
        self.assertIn("User-confirmed", context)

    def test_near_duplicate_punctuation_and_case_is_not_saved_twice(self) -> None:
        first = ProfileAddition(
            experience_number=3, experience_title="Community Project",
            action="Organized five weekly meetings.", outcome="Reached 20 students!",
            reflection="I learned to listen.",
        )
        duplicate = first.model_copy(update={
            "action": "organized FIVE weekly meetings",
            "outcome": "Reached 20 students",
            "reflection": "I learned to listen!",
        })
        with tempfile.TemporaryDirectory() as directory, patch(
            "backend.app.profile_additions.ADDITIONS_DIR", Path(directory)
        ):
            original = save_addition("profile-id", first)
            repeated = save_addition("profile-id", duplicate)
            self.assertEqual(original.id, repeated.id)
            self.assertEqual(1, len(load_additions("profile-id")))

    def test_conflicting_number_or_negation_requires_confirmation_signal(self) -> None:
        original = ProfileAddition(
            experience_number=4, experience_title="Tutoring",
            action="Tutored 12 students.", outcome="I won an award.", reflection="",
        )
        conflicting = original.model_copy(update={
            "action": "Tutored 30 students.",
            "outcome": "I did not win an award.",
        })
        unrelated = original.model_copy(update={"action": "Designed new lesson plans.", "outcome": ""})
        with tempfile.TemporaryDirectory() as directory, patch(
            "backend.app.profile_additions.ADDITIONS_DIR", Path(directory)
        ):
            save_addition("profile-id", original)
            self.assertEqual(["action", "outcome"], addition_conflicts("profile-id", conflicting))
            self.assertEqual([], addition_conflicts("profile-id", unrelated))

    def test_repository_boundary_preserves_profile_isolation(self) -> None:
        class MemoryRepository:
            def __init__(self): self.values = {}
            def load(self, profile_id): return [dict(item) for item in self.values.get(profile_id, [])]
            def write(self, profile_id, records): self.values[profile_id] = [dict(item) for item in records]

        repository = MemoryRepository()
        configure_profile_addition_repository(repository)
        addition = ProfileAddition(experience_title="Robotics", action="Built a prototype.")
        save_addition("student-a", addition)
        self.assertEqual(1, len(load_additions("student-a")))
        self.assertEqual([], load_additions("student-b"))


if __name__ == "__main__":
    unittest.main()
