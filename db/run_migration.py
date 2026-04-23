import os
import pandas as pd
import re
from datetime import date
from app.database import engine, Base, db_session
from app.models import Person, Legislature, Mandate


def parse_date(val):
    """Convertit une chaîne en objet date, ou retourne None si invalide/vide."""
    if pd.isna(val) or str(val).strip() == "":
        return None
    try:
        # Ne garde que les 10 premiers caractères (YYYY-MM-DD) au cas où
        return date.fromisoformat(str(val).strip()[:10])
    except ValueError:
        return None


def validate_url(url):
    """Garantit que l'URL est propre, ou retourne None."""
    if pd.isna(url) or str(url).strip() == "": return None
    return url if re.match(r'^https?://', str(url).strip().lower()) else None


def clean_row_data(row):
    data = row.to_dict()
    cleaned = {}

    # 1. Variables "NULL si vide" (Identifiants et Liens)
    for col in ['person_alias', 'person_sycomore_id', 'person_senat_id', 'person_wikidata_qid']:
        val = data.get(col)
        cleaned[col.replace('person_', '')] = None if pd.isna(val) or str(val).strip() == "" else val

    cleaned['wikipedia_url'] = validate_url(data.get('person_wikipedia_url'))

    # 2. Groupe parlementaire (Désormais NULL si vide pour être homogène)
    val_group = data.get('mandate_group')
    cleaned['group'] = None if pd.isna(val_group) or str(val_group).strip() == "" else str(val_group).strip()

    # 3. Dates (Doivent absolument devenir des objets 'date' ou 'None')
    cleaned['birth_date'] = parse_date(data.get('person_birth_date'))
    cleaned['death_date'] = parse_date(data.get('person_death_date'))
    cleaned['start_date'] = parse_date(data.get('mandate_start_date'))
    cleaned['end_date'] = parse_date(data.get('mandate_end_date'))

    # Dates législatures (Obligatoires dans votre modèle, on garde les valeurs par défaut si absentes)
    leg_start = parse_date(data.get('legislature_start_date'))
    leg_end = parse_date(data.get('legislature_end_date'))
    cleaned['leg_start_date'] = leg_start if leg_start else date(1900, 1, 1)
    cleaned['leg_end_date'] = leg_end if leg_end else date(1900, 1, 1)

    # 4. Champs obligatoires String
    cleaned['person_id'] = data.get('person_id')
    cleaned['last_name'] = data.get('person_last_name')
    cleaned['first_name'] = data.get('person_first_name')
    cleaned['legislature_id'] = data.get('legislature_id')
    cleaned['legislature_name'] = data.get('legislature_name')
    cleaned['institution'] = data.get('legislature_institution', 'unknown')  # Valeur par défaut
    raw_position = data.get('mandate_position')
    cleaned['position'] = str(raw_position).strip() if not pd.isna(raw_position) and str(
        raw_position).strip() != "" else "inconnu"

    return cleaned


def run_migration():
    # Détermine le chemin absolu du dossier contenant ce script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Construit le chemin vers le fichier TSV de manière fiable
    tsv_path = os.path.join(base_dir, 'data', 'prosopography.tsv')

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Note: On s'assure d'utiliser le bon chemin relatif basé sur l'exécution du script
    df = pd.read_csv(tsv_path, sep="\t")

    for _, row in df.iterrows():
        d = clean_row_data(row)

        # A. Legislature
        leg = db_session.query(Legislature).filter_by(legislature_id=d['legislature_id']).first()
        if not leg:
            leg = Legislature(
                legislature_id=d['legislature_id'],
                name=d['legislature_name'],
                institution=d['institution'],
                start_date=d['leg_start_date'],
                end_date=d['leg_end_date']
            )
            db_session.add(leg)

        # B. Person
        person = db_session.query(Person).filter_by(person_id=d['person_id']).first()
        if not person:
            person = Person(
                person_id=d['person_id'],
                last_name=d['last_name'],
                first_name=d['first_name'],
                alias=d['alias'],
                birth_date=d['birth_date'],
                death_date=d['death_date'],
                wikidata_qid=d['wikidata_qid'],
                wikipedia_url=d['wikipedia_url'],
                sycomore_id=d['sycomore_id'],
                senat_id=d['senat_id']
            )
            db_session.add(person)

        # C. Mandate
        mandate = Mandate(
            person_id=person.person_id,
            legislature_id=leg.legislature_id,
            position=d['position'],
            group=d['group'],
            start_date=d['start_date'],
            end_date=d['end_date']
        )
        db_session.add(mandate)

    db_session.commit()


if __name__ == "__main__":
    run_migration()