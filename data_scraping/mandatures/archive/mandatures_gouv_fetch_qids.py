"""
fetch_qids_wikipedia.py
=======================
Récupère les QIDs Wikidata des gouvernements de la IIIe République
via l'API Wikipedia (qui retourne le QID directement pour chaque page).

Usage
-----
    pip install requests
    python fetch_qids_wikipedia.py
    python fetch_qids_wikipedia.py --input mandature.csv --output mandature.csv

Logique
-------
Pour chaque gouvernement sans QID dans le CSV, on essaie plusieurs
variantes du titre Wikipedia (ex: "Gouvernement Léon Gambetta",
"Gouvernement Gambetta", etc.) jusqu'à trouver une page qui existe,
puis on récupère son QID via l'API Wikidata sitelinks.
"""

import csv
import json
import time
import argparse
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote
from urllib.error import URLError, HTTPError

WIKIPEDIA_API = "https://fr.wikipedia.org/api/rest_v1/page/summary/"
WIKIDATA_API  = "https://www.wikidata.org/w/api.php"

# Mapping manuel nom CSV → titre Wikipedia exact
# (pour les cas où le titre diffère du nom dans le CSV)
TITLE_OVERRIDES = {
    "Gouvernement Gambetta":            "Gouvernement Léon Gambetta",
    "Gouvernement de Freycinet (2)":    "Gouvernement Charles de Freycinet (2)",
    "Gouvernement de Freycinet (3)":    "Gouvernement Charles de Freycinet (3)",
    "Gouvernement de Freycinet (4)":    "Gouvernement Charles de Freycinet (4)",
    "Gouvernement Duclerc":             "Gouvernement Charles Duclerc",
    "Gouvernement Fallières":           "Gouvernement Armand Fallières",
    "Gouvernement Ferry (2)":           "Gouvernement Jules Ferry (2)",
    "Gouvernement Brisson (1)":         "Gouvernement Henri Brisson (1)",
    "Gouvernement Brisson (2)":         "Gouvernement Henri Brisson (2)",
    "Gouvernement Goblet":              "Gouvernement René Goblet",
    "Gouvernement Rouvier (1)":         "Gouvernement Maurice Rouvier (1)",
    "Gouvernement Rouvier (2)":         "Gouvernement Maurice Rouvier (2)",
    "Gouvernement Rouvier (3)":         "Gouvernement Maurice Rouvier (3)",
    "Gouvernement Tirard (1)":          "Gouvernement Pierre Tirard (1)",
    "Gouvernement Tirard (2)":          "Gouvernement Pierre Tirard (2)",
    "Gouvernement Floquet":             "Gouvernement Charles Floquet",
    "Gouvernement Loubet":              "Gouvernement Émile Loubet",
    "Gouvernement Ribot (1)":           "Gouvernement Alexandre Ribot (1)",
    "Gouvernement Ribot (2)":           "Gouvernement Alexandre Ribot (2)",
    "Gouvernement Ribot (3)":           "Gouvernement Alexandre Ribot (3)",
    "Gouvernement Ribot (4)":           "Gouvernement Alexandre Ribot (4)",
    "Gouvernement Ribot (5)":           "Gouvernement Alexandre Ribot (5)",
    "Gouvernement Dupuy (1)":           "Gouvernement Charles Dupuy (1)",
    "Gouvernement Dupuy (2)":           "Gouvernement Charles Dupuy (2)",
    "Gouvernement Dupuy (3)":           "Gouvernement Charles Dupuy (3)",
    "Gouvernement Dupuy (4)":           "Gouvernement Charles Dupuy (4)",
    "Gouvernement Dupuy (5)":           "Gouvernement Charles Dupuy (5)",
    "Gouvernement Casimir-Perier":      "Gouvernement Jean Casimir-Perier",
    "Gouvernement Bourgeois":           "Gouvernement Léon Bourgeois",
    "Gouvernement Méline":              "Gouvernement Jules Méline",
    "Gouvernement Waldeck-Rousseau":    "Gouvernement Pierre Waldeck-Rousseau",
    "Gouvernement Combes":              "Gouvernement Émile Combes",
    "Gouvernement Sarrien":             "Gouvernement Ferdinand Sarrien",
    "Gouvernement Clemenceau (1)":      "Gouvernement Georges Clemenceau (1)",
    "Gouvernement Clemenceau (2)":      "Gouvernement Georges Clemenceau (2)",
    "Gouvernement Briand (1)":          "Gouvernement Aristide Briand (1)",
    "Gouvernement Briand (2)":          "Gouvernement Aristide Briand (2)",
    "Gouvernement Briand (3)":          "Gouvernement Aristide Briand (3)",
    "Gouvernement Briand (4)":          "Gouvernement Aristide Briand (4)",
    "Gouvernement Briand (5)":          "Gouvernement Aristide Briand (5)",
    "Gouvernement Briand (6)":          "Gouvernement Aristide Briand (6)",
    "Gouvernement Briand (7)":          "Gouvernement Aristide Briand (7)",
    "Gouvernement Briand (8)":          "Gouvernement Aristide Briand (8)",
    "Gouvernement Briand (9)":          "Gouvernement Aristide Briand (9)",
    "Gouvernement Briand (10)":         "Gouvernement Aristide Briand (10)",
    "Gouvernement Briand (11)":         "Gouvernement Aristide Briand (11)",
    "Gouvernement Monis":               "Gouvernement Ernest Monis",
    "Gouvernement Caillaux":            "Gouvernement Joseph Caillaux",
    "Gouvernement Poincaré (1)":        "Gouvernement Raymond Poincaré (1)",
    "Gouvernement Poincaré (2)":        "Gouvernement Raymond Poincaré (2)",
    "Gouvernement Poincaré (3)":        "Gouvernement Raymond Poincaré (3)",
    "Gouvernement Poincaré (4)":        "Gouvernement Raymond Poincaré (4)",
    "Gouvernement Poincaré (5)":        "Gouvernement Raymond Poincaré (5)",
    "Gouvernement Barthou":             "Gouvernement Louis Barthou",
    "Gouvernement Doumergue (1)":       "Gouvernement Gaston Doumergue (1)",
    "Gouvernement Doumergue (2)":       "Gouvernement Gaston Doumergue (2)",
    "Gouvernement Viviani (1)":         "Gouvernement René Viviani (1)",
    "Gouvernement Viviani (2)":         "Gouvernement René Viviani (2)",
    "Gouvernement Painlevé (1)":        "Gouvernement Paul Painlevé (1)",
    "Gouvernement Painlevé (2)":        "Gouvernement Paul Painlevé (2)",
    "Gouvernement Painlevé (3)":        "Gouvernement Paul Painlevé (3)",
    "Gouvernement Millerand (1)":       "Gouvernement Alexandre Millerand (1)",
    "Gouvernement Millerand (2)":       "Gouvernement Alexandre Millerand (2)",
    "Gouvernement Leygues":             "Gouvernement Georges Leygues",
    "Gouvernement François-Marsal":     "Gouvernement Frédéric François-Marsal",
    "Gouvernement Herriot (1)":         "Gouvernement Édouard Herriot (1)",
    "Gouvernement Herriot (2)":         "Gouvernement Édouard Herriot (2)",
    "Gouvernement Herriot (3)":         "Gouvernement Édouard Herriot (3)",
    "Gouvernement Tardieu (1)":         "Gouvernement André Tardieu (1)",
    "Gouvernement Tardieu (2)":         "Gouvernement André Tardieu (2)",
    "Gouvernement Tardieu (3)":         "Gouvernement André Tardieu (3)",
    "Gouvernement Chautemps (1)":       "Gouvernement Camille Chautemps (1)",
    "Gouvernement Chautemps (2)":       "Gouvernement Camille Chautemps (2)",
    "Gouvernement Chautemps (3)":       "Gouvernement Camille Chautemps (3)",
    "Gouvernement Chautemps (4)":       "Gouvernement Camille Chautemps (4)",
    "Gouvernement Steeg":               "Gouvernement Théodore Steeg",
    "Gouvernement Laval (1)":           "Gouvernement Pierre Laval (1)",
    "Gouvernement Laval (2)":           "Gouvernement Pierre Laval (2)",
    "Gouvernement Laval (3)":           "Gouvernement Pierre Laval (3)",
    "Gouvernement Laval (4)":           "Gouvernement Pierre Laval (4)",
    "Gouvernement Flandin (1)":         "Gouvernement Pierre-Étienne Flandin",
    "Gouvernement Bouisson":            "Gouvernement Fernand Bouisson",
    "Gouvernement Sarraut (1)":         "Gouvernement Albert Sarraut (1)",
    "Gouvernement Sarraut (2)":         "Gouvernement Albert Sarraut (2)",
    "Gouvernement Paul-Boncour":        "Gouvernement Joseph Paul-Boncour",
    "Gouvernement Daladier (1)":        "Gouvernement Édouard Daladier (1)",
    "Gouvernement Daladier (2)":        "Gouvernement Édouard Daladier (2)",
    "Gouvernement Daladier (3)":        "Gouvernement Édouard Daladier (3)",
    "Gouvernement Daladier (4)":        "Gouvernement Édouard Daladier (4)",
    "Gouvernement Daladier (5)":        "Gouvernement Édouard Daladier (5)",
    "Gouvernement Blum (1)":            "Gouvernement Léon Blum (1)",
    "Gouvernement Blum (2)":            "Gouvernement Léon Blum (2)",
    "Gouvernement Reynaud":             "Gouvernement Paul Reynaud",
    "Gouvernement Pétain":              "Gouvernement Philippe Pétain",
}


