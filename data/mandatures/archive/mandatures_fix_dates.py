"""
fix_dates_from_wikidata.py
==========================
Pour chaque gouvernement dans mandature.csv qui a un wikidata_qid,
récupère les dates officielles depuis Wikidata et met à jour
from_date et to_date si elles diffèrent.

Usage
-----
    pip install requests
    python fix_dates_from_wikidata.py
    python fix_dates_from_wikidata.py --input mandature.csv --output mandature.csv
    python fix_dates_from_wikidata.py --dry-run   # affiche les différences sans modifier
"""

import csv
import json
import time
import argparse
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

WIKIDATA_API = "https://www.wikidata.org/w/api.php"


def get_dates_from_wikidata(qid: str) -> tuple[str, str]:
    """
    Récupère les dates de début (P571 ou P580) et de fin (P576 ou P582)
    d'une entité Wikidata. Retourne (from_date, to_date) au format YYYY-MM-DD.
    """
    params = urlencode({
        "action": "wbgetentities",
        "ids": qid,
        "props": "claims",
        "format": "json"
    })
    url = f"{WIKIDATA_API}?{params}"
    req = Request(url, headers={"User-Agent": "prosopographie-3rep/1.0"})

    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError) as e:
        print(f"    Erreur réseau : {e}")
        return "", ""

    claims = data.get("entities", {}).get(qid, {}).get("claims", {})

    def extract_date(prop_list):
        """Essaie plusieurs propriétés et retourne la première date trouvée."""
        for prop in prop_list:
            if prop in claims:
                try:
                    raw = claims[prop][0]["mainsnak"]["datavalue"]["value"]["time"]
                    # Format Wikidata : +1886-01-09T00:00:00Z
                    return raw[1:11]  # → YYYY-MM-DD
                except (KeyError, IndexError):
                    continue
        return ""

    from_date = extract_date(["P571", "P580"])  # fondation ou début
    to_date   = extract_date(["P576", "P582"])  # dissolution ou fin

    return from_date, to_date


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",   default="mandature.csv")
    parser.add_argument("--output",  default="mandature.csv")
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche les différences sans modifier le fichier")
    args = parser.parse_args()

    print("\n  Correction des dates depuis Wikidata")
    print("  " + "─" * 42)
    if args.dry_run:
        print("  Mode dry-run — aucune modification ne sera écrite\n")

    with open(args.input, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fieldnames = list(rows[0].keys())

    corrected  = 0
    unchanged  = 0
    no_qid     = 0
    no_dates   = 0

    for row in rows:
        if row["type"] != "gouvernement":
            continue

        qid = row.get("wikidata_qid", "").strip()
        if not qid:
            no_qid += 1
            continue

        wd_from, wd_to = get_dates_from_wikidata(qid)

        if not wd_from and not wd_to:
            no_dates += 1
            print(f"  ⚠️  {row['nom']} ({qid}) — aucune date sur Wikidata")
            time.sleep(0.2)
            continue

        csv_from = row.get("from_date", "").strip()
        csv_to   = row.get("to_date",   "").strip()

        changed = False
        changes = []

        if wd_from and wd_from != csv_from:
            changes.append(f"from {csv_from} → {wd_from}")
            if not args.dry_run:
                row["from_date"] = wd_from
            changed = True

        if wd_to and wd_to != csv_to:
            changes.append(f"to {csv_to} → {wd_to}")
            if not args.dry_run:
                row["to_date"] = wd_to
            changed = True

        if changed:
            corrected += 1
            print(f"  ✓  {row['nom']:<45} {' | '.join(changes)}")
        else:
            unchanged += 1

        time.sleep(0.2)  # respecter le rate limit Wikidata

    # Écriture
    if not args.dry_run:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"\n  ── Résumé ───────────────────────────────")
    print(f"  Dates corrigées  : {corrected}")
    print(f"  Dates correctes  : {unchanged}")
    print(f"  Sans QID         : {no_qid}")
    print(f"  Sans dates Wikidata : {no_dates}")
    if not args.dry_run:
        print(f"\n  Fichier mis à jour : {args.output}")
    print()


if __name__ == "__main__":
    main()
