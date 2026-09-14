# 🦷 Dental DDI Risk Scorer

> **Drug-drug interaction risk analytics for dental prescribers, powered by FDA pharmacovigilance data.**

Dentists prescribe from a small, specialist pharmacopeia (antibiotics, analgesics, anxiolytics, antifungals). Yet, patients often present with complex chronic regimens—anticoagulants, statins, antihypertensives—creating a high-stakes Drug-Drug Interaction (DDI) landscape. 

This tool maps **what a dentist is about to prescribe** against **what the patient is already taking**, using statistical adverse event signals from the FDA FAERS database to rank and surface interaction risks.

*Disclaimer: This tool is for educational and portfolio demonstration purposes only. It is not a clinical decision support system.*

---

## 🏗️ The Engineering Approach

To ensure maintainability and reflect professional Software Development Life Cycle (SDLC) standards, this project was built using a strict feature-branch methodology. Each layer is independently testable, replaceable, and documented.

*   **`feature/data-pipeline`**: The raw TWOSIDES dataset is a 4 GB, 42-million row CSV. Loading it entirely into memory is not viable. The pipeline uses Pandas to stream it in 500k-row chunks, filters for our 27 target dental drugs, and writes the output to a compressed Parquet file (reducing 4GB to 105MB).
*   **`feature/scoring-engine`**: Collapses 7 million interaction rows into a single risk score per drug pair. Because FDA FAERS data is heavily biased toward severe events (meaning naïve thresholds flag everything as a "Major" risk), the engine uses **percentile-rank normalisation**. It scores based on statistical signal (PRR), adverse effect breadth, and clinical severity.
*   **`feature/fastapi-backend`**: A FastAPI service that loads the 1.3MB scored data into memory at startup via a `lifespan` context manager, ensuring ultra-fast, sub-millisecond REST API responses without database overhead.
*   **`feature/frontend`**: A React/Vite single-page application providing autocomplete search, dynamic severity badging, and a clean clinical UI.

---

## ⚙️ System Architecture

```text
Raw TWOSIDES.csv (4 GB, 42M rows)
        │
        ▼  [ streaming chunk processor ]
 interactions.parquet (105 MB, 7M rows)
        │
        ▼  [ percentile-rank normaliser ]
   scores.parquet (1.3 MB, 20,592 pairs)
        │
        ▼  [ in-memory lifespan load ]
  FastAPI Backend (Railway)  ────────────▶  React + Vite Frontend (Vercel)
```

### Tech Stack
*   **Data Engineering:** Python, Pandas, PyArrow, Parquet
*   **Backend:** FastAPI, Uvicorn, Pydantic v2
*   **Frontend:** React 18, Vite 5, Vanilla CSS
*   **MLOps / Tooling:** Poetry, Ruff, Black, Pytest, Make

---

## 📡 API Reference & Examples

The backend provides a clean REST API. Here is how a client interacts with it.

### `POST /check` (Core Endpoint)
Submits a patient's current medication list and returns all known interaction risks with dental drugs, ranked by severity.

**Request:**
```bash
curl -X POST "http://localhost:8000/check" \
     -H "Content-Type: application/json" \
     -d '{"patient_drugs": ["warfarin", "atorvastatin"]}'
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
      "top_adverse_effects": [
        "Rhabdomyolysis", 
        "Myopathy", 
        "Hepatitis"
      ],
      "prr_max": 45.1,
      "n_adverse_effects": 312
    }
  ],
  "patient_drugs_checked": ["warfarin", "atorvastatin"],
  "patient_drugs_not_found": [],
  "total_interactions": 1
}
```

### Supporting Endpoints
*   `GET /health`: Returns API status and memory-load confirmation.
*   `GET /dental-drugs`: Returns the curated list of 27 dental prescribing drugs (categories, ATC codes).
*   `GET /patient-drugs`: Returns the ~1,700 patient-side drug names to power frontend autocomplete.

---

## 🚀 Local Development (Quick Start)

### 1. Install dependencies
```bash
git clone https://github.com/asmaaliouche/dental-ddi-risk-scorer.git
cd dental-ddi-risk-scorer
poetry install
```

### 2. Prepare the Data
To run the full pipeline, download `TWOSIDES.csv` from [nsides.io](http://nsides.io/) and place it in `data/raw/`.
*(Note: If you just want to run the API, the final `scores.parquet` is already committed to the repo).*

```bash
make pipeline   # 4GB CSV -> 105MB Parquet
make score      # 105MB Parquet -> 1.3MB Scored Pairs
make verify     # Sanity check the data
```

### 3. Run the Stack
```bash
# Terminal 1: Start the FastAPI backend (http://localhost:8000)
make run

# Terminal 2: Start the React frontend (http://localhost:5173)
make dev-ui
```

### 4. Code Quality & Testing
```bash
make check      # Runs Ruff linting and Pytest suite
make smoke      # Runs API integration tests
```

---

## 📊 What the Data Revealed

Building this tool produced some clinical findings directly from the data:
1. **The Fluconazole Burden:** Of the 27 dental drugs, fluconazole carries the highest interaction risk by a significant margin. As a strong inhibitor of major drug-metabolising enzymes, its interactions with statins (causing rhabdomyolysis) and anticoagulants (haemorrhage) dominate the top-scoring pairs.
2. **Discriminating Scoring:** Out of 20,592 possible drug pair combinations, fewer than 1% scored as "Major" under this percentile-rank model. This proves the scoring is discriminating and clinically useful, rather than generating alert fatigue.

---

## 📄 License
MIT — see [LICENSE](LICENSE).