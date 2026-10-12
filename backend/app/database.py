import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "runs.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            stage_message TEXT,
            timing_ms TEXT,
            source_filename TEXT,
            reference_filename TEXT,
            source_dims TEXT,
            ref_dims TEXT,
            modes TEXT,
            warnings TEXT,
            inlier_count INTEGER,
            candidate_count INTEGER,
            median_residual REAL,
            overlap_bbox TEXT,
            affine_params TEXT,
            config TEXT
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            metric_code TEXT NOT NULL,
            name TEXT NOT NULL,
            stage TEXT NOT NULL,
            image_role TEXT NOT NULL,
            raw_value REAL,
            raw_unit TEXT,
            display_index REAL,
            index_label TEXT,
            formula_id TEXT,
            formula_text TEXT,
            substituted_inputs TEXT,
            numerator REAL,
            denominator REAL,
            availability INTEGER NOT NULL,
            unavailable_reason TEXT,
            provenance TEXT,
            extra_data TEXT,
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            match_index INTEGER NOT NULL,
            source_x REAL NOT NULL,
            source_y REAL NOT NULL,
            ref_x REAL NOT NULL,
            ref_y REAL NOT NULL,
            pred_ref_x REAL,
            pred_ref_y REAL,
            distance REAL NOT NULL,
            ambiguity_ratio REAL NOT NULL,
            is_inlier INTEGER NOT NULL,
            residual REAL,
            rejection_reason TEXT,
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            checkpoint_id TEXT,
            source_x REAL NOT NULL,
            source_y REAL NOT NULL,
            ref_x REAL NOT NULL,
            ref_y REAL NOT NULL,
            pred_ref_x REAL,
            pred_ref_y REAL,
            residual REAL,
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_metrics_run_id ON metrics(run_id);
        CREATE INDEX IF NOT EXISTS idx_matches_run_id ON matches(run_id);
        CREATE INDEX IF NOT EXISTS idx_checkpoints_run_id ON checkpoints(run_id);
        """)

        # Backward-compatible migrations for existing runs.db tables
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(runs)")
        cols = [r[1] for r in cur.fetchall()]
        if "overlap_bbox" not in cols:
            cur.execute("ALTER TABLE runs ADD COLUMN overlap_bbox TEXT")
        if "affine_params" not in cols:
            cur.execute("ALTER TABLE runs ADD COLUMN affine_params TEXT")
        if "failure_reason" not in cols:
            cur.execute("ALTER TABLE runs ADD COLUMN failure_reason TEXT")
    conn.close()

def save_run(run_data: Dict[str, Any]):
    conn = get_db()
    with conn:
        conn.execute("""
        INSERT INTO runs (
            id, created_at, status, stage_message, timing_ms,
            source_filename, reference_filename, source_dims, ref_dims,
            modes, warnings, inlier_count, candidate_count, median_residual,
            overlap_bbox, affine_params, failure_reason, config
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status,
            stage_message=excluded.stage_message,
            timing_ms=excluded.timing_ms,
            source_dims=excluded.source_dims,
            ref_dims=excluded.ref_dims,
            modes=excluded.modes,
            warnings=excluded.warnings,
            inlier_count=excluded.inlier_count,
            candidate_count=excluded.candidate_count,
            median_residual=excluded.median_residual,
            overlap_bbox=excluded.overlap_bbox,
            affine_params=excluded.affine_params,
            failure_reason=excluded.failure_reason,
            config=excluded.config
        """, (
            run_data["id"],
            run_data["created_at"],
            run_data["status"],
            run_data.get("stage_message", ""),
            json.dumps(run_data.get("timing_ms", {})),
            run_data.get("source_filename", ""),
            run_data.get("reference_filename", ""),
            json.dumps(run_data.get("source_dims", [])),
            json.dumps(run_data.get("ref_dims", [])),
            json.dumps(run_data.get("modes", ["image"])),
            json.dumps(run_data.get("warnings", [])),
            run_data.get("inlier_count"),
            run_data.get("candidate_count"),
            run_data.get("median_residual"),
            json.dumps(run_data.get("overlap_bbox", [])) if run_data.get("overlap_bbox") else None,
            json.dumps(run_data.get("affine_params", {})) if run_data.get("affine_params") else None,
            run_data.get("failure_reason"),
            json.dumps(run_data.get("config", {}))
        ))
    conn.close()

def update_run_status(run_id: str, status: str, stage_message: str = "", warnings: Optional[List[str]] = None):
    conn = get_db()
    with conn:
        if warnings is not None:
            conn.execute("UPDATE runs SET status=?, stage_message=?, warnings=? WHERE id=?", 
                         (status, stage_message, json.dumps(warnings), run_id))
        else:
            conn.execute("UPDATE runs SET status=?, stage_message=? WHERE id=?", 
                         (status, stage_message, run_id))
    conn.close()

def save_metrics(run_id: str, metrics: List[Dict[str, Any]]):
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM metrics WHERE run_id=?", (run_id,))
        for m in metrics:
            conn.execute("""
            INSERT INTO metrics (
                run_id, metric_code, name, stage, image_role,
                raw_value, raw_unit, display_index, index_label,
                formula_id, formula_text, substituted_inputs,
                numerator, denominator, availability, unavailable_reason,
                provenance, extra_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                m["metric_code"],
                m["name"],
                m["stage"],
                m["image_role"],
                m.get("raw_value"),
                m.get("raw_unit", ""),
                m.get("display_index"),
                m.get("index_label", ""),
                m.get("formula_id", ""),
                m.get("formula_text", ""),
                json.dumps(m.get("substituted_inputs", {})),
                m.get("numerator"),
                m.get("denominator"),
                1 if m.get("availability", True) else 0,
                m.get("unavailable_reason"),
                m.get("provenance", "computed"),
                json.dumps(m.get("extra_data", {})) if m.get("extra_data") else None
            ))
    conn.close()

