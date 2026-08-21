import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.app.profile_localization import _cache, localize_profile
from backend.app.schemas import ProfileEvidenceSource, StructuredExperience, StructuredStudentProfile


class ProfileLocalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        _cache.clear()
        self.profile = StructuredStudentProfile(
            profile_id="profile-1",
            profile_name="Student",
            academic_interests=["Computer Science"],
            background=["Moved during middle school."],
            core_themes=["Adaptability"],
            experiences=[StructuredExperience(
                experience_number=1,
                experience_title="Programming Journey",
                category="Academic Interest",
                action="Practiced coding.",
                outcome="Built confidence.",
                reflection="Technology affects people.",
                traits=["curiosity"],
                status="documented",
                sources=[ProfileEvidenceSource(kind="original_profile", label="student.docx")],
            )],
        )

    def test_english_returns_original_without_model_call(self) -> None:
        with patch("backend.app.profile_localization.ChatOpenAI") as chat:
            result = localize_profile(self.profile, "en")
        self.assertEqual("Computer Science", result.academic_interests[0])
        chat.assert_not_called()

    def test_chinese_translation_preserves_structural_metadata_and_is_cached(self) -> None:
        translations = ["学生", "计算机科学", "初中时搬家。", "适应力", "编程历程", "学术兴趣", "", "", "练习编程。", "建立了信心。", "技术影响人。", "好奇心"]
        model = Mock()
        model.invoke.return_value = SimpleNamespace(content=json.dumps(translations, ensure_ascii=False))
        with patch.dict("os.environ", {"DASHSCOPE_API_KEY": "test"}), patch("backend.app.profile_localization.ChatOpenAI", return_value=model):
            first = localize_profile(self.profile, "zh")
            second = localize_profile(self.profile, "zh")
        self.assertEqual("计算机科学", first.academic_interests[0])
        self.assertEqual(1, first.experiences[0].experience_number)
        self.assertEqual("original_profile", first.experiences[0].sources[0].kind)
        self.assertEqual("计算机科学", second.academic_interests[0])
        model.invoke.assert_called_once()


if __name__ == "__main__":
    unittest.main()
