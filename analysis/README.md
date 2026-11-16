# SupeRR Selector Season 2, Round 1: pressure rating

Run everything (about one minute):

    .venv/Scripts/python analysis/runPipeline.py

Check the rebuilt match state against official results (run by hand, not automated):

    .venv/Scripts/python analysis/validateState.py

Inputs are read from `dataPack/Data Pack/`. Intermediate tables and charts go to `analysis/output/`.
Deliverables go to `submission/`: `superrSelectorRound1Report.pdf` and `finalRankings.csv`.
All thresholds are in `analysis/pipelineConfig.py`. Dependencies are in `analysis/requirements.txt`.
