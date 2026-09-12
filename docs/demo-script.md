# SIH 2026 — Demo Walk-Through Script
**Platform:** SIH Intelligence — AI-Driven Social Media Analytics  
**Slot duration:** 10 minutes (adjust checkmarks per time available)

---

## Setup (Before Judges Arrive)

```bash
cd D:\TEAM007
make demo          # or: docker compose up -d && python -m app.scripts.seed_demo
```

- Verify http://localhost:3000 loads the login page
- Verify http://localhost:8000/health returns `{"status":"ok"}`
- Keep terminal visible showing Celery worker output (shows "live" activity)
- Browser: open in fullscreen, zoom 100%

---

## Talking Points — 30-Second Elevator Pitch

> "Every time the government announces a major policy, it faces unexpected backlash — petrol prices, farm laws, demonetisation. The problem is the government has no early-warning system. We built one. This platform monitors public discourse across six social media platforms in real time, segments the population into opinion groups, and lets you simulate citizen reaction to a policy *before* it is announced — 'simulate before you announce'."

---

## Demo Flow (10 minutes)

### 1. Login & Overview (1 min)

- Navigate to `http://localhost:3000`
- Login: `admin@sih.gov.in` / `Admin@SIH2026`
- **Point out:**
  - "Demo Mode" banner — real platform connectors available in production
  - KPI tiles: total posts monitored, active segments, trending topics, overall sentiment
  - "Quick Insights" row — top emerging topic + discourse tone
  - Sentiment timeline chart (24h)
  - Platform activity breakdown — 6 platforms, colour-coded
  - Connector status panel at the bottom — each platform's health

---

### 2. Trend Intelligence (1.5 min)

- Click **Trends** in sidebar
- **Show:** list of 10 trending topics with velocity and emerging badge
- Click **"Petrol Price Hike Backlash"**
- **Point out detail panel:**
  - Trend Score (0.91), Velocity (+4.2/hr), Acceleration
  - Unique Users (18,400), Platform Count (5)
  - Estimated Volume Curve — 7-day sparkline
- Switch to **Emerging** tab — "EV Subsidy Announcement Buzz" and "Delhi AQI Emergency"
- **Key message:** *"We don't just count posts — we measure velocity and acceleration so you see what's about to trend, not what already did."*

---

### 3. Demographic Segmentation (2 min)

- Click **Audience** in sidebar
- **Show:** 6 segments with epistemic labels (Observed / Inferred / Modeled)
- Click **"Hindi-speaking Twitter users interested in Fuel & Energy Prices"**
- **Point out:**
  - Segment size (4,200 estimated), 50% negative sentiment
  - Geo distribution: UP, Delhi, Bihar
  - Topic preference radar chart
  - Activity profile — peaks in evenings
  - 7-day sentiment timeline
  - Persona card: "This segment represents strongly negative voices primarily discussing fuel & energy price hikes…"
- **Key message:** *"We don't treat India as one monolith. A policy on fuel prices will land completely differently with rural Tamil farmers versus English-speaking Bangalore tech workers."*

---

### 4. Policy Simulation — Core Demo (3 min)

- Click **Policy Sim** in sidebar
- In the textarea, type or click:
  **"Proposed increase in fuel tax by 8%"**
- Click **Run Simulation**
- **While loading, explain:** *"The engine is extracting topic keywords, finding analogous historical posts, and combining each segment's sentiment profile with our topic-affinity model."*
- **Show results:**
  - Detected topics: `fuel_prices`, `taxation_gst`
  - Overall: ~18% positive, ~32% neutral, ~50% negative
  - Confidence score
  - **Expand** "Hindi-speaking Twitter" segment → 60% oppose, likely narratives: "diesel prices killing transport businesses", "middle class bearing all the burden"
  - **Expand** "English-speaking Reddit / AI" segment → more moderate response
- **Then run a second query:**
  **"Expansion of PM-KISAN direct benefit transfer"**
  - Show the *positive* prediction — farm subsidy gets 42% support
  - *"Same platform, opposite prediction — because the model knows which segments care about which topics."*
- **Key message:** *"Give any draft policy. Get back: which segments oppose it, how strongly, and what specific narratives will circulate — before a single announcement is made."*

---

### 5. Network Analysis (1.5 min)

- Click **Network** in sidebar
- **Show force-directed graph** — nodes sized by influence (PageRank)
- Toggle Color-by: **Platform** → see cross-platform cluster structure
- Toggle Color-by: **Community** → Louvain-detected communities
- **Point out:** dashed rings = bridge nodes (connect otherwise-separate communities)
- Click **Influencers** tab → sortable table by PageRank
- Click **Bridges** tab → high-betweenness nodes
- **Key message:** *"If you want a policy to reach rural Hindi speakers, you target these bridge nodes — they're the connectors between platform bubbles."*

---

### 6. (Optional — if Ollama is running) Local LLM Demo (1 min)

- Go back to **Policy Sim**
- Toggle **Local LLM Mode** ON (shows model name + "ready" in green)
- Run **"Proposed 5% GST on packaged food items"**
- Show the **AI Executive Intelligence Brief** panel in results
- Go to **Audience** → select any segment → "Regenerate with LLM" button
- **Key message:** *"For sensitive policy deliberations, everything can run fully offline. No API calls. No data leaving the government network."*

---

### 7. Privacy & Compliance (30 sec)

- Click **Settings**
- Point out:
  - "Author IDs: SHA-256 pseudonymised — no individual can be identified"
  - "Policy queries hashed — raw text never stored on server"
  - "30-day data TTL — DPDP Act 2023 compliant"
  - "Local LLM option — fully air-gapped deployment"

---

## Q&A Preparation

**Q: How accurate is the simulation?**
> The model uses historical post sentiment patterns as ground truth. Confidence scores are honest — typically 60-80% for well-documented topics with analogue data, lower for novel policies. We label all outputs with epistemic status: OBSERVED / INFERRED / MODELED.

**Q: Can it handle Indian languages?**
> Yes — the NLP pipeline uses XLM-RoBERTa (multilingual, fine-tuned on Indian social media) and sentence-transformers with 50+ language support. Hindi, Tamil, Telugu, Bengali, and Marathi are the primary targets.

**Q: Is this a scraper? How do you handle platform ToS?**
> The connectors use official APIs where available (Twitter v2, Reddit, YouTube Data API). The mock mode used in this demo generates synthetic data. Real deployment uses API credentials managed by the ministry.

**Q: What about misinformation or bot accounts?**
> Author hashes let us detect repeated posting patterns without storing identities. Engagement weighting in the trend score penalises sudden volume spikes inconsistent with historical baselines — a partial bot signal.

**Q: Where would this be deployed?**
> On NIC (National Informatics Centre) infrastructure. PostgreSQL + Redis on government cloud, Ollama on local servers for sensitive queries. The entire stack is containerised with Docker.

---

## Fallback (if internet/Docker is down)

- The seed data is already in the database — all pages work offline
- The synthetic cold-start mode activates automatically if DB is empty
- Screenshot deck at `docs/screenshots/` as last resort

---

## Post-Demo Checklist

- [ ] Leave dashboard running for judges to explore independently
- [ ] Have README.md printed / open in separate tab
- [ ] API docs at http://localhost:8000/api/docs for technical judges
- [ ] Makefile visible in terminal — shows one-command setup
