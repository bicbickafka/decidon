import pandas as pd
import requests
import time
from urllib.parse import unquote
from tqdm import tqdm  # Recommended: pip install tqdm


def get_minister_data(wiki_url):
    if not isinstance(wiki_url, str) or 'wiki/' not in wiki_url:
        return None, "Invalid URL", "N/A"

    title = unquote(wiki_url.split('/')[-1])
    # It's good practice to include a real User-Agent
    headers = {'User-Agent': 'MinistersDataBot/1.0 (Contact: your_email@example.com)'}

    try:
        # STEP 1: Get QID from Wikipedia
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

        # STEP 2: Get Dates from Wikidata
        wd_api_url = "https://www.wikidata.org/w/api.php"
        wd_params = {"action": "wbgetentities", "ids": qid, "props": "claims", "format": "json"}

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

        return qid, extract_date('P569'), extract_date('P570')

    except Exception:
        return None, "Error", "Error"


# --- FULL EXECUTION BLOCK ---
input_file = 'ministers_v2.xlsx'
output_file = 'ministers_v2_with_death_birth_dates.xlsx'

print(f"Loading {input_file}...")
df = pd.read_excel(input_file)

# Get all unique URLs (this avoids redundant API calls for the same person)
unique_urls = df['url'].dropna().unique()
results_cache = {}

print(f"Starting API calls for {len(unique_urls)} unique ministers...")

# Using tqdm for a progress bar. If you don't have it, use: for url in unique_urls:
for url in tqdm(unique_urls):
    qid, birth, death = get_minister_data(url)
    results_cache[url] = {
        'wikidata_qid': qid,
        'birth_date_new': birth,
        'death_date_new': death
    }
    # Respectful delay (0.3s * 600 people ≈ 3 minutes total)
    time.sleep(0.3)

# --- APPLY RESULTS TO DATAFRAME ---
print("\nMapping data back to main table...")
res_df = pd.DataFrame.from_dict(results_cache, orient='index').reset_index()
res_df.columns = ['url', 'wikidata_qid', 'birth_date_new', 'death_date_new']

# Merge the new columns into the main dataframe
df = df.merge(res_df, on='url', how='left')

# Update original columns and handle the new QID column
df['birth_date'] = df['birth_date_new']
df['death_date'] = df['death_date_new']
# Only keep the new columns we want
df.drop(columns=['birth_date_new', 'death_date_new'], inplace=True)

# Save the final file
df.to_excel(output_file, index=False)
print(f"Success! Full data saved to {output_file}")