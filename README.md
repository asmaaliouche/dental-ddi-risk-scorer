# Dental DDI Risk Scorer

> **Drug-drug interaction risk analytics for dental prescribers.**  
> Given a patient's chronic medication list, instantly surfaces pharmacovigilance-backed interaction risks with commonly prescribed dental drugs.

> **Disclaimer:** This tool is for **educational and reference use only**. It is not a clinical decision support system and must not replace professional pharmacological judgment or prescribing guidelines.

---

## What It Does

Dentists prescribe from a small, specialist pharmacopeia (antibiotics, analgesics, anxiolytics, antifungals, local anaesthetics, corticosteroids). Yet their patients often present with complex chronic regimens — anticoagulants, statins, antihypertensives, antidepressants — creating a high-stakes DDI landscape.

This tool maps **what a dentist is about to prescribe** against **what the patient is already taking**, using statistical adverse event signals from the FDA FAERS database to rank interaction risks.

---

## Architecture

```
Raw TWOSIDES.csv (4 GB, 42M rows)
        │
        ▼  src/ddi_scorer/pipeline.py
 interactions.parquet (105 MB, 7M rows)
        │
        ▼  src/ddi_scorer/scorer.py
   scores.parquet (1.3 MB, 20,592 pairs)
        │
        ▼  api/main.py (FastAPI)
  REST API  ─────────────────────────▶  frontend/  (React + Vite)
  :8000                                 :5173
```

### Scoring Methodology

Each drug pair is scored on three axes using **percentile-rank normalisation** (absolute thresholds are avoided because FAERS data is biased toward severe events, rendering ~95% of pairs "Major" under naive scoring):

| Component | Weight | Signal |
|---|---|---|
| PRR signal strength | 40 pts | Percentile rank of max Proportional Reporting Ratio |
| Adverse effect breadth | 30 pts | Percentile rank of distinct adverse events reported |
| Mean severity weight | 30 pts | Keyword-mapped clinical severity (normalised mean) |

Severity bins: **Major** (≥70), **Moderate** (45–70), **Minor** (<45).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data pipeline | Python 3.10+, Pandas, PyArrow |
| Scoring engine | NumPy, SciPy (rankdata) |
| API | FastAPI, Uvicorn, Pydantic v2 |
| Frontend | React 18, Vite 5, vanilla CSS |
| Dependency management | Poetry |
| Code quality | Ruff, Black, isort, pytest |

---

## Prerequisites

| Tool | Version | Required For |
|---|---|---|
| Python | ≥ 3.10 | All Python components |
| Poetry | ≥ 1.8 | Dependency management |
| Node.js | ≥ 18 | Frontend development |
| TWOSIDES dataset | — | Data pipeline (one-time) |

### Obtaining TWOSIDES

TWOSIDES is a free, open pharmacovigilance dataset derived from FDA FAERS.

