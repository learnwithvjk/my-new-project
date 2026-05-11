from flask import Flask, render_template_string, request
import os, requests

app = Flask(__name__)
API_URL = os.getenv("API_URL", "http://api:5012")

TEMPLATE = """
<html><body>
<h1>Web → API demo</h1>
<form method="get">
  <input name="name" placeholder="your name" value="{{name}}"/>
  <button>Say hello</button>
</form>
<pre>{{result}}</pre>
</body></html>
"""

@app.get("/")
def index():
    name = request.args.get("name", "docker learner")
    try:
        r = requests.get(f"{API_URL}/hello", params={"name": name}, timeout=3)
        r.raise_for_status()
        result = r.json()
    except Exception as e:
        result = {"error": str(e)}
    return render_template_string(TEMPLATE, name=name, result=result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
