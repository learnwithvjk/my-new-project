from flask import Flask, jsonify, request
from pathlib import Path
import os, psycopg

app = Flask(__name__)
MESSAGE_FILE = Path("/data/message.txt")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/app")

def get_conn():
    return psycopg.connect(DATABASE_URL, autocommit=True)

# ensure table exists
with get_conn() as conn, conn.cursor() as cur:
    cur.execute("""
      CREATE TABLE IF NOT EXISTS visits (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        ts TIMESTAMPTZ DEFAULT now()
      );
    """)

@app.get("/health")
def health():
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        db_ok = True
    except Exception as e:
        db_ok = False
    return jsonify(status="ok", db_ok=db_ok)

@app.get("/hello")
def hello():
    name = request.args.get("name", "world")
    try:
        msg = MESSAGE_FILE.read_text().strip() if MESSAGE_FILE.exists() else "no host message found"
    except Exception as e:
        msg = f"error reading message: {e}"
    # record visit
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO visits(name) VALUES (%s) RETURNING id, ts", (name,))
            vid, ts = cur.fetchone()
    except Exception as e:
        vid, ts = None, str(e)
    return jsonify(message=f"hello, {name}", from_host=msg, visit={"id": vid, "ts": str(ts)})

@app.get("/visits")
def visits():
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, name, ts FROM visits ORDER BY id DESC LIMIT 50")
            rows = [{"id": r[0], "name": r[1], "ts": str(r[2])} for r in cur.fetchall()]
        return jsonify(rows)
    except Exception as e:
        return jsonify(error=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5012)
    