"""Static contract checks for proposed Company OS Studio UI/UX review. Stdlib only."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "knowledge/departments/game/skills/studio-ui-ux-review"


class StudioUiUxReviewContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        cls.notice = (SKILL_DIR / "UPSTREAM-NOTICE.md").read_text(encoding="utf-8")
        cls.readme = (SKILL_DIR / "README.md").read_text(encoding="utf-8")

    def test_frontmatter_is_read_only(self):
        header = self.text.split("---", 2)[1]
        self.assertIn("name: studio-ui-ux-review", header)
        self.assertIn("allowed-tools: Read, Glob, Grep", header)
        for unsafe in ("Bash", "Write", "Edit", "Agent", "AskUserQuestion"):
            self.assertNotIn(unsafe, header)

    def test_review_lenses_present(self):
        for value in ("Screen / UX flow", "Combat HUD", "Interaction-pattern"):
            self.assertIn(value, self.text)

    def test_missing_evidence_not_marked_approved(self):
        self.assertIn("**NOT ASSESSED**", self.text)
        self.assertIn("This is **not** an approval", self.text)
        self.assertIn("Do not invent missing standards", self.text)

    def test_verdict_precedence(self):
        indexes = [self.text.index("**" + value + "** —") for value in (
            "MAJOR REVISION NEEDED", "NEEDS REVISION", "NOT ASSESSED", "APPROVED")]
        self.assertEqual(indexes, sorted(indexes))

    def test_human_approval_and_assignment_gates_remain(self):
        self.assertIn("**Never** interpret this skill's `APPROVED`", self.text)
        self.assertIn("No automated delivery", self.text)
        self.assertIn("NOT assigned", self.readme)

    def test_output_is_evidence_based(self):
        for value in ("UX-REVIEW:", "Reviewed inputs:", "Blocking findings:",
                      "Not assessed:", "Execution performed: NONE"):
            self.assertIn(value, self.text)

    def test_license_attribution(self):
        self.assertIn("abc0de79d6ceb0b5d7aa693945849b3937afbe6a", self.text)
        self.assertIn("MIT License", self.notice)
        self.assertIn("copyright (c) 2026 Donchitos", self.notice)
        self.assertIn("THE SOFTWARE IS PROVIDED", self.notice)

    def test_no_unexpected_control_characters(self):
        for value in (self.text, self.notice, self.readme):
            self.assertFalse([x for x in value if ord(x) < 32 and x not in "\n\t\r"])


if __name__ == "__main__":
    unittest.main()