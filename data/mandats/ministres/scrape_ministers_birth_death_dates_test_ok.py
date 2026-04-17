import pandas as pd
import requests
import time
from urllib.parse import unquote


def get_minister_data(wiki_url):
    """
    Step 1: Get QID from Wikipedia API.
    Step 2: Get Birth/Death dates from Wikidata API using that QID.
    """
    if not isinstance(wiki_url, str) or 'wiki/' not in wiki_url:
        return None, "Invalid URL", "N/A"

    # Extract and clean the Wikipedia Title (fixes %C3%A9 -> é)
    title = unquote(wiki_url.split('/')[-1])
    headers = {'User-Agent': 'MinistersDataBot/1.0 (Contact: your_email@example.com)'}

    try:
        # --- STEP 1: GET QID (Logic from your fetch_qids script) ---
        wp_api_url = "https://fr.wikipedia.org/w/api.php"
        wp_params = {
            "action": "query",
            "prop": "pageprops",
            "titles": title,
            "format": "json",
            "redirects": 1
        }

        wp_res = requests.get(wp_api_url, params=wp_params, headers=headers, timeout=10).json()
        pages = wp_res.get('query', {}).get('pages', {})
        page_id = list(pages.keys())[0]

        if page_id == "-1":
            return None, "Not Found", "N/A"

        qid = pages[page_id].get('pageprops', {}).get('wikibase_item')

        if not qid:
            return None, "No QID", "N/A"

        # --- STEP 2: GET DATES FROM WIKIDATA ---
        wd_api_url = "https://www.wikidata.org/w/api.php"
        wd_params = {
            "action": "wbgetentities",
            "ids": qid,
            "props": "claims",
            "format": "json"
        }

        wd_res = requests.get(wd_api_url, params=wd_params, headers=headers, timeout=10).json()
        claims = wd_res.get('entities', {}).get(qid, {}).get('claims', {})

        def extract_date(prop_id):
            if prop_id in claims:
                try:
                    date_val = claims[prop_id][0]['mainsnak']['datavalue']['value']['time']
                    return date_val.lstrip('+').split('T')[0]
                except (IndexError, KeyError):
                    return "Missing"
            return "Missing"

        birth = extract_date('P569')
        death = extract_date('P570')

        return qid, birth, death

    except Exception:
        return None, "Error", "Error"


# --- TEST AND SAVE BLOCK ---
file_path = 'ministers_v2.xlsx'
df = pd.read_excel(file_path)

# For the test, we only take the first 5 unique URLs
test_urls = df['url'].dropna().unique()[:5]

# Dictionary to store results to avoid redundant API calls
results_cache = {}

print(f"{'NAME':<25} | {'QID':<12} | {'BIRTH':<12} | {'DEATH'}")
print("-" * 70)

for url in test_urls:
    name = unquote(url.split('/')[-1]).replace('_', ' ')
    qid, birth, death = get_minister_data(url)

    # Store in cache
    results_cache[url] = {'wikidata_qid': qid, 'birth_date_new': birth, 'death_date_new': death}

    print(f"{name[:25]:<25} | {str(qid):<12} | {birth:<12} | {death}")
    time.sleep(0.3)

# --- APPLY TO DATAFRAME ---
# Map the cached results back to the original dataframe rows
res_df = pd.DataFrame.from_dict(results_cache, orient='index').reset_index()
res_df.columns = ['url', 'wikidata_qid', 'birth_date_new', 'death_date_new']

# Merge new data into the main dataframe
df = df.merge(res_df, on='url', how='left')

# Fill the original columns with the new data
df['birth_date'] = df['birth_date_new']
df['death_date'] = df['death_date_new']
df['wikidata_qid'] = df['wikidata_qid']  # New column

# Drop the temporary helper columns
df.drop(columns=['birth_date_new', 'death_date_new'], inplace=True)

# Save to a new file
output_file = 'ministers_v2_with_death_birth_dates.xlsx'
df.to_excel(output_file, index=False)
print(f"\nSaved test results to {output_file}")