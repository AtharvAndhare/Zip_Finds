# api/server.py
"""
Flask API server — replaces the Streamlit frontend.
The React frontend calls these endpoints.

Run:  python -m api.server
"""

import sys
import os

# Ensure project root is on the path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from flask import Flask, request, jsonify
from flask_cors import CORS

from data_sources.zip_validator import is_valid_us_zip, normalize_zip
from core.aggregator import collect_all_data
from core.scoring_engine import compute_scores
from core.geo_utils import zip_to_latlon
from llm.narrative_generator import generate_narrative
from app.chatbot import answer_followup
from app.personas import PERSONAS
from db.zip_cache import clear_zip_cache

# ──────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Allow all origins so the React dev-server can reach the API


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _analyze_single_zip(zip_code: str, fresh: bool = False) -> dict:
    """Fetch + score + geo for one ZIP code.
    If fresh=True, clears cache first to force live API calls."""
    if fresh:
        clear_zip_cache(zip_code)
    raw_data = collect_all_data(zip_code)
    scores = compute_scores(raw_data)
    lat, lon = zip_to_latlon(zip_code)
    return {
        "zip_code": zip_code,
        "raw_data": raw_data,
        "scores": scores,
        "location": {"lat": lat, "lon": lon},
    }


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.route("/api/analyze/<zip_code>", methods=["GET"])
def analyze(zip_code: str):
    """Analyze a single ZIP code — returns raw data, scores, and location.
    Add ?fresh=true to bypass cache and fetch live data."""
    normalized = normalize_zip(zip_code)
    if not is_valid_us_zip(normalized):
        return jsonify({"error": "Invalid US ZIP code"}), 400

    fresh = request.args.get("fresh", "").lower() in ("true", "1", "yes")

    try:
        result = _analyze_single_zip(normalized, fresh=fresh)
        return jsonify(result)
    except Exception as e:
        print(f"[API] Error analyzing {normalized}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    """Clear all cached ZIP data. Use after updating scoring/data logic."""
    try:
        clear_zip_cache()
        return jsonify({"status": "ok", "message": "All cache cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/compare", methods=["GET"])
def compare():
    """Compare multiple ZIP codes. Query param: ?zips=07030,10001,07302"""
    zips_param = request.args.get("zips", "")
    zip_list = [z.strip() for z in zips_param.split(",") if z.strip()]

    if len(zip_list) < 2:
        return jsonify({"error": "Provide at least 2 ZIP codes (comma-separated)"}), 400

    if len(zip_list) > 5:
        return jsonify({"error": "Maximum 5 ZIP codes allowed"}), 400

    results = []
    for z in zip_list:
        normalized = normalize_zip(z)
        if not is_valid_us_zip(normalized):
            results.append({"zip_code": z, "error": f"Invalid ZIP: {z}"})
            continue
        try:
            results.append(_analyze_single_zip(normalized))
        except Exception as e:
            results.append({"zip_code": z, "error": str(e)})

    return jsonify(results)


@app.route("/api/chat", methods=["POST"])
def chat():
    """Chat / follow-up question about a ZIP code."""
    body = request.get_json(silent=True) or {}
    zip_code = body.get("zip_code", "")
    question = body.get("question", "")
    scores = body.get("scores", {})
    persona = body.get("persona", "General")

    if not zip_code or not question:
        return jsonify({"error": "zip_code and question are required"}), 400

    try:
        reply = answer_followup(zip_code, persona, scores, question)
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"[API] Chat error: {e}")
        return jsonify({"reply": f"Sorry, I encountered an error: {e}"}), 500


@app.route("/api/narrative", methods=["POST"])
def narrative():
    """Generate an AI narrative for a ZIP code."""
    body = request.get_json(silent=True) or {}
    zip_code = body.get("zip_code", "")
    scores = body.get("scores", {})
    persona = body.get("persona", "General")

    if not zip_code:
        return jsonify({"error": "zip_code is required"}), 400

    try:
        text = generate_narrative(zip_code, scores, persona)
        return jsonify({"narrative": text})
    except Exception as e:
        print(f"[API] Narrative error: {e}")
        return jsonify({"narrative": f"Unable to generate narrative: {e}"}), 500


@app.route("/api/personas", methods=["GET"])
def personas():
    """Return the list of available personas."""
    return jsonify({"personas": PERSONAS})


@app.route("/api/health", methods=["GET"])
def health_check():
    """Simple health check."""
    return jsonify({"status": "ok", "message": "Zip Finds API is running"})


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[API] Starting Zip Finds API on http://localhost:{port}")
    print(f"[API] Endpoints:")
    print(f"       GET  /api/analyze/<zip>")
    print(f"       GET  /api/compare?zips=zip1,zip2,...")
    print(f"       POST /api/chat")
    print(f"       POST /api/narrative")
    print(f"       GET  /api/personas")
    print(f"       GET  /api/health")
    app.run(host="0.0.0.0", port=port, debug=True)
