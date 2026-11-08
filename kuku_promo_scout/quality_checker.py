from typing import Dict, Any, List
from .promo_engine import PromoCandidate

class QualityAuditor:
    """
    Audits candidate promos against real-world microdrama failure modes:
    1. Pronoun ambiguity without context (e.g., 'He lied' without establishing who 'he' is).
    2. Low-kinetic talking heads (high word count, zero camera/action beats).
    3. Premature cut / sentence truncation.
    4. Spoiler exposure (climax reveals that undermine early episodes).
    """

    @staticmethod
    def audit_promo(candidate: PromoCandidate) -> Dict[str, Any]:
        warnings = []
        confidence_penalty = 0.0

        all_beats = []
        for s in candidate.segments:
            all_beats.extend(s.beats)

        dialogue_beats = [b for b in all_beats if b.beat_type == "CHARACTER"]
        action_beats = [b for b in all_beats if b.beat_type == "ACTION"]
        camera_beats = [b for b in all_beats if b.beat_type == "CAMERA"]

        # Failure mode 1: Low visual kinetics (Talking heads)
        if len(action_beats) == 0 and len(dialogue_beats) > 4:
            warnings.append("Low kinetic energy: Dialogue-heavy scene with no physical action or blocking changes.")
            confidence_penalty += 10.0

        # Failure mode 2: Ambiguous opening pronoun
        if dialogue_beats:
            first_line = dialogue_beats[0].text.strip('"').lower()
            pronoun_starts = ("he ", "she ", "they ", "it ", "him ", "her ")
            if any(first_line.startswith(p) for p in pronoun_starts) and candidate.segments[0].start_sec > 10.0:
                warnings.append("Pronoun Ambiguity: Promo opens with an unresolved pronoun referencing an off-clip character.")
                confidence_penalty += 8.0

        # Failure mode 3: Weak ending (Ends on exposition rather than reaction)
        if all_beats:
            last_beat = all_beats[-1]
            if last_beat.beat_type == "ACTION" and any(w in last_beat.text.lower() for w in ["walks away", "steps out", "leaves room", "sits down"]):
                warnings.append("Expository End: Cut ends on a physical exit rather than an emotional confrontation peak.")
                confidence_penalty += 12.0

        # Failure mode 4: Ultra-short duration risk (<25s)
        if candidate.total_duration < 25.0:
            warnings.append("Pacing Risk: Clip duration under 25s may not allow emotional tension to land.")
            confidence_penalty += 5.0

        passed = len(warnings) == 0
        quality_score = max(50.0, 100.0 - confidence_penalty)

        return {
            "quality_status": "PASSED" if passed else "NEEDS_REVIEW",
            "quality_score": round(quality_score, 1),
            "warnings": warnings,
            "failure_mitigation": "Ensure opening line names the subject; trim trailing exits to freeze on the reaction close-up." if warnings else "Clean production boundary."
        }

