#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Indexing and search with Whoosh + BM25F
for Decidon project.

Features:
- SQLite -> Whoosh indexing
- Accent/case-insensitive search
- Stopword removal
- Prefix search: "ben jaur" -> "ben* jaur*"
- BM25F scoring
- Optional AND/OR query mode
- Fallback strategy:
  1. Exact match
  2. Main query according to bool_type (AND by default)
  3. Token-by-token fallback
  4. OR fallback
- Partial dates supported:
  - None
  - 1901
  - "1901"
  - "1901-11"
  - "1901-11-04"
  - date(1901, 11, 4)
- Persistent search engine suitable for API-like usage
- Precomputed active docnum filter by date
- LRU cache for parsed queries and active date filters
- Single query test mode
- Batch JSON simulation mode

Batch JSON format expected:
{
  "session_id": "...",
  "session_date": "1903-11-28",
  "occurrences": [
    {
      "source_id": "...",
      "str_ref": "Paul Doumer"
    }
  ]
}
"""

from __future__ import annotations

import argparse
import calendar
import json
import re
import shutil
import time as time_module
import unicodedata
import warnings

from datetime import date, datetime, time
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from stopwordsiso import stopwords
from whoosh import index, query as whoosh_query, scoring, sorting
from whoosh.fields import DATETIME, ID, Schema, TEXT
from whoosh.qparser import AndGroup, MultifieldParser, OrGroup

# A virer à terme permet juste de supprimer les warnings de la dépendance whoosh
warnings.filterwarnings(
    "ignore",
    category=SyntaxWarning,
    module="whoosh.codec.whoosh3",
)


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "db" / "data" / "prosopography.db"
INDEX_DIR = BASE_DIR / "indexdir"

BM25_K1 = 1.5
BM25_B = 0.75

SEARCH_FIELDS = ["first_name", "last_name", "alias", "position", "role"]

FRENCH_STOPWORDS = stopwords("fr")


engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def db_session():
    return SessionLocal()


def normalize(value: Optional[str]) -> str:
    if not value:
        return ""

    value = value.replace("’", "'").replace("`", "'")
    value = value.replace("-", " ")
    value = re.sub(r"[()\[\]{},;:!?]", " ", value)
    value = re.sub(r"[.,;:]+$", "", value.strip())
    value = unicodedata.normalize("NFD", value).encode("ascii", "ignore").decode("utf-8")
    value = re.sub(r"\s+", " ", value)

    return value.lower().strip()


# legacy
# def normalize(value: Optional[str]) -> str:
#     """Return a normalized string suitable for indexing and searching."""
#     if not value:
#         return ""
#
#     value = value.replace("’", "'").replace("`", "'")
#     value = re.sub(r"\s*-\s*", "-", value)
#     value = re.sub(r"[.,;:]+$", "", value.strip())
#     value = unicodedata.normalize("NFD", value).encode("ascii", "ignore").decode("utf-8")
#     value = re.sub(r"\s+", " ", value)
#
#     return value.lower().strip()


def remove_stopwords(query_str: str) -> str:
    """
    Remove French stopwords from a normalized query.

    Examples:
    - "le président" -> "president"
    - "président du conseil" -> "president conseil"
    """
    normalized = normalize(query_str)
    tokens = [
        token
        for token in normalized.split()
        if token not in FRENCH_STOPWORDS
    ]
    return " ".join(tokens)


def query_tokens(query_str: str) -> list[str]:
    """
    Return cleaned tokens used for search and fallback.

    Removes:
    - French stopwords
    - one-letter initials such as "G."
    - very short tokens
    - punctuation and parentheses

    Example:
    - "G. de Beauregard (Indre)" -> ["beauregard", "indre"]
    """
    cleaned = remove_stopwords(query_str)
    # Remove punctuation-like characters but keep letters/numbers/hyphens.
    cleaned = re.sub(r"[()\[\]{},;:!?]", " ", cleaned)
    cleaned = re.sub(r"\.", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    tokens = []
    for token in cleaned.split():
        token = token.strip("-_ ")
        if not token:
            continue
        # Remove initials and tiny tokens: "g", "m", "l", etc.
        if len(token) <= 1:
            continue
        tokens.append(token)
    return tokens


def parse_iso_date(value: Any) -> Optional[date]:
    """
    Parse a date-like value into a Python date, or return None.

    Accepts:
    - date
    - datetime
    - "YYYY-MM-DD"
    - "YYYY-MM-DD HH:MM:SS"
    - "YYYY-MM-DDTHH:MM:SS"
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


