import requests
import pandas as pd
import time
import re

# --- CONFIG ---
SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "research-bot/1.0 (historical-parliament-db)"}
INPUT_FILE = "consolidated_table.xlsx"
OUTPUT_FILE = "consolidated_table_with_qids.xlsx"


def sparql_query(query):
    resp = requests.get(SPARQL_URL, params={"query": query, "format": "json"}, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def get_core_name(sid):
    """Strips trailing digits/codes like '1514r3' to leave 'martel_louis'"""
    if pd.isna(sid): return None
    return re.sub(r'\d+r\d+$', '', str(sid)).strip()


# 1. LOAD DATA
print(f"Loading {INPUT_FILE}...")
df = pd.read_excel(INPUT_FILE, dtype={'senat_id': str, 'sycomore_id': str})

# 2. CHAMBRE MATCHING (SYCOMORE - P1045)
print("Processing Chambre members (P1045)...")
sycomore_ids = df.loc[df["institution"] == "chambre", "sycomore_id"].dropna().unique().tolist()
sycomore_map = {}

for batch in chunks(sycomore_ids, 200):
    values = " ".join(f'"{sid}"' for sid in batch)
    query = f"SELECT ?item ?sid WHERE {{ VALUES ?sid {{ {values} }} ?item wdt:P1045 ?sid. }}"
    rows = sparql_query(query)
    for r in rows:
        sid = r["sid"]["value"]
        qid = r["item"]["value"].split("/")[-1]
        sycomore_map[sid] = qid
    time.sleep(0.5)

# 3. SÉNAT MATCHING (FUZZY P1808)
print("Processing Sénat members (Fuzzy P1808)...")
senat_raw_ids = df.loc[df["institution"] == "senat", "senat_id"].dropna().unique()
# Map: Cleaned Core -> Original ID from Excel
senat_core_map = {get_core_name(sid): sid for sid in senat_raw_ids if get_core_name(sid)}
core_names = list(senat_core_map.keys())
senat_map = {}

for batch in chunks(core_names, 50):  # Smaller batches for FILTER performance
    values = " ".join(f'"{name}"' for name in batch)
    query = f"""
    SELECT ?item ?sid_found ?core WHERE {{
      VALUES ?core {{ {values} }}
      ?item p:P1808/ps:P1808 ?sid_found .
      FILTER(CONTAINS(?sid_found, ?core))
    }}"""

    rows = sparql_query(query)
    for r in rows:
        qid = r["item"]["value"].split("/")[-1]
        core_name = r["core"]["value"]
        original_id = senat_core_map.get(core_name)
        if original_id:
            senat_map[original_id] = qid
    print(f"  ...cumulative sénat matches: {len(senat_map)}")
    time.sleep(1)

# 4. APPLY MAPPINGS
filled = 0
for idx, row in df.iterrows():
    if pd.notna(row.get("wikidata_qid")):
        continue

    qid = None
    if row["institution"] == "chambre":
        qid = sycomore_map.get(str(row.get("sycomore_id")))
    elif row["institution"] == "senat":
        qid = senat_map.get(str(row.get("senat_id")))

    if qid:
        df.at[idx, "wikidata_qid"] = qid
        filled += 1

print(f"\n✅ Total QIDs newly filled: {filled}")
df.to_excel(OUTPUT_FILE, index=False)
print(f"File saved as: {OUTPUT_FILE}")