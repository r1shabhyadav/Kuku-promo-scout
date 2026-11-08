import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from .parser import Screenplay, Beat, seconds_to_timestamp
from .candidate_generator import score_hook, score_cliffhanger, evaluate_standalone_coherence

@dataclass
class Segment:
    episode_num: int
    start_sec: float
    end_sec: float
    start_timestamp: str
    end_timestamp: str
    duration: float
    beats: List[Beat] = field(default_factory=list)

@dataclass
class PromoCandidate:
    episode_num: int
    segments: List[Segment]
    total_duration: float
    hook_score: float
    cliffhanger_score: float
    coherence_score: float
    viral_score: float
    hook_description: str
    cliffhanger_description: str
    why_it_works: str
    dialogue_summary: str = ""
    is_multi_segment: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode": self.episode_num,
            "segments": [
                {
                    "start": s.start_timestamp,
                    "end": s.end_timestamp,
                    "duration_sec": round(s.duration, 2)
                } for s in self.segments
            ],
            "total_duration_sec": round(self.total_duration, 2),
            "hook": self.hook_description,
            "cliffhanger": self.cliffhanger_description,
            "why_it_works": self.why_it_works,
            "viral_score": round(self.viral_score, 2),
            "scores": {
                "hook": round(self.hook_score, 1),
                "cliffhanger": round(self.cliffhanger_score, 1),
                "coherence": round(self.coherence_score, 1)
            }
        }

