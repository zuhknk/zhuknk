"""SQLite 历史记录数据库"""

import sqlite3
import json
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "history.db")


def _get_conn():
    os.makedirs(DB_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """初始化数据库表"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            source_type TEXT DEFAULT 'unknown',
            analysis_goal TEXT DEFAULT '',
            reviews_count INTEGER DEFAULT 0,
            findings_count INTEGER DEFAULT 0,
            requirements_count INTEGER DEFAULT 0,
            testcases_count INTEGER DEFAULT 0,
            avg_rating REAL DEFAULT 0,
            created_at TEXT,
            result_json TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_analysis(data: dict) -> int:
    """保存分析结果，返回 ID"""
    conn = _get_conn()
    cursor = conn.execute("""
        INSERT INTO analyses (app_name, source_url, source_type, analysis_goal,
            reviews_count, findings_count, requirements_count, testcases_count,
            avg_rating, created_at, result_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("app_name", ""),
        data.get("source_url", ""),
        data.get("source_type", "unknown"),
        data.get("analysis_goal", ""),
        data.get("reviews_count", 0),
        data.get("findings_count", 0),
        data.get("requirements_count", 0),
        data.get("testcases_count", 0),
        data.get("avg_rating", 0),
        datetime.now().isoformat(),
        json.dumps(data.get("result", {}), ensure_ascii=False),
    ))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def list_analyses(limit: int = 50) -> list:
    """获取历史分析列表"""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT id, app_name, source_url, source_type, analysis_goal,
               reviews_count, findings_count, requirements_count, avg_rating, created_at
        FROM analyses ORDER BY created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "app_name": r[1], "source_url": r[2], "source_type": r[3],
            "analysis_goal": r[4], "reviews_count": r[5], "findings_count": r[6],
            "requirements_count": r[7], "avg_rating": r[8], "created_at": r[9],
        }
        for r in rows
    ]


def get_analysis(analysis_id: int) -> dict:
    """获取单条分析详情"""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()
    if not row:
        return {}
    return {
        "id": row[0], "app_name": row[1], "source_url": row[2],
        "source_type": row[3], "analysis_goal": row[4],
        "reviews_count": row[5], "findings_count": row[6],
        "requirements_count": row[7], "testcases_count": row[8],
        "avg_rating": row[9], "created_at": row[10],
        "result": json.loads(row[11]) if row[11] else {},
    }


def delete_analysis(analysis_id: int) -> bool:
    """删除一条分析记录"""
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted
