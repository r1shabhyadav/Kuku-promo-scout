import os
import glob
import json
import csv
import time
from typing import List, Dict, Any
from .parser import parse_screenplay, seconds_to_timestamp
from .promo_engine import find_promos_for_screenplay, PromoCandidate
from .llm_evaluator import LLMEvaluator
from .quality_checker import QualityAuditor
from .ranker import rank_promos

def run_batch_pipeline(
    input_dir: str = "kuku fm/scripts/I Married a Broken Soldier. He was a Duke",
    output_dir: str = "kuku fm/raw_outputs",
    use_llm: bool = True,
    enrich_all: bool = True
) -> Dict[str, Any]:
    """
    Executes end-to-end promo discovery across all screenplays.
    Outputs comprehensive JSON, CSV, and Markdown logs.
    """
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "episodes"), exist_ok=True)

    files = sorted(glob.glob(os.path.join(input_dir, "*.txt")))
    print(f"[+] Found {len(files)} screenplay files in {input_dir}")

    evaluator = LLMEvaluator() if use_llm else None

    all_best_candidates: List[PromoCandidate] = []
    episode_results: List[Dict[str, Any]] = []

    for idx, fpath in enumerate(files):
        sp = parse_screenplay(fpath)
        candidates = find_promos_for_screenplay(sp, min_duration=20.0, max_duration=60.0, top_k=2)

        if not candidates:
            print(f"[-] No candidate found for Episode {sp.episode_num}")
            continue

        best_cand = candidates[0]

        # Audit quality
        audit = QualityAuditor.audit_promo(best_cand)

        # Refine candidate with LLM if enabled
        if evaluator:
            if enrich_all or idx < 5:
                try:
                    best_cand = evaluator.refine_candidate(best_cand, sp.logline)
                except Exception as e:
                    print(f"[!] LLM fallback on Ep {sp.episode_num}: {e}")

        all_best_candidates.append(best_cand)

        ep_data = best_cand.to_dict()
        ep_data["logline"] = sp.logline
        ep_data["total_episode_duration"] = seconds_to_timestamp(sp.total_duration)
        ep_data["quality_audit"] = audit
        episode_results.append(ep_data)

        # Write individual episode JSON
        ep_file = os.path.join(output_dir, "episodes", f"episode_{sp.episode_num:03d}_promo.json")
        with open(ep_file, "w", encoding="utf-8") as f:
            json.dump(ep_data, f, indent=2)

        if (idx + 1) % 10 == 0:
            print(f"  Processed {idx + 1}/{len(files)} episodes...")

    # Global Ranking
    ranked_promos = rank_promos(all_best_candidates)

    # Attach quality audit to ranked promos
    audit_lookup = {e["episode"]: e["quality_audit"] for e in episode_results}
    logline_lookup = {e["episode"]: e["logline"] for e in episode_results}
    for item in ranked_promos:
        item["logline"] = logline_lookup.get(item["episode"], "")
        item["quality_audit"] = audit_lookup.get(item["episode"], {})

    # Save master JSON
    master_json_path = os.path.join(output_dir, "promos_all_50_episodes.json")
    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(ranked_promos, f, indent=2)

    # Save CSV
    csv_path = os.path.join(output_dir, "promos_ranked.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Global Rank", "Episode", "Funnel Stage", "Total Duration (s)",
            "Segment Timestamps", "Hook (First 3s)", "Cliffhanger Cut",
            "Why It Works", "Global Rank Score", "Quality Status"
        ])
        for p in ranked_promos:
            seg_str = " + ".join([f"{s['start']}-{s['end']}" for s in p["segments"]])
            writer.writerow([
                p["rank"],
                f"Episode {p['episode']}",
                p["funnel_stage"],
                p["total_duration_sec"],
                seg_str,
                p["hook"],
                p["cliffhanger"],
                p["why_it_works"],
                p["global_rank_score"],
                p["quality_audit"].get("quality_status", "PASSED")
            ])

    # Save Markdown Summary
    md_path = os.path.join(output_dir, "promos_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Kuku FM — AI Microdrama Promo Discovery: 50 Episode Master Index\n\n")
        f.write(f"**Total Screenplays Processed:** {len(files)}  \n")
        f.write(f"**Promos Generated:** {len(ranked_promos)}  \n")
        f.write(f"**Execution Runtime:** {time.time() - start_time:.2f} seconds  \n\n")
        f.write("## Top 10 Recommended Promos to Post First\n\n")
        f.write("| Rank | Episode | Timestamps | Duration | Hook (First 3s) | Cliffhanger Cut | Why It Works |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for p in ranked_promos[:10]:
            seg_str = " + ".join([f"`{s['start']} → {s['end']}`" for s in p["segments"]])
            f.write(f"| **#{p['rank']}** | Ep {p['episode']} | {seg_str} | {p['total_duration_sec']}s | {p['hook']} | {p['cliffhanger']} | {p['why_it_works']} |\n")

    print(f"[✓] Batch pipeline complete in {time.time() - start_time:.2f}s!")
    print(f"[✓] Generated files in: {output_dir}")
    return {"total": len(ranked_promos), "top_promo": ranked_promos[0]}
