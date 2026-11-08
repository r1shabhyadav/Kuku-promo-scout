from typing import List, Dict, Any
from .promo_engine import PromoCandidate

def rank_promos(candidates: List[PromoCandidate]) -> List[Dict[str, Any]]:
    """
    Ranks promos globally across all episodes using Kuku's marketing release strategy:
    1. Cold Conversion Potential (Episodes 1-5 foundational betrayal/revenge hooks get priority for ad spend).
    2. Hook Intensity (3-second thumb-stop velocity).
    3. Cliffhanger Severity (Unresolved urgency).
    4. Quality Audit Score.
    """
    ranked_list = []

    for cand in candidates:
        ep = cand.episode_num
        
        # Strategic Ad Spend Funnel Weight:
        # Early episodes (1-5) get priority for launch ads because they require zero backstory.
        if 1 <= ep <= 5:
            funnel_weight = 15.0
            funnel_stage = "Tier 1: Cold Traffic Acquisition (Launch Day Ads)"
            posting_strategy = "Post immediately on TikTok/Instagram ads. Universal outrage & betrayal hooks convert cold audiences without prior lore."
        elif 6 <= ep <= 20:
            funnel_weight = 8.0
            funnel_stage = "Tier 2: Mid-Funnel Re-engagement"
            posting_strategy = "Post in Week 1. High-voltage romantic tension & secrets re-engage dropped viewers."
        else:
            funnel_weight = 2.0
            funnel_stage = "Tier 3: Core Fan Retention / High Stakes Climax"
            posting_strategy = "Post later in the campaign to avoid early plot spoilers while rewarding binge-watchers."

        final_composite_score = cand.viral_score + funnel_weight

        item = cand.to_dict()
        item["global_rank_score"] = round(final_composite_score, 2)
        item["funnel_stage"] = funnel_stage
        item["posting_strategy"] = posting_strategy
        ranked_list.append(item)

    ranked_list.sort(key=lambda x: x["global_rank_score"], reverse=True)

    # Assign 1-indexed ranks
    for rank_idx, item in enumerate(ranked_list, start=1):
        item["rank"] = rank_idx

    return ranked_list

