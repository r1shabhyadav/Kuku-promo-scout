import os
import glob
import json
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .parser import parse_screenplay, seconds_to_timestamp
from .promo_engine import find_promos_for_screenplay, PromoCandidate
from .llm_evaluator import LLMEvaluator
from .quality_checker import QualityAuditor
from .ranker import rank_promos

app = FastAPI(title="Kuku FM — AI Microdrama Promo Scout")

SCRIPTS_DIR = "kuku fm/scripts/I Married a Broken Soldier. He was a Duke"

@app.get("/", response_class=HTMLResponse)
async def index():
    # List available sample episodes
    files = sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.txt")))
    episodes = []
    for f in files:
        base = os.path.basename(f)
        episodes.append({"filename": base, "title": base.replace(".txt", "")})

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kuku FM — AI Promo Scout</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0b0f19; }}
        .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
        .gradient-border {{
            background: linear-gradient(60deg, #f72585, #7209b7, #3a0ca3, #4361ee, #4cc9f0);
        }}
    </style>
</head>
<body class="text-slate-100 min-h-screen">
    <!-- Header -->
    <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-rose-500 to-amber-500 flex items-center justify-center font-extrabold text-xl shadow-lg shadow-rose-500/30">
                    K
                </div>
                <div>
                    <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                        Kuku FM <span class="text-xs px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 font-medium">Promo Scout AI</span>
                    </h1>
                    <p class="text-xs text-slate-400">Microdrama Trailer Extraction & Viral Ranking Engine</p>
                </div>
            </div>

            <!-- Model Switcher / Interview Config -->
            <div class="flex items-center space-x-4">
                <div class="flex items-center space-x-2 bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-1.5 text-xs">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span class="text-slate-300 font-medium">Engine:</span>
                    <select id="model-provider" class="bg-transparent text-white font-semibold focus:outline-none">
                        <option value="groq" selected>Groq (Qwen 2.5 300 t/s)</option>
                        <option value="gemini">Gemini 1.5 Flash</option>
                        <option value="local">Local Semantic Heuristic</option>
                    </select>
                </div>
                <a href="#about" class="text-xs text-slate-400 hover:text-white transition">Brief Specs</a>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 py-8">
        <!-- Top Control Deck -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <!-- Left: Input Selection -->
            <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-sm font-semibold tracking-wide text-slate-300 uppercase">1. Select or Upload Script</h2>
                    <span class="text-xs text-rose-400 font-mono">50 episodes ready</span>
                </div>
                
                <div class="space-y-4">
                    <div>
                        <label class="block text-xs text-slate-400 mb-1.5">Preset Episode</label>
                        <select id="episode-select" class="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-rose-500">
                            {"".join([f'<option value="{ep["filename"]}">Ep {i+1}: {ep["title"][:42]}...</option>' for i, ep in enumerate(episodes)])}
                        </select>
                    </div>

                    <div class="relative flex py-1 items-center">
                        <div class="flex-grow border-t border-slate-800"></div>
                        <span class="flex-shrink mx-3 text-slate-500 text-xs">OR TEST NEW INPUT</span>
                        <div class="flex-grow border-t border-slate-800"></div>
                    </div>

                    <div>
                        <label class="block text-xs text-slate-400 mb-1.5">Upload Any Screenplay (.txt)</label>
                        <input type="file" id="script-file" accept=".txt" class="block w-full text-xs text-slate-400 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-rose-400 hover:file:bg-slate-700 cursor-pointer border border-dashed border-slate-700 rounded-xl p-2 bg-slate-950/50">
                    </div>
                </div>
            </div>

            <!-- Middle: Parameters & Duration Bounds -->
            <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-sm font-semibold tracking-wide text-slate-300 uppercase">2. Promo Specifications</h2>
                        <span class="text-xs text-cyan-400 font-mono">20s - 60s TikTok/Reels</span>
                    </div>

                    <div class="space-y-4">
                        <div>
                            <div class="flex justify-between text-xs text-slate-400 mb-1">
                                <span>Duration Bounds</span>
                                <span class="font-mono text-slate-200" id="duration-label">20s — 60s</span>
                            </div>
                            <div class="grid grid-cols-2 gap-3">
                                <div>
                                    <span class="text-[10px] text-slate-500">Min Duration (s)</span>
                                    <input type="number" id="min-dur" value="20" min="15" max="40" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white">
                                </div>
                                <div>
                                    <span class="text-[10px] text-slate-500">Max Duration (s)</span>
                                    <input type="number" id="max-dur" value="60" min="40" max="90" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white">
                                </div>
                            </div>
                        </div>

                        <div>
                            <span class="text-[10px] text-slate-500">API Key Override (Optional)</span>
                            <input type="password" id="custom-api-key" placeholder="Paste Groq/Gemini key for interview demo..." class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-600">
                        </div>
                    </div>
                </div>

                <button id="run-btn" onclick="runDiscovery()" class="w-full mt-4 bg-gradient-to-r from-rose-500 to-pink-600 hover:from-rose-600 hover:to-pink-700 text-white font-bold py-3 px-4 rounded-xl shadow-lg shadow-rose-500/25 transition flex items-center justify-center space-x-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                    <span>Extract & Score Promos</span>
                </button>
            </div>

            <!-- Right: Performance & Funnel Summary -->
            <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
                <div>
                    <h2 class="text-sm font-semibold tracking-wide text-slate-300 uppercase mb-4">3. Optimization Lenses</h2>
                    <div class="space-y-3">
                        <div class="flex items-start space-x-3 text-xs">
                            <div class="w-6 h-6 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold flex-shrink-0">1</div>
                            <div>
                                <span class="font-semibold text-slate-200">The 3-Second Hook:</span>
                                <p class="text-slate-400">Slaps, betrayals, sudden reveals, high-arousal lines that stop thumb scrolling.</p>
                            </div>
                        </div>
                        <div class="flex items-start space-x-3 text-xs">
                            <div class="w-6 h-6 rounded-lg bg-pink-500/20 text-pink-400 flex items-center justify-center font-bold flex-shrink-0">2</div>
                            <div>
                                <span class="font-semibold text-slate-200">The Cliffhanger Cut:</span>
                                <p class="text-slate-400">Audio swell cut right on an unanswered ultimatum before reaction plays out.</p>
                            </div>
                        </div>
                        <div class="flex items-start space-x-3 text-xs">
                            <div class="w-6 h-6 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold flex-shrink-0">3</div>
                            <div>
                                <span class="font-semibold text-slate-200">Standalone Sense:</span>
                                <p class="text-slate-400">Zero prior lore required. Universal archetypes (Cheating groom, Secret Duke).</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                    <span>Quality Filter: <strong class="text-emerald-400">Active</strong></span>
                    <span>Multi-Segment Stitching: <strong class="text-emerald-400">Enabled</strong></span>
                </div>
            </div>
        </div>

        <!-- Results Section -->
        <div id="results-container" class="space-y-6">
            <div id="empty-state" class="text-center py-16 border-2 border-dashed border-slate-800 rounded-3xl bg-slate-900/20">
                <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-800/60 flex items-center justify-center text-slate-500">
                    <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                </div>
                <h3 class="text-base font-semibold text-slate-300">No Promos Generated Yet</h3>
                <p class="text-xs text-slate-500 max-w-sm mx-auto mt-1">Select an episode or upload any screenplay and click 'Extract & Score Promos'.</p>
            </div>

            <div id="loading-state" class="hidden text-center py-16">
                <div class="inline-block animate-spin w-10 h-10 border-4 border-rose-500 border-t-transparent rounded-full mb-3"></div>
                <p class="text-sm font-medium text-slate-300">Analyzing screenplay beats & finding optimal promo cuts...</p>
                <p class="text-xs text-slate-500 mt-1">Applying timestamp constraints, scoring hooks, and auditing quality</p>
            </div>

            <!-- Dynamic Output Cards -->
            <div id="cards-wrapper" class="hidden space-y-6"></div>
        </div>
    </main>

    <script>
        async function runDiscovery() {{
            const emptyState = document.getElementById('empty-state');
            const loadingState = document.getElementById('loading-state');
            const cardsWrapper = document.getElementById('cards-wrapper');
            const fileInput = document.getElementById('script-file');
            const episodeSelect = document.getElementById('episode-select');
            const minDur = document.getElementById('min-dur').value;
            const maxDur = document.getElementById('max-dur').value;
            const provider = document.getElementById('model-provider').value;
            const customKey = document.getElementById('custom-api-key').value;

            emptyState.classList.add('hidden');
            cardsWrapper.classList.add('hidden');
            loadingState.classList.remove('hidden');

            const formData = new FormData();
            formData.append('min_duration', minDur);
            formData.append('max_duration', maxDur);
            formData.append('provider', provider);
            formData.append('api_key', customKey);

            if (fileInput.files.length > 0) {{
                formData.append('uploaded_file', fileInput.files[0]);
            }} else {{
                formData.append('selected_filename', episodeSelect.value);
            }}

            try {{
                const res = await fetch('/api/find-promos', {{
                    method: 'POST',
                    body: formData
                }});
                const data = await res.json();
                renderResults(data);
            }} catch (err) {{
                alert('Error running promo discovery: ' + err);
            }} finally {{
                loadingState.classList.add('hidden');
            }}
        }}

        function renderResults(data) {{
            const cardsWrapper = document.getElementById('cards-wrapper');
            cardsWrapper.innerHTML = '';

            if (!data.promos || data.promos.length === 0) {{
                cardsWrapper.innerHTML = `<div class="p-6 bg-amber-500/10 border border-amber-500/30 rounded-2xl text-amber-300 text-sm">No segments matched the specified duration window. Try loosening bounds (e.g. 15s to 70s).</div>`;
                cardsWrapper.classList.remove('hidden');
                return;
            }}

            // Render Episode Meta
            const metaHeader = document.createElement('div');
            metaHeader.className = "p-5 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4";
            metaHeader.innerHTML = `
                <div>
                    <div class="flex items-center gap-2 mb-1">
                        <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">Episode ${{data.episode_num}}</span>
                        <span class="text-xs text-slate-400 font-mono">Full Duration: ${{data.total_episode_duration}}</span>
                    </div>
                    <p class="text-xs text-slate-300 italic">"${{data.logline}}"</p>
                </div>
                <div class="flex items-center gap-3">
                    <button onclick="downloadJSON()" class="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition">Export JSON</button>
                </div>
            `;
            cardsWrapper.appendChild(metaHeader);

            window.__CURRENT_DATA = data;

            data.promos.forEach((p, idx) => {{
                const card = document.createElement('div');
                card.className = "bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden";
                
                const segBadges = p.segments.map(s => 
                    `<span class="px-2 py-1 rounded-md bg-slate-800 border border-slate-700 font-mono text-xs text-cyan-300 font-semibold">${{s.start}} ➔ ${{s.end}} (${{s.duration_sec}}s)</span>`
                ).join(' ');

                const auditStatus = p.quality_audit ? p.quality_audit.quality_status : 'PASSED';
                const auditBadge = auditStatus === 'PASSED'
                    ? `<span class="px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">AUDIT: PASSED</span>`
                    : `<span class="px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">AUDIT: REVIEW</span>`;

                card.innerHTML = `
                    <div class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800/80 gap-3 mb-5">
                        <div class="flex items-center space-x-3">
                            <span class="w-8 h-8 rounded-xl bg-gradient-to-tr from-rose-500 to-purple-600 flex items-center justify-center font-black text-sm text-white">#${{idx+1}}</span>
                            <div>
                                <h3 class="text-base font-bold text-white flex items-center gap-2">
                                    Option ${{idx+1}} — Total Duration: ${{p.total_duration_sec}}s
                                    ${{p.is_multi_segment ? '<span class="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-semibold">2-Part Stitch</span>' : ''}}
                                </h3>
                                <div class="flex items-center gap-2 mt-1.5">${{segBadges}}</div>
                            </div>
                        </div>

                        <div class="flex items-center space-x-3">
                            <div class="text-right">
                                <div class="text-[10px] text-slate-400">Viral Engagement Score</div>
                                <div class="text-xl font-black text-rose-400 font-mono">${{p.viral_score}} <span class="text-xs text-slate-500">/ 100</span></div>
                            </div>
                            ${{auditBadge}}
                        </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
                        <!-- Hook Box -->
                        <div class="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80">
                            <div class="flex items-center justify-between text-xs font-bold text-purple-400 uppercase tracking-wide mb-2">
                                <span>⚡ The 3-Second Hook</span>
                                <span class="font-mono text-slate-400">Score: ${{p.scores.hook}}/10</span>
                            </div>
                            <p class="text-xs text-slate-200 leading-relaxed">${{p.hook}}</p>
                        </div>

                        <!-- Cliffhanger Box -->
                        <div class="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80">
                            <div class="flex items-center justify-between text-xs font-bold text-pink-400 uppercase tracking-wide mb-2">
                                <span>🛑 The Cliffhanger Cut</span>
                                <span class="font-mono text-slate-400">Score: ${{p.scores.cliffhanger}}/10</span>
                            </div>
                            <p class="text-xs text-slate-200 leading-relaxed">${{p.cliffhanger}}</p>
                        </div>
                    </div>

                    <!-- Why it Works -->
                    <div class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 mb-4">
                        <div class="text-xs font-bold text-rose-300 uppercase tracking-wide mb-1">🎯 Why It Works for Social Scrollers</div>
                        <p class="text-xs text-rose-100 italic">"${{p.why_it_works}}"</p>
                    </div>

                    <!-- Excerpt Preview -->
                    <div class="text-xs text-slate-400 bg-slate-950 rounded-xl p-3 border border-slate-800/60 font-mono">
                        <span class="text-[10px] uppercase text-slate-500 font-bold block mb-1">Script Excerpt Sample:</span>
                        <div class="text-slate-300 line-clamp-2">${{p.dialogue_summary || 'Dialogue & visual beat action.'}}</div>
                    </div>
                `;
                cardsWrapper.appendChild(card);
            }});

            cardsWrapper.classList.remove('hidden');
        }}

        function downloadJSON() {{
            if (!window.__CURRENT_DATA) return;
            const blob = new Blob([JSON.stringify(window.__CURRENT_DATA, null, 2)], {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `kuku_promo_ep_${{window.__CURRENT_DATA.episode_num}}.json`;
            a.click();
        }}
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)

def find_promos_service(
    target_path: str,
    min_duration: float = 20.0,
    max_duration: float = 60.0,
    provider: str = "groq",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    sp = parse_screenplay(target_path)
    candidates = find_promos_for_screenplay(sp, min_duration=min_duration, max_duration=max_duration, top_k=3)

    evaluator = LLMEvaluator(api_key=api_key, provider=provider)

    promos_out = []
    for cand in candidates:
        if provider != "local":
            cand = evaluator.refine_candidate(cand, sp.logline)
        audit = QualityAuditor.audit_promo(cand)
        d = cand.to_dict()
        d["quality_audit"] = audit
        d["is_multi_segment"] = cand.is_multi_segment
        d["dialogue_summary"] = cand.dialogue_summary
        promos_out.append(d)

    return {
        "episode_num": sp.episode_num,
        "logline": sp.logline,
        "total_episode_duration": seconds_to_timestamp(sp.total_duration),
        "promos": promos_out
    }

@app.post("/api/find-promos")
async def api_find_promos(
    min_duration: float = Form(20.0),
    max_duration: float = Form(60.0),
    provider: str = Form("groq"),
    api_key: Optional[str] = Form(None),
    selected_filename: Optional[str] = Form(None),
    uploaded_file: Optional[UploadFile] = File(None)
):
    target_path = None
    temp_path = None

    if uploaded_file and uploaded_file.filename:
        temp_path = f"kuku fm/kuku_promo_scout/temp_{uploaded_file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await uploaded_file.read())
        target_path = temp_path
    elif selected_filename:
        target_path = os.path.join(SCRIPTS_DIR, selected_filename)
    else:
        target_path = os.path.join(SCRIPTS_DIR, "episode-001-Episode 1671703.txt")

    try:
        result = find_promos_service(
            target_path=target_path,
            min_duration=min_duration,
            max_duration=max_duration,
            provider=provider,
            api_key=api_key
        )
        return result
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    uvicorn.run("kuku_promo_scout.app:app", host="127.0.0.1", port=8000, reload=False)
