import uuid
import boto3
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

documents_bp = Blueprint("documents", __name__)

def get_minio_client():
    """Función auxiliar para conectarnos a MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=f"http://{current_app.config['MINIO_ENDPOINT']}",
        aws_access_key_id=current_app.config["MINIO_ACCESS_KEY"],
        aws_secret_access_key=current_app.config["MINIO_SECRET_KEY"],
    )

@documents_bp.route("/documents", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "No se ha enviado ningún archivo"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "El nombre del archivo está vacío"}), 400
        
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower()
    
    if ext not in ["pdf", "docx"]:
        return jsonify({"error": "Solo se permiten archivos PDF y DOCX"}), 400

    doc_id = str(uuid.uuid4())
    object_name = f"{doc_id}_{filename}"
    bucket_name = current_app.config["MINIO_BUCKET"]
    
    try:
        client = get_minio_client()
        
        try:
            client.head_bucket(Bucket=bucket_name)
        except Exception:
            client.create_bucket(Bucket=bucket_name)

        file.seek(0)
        content_type = "application/pdf" if ext == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
        client.put_object(
            Bucket=bucket_name,
            Key=object_name,
            Body=file.read(),
            ContentType=content_type
        )
        
        
        return jsonify({
            "message": "Archivo subido a MinIO con éxito",
            "document_id": doc_id,
            "filename": filename
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500