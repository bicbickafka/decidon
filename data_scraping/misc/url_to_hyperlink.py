import pandas as pd

# 1. Load the Excel file
# Make sure you have 'openpyxl' installed (pip install openpyxl)
input_file = 'full_table.xlsx'
output_file = 'final_links.xlsx'

df = pd.read_excel(input_file)


# 2. Define the hyperlink function
def make_clickable(url):
    if pd.isna(url) or str(url).strip() == "":
        return ""
    # Using semicolon (;) for regional settings as per your original code
    # If your Excel uses commas, change ";" to ","
    return f'=HYPERLINK("{url}"; "{url}")'


# 3. Identify the column by position (Column O is the 15th column -> Index 14)
# This prevents the "KeyError" because it doesn't care what the header is named
column_index = 14

try:
    column_name = df.columns[column_index]
    print(f"Targeting column: '{column_name}' at index {column_index}")

    # 4. Apply the function to create a new column
    df['Clickable_Link'] = df[column_name].apply(make_clickable)

    # 5. Save to a new Excel file
    df.to_excel(output_file, index=False)
    print(f"Success! Your file is saved as: {output_file}")

except IndexError:
    print(f"Error: Your file doesn't have 15 columns. It only has {len(df.columns)}.")