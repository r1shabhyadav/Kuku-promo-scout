# 🎙️ 2-to-3 Minute Screen Walkthrough Script
> **Kuku FM AI Generalist Assignment — Problem 1: Find the Promos**  
> *Record this using Loom, OBS, or QuickTime, and share the unlisted YouTube or Google Drive link.*

---

### [0:00 - 0:30] Introduction & Problem Choice
*(Screen shows: Your terminal or the Web Dashboard at `http://127.0.0.1:8000`)*

> "Hi team at Kuku! For this assignment, I chose **Problem 1: Find the Promos**.
> Kuku is scaling AI microdramas faster than ever, and manual promo hunting by editors is a major bottleneck when releasing new shows every week. 
> To solve this, I built **Promo Scout AI**—a hybrid system that automates extracting 20 to 60-second viral promos directly from microdrama screenplays with millisecond timestamp precision."

---

### [0:30 - 1:15] Architecture: Code vs. AI
*(Screen shows: Architecture diagram or code structure in VS Code / IDE)*

> "When approaching this, a classic mistake is dumping 50 full episodes into an LLM prompt. That leads to hallucinated timestamps and heavy API costs.
> Instead, I separated signal processing from AI reasoning:
> 1. **Deterministic Python AST Parser:** Handles millisecond-accurate regex parsing of camera and dialogue beats, strictly enforces the 20 to 60-second duration bounds, and prevents awkward sentence truncations.
> 2. **AI Semantic Layer:** Uses a swappable LLM engine—currently connected to Groq for ultra-fast 300 token/sec inference, but also supporting Gemini or local offline heuristics—to evaluate the **first 3-second thumb-stopping hook** and **cliffhanger tension**.
> 3. **Strategic Funnel Ranker:** Classifies promos into Tier 1 (Launch Day cold traffic), Tier 2 (Mid-funnel re-engagement), and Tier 3 (Retention), so media buyers know exactly what to post first."

---

### [1:15 - 2:00] Live Prototype Demo
*(Screen shows: Web Dashboard in browser, clicking 'Extract & Score Promos' or running `python run_demo.py --episode 3` in terminal)*

> "Let's see it in action. Here is the web dashboard running locally.
> I can select any of the 50 episodes, or drop in any brand-new screenplay file during our interview.
> I click **'Extract & Score Promos'**—and in just fractions of a second, the engine evaluates candidate windows.
> 
> For **Episode 3**, our top ranked promo runs for **40.2 seconds** from `00:25.80` to `01:06.00`.
> - **The Hook:** Guards violently yanking Juliana backward as she screams 'Let me go!'.
> - **The Cliffhanger Cut:** Cuts abruptly as Juliana is dragged into the dark cathedral nave, right as an ominous string swell peaks and before the mysterious stranger's proposal is revealed.
> - **Why it Works:** Physical violence plus family betrayal triggers instant empathy on TikTok and Instagram feeds."

---

### [2:00 - 2:40] Quality Checking & Failure Modes
*(Screen shows: Quality Audit card in the UI highlighting warnings)*

> "The brief specifically asks: *'Where does your tool pick badly?'*
> We built an automated **Quality Auditor** that flags edge cases:
> - **Pronoun Ambiguity ('Cold Start' failure):** When a clip opens with 'He lied to you' without establishing who 'He' is, the tool flags it and penalizes the score.
> - **Low-Kinetic Talking Heads:** If a scene has high dramatic words but zero camera movement or physical action, scrollers bounce within 2 seconds. The auditor requires blocking movement.
> - **Expository Endings:** Snaps cut points before characters exit doors, freezing on the emotional reaction shot."

---

### [2:40 - 3:00] Wrap-up & Economics
*(Screen shows: The 2-page Solution Doc PDF)*

> "I ran the pipeline across all 50 episodes in just 4.38 seconds, generating the full raw JSON and CSV outputs.
> At Kuku's scale, this costs virtually **$0.00** on local/Groq inference, or under **$0.03 per entire show** on commercial models.
> Thank you, and I look forward to running this live on your test scripts during the interview!"

