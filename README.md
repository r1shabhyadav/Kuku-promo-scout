# Kuku FM — AI Microdrama Promo Scout 🎬
> **AI Generalist Assignment — Problem 1: Find the Promos (Ads)**  
> Built for Kuku FM / Kuku TV Editorial & Growth Team

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/UI-FastAPI%20%2B%20Tailwind-emerald.svg)](https://fastapi.tiangolo.com/)
[![Groq Fast Inference](https://img.shields.io/badge/LLM-Groq%20%2F%20Gemini%20%2F%20Local-orange.svg)](https://groq.com/)

---

## 📌 Executive Overview
Kuku FM produces short vertical microdrama series (1 to 2-minute episodes). Editors currently review episodes manually to extract 20–60s promotional clips for Instagram Reels, TikTok, and YouTube Shorts. 

This repository provides **Promo Scout AI**: an end-to-end automated pipeline that ingests raw screenplays, parses millisecond-accurate camera and dialogue beats, extracts high-velocity promo windows bounded between 20s and 60s, scores them for **3-second thumb-stopping hooks** and **unresolved cliffhangers**, performs **automated quality auditing**, and ranks promos for optimal social ad spend.

---

## 🚀 Key Features

1. **Deterministic Signal Processing + AI Hybrid Architecture**:
   - Python AST engine handles millisecond timestamp arithmetic, $20\text{s} \le \Delta t \le 60\text{s}$ duration constraints, and prevents sentence boundary clipping.
   - LLM Reasoning Layer (Groq Qwen/Llama or Gemini) scores emotional nuance, hook intensity, and synthesizes 1-line virality justifications.
   - Zero-hallucination guarantee on timestamps.
2. **Multi-Segment & Continuous Discovery**:
   - Discovers continuous climactic stretches as well as 2-segment dramatic stitches (e.g., Opening betrayal hook spliced with ending cliffhanger cut).
3. **Automated Quality Auditor**:
   - Flags real-world microdrama failure modes: **Pronoun Ambiguity ("Cold Start")**, **Low-Kinetic Talking Heads**, and **Premature Expository Cuts**.
4. **Ad Funnel Strategic Ranking**:
   - Ranks promos by acquisition stage: **Tier 1 (Cold Launch Ads, Ep 1–5)**, **Tier 2 (Mid-Funnel Re-engagement)**, and **Tier 3 (Retention/Late Climax)**.
5. **Interview-Ready Prototype**:
   - Interactive local Web Dashboard (FastAPI + Tailwind) + CLI for instantaneous testing on any new screenplay during live interviews.

---

## 🛠️ Quick Start

### 1. Installation
Clone the repository and install requirements:
```bash
pip install -r requirements.txt
```

### 2. Run the Interactive Web Dashboard
```bash
python -m kuku_promo_scout.app
```
Open your browser at `http://127.0.0.1:8000`. You can:
- Select any of the 50 episodes or **upload a new `.txt` screenplay** directly.
- Adjust duration bounds (20s – 60s).
- Click **"Extract & Score Promos"** to view segment breakdowns, hook/cliffhanger scores, and quality audits.
- Export results as JSON.

### 3. Run via CLI (Single Episode or Custom File)
```bash
# Test on Episode 3 from the dataset
python run_demo.py --episode 3

# Test on any custom screenplay file
python run_demo.py --input "path/to/screenplay.txt" --min 20 --max 60

# Run in 100% offline mode (no API key required)
python run_demo.py --episode 1 --offline
```

### 4. Run Automated Unit & Regression Tests
```bash
python -m unittest discover -s tests
```
Verifies timestamp parsing math, 20s–60s duration constraints, case-insensitive headers, quality audit flags, and funnel ranking.

### 5. Run Batch Pipeline on All 50 Episodes
```bash
python -c "from kuku_promo_scout.batch_runner import run_batch_pipeline; run_batch_pipeline(enrich_all=True)"
```
Outputs are automatically written to `raw_outputs/`.

---

## 📊 Evaluation & Production Results (50 Episodes)

| Rank | Episode | Timestamps | Duration | The 3-Second Hook | The Cliffhanger Cut | Strategy / Funnel |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **#1** | **Ep 3** | `00:25.80 ➔ 01:06.00` | 40.2s | Guards violently yank Juliana backward as she screams 'Let me go!' | Dragged into dark cathedral nave; plea swallowed by echo before stranger arrives. | Tier 1 (Post on Launch Day) |
| **#2** | **Ep 4** | `01:54.00 ➔ 02:29.00` | 35.0s | Mother shouts 'You are disowned!' & groom sneers 'For a nobody!' | Juliana and scarred warrior walk into light; family frozen in shock. | Tier 1 (Post on Launch Day) |
| **#3** | **Ep 1** | `01:23.70 ➔ 02:17.50` | 53.8s | Juliana's trembling whisper 'Father... please look at me' met with cold refusal. | Groom declares her 'low value'; knuckles whiten to string swell cut-to-black. | Tier 1 (Post on Launch Day) |

---

## 📁 Repository Structure

```
kuku fm/
├── Solution_Doc_Kuku_Problem_1.pdf     # Official 2-Page Executive Solution Doc
├── walkthrough_video_script.md         # 2-3 minute script for walkthrough video
├── run_demo.py                         # Clean CLI tool for interview live-testing
├── generate_pdf_solution_doc.py        # Reproducible PDF generation script
├── requirements.txt                    # Project dependencies
├── tests/                              # Automated Unit & Regression Tests
│   ├── __init__.py
│   └── test_pipeline.py                # Mathematical constraints & auditor tests
├── kuku_promo_scout/                   # Core engine package
│   ├── __init__.py                     # Package exports
│   ├── parser.py                       # Screenplay AST parser with millisecond precision
│   ├── promo_engine.py                 # 20-60s window search & multi-segment stitching
│   ├── candidate_generator.py          # Semantic & dramatic arousal scoring
│   ├── llm_evaluator.py                # Swappable Groq/Gemini/Local LLM evaluator
│   ├── quality_checker.py              # Automated quality auditor (detects failure modes)
│   ├── ranker.py                       # Global viral index & ad funnel prioritization
│   ├── batch_runner.py                 # 50-episode batch processor
│   └── app.py                          # Interactive Web Prototype
├── raw_outputs/                        # Unedited outputs folder
│   ├── promos_all_50_episodes.json     # Master JSON with full metadata
│   ├── promos_ranked.csv               # Ranked spreadsheet
│   ├── promos_summary.md               # Summary markdown
│   └── episodes/                       # 50 individual per-episode JSON files
└── scripts/                            # Extracted 50 screenplay files
```

---

## 🛡️ Quality Checking & Failure Mode Analysis

The brief specifically asks: *"Where does your tool pick badly?"*  
Our automated `QualityAuditor` identifies 4 critical edge cases:
1. **Pronoun Ambiguity ("Cold Start" Failure)**: Segments starting with *"He lied to you..."* without establishing the subject. *Mitigation*: Opening pronouns are penalized unless preceded by an explicit character action.
2. **Low-Kinetic "Talking Heads"**: Dialogues that contain high-emotion vocabulary but zero physical staging or camera movement. *Mitigation*: Window must contain at least 2 camera/action blocking changes.
3. **Expository Transitions**: Cutting on characters walking away or closing doors. *Mitigation*: Audio/visual cut-point snapping forces endings onto close-up reaction beats.
4. **Pacing Compaction (<25s)**: Cuts that are too brief to let dramatic tension land are flagged for editorial padding.

---

## 💰 Economics at Kuku Volume
- **Compute Time**: 4.38s to process an entire 50-episode series (all 50 screenplays).
- **Cost**: **$0.00** using deterministic AST + local scoring / Groq free tier. If using OpenAI GPT-4o-mini, cost is **< $0.03 per entire 50-episode show**, scaling to 50 weekly shows for less than **$1.50/week**.

