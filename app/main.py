from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import date as DateType
from app.database import get_db
from app import crud, schemas

app = FastAPI(
    title="Référentiel des parlementaires et membres du gouvernement sous la IIIe République",
    description="Documentation de l'API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 0. Serve Frontend ─────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def read_index():
    return FileResponse('app/index.html')

# ── 1. Search persons ─────────────────────────────────────────────────────────
@app.get("/persons", response_model=list[schemas.PersonOut])
def search_persons(
    last_name: str | None = Query(None), first_name: str | None = Query(None),
    department: str | None = Query(None), group: str | None = Query(None),
    institution: str | None = Query(None), limit: int = Query(50, le=500),
    offset: int = Query(0), db: Session = Depends(get_db)
):
    return crud.search_persons_logic(db, last_name, first_name, department, group, institution, limit, offset)

# ── 2. Get persons by role at date ────────────────────────────────────────────
# Must be BEFORE /persons/{person_id} to avoid being swallowed by it
@app.get("/persons/by-role")
def get_by_role(
    position: str = Query(...),
    date: DateType = Query(...),
    db: Session = Depends(get_db)
):
    return crud.get_persons_by_role_at_date(db, position, date)

# ── 3. Get one person ─────────────────────────────────────────────────────────
@app.get("/persons/{person_id}", response_model=schemas.PersonDetailOut)
def get_person(person_id: str, db: Session = Depends(get_db)):
    result = crud.get_person_by_id(db, person_id)
    if not result:
        raise HTTPException(404, "Person not found")
    return result

# ── 4. List all legislatures ──────────────────────────────────────────────────
@app.get("/legislatures", response_model=list[schemas.LegislatureOut])
def list_legislatures(
    institution: str | None = Query(None),
    name: str | None = Query(None),
    db: Session = Depends(get_db)
):
    return crud.list_legislatures_logic(db, institution, name)

# ── 5. Members of one legislature ─────────────────────────────────────────────
@app.get("/legislatures/{legislature_id}/members", response_model=list[schemas.PersonOut])
def get_members(legislature_id: str, db: Session = Depends(get_db)):
    return crud.get_members_logic(db, legislature_id)

# ── 6. Fuzzy name lookup ──────────────────────────────────────────────────────
@app.get("/lookup", response_model=list[schemas.PersonOut])
def lookup(q: str = Query(...), limit: int = Query(10, le=50), db: Session = Depends(get_db)):
    return crud.lookup_logic(db, q, limit)