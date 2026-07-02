#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scale index.py pour traiter directement le format CHANDRA (liste plate)
et produire un JSON de meme structure, enrichi avec les "persons" trouves.

Usage:
    python3 app/index_gt.py \
        --json app/2026-07-01-CHANDRA-GT-NEL-SPK_PER.json \
        --output-json app/2026-07-01-CHANDRA-GT-NEL-SPK_PER-linked.json
"""

from __future__ import annotations

import argparse
import json
import time as time_module
from collections import defaultdict
from typing import Any

from index import DecidonSearchEngine, group_results_by_person


def load_chandra_list(filename: str) -> list[dict[str, Any]]:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Le fichier CHANDRA doit avoir une liste en racine.")

    return data


def run_chandra_scaled(
    filename: str,
    bool_type: str = "AND",
    limit: int = 10,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    entities = load_chandra_list(filename)

    by_date: dict[str, list[int]] = defaultdict(list)
    for idx, item in enumerate(entities):
        session_date = item.get("date")
        by_date[session_date].append(idx)

    print(f"{len(entities)} entites, {len(by_date)} dates distinctes")
    print(f"bool_type={bool_type}  limit={limit}")

    engine = DecidonSearchEngine(bool_type=bool_type)

    start = time_module.time()
    total_results = 0
    empty_queries = 0

    try:
        for session_date, indices in by_date.items():
            print(f"-- session_date={session_date} ({len(indices)} entites) --")

            for idx in indices:
                item = entities[idx]
                text_value = (item.get("entity") or "").strip()

                if not text_value:
                    item["persons"] = []
                    empty_queries += 1
                    continue

                raw_results = engine.search(
                    text_value,
                    session_date=session_date,
                    limit=limit,
                )
                persons = group_results_by_person(raw_results)
                item["persons"] = persons

                total_results += len(persons)
                if not persons:
                    empty_queries += 1

                if verbose:
                    print(f"  uuid={item.get('uuid')!r} text={text_value!r} "
                          f"-> {len(persons)} personne(s)")

    finally:
        engine.close()

    end = time_module.time()

    print(f"Temps total : {end - start:.2f} secondes")
    print(f"Temps moyen / entite : {(end - start) / max(len(entities), 1):.4f} secondes")
    print(f"Resultats retournes : {total_results}")
    print(f"Entites sans resultat : {empty_queries}")

    return entities


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scale du moteur de recherche DECIDON pour le format CHANDRA plat."
    )
    parser.add_argument("--json", type=str, required=True)
    parser.add_argument("--output-json", type=str, required=True)
    parser.add_argument("--bool-type", type=str, choices=["AND", "OR"], default="AND")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    output = run_chandra_scaled(
        filename=args.json,
        bool_type=args.bool_type,
        limit=args.limit,
        verbose=args.verbose,
    )

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Resultats JSON ecrits dans : {args.output_json}")


if __name__ == "__main__":
    main()