import argparse
import sys
import os
import json

# Ensure kuku_promo_scout is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kuku_promo_scout.parser import parse_screenplay, seconds_to_timestamp
from kuku_promo_scout.promo_engine import find_promos_for_screenplay
from kuku_promo_scout.quality_checker import QualityAuditor
from kuku_promo_scout.llm_evaluator import LLMEvaluator

def main():
    parser = argparse.ArgumentParser(description="Kuku FM AI Microdrama Promo Scout CLI")
    parser.add_argument("--input", "-i", type=str, help="Path to screenplay .txt file")
    parser.add_argument("--episode", "-e", type=int, default=1, help="Episode number (1-50) from the input pack")
    parser.add_argument("--min", type=float, default=20.0, help="Minimum promo duration (seconds)")
    parser.add_argument("--max", type=float, default=60.0, help="Maximum promo duration (seconds)")
    parser.add_argument("--offline", action="store_true", help="Use 100% offline heuristic (skip external API)")
    args = parser.parse_args()

    if args.input:
        fpath = args.input
    else:
        # Search by episode number
        folder = "kuku fm/scripts/I Married a Broken Soldier. He was a Duke"
        candidates = [f for f in os.listdir(folder) if f"episode-{args.episode:03d}" in f]
        if not candidates:
            print(f"Error: Episode {args.episode} not found in {folder}")
            return
        fpath = os.path.join(folder, candidates[0])

    print(f"\n=======================================================")
    print(f"  🎬 KUKU FM — PROMO SCOUT AI ENGINE")
    print(f"  Processing: {os.path.basename(fpath)}")
    print(f"=======================================================\n")

    sp = parse_screenplay(fpath)
    print(f"📖 Episode: {sp.episode_num}")
    print(f"⏱ Total Duration: {seconds_to_timestamp(sp.total_duration)}")
    print(f"📝 Logline: {sp.logline}\n")

    print(f"🔍 Searching promo windows between {args.min}s and {args.max}s...")
    candidates = find_promos_for_screenplay(sp, min_duration=args.min, max_duration=args.max, top_k=3)

    if not candidates:
        print("[-] No candidate found within constraints.")
        return

    evaluator = None if args.offline else LLMEvaluator()

    for idx, c in enumerate(candidates, 1):
        if evaluator:
            c = evaluator.refine_candidate(c, sp.logline)
        audit = QualityAuditor.audit_promo(c)

        print(f"-------------------------------------------------------")
        print(f" PROMO CUT #{idx} | Viral Score: {c.viral_score:.1f}/100 | Total Duration: {c.total_duration:.1f}s")
        print(f"-------------------------------------------------------")
        for s_idx, s in enumerate(c.segments, 1):
            print(f"  Segment {s_idx}: {s.start_timestamp} ➔ {s.end_timestamp} ({s.duration:.1f}s)")
        print(f"\n  ⚡ THE HOOK (First 3s):")
        print(f"     {c.hook_description}")
        print(f"\n  🛑 THE CLIFFHANGER CUT:")
        print(f"     {c.cliffhanger_description}")
        print(f"\n  🎯 WHY IT WORKS (Social Scroller Psychology):")
        print(f"     \"{c.why_it_works}\"")
        print(f"\n  🛡 QUALITY AUDIT:")
        print(f"     Status: {audit['quality_status']} (Score: {audit['quality_score']}/100)")
        if audit['warnings']:
            for w in audit['warnings']:
                print(f"     ⚠️  {w}")
        print()

if __name__ == "__main__":
    main()

