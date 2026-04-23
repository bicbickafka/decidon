"""
Fetch Wikidata QIDs for all chambre (sycomore ID / P1045) and sénat (senat.fr ID / P1808) members.
Run: pip install requests pandas openpyxl
     python fetch_wikidata_qids.py
"""
import requests
import pandas as pd
import time

SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "research-bot/1.0 (historical-parliament-db)"}

def sparql_query(query):
    resp = requests.get(SPARQL_URL, params={"query": query, "format": "json"}, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


df = pd.read_excel("consolidated_table.xlsx")

# ── 1. CHAMBRE: match via sycomore ID (P1045) ──────────────────────────────
print("Fetching QIDs for chambre members via sycomore ID (P1045)...")
sycomore_ids = df.loc[df["institution"] == "chambre", "sycomore_id"].dropna().astype(int).unique().tolist()
sycomore_map = {}  # sycomore_id (int) -> QID

for batch in chunks(sycomore_ids, 200):
    values = " ".join(f'"{sid}"' for sid in batch)
    query = f"""
SELECT ?item ?sid WHERE {{
  VALUES ?sid {{ {values} }}
  ?item wdt:P1045 ?sid.
}}"""
    rows = sparql_query(query)
    for r in rows:
        sid = int(r["sid"]["value"])
        qid = r["item"]["value"].split("/")[-1]
        sycomore_map[sid] = qid
    print(f"  batch done, cumulative matches: {len(sycomore_map)}")
    time.sleep(1)

print(f"Sycomore matches: {len(sycomore_map)} / {len(sycomore_ids)}")

# ── 2. SÉNAT: match via senat.fr IIIe République ID (P1808) ────────────────
print("\nFetching QIDs for sénat members via senat.fr ID (P1808)...")
senat_ids = df.loc[df["institution"] == "senat", "senat_id"].dropna().unique().tolist()
senat_map = {}  # senat_id (str) -> QID

for batch in chunks(senat_ids, 200):
    values = " ".join(f'"{sid}"' for sid in batch)
    query = f"""
SELECT ?item ?sid WHERE {{
  VALUES ?sid {{ {values} }}
  ?item wdt:P1808 ?sid.
}}"""
    rows = sparql_query(query)
    for r in rows:
        sid = r["sid"]["value"]
        qid = r["item"]["value"].split("/")[-1]
        senat_map[sid] = qid
    print(f"  batch done, cumulative matches: {len(senat_map)}")
    time.sleep(1)

print(f"Sénat matches: {len(senat_map)} / {len(senat_ids)}")

# ── 3. Apply mappings back to the dataframe ─────────────────────────────────
df["sycomore_id_int"] = pd.to_numeric(df["sycomore_id"], errors="coerce")

# Fill wikidata_qid where currently empty
filled = 0
for idx, row in df.iterrows():
    if pd.notna(row["wikidata_qid"]):
        continue
    qid = None
    if row["institution"] == "chambre" and pd.notna(row.get("sycomore_id_int")):
        qid = sycomore_map.get(int(row["sycomore_id_int"]))
    elif row["institution"] == "senat" and pd.notna(row.get("senat_id")):
        qid = senat_map.get(row["senat_id"])
    if qid:
        df.at[idx, "wikidata_qid"] = qid
        filled += 1

df.drop(columns=["sycomore_id_int"], inplace=True)

print(f"\nFilled {filled} new wikidata_qid values")
print(f"Total filled now: {df['wikidata_qid'].notna().sum()} / {len(df)}")

# ── 4. Save ──────────────────────────────────────────────────────────────────
df.to_excel("consolidated_table_with_qids.xlsx", index=False)
print("Saved to consolidated_table_with_qids.xlsx")

# Also save a summary of unmatched people
unmatched = df[df["wikidata_qid"].isna()][["person_id","institution","last_name","first_name","sycomore_id","senat_id"]].drop_duplicates("person_id")
unmatched.to_csv("unmatched_no_qid.csv", index=False)
print(f"Unmatched (no QID found): {len(unmatched)} unique people → unmatched_no_qid.csv")
