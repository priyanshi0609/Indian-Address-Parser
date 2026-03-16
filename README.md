# 🗺️ Indian Address Parser

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.2-150458?style=for-the-badge&logo=pandas&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A Python-based project that extracts structured components (like house number, street, locality, city, state, and pincode) from unstructured Indian addresses using regex and spaCy NLP. This system helps in cleaning, standardizing, and validating Indian address data, especially useful for logistics, e-commerce, and government data handling. Optionally integrates a PIN code dataset for enhanced accuracy**

[Live Demo](#) · [API Docs](#api-reference) · [Report Bug](issues) · [Request Feature](issues)

</div>

---

## 📌 The Problem

Delivery agents across India receive addresses like:

```
Near Durga Mandir, Shahdara, 110032
```

No city. No state. No district. Just a landmark, a neighbourhood name, and a PIN code — yet this is all a real person wrote when placing an order.

The Indian Address Parser turns this into:

```json
{
  "locality":   "Shahdara",
  "landmark":   "Near Durga Mandir",
  "city":       "Delhi",
  "district":   "East Delhi",
  "state":      "Delhi",
  "pincode":    "110032",
  "confidence_score": 0.75,
  "validation_errors": ["House number missing — delivery agent may need to ask"],
  "match_method": "pincode"
}
```

City, district, and state were inferred entirely from the PIN code — the user never wrote them.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **PIN-Anchor Strategy** | Uses the 6-digit PIN as the primary anchor. Auto-fills city, district, state from a 155,000+ entry reference dataset. |
| **Leftover Token Inference** | After all explicit fields are extracted, scans remaining comma-separated segments to infer locality. |
| **Stuck Token Splitting** | `237okhlaphase3NewDelhi` → `237 okhla phase 3 New Delhi`. Handles mobile keyboard concatenation. |
| **Fuzzy City Matching** | Handles typos in city names using RapidFuzz token_set_ratio. |
| **12 Extracted Fields** | care_of, house_number, building_name, street, locality, landmark, village, subdistrict, district, city, state, pincode |
| **Confidence Score** | Each result includes a 0–1 confidence score and a list of missing fields. |
| **Bulk API** | Parse up to 500 addresses in a single request. |
| **Self-Documenting API** | Swagger UI at `/docs`, ReDoc at `/redoc`. |

---

## 🏗️ Architecture

```
Raw Address String
       │
       ▼
┌─────────────────────────────────────────────────┐
│                  normalize_text()                │
│  • CamelCase / digit-letter split               │
│  • Abbreviation expansion (s/o → son of, etc.)  │
│  • Noise character removal                       │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│            extract_pincode()   ← ANCHOR          │
│  Regex extracts 6-digit PIN                      │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│          _enrich_from_pin()  ← KEY STEP          │
│  PIN → city / district / state                   │
│  (155,000-row lookup, ~100% accurate)            │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│           Regex Extractors (parallel)            │
│  care_of │ house_number │ building │ landmark    │
│  street  │ locality     │ village  │ district    │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│        infer_locality_from_tokens()              │
│  Scans leftover comma-separated segments         │
│  Anything not already claimed → locality         │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│     Text-Based Fallback (if PIN failed)          │
│  Exact match → Fuzzy match → State abbreviation  │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
         Confidence Score + Validation Errors
```

---

## 📂 Project Structure

```
Indian-Address-Parser/
│
├── main.py              # FastAPI application, all API endpoints
├── parser.py            # Core parsing pipeline (IndianAddressParser class)
├── extractor.py         # All regex patterns and extraction functions
├── models.py            # Pydantic request/response schemas + internal dataclass
├── utils.py             # Text normalisation, abbreviation expansion
├── data_loader.py       # CSV loading with flexible column detection
├── config.py            # Centralised config: thresholds, paths, logging
│
├── addresses.csv        # Sample addresses for bulk testing
├── pincodes.csv         # PIN code → city/district/state reference (155k+ rows)
├── Cities_Towns_District_State_India.csv   # City name → district/state lookup
│
├── tests/
│   └── test_parser.py   # 30+ unit + integration tests (pytest)
│
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- `pincodes.csv` with columns: `Pincode`, `City`, `District`, `State`
- `Cities_Towns_District_State_India.csv` with city/district/state data

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/priyanshi0609/Indian-Address-Parser.git
cd Indian-Address-Parser

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn main:app --reload --port 8000
```

### Verify it's running

```bash
curl http://localhost:8000/health
# → {"status": "ok", "version": "1.0.0", "datasets_ok": true}
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## 📡 API Reference

### `POST /parse` — Parse a single address

**Request:**
```json
{
  "address": "S/O Ram Singh, H No 15/1 Near City Mall, Indira Nagar, Lucknow, UP - 226016"
}
```

**Response:**
```json
{
  "original": "S/O Ram Singh, H No 15/1 Near City Mall, Indira Nagar, Lucknow, UP - 226016",
  "parsed": {
    "care_of":        "Son of Ram Singh",
    "house_number":   "15/1",
    "landmark":       "City Mall",
    "locality":       "Indira Nagar",
    "city":           "Lucknow",
    "state":          "Uttar Pradesh",
    "pincode":        "226016",
    "district":       "Lucknow",
    "confidence_score": 0.95,
    "validation_errors": [],
    "match_method":   "pincode"
  }
}
```

### `POST /parse/bulk` — Parse up to 500 addresses

```json
{
  "addresses": [
    "Near Durga Mandir, Shahdara, 110032",
    "Vill Rampur, Dist Pratapgarh, UP - 230143"
  ]
}
```

### `GET /health` — Health check

```json
{ "status": "ok", "version": "1.0.0", "datasets_ok": true }
```

### `GET /parse-all` — Parse all addresses in `addresses.csv`

Parses every row and saves results to `parsed_output.json`.

---

## 🔍 How Field Extraction Works

### PIN-Anchor Strategy (Most Important)
The PIN code is extracted first and immediately used to look up **city, district, and state** from the reference dataset. This works even when the user writes nothing but a landmark and a PIN:

```
Input:  "Opp. Bus Stand, Karol Bagh, 110005"
PIN:    110005  →  city=New Delhi, state=Delhi, district=Central Delhi
Result: locality=Karol Bagh, landmark=Bus Stand, city/state from PIN
```

### Supported Care-of Patterns
`S/O`, `W/O`, `C/O`, `D/O`, `H/O`, `F/O`, `M/O` and their full English equivalents.

### Supported House/Plot Indicators
`H No`, `House No`, `Plot No`, `Door No`, `Flat No`, `Room No`, `Khasra No`, `Gali No`

### Landmark Indicators
`Near`, `Opp.`, `Opposite`, `Beside`, `Behind`, `Next to`, `Adjacent`, `In front of`

### Stuck Token Splitting
```
237okhlaphase3    →  237 okhla phase 3
NewDelhi110001    →  New Delhi 110001
HNo15SectorA      →  H No 15 Sector A
```

---

## 📊 Confidence Score

Each response includes a `confidence_score` from 0.0 to 1.0:

| Score | Meaning | Action |
|---|---|---|
| 0.8 – 1.0 | All key fields found | Auto-process |
| 0.5 – 0.79 | Most fields found, minor gaps | Review optional |
| 0.3 – 0.49 | Several fields missing | Human review recommended |
| < 0.3 | Critical fields missing | Contact sender |

The `validation_errors` array lists exactly what's missing:
```json
"validation_errors": [
  "House number missing — delivery agent may need to ask",
  "Pincode not found in reference dataset"
]
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

The test suite covers:
- Pincode extraction edge cases (7-digit numbers, prefixed PINs, bare PINs)
- All care-of patterns (S/O, W/O, C/O, D/O, H/O)
- House number variants (H No, Flat, Plot, Door, Khasra)
- Full pipeline integration (confidence score, to_dict() contract)
- FastAPI endpoints (single, bulk, health, validation errors)
- Stuck token splitting
- Empty / noisy inputs

---

## 🗄️ Database (PostgreSQL)

The next phase adds PostgreSQL persistence:

```sql
-- Core table
CREATE TABLE parse_requests (
    id              BIGSERIAL PRIMARY KEY,
    raw_address     TEXT NOT NULL,
    parsed_output   JSONB NOT NULL,           -- full parsed result
    confidence_score FLOAT,
    match_method    VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for analytics
CREATE INDEX idx_confidence  ON parse_requests(confidence_score);
CREATE INDEX idx_created_at  ON parse_requests(created_at DESC);
CREATE INDEX idx_city_state  ON parse_requests(
    (parsed_output->>'city'),
    (parsed_output->>'state')
);
```

**Why PostgreSQL?** The parsed address has a fixed schema (relational), but storing the full parsed dict as JSONB avoids 12+ nullable columns while remaining queryable. See the interview prep doc for full justification.

---

## 🖥️ Frontend (React + Tailwind)

A single-page React app with three components:

- **AddressInput** — textarea + parse button, loading state
- **ParsedResult** — field card, colour-coded by confidence (green/yellow/red)
- **HistoryTable** — past parses from DB, filterable by confidence/date

*Screenshots will be added when frontend is complete.*


## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/add-spacy-ner`)
3. Add tests for any new extractor patterns
4. Open a Pull Request

When adding new regex patterns, follow the existing convention in `extractor.py` — document what the pattern matches with a comment above it.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [India Post PIN Code dataset](https://data.gov.in) — Government of India open data
- [RapidFuzz](https://github.com/maxbachmann/RapidFuzz) — Fast fuzzy string matching
- [FastAPI](https://fastapi.tiangolo.com) — Modern Python API framework

