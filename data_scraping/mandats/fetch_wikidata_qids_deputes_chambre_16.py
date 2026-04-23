import requests
import pandas as pd
import time
import re

SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "research-bot/1.0 (historical-parliament-db)"}


def sparql_query(query):
    resp = requests.get(SPARQL_URL, params={"query": query, "format": "json"}, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# Load the data
file_path = "chambre_16_wiki_qid.xlsx"
df = pd.read_excel(file_path)

# ── 1. CHAMBRE: match via sycomore ID (P1045) ──────────────────────────────
print("Fetching QIDs for chambre members via sycomore ID (P1045)...")

# Robust extraction: get digits from the end of the URL (e.g., .../fiche/45 -> 45)
sycomore_series = df.loc[df["mandature_institution"] == "chambre", "person_sycomore_id"].astype(str)
extracted_sycomore = sycomore_series.str.extract(r'(\d+)$')[0]
sycomore_ids = pd.to_numeric(extracted_sycomore, errors='coerce').dropna().astype(int).unique().tolist()

sycomore_map = {}  # sycomore_id (int) -> QID

for batch in chunks(sycomore_ids, 200):
    values = " ".join(f'"{sid}"' for sid in batch)
    query = f"""
SELECT ?item ?sid WHERE {{
  VALUES ?sid {{ {values} }}
  ?item wdt:P1045 ?sid.
}}"""
    try:
        rows = sparql_query(query)
        for r in rows:
            sid = int(r["sid"]["value"])
            qid = r["item"]["value"].split("/")[-1]
            sycomore_map[sid] = qid
        print(f"  batch done, cumulative matches: {len(sycomore_map)}")
    except Exception as e:
        print(f"  Error in batch: {e}")
    time.sleep(1)

# ── 2. SÉNAT: match via senat.fr ID (P1808) ────────────────
print("\nFetching QIDs for sénat members via senat.fr ID (P1808)...")

# Senat IDs are usually strings (e.g., 'senateur/nom_prenom01234r')
senat_ids = df.loc[df["mandature_institution"] == "senat", "person_senat_id"].dropna().unique().tolist()
senat_map = {}

for batch in chunks(senat_ids, 200):
    values = " ".join(f'"{sid}"' for sid in batch)
    query = f"""
SELECT ?item ?sid WHERE {{
  VALUES ?sid {{ {values} }}
  ?item wdt:P1808 ?sid.
}}"""
    try:
        rows = sparql_query(query)
        for r in rows:
            sid = r["sid"]["value"]
            qid = r["item"]["value"].split("/")[-1]
            senat_map[sid] = qid
        print(f"  batch done, cumulative matches: {len(senat_map)}")
    except Exception as e:
        print(f"  Error in batch: {e}")
    time.sleep(1)

# ── 3. Apply mappings back to the dataframe ─────────────────────────────────
# Create a temporary numeric column for the lookup
temp_ids = df["person_sycomore_id"].astype(str).str.extract(r'(\d+)$')[0]
df["temp_sycomore_int"] = pd.to_numeric(temp_ids, errors="coerce")

filled = 0
for idx, row in df.iterrows():
    # Only fill if the QID is currently empty/NaN
    if pd.notna(row["person_wikidata_qid"]):
        continue

    qid = None
    inst = row["mandature_institution"]

    if inst == "chambre" and pd.notna(row["temp_sycomore_int"]):
        qid = sycomore_map.get(int(row["temp_sycomore_int"]))
    elif inst == "senat" and pd.notna(row["person_senat_id"]):
        qid = senat_map.get(row["person_senat_id"])

    if qid:
        df.at[idx, "person_wikidata_qid"] = qid
        filled += 1

# Cleanup
df.drop(columns=["temp_sycomore_int"], inplace=True)

print(f"\nSuccess! Filled {filled} new wikidata_qid values.")
print(f"Total rows with QIDs: {df['person_wikidata_qid'].notna().sum()} / {len(df)}")

# ── 4. Save ──────────────────────────────────────────────────────────────────
output_file = "chambre_16_wiki_qid_completed.xlsx"
df.to_excel(output_file, index=False)
print(f"File saved as: {output_file}")

# Optional: summary of missing ones
unmatched = df[df["person_wikidata_qid"].isna()]
if not unmatched.empty:
    unmatched_count = unmatched["person_id"].nunique()
    print(f"Note: {unmatched_count} unique people still missing QIDs.")