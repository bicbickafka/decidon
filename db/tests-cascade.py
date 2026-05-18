import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db_session
from app.models import Person, Mandate, Legislature

db = db_session()

PASS = "✓"
FAIL = "✗"

print("=" * 60)
print("  TESTS DE CASCADE — Decidon")
print("=" * 60)


# ─────────────────────────────────────────────────────────────
# TEST 1 — Supprimer un mandat ne supprime PAS la personne
# ─────────────────────────────────────────────────────────────
print("\n[TEST 1] Supprimer un mandat ne supprime pas la personne")

person1 = db.query(Person).first()
mandate1 = db.query(Mandate).filter_by(person_id=person1.person_id).first()
person1_id = person1.person_id
mandate1_id = mandate1.id

db.delete(mandate1)
db.commit()

person1_check = db.query(Person).filter_by(person_id=person1_id).first()
mandate1_check = db.query(Mandate).filter_by(id=mandate1_id).first()

if person1_check is not None and mandate1_check is None:
    print(f"  {PASS} Mandat {mandate1_id} supprimé")
    print(f"  {PASS} Personne '{person1_id}' toujours présente")
else:
    if person1_check is None:
        print(f"  {FAIL} La personne '{person1_id}' a été supprimée — ERREUR")
    if mandate1_check is not None:
        print(f"  {FAIL} Le mandat {mandate1_id} n'a pas été supprimé — ERREUR")


# ─────────────────────────────────────────────────────────────
# TEST 2 — Supprimer une personne supprime ses mandats
# ─────────────────────────────────────────────────────────────
print("\n[TEST 2] Supprimer une personne supprime ses mandats en cascade")

person2 = db.query(Person).filter(Person.person_id != person1_id).first()
person2_id = person2.person_id
mandate_ids = [m.id for m in db.query(Mandate).filter_by(person_id=person2_id).all()]
print(f"  Mandats avant suppression : {mandate_ids}")

db.delete(person2)
db.commit()

person2_check = db.query(Person).filter_by(person_id=person2_id).first()
remaining_mandates = db.query(Mandate).filter(Mandate.id.in_(mandate_ids)).all()

if person2_check is None and len(remaining_mandates) == 0:
    print(f"  {PASS} Personne '{person2_id}' supprimée")
    print(f"  {PASS} Tous les mandats associés supprimés ({len(mandate_ids)} mandats)")
else:
    if person2_check is not None:
        print(f"  {FAIL} La personne '{person2_id}' n'a pas été supprimée — ERREUR")
    if remaining_mandates:
        print(f"  {FAIL} {len(remaining_mandates)} mandat(s) orphelin(s) subsistent — ERREUR")


# ─────────────────────────────────────────────────────────────
# TEST 3 — Supprimer une législature avec mandats est bloqué
# ─────────────────────────────────────────────────────────────
print("\n[TEST 3] Supprimer une législature avec mandats est bloqué")

legislature = db.query(Legislature).join(Mandate).first()
leg_id = legislature.legislature_id
mandate_count = db.query(Mandate).filter_by(legislature_id=leg_id).count()
print(f"  Législature '{leg_id}' — {mandate_count} mandats rattachés")

try:
    db.delete(legislature)
    db.commit()
    print(f"  {FAIL} Législature supprimée malgré des mandats — ERREUR")
except Exception:
    db.rollback()
    leg_check = db.query(Legislature).filter_by(legislature_id=leg_id).first()
    if leg_check is not None:
        print(f"  {PASS} Suppression bloquée (IntegrityError)")
        print(f"  {PASS} Législature '{leg_id}' toujours présente")
    else:
        print(f"  {FAIL} Législature supprimée malgré l'exception — ERREUR")
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  FIN DES TESTS")
print("=" * 60)