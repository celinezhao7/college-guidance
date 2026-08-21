import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.profile_additions import (
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


if __name__ == "__main__":
    unittest.main()
