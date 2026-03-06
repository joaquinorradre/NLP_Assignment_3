import uuid
import boto3
import io
import pdfplumber
import docx
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

documents_bp = Blueprint("documents", __name__)

def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{current_app.config['MINIO_ENDPOINT']}",
        aws_access_key_id=current_app.config["MINIO_ACCESS_KEY"],
        aws_secret_access_key=current_app.config["MINIO_SECRET_KEY"],
    )

def extract_text_from_pdf(file_stream):
    """Extrae texto de un PDF. Devuelve un string vacío si es escaneado."""
    text = ""
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text.strip()

def extract_text_from_docx(file_stream):
    """Extrae texto de un archivo Word."""
    doc = docx.Document(file_stream)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

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
        
        file.seek(0) 
        if ext == "pdf":
            extracted_text = extract_text_from_pdf(file)
        else:
            extracted_text = extract_text_from_docx(file)
            
        if not extracted_text:
            client.delete_object(Bucket=bucket_name, Key=object_name)
            return jsonify({"error": "El documento no contiene texto extraíble. ¿Es un PDF escaneado?"}), 400
        
        # AQUÍ IRÁ EL CÓDIGO DE CHUNKING Y CHROMADB
        
        return jsonify({
            "message": "Archivo subido y texto extraído con éxito",
            "document_id": doc_id,
            "filename": filename,
            "text_preview": extracted_text[:200] + "..." 
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500