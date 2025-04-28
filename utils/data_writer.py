from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd


# --------------------------------------------------------------------------- #
#  Canonical list of CSV columns                                              #
# --------------------------------------------------------------------------- #
def get_required_fields() -> List[str]:
    return [
        "Project Name",
        "Project Price per SFT",
        "total Price",
        "Possession (Year & Month)",
        "Location",
        "Builder Reputation & Legal Compliance",
        "Property Type & Space Utilization",
        "Open Space",                       # 🆕 exact open-space %
        "Safety & Security",
        "Quality of Construction",
        "Home Loan & Financing Options",
        "Orientation",
        "Configuration (2BHK, 3BHK, etc.)",
        "Source URLs",
        "Why"
    ]


# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #
def _flatten(row: Dict[str, Any]) -> Dict[str, str]:
    """Convert lists/dicts to strings so they fit in CSV cells."""
    flat: Dict[str, str] = {}
    for key in get_required_fields():
        value = row.get(key, "Information not available")
        if isinstance(value, dict):
            flat[key] = ", ".join(f"{k}: {v}" for k, v in value.items())
        elif isinstance(value, list):
            flat[key] = ", ".join(map(str, value))
        else:
            flat[key] = str(value)
    return flat


def ensure_csv_structure(path: str) -> None:
    """Create the CSV or add any columns that are missing."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    required = get_required_fields()

    if not os.path.isfile(path):
        # brand‑new file → just write header
        with open(path, "w", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=required).writeheader()
        return

    # File exists – check for missing columns
    df = pd.read_csv(path)
    missing = [c for c in required if c not in df.columns]
    if missing:
        for col in missing:
            df[col] = "Information not available"
        df.to_csv(path, index=False)


# --------------------------------------------------------------------------- #
#  Public helpers                                                             #
# --------------------------------------------------------------------------- #
def write_to_csv(row: Dict[str, Any], path: str) -> None:
    """Append *row* to *path*, patching the header if needed."""
    ensure_csv_structure(path)  # <‑‑ guarantees header is up‑to‑date

    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=get_required_fields())
        writer.writerow(_flatten(row))


def write_error_log(
    project_name: str,
    message: str,
    path: str = "output/error_log.csv",
) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file_exists = os.path.isfile(path)

    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["Project Name", "Error Message", "Timestamp"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "Project Name": project_name,
                "Error Message": message,
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
