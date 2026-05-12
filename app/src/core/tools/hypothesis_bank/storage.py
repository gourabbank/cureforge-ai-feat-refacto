# app/src/core/tools/hypothesis_bank/storage.py

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from app.src.utils.logger import get_logger

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

logger = get_logger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

DB_PATH = Path(".cache/hypothesis_bank/embeddings.db")
FAISS_PATH = Path(".cache/hypothesis_bank/faiss.index")
FAISS_ID_MAP_PATH = Path(".cache/hypothesis_bank/faiss_id_map.json")

_lock = threading.Lock()
_embedder = SentenceTransformer(EMBEDDING_MODEL)


# ── DB ────────────────────────────────────────────────────────────────────────

def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _init_db(db_path: Path):
    with _connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS hypotheses (
                id              TEXT PRIMARY KEY,
                disease         TEXT,
                phase_origin    TEXT,
                text            TEXT,
                keywords        TEXT,
                efficacy_score  REAL,
                safety_score    REAL,
                notes           TEXT,
                created_at      TEXT,
                updated_at      TEXT,
                retrieval_count INTEGER DEFAULT 0
            );
        """)


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if isinstance(d.get("keywords"), str):
        try:
            d["keywords"] = json.loads(d["keywords"])
        except Exception:
            d["keywords"] = []
    return d


# ── Embeddings ────────────────────────────────────────────────────────────────

def _embed(text: str) -> np.ndarray:
    return _embedder.encode([text], normalize_embeddings=True)[0].astype(np.float32)


def _load_faiss(faiss_path: Path, id_map_path: Path):
    if not FAISS_AVAILABLE:
        return None, []
    if faiss_path.exists() and id_map_path.exists():
        index = faiss.read_index(str(faiss_path))
        with open(id_map_path) as f:
            id_map = json.load(f)
    else:
        index = faiss.IndexFlatIP(EMBEDDING_DIM)
        id_map = []
    return index, id_map


def _save_faiss(index, id_map, faiss_path: Path, id_map_path: Path):
    if not FAISS_AVAILABLE or index is None:
        return
    faiss_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(faiss_path))
    with open(id_map_path, "w") as f:
        json.dump(id_map, f)


# ── Public API ────────────────────────────────────────────────────────────────

def add_hypothesis(
    text: str,
    disease: str,
    phase_origin: str = "unknown",
    keywords: list[str] = None,
    efficacy_score: float = 0.0,
    safety_score: float = 0.0,
    notes: str = "",
    db_path: Path = None,
    faiss_path: Path = None,
    id_map_path: Path = None,
) -> str:
    db_path = db_path or DB_PATH
    faiss_path = faiss_path or FAISS_PATH
    id_map_path = id_map_path or FAISS_ID_MAP_PATH

    _init_db(db_path)
    hyp_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    kw_str = json.dumps(keywords or [])
    vec = _embed(text)

    with _lock:
        with _connect(db_path) as conn:
            conn.execute(
                """INSERT INTO hypotheses
                   (id, disease, phase_origin, text, keywords,
                    efficacy_score, safety_score, notes, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (hyp_id, disease.lower().strip(), phase_origin, text, kw_str,
                 efficacy_score, safety_score, notes, now, now),
            )
        index, id_map = _load_faiss(faiss_path, id_map_path)
        if FAISS_AVAILABLE and index is not None:
            index.add(vec.reshape(1, -1))
            id_map.append(hyp_id)
            _save_faiss(index, id_map, faiss_path, id_map_path)

    logger.info(f"[HypothesisBank] Added {hyp_id} | disease={disease}")
    return hyp_id


