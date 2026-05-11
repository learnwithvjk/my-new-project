from flask import Flask, jsonify
from pathlib import Path
import os, requests, datetime

app = Flask(__name__)

API_URL = os.getenv("API_URL", "http://api:5012")
INPUT_FILE = Path("/shared/instructions.txt")
OUTPUT_FILE = Path("/shared/worker-output.log")

@app.get("/health")
def health():
    return jsonify(status="ok", api_url=API_URL)

@app.get("/sync")
def sync():
    try:
        host_text = INPUT_FILE.read_text().strip() if INPUT_FILE.exists() else "no host input file found"
    except Exception as e:
        host_text = f"error reading host file: {e}"

    try:
        r = requests.get(f"{API_URL}/hello", params={"name": "worker-repo"}, timeout=5)
        r.raise_for_status()
        api_data = r.json()
    except Exception as e:
        api_data = {"error": str(e)}

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        f"time={datetime.datetime.utcnow().isoformat()}Z\n"
        f"host_text={host_text}\n"
        f"api_data={api_data}\n"
    )

    return jsonify(
        status="synced",
        host_text=host_text,
        api_data=api_data,
        wrote_to=str(OUTPUT_FILE)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)