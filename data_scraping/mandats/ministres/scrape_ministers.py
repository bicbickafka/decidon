import csv
import re
import time
from datetime import datetime
from urllib.request import urlopen, Request

# Configuration
RULERS_URL = "https://rulers.org/frgovt2.html"
USER_AGENT = "MargueriteBot/1.0 (contact: mfresq@PycharmProjects)"


def load_mandature_dates(filepath):
    """Creates a mapping of mandature_id -> (start_date, end_date)"""
    dates = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['type'] == 'gouvernement':
                dates[row['mandature_id']] = (row['from_date'], row['to_date'])
    return dates


def fetch_rulers_data():
    """Scrapes the Rulers.org page and returns structured list of date entries."""
    req = Request(RULERS_URL, headers={'User-Agent': USER_AGENT})
    try:
        with urlopen(req, timeout=30) as resp:
            content = resp.read().decode('latin-1')
            # Regex to find: 22 Mar 1913 - 02 Dec 1913  Name
            # (Note: This is a simplified version of your existing regex logic)
            return re.findall(r"(\d{1,2}\s\w{3}\s\d{4})\s-\s(\d{1,2}\s\w{3}\s\d{4})\s+([^(\n]+)", content)
    except Exception as e:
        print(f"Error fetching Rulers.org: {e}")
        return []


def main():
    # 1. Load existing data
    mandature_dates = load_mandature_dates('mandature.csv')
    rulers_entries = fetch_rulers_data()

    ministers = []
    with open('mandat_ministers.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        ministers = list(reader)

    print(f"Processing {len(ministers)} rows...")

    # 2. Match and Fill
    for row in ministers:
        # Only process if dates are missing
        if not row['from_date'] or not row['to_date']:
            mid = row['mandature_id']
            full_name = f"{row['prenom']} {row['nom']}".strip()

            if mid in mandature_dates:
                m_start, m_end = mandature_dates[mid]

                # Look for name in Rulers data
                for r_start, r_end, r_name in rulers_entries:
                    if row['nom'].lower() in r_name.lower():
                        # Here you would add the overlap logic from your original script
                        # to confirm r_start/r_end falls within m_start/m_end
                        row['from_date'] = r_start
                        row['to_date'] = r_end
                        break

    # 3. Save completed file
    fieldnames = reader.fieldnames
    with open('mandat_ministers_completed.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ministers)

    print("Done. Saved to 'mandat_ministers_completed.csv'")


if __name__ == "__main__":
    main()