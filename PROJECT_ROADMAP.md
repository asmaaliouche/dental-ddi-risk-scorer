# Dental DDI Risk Scorer — Project Roadmap & Technical Reference

This document serves as a complete project guide, covering the overall architecture, data strategy, completed steps, files created, and upcoming steps to build, test, and deploy the Dental Drug-Drug Interaction (DDI) Risk Scorer.

---

## 1. Project Overview & Strategy

### The Clinical Goal
Dentists prescribe from a small, specialized pharmacopeia (antibiotics, analgesics, local anesthetics, anxiolytics, antifungals, corticosteroids). However, dental patients present with complex, chronic medications (anticoagulants, statins, beta-blockers, antiplatelets, etc.). General-purpose DDI checkers are noisy and flood clinicians with irrelevant warnings. 

This tool maps **what a dentist is about to prescribe** against **what the patient is already taking**, filtering out generic clutter and focusing solely on high-risk dental scenarios.

### The Data Strategy: TWOSIDES vs DrugBank
Instead of DrugBank (which requires a restrictive academic registration for releases), we pivoted to **TWOSIDES**, a free, open, and robust pharmacovigilance dataset containing:
- Over **42.9 Million** adverse event co-reports derived from the FDA FAERS database.
- Proportional Reporting Ratios (PRR) to calculate statistical signal strength of drug-drug interactions.
- Over **1,918 unique drugs** and **11,281 unique adverse events**.

---

## 2. Project Architecture & File Map

Here is the current directory structure:

```
dental-ddi-risk-scorer/
├── .env.example                # Shell config blueprint
├── .gitignore                  # Keeps large datasets and local env files safe
├── Makefile                    # Unified commands (pipeline, score, test, lint, run)
├── poetry.lock                 # Pinned dependencies
├── pyproject.toml              # Project metadata & tool settings (Ruff, pytest, black)
├── README.md                   # Primary repo documentation
├── test_api.py                 # Smoke test script for the FastAPI backend
├── data/
│   ├── raw/                    # Git-ignored: holds 4GB raw TWOSIDES.csv
│   ├── processed/              # Git-ignored: processed parquet data
│   │   ├── interactions.parquet # 105MB pipeline output (7M rows, 20.5k pairs)
│   │   └── scores.parquet      # 1.3MB scoring output (20,592 unique pairs)
│   └── reference/
│       └── dental_drugs.csv    # 27 Curated dental prescribing drugs (Committed)
├── notebooks/
│   └── scan_twosides.py        # Archive: initial name validation script
├── src/
│   └── ddi_scorer/
│       ├── __init__.py
│       ├── pipeline.py         # Step 1-2: Chunked streaming & filter pipeline
│       └── scorer.py           # Step 3: Percentile-rank aggregation and severity weight scorer
├── api/
│   ├── __init__.py
│   ├── main.py                 # Step 4: FastAPI entrypoint, lifespan loaders, CORS
│   ├── schemas.py              # Pydantic request/response models
│   └── routers/
│       ├── __init__.py
│       ├── check.py            # POST /check endpoint logic
│       └── drugs.py            # GET /dental-drugs and GET /patient-drugs autocomplete routers
└── tests/
    ├── __init__.py
    ├── test_pipeline.py        # 9 unit tests for pipeline loader, filter & enricher
    └── test_scorer.py          # 19 unit tests for severity calculation & score ranges
```

---

## 3. Completed Pipeline & Features

### Step 1 & 2: The Data Pipeline (`pipeline.py` & `dental_drugs.csv`)
1. **Curated Reference**: We created `data/reference/dental_drugs.csv` containing **27 core drugs** dentists prescribe, mapped to their canonical TWOSIDES spelling, categorized, and annotated with clinical notes (e.g., Clarithromycin as a strong CYP3A4 inhibitor).
2. **Chunked Streaming**: Because `TWOSIDES.csv` is 4GB, `pipeline.py` streams it in chunks of 500,000 rows.
3. **Filtering & Enrichment**: It keeps rows where `drug_1` OR `drug_2` matches our dental drug list, labels which is the "dental drug" versus the "patient drug", and saves the result to `interactions.parquet` (105MB, 7,038,176 rows, 20,592 unique pairs).