def search_hypotheses(
    query: str,
    disease_filter: Optional[str] = None,
    keyword_filter: Optional[str] = None,
    top_k: int = 5,
    db_path: Path = None,
    faiss_path: Path = None,
    id_map_path: Path = None,
) -> list[dict]:
    db_path = db_path or DB_PATH
    faiss_path = faiss_path or FAISS_PATH
    id_map_path = id_map_path or FAISS_ID_MAP_PATH

    _init_db(db_path)
    query_vec = _embed(query).reshape(1, -1)

    with _lock:
        index, id_map = _load_faiss(faiss_path, id_map_path)

    if not FAISS_AVAILABLE or index is None or index.ntotal == 0:
        return []

    search_k = min(index.ntotal, top_k * 10 if (disease_filter or keyword_filter) else top_k)
    scores, indices = index.search(query_vec, search_k)

    results = []
    with _connect(db_path) as conn:
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(id_map):
                continue
            hyp_id = id_map[idx]
            row = conn.execute("SELECT * FROM hypotheses WHERE id=?", (hyp_id,)).fetchone()
            if row is None:
                continue
            entry = _row_to_dict(row)
            if disease_filter and entry["disease"] != disease_filter.lower().strip():
                continue
            if keyword_filter:
                kws = [k.lower() for k in entry["keywords"]]
                if keyword_filter.lower() not in kws:
                    continue
            entry["score"] = round(float(score), 4)
            results.append(entry)
            if len(results) >= top_k:
                break

    if results:
        with _lock:
            with _connect(db_path) as conn:
                conn.executemany(
                    "UPDATE hypotheses SET retrieval_count = retrieval_count + 1 WHERE id=?",
                    [(r["id"],) for r in results],
                )
    return results


def get_hypothesis(
    hyp_id: str,
    db_path: Path = None,
) -> Optional[dict]:
    db_path = db_path or DB_PATH

    _init_db(db_path)
    with _lock:
        with _connect(db_path) as conn:
            row = conn.execute("SELECT * FROM hypotheses WHERE id=?", (hyp_id,)).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE hypotheses SET retrieval_count = retrieval_count + 1 WHERE id=?",
                (hyp_id,),
            )
    return _row_to_dict(row)


def list_hypotheses(
    disease: Optional[str] = None,
    phase_filter: Optional[str] = None,
    limit: int = 20,
    db_path: Path = None,
) -> list[dict]:
    db_path = db_path or DB_PATH

    _init_db(db_path)
    query = "SELECT * FROM hypotheses WHERE 1=1"
    params: list = []
    if disease:
        query += " AND disease = ?"
        params.append(disease.lower().strip())
    if phase_filter:
        query += " AND phase_origin = ?"
        params.append(phase_filter.lower().strip())
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with _connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_scores(
    hyp_id: str,
    efficacy_score: float,
    safety_score: float,
    update_reason: str = "",
    db_path: Path = None,
) -> bool:
    db_path = db_path or DB_PATH

    _init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        with _connect(db_path) as conn:
            cursor = conn.execute(
                """UPDATE hypotheses
                   SET efficacy_score=?, safety_score=?,
                       notes = notes || ?,
                       updated_at=?
                   WHERE id=?""",
                (efficacy_score, safety_score,
                 f"\n[{now}] Score update: {update_reason}",
                 now, hyp_id),
            )
            return cursor.rowcount > 0


def export_to_markdown(
    disease: Optional[str] = None,
    db_path: Path = None,
) -> str:
    db_path = db_path or DB_PATH

    rows = list_hypotheses(disease=disease, limit=1000, db_path=db_path)
    if not rows:
        return "# Hypothesis Bank\n\n_No hypotheses found._\n"
    lines = ["# Hypothesis Bank\n"]
    if disease:
        lines.append(f"**Filter:** {disease}\n")
    lines.append(f"**Total:** {len(rows)}\n\n---\n")
    for r in rows:
        lines += [
            f"## {r['id'][:8]}… — {r['disease']}",
            f"**Phase:** {r['phase_origin']} | **Created:** {r['created_at'][:10]}",
            f"**Efficacy:** {r['efficacy_score']} | **Safety:** {r['safety_score']} | **Retrievals:** {r['retrieval_count']}",
            f"**Keywords:** {', '.join(r['keywords']) or 'none'}",
            f"\n{r['text']}\n",
            f"> {r['notes']}\n" if r.get("notes") else "",
            "---\n",
        ]
    return "\n".join(lines)