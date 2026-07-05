# Dental DDI Risk Scorer

> **Disclaimer:** This tool is for educational and research purposes only. It is **not** a clinical decision support system and must **not** be used to guide prescribing decisions.

A drug-drug interaction (DDI) risk scorer tailored to dental prescribers. Input a patient's current medication list and get a ranked, explainable list of interaction risks against the drugs a dentist would actually prescribe.

---

## The Clinical Problem

Dentists routinely prescribe a small, well-defined set of drugs — antibiotics, analgesics, anxiolytics, local anaesthetics, antifungals — yet patients present with increasingly complex medication lists. The risk of a clinically significant DDI is real and underappreciated in dental practice. Existing general-purpose interaction checkers are noisy and non-specific to the dental context.

This tool filters the known interaction space down to what matters in the dental chair.

---

## Data Sources

| Source | Description | Licence |
|--------|-------------|---------|
| [TWOSIDES](http://tatonettilab.org/offsides/) | 1,332 drug pairs with 868 adverse drug reactions derived from FDA FAERS spontaneous reports via disproportionality analysis | Creative Commons |

> **Note:** DrugBank was the original target but was replaced by TWOSIDES, which is freely available without registration and provides real-world pharmacovigilance signal.

---

## Dental Drug List

Manually curated ~35 drugs that dentists prescribe across six categories:

| Category | Drugs |
|----------|-------|
| **Antibiotics** | Amoxicillin, Amoxicillin-clavulanate, Metronidazole, Clindamycin, Clarithromycin, Azithromycin |
| **Analgesics (NSAIDs)** | Ibuprofen, Aspirin, Naproxen |
| **Analgesics (other)** | Paracetamol (Acetaminophen) |
| **Opioids** | Codeine, Tramadol |
| **Local Anaesthetics** | Lidocaine, Articaine, Mepivacaine |
| **Anxiolytics** | Diazepam, Midazolam |
| **Antifungals** | Fluconazole |
| **Steroids** | Dexamethasone, Prednisolone |

This list is what makes the tool *clinical* rather than generic — a pure ML engineer would treat all drugs equally; the curation is where domain knowledge adds value.

---

## Methodology

### Scoring (Path A — Rule-based composite risk score)

Each interaction pair is scored on three axes:

1. **Pharmacovigilance signal strength** — proportional reporting ratio (PRR) and reporting odds ratio (ROR) from TWOSIDES
2. **Report count** — raw number of adverse event co-reports
3. **Adverse event severity** — weighted by outcome type (death > hospitalisation > other)

Scores are normalised to a 0–100 scale and binned into `major / moderate / minor`.

Interpretability is prioritised over model complexity — a clinician must be able to understand *why* a pair is flagged.

---

## Project Structure

```
dental-ddi-risk-scorer/
├── data/
│   ├── raw/           # TWOSIDES source files (git-ignored)
│   ├── processed/     # Cleaned interaction tables (git-ignored)
│   └── reference/     # Curated dental drug list (committed)
├── notebooks/         # Exploratory analysis
├── src/
│   └── ddi_scorer/    # Core scoring package
├── api/
│   ├── main.py        # FastAPI app entry point
│   └── routers/       # Endpoint modules
├── tests/
├── pyproject.toml
├── Makefile
└── .env.example
```

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
git clone https://github.com/your-username/dental-ddi-risk-scorer.git
cd dental-ddi-risk-scorer
poetry install --with dev

# 2. Set up environment
cp .env.example .env

# 3. Run the API
make run
# → http://localhost:8000/docs
```

---

## Known Limitations

- **TWOSIDES coverage:** Based on FDA FAERS spontaneous reports — reporting bias means common drug pairs are over-represented; rare but serious interactions may be missed.
- **No pharmacogenomic adjustment:** CYP450 polymorphisms (e.g., CYP2D6 in codeine metabolism) are not modelled.
- **No dose-dependency:** Interaction risk often varies with dose; this tool treats each drug as a binary presence.
- **Dental drug coverage:** Articaine and mepivacaine have limited pharmacovigilance data; local anaesthetic interactions are flagged conservatively.
- **Not for clinical use:** See disclaimer above.

---

## Licence

Code: MIT  
Data (TWOSIDES): Creative Commons — see original source for terms.  
DrugBank data (if used in future): non-commercial academic use only.
