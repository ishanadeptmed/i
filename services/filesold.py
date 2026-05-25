"""File paths, uploads, processed outputs, and logout cleanup."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from config import (
    PROCESSED_FOLDER,
    PROCESSED_MANIFEST_NAME,
    PROCESSED_MERGED_NAME,
    PROCESSED_SUMMARY_NAME,
    RAW_ACTIVATION_NAME,
    RAW_CALLIDUS_DETAIL_NAME,
    RAW_CUR_CALLIDUS_NAME,
    RAW_FOLDER,
    UPLOAD_FOLDER,
)
from services.bootstrap import get_logger
from Drug_EDA.exception import customexception, format_error, raise_custom
from services.ingestion import build_summary, run_ingestion

logger = get_logger("services.files")

RAW_FILE_NAMES = {
    "activation": RAW_ACTIVATION_NAME,
    "cur_callidus": RAW_CUR_CALLIDUS_NAME,
    "callidus_detail": RAW_CALLIDUS_DETAIL_NAME,
}


def period_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def raw_period_dir(year: int, month: int) -> str:
    path = os.path.join(RAW_FOLDER, period_key(year, month))
    os.makedirs(path, exist_ok=True)
    return path


def processed_period_dir(year: int, month: int) -> str:
    path = os.path.join(PROCESSED_FOLDER, period_key(year, month))
    os.makedirs(path, exist_ok=True)
    return path


def raw_paths(year: int, month: int) -> dict[str, str]:
    base = raw_period_dir(year, month)
    return {key: os.path.join(base, name) for key, name in RAW_FILE_NAMES.items()}


def save_uploaded_file(uploaded_file, dest_path: str) -> None:
    logger.info("Saving upload to %s", dest_path)
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        logger.info("Saved upload: %s (%d bytes)", dest_path, os.path.getsize(dest_path))
    except Exception as exc:
        logger.exception("Failed to save upload to %s", dest_path)
        raise_custom(exc)


def list_available_periods() -> list[str]:
    periods: set[str] = set()
    for root_name in (RAW_FOLDER, PROCESSED_FOLDER):
        if not os.path.isdir(root_name):
            continue
        for name in os.listdir(root_name):
            full = os.path.join(root_name, name)
            if os.path.isdir(full) and len(name) == 7 and name[4] == "-":
                periods.add(name)
    result = sorted(periods, reverse=True)
    logger.debug("Available periods: %s", result)
    return result


def parse_period(period: str) -> tuple[int, int]:
    year_str, month_str = period.split("-", 1)
    return int(year_str), int(month_str)


def process_period(
    year: int,
    month: int,
    manager_email: str,
    store_ids: list[str],
) -> tuple[bool, str]:
    pk = period_key(year, month)
    logger.info("Processing period %s for manager=%s", pk, manager_email)
    paths = raw_paths(year, month)
    missing = [p for p in paths.values() if not os.path.isfile(p)]
    if missing:
        logger.warning("Missing raw files for %s: %s", pk, missing)
        return False, f"Missing raw files for {pk}: upload all three CSVs first."

    try:
        df = run_ingestion(
            paths["activation"],
            paths["cur_callidus"],
            paths["callidus_detail"],
            store_ids=store_ids,
        )
    except customexception as exc:
        logger.exception("Processing failed for %s", pk)
        return False, str(exc)
    except Exception as exc:
        logger.exception("Processing failed for %s", pk)
        return False, format_error(exc)

    try:
        out_dir = processed_period_dir(year, month)
        merged_path = os.path.join(out_dir, PROCESSED_MERGED_NAME)
        df.to_csv(merged_path, index=False)
        logger.info("Wrote merged CSV: %s", merged_path)

        summary = build_summary(df, year, month, manager_email)
        summary["processed_at"] = datetime.now(timezone.utc).isoformat()
        summary_path = os.path.join(out_dir, PROCESSED_SUMMARY_NAME)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        logger.info("Wrote summary: %s", summary_path)

        manifest = {
            "period": pk,
            "raw_files": {k: os.path.basename(v) for k, v in paths.items()},
            "processed_files": [PROCESSED_MERGED_NAME, PROCESSED_SUMMARY_NAME],
        }
        manifest_path = os.path.join(out_dir, PROCESSED_MANIFEST_NAME)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        logger.info("Wrote manifest: %s", manifest_path)

        msg = f"Processed {len(df)} activations for {pk}."
        logger.info(msg)
        return True, msg
    except Exception as exc:
        logger.exception("Failed to write processed outputs for %s", pk)
        return False, format_error(exc)


def load_summary(period: str) -> dict[str, Any] | None:
    path = os.path.join(PROCESSED_FOLDER, period, PROCESSED_SUMMARY_NAME)
    if not os.path.isfile(path):
        logger.debug("No summary at %s", path)
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Loaded summary for %s", period)
        return data
    except Exception as exc:
        logger.exception("Failed to load summary %s", path)
        raise_custom(exc)


def load_merged_csv(period: str) -> pd.DataFrame | None:
    path = os.path.join(PROCESSED_FOLDER, period, PROCESSED_MERGED_NAME)
    if not os.path.isfile(path):
        logger.debug("No merged CSV at %s", path)
        return None
    try:
        df = pd.read_csv(path)
        logger.debug("Loaded merged CSV for %s: %d rows", period, len(df))
        return df
    except Exception as exc:
        logger.exception("Failed to load merged CSV %s", path)
        raise_custom(exc)


def read_file_bytes(path: str) -> bytes | None:
    if not os.path.isfile(path):
        logger.warning("File not found for download: %s", path)
        return None
    try:
        with open(path, "rb") as f:
            data = f.read()
        logger.debug("Read %d bytes from %s", len(data), path)
        return data
    except Exception as exc:
        logger.exception("Failed to read file %s", path)
        raise_custom(exc)


def list_period_files(period: str) -> list[tuple[str, str]]:
    """Return (label, absolute_path) for downloadable files in a period."""
    files: list[tuple[str, str]] = []
    raw_dir = os.path.join(RAW_FOLDER, period)
    if os.path.isdir(raw_dir):
        for name in sorted(os.listdir(raw_dir)):
            full = os.path.join(raw_dir, name)
            if os.path.isfile(full):
                files.append((f"raw/{name}", full))

    proc_dir = os.path.join(PROCESSED_FOLDER, period)
    if os.path.isdir(proc_dir):
        for name in sorted(os.listdir(proc_dir)):
            full = os.path.join(proc_dir, name)
            if os.path.isfile(full):
                files.append((f"processed/{name}", full))
    logger.debug("Period %s files: %s", period, [f[0] for f in files])
    return files


def cleanup_on_logout() -> None:
    """Delete everything under uploads/ except processed/."""
    logger.info("Logout cleanup: removing non-processed uploads")
    if not os.path.isdir(UPLOAD_FOLDER):
        return
    for name in os.listdir(UPLOAD_FOLDER):
        if name == "processed":
            continue
        path = os.path.join(UPLOAD_FOLDER, name)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
            logger.info("Removed directory: %s", path)
        else:
            try:
                os.remove(path)
                logger.info("Removed file: %s", path)
            except OSError as exc:
                logger.warning("Could not remove %s: %s", path, exc)
    os.makedirs(RAW_FOLDER, exist_ok=True)
    logger.info("Logout cleanup complete")


def tail_log_file(log_path: str, lines: int = 40) -> str:
    """Return last N lines of the log file for in-app display."""
    if not os.path.isfile(log_path):
        return "(no log file yet)"
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            content = f.readlines()
        return "".join(content[-lines:]) if content else "(empty log)"
    except Exception as exc:
        logger.exception("Failed to read log tail")
        return format_error(exc)