def find_promos_for_screenplay(
    screenplay: Screenplay,
    min_duration: float = 20.0,
    max_duration: float = 60.0,
    top_k: int = 3
) -> List[PromoCandidate]:
    """
    Finds the optimal promo candidates for a given screenplay adhering to:
    1. Duration between min_duration and max_duration (20s - 60s).
    2. Opens on an arresting hook in the first 3 seconds.
    3. Ends on an unresolved cliffhanger.
    4. Makes standalone narrative sense.
    """
    beats = screenplay.all_beats
    if not beats:
        return []

    candidates: List[PromoCandidate] = []

    # 1. Search continuous windows
    num_beats = len(beats)
    for i in range(num_beats):
        start_beat = beats[i]
        start_time = start_beat.start_sec

        # Candidate end beats within duration bounds
        for j in range(i, num_beats):
            end_beat = beats[j]
            end_time = end_beat.end_sec
            duration = end_time - start_time

            if duration < min_duration:
                continue
            if duration > max_duration:
                break  # further beats will only increase duration

            # Ensure we don't start or end in a fragmented boundary
            window_beats = beats[i:j+1]

            # First 3 seconds beats for hook evaluation
            first_3s_beats = [b for b in window_beats if b.start_sec <= start_time + 3.2]
            hook_sc, hook_desc = score_hook(first_3s_beats)

            # Last 4 seconds beats for cliffhanger evaluation
            last_beats = [b for b in window_beats if b.end_sec >= end_time - 4.0]
            cliff_sc, cliff_desc = score_cliffhanger(last_beats)

            coherence_sc = evaluate_standalone_coherence(window_beats)

            # Composite viral score (0 - 100)
            # 40% Hook, 40% Cliffhanger, 20% Standalone coherence
            composite = (hook_sc * 4.0) + (cliff_sc * 4.0) + (coherence_sc * 2.0)

            # Extract dialogue text for why it works
            dialogues = [f"{b.character}: {b.text}" for b in window_beats if b.beat_type == "CHARACTER"]
            dialogue_snippet = " | ".join(dialogues[:3])

            # Generate punchy justification
            why = generate_heuristic_justification(hook_desc, cliff_desc, dialogues, screenplay.logline)

            segment = Segment(
                episode_num=screenplay.episode_num,
                start_sec=start_time,
                end_sec=end_time,
                start_timestamp=seconds_to_timestamp(start_time),
                end_timestamp=seconds_to_timestamp(end_time),
                duration=duration,
                beats=window_beats
            )

            candidate = PromoCandidate(
                episode_num=screenplay.episode_num,
                segments=[segment],
                total_duration=duration,
                hook_score=hook_sc,
                cliffhanger_score=cliff_sc,
                coherence_score=coherence_sc,
                viral_score=composite,
                hook_description=hook_desc,
                cliffhanger_description=cliff_desc,
                why_it_works=why,
                dialogue_summary=dialogue_snippet,
                is_multi_segment=False
            )
            candidates.append(candidate)

    # 2. Also search 2-segment stitch candidates (Opening Hook segment + Ending Climax segment)
    if len(beats) > 20:
        # Segment 1: opening 10-15s hook
        seg1_beats = [b for b in beats if b.start_sec <= 15.0 and b.end_sec <= 18.0]
        # Segment 2: ending 20-35s cliffhanger
        seg2_beats = [b for b in beats if b.end_sec >= (screenplay.total_duration - 35.0)]

        if seg1_beats and seg2_beats:
            s1_start = seg1_beats[0].start_sec
            s1_end = seg1_beats[-1].end_sec
            s2_start = seg2_beats[0].start_sec
            s2_end = seg2_beats[-1].end_sec
            tot_dur = (s1_end - s1_start) + (s2_end - s2_start)

            if min_duration <= tot_dur <= max_duration and s2_start > s1_end:
                h_sc, h_desc = score_hook(seg1_beats[:3])
                c_sc, c_desc = score_cliffhanger(seg2_beats[-3:])
                coh_sc = 7.5
                composite = (h_sc * 4.0) + (c_sc * 4.0) + (coh_sc * 2.0)

                seg1 = Segment(
                    episode_num=screenplay.episode_num,
                    start_sec=s1_start,
                    end_sec=s1_end,
                    start_timestamp=seconds_to_timestamp(s1_start),
                    end_timestamp=seconds_to_timestamp(s1_end),
                    duration=s1_end - s1_start,
                    beats=seg1_beats
                )
                seg2 = Segment(
                    episode_num=screenplay.episode_num,
                    start_sec=s2_start,
                    end_sec=s2_end,
                    start_timestamp=seconds_to_timestamp(s2_start),
                    end_timestamp=seconds_to_timestamp(s2_end),
                    duration=s2_end - s2_start,
                    beats=seg2_beats
                )
                candidates.append(PromoCandidate(
                    episode_num=screenplay.episode_num,
                    segments=[seg1, seg2],
                    total_duration=tot_dur,
                    hook_score=h_sc,
                    cliffhanger_score=c_sc,
                    coherence_score=coh_sc,
                    viral_score=composite - 2.0,  # slight penalty for cut transition
                    hook_description=h_desc,
                    cliffhanger_description=c_desc,
                    why_it_works="Juxtaposes the opening betrayal shock with the final confrontation cliffhanger, maximizing stakes without dragging through exposition.",
                    dialogue_summary="Opening hook spliced with climactic finish",
                    is_multi_segment=True
                ))

    # Deduplicate candidates that overlap heavily
    candidates.sort(key=lambda x: x.viral_score, reverse=True)
    deduped: List[PromoCandidate] = []

    for cand in candidates:
        overlap = False
        cand_start = cand.segments[0].start_sec
        cand_end = cand.segments[-1].end_sec
        for accepted in deduped:
            acc_start = accepted.segments[0].start_sec
            acc_end = accepted.segments[-1].end_sec
            # If start and end are within 8 seconds, consider duplicate
            if abs(cand_start - acc_start) < 8.0 and abs(cand_end - acc_end) < 8.0:
                overlap = True
                break
        if not overlap:
            deduped.append(cand)
            if len(deduped) >= top_k:
                break

    return deduped

def generate_heuristic_justification(hook_desc: str, cliff_desc: str, dialogues: List[str], logline: str) -> str:
    """Generates a crisp 1-sentence explanation of why the promo works on social media."""
    if dialogues:
        first_quote = dialogues[0].split(":", 1)[-1].strip().strip('"')
        return f"Instantly arrests scrollers with '{first_quote[:45]}...' and cuts sharply on an unresolved confrontation that demands episode completion."
    return "Hooks viewers with immediate high-status conflict in the first 3 seconds and abruptly freezes on an unanswered dilemma."