def get_qid_from_wikipedia(title: str) -> str | None:
    """
    Récupère le QID Wikidata d'une page Wikipedia française via l'API REST.
    Retourne None si la page n'existe pas ou n'a pas de QID.
    """
    url = WIKIPEDIA_API + quote(title.replace(" ", "_"))
    req = Request(url, headers={"User-Agent": "prosopographie-3rep/1.0"})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("wikibase_item")  # ex: "Q3112258"
    except (URLError, HTTPError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="mandature.csv")
    parser.add_argument("--output", default="mandature.csv")
    args = parser.parse_args()

    print("\n  Récupération des QIDs via l'API Wikipedia")
    print("  " + "─" * 45)

    with open(args.input, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fieldnames = list(rows[0].keys())

    filled  = 0
    already = 0
    missing = []

    for row in rows:
        if row["type"] != "gouvernement":
            continue
        if row.get("wikidata_qid"):
            already += 1
            continue

        nom   = row["nom"]
        title = TITLE_OVERRIDES.get(nom, nom)

        print(f"  → {title}", end=" ... ", flush=True)
        qid = get_qid_from_wikipedia(title)

        if qid:
            row["wikidata_qid"] = qid
            filled += 1
            print(f"{qid}")
        else:
            missing.append(nom)
            print("non trouvé")

        time.sleep(0.3)  # respecter le rate limit Wikipedia

    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n  ── Résumé ──────────────────────────")
    print(f"  Déjà renseignés : {already}")
    print(f"  QIDs ajoutés    : {filled}")
    print(f"  Non trouvés     : {len(missing)}")
    if missing:
        print("\n  À compléter manuellement :")
        for m in missing:
            print(f"    - {m}")
    print(f"\n  Fichier mis à jour : {args.output}\n")


if __name__ == "__main__":
    main()
