# Dental DDI Risk Scorer

> **Disclaimer:** This tool is for educational and research purposes only. It is **not** a clinical decision support system and must **not** be used to guide prescribing decisions.

A drug-drug interaction (DDI) risk scorer tailored to dental prescribers. Input a patient's current medication list and get a ranked, explainable list of interaction risks against the drugs a dentist would actually prescribe.

---

## The Clinical Problem

Dentists routinely prescribe a small, well-defined set of drugs — antibiotics, analgesics, anxiolytics, local anaesthetics, antifungals — yet patients present with increasingly complex medication lists. The risk of a clinically significant DDI is real and underappreciated in dental practice. Existing general-purpose interaction checkers are noisy and non-specific to the dental context.

This tool filters the known interaction space down to what matters in the dental chair.

---

## How It Works (Data Flow)

```
dental_drugs.csv          TWOSIDES (42.9M rows)
(27 dental drugs)    →    filter: keep rows where
curated by category        drug_1 OR drug_2 is dental
                                    ↓
                      interactions.parquet (7M rows, 105 MB)
                      dental drug ↔ patient drug pairs
                                    ↓
                         scorer.py (next step)
                         composite risk score per pair
                                    ↓
                         POST /check → ranked results
```

**The key idea:** We don't look at all possible drug interactions — only the subset where a dentist's drug meets a patient's existing medication. The 27 dental drugs intersect with 1,739 drugs a patient might already be on, producing 20,592 unique drug pairs with real pharmacovigilance signal.

---

## Data Sources

| Source | Description | Licence |
|--------|-------------|---------|
| [TWOSIDES](http://tatonettilab.org/offsides/) | 42.9M rows — drug pairs × adverse effects derived from FDA FAERS spontaneous reports via disproportionality analysis (PRR). Covers 1,918 unique drugs and 11,281 unique adverse effects. | Creative Commons |

### What TWOSIDES contains (per row)

| Column | Description |
|--------|-------------|
| `drug_1_concept_name` / `drug_2_concept_name` | Drug pair |
| `condition_concept_name` | Reported adverse effect (e.g. "Arthralgia", "QT prolongation") |
| `PRR` | Proportional Reporting Ratio — how much more often this pair is reported together vs. separately. Higher = stronger signal. |
| `PRR_error` | Standard error of PRR |
| `mean_reporting_frequency` | Co-report frequency in FAERS |
| `A, B, C, D` | 2×2 contingency table for the disproportionality calculation |

---

## Dental Drug List (`data/reference/dental_drugs.csv`)

27 drugs across 8 categories — curated to match the exact concept names used in TWOSIDES so they join cleanly with no fuzzy matching.

| Category | Drugs |
|----------|-------|
| **Antibiotics** | Amoxicillin, Metronidazole, Clindamycin, Clarithromycin, Azithromycin |
| **NSAIDs** | Ibuprofen, Aspirin, Naproxen |
| **Non-opioid Analgesics** | Acetaminophen (Paracetamol) |
| **Opioid Analgesics** | Codeine, Dihydrocodeine, Tramadol |
| **Local Anaesthetics** | Lidocaine, Articaine, Mepivacaine, Bupivacaine, Levobupivacaine, Prilocaine |
| **Anxiolytics / Sedatives** | Diazepam, Midazolam |
| **Antifungals** | Fluconazole, Nystatin |
| **Corticosteroids** | Dexamethasone, Prednisolone, Methylprednisolone, Prednisone |
| **Vasoconstrictors** | Epinephrine (used with local anaesthetics) |

The reference CSV also stores ATC codes and clinical notes for each drug (e.g. "Strong CYP3A4 inhibitor" for clarithromycin and fluconazole).

---

## Data Pipeline (`src/ddi_scorer/pipeline.py`)

Streams the 4 GB TWOSIDES CSV in 500,000-row chunks - never loads the whole file into memory.

**Steps:**
1. Load the 27 dental drugs from `data/reference/dental_drugs.csv`
2. For each chunk, keep rows where `drug_1` OR `drug_2` is a dental drug
3. Label each row: which drug is the dental drug (prescriber side) and which is the patient's drug
4. Save filtered data to `data/processed/interactions.parquet` (105 MB, 7,038,176 rows)

**Run it:**
```bash
make pipeline
```

**Verify the output:**
```bash
make verify
```

---

## Methodology

### Scoring (Path A — Rule-based composite risk score)

Each dental drug ↔ patient drug pair generates many rows in `interactions.parquet` (one per reported adverse effect). The scorer aggregates them into a single risk score per pair using three axes:

1. **Signal strength** — PRR from TWOSIDES (how disproportionately often this pair is co-reported)
2. **Breadth** — number of distinct adverse effects reported for this pair
3. **Severity weight** — adverse effects vary in clinical seriousness (QT prolongation ≠ dry mouth)

Scores are normalised to a 0–100 scale and binned into `major / moderate / minor`.

Interpretability is prioritised over model complexity - a clinician must be able to understand why a pair is flagged.

---

## Project Structure

```
dental-ddi-risk-scorer/
├── data/
│   ├── raw/                    # TWOSIDES.csv — git-ignored (4 GB)
│   ├── processed/              # interactions.parquet — git-ignored (105 MB)
│   └── reference/
│       └── dental_drugs.csv    # 27 curated dental drugs — committed
├── notebooks/                  # Jupyter notebooks for exploration
├── src/
│   └── ddi_scorer/
│       ├── __init__.py
│       └── pipeline.py         # TWOSIDES filter → interactions.parquet
├── api/
│   ├── main.py                 # FastAPI app entry point
│   └── routers/                # Endpoint modules
├── tests/
├── pyproject.toml
├── Makefile
└── .env.example
```

---

## Makefile Commands

| Command | What it does |
|---------|-------------|
| `make install` | Install dependencies |
| `make dev` | Install with dev tools (jupyter, pytest, ruff…) |
| `make pipeline` | Run the TWOSIDES filter pipeline |
| `make verify` | Sanity-check the output parquet |
| `make lint` | Run ruff linter |
| `make test` | Run pytest |
| `make check` | lint + test — **run this before every commit** |
| `make run` | Start the FastAPI server |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/check` | Takes a list of drug names → returns ranked interactions |
| `GET` | `/dental-drugs` | Returns the curated dental drug list (for frontend autocomplete) |

---

## Running Locally

```bash
# 1. Clone and install
git clone https://github.com/asmaaliouche/dental-ddi-risk-scorer.git
cd dental-ddi-risk-scorer
poetry install --with dev

# 2. Set up environment
cp .env.example .env

# 3. Download TWOSIDES
# → http://tatonettilab.org/offsides/
# Place TWOSIDES.csv in data/raw/

# 4. Run the data pipeline (generates data/processed/interactions.parquet)
make pipeline

# 5. Start the API
make run
# → http://localhost:8000/docs
```

---

## Known Limitations

- **TWOSIDES coverage:** Based on FDA FAERS spontaneous reports — reporting bias means common drug pairs are over-represented; rare but serious interactions may be missed.
- **No pharmacogenomic adjustment:** CYP450 polymorphisms (e.g., CYP2D6 in codeine metabolism) are not modelled.
- **No dose-dependency:** Interaction risk often varies with dose; this tool treats each drug as a binary presence.
- **Local anaesthetic coverage:** Articaine and mepivacaine appear in TWOSIDES but have limited adverse event reports; their interactions should be interpreted conservatively.
- **Not for clinical use:** See disclaimer above.

---

## Licence

Code: MIT  
Data (TWOSIDES): Creative Commons — see original source for terms.
