"""Ingestion pipeline ported from notebook/ingestion.ipynb."""

from __future__ import annotations

from typing import Any

import pandas as pd

from services.bootstrap import get_logger
from Drug_EDA.exception import customexception, format_error, raise_custom

logger = get_logger("services.ingestion")

ACTIVATION_COLUMNS = [
    "storeid",
    "company",
    "serial",
    "acttype",
    "plancode",
    "plantype1",
]

OUTPUT_COLUMNS = ACTIVATION_COLUMNS + ["Compensation", "Rebate", "Chargeback"]


def _read_csv(path: str, encoding: str = "latin1") -> pd.DataFrame:
    logger.debug("Reading CSV: %s (encoding=%s)", path, encoding)
    try:
        df = pd.read_csv(path, encoding=encoding)
        logger.info("Read %s: %d rows, %d columns", path, len(df), len(df.columns))
        return df
    except UnicodeDecodeError:
        logger.warning("UnicodeDecodeError for %s; detecting encoding with chardet", path)
        import chardet

        with open(path, "rb") as f:
            detected = chardet.detect(f.read())

        fallback = detected.get("encoding") or encoding
        logger.info("Retrying %s with encoding=%s", path, fallback)

        df = pd.read_csv(path, encoding=fallback)
        logger.info("Read %s: %d rows after fallback encoding", path, len(df))
        return df

    except Exception as exc:
        logger.exception("Failed to read CSV: %s", path)
        raise_custom(exc)


def _normalize_esn(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(r"\D", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").astype("Int64")


def run_ingestion(
    activation_path: str,
    cur_callidus_path: str,
    callidus_detail_path: str,
    encoding: str = "latin1",
    store_ids: list[str] | None = None,
) -> pd.DataFrame:
    """
    Run the activation + Callidus merge pipeline.

    Returns dataframe with Compensation and Chargeback columns.
    """
    logger.info(
        "Starting ingestion activation=%s cur_callidus=%s callidus=%s store_filter=%s",
        activation_path,
        cur_callidus_path,
        callidus_detail_path,
        store_ids,
    )

    try:
        activation = _read_csv(activation_path, encoding=encoding)
        cur_callidus = _read_csv(cur_callidus_path, encoding=encoding)
        callidus_detail = _read_csv(callidus_detail_path, encoding=encoding)

        useful = activation[ACTIVATION_COLUMNS].copy()

        before_voice = len(useful)
        useful = useful[useful["plantype1"] == "Voice"]

        logger.info("Filtered Voice rows: %d -> %d", before_voice, len(useful))

        useful["serial"] = useful["serial"].astype(str).str.replace(
            r"\D", "", regex=True
        )
        useful["serial"] = useful["serial"].astype(int)

        dupes = useful["serial"].value_counts()
        dupes = dupes[dupes > 1]

        if not dupes.empty:
            logger.warning(
                "Duplicate serial numbers found: %s",
                dupes.index.tolist(),
            )

        chargeback_rows = cur_callidus[
            cur_callidus["transaction_type_desc"].str.contains(
                "charge",
                case=False,
                na=False,
            )
        ].copy()

        chargeback_rows["esn"] = _normalize_esn(chargeback_rows["esn"])

        chargeback_dict = (
            chargeback_rows.dropna(subset=["esn"])
            .set_index("esn")["transaction_type_desc"]
            .to_dict()
        )

        logger.info("Chargeback dict entries: %d", len(chargeback_dict))

        # edit here to make Rebate

        callidus_detail = callidus_detail.copy()
        callidus_detail["esn"] = _normalize_esn(callidus_detail["esn"])

        # Sum all transaction_amount values per ESN
        transaction_per_esn = (
            callidus_detail.groupby("esn", as_index=False)["transaction_amount"]
            .sum()
        )

        compensation_map = (
            transaction_per_esn
            .set_index("esn")["transaction_amount"]
        )

        useful["Compensation"] = (
            useful["serial"]
            .map(compensation_map)
            .fillna(0.00)
            .astype(float)
            .round(2)
        )

        useful["Chargeback"] = useful["serial"].map(chargeback_dict)

        # Placeholder Rebate column
        useful["Rebate"] = 0.00

        if store_ids:
            before = len(useful)

            useful = useful[useful["storeid"].isin(store_ids)]

            logger.info(
                "Store filter %s: %d -> %d rows",
                store_ids,
                before,
                len(useful),
            )

        result = useful[OUTPUT_COLUMNS].copy()

        # create total_rebate = float(result["Rebate"].sum())
        total_comp = float(result["Compensation"].sum())
        chargebacks = int(result["Chargeback"].notna().sum())

        logger.info(
            "Ingestion complete: rows=%d total_compensation=%.2f chargebacks=%d",
            len(result),
            total_comp,
            chargebacks,
        )

        return result

    except customexception:
        raise

    except Exception as exc:
        logger.exception("Ingestion failed")
        raise_custom(exc)


def build_summary(
    df: pd.DataFrame,
    year: int,
    month: int,
    manager_email: str,
) -> dict[str, Any]:
    """Build dashboard summary JSON payload."""

    logger.debug(
        "Building summary for %04d-%02d manager=%s",
        year,
        month,
        manager_email,
    )

    try:
        by_store = (
            df.groupby("storeid", as_index=False)["Compensation"]
            .sum()
            .sort_values("Compensation", ascending=False)
        )

        summary = {
            "year": year,
            "month": month,
            "manager_email": manager_email,
            "total_compensation": float(df["Compensation"].sum()),
            "activation_count": int(len(df)),
            "chargeback_count": int(df["Chargeback"].notna().sum()),
            "by_store": by_store.to_dict(orient="records"),
        }

        logger.info("Summary built: %s", summary)

        return summary

    except Exception as exc:
        logger.exception("build_summary failed")
        raise_custom(exc)