@lru_cache(maxsize=512)
def parse_partial_date_range_cached(
    value: Optional[str | int | date],
) -> Optional[tuple[date, date]]:
    """
    Parse a partial date into an inclusive date range.

    Accepted values:
    - None
    - date(1901, 11, 4)
    - 1901
    - "1901"
    - "1901-11"
    - "1901-11-04"
    """
    if value is None:
        return None

    if isinstance(value, date):
        return value, value

    value = str(value).strip()

    if re.fullmatch(r"\d{4}", value):
        year = int(value)
        return date(year, 1, 1), date(year, 12, 31)

    if re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = map(int, value.split("-"))
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        day = date.fromisoformat(value)
        return day, day

    raise ValueError(
        "Invalid session_date. Expected None, YYYY, YYYY-MM, YYYY-MM-DD, "
        "or a datetime.date object."
    )


def parse_partial_date_range(
    value: Optional[str | int | date],
) -> Optional[tuple[date, date]]:
    """Public wrapper around the cached partial date parser."""
    return parse_partial_date_range_cached(value)


def is_active_during_range(
    active_from: Any,
    active_until: Any,
    date_range: Optional[tuple[date, date]],
) -> bool:
    """
    Return True if [active_from, active_until] overlaps date_range.

    If date_range is None, the row is considered active.
    """
    if date_range is None:
        return True

    start_date = parse_iso_date(active_from)
    end_date = parse_iso_date(active_until)

    if start_date is None or end_date is None:
        return False

    range_start, range_end = date_range

    return start_date <= range_end and end_date >= range_start


def is_active_during_hit(
    hit: dict[str, Any],
    date_range: Optional[tuple[date, date]],
) -> bool:
    """
    Return True if a stored Whoosh hit is active during date_range.
    """
    return is_active_during_range(
        hit.get("active_from"),
        hit.get("active_until"),
        date_range,
    )


def create_schema() -> Schema:
    """
    Create the Whoosh schema.

    Search fields are indexed but not stored.
    Display fields are stored so terminal output keeps the original DB text.
    Date fields are stored as DATETIME for fast preprocessing.
    """
    return Schema(
        row_key=ID(stored=True, unique=True),
        person_id=ID(stored=True),
        mandate_id=ID(stored=True),

        first_name=TEXT(stored=False),
        last_name=TEXT(stored=False),
        alias=TEXT(stored=False),
        position=TEXT(stored=False),
        role=TEXT(stored=False),

        first_name_display=TEXT(stored=True),
        last_name_display=TEXT(stored=True),
        alias_display=TEXT(stored=True),
        position_display=TEXT(stored=True),
        role_display=TEXT(stored=True),

        active_from=DATETIME(stored=True),
        active_until=DATETIME(stored=True),
    )


def _joined_rows(db: Session) -> list[dict[str, Any]]:
    """
    Fetch persons joined to mandate memberships and mandates.

    Assumption:
    - Relevant dates are always stored in is_member_of_mandate.start_date
      and is_member_of_mandate.end_date.
    - Rows missing these dates are excluded.
    """
    sql = text(
        """
        SELECT
            p.person_id,
            p.first_name,
            p.last_name,
            p.alias,
            imm.mandate_id,
            imm.position,
            imm.role,
            imm.start_date AS active_from,
            imm.end_date AS active_until
        FROM persons p
        JOIN is_member_of_mandate imm ON imm.person_id = p.person_id
        JOIN mandates m ON m.mandate_id = imm.mandate_id
        WHERE
            imm.start_date IS NOT NULL
            AND imm.end_date IS NOT NULL
        """
    )

    return [dict(row) for row in db.execute(sql).mappings().all()]