1. Download `TWOSIDES.csv` from [nsides.io](http://nsides.io/) or the [Tatonetti Lab](http://tatonetti-lab.github.io/TWOSIDES/).
2. Place it at `data/raw/TWOSIDES.csv`.

> The file is approximately 4 GB. It is excluded from version control via `.gitignore`.

---

## Quick Start

### 1. Install dependencies

```bash
git clone https://github.com/asmaaliouche/dental-ddi-risk-scorer.git
cd dental-ddi-risk-scorer
poetry install
```

### 2. Run the data pipeline *(one-time, requires TWOSIDES)*

```bash
# Filter TWOSIDES → interactions.parquet
make pipeline

# Aggregate and score → scores.parquet
make score

# Verify output
make verify
```

> If you already have `data/processed/scores.parquet`, skip directly to step 3.

### 3. Start the API

```bash
make run
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
# UI available at http://localhost:5173
```

### 5. Smoke test the API

```bash
make smoke
```

---

## API Reference

Base URL: `http://localhost:8000`

### `GET /health`
Returns API status and data load confirmation.

```json
{
  "status": "ok",
  "scores_loaded": true,
  "n_pairs": 20592,
  "n_dental_drugs": 27
}
```

---

### `GET /dental-drugs`
Returns the curated list of 27 dental prescribing drugs with category, ATC code, and clinical notes.

---

### `GET /patient-drugs`
Returns all patient-side drug names available in the interaction database (~1,739 drugs). Use this to power frontend autocomplete.

---

### `POST /check`
**The core endpoint.** Takes a list of patient medications and returns all known interaction risks with dental drugs, ranked by composite risk score.

**Request:**
```json
{
  "patient_drugs": ["warfarin", "atorvastatin"]
}
```

**Response:**
```json
{
  "interactions": [
    {
      "dental_drug": "fluconazole",
      "dental_drug_display": "Fluconazole",
      "dental_drug_category": "Antifungal",
      "dental_drug_notes": "Strong CYP2C9 and CYP3A4 inhibitor...",
      "patient_drug": "atorvastatin",
      "risk_score": 74.2,
      "severity_bin": "major",
      "top_adverse_effects": ["Rhabdomyolysis", "Myopathy", "Hepatitis"],
      "prr_max": 45.1,
      "n_adverse_effects": 312
    }
  ],
  "patient_drugs_checked": ["warfarin", "atorvastatin"],
  "patient_drugs_not_found": [],
  "total_interactions": 18
}
```

---

## Project Structure

```
dental-ddi-risk-scorer/
├── api/                        # FastAPI backend
│   ├── main.py                 # App entry point, lifespan data loader, CORS
│   ├── schemas.py              # Pydantic request / response models
│   └── routers/
│       ├── check.py            # POST /check
│       └── drugs.py            # GET /dental-drugs, GET /patient-drugs
├── data/
│   ├── raw/                    # [git-ignored] Raw TWOSIDES.csv (4 GB)
│   ├── processed/              # [git-ignored] interactions.parquet, scores.parquet
│   └── reference/
│       └── dental_drugs.csv    # Curated 27-drug dental reference list
├── frontend/                   # React + Vite single-page app
│   ├── src/
│   │   ├── App.jsx             # Main application component
│   │   └── index.css           # Design system (glassmorphism + animation)
│   └── vite.config.js          # Dev proxy to API backend
├── scripts/
│   ├── get_node.py             # Downloads portable Node.js (Windows helper)
│   └── smoke_test.py           # Integration smoke test for the API
├── src/ddi_scorer/
│   ├── pipeline.py             # TWOSIDES streaming filter + dental enrichment
│   └── scorer.py               # Percentile-rank composite risk scorer
├── tests/
│   ├── test_pipeline.py        # 9 unit tests (pipeline logic)
│   └── test_scorer.py          # 19 unit tests (scoring engine)
├── Makefile                    # Developer workflow automation
├── pyproject.toml              # Poetry project + tool configuration
└── .env.example                # Environment variable template
```

---

## Development

```bash
# Run all checks before committing
make check      # lint + tests

# Individual tools
make lint       # ruff static analysis
make format     # black + isort
make test       # pytest (28 tests, no raw data required)

# Frontend
make dev-ui     # start Vite dev server
make build-ui   # production bundle
```

---

## Deployment

See the deployment guide for Railway (backend) and Vercel (frontend) configuration. The key requirement is that `scores.parquet` (1.3 MB) must be accessible to the backend at startup — either committed to the repository or generated during the build phase.

---

## Data & Methodology Notes

- **TWOSIDES** is derived from FDA FAERS spontaneous adverse event reports. Signals represent statistical co-reporting, not proven causality.
- **PRR (Proportional Reporting Ratio)** measures how much more often a drug pair is co-reported than expected by chance.
- **Percentile-rank scoring** is used instead of absolute thresholds because FAERS data is dominated by serious events, causing naïve severity-threshold models to classify ~95% of pairs as "Major".
- The dental drug reference list (`data/reference/dental_drugs.csv`) was curated manually to match exact TWOSIDES drug name spellings.

---

## License

MIT — see [LICENSE](LICENSE).