def save_matches(run_id: str, matches: List[Dict[str, Any]]):
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM matches WHERE run_id=?", (run_id,))
        for m in matches:
            conn.execute("""
            INSERT INTO matches (
                run_id, match_index, source_x, source_y, ref_x, ref_y,
                pred_ref_x, pred_ref_y, distance, ambiguity_ratio,
                is_inlier, residual, rejection_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                m["match_index"],
                m["source_x"],
                m["source_y"],
                m["ref_x"],
                m["ref_y"],
                m.get("pred_ref_x"),
                m.get("pred_ref_y"),
                m["distance"],
                m["ambiguity_ratio"],
                1 if m["is_inlier"] else 0,
                m.get("residual"),
                m.get("rejection_reason")
            ))
    conn.close()

def save_checkpoints(run_id: str, checkpoints: List[Dict[str, Any]]):
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM checkpoints WHERE run_id=?", (run_id,))
        for cp in checkpoints:
            conn.execute("""
            INSERT INTO checkpoints (
                run_id, checkpoint_id, source_x, source_y, ref_x, ref_y,
                pred_ref_x, pred_ref_y, residual
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                cp.get("checkpoint_id"),
                cp["source_x"],
                cp["source_y"],
                cp["ref_x"],
                cp["ref_y"],
                cp.get("pred_ref_x"),
                cp.get("pred_ref_y"),
                cp.get("residual")
            ))
    conn.close()

def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        conn.close()
        return None
    data = dict(row)
    data["timing_ms"] = json.loads(data["timing_ms"]) if data["timing_ms"] else {}
    data["source_dims"] = json.loads(data["source_dims"]) if data["source_dims"] else None
    data["ref_dims"] = json.loads(data["ref_dims"]) if data["ref_dims"] else None
    data["modes"] = json.loads(data["modes"]) if data["modes"] else ["image"]
    data["warnings"] = json.loads(data["warnings"]) if data["warnings"] else []
    data["overlap_bbox"] = json.loads(data["overlap_bbox"]) if data.get("overlap_bbox") else None
    data["affine_params"] = json.loads(data["affine_params"]) if data.get("affine_params") else None
    data["config"] = json.loads(data["config"]) if data["config"] else {}
    conn.close()
    return data

def list_runs(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["timing_ms"] = json.loads(d["timing_ms"]) if d["timing_ms"] else {}
        d["source_dims"] = json.loads(d["source_dims"]) if d["source_dims"] else None
        d["ref_dims"] = json.loads(d["ref_dims"]) if d["ref_dims"] else None
        d["modes"] = json.loads(d["modes"]) if d["modes"] else ["image"]
        d["warnings"] = json.loads(d["warnings"]) if d["warnings"] else []
        d["overlap_bbox"] = json.loads(d["overlap_bbox"]) if d.get("overlap_bbox") else None
        d["affine_params"] = json.loads(d["affine_params"]) if d.get("affine_params") else None
        d["config"] = json.loads(d["config"]) if d["config"] else {}
        results.append(d)
    conn.close()
    return results

def get_run_metrics(run_id: str) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM metrics WHERE run_id=? ORDER BY id ASC", (run_id,)).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["substituted_inputs"] = json.loads(d["substituted_inputs"]) if d["substituted_inputs"] else {}
        d["extra_data"] = json.loads(d["extra_data"]) if d["extra_data"] else None
        d["availability"] = bool(d["availability"])
        results.append(d)
    conn.close()
    return results

def get_run_matches(run_id: str, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM matches WHERE run_id=? ORDER BY match_index ASC LIMIT ? OFFSET ?", 
                        (run_id, limit, offset)).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["is_inlier"] = bool(d["is_inlier"])
        results.append(d)
    conn.close()
    return results

def get_run_checkpoints(run_id: str) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM checkpoints WHERE run_id=? ORDER BY id ASC", (run_id,)).fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results
