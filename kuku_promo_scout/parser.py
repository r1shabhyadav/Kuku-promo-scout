import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

def timestamp_to_seconds(ts: str) -> float:
    """Converts MM:SS.SS or HH:MM:SS.SS into seconds (float)."""
    ts = ts.strip().strip("()")
    parts = ts.split(":")
    if len(parts) == 2:
        return float(parts[0]) * 60.0 + float(parts[1])
    elif len(parts) == 3:
        return float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
    return float(ts)

def seconds_to_timestamp(secs: float) -> str:
    """Converts seconds into MM:SS.SS format."""
    mins = int(secs // 60)
    remainder = secs - (mins * 60)
    return f"{mins:02d}:{remainder:05.2f}"

@dataclass
class Beat:
    beat_type: str  # CAMERA, ACTION, CHARACTER, SOUND FX, etc.
    character: Optional[str]
    delivery: Optional[str]  # e.g. Cold, Commanding, Defiant
    start_sec: float
    end_sec: float
    text: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)

@dataclass
class Scene:
    scene_num: str
    heading: str
    start_sec: float
    end_sec: float
    beats: List[Beat] = field(default_factory=list)

@dataclass
class Screenplay:
    episode_num: int
    logline: str
    continuity_notes: str
    scenes: List[Scene] = field(default_factory=list)
    raw_path: str = ""

    @property
    def total_duration(self) -> float:
        if not self.scenes:
            return 0.0
        return max(s.end_sec for s in self.scenes)

    @property
    def all_beats(self) -> List[Beat]:
        beats = []
        for s in self.scenes:
            beats.extend(s.beats)
        return beats

def parse_screenplay(file_path: str) -> Screenplay:
    """Parses a Kuku microdrama screenplay file into a structured Screenplay object."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Episode Number
    ep_match = re.search(r"EPISODE NUMBER:\s*Episode\s*(\d+)", content, re.IGNORECASE)
    ep_num = int(ep_match.group(1)) if ep_match else 0

    # Logline
    logline_match = re.search(r"EPISODE LOGLINE:\s*(.*?)(?=\n[A-Z\s]+:|\n---|\Z)", content, re.DOTALL)
    logline = logline_match.group(1).strip() if logline_match else ""

    # Continuity notes
    continuity_match = re.search(r"CONTINUITY NOTES:\s*(.*?)(?=\n---|\Z)", content, re.DOTALL)
    continuity = continuity_match.group(1).strip() if continuity_match else ""

    # Split into scenes
    scene_blocks = re.split(r"\n(?=SCENE\s+\d+)", content, flags=re.IGNORECASE)
    scenes = []

    for block in scene_blocks:
        scene_header = re.search(
            r"SCENE\s+(\d+)\s*\r?\n(?:Scene heading|SCENE HEADING):\s*([^\r\n]+)\r?\n(?:Scene start|SCENE START):\s*([0-9:.]+)\r?\n(?:Scene end|SCENE END):\s*([0-9:.]+)",
            block,
            re.IGNORECASE
        )
        if not scene_header:
            continue

        s_num = scene_header.group(1)
        s_heading = scene_header.group(2).strip()
        s_start = timestamp_to_seconds(scene_header.group(3))
        s_end = timestamp_to_seconds(scene_header.group(4))

        # Parse all beats within this scene block
        # Format: **TAG:**\nStart: (MM:SS.SS) | End: (MM:SS.SS)\nText
        beat_pattern = re.compile(
            r"\*\*([^*:]+):\*\*\s*\r?\nStart:\s*\(([0-9:.]+)\)\s*\|\s*End:\s*\(([0-9:.]+)\)\s*\r?\n(.*?)(?=\n\*\*|\n---|\Z)",
            re.DOTALL
        )

        beats = []
        for m in beat_pattern.finditer(block):
            raw_tag = m.group(1).strip()
            b_start = timestamp_to_seconds(m.group(2))
            b_end = timestamp_to_seconds(m.group(3))
            b_text = m.group(4).strip()

            # Determine beat type, character, and tone/delivery
            if raw_tag in ("CAMERA", "ACTION", "SOUND FX", "SFX"):
                b_type = raw_tag
                char_name = None
                delivery = None
            else:
                b_type = "CHARACTER"
                # Check for delivery in parenthesis e.g. "MATRIARCH (Cold, Commanding)"
                char_match = re.match(r"^([^()]+)(?:\((.*)\))?", raw_tag)
                if char_match:
                    char_name = char_match.group(1).strip()
                    delivery = char_match.group(2).strip() if char_match.group(2) else None
                else:
                    char_name = raw_tag
                    delivery = None

            beats.append(Beat(
                beat_type=b_type,
                character=char_name,
                delivery=delivery,
                start_sec=b_start,
                end_sec=b_end,
                text=b_text
            ))

        scenes.append(Scene(
            scene_num=s_num,
            heading=s_heading,
            start_sec=s_start,
            end_sec=s_end,
            beats=beats
        ))

    return Screenplay(
        episode_num=ep_num,
        logline=logline,
        continuity_notes=continuity,
        scenes=scenes,
        raw_path=file_path
    )
