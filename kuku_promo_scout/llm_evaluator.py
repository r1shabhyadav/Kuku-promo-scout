import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from .promo_engine import PromoCandidate

GROQ_MODEL = "qwen/qwen3.8-27b"

class LLMEvaluator:
    def __init__(self, api_key: Optional[str] = None, provider: str = "groq", model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.provider = provider
        self.model = model or (GROQ_MODEL if provider == "groq" else "gemini-1.5-flash")

    def refine_candidate(self, candidate: PromoCandidate, episode_logline: str) -> PromoCandidate:
        """
        Uses LLM (or falls back gracefully to smart heuristic) to generate high-grade
        editorial annotations matching Kuku FM's promo criteria.
        """
        if not self.api_key:
            return candidate

        # Prepare excerpt of the candidate beats
        excerpt_lines = []
        for seg in candidate.segments:
            excerpt_lines.append(f"--- Segment ({seg.start_timestamp} -> {seg.end_timestamp}) ---")
            for b in seg.beats:
                if b.beat_type == "CHARACTER":
                    excerpt_lines.append(f"{b.character} ({b.delivery or 'Spoken'}): {b.text}")
                elif b.beat_type in ("ACTION", "SOUND FX"):
                    excerpt_lines.append(f"[{b.beat_type}] {b.text}")

        script_text = "\n".join(excerpt_lines[:25])

        prompt = f"""You are an elite short-form drama trailer editor for ReelShort, DramaBox, and Kuku FM.
Analyze this proposed 20-60s microdrama promo cut from Episode {candidate.episode_num}.

Episode Logline: {episode_logline}
Duration: {candidate.total_duration:.1f}s

Script Excerpt:
{script_text}

Task:
Return a valid JSON object with EXACTLY these four keys:
{{
  "hook": "Specific action/line in the first 3 seconds that stops a scrolling viewer",
  "cliffhanger": "The unresolved moment/reaction/ultimatum right at the cut point that forces the viewer to watch the full episode",
  "why_it_works": "Exactly one punchy sentence on why this works for TikTok/Instagram/YouTube scrollers",
  "viral_boost": <integer from -5 to +5 reflecting true social viral potential>
}}
Return ONLY the raw JSON object, no markdown ticks, no preamble."""

        try:
            res = self._call_llm(prompt)
            if res:
                cleaned = res.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                data = json.loads(cleaned.strip())

                candidate.hook_description = data.get("hook", candidate.hook_description)
                candidate.cliffhanger_description = data.get("cliffhanger", candidate.cliffhanger_description)
                candidate.why_it_works = data.get("why_it_works", candidate.why_it_works)
                boost = float(data.get("viral_boost", 0))
                candidate.viral_score = max(1.0, min(100.0, candidate.viral_score + boost))
        except Exception as e:
            # Silently use heuristic scores if network/API limits block
            pass

        return candidate

    def _call_llm(self, prompt: str) -> Optional[str]:
        if self.provider == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "KukuPromoScout/1.0"
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 300
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        return None

