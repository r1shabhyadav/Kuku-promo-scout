import re
from typing import List, Dict, Any, Tuple
from .parser import Screenplay, Beat, seconds_to_timestamp

# Microdrama viral lexicons
HOOK_ACTION_KEYWORDS = {
    "slap": 4.5, "strikes": 4.0, "grab": 3.5, "grabs": 3.5, "knelt": 3.8, "kneel": 3.8, "kneels": 3.8,
    "drops to one knee": 4.5, "tear": 3.0, "clenches": 3.2, "blood": 4.0, "bloody": 4.0, "sword": 4.0,
    "blade": 4.0, "dagger": 4.0, "seize": 3.5, "seized": 3.5, "guards": 3.0, "poison": 4.2,
    "shoves": 3.8, "chokes": 4.2, "screams": 3.8, "gasps": 3.5, "defiance": 3.2, "stranger": 3.2
}

HOOK_DIALOGUE_KEYWORDS = {
    "cannot marry": 4.5, "stop": 3.5, "liar": 4.0, "turn around": 3.8, "leave": 3.2,
    "how dare": 4.0, "beg": 3.8, "kill": 4.2, "die": 4.0, "bastard": 4.5, "whore": 4.5,
    "servant": 3.5, "plain": 3.5, "worthless": 4.0, "unworthy": 3.8, "disgrace": 4.0,
    "divorce": 4.5, "marry me": 4.5, "who are you": 4.0, "never": 3.0, "betrayal": 3.8,
    "arrest": 4.0, "poison": 4.2, "dead": 4.0, "mine": 3.2, "touch her": 4.5
}

HOOK_DELIVERIES = {
    "cold": 3.5, "commanding": 3.5, "cruel": 4.0, "furious": 4.0, "derisive": 3.8,
    "mocking": 3.8, "defiant": 3.5, "desperate": 3.2, "venomous": 4.2, "lethal": 4.2,
    "chilling": 4.0, "authoritative": 3.5, "steely": 3.8
}

CLIFFHANGER_KEYWORDS = {
    "cliffhanger": 4.5, "cut to black": 4.0, "string swell": 3.8, "drone swells": 4.0,
    "unresolved": 4.0, "freezes": 3.5, "gasps": 3.5, "silence": 3.2, "hardens": 3.5,
    "stares": 3.0, "ominous": 3.8, "defiance": 3.5, "shock": 3.5, "breathless": 3.2
}

CLIFFHANGER_DIALOGUE_PATTERNS = [
    r"\?$",  # ends with a burning question
    r"\.\.\.$",  # trailing ellipsis / interrupted
    r"(who (are|is)|what did you|why would you|unless|or else|tell me)",
    r"(marry me|kill you|regret this|pay for this)"
]

def score_hook(beats_in_first_3s: List[Beat]) -> Tuple[float, str]:
    """Scores how compelling the first 3 seconds are as a scrolling hook."""
    score = 1.0
    reasons = []
    quote_highlight = None
    action_highlight = None

    for b in beats_in_first_3s:
        text_lower = b.text.lower()

        # Capture dialogue quote if present
        if b.beat_type == "CHARACTER" and not quote_highlight:
            cleaned_text = b.text.strip(' "\'')
            delivery_str = f" ({b.delivery})" if b.delivery else ""
            quote_highlight = f"{b.character}{delivery_str}: \"{cleaned_text[:50]}\""

        # Action/Visual hook
        for kw, weight in HOOK_ACTION_KEYWORDS.items():
            if kw in text_lower:
                score += weight
                action_highlight = f"Visual '{kw}': {b.text[:60]}"
                break

        # Dialogue text hook
        for kw, weight in HOOK_DIALOGUE_KEYWORDS.items():
            if kw in text_lower:
                score += weight
                reasons.append(f"Shock line '{kw}'")
                break

        # Character delivery/emotion tone
        if b.delivery:
            deliv_lower = b.delivery.lower()
            for kw, weight in HOOK_DELIVERIES.items():
                if kw in deliv_lower:
                    score += weight
                    reasons.append(f"{kw.capitalize()} delivery")
                    break

        # Close-up or dynamic camera
        if b.beat_type == "CAMERA":
            if "close-up" in text_lower or "tight" in text_lower or "push" in text_lower:
                score += 1.5
                reasons.append("Tight close-up zoom")

    # Deduplicate reasons preserving order
    unique_reasons = []
    for r in reasons:
        if r not in unique_reasons:
            unique_reasons.append(r)

    # Build rich human-readable description
    if quote_highlight and action_highlight:
        hook_desc = f"{action_highlight}; {quote_highlight}"
    elif quote_highlight:
        hook_desc = f"Opens with {quote_highlight}"
    elif action_highlight:
        hook_desc = f"Opens with {action_highlight}"
    elif unique_reasons:
        hook_desc = f"Dynamic scene opening: {', '.join(unique_reasons[:2])}"
    else:
        hook_desc = "Immediate in-media-res scene entry"

    return min(10.0, score), hook_desc

def score_cliffhanger(last_beats: List[Beat]) -> Tuple[float, str]:
    """Scores whether the final beats cut on an unresolved, urgent cliffhanger."""
    score = 1.0
    reasons = []
    ending_cue = None

    for b in last_beats:
        text_lower = b.text.lower()

        # Check SFX / Sound cues
        if b.beat_type in ("SOUND FX", "SFX") or "cliffhanger" in text_lower or "swells" in text_lower:
            score += 3.5
            ending_cue = "Ominous audio swell cuts at maximum tension"

        for kw, weight in CLIFFHANGER_KEYWORDS.items():
            if kw in text_lower:
                score += weight
                reasons.append(f"Climactic cue '{kw}'")
                break

        # Dialogue cliffhanger patterns
        if b.beat_type == "CHARACTER":
            for pat in CLIFFHANGER_DIALOGUE_PATTERNS:
                if re.search(pat, text_lower):
                    score += 3.0
                    cleaned = b.text.strip(' "\'')
                    ending_cue = f"Cuts on unresolved line: {b.character}: \"{cleaned[:45]}...\""
                    break

    # If it ends right at episode cut-to-black
    if any("cut to black" in b.text.lower() for b in last_beats):
        score += 2.5
        reasons.append("Official episode cut-to-black")

    # Deduplicate reasons preserving order
    unique_reasons = []
    for r in reasons:
        if r not in unique_reasons:
            unique_reasons.append(r)

    if ending_cue:
        desc = ending_cue
    elif unique_reasons:
        desc = f"Dramatic tension cutoff: {', '.join(unique_reasons[:2])}"
    else:
        desc = "Abrupt narrative cut point before resolution"

    return min(10.0, score), desc

def evaluate_standalone_coherence(beats: List[Beat]) -> float:
    """Evaluates if the segment is self-contained and makes sense without backstory."""
    dialogue_beats = [b for b in beats if b.beat_type == "CHARACTER"]
    if not dialogue_beats:
        return 4.0  # pure silent montage has lower coherence
    
    # Needs dialogue exchange or a clear conflict
    speakers = set(b.character for b in dialogue_beats if b.character)
    score = 6.0
    if len(speakers) >= 2:
        score += 2.5  # direct confrontation
    elif len(speakers) == 1 and len(dialogue_beats) >= 2:
        score += 1.5  # powerful monologue / ultimatum

    # Check length of dialogue
    total_words = sum(len(b.text.split()) for b in dialogue_beats)
    if total_words < 10:
        score -= 2.0  # too sparse
    elif total_words > 80:
        score -= 1.0  # too verbose for a fast 40s clip

    return min(10.0, max(2.0, score))
