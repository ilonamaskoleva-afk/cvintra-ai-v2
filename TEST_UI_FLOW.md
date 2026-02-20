# UI Flow Test: One-Button Synopsis Generation

## Changes Made ✓

### 1. Frontend - HTML (index.html)
- **Removed**: `searchBtn` (Поиск в PubMed button)
- **Kept**: `generateBtn` renamed to "Сгенерировать синопсис" (Generate Synopsis)
- **Result**: Single button submission form

### 2. Frontend - JavaScript (app.js)
- **Removed**: 
  - `searchBtn` event listener
  - Two separate functions: `handleSearch()` and `handleAnalysis()`
- **Added**: 
  - Single unified `handleGenerateSynopsis()` function
  - Calls `/api/full-analysis` endpoint (does everything in one go)
- **Enhanced**: 
  - Status messages update during analysis
  - CVintra fallback: `result.cvintra || result.design_recommendation?.cvintra || 25%`
  - Source label shows origin: "(пользователь)", "(PubMed)", "(база данных)", or "(стандартное значение)"

### 3. Backend - Flask (app.py)
- **Already Working**: 
  - `/api/full-analysis` endpoint orchestrates entire pipeline
  - Always provides `results["cvintra"]` from fallback chain
  - Sets `design_recommendation.cvintra` for frontend
  - Returns articles, confidence, sources in one response

## Expected User Flow

1. **User enters**: МНН (e.g., "aspirin"), optional dosage/form
2. **User clicks**: ONE button "Сгенерировать синопсис"
3. **Backend processes**:
   - Queries PubMed for articles
   - Tries to extract CVintra from abstracts
   - Falls back to `cv_database.get_typical_cv('aspirin')` → 15%
   - If still missing, defaults to 25%
   - Calculates study design based on CVintra
   - Collects n_articles count
4. **Frontend displays** (in card format):
   - ✅ CVintra: 15% (база данных)
   - ✅ Articles: [list or count]
   - ✅ Design recommendation
   - ✅ Sample size calculation
   - ✅ Regulatory info

## Key Fallback Chain (Frontend)

```javascript
const cvintra = result.cvintra 
  || result.design_recommendation?.cvintra 
  || 25;  // Fallback to 25%
```

This ensures display never shows "Данные не найдены" or N/A.

## Key Fallback Chain (Backend)

```python
cvintra_source = "user_input"
if cvintra is None:
    cvintra = get_typical_cv(inn)  # Try database
    cvintra_source = "database"
if cvintra is None:
    cvintra = 25  # Default
    cvintra_source = "default"
```

This ensures backend always has a value.

## Files Modified

| File | Changes |
|------|---------|
| [frontend/index.html](frontend/index.html#L152) | Removed searchBtn; kept only generateBtn |
| [frontend/js/app.js](frontend/js/app.js#L72) | Unified handler; added CVintra fallback |
| [backend/app.py](backend/app.py#L200-L395) | Already complete; ensures CVintra always in response |

## Testing Notes

To verify:
1. Open http://localhost:8000/ in browser
2. Enter "aspirin" as МНН
3. Click "Сгенерировать синопсис"
4. Check results show:
   - CVintra value with source label
   - Article count
   - Design recommendation
   - Sample size

No more "Данные не найдены" or separate search/analysis buttons! ✓
