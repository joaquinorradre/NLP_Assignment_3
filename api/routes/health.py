import requests
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import chromadb
from flask import Blueprint, jsonify, current_app

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health():
    status = {}
    ok = True

    # ── MinIO ──────────────────────────────────────
    try:
        client = boto3.client(
            "s3",
            endpoint_url=f"http://{current_app.config['MINIO_ENDPOINT']}",
            aws_access_key_id=current_app.config["MINIO_ACCESS_KEY"],
            aws_secret_access_key=current_app.config["MINIO_SECRET_KEY"],
        )
        client.list_buckets()
        status["minio"] = "ok"
    except Exception as e:
        status["minio"] = f"error: {e}"
        ok = False

    # ── ChromaDB ───────────────────────────────────
    try:
        chroma = chromadb.HttpClient(
            host=current_app.config["CHROMA_HOST"],
            port=current_app.config["CHROMA_PORT"],
        )
        chroma.heartbeat()
        status["chromadb"] = "ok"
    except Exception as e:
        status["chromadb"] = f"error: {e}"
        ok = False

    # ── LLM ───────────────────────────────────────
    try:
        resp = requests.get(
            f"{current_app.config['LLM_URL']}/health",
            timeout=5
        )
        resp.raise_for_status()
        status["llm"] = "ok"
    except Exception as e:
        status["llm"] = f"error: {e}"
        ok = False

    http_code = 200 if ok else 503
    return jsonify({"status": "ok" if ok else "degraded", "services": status}), http_code