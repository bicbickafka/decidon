import pandas as pd
import os

# --- CONFIGURATION ---
BASE_PATH = "/home/mfresq/PycharmProjects/marguerite/decidon/mandats/"
INPUT_FILE = os.path.join(BASE_PATH, "tables prosopographiques DECIDON.xlsx")
OUTPUT_FILE = os.path.join(BASE_PATH, "DECIDON_Consolidated_Links.xlsx")
SHEET_NAME = "mandatures+mandats+personnes"


def run_generator():
    print(f"Step 1: Opening {INPUT_FILE}...")
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Could not find the file at {INPUT_FILE}")
        return

    # Load the specific consolidated sheet
    try:
        # We use header=0 to get column names
        df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
        print(f"✅ Loaded sheet '{SHEET_NAME}' with {len(df)} rows.")
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        return

    print("Step 2: Embedding permanent links...")

    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Consolidated')

        workbook = writer.book
        worksheet = writer.sheets['Consolidated']
        link_format = workbook.add_format({'font_color': 'blue', 'underline': 1})

        # Get column headers as a list to find indices
        headers = list(df.columns)

        # Iterate through every cell in the dataframe
        for row_idx, row in enumerate(df.values, start=1):
            for col_idx, value in enumerate(row):
                col_name = headers[col_idx]
                val_str = str(value).strip()

                if not val_str or val_str == 'nan':
                    continue

                # 1. Handle Wikidata QIDs
                if "wikidata_qid" in col_name and val_str.startswith('Q'):
                    url = f"https://www.wikidata.org/wiki/{val_str}"
                    worksheet.write_url(row_idx, col_idx, url, link_format, string=val_str)

                # 2. Handle Sénat IDs
                elif "senat_id" in col_name:
                    url = f"https://www.senat.fr/senateur-3eme-republique/{val_str}.html"
                    worksheet.write_url(row_idx, col_idx, url, link_format, string=val_str)

                # 3. Handle Sycomore IDs (Numbers)
                elif "sycomore_id" in col_name:
                    clean_sy = val_str.replace('.0', '')
                    url = f"https://www2.assemblee-nationale.fr/sycomore/fiche/(num_dept)/{clean_sy}"
                    worksheet.write_url(row_idx, col_idx, url, link_format, string=clean_sy)

    print(f"\n✅ SUCCESS! Consolidated file created at:")
    print(f"👉 {OUTPUT_FILE}")


if __name__ == "__main__":
    run_generator()