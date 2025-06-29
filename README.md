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
├── parser.py # Main address parsing script
├── requirements.txt # Python dependencies
└── README.md # Project documentation
```
## ⚙️ Setup Instructions

1. **Clone the repository**

```bash
git clone 
cd indian-address-parser
```


