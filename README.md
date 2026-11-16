# 🏏 SupeRR Selector Season 2: Round 1 — Pressure Ratings

[![Live Dashboard](https://img.shields.io/badge/Live_Dashboard-GitHub_Pages-0969da?style=for-the-badge&logo=github)](https://srijan300.github.io/superr-selector-pressure-ratings/)
[![Report](https://img.shields.io/badge/PDF_Report-Download-ff5722?style=for-the-badge&logo=adobeacrobatreader)](./submission/superrSelectorRound1Report.pdf)

> A context-aware leverage rating pipeline evaluating T20 batter and bowler reliability under pressure to drive **Rajasthan Royals'** squad strategy ahead of the **IPL 2027 auction**.

---

## 🌐 Live Interactive Dashboard
👉 **[View the Live Dashboard Here](https://srijan300.github.io/superr-selector-pressure-ratings/)**  
Interactive SVG charts, full player search & cards, uncertainty intervals, and Rajasthan Royals squad gap analysis — runs directly in the browser with zero dependencies.

---

## 🏆 Top 10 Picks Under Pressure

### 🏏 Top 10 Batters
| Rank | Player Name | Pressure Rating (Runs / 100 Balls Above Avg) | Credible Top-Tier Prob. |
| :---: | :--- | :---: | :---: |
| **1** | **Vaibhav Sooryavanshi** | +24.78 | 97.2% |
| **2** | **Abhishek Sharma** | +22.83 | 98.6% |
| **3** | **Suryakumar Yadav** | +16.13 | 93.2% |
| **4** | **Tim David** | +14.21 | 86.4% |
| **5** | **Shreyas Iyer** | +11.03 | 63.6% |
| **6** | **Heinrich Klaasen** | +11.00 | 68.0% |
| **7** | **Phil Salt** | +9.67 | 48.2% |
| **8** | **Virat Kohli** | +9.65 | 46.0% |
| **9** | **Ishan Kishan** | +8.35 | 37.8% |
| **10** | **Sai Sudharsan** | +8.25 | 33.6% |

### 🎯 Top 10 Bowlers
| Rank | Player Name | Pressure Rating (Runs Saved / 100 Balls Above Avg) | Credible Top-Tier Prob. |
| :---: | :--- | :---: | :---: |
| **1** | **Varun Chakravarthy** | +15.41 | 85.0% |
| **2** | **Sunil Narine** | +13.81 | 75.2% |
| **3** | **Josh Hazlewood** | +13.07 | 60.2% |
| **4** | **Mustafizur Rahman** | +12.48 | 65.2% |
| **5** | **Mohammad Nawaz** | +11.90 | 50.6% |
| **6** | **Jasprit Bumrah** | +11.17 | 51.6% |
| **7** | **Kagiso Rabada** | +10.50 | 44.2% |
| **8** | **Bhuvneshwar Kumar** | +9.80 | 40.2% |
| **9** | **Rashid Khan** | +9.37 | 36.8% |
| **10** | **Mitchell Santner** | +9.16 | 33.0% |

---

## 🧠 Methodology Summary

1. **Match Rebuilding:** Exact ball-by-ball score, target, wickets in hand, and balls remaining reconstructed across all IPL and T20I matches.
2. **Dynamic Win Probability & Pressure:** Pressure is defined as the expected outcome volatility (win probability swing) on each delivery.
3. **Contextual Ball Valuation:** Deliveries are valued against state-expected run distributions and dismissal costs (wicket resource curves).
4. **Bayesian Shrinkage & Credibility Filtering:** Small sample flukes are shrunk towards league mean; players are ranked by expected performance with strict credibility checks against overall performance baselines.

---

## 📁 Repository Structure

```text
├── index.html                 # Dashboard entry point (hosted via GitHub Pages)
├── dashboardStyles.css        # Dashboard styling
├── dashboardData.js           # Compiled player-level dataset
├── dashboardMain.js           # Interactive UI scripts & SVG renderer
├── methodologyReport.pdf      # Detailed methodology document
│
├── analysis/                  # Python analytics pipeline
│   ├── runPipeline.py         # Main execution script
│   ├── matchState.py          # State reconstructor
│   ├── winProbability.py      # Win probability models
│   ├── pressureIndex.py       # Ball leverage scoring
│   ├── playerRating.py        # Bayesian shrinkage & rating calculations
│   └── requirements.txt       # Python dependencies
│
└── submission/                # Deliverables
    ├── superrSelectorRound1Report.pdf # Official submission report
    ├── finalRankings.csv              # Exact final ranked table
    └── submissionGuide.md             # Competition submission notes
```

---

## 💻 Local Setup & Execution

### 1. View Dashboard Locally
```bash
python -m http.server 8000
```
Then open `http://localhost:8000` in your browser.

### 2. Run Analysis Pipeline
```bash
pip install -r analysis/requirements.txt
python analysis/runPipeline.py
```
