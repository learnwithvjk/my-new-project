from flask import Flask, jsonify, request
app = Flask(__name__)

@app.get("/health")
def health():
    return jsonify(status="ok")

@app.get("/hello")
def hello():
    name = request.args.get("name", "world")
    return jsonify(message=f"hello, {name}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5012)
