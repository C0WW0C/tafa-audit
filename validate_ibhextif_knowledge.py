#!/usr/bin/env python3
"""Validate core references in the local Ibhextif knowledge registry."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "knowledge"


def load_yaml(name: str) -> dict:
    path = KB / name
    if not path.is_file():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{name}: expected mapping")
    return data


def ids(items: list[dict]) -> set[str]:
    return {str(item["id"]) for item in items if isinstance(item, dict) and item.get("id")}


def main() -> int:
    errors: list[str] = []
    sources = load_yaml("sources.yaml").get("sources", [])
    documents = load_yaml("documents.yaml").get("documents", [])
    concepts = load_yaml("concepts.yaml").get("concepts", [])
    strategies = load_yaml("strategies.yaml").get("strategies", [])
    backtests = load_yaml("backtests.yaml").get("backtests", [])

    source_ids, document_ids, concept_ids, strategy_ids = ids(sources), ids(documents), ids(concepts), ids(strategies)
    for doc in documents:
        if doc.get("source_id") not in source_ids:
            errors.append(f"document {doc.get('id')} references unknown source")
        locator = ROOT / str(doc.get("source_locator", ""))
        if not locator.is_file():
            errors.append(f"document {doc.get('id')} locator missing: {locator}")
        if not doc.get("content_hash"):
            errors.append(f"document {doc.get('id')} has no content hash")
    for strategy in strategies:
        for concept_id in strategy.get("related_concepts", []):
            if concept_id not in concept_ids:
                errors.append(f"strategy {strategy.get('id')} references unknown concept {concept_id}")
    for backtest in backtests:
        if backtest.get("strategy_id") not in strategy_ids:
            errors.append(f"backtest {backtest.get('id')} references unknown strategy")
        for field in ("code_document_id", "dataset_document_id"):
            if backtest.get(field) not in document_ids:
                errors.append(f"backtest {backtest.get('id')} references unknown {field}")
    if errors:
        print("IBHEXTIF KNOWLEDGE: FAILED")
        for error in errors:
            print(" -", error)
        return 1
    print(
        "IBHEXTIF KNOWLEDGE: PASSED "
        f"sources={len(source_ids)} documents={len(document_ids)} "
        f"concepts={len(concept_ids)} strategies={len(strategy_ids)} backtests={len(backtests)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
