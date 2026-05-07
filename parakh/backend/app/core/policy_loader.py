from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_evaluation_criteria() -> list[dict[str, str]]:
    settings = get_settings()
    return _read_csv(settings.fixtures_root / "evaluation_criteria.csv")


def load_bidder_doc_checklist() -> list[dict[str, str]]:
    settings = get_settings()
    return _read_csv(settings.fixtures_root / "bidder_doc_checklist.csv")


def load_disqualification_factors() -> list[dict[str, str]]:
    settings = get_settings()
    return _read_csv(settings.fixtures_root / "disqualification_factors.csv")


def build_disqualification_rules() -> list[dict[str, Any]]:
    rows = load_disqualification_factors()
    rules: list[dict[str, Any]] = []
    for row in rows:
        category = row["Category"].strip().lower().replace(" ", "_")
        rule_id = f"{category}_{len(rules) + 1}"
        rules.append(
            {
                "rule_id": rule_id,
                "category": row["Category"],
                "trigger": row["DisqualificationTrigger"],
                "impact": row["Impact"],
            }
        )
    return rules


def load_policy() -> dict[str, Any]:
    settings = get_settings()
    policy_path = settings.fixtures_root / "policy.yaml"
    with policy_path.open("r", encoding="utf-8") as handle:
        policy = yaml.safe_load(handle) or {}
    policy["disqualification_rules"] = build_disqualification_rules()
    return policy
