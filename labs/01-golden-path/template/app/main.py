"""Hello — the smallest service that can walk the whole golden path.

Three routes:
  /         a greeting, plus which pod answered and which version is running
  /healthz  used by Kubernetes readiness/liveness probes
  /add      a tiny bit of logic so there is something worth testing
"""
import os
import socket

from flask import Flask, jsonify, request

app = Flask(__name__)

APP_VERSION = os.environ.get("APP_VERSION", "dev")


def add(a: float, b: float) -> float:
    return a + b


@app.get("/")
def index():
    return jsonify(
        message="Hello from the DevOps Sandbox",
        version=APP_VERSION,
        served_by=socket.gethostname(),
    )


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/add")
def add_route():
    try:
        a = float(request.args.get("a", ""))
        b = float(request.args.get("b", ""))
    except ValueError:
        return jsonify(error="a and b must be numbers"), 400
    return jsonify(result=add(a, b))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
