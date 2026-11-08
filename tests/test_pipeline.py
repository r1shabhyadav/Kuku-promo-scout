import unittest
import os
import sys

# Ensure kuku_promo_scout is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from kuku_promo_scout.parser import (
    timestamp_to_seconds,
    seconds_to_timestamp,
    parse_screenplay,
    Beat,
    Scene,
    Screenplay
)
from kuku_promo_scout.promo_engine import find_promos_for_screenplay, PromoCandidate, Segment
from kuku_promo_scout.quality_checker import QualityAuditor
from kuku_promo_scout.ranker import rank_promos

class TestKukuPromoScout(unittest.TestCase):

    def test_timestamp_math(self):
        """Verifies bidirectional timestamp parsing and float conversion."""
        self.assertEqual(timestamp_to_seconds("00:00.00"), 0.0)
        self.assertEqual(timestamp_to_seconds("01:30.50"), 90.5)
        self.assertEqual(timestamp_to_seconds("02:18.00"), 138.0)
        self.assertEqual(seconds_to_timestamp(90.5), "01:30.50")
        self.assertEqual(seconds_to_timestamp(138.0), "02:18.00")

    def test_parser_basic_script(self):
        """Tests parsing a production episode from the input pack."""
        ep1_path = "kuku fm/scripts/I Married a Broken Soldier. He was a Duke/episode-001-Episode 1671703.txt"
        if not os.path.exists(ep1_path):
            self.skipTest("Screenplay file not found on disk")

        sp = parse_screenplay(ep1_path)
        self.assertEqual(sp.episode_num, 1)
        self.assertTrue(len(sp.scenes) >= 1)
        self.assertTrue(len(sp.all_beats) > 20)
        self.assertIn("Juliana", sp.logline)
        self.assertAlmostEqual(sp.total_duration, 138.0, delta=1.0)

    def test_case_insensitive_headers(self):
        """Ensures all-caps headers (e.g. Episode 6 'SCENE HEADING:') are parsed properly."""
        ep6_path = "kuku fm/scripts/I Married a Broken Soldier. He was a Duke/episode-006-Episode 1671708.txt"
        if not os.path.exists(ep6_path):
            self.skipTest("Episode 6 screenplay not found")

        sp = parse_screenplay(ep6_path)
        self.assertEqual(sp.episode_num, 6)
        self.assertTrue(len(sp.scenes) >= 1, "Failed to parse scenes with uppercase headers")
        self.assertTrue(len(sp.all_beats) > 10)

    def test_promo_duration_constraints(self):
        """Verifies that all discovered promos strictly satisfy 20.0s <= duration <= 60.0s."""
        ep3_path = "kuku fm/scripts/I Married a Broken Soldier. He was a Duke/episode-003-Episode 1671705.txt"
        if not os.path.exists(ep3_path):
            self.skipTest("Episode 3 screenplay not found")

        sp = parse_screenplay(ep3_path)
        candidates = find_promos_for_screenplay(sp, min_duration=20.0, max_duration=60.0, top_k=3)
        self.assertTrue(len(candidates) > 0)

        for c in candidates:
            self.assertGreaterEqual(c.total_duration, 20.0, "Promo duration too short")
            self.assertLessEqual(c.total_duration, 60.0, "Promo duration too long")

    def test_quality_auditor_flags(self):
        """Verifies the QualityAuditor detects pronoun ambiguity and low-kinetic scenes."""
        # Synthetic promo starting with an unanchored pronoun
        ambiguous_seg = Segment(
            episode_num=99,
            start_sec=15.0,
            end_sec=50.0,
            start_timestamp="00:15.00",
            end_timestamp="00:50.00",
            duration=35.0,
            beats=[
                Beat("CHARACTER", "GERALD", "Furious", 15.0, 18.0, '"He lied to us about the Duke!"'),
                Beat("CHARACTER", "JULIANA", "Defiant", 18.0, 22.0, '"You know nothing of him."')
            ]
        )
        cand = PromoCandidate(
            episode_num=99,
            segments=[ambiguous_seg],
            total_duration=35.0,
            hook_score=5.0,
            cliffhanger_score=5.0,
            coherence_score=5.0,
            viral_score=50.0,
            hook_description="Test hook",
            cliffhanger_description="Test cliffhanger",
            why_it_works="Test why"
        )

        audit = QualityAuditor.audit_promo(cand)
        self.assertEqual(audit["quality_status"], "NEEDS_REVIEW")
        has_pronoun_warning = any("Pronoun Ambiguity" in w for w in audit["warnings"])
        self.assertTrue(has_pronoun_warning, "Auditor should flag opening pronoun ambiguity")

    def test_ranking_funnel(self):
        """Verifies that early launch episodes receive cold traffic acquisition weight."""
        c1 = PromoCandidate(
            episode_num=2,
            segments=[],
            total_duration=30.0,
            hook_score=7.0,
            cliffhanger_score=7.0,
            coherence_score=7.0,
            viral_score=70.0,
            hook_description="",
            cliffhanger_description="",
            why_it_works=""
        )
        c2 = PromoCandidate(
            episode_num=45,
            segments=[],
            total_duration=30.0,
            hook_score=7.0,
            cliffhanger_score=7.0,
            coherence_score=7.0,
            viral_score=70.0,
            hook_description="",
            cliffhanger_description="",
            why_it_works=""
        )

        ranked = rank_promos([c1, c2])
        self.assertEqual(ranked[0]["episode"], 2, "Episode 2 should outrank Episode 45 due to cold launch funnel weight")
        self.assertIn("Tier 1", ranked[0]["funnel_stage"])

if __name__ == "__main__":
    unittest.main()

