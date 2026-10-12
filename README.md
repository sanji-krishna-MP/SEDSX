# Chandrayaan-2/3 OHRC & NASA LRO NAC Lunar Image Comparison Engine (v2.0)

A local web application that inputs a **Source image** (ISRO Chandrayaan-2/3 OHRC) and a **Reference image** (NASA LRO NAC), performs full pixel-level preprocessing, establishes terrain correspondences via SIFT and robust affine fitting, and calculates all **20 metric types** (9 Preprocessing metrics per image and 11 Comparison metrics) with normalized display indicators out of 100.

---

## Architecture Overview

```
SEDS-HACKS/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point & CORS configuration
│   │   ├── routes.py             # REST API endpoints (runs, metrics, matches, assets, demo)
│   │   ├── models.py             # Pydantic schemas (RunSummary, MetricDetail, MatchPoint)
│   │   ├── database.py           # SQLite persistence layer (runs, metrics, matches, checkpoints)
│   │   ├── image_processing.py   # Full mathematical computation of 9 P-metrics & 11 C-metrics
│   │   └── sample_generator.py   # Realistic cratered lunar terrain generator for testing
│   ├── data/
│   │   ├── runs.db               # SQLite database
│   │   ├── runs/                 # Stored runs, visual artifacts & warps
│   │   └── samples/              # Bundled realistic OHRC/LRO test images & metadata
│   └── tests/
│       └── test_metrics.py       # Unit tests for all 20 metrics & Section 13 worked examples
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx                # Title bar, status badge & demo loader
│   │   │   ├── EvidenceSidebar.tsx       # Left panel prioritizing C1–C11 indicators
│   │   │   ├── OriginalsPreview.tsx      # Reference & Source previews with layer toggles
│   │   │   ├── RegisteredComparison.tsx  # Central viewer with draggable split curtain
│   │   │   ├── MetricsTabs.tsx           # Preprocessing (9 rows), Comparison (11 rows), Matches
│   │   │   ├── FormulaModal.tsx          # Mathematical drilldown modal with substituted values
│   │   │   ├── UploadView.tsx            # Dual upload cards, preview, swap & advanced options
│   │   │   └── HistoryView.tsx           # Saved runs history with instant reload
│   │   ├── App.tsx                       # Main view router and polling controller
│   │   ├── types.ts                      # TypeScript interfaces
│   │   └── index.css                     # Design system & Tailwind styling
│   ├── vite.config.ts                    # Vite config with API proxy to localhost:8000
│   └── package.json
└── Dev_plan/
    ├── OHRC_LRO_Detailed_PRD_20_Metrics.docx
    └── extracted_prd.txt
```

---

## Quick Start & Running Locally

### 1. Backend (FastAPI)
```powershell
cd d:\SEDS-HACKS\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- API Documentation (Swagger): `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### 2. Frontend (Vite + React)
```powershell
cd d:\SEDS-HACKS\frontend
npm install
npm run dev
```
- Open browser at `http://localhost:3000/`

### 3. Run Automated Tests
```powershell
cd d:\SEDS-HACKS\backend
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 20 Metric Types Specification

### Preprocessing Metrics (Evaluated separately for Source & Reference):
- **P1**: Mean intensity ($\mu = \frac{1}{N}\sum I_i$, Brightness position index)
- **P2**: Median intensity ($m = \text{median}(I)$, Median position index)
- **P3**: Standard deviation ($\sigma$, Variation index)
- **P4**: Intensity histogram (256 uniform bins, percentage per bin)
- **P5**: Percentiles ($Q_{0.01}, Q_{0.50}, Q_{0.99}$)
- **P6**: Valid pixel fraction ($f_{\text{valid}} = 100 \frac{N}{P}$, Valid-data index)
- **P7**: Dark pixel fraction ($f_{\text{dark}} = 100 \frac{\text{count}(J_i < t_{\text{dark}})}{N}$)
- **P8**: Endpoint / saturation fraction ($f_{\text{endpoint}} = 100 \frac{N_{\text{endpoint}}}{N_{\text{eval}}}$)
- **P9**: Intensity range ($\text{span} = I_{\max} - I_{\min}$, Range utilization index)

### Comparison Metrics (Pair Alignment & Evaluation):
- **C1**: Overlap percentage ($O = 100 \frac{\text{Area}(F_s \cap F_r)}{\text{Area}(F_s)}$)
- **C2**: Usable overlap fraction ($U = 100 \frac{\text{Area}(\text{shared valid})}{\text{Area}(\text{shared geometric})}$)
- **C3**: Candidate match count ($M$, Candidate-utilization index $100 \frac{M}{\min(N_s, N_r)}$)
- **C4**: Inlier count ($N_{\text{in}}$, Verified-feature utilization index $100 \frac{N_{\text{in}}}{\min(N_s, N_r)}$)
- **C5**: Inlier ratio ($R_{\text{in}} = 100 \frac{N_{\text{in}}}{M}$, Inlier-agreement index)
- **C6**: Inlier spatial coverage ($100 \frac{N_{\text{occupied}}}{N_{\text{eligible}}}$ across $4 \times 4$ grid)
- **C7**: Median geometric residual ($E_{\text{med}}$, Consistency index $\frac{100}{1 + E_{\text{med}}/e_0}$)
- **C8**: Independent checkpoint RMSE (RMSE on withheld ground-truth points, Checkpoint error index $\frac{100}{1 + \text{RMSE}/r_0}$)
- **C9**: Sun direction difference ($\Delta S = \arccos(s_s \cdot s_r)$, Solar-direction similarity index $100(1 - \Delta S/180)$)
- **C10**: Sun elevation difference ($\Delta E = |E_s - E_r|$, Solar-elevation similarity index $100(1 - \Delta E/180)$)
- **C11**: Sampling ratio ($R = \frac{\max(\text{GSD}_s, \text{GSD}_r)}{\min(\text{GSD}_s, \text{GSD}_r)}$, Sampling compatibility index $\frac{100}{R}$)
