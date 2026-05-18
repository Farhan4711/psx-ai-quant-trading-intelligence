# Training the PSX prediction models — Colab Pro walkthrough

Step-by-step instructions for taking the heuristic ensemble shipped with
the repo and replacing it with **real trained ML models** (XGBoost +
Random Forest + LSTM + a stacked logistic meta-model per symbol).

> **Total time, end-to-end:** ~8 hours of your active attention spread
> across ~3 days. ~5 hours of that is unattended Colab training; you
> can tab away.
>
> **Cost:** $10 for one month of Colab Pro. Cancel after the run if you
> don't want to keep paying.

---

## Prerequisites

1. **Local Postgres with the EOD ingest run** — the trainer needs at
   least ~250 OHLCV bars per symbol. If you haven't run the ingest
   yet, complete Phase 6 of `REMAINING_BUILD_PLAN.md` first.
2. **Google account + Colab Pro subscription** ($10/mo via
   colab.research.google.com → Upgrade to Pro).
3. **psx-api Python venv** with the deps installed locally. You'll
   need `pandas` + `pyarrow` for the export step. They're already in
   `psx-ingest/pyproject.toml`; if you're using the `psx-api` venv,
   `pip install pandas pyarrow` covers it.

---

## Step 1 — Export training data (local, ~2 minutes)

From the repo root:

```bash
# Default: every active symbol, all available history
python scripts/export_training_data.py

# Or: a quick sanity-check run on just a few symbols
python scripts/export_training_data.py --symbols HBL,UBL,ENGRO --out /tmp/sample.parquet

# Or: limit to the last 5 years
python scripts/export_training_data.py --since 2021-01-01
```

The script:
- Connects to Postgres at `DATABASE_URL` (default
  `postgresql+asyncpg://psx_user:psx_pass@localhost:5432/psx_dev`)
- Loops through every active symbol, builds the 23-feature vector
  used by `psx_api.predictions.features`
- Adds a `y_next_day_up` binary label per row
- Writes a single Parquet file to `data/training/psx_features.parquet`

For 84 symbols × 5 years the output is ~5-10 MB.

---

## Step 2 — Upload the Parquet to Google Drive (~2 minutes)

1. Go to **drive.google.com**
2. Create a folder structure: `MyDrive / psx-ai / training`
3. Drag `data/training/psx_features.parquet` into the `training`
   folder

When you're done, Drive should look like:

```
MyDrive/
└── psx-ai/
    └── training/
        └── psx_features.parquet
```

The notebook expects exactly this path. If you put it somewhere else,
edit the `TRAINING_PARQUET` constant in cell 2.

---

## Step 3 — Open the notebook in Colab (~1 minute)

1. Go to **colab.research.google.com**
2. File → Upload notebook → pick
   `psx-inference/notebooks/train_models.ipynb` from your clone
3. **Runtime → Change runtime type → GPU → T4** (or V100 if offered)
4. Save the notebook back to Drive (File → Save a copy in Drive)

---

## Step 4 — Run the notebook (~5 hours unattended)

1. **Cell 0** (sanity check) — confirm the GPU is visible
2. **Cell 1** (install deps) — ~30 seconds
3. **Cell 2** (mount Drive) — pops a consent dialog the first time
4. **Cell 3** (load data) — should print row count + class balance
5. **Cells 4-5** (training loop) — **this is the long one.** Click run
   and walk away. Colab Pro keeps the kernel alive for up to 24h.
6. **Cell 6** (export to ONNX) — ~5 minutes
7. **Cell 7** (save report)
8. **Cell 8** (sanity-check one model)

If a cell fails halfway through, you can re-run from cell 4 — already-
trained models stay in memory until you disconnect the runtime.

---

## Step 5 — Download the models (~5 minutes)

Once cell 6 finishes:

1. In Drive, navigate to `MyDrive/psx-ai/models/onnx`
2. Right-click the `onnx` folder → **Download** (Drive zips it)
3. Extract the zip on your laptop
4. Move the contents into `psx-inference/models/onnx/` in the repo
5. Commit:

```bash
cd psx-ai-trading-system
git add psx-inference/models/onnx/
git commit -m "feat: trained ML models v1 (heuristic-v0.1.0 → real-v1)"
git push
```

`models/onnx/` is intentionally tracked rather than .gitignored — the
files are small (~30 MB total), reviewable in PRs, and reproducible
from the same notebook.

---

## Step 6 — Wire the inference service (handled in code, see [Step 105])

The inference service (`psx-inference/psx_inference/inference.py`)
loads any models that appear in `models/onnx/` at startup. As long as
the directory structure matches what the notebook emits, you don't
need to write any code — restart the service and inference flips from
heuristic to real models automatically.

To make `psx-api` use the real predictions, set:

```bash
INFERENCE_SERVICE_URL=http://localhost:8001
```

in your `psx-api/.env` and restart `uvicorn psx_api.main:app`.

---

## What's actually trained per symbol

| Sub-model | Library | Role | GPU? |
|---|---|---|---|
| XGBoost | xgboost | Non-linear interactions; mean-reversion bias | No (`tree_method='hist'`) |
| Random Forest | scikit-learn | Trend / robust to outliers | No |
| LSTM (2 layers, hidden=32) | PyTorch | Sequence patterns over a 30-day window | Yes |
| Meta (logistic regression) | scikit-learn | Stacks the 3 sub-model probabilities | No |

Sub-models that fail to beat **53% AUC** on validation are dropped and
the symbol's `predictions_disabled` flag is set to True. The UI already
handles the disabled state via the existing
`psx_api.alerts.pump_dump` / Signal panel components.

## Why ONNX

- One file format means the inference service doesn't need PyTorch *or*
  sklearn at runtime — just `onnxruntime` (10 MB instead of 2 GB)
- CPU inference is fast enough that we don't need a GPU at serve time
- Models are byte-deterministic so reproducibility is straightforward

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `psx_features.parquet` doesn't exist in Drive | Re-check the path; case-sensitive. Should be `MyDrive/psx-ai/training/psx_features.parquet` |
| Cell 3: `class balance: y=1 X%` is wildly off 50% | Confirm `y_next_day_up` is computed against next-day close not next-day open. Should be ~48-52% for PSX |
| LSTM training is extremely slow | Confirm Runtime → GPU is selected; check cell 0 prints `CUDA available: True` |
| `convert_xgboost` import error | Older xgboost versions need `onnxmltools` instead. The notebook pins the working versions |
| Colab disconnects after 90 min | Either keep a tab open and active, or pay for Pro (gets 24h background) |
| Some symbols `predictions_disabled='only X rows'` | Symbol doesn't have enough OHLCV history yet. Either backfill more data or accept the disabled state |

If you hit anything else, the training report CSV
(`models/onnx/training_report.csv`) has per-symbol diagnostics.
