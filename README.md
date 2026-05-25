# Metro earnings

Streamlit app for store managers to upload Metro sales CSVs, run the ingestion pipeline from `notebook/ingestion.ipynb`, and view monthly compensation dashboards.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run streamlit_app.py
```

## Auth flow

1. **Store owner signup** — register owner email, store IDs, and manager emails (whitelist).
2. **Store manager signup** — manager email must appear on an owner's whitelist.
3. **Store manager login** — managers upload files, process data, preview downloads, and view dashboards.

User accounts are stored locally in `data/users.json` (not committed).

## Data layout

| Path | Purpose |
|------|---------|
| `uploads/raw/YYYY-MM/` | Three uploaded CSVs per analysis month |
| `uploads/processed/YYYY-MM/` | `merged_activations.csv`, `summary.json`, `manifest.json` |

On logout, everything under `uploads/` is deleted **except** `uploads/processed/`.

## Logging and errors

The app uses `src/Drug_EDA/logger.py` and `src/Drug_EDA/exception.py`:

- **Logs** are written to `logs/` (timestamped `.log` file) and echoed to the console.
- In the Streamlit sidebar, open **Activity log (this session)** to see recent log lines.
- Failures show a clear message in the UI; full details (file, line number) are in the log file.

Successful steps (signup, login, upload, process, dashboard load) are logged at `INFO`; validation failures at `WARNING`; crashes at `ERROR` with stack traces.

## Raw file names (per month folder)

- `ActivationDetailReport.csv`
- `curCallidus.csv`
- `CallidusDetail.csv`