def create_index(index_dir: Path = INDEX_DIR) -> dict[str, Any]:
    """
    Build the Whoosh index.

    The existing index directory is removed first so the index always reflects
    the current database state.
    """
    db = db_session()

    try:
        rows = _joined_rows(db)
    finally:
        db.close()

    if index_dir.exists():
        shutil.rmtree(index_dir)

    index_dir.mkdir(parents=True, exist_ok=True)

    ix = index.create_in(index_dir, create_schema())
    writer = ix.writer()

    indexed_count = 0
    skipped_count = 0

    for row in rows:
        start_date = parse_iso_date(row["active_from"])
        end_date = parse_iso_date(row["active_until"])

        if start_date is None or end_date is None:
            skipped_count += 1
            continue

        writer.add_document(
            row_key=f"{row['person_id']}::{row['mandate_id']}",
            person_id=str(row["person_id"]),
            mandate_id=str(row["mandate_id"]),

            first_name=normalize(row["first_name"]),
            last_name=normalize(row["last_name"]),
            alias=normalize(row.get("alias") or ""),
            position=normalize(row.get("position") or ""),
            role=normalize(row.get("role") or ""),

            first_name_display=row["first_name"],
            last_name_display=row["last_name"],
            alias_display=row.get("alias") or "",
            position_display=row.get("position") or "",
            role_display=row.get("role") or "",

            active_from=datetime.combine(start_date, time.min),
            active_until=datetime.combine(end_date, time.max),
        )

        indexed_count += 1

    writer.commit(optimize=True)

    return {
        "index_dir": str(index_dir),
        "rows_from_database": len(rows),
        "documents_indexed": indexed_count,
        "documents_skipped": skipped_count,
    }


def get_index(index_dir: Path = INDEX_DIR):
    """
    Open an existing Whoosh index.

    This does not rebuild the index automatically.
    """
    if not index_dir.exists():
        raise FileNotFoundError(
            f"Index directory not found: {index_dir}. "
            "Run with --build-index first."
        )

    return index.open_dir(index_dir)


def get_or_create_index(index_dir: Path = INDEX_DIR):
    """
    Open the existing index, or create it if it does not exist yet.
    Useful for quick tests.
    """
    if not index_dir.exists():
        create_index(index_dir=index_dir)

    return index.open_dir(index_dir)


def build_prefix_query(query_str: str) -> str:
    """
    Convert a user query into a Whoosh prefix query after cleaning.

    Examples:
    - "le président" -> "president*"
    - "président du conseil" -> "president* conseil*"
    - "G. de Beauregard (Indre)" -> "beauregard* indre*"
    """
    tokens = query_tokens(query_str)

    if not tokens:
        return ""

    return " ".join(f"{token}*" for token in tokens)


def build_exact_query(query_str: str):
    """
    Build an exact-match query across search fields from normalized tokens.

    Example:
    - "Paul Doumer" -> exact AND query on "paul" and "doumer"
    """
    tokens = query_tokens(query_str)

    if not tokens:
        return None

    field_queries = []
    for field in SEARCH_FIELDS:
        token_queries = [whoosh_query.Term(field, token) for token in tokens]
        field_queries.append(whoosh_query.And(token_queries))

    return whoosh_query.Or(field_queries)


@lru_cache(maxsize=512)
def build_active_docnums_filter_cached(
    index_dir_str: str,
    session_date: Optional[str | int | date],
) -> Optional[set[int]]:
    """
    Precompute active Whoosh docnums for a date.

    Returns:
    - None if no date filter is requested
    - set[int] of active docnums otherwise

    Important:
    Whoosh accepts set[int] as a search filter, but not frozenset[int].
    """
    date_range = parse_partial_date_range(session_date)

    if date_range is None:
        return None

    index_dir = Path(index_dir_str)
    ix = get_index(index_dir)

    active_docnums: set[int] = set()

    with ix.searcher() as searcher:
        reader = searcher.reader()
        doc_count = reader.doc_count_all()

        for docnum in range(doc_count):
            is_deleted = False

            if hasattr(reader, "is_deleted"):
                is_deleted = reader.is_deleted(docnum)

            if is_deleted:
                continue

            try:
                fields = searcher.stored_fields(docnum)
            except Exception:
                continue

            if not fields:
                continue

            if is_active_during_hit(fields, date_range):
                active_docnums.add(docnum)

    return active_docnums


