"""
app.py — Flask backend for Personal Finance Advisor.

Routes:
  POST /api/upload        — Upload CSV/PDF bank statement
  POST /api/chat          — Chat with finance advisor
  GET  /api/summary       — Get financial summary for current session
  GET  /api/sample-csv    — Download sample CSV for testing
  GET  /api/health        — Health check
  GET  /                  — Serve frontend
"""

import os
import json
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

from data_processor import parse_csv, parse_pdf, compute_financial_summary, summary_to_text, generate_sample_csv
from anomaly_detector import full_anomaly_report, anomalies_to_text
from rag_pipeline import generate_advice, generate_initial_analysis, build_knowledge_index

# ─── APP SETUP ────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "financeadvisor-dev-secret-2024")
CORS(app, supports_credentials=True)

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB max

ALLOWED_EXTENSIONS = {"csv", "pdf"}

# In-memory session store (use Redis for production)
_sessions: dict = {}

# ─── STARTUP ──────────────────────────────────────────────────────────────────

@app.before_request
def startup_once():
    """Build knowledge index on first request (deferred to avoid blocking)."""
    if not hasattr(app, "_kb_built"):
        # Mark as built to avoid repeated attempts
        app._kb_built = True
        # Don't block the request - knowledge base will be initialized on-demand
        # This prevents the first request from timing out
        try:
            app.logger.info("💡 Knowledge base will be initialized on first API call...")
        except Exception as e:
            app.logger.warning(f"⚠️  Startup warning: {e}")


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_session_id() -> str:
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def get_session_data(session_id: str) -> dict:
    return _sessions.get(session_id, {})


def set_session_data(session_id: str, data: dict):
    _sessions[session_id] = data


# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "api_key_set": bool(os.environ.get("OPENAI_API_KEY")),
        "kb_built": hasattr(app, "_kb_built"),
    })


@app.route("/api/sample-csv")
def sample_csv():
    """Generate and return a sample CSV for demo."""
    csv_content = generate_sample_csv()
    import io
    return send_file(
        io.BytesIO(csv_content.encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="sample_bank_statement.csv"
    )


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Upload and process bank statement CSV or PDF."""
    session_id = get_session_id()

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Only CSV and PDF files are supported"}), 400

    try:
        file_content = file.read()
        ext = file.filename.rsplit(".", 1)[1].lower()

        if ext == "csv":
            df = parse_csv(file_content)
        else:
            df = parse_pdf(file_content)

        summary = compute_financial_summary(df)
        anomaly_report = full_anomaly_report(df, summary)

        summary_text = summary_to_text(summary)
        anomaly_text = anomalies_to_text(anomaly_report)

        # Store in session
        set_session_data(session_id, {
            "df_json": df.drop(columns=["month"], errors="ignore").to_json(orient="records", date_format="iso"),
            "summary": summary,
            "summary_text": summary_text,
            "anomaly_report": anomaly_report,
            "anomaly_text": anomaly_text,
            "conversation_history": [],
        })

        # Generate initial analysis
        api_key = os.environ.get("OPENAI_API_KEY", "")
        initial_analysis = None
        if api_key:
            result = generate_initial_analysis(summary_text, anomaly_text)
            if result["success"]:
                initial_analysis = result["response"]
                # Add to history
                session_data = get_session_data(session_id)
                session_data["conversation_history"].append({
                    "role": "assistant",
                    "content": initial_analysis
                })
                set_session_data(session_id, session_data)

        # Prepare chart data
        chart_data = {
            "categoryBreakdown": [
                {"name": cat, "value": round(amt, 2), "pct": summary["category_pct"].get(cat, 0)}
                for cat, amt in summary["category_spend"].items()
            ],
            "monthlyTrend": [
                {"month": m, "spend": round(v, 2), "income": round(summary["monthly_income"].get(m, 0), 2)}
                for m, v in summary["monthly_spend"].items()
            ],
            "momChanges": [
                {"category": cat, "change": chg}
                for cat, chg in sorted(summary["mom_changes"].items(), key=lambda x: x[1], reverse=True)
            ]
        }

        return jsonify({
            "success": True,
            "summary": {
                "latest_month": summary["latest_month"],
                "total_income": summary["total_income"],
                "total_spend": summary["total_spend"],
                "savings": summary["savings"],
                "savings_rate": summary["savings_rate"],
                "transaction_count": summary["transaction_count"],
                "months_available": summary["months_available"],
            },
            "anomalies": {
                "alert_count": anomaly_report["alert_count"],
                "has_critical": anomaly_report["has_critical"],
                "all_alerts": anomaly_report["all_alerts"][:6],
                "transaction_anomalies": anomaly_report["transaction_anomalies"][:3],
            },
            "chart_data": chart_data,
            "initial_analysis": initial_analysis,
            "session_id": session_id,
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 422
    except Exception as e:
        app.logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Processing failed: {str(e)}"}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """Chat endpoint — RAG-powered financial advice."""
    session_id = get_session_id()
    session_data = get_session_data(session_id)

    if not session_data:
        return jsonify({
            "success": False,
            "error": "No financial data loaded. Please upload your bank statement first."
        }), 400

    body = request.get_json()
    if not body or "message" not in body:
        return jsonify({"success": False, "error": "No message provided"}), 400

    user_message = body["message"].strip()
    if not user_message:
        return jsonify({"success": False, "error": "Empty message"}), 400

    if not os.environ.get("OPENAI_API_KEY"):
        return jsonify({
            "success": False,
            "error": "OPENAI_API_KEY not configured. Please set it in your .env file."
        }), 500

    try:
        # Add user message to history
        history = session_data.get("conversation_history", [])
        history.append({"role": "user", "content": user_message})

        result = generate_advice(
            user_query=user_message,
            financial_summary_text=session_data["summary_text"],
            anomaly_text=session_data["anomaly_text"],
            conversation_history=history[:-1],  # all except current user msg
        )

        if result["success"]:
            # Add assistant response to history
            history.append({"role": "assistant", "content": result["response"]})
            session_data["conversation_history"] = history[-12:]  # keep last 6 turns
            set_session_data(session_id, session_data)

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/summary")
def get_summary():
    """Return current session's financial summary."""
    session_id = get_session_id()
    session_data = get_session_data(session_id)
    if not session_data:
        return jsonify({"success": False, "error": "No data loaded"}), 404
    return jsonify({"success": True, "summary": session_data.get("summary", {})})


@app.route("/api/anomalies")
def get_anomalies():
    """Return anomaly report for current session."""
    session_id = get_session_id()
    session_data = get_session_data(session_id)
    if not session_data:
        return jsonify({"success": False, "error": "No data loaded"}), 404
    return jsonify({"success": True, "anomalies": session_data.get("anomaly_report", {})})


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    print(f"\n🚀 Finance Advisor running at http://localhost:{port}")
    print(f"   API key set: {bool(os.environ.get('OPENAI_API_KEY'))}")
    # Disable watchdog reloader on Windows to prevent continuous restarts from transformers lib
    app.run(debug=debug, port=port, host="0.0.0.0", use_reloader=False)