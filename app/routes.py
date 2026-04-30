"""
routes.py
FastAPI routes for the parlementaires API.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import date as DateType
from app.database import get_db
from app import crud, schemas

api_router = APIRouter()


# ── 0. Serve Frontend ─────────────────────────────────────────────────────────

@api_router.get("/", include_in_schema=False)
async def read_index():
    return FileResponse("app/index.html")


# ── 1. Search persons ─────────────────────────────────────────────────────────

@api_router.get("/persons", response_model=list[schemas.PersonOut])
def search_persons(
    last_name: str | None = Query(None),
    first_name: str | None = Query(None),
    department: str | None = Query(None),
    group: str | None = Query(None),
    institution: str | None = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    return crud.search_persons_logic(
        db, last_name, first_name, department, group, institution, limit, offset
    )


# ── 2. Search persons with grouped mandates ───────────────────────────────────
# Must be BEFORE /persons/{person_id} to avoid being swallowed by it

@api_router.get("/persons/grouped-mandates", response_model=schemas.PersonMandateGroupSearchResponse)
def search_grouped_mandates(
    first_name: str | None = Query(None),
    last_name: str | None = Query(None),
    position: str | None = Query(None),
    group_value: str | None = Query(None),
    legislature_name: str | None = Query(None),
    institution: str | None = Query(None),
    start_from: DateType | None = Query(None),
    end_until: DateType | None = Query(None),
    sort_by: str = Query("last_name"),
    sort_dir: str = Query("asc"),
    limit: int = Query(40, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    total_groups = crud.count_person_mandate_groups_logic(
        db, first_name, last_name, position, group_value,
        legislature_name, institution, start_from, end_until,
    )
    items = crud.search_person_mandate_groups_logic(
        db, first_name, last_name, position, group_value,
        legislature_name, institution, start_from, end_until,
        sort_by, sort_dir, limit, offset,
    )
    return {
        "total_groups": total_groups,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


# ── 3. Get persons by role at date ────────────────────────────────────────────
# Must be BEFORE /persons/{person_id} to avoid being swallowed by it

@api_router.get("/persons/by-role")
def get_by_role(
    position: str = Query(...),
    date: DateType = Query(...),
    db: Session = Depends(get_db),
):
    return crud.get_persons_by_role_at_date(db, position, date)


# ── 4. Get one person (permalink) ─────────────────────────────────────────────

@api_router.get("/persons/{person_id}", response_model=schemas.PersonDetailOut)
def get_person(person_id: str, db: Session = Depends(get_db)):
    result = crud.get_person_by_id(db, person_id)
    if not result:
        raise HTTPException(404, "Person not found")
    return result


# ── 5. List all legislatures ──────────────────────────────────────────────────

@api_router.get("/legislatures", response_model=list[schemas.LegislatureOut])
def list_legislatures(
    institution: str | None = Query(None),
    name: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return crud.list_legislatures_logic(db, institution, name)


# ── 6. Members of one legislature ─────────────────────────────────────────────

@api_router.get(
    "/legislatures/{legislature_id}/members",
    response_model=list[schemas.PersonOut],
)
def get_members(legislature_id: str, db: Session = Depends(get_db)):
    return crud.get_members_logic(db, legislature_id)


# ── 7. Fuzzy name lookup ──────────────────────────────────────────────────────

@api_router.get("/lookup", response_model=list[schemas.PersonOut])
def lookup(
    q: str = Query(...),
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
):
    return crud.lookup_logic(db, q, limit)