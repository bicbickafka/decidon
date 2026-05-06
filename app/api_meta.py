"""
api_meta.py

API Decidon metadatas.
"""

METADATA = {
    "title": "Decidon — API",
    "version": "0.1.0",
    "description": """
## Decidon — Prosopographical Directory of the French Third Republic

This API provides access to the **Decidon** reference dataset, a historical database dedicated to
members of parliament and government under the **French Third Republic** from 1870 to 1939.

Data covers:

- the **persons** themselves (deputies, senators, ministers);
- their **mandates** (position, political group, dates of office);
- the **legislatures** of the three institutions (Chamber of Deputies, Senate, Government).

Data is made available under the (TODO - Nom licence + modif champ licence_info) license.

----
""",
    "openapi_url": "/api/openapi.json",
    "docs_url": "/api/docs",
    "redoc_url": "/api/redoc",
    "license_info": {
        "name": "CC BY-SA 4.0",
        "url": "https://creativecommons.org/licenses/by-sa/4.0/",
    },
    "openapi_tags": [
        {
            "name": "persons",
            "description": "Search and retrieve referenced persons."
        },
        {
            "name": "persons mandates",
            "description": "Retrieve mandates associated with a person, grouped or filtered."
        },
        {
            "name": "legislatures",
            "description": "Retrieve legislatures and their members."
        },
        {
            "name": "utils",
            "description": "Utility routes: fuzzy name search, persons in office at a given date, service availability."
        },
    ],
    "routes": {
        "read_root": {
            "summary": "Check if the service is available.",
            "description": "Returns a simple message confirming that the service is up and running.",
            "tags": ["utils"],
        },
        "search_persons": {
            "summary": "Retrieve all persons, with optional filters.",
            "description": (
                "Returns a paginated list of persons, filterable by last name, first name, "
                "department, group or institution. "
                "Does not include mandates — use `/persons/grouped-mandates` for an enriched response."
            ),
            "tags": ["persons"],
        },
        "search_grouped_mandates": {
            "summary": "Retrieve persons with their grouped mandates.",
            "description": (
                "**Main route powering the search interface.** Returns persons with their mandates "
                "filtered and grouped by person. Supports sorting and pagination.\n\n"
                "Available filters:\n\n"
                "| Parameter | Description |\n"
                "|---|---|\n"
                "| `last_name` | Filter by last name |\n"
                "| `first_name` | Filter by first name |\n"
                "| `legislature_name` | Legislature name (e.g. `Élections sénatoriales de 1882`) |\n"
                "| `position` | Department or territory of representation |\n"
                "| `institution` | One of `chambre`, `senat` or `gouvernement` |\n"
                "| `start_from` | Persons in office on this date (`YYYY-MM-DD`) |\n"
                "| `end_until` | Mandates ended before this date (`YYYY-MM-DD`) |\n\n"
                "All text filters are case-insensitive and accent-insensitive."
            ),
            "tags": ["persons mandates"],
        },
        "get_by_role": {
            "summary": "Retrieve persons holding a position at a given date.",
            "description": (
                "Returns all persons holding a given position on a specific date. "
                "Useful for reconstructing a governmental or parliamentary composition at a point in time.\n\n"
                "Example: `position=président du conseil&date=1900-01-01`"
            ),
            "tags": ["utils"],
        },
        "get_person": {
            "summary": "Retrieve a person by their person_id.",
            "description": (
                "Returns the full detail of a person identified by their `person_id` "
                "(e.g. `PER-000001`), including all their mandates sorted chronologically. "
                "Used to power the detail view and permalinks (`/#PER-000001`)."
            ),
            "tags": ["persons"],
        },
        "list_legislatures": {
            "summary": "Retrieve all legislatures, with optional filters.",
            "description": (
                "Returns all legislatures, filterable by institution (`chambre`, `senat`, `gouvernement`) "
                "and by name. Results are sorted chronologically by start date."
            ),
            "tags": ["legislatures"],
        },
        "get_members": {
            "summary": "Retrieve all members of a legislature.",
            "description": (
                "Returns all persons holding a mandate in the specified legislature, "
                "identified by its `legislature_id` (e.g. `LEG-000001`). "
                "Results are sorted alphabetically by last name."
            ),
            "tags": ["legislatures"],
        },
        "lookup": {
            "summary": "Fuzzy name lookup.",
            "description": (
                "Fast accent- and case-insensitive search across `last_name` and `first_name`. "
                "Designed for autocomplete — capped at 50 results."
            ),
            "tags": ["utils"],
        },
    }
}