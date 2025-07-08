# 📍 Indian Address Parsing System

A Python-based project that extracts structured components (like house number, street, locality, city, state, and pincode) from unstructured Indian addresses using regex and spaCy NLP. This system helps in cleaning, standardizing, and validating Indian address data, especially useful for logistics, e-commerce, and government data handling. Optionally integrates a PIN code dataset for enhanced accuracy.

---

## 🚀 Features

- ✅ Extracts house number, street, locality, city, state, and pincode
- 🔍 Uses spaCy for Named Entity Recognition (NER)
- 📦 Regex-based parsing for Indian address formats
- 🧪 Pincode validation using external CSV (if provided)
- 🧼 Standardizes and cleans raw address data
- 📊 Suitable for bulk processing using CSV files

---

## 🛠️ Tech Stack

- **Python 3**
- **spaCy** (`en_core_web_sm`)
- **Regex**
- **Pandas**

---

## 📁 File Structure
```bash
├── addresses.csv # Input file containing raw address data
├── pincodes.csv # Optional - for validating pin codes
├── address_parser.py # Main address parsing script
└── README.md # Project documentation
```
## ⚙️ Setup Instructions

1. **Clone the repository**

```bash
git clone https://github.com/priyanshi0609/Indian-Address-Parser.git
cd indian-address-parser
```
2. **Install dependencies**
```bash
pip install pandas spacy
python -m spacy download en_core_web_sm
```
3.**Run the parser**
```bash
python address_parser.py
```

## Input