### Step 3: Percentile-Rank Scoring Engine (`scorer.py`)
Because FAERS reports are inherently biased towards severe outcomes (almost every pair has at least one "death" report, meaning a simple max-severity model marks 94% of pairs as "Major"), we implemented **Percentile-Rank Normalization**:
- **PRR Component (40 pts)**: Normalized percentile rank of the maximum PRR for a pair.
- **Breadth Component (30 pts)**: Normalized percentile rank of the number of distinct adverse events reported for the pair.
- **Severity Component (30 pts)**: Calculated by mapping clinical severity weights (HIGH = 1.0, MEDIUM = 0.5, LOW = 0.2) to adverse event names. We use the **mean severity weight** (normalized 0 to 1) to distinguish pairs that only cause minor symptoms from those causing predominantly life-threatening conditions.
- **Result Bins**:
  - **Major** (Score 70-100): ~0.7% (148 pairs) — e.g., Prednisone ↔ chemotherapy, Acetaminophen ↔ Digoxin.
  - **Moderate** (Score 45-70): ~39.7%
  - **Minor** (Score 0-45): ~59.6%

### Step 4: FastAPI Backend (Currently on `feature/fastapi-backend`)
We have built:
- `api/schemas.py`: Pydantic definitions for requesting and returning checks, autocomplete lists.
- `api/routers/check.py`: `POST /check` matching inputted patient drugs and returning ranked DDIs.
- `api/routers/drugs.py`: `GET /dental-drugs` and `GET /patient-drugs` endpoints to feed autocomplete.
- `api/main.py`: Setup for CORS, app lifespans to load the parquet engine, and health endpoints.
- `test_api.py`: A local smoke test script verifying the web server.

---

## 4. Current Task & Git Branch Workflow

We are currently on the **`feature/fastapi-backend`** branch.
The backend code is complete and has been tested locally. 

### Branch Transition Steps:
To finalize this step, run the following commands:
1. **Stage and Commit the Backend**:
   ```bash
   git add api/ main.py schemas.py routers/ test_api.py
   git commit -m "feat(backend): FastAPI endpoints for check, dental-drugs, and patient-drugs autocomplete"
   git push origin feature/fastapi-backend
   ```
2. **Merge on GitHub**: Go to GitHub, create a Pull Request for `feature/fastapi-backend` -> `main`, review it, and merge it.
3. **Pull Main Locally**:
   ```bash
   git checkout main
   git pull origin main
   ```

---

## 5. Next Steps

Once the backend is merged to `main`, we will begin the next two phases:

### Step 5: Frontend Tool (`feature/frontend`)
We will build a React app (standalone Vite/React in the workspace or a React framework project) with:
1. **Patient Meds Search**: A search input with multi-select autocomplete pulling from `GET /patient-drugs`.
2. **Dental Drug Prescriber**: A checklist or dropdown of the 27 dental drugs (`GET /dental-drugs`).
3. **DDI Results Panel**: A clean, premium dashboard showcasing:
   - Highlighted **Major** interactions.
   - Severity badges (Red/Major, Orange/Moderate, Blue/Minor).
   - Expandable panels showing clinical notes (e.g. "CYP3A4 inhibition") and the top 5 adverse events (e.g. "Rhabdomyolysis", "Torsades de pointes").
4. **Clinical Disclaimer**: A persistent modal or banner explicitly warning that the tool is for educational use and not active clinical support.

### Step 6: Backend & Frontend Deployment (`feature/deploy`)
1. **Backend Deployment (Railway)**:
   - Connect the GitHub repository directly to Railway.
   - Ensure the server starts using `poetry run uvicorn api.main:app --host 0.0.0.0 --port $PORT`.
   - Note: The `interactions.parquet` is NOT committed to Git because of size. However, the final `scores.parquet` (1.3MB) is small enough to commit, or we can run the pipeline/scorer script inside a build phase. Committing `scores.parquet` directly is recommended for fast, serverless-like startups.
2. **Frontend Deployment (Vercel)**:
   - Deploy the Vite/React static build directory to Vercel.
   - Set up env variables pointing `VITE_API_BASE_URL` to the Railway deployment.
