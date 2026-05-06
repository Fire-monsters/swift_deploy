import os
import time
import random
import threading
from datetime import datetime
from flask import Flask, jsonify, request, Response, g

app = Flask(__name__)

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────
MODE = os.environ.get("MODE", "stable")
VERSION = os.environ.get("APP_VERSION", "1.0.0")
PORT = int(os.environ.get("APP_PORT", 3000))
START_TIME = time.time()

# ─────────────────────────────────────────
# CHAOS STATE
# ─────────────────────────────────────────
chaos_state = {"mode": None, "duration": 0, "rate": 0.0}

# ─────────────────────────────────────────
# METRICS STATE
# ─────────────────────────────────────────
metrics = {
    "requests": {},    # {(method, path, status_code): count}
    "durations": [],   # list of (path, duration) tuples
}
metrics_lock = threading.Lock()

def record_request(method, path, status_code, duration):
    key = (method, path, str(status_code))
    with metrics_lock:
        metrics["requests"][key] = metrics["requests"].get(key, 0) + 1
        metrics["durations"].append((path, duration))
        # Keep last 1000 only
        if len(metrics["durations"]) > 1000:
            metrics["durations"].pop(0)

# ─────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────
@app.before_request
def start_timer():
    g.start_time = time.time()

@app.before_request
def apply_chaos():
    """Simulate degraded behavior in canary mode"""
    if MODE != "canary":
        return
    if chaos_state["mode"] == "slow":
        time.sleep(chaos_state["duration"])
    elif chaos_state["mode"] == "error":
        if random.random() < chaos_state["rate"]:
            return jsonify({"error": "chaos error injected"}), 500

@app.after_request
def after_request(response):
    """Record metrics and add headers after every request"""
    duration = time.time() - g.start_time
    record_request(
        request.method,
        request.path,
        response.status_code,
        duration
    )
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    return response

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({
        "message": "Welcome to SwiftDeploy API",
        "mode": MODE,
        "version": VERSION,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

@app.route("/healthz")
def health():
    return jsonify({
        "status": "ok",
        "uptime": time.time() - START_TIME
    })

@app.route("/chaos", methods=["POST"])
def chaos():
    if MODE != "canary":
        return jsonify({"error": "chaos only available in canary mode"}), 403

    body = request.get_json()
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    mode = body.get("mode")

    if mode == "slow":
        chaos_state["mode"] = "slow"
        chaos_state["duration"] = body.get("duration", 1)
        return jsonify({
            "chaos": "slow mode activated",
            "duration": chaos_state["duration"]
        })
    elif mode == "error":
        chaos_state["mode"] = "error"
        chaos_state["rate"] = body.get("rate", 0.5)
        return jsonify({
            "chaos": "error mode activated",
            "rate": chaos_state["rate"]
        })
    elif mode == "recover":
        chaos_state["mode"] = None
        chaos_state["duration"] = 0
        chaos_state["rate"] = 0.0
        return jsonify({"chaos": "recovered", "status": "normal"})

    return jsonify({"error": "unknown chaos mode"}), 400

@app.route("/metrics")
def metrics_endpoint():
    """
    Expose metrics in Prometheus text format.
    Prometheus format:
    # HELP metric_name Description
    # TYPE metric_name counter|gauge|histogram
    metric_name{label="value"} 123
    """
    uptime = time.time() - START_TIME
    app_mode_value = 1 if MODE == "canary" else 0
    chaos_value = {"slow": 1, "error": 2}.get(chaos_state["mode"], 0)

    # Standard Prometheus histogram buckets (in seconds)
    buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

    lines = []

    # ── http_requests_total ──
    lines.append("# HELP http_requests_total Total HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    with metrics_lock:
        requests_snapshot = dict(metrics["requests"])
        durations_snapshot = list(metrics["durations"])

    for (method, path, status), count in requests_snapshot.items():
        lines.append(
            f'http_requests_total{{method="{method}",'
            f'path="{path}",status_code="{status}"}} {count}'
        )

    # ── http_request_duration_seconds ──
    lines.append("# HELP http_request_duration_seconds Request duration histogram")
    lines.append("# TYPE http_request_duration_seconds histogram")

    all_durations = [d for _, d in durations_snapshot]
    total_count = len(all_durations)
    total_sum = sum(all_durations)

    for bucket in buckets:
        count_le = sum(1 for d in all_durations if d <= bucket)
        lines.append(
            f'http_request_duration_seconds_bucket{{le="{bucket}"}} {count_le}'
        )
    lines.append(
        f'http_request_duration_seconds_bucket{{le="+Inf"}} {total_count}'
    )
    lines.append(f'http_request_duration_seconds_sum {total_sum:.6f}')
    lines.append(f'http_request_duration_seconds_count {total_count}')

    # ── app_uptime_seconds ──
    lines.append("# HELP app_uptime_seconds Seconds since app started")
    lines.append("# TYPE app_uptime_seconds gauge")
    lines.append(f"app_uptime_seconds {uptime:.2f}")

    # ── app_mode ──
    lines.append("# HELP app_mode Current mode (0=stable 1=canary)")
    lines.append("# TYPE app_mode gauge")
    lines.append(f"app_mode {app_mode_value}")

    # ── chaos_active ──
    lines.append("# HELP chaos_active Chaos state (0=none 1=slow 2=error)")
    lines.append("# TYPE chaos_active gauge")
    lines.append(f"chaos_active {chaos_value}")

    return Response("\n".join(lines) + "\n", mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)