import pandas as pd
import openpyxl


def extract_hyperlinks_with_label(filename):
    wb = openpyxl.load_workbook(filename, data_only=False)
    sheet = wb.active
    data = []

    headers = [cell.value for cell in sheet[1]]

    for row in sheet.iter_rows(min_row=2):
        row_values = []
        for cell in row:
            # Si la cellule a un lien hypertexte
            if cell.hyperlink:
                url = cell.hyperlink.target
                label = str(cell.value) if cell.value is not None else url
                # On crée la formule Excel pour garder le lien "sous" le texte
                row_values.append(f'=HYPERLINK("{url}", "{label}")')
            else:
                row_values.append(cell.value)
        data.append(row_values)

    return pd.DataFrame(data, columns=headers)


# 1. Extraction avec préservation des liens
print("Traitement des liens et des identifiants...")
df = extract_hyperlinks_with_label('personnes.xlsx')

# 2. Nettoyage des valeurs vides
df = df.replace(r'^\s*$', pd.NA, regex=True)

# 3. Consolidation par person_id
# .first() gardera la première formule HYPERLINK ou la première valeur texte trouvée
consolidated_df = df.groupby('person_id', as_index=False).first()

# 4. Sauvegarde en format Excel (obligatoire pour que les formules fonctionnent)
consolidated_df.to_excel('personnes_final_cliquable.xlsx', index=False)

print("Succès ! Le fichier 'personnes_final_cliquable.xlsx' contient vos IDs avec liens intégrés.")