def build_active_docnums_filter(
    index_dir: Path,
    session_date: Optional[str | int | date],
) -> Optional[set[int]]:
    """
    Public wrapper for cached active docnum filter construction.
    """
    return build_active_docnums_filter_cached(str(index_dir), session_date)


def format_whoosh_datetime(value: Any) -> str:
    """Format Whoosh DATETIME values for output."""
    if isinstance(value, datetime):
        return value.date().isoformat()

    return str(value)


def result_to_dict(
    result,
    rank: int,
) -> dict[str, Any]:
    """
    Convert a Whoosh result hit to a JSON/API-friendly dictionary.
    """
    hit = dict(result)

    return {
        "rank": rank,
        "score": float(result.score),
        "person_id": hit["person_id"],
        "first_name": hit["first_name_display"],
        "last_name": hit["last_name_display"],
        "alias": hit["alias_display"],
        "position": hit["position_display"],
        "mandate_id": hit["mandate_id"],
        "role": hit["role_display"],
        "active_from": format_whoosh_datetime(hit["active_from"]),
        "active_until": format_whoosh_datetime(hit["active_until"]),
    }


class DecidonSearchEngine:
    """
    Persistent search engine suitable for DECIDON API usage.

    The index, searcher and parsers are initialized once.
    Date filters are precomputed from active docnums and cached.
    """

    def __init__(
        self,
        index_dir: Path = INDEX_DIR,
        bool_type: str = "AND",
    ):
        self.index_dir = index_dir
        self.bool_type = bool_type.upper()

        self.ix = get_index(index_dir)
        self.searcher = self.ix.searcher(
            weighting=scoring.BM25F(B=BM25_B, K1=BM25_K1)
        )

        self.parser = MultifieldParser(
            SEARCH_FIELDS,
            schema=self.ix.schema,
            group=AndGroup if self.bool_type == "AND" else OrGroup,
        )

        self.and_parser = MultifieldParser(
            SEARCH_FIELDS,
            schema=self.ix.schema,
            group=AndGroup,
        )

        self.or_parser = MultifieldParser(
            SEARCH_FIELDS,
            schema=self.ix.schema,
            group=OrGroup,
        )

    def close(self) -> None:
        self.searcher.close()

    @lru_cache(maxsize=4096)
    def get_query(self, query_str: str, mode: str = "DEFAULT"):
        """
        Parse and cache Whoosh query.

        mode:
        - DEFAULT: uses self.parser, according to self.bool_type
        - AND: forces AndGroup
        - OR: forces OrGroup
        """
        prefix_query = build_prefix_query(query_str)

        if not prefix_query:
            return None

        mode = mode.upper()

        if mode == "AND":
            return self.and_parser.parse(prefix_query)

        if mode == "OR":
            return self.or_parser.parse(prefix_query)

        return self.parser.parse(prefix_query)

    @lru_cache(maxsize=512)
    def get_active_filter(
        self,
        session_date: Optional[str | int | date],
    ) -> Optional[set[int]]:
        """
        Return a precomputed docnum filter for the requested date.

        None means no date filter.
        Empty set means no document is active.
        """
        return build_active_docnums_filter(self.index_dir, session_date)

    def cache_info(self) -> dict[str, Any]:
        """
        Return cache statistics.
        """
        return {
            "query_cache": self.get_query.cache_info(),
            "active_filter_cache": self.get_active_filter.cache_info(),
            "global_parse_partial_date_range_cache": parse_partial_date_range_cached.cache_info(),
            "global_active_docnums_filter_cache": build_active_docnums_filter_cached.cache_info(),
        }

    def _run_query(
        self,
        query,
        active_filter: Optional[set[int]],
        limit: int,
        match_strategy: str,
    ) -> list[dict[str, Any]]:
        """
        Execute a parsed Whoosh query and return formatted rows.
        """
        if query is None:
            return []

        results = self.searcher.search(
            query,
            limit=limit,
            filter=active_filter,
            groupedby=sorting.FieldFacet("person_id")
        )

        if not results:
            return []

        rows = [
            result_to_dict(result, rank)
            for rank, result in enumerate(results, start=1)
        ]

        for row in rows:
            row["match_strategy"] = match_strategy

        return rows

    def search(
            self,
            query_str: str,
            session_date: Optional[str | int | date] = None,
            limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search one query with safer fallback strategy.

        Strategy:
        1. Exact match
        2. Main search according to bool_type (AND by default)
        3. Strong token fallback, longest token first
        4. OR fallback as last

        This avoids noisy OR results caused by weak tokens.
        """
        active_filter = self.get_active_filter(session_date)

        if active_filter is not None and len(active_filter) == 0:
            return []

        # 1. Exact match first.
        exact_query = build_exact_query(query_str)
        rows = self._run_query(
            query=exact_query,
            active_filter=active_filter,
            limit=limit,
            match_strategy="EXACT",
        )
        if rows:
            return rows

        # 2. Main search: AND or OR according to self.bool_type.
        query = self.get_query(query_str, "DEFAULT")
        rows = self._run_query(
            query=query,
            active_filter=active_filter,
            limit=limit,
            match_strategy=self.bool_type,
        )

        if rows:
            return rows

        # 3. Strong token fallback first.
        # Example: "G. de Beauregard (Indre)" -> try "beauregard" before OR.
        tokens = sorted(query_tokens(query_str), key=len, reverse=True)

        for token in tokens:
            # Ignore weak short tokens in fallback.
            if len(token) < 4:
                continue

            query = self.get_query(token, "OR")
            rows = self._run_query(
                query=query,
                active_filter=active_filter,
                limit=limit,
                match_strategy=f"TOKEN_FALLBACK:{token}",
            )
            if rows:
                return rows

        # 4. OR fallback only as last resort.
        if self.bool_type != "OR":
            query = self.get_query(query_str, "OR")
            rows = self._run_query(
                query=query,
                active_filter=active_filter,
                limit=limit,
                match_strategy="OR_FALLBACK",
            )
            if rows:
                return rows

        return []


def run_date_tests() -> None:
    """
    Tests for partial date parsing.
    """
    tests = [
        (None, None),
        (1901, (date(1901, 1, 1), date(1901, 12, 31))),
        ("1901", (date(1901, 1, 1), date(1901, 12, 31))),
        ("1901-11", (date(1901, 11, 1), date(1901, 11, 30))),
        ("1901-11-04", (date(1901, 11, 4), date(1901, 11, 4))),
        (date(1901, 11, 4), (date(1901, 11, 4), date(1901, 11, 4))),
    ]

    for value, expected in tests:
        result = parse_partial_date_range(value)
        assert result == expected, f"{value!r}: expected {expected}, got {result}"

    invalid_values = [
        "1901-13",
        "1901-02-31",
        "abc",
        "190",
    ]

    for value in invalid_values:
        try:
            parse_partial_date_range(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{value!r} should have raised ValueError")

    print("Date tests OK")


def print_results(query: str, results: list[dict[str, Any]]) -> None:
    """
    Pretty print results for manual tests in tabular format.
    """
    print(f"Requête : {query!r}")

    if not results:
        print("Aucun résultat")
        return

    print(f"{len(results)} résultat(s)\n")

    columns = [
        ("rank", "RANK"),
        ("score", "SCORE"),
        ("person_id", "PERSON_ID"),
        ("first_name", "FIRST_NAME"),
        ("last_name", "LAST_NAME"),
        ("alias", "ALIAS"),
        ("position", "POSITION"),
        ("mandate_id", "MANDATE_ID"),
        ("role", "ROLE"),
        ("active_from", "ACTIVE_FROM"),
        ("active_until", "ACTIVE_UNTIL"),
        ("match_strategy", "STRATEGY"),
    ]

    rows = []
    for row in results:
        formatted = {
            "rank": str(row.get("rank", "")),
            "score": f"{row.get('score', 0.0):.4f}",
            "person_id": str(row.get("person_id", "")),
            "first_name": str(row.get("first_name", "")),
            "last_name": str(row.get("last_name", "")),
            "alias": str(row.get("alias", "")),
            "position": str(row.get("position", "")),
            "mandate_id": str(row.get("mandate_id", "")),
            "role": str(row.get("role", "")),
            "active_from": str(row.get("active_from", "")),
            "active_until": str(row.get("active_until", "")),
            "match_strategy": str(row.get("match_strategy", "")),
        }
        rows.append(formatted)

    widths: dict[str, int] = {}
    for key, label in columns:
        widths[key] = max(
            len(label),
            max((len(r[key]) for r in rows), default=0)
        )

    header = "  ".join(label.ljust(widths[key]) for key, label in columns)
    separator = "  ".join("-" * widths[key] for key, _ in columns)

    print(header)
    print(separator)

    for row in rows:
        line = "  ".join([
            row["rank"].rjust(widths["rank"]),
            row["score"].rjust(widths["score"]),
            row["person_id"].ljust(widths["person_id"]),
            row["first_name"].ljust(widths["first_name"]),
            row["last_name"].ljust(widths["last_name"]),
            row["alias"].ljust(widths["alias"]),
            row["position"].ljust(widths["position"]),
            row["mandate_id"].ljust(widths["mandate_id"]),
            row["role"].ljust(widths["role"]),
            row["active_from"].ljust(widths["active_from"]),
            row["active_until"].ljust(widths["active_until"]),
            row["match_strategy"].ljust(widths["match_strategy"]),
        ])
        print(line)

def run_single_query(
    query: str,
    session_date: Optional[str | int | date],
    bool_type: str,
    limit: int,
    show_cache_info: bool = False,
) -> None:
    """
    Simulate one API query.
    """
    engine = DecidonSearchEngine(
        bool_type=bool_type,
    )

    start = time_module.time()

    try:
        results = engine.search(
            query,
            session_date=session_date,
            limit=limit,
        )

        if show_cache_info:
            print("Cache info:", engine.cache_info())

    finally:
        engine.close()

    end = time_module.time()

    print_results(query, results)
    print(f"Temps requête : {end - start:.4f} secondes")


def load_batch_payload(filename: str) -> dict[str, Any]:
    """
    Load the new DECIDON batch payload format.

    Expected format:
    {
        "session_id": "...",
        "session_date": "1903-11-28",
        "occurrences": [
            {"source_id": "...", "str_ref": "Paul Doumer"},
            ...
        ]
    }
    """
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object.")

    if "occurrences" not in data or not isinstance(data["occurrences"], list):
        raise ValueError("JSON must contain an 'occurrences' list.")

    return data


def load_occurrences_from_json(filename: str) -> dict[str, Any]:
    """
    Return validated session metadata and cleaned occurrences.
    """
    data = load_batch_payload(filename)

    session_id = data.get("session_id")
    session_date = data.get("session_date")
    raw_occurrences = data["occurrences"]

    occurrences: list[dict[str, str]] = []

    for occ in raw_occurrences:
        if not isinstance(occ, dict):
            continue

        source_id = str(occ.get("source_id") or "").strip()
        str_ref = str(occ.get("str_ref") or "").strip()

        if not source_id or not str_ref:
            continue

        occurrences.append(
            {
                "source_id": source_id,
                "str_ref": str_ref,
            }
        )

    return {
        "session_id": session_id,
        "session_date": session_date,
        "occurrences": occurrences,
    }


def run_batch_json(
    filename: str,
    session_date: Optional[str | int | date],
    bool_type: str = "AND",
    limit: int = 10,
    verbose: bool = False,
    show_cache_info: bool = False,
) -> dict[str, Any]:
    """
    Simulate many API queries in a row from a JSON file.

    Output format:
    - one search per unique str_ref
    - preserve all source_id values attached to each str_ref
    """
    payload = load_occurrences_from_json(filename)
    occurrences = payload["occurrences"]

    if session_date is None:
        session_date = payload.get("session_date")

    grouped: dict[str, list[str]] = {}
    for occ in occurrences:
        str_ref = occ["str_ref"]
        source_id = occ["source_id"]

        if str_ref not in grouped:
            grouped[str_ref] = []

        grouped[str_ref].append(source_id)

    unique_refs = sorted(grouped.keys())

    print(f"Recherche dans {len(occurrences)} occurrences extraites du JSON")
    print(f"Chaînes uniques à chercher : {len(unique_refs)}")
    print(f"bool_type={bool_type}")
    print(f"session_date={session_date}")
    print("date_filter=precomputed active docnum filter")
    print("fallback=EXACT/AND/OR/token")
    print(f"limit={limit}\n")

    engine = DecidonSearchEngine(
        bool_type=bool_type,
    )

    results_by_group: list[dict[str, Any]] = []

    start = time_module.time()

    try:
        for str_ref in unique_refs:
            results = engine.search(
                str_ref,
                session_date=session_date,
                limit=limit,
            )

            group_row = {
                "str_ref": str_ref,
                "source_ids": grouped[str_ref],
                "results": results,
            }
            results_by_group.append(group_row)

            if verbose:
                print(f"str_ref={str_ref!r}")
                print(f"source_ids={grouped[str_ref]}")
                print_results(str_ref, results)
                print("==============\n")

        if show_cache_info:
            print("Cache info:", engine.cache_info())

    finally:
        engine.close()

    end = time_module.time()

    total_results = sum(len(item["results"]) for item in results_by_group)
    empty_queries = sum(1 for item in results_by_group if not item["results"])

    strategy_counts: dict[str, int] = {}

    for item in results_by_group:
        results = item["results"]
        if not results:
            continue

        strategy = results[0].get("match_strategy", "UNKNOWN")
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

    print(f"Temps total : {end - start:.2f} secondes")
    print(f"Temps moyen / chaîne unique : {(end - start) / max(len(unique_refs), 1):.4f} secondes")
    print(f"Résultats retournés : {total_results}")
    print(f"Chaînes sans résultat : {empty_queries}")
    print(f"Stratégies utilisées : {strategy_counts}")

    return {
        "session_id": payload.get("session_id"),
        "session_date": session_date,
        "results": results_by_group,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prosopography search with Whoosh + BM25F"
    )

    parser.add_argument(
        "--build-index",
        action="store_true",
        help="Rebuild Whoosh index from SQLite database.",
    )

    parser.add_argument(
        "--test-dates",
        action="store_true",
        help="Run date parsing tests.",
    )

    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Run a single query.",
    )

    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Run batch queries from a JSON file.",
    )

    parser.add_argument(
        "--session-date",
        type=str,
        default=None,
        help="Date filter: YYYY, YYYY-MM, YYYY-MM-DD, or omitted.",
    )

    parser.add_argument(
        "--bool-type",
        type=str,
        choices=["AND", "OR"],
        default="AND",
        help="Boolean mode for query terms.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results per query.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed results in batch mode.",
    )

    parser.add_argument(
        "--cache-info",
        action="store_true",
        help="Print LRU cache statistics.",
    )

    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Optional path to save batch results as JSON.",
    )

    args = parser.parse_args()

    if args.build_index:
        info = create_index()
        print(info)
        return

    if args.test_dates:
        run_date_tests()
        return

    if args.query:
        run_single_query(
            query=args.query,
            session_date=args.session_date,
            bool_type=args.bool_type,
            limit=args.limit,
            show_cache_info=args.cache_info,
        )
        return

    if args.json:
        output = run_batch_json(
            filename=args.json,
            session_date=args.session_date,
            bool_type=args.bool_type,
            limit=args.limit,
            verbose=args.verbose,
            show_cache_info=args.cache_info,
        )

        if args.output_json:
            with open(args.output_json, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            print(f"Résultats JSON écrits dans : {args.output_json}")

        return

    print("No action requested.")
    print("Examples:")
    print("  python3 app/index.py --build-index")
    print("  python3 app/index.py --test-dates")
    print("  python3 app/index.py --query 'jean jaurès' --session-date 1914-05-01")
    print("  python3 app/index.py --json 'app/2026-06-03-1903-11-28-INFER-SPK.json' --output-json 'app/2026-06-03-1903-11-28-INFER-SPK.linked.json'")

if __name__ == "__main__":
    main()