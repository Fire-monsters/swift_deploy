import os
import time
import random
from datetime import datetime
from flask import Flask, jsonify, request, g

app = Flask(__name__)

# Read environment variables
MODE = os.environ.get("MODE", "stable")
VERSION = os.environ.get("APP_VERSION", "1.0.0")
PORT = int(os.environ.get("APP_PORT", 3000))

# Chaos state (stored in memory)
chaos_state = {"mode": None, "duration": 0, "rate": 0.0}

# ─────────────────────────────────────────
# Middleware — runs before every request
# ─────────────────────────────────────────
@app.before_request
def apply_chaos():
    """Simulate degraded behavior if chaos is active"""
    if MODE != "canary":
        return  # chaos only works in canary mode

    if chaos_state["mode"] == "slow":
        time.sleep(chaos_state["duration"])

    elif chaos_state["mode"] == "error":
        if random.random() < chaos_state["rate"]:
            return jsonify({"error": "chaos error injected"}), 500

@app.after_request
def add_headers(response):
    """Add X-Mode header in canary mode"""
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    return response

# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({
        "message": f"Welcome to SwiftDeploy API",
        "mode": MODE,
        "version": VERSION,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

@app.route("/healthz")
def health():
    return jsonify({
        "status": "ok",
        "uptime": time.process_time()  # seconds process has been running
    })

@app.route("/chaos", methods=["POST"])
def chaos():
    # Only available in canary mode
    if MODE != "canary":
        return jsonify({"error": "chaos only available in canary mode"}), 403

    body = request.get_json()
    mode = body.get("mode")

    if mode == "slow":
        chaos_state["mode"] = "slow"
        chaos_state["duration"] = body.get("duration", 1)
        return jsonify({"chaos": "slow mode activated", "duration": chaos_state["duration"]})

    elif mode == "error":
        chaos_state["mode"] = "error"
        chaos_state["rate"] = body.get("rate", 0.5)
        return jsonify({"chaos": "error mode activated", "rate": chaos_state["rate"]})

    elif mode == "recover":
        chaos_state["mode"] = None
        chaos_state["duration"] = 0
        chaos_state["rate"] = 0.0
        return jsonify({"chaos": "recovered", "status": "normal"})

    return jsonify({"error": "unknown chaos mode"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)