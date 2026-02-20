# CVintra AI v2 - Intelligent Bioequivalence Study Assistant

![Status](https://img.shields.io/badge/status-active-brightgreen)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**CVintra AI** is an intelligent system for automated bioequivalence (BE) study design and protocol generation, powered by PubMed data mining, RAG (Retrieval-Augmented Generation), and regulatory compliance checks.

## 🎯 Key Features

### Core Functionality
- **One-Click Synopsis Generation**: Single button generates complete BE study protocol
- **CVintra Auto-Detection**: Extracts intra-individual variability from PubMed articles
- **Fallback Chain System**: Always provides meaningful data (PubMed → Database → Default 25%)
- **Study Design Recommendation**: 2×2 Cross-over, ANOVA analysis, sample size calculation
- **Regulatory Compliance**: Decision 85 (RF), EMA, FDA guidelines checks

### Data Sources
- 🌍 **PubMed** - Literature mining for CVintra (20+ articles per query)
- 💊 **DrugBank** - Drug information and pharmacokinetics
- 📋 **ГРЛС** - Russian drug registry for registered drugs
- 🗄️ **Local Database** - Fallback CVintra values (15-50%)

### Smart Analysis
- **Live Data Mode**: Local DB → PubMed → DrugBank fallback chain
- **HuggingFace QA**: Question-answering on drug data
- **Semantic Search RAG**: Vector embeddings for contextual search
- **Article Deduplication**: 85% similarity threshold
- **Source Ranking**: Reliability scoring for extracted parameters

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.8+
pip install flask flask-cors biopython requests python-docx
```

### Installation
```bash
git clone https://github.com/ilonamaskoleva-afk/cvintra-ai-v2.git
cd cvintra-ai-v2
pip install -r backend/requirements.txt
```

### Running the System
```bash
# Start Flask backend
cd backend
python app.py

# Frontend automatically serves at http://localhost:8000/
```

Open browser → http://localhost:8000/ → Enter drug name → Click "Сгенерировать синопсис" (Generate Synopsis)

## 📊 Project Structure

```
cvintra-ai-v2/
├── frontend/                      # Web interface
│   ├── index.html                # Main UI (Russian)
│   ├── js/app.js                 # Client logic
│   └── css/style.css             # Purple & periwinkle palette
│
├── backend/
│   ├── app.py                    # Flask API server
│   ├── cv_database.py            # Fallback CVintra values
│   ├── config.py                 # Configuration
│   │
│   ├── scrapers/                 # Data collection
│   │   ├── pubmed_scraper.py     # PubMed API + CVintra extraction
│   │   ├── drugbank_scraper.py   # DrugBank mining
│   │   └── grls_scraper.py       # Russian registry
│   │
│   ├── llm/                      # Language models
│   │   ├── cvintra_extractor.py  # Regex + LLM hybrid
│   │   └── api_reference.md      # Full API docs
│   │
│   ├── rag/                      # Semantic search
│   │   ├── rag_pipeline.py       # RAG orchestration
│   │   ├── vector_store.py       # Embeddings
│   │   └── document_loader.py    # Document parsing
│   │
│   ├── models/                   # Data models
│   │   └── llm_handler.py        # LLM integration
│   │
│   ├── utils/
│   │   ├── intelligent_drug_lookup.py    # Live Data + QA + RAG
│   │   ├── full_synopsis_generator.py    # Protocol generation
│   │   ├── synopsis_formatters.py        # Output formatting
│   │   ├── sample_size.py                # Sample size calculation
│   │   └── synopsis_generator.py         # Template processing
│   │
│   └── cache/                    # Query & article cache
│
├── TEST_UI_FLOW.md              # UI flow documentation
├── QUICKSTART.md                # Quick reference
├── ARCHITECTURE_OVERVIEW.md     # System design
└── README.md                    # This file
```

## 🔄 One-Button Workflow

```
User Input (МНН, dosage, form)
    ↓
[Сгенерировать синопсис] ← ONE BUTTON
    ↓
/api/full-analysis endpoint
    ├─ Search PubMed (20 articles)
    ├─ Extract CVintra (regex + LLM)
    ├─ Fallback: cv_database.get_typical_cv()
    ├─ Default: 25% if not found
    ├─ Calculate study design
    ├─ Compute sample size
    ├─ Check regulatory compliance
    └─ Return complete results
    ↓
Display Results:
    ├─ CVintra: X% (with source: база данных/PubMed/стандартное)
    ├─ Articles: N found
    ├─ Design: 2×2 Cross-over
    ├─ Sample Size: N subjects
    └─ Compliance: ✓ Decision 85, ✓ EMA, ✓ FDA
```

## 🎨 Frontend Features

### UI Components
- **Modern responsive design** - Works on desktop/tablet/mobile
- **4-color palette** - Periwinkle (#E6E6FA), Purple (#6A0DAD), Blue (#3B82F6), Lavender (#C8A2C8)
- **Real-time status** - Animated loading with step indicators
- **Card-based results** - Clean data presentation
- **Fallback display** - Never shows "Данные не найдены"

### CVintra Display
```
CVintra: 15% (база данных)
Уверенность: 72%
```

Source labels:
- `(пользователь)` - User input
- `(PubMed)` - Extracted from literature
- `(база данных)` - Local fallback database
- `(стандартное значение)` - Default 25%

## 🔧 API Endpoints

### Main Endpoints

#### **POST /api/full-analysis**
Complete BE study analysis in one call
```json
{
  "inn": "aspirin",
  "dosage_form": "tablet",
  "dosage": "500mg",
  "administration_mode": "fasted",
  "cvintra": null
}
```

Response includes:
- `cvintra` - Intra-individual variability (%)
- `design_recommendation` - Recommended study design
- `sample_size` - Calculated sample size with dropout adjustment
- `literature` - PubMed, DrugBank, ГРЛС results
- `regulatory_check` - Compliance status

#### **POST /api/search/pubmed**
Search PubMed for drug PKs
```json
{ "inn": "aspirin" }
```

#### **POST /api/analyze-smart**
Advanced analysis with Live Data Mode (WOW Feature)
```json
{
  "inn": "aspirin",
  "questions": ["What is typical CVintra?", "Any safety concerns?"]
}
```

See [backend/llm/API_REFERENCE.md](backend/llm/API_REFERENCE.md) for complete documentation.

## 💾 CVintra Fallback Database

Typical CVintra values (%) for common drugs:
```python
cv_typical = {
    "aspirin": 15,
    "metformin": 35,
    "ibuprofen": 20,
    "paracetamol": 18,
    "amlodipine": 22,
    "omeprazole": 40,
    "levothyroxine": 50,
    "propranolol": 55,  # High variability
    # ... 20+ more drugs
}
```

When PubMed extraction fails: `get_typical_cv('aspirin')` → 15%
When DB doesn't have drug: Default → 25%

## 🧪 Testing

### Run Tests
```bash
cd backend
python -m pytest tests/ -v
```

### Manual Testing
1. Start server: `python app.py`
2. Open http://localhost:8000/
3. Enter "aspirin" → Click button → See results

Expected results:
- ✅ CVintra shows value with source
- ✅ Articles count populated
- ✅ Design recommendation shown
- ✅ Sample size calculated
- ✅ No "Данные не найдены" display

## 📝 Recent Changes (v2.1)

### UI Consolidation ✓
- Merged 2 buttons into 1: "Сгенерировать синопсис"
- Single `/api/full-analysis` endpoint call
- No more separate search/analysis workflow

### CVintra Fallback System ✓
- Frontend triple fallback: `result.cvintra || result.design_recommendation?.cvintra || 25%`
- Backend triple fallback: user_input → PubMed → database → default
- Source labels show origin of data

### Results Display ✓
- Articles always shown with count
- CVintra displays with source label
- Design recommendation with rationale
- No empty fields or placeholders

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "feat: description"`
4. Push: `git push origin feature/your-feature`
5. Submit Pull Request

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 👥 Authors

- **Ilona Maskoleva** - Project lead
- **AI Assistant** - Feature implementation & optimization

## 🔗 Links

- GitHub: https://github.com/ilonamaskoleva-afk/cvintra-ai-v2
- Frontend: http://localhost:8000/
- API Docs: [backend/llm/API_REFERENCE.md](backend/llm/API_REFERENCE.md)
- Architecture: [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md)

## ⚠️ Disclaimer

This system is for **research and educational purposes**. It assists in BE study design but does not replace professional medical or regulatory expertise. Always consult regulatory guidelines and medical professionals for clinical decisions.

## 📧 Support

For issues, feature requests, or questions:
1. Check [TEST_UI_FLOW.md](TEST_UI_FLOW.md) for workflow docs
2. Check [QUICKSTART.md](QUICKSTART.md) for common issues
3. Open GitHub Issue with detailed description

---

**Last Updated**: February 20, 2026 | **v2.1** | **Status**: Active Development ✓
