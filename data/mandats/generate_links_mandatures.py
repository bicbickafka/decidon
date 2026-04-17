import pandas as pd
import os

# --- CONFIGURATION ---
BASE_PATH = "/home/mfresq/PycharmProjects/marguerite/decidon/mandats/"
INPUT_FILE = os.path.join(BASE_PATH, "tables prosopographiques DECIDON.xlsx")
OUTPUT_FILE = os.path.join(BASE_PATH, "Mandatures_avec_Liens.xlsx")
SHEET_NAME = "mandatures"


def generate_mandatures_links():
    print(f"Ouverture du fichier : {INPUT_FILE}...")
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Erreur : Fichier introuvable à l'adresse {INPUT_FILE}")
        return

    # Chargement de l'onglet mandatures
    try:
        df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
        print(f"✅ {len(df)} lignes chargées.")
    except Exception as e:
        print(f"❌ Erreur lors de la lecture de l'onglet : {e}")
        return

    print("Création des liens Wikidata (métadonnées permanentes)...")

    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Mandatures')

        workbook = writer.book
        worksheet = writer.sheets['Mandatures']

        # Style : Bleu et souligné
        link_format = workbook.add_format({'font_color': 'blue', 'underline': 1})

        # Trouver l'index de la colonne wikidata_qid
        try:
            qid_col_idx = list(df.columns).index('wikidata_qid')
        except ValueError:
            print("❌ Erreur : Colonne 'wikidata_qid' introuvable.")
            return

        # Parcourir les lignes pour insérer les liens
        for row_num, qid in enumerate(df['wikidata_qid'], start=1):
            val_str = str(qid).strip()

            if val_str and val_str.startswith('Q') and val_str != 'nan':
                url = f"https://www.wikidata.org/wiki/{val_str}"
                # On écrit le lien directement dans la cellule
                worksheet.write_url(row_num, qid_col_idx, url, link_format, string=val_str)

    print(f"\n✅ TERMINÉ ! Fichier créé : {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_mandatures_links()