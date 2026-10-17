"""Shared dataset validation for extraction and retrieval (standard library only)."""

import json
from pathlib import Path

DATA_PATH = Path(__file__).with_name("faculty_data.json")


def load_faculty_database(path=DATA_PATH):
    """Load usable records or raise a clear ValueError; null optional fields are OK."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read faculty dataset {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("faculty"), list):
        raise ValueError("Dataset must contain a 'faculty' list.")
    records = data["faculty"]
    if not records:
        raise ValueError("Faculty dataset is empty.")
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Faculty record {index + 1} must be an object.")
        for field in ("id", "name"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError(f"Faculty record {index + 1} needs a nonempty {field}.")
        if record["id"] in seen:
            raise ValueError(f"Duplicate faculty ID: {record['id']}")
        seen.add(record["id"])
        keywords = record.get("keywords")
        if not isinstance(keywords, list) or any(
            not isinstance(k, str) or not k.strip() for k in keywords
        ):
            raise ValueError(f"Invalid keywords for {record['id']}; expected a list of text.")
        for field in ("title", "research_area", "technical_summary", "plain_summary",
                      "lab_name", "lab_url"):
            if record.get(field) is not None and not isinstance(record[field], str):
                raise ValueError(f"Invalid {field} for {record['id']}; expected text or null.")
    return records


def vocabulary(records):
    return sorted({k.strip().lower() for p in records for k in p["keywords"]})
