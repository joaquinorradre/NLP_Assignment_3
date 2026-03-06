import uuid
import boto3
import io
import pdfplumber
import docx
import chromadb
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from sentence_transformers import SentenceTransformer

documents_bp = Blueprint("documents", __name__)

# Cargamos el modelo de embeddings en memoria al iniciar la API.
# Este modelo (all-MiniLM-L6-v2) es muy ligero y rápido, ideal para CPU.
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{current_app.config['MINIO_ENDPOINT']}",
        aws_access_key_id=current_app.config["MINIO_ACCESS_KEY"],
        aws_secret_access_key=current_app.config["MINIO_SECRET_KEY"],
    )

def get_chroma_collection():
    """Conecta a ChromaDB y devuelve (o crea) la colección para nuestros documentos."""
    chroma_client = chromadb.HttpClient(
        host=current_app.config["CHROMA_HOST"],
        port=current_app.config["CHROMA_PORT"]
    )
    # Usamos la distancia del coseno, que es la recomendada para sentence-transformers
    return chroma_client.get_or_create_collection(
        name="rag_documents", 
        metadata={"hnsw:space": "cosine"}
    )

def extract_text_from_pdf(file_stream):
    text = ""
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text.strip()

def extract_text_from_docx(file_stream):
    doc = docx.Document(file_stream)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

def chunk_text(text, chunk_size=200, overlap=50):
    """
    Estrategia de Chunking: Ventana deslizante (Fixed-Size).
    Divide el texto en bloques de N palabras con un solapamiento para no cortar ideas.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
    return chunks

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
        # 1. Guardar archivo original en MinIO
        client = get_minio_client()
        try:
            client.head_bucket(Bucket=bucket_name)
        except Exception:
            client.create_bucket(Bucket=bucket_name)

        file.seek(0)
        content_type = "application/pdf" if ext == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        client.put_object(
            Bucket=bucket_name, Key=object_name, Body=file.read(), ContentType=content_type
        )
        
        # 2. Extracción de texto
        file.seek(0)
        if ext == "pdf":
            extracted_text = extract_text_from_pdf(file)
        else:
            extracted_text = extract_text_from_docx(file)
            
        if not extracted_text:
            client.delete_object(Bucket=bucket_name, Key=object_name)
            return jsonify({"error": "El documento no contiene texto extraíble."}), 400
        
        # 3. Chunking (Dividir en trozos manejables)
        chunks = chunk_text(extracted_text, chunk_size=200, overlap=50)
        
        # 4. Generar Embeddings y guardar en ChromaDB
        collection = get_chroma_collection()
        
        # Preparamos las listas que necesita ChromaDB
        chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"doc_id": doc_id, "filename": filename} for _ in range(len(chunks))]
        embeddings = embedder.encode(chunks).tolist() # Convertimos a lista normal de Python
        
        collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        
        return jsonify({
            "message": "Archivo indexado con éxito",
            "document_id": doc_id,
            "filename": filename,
            "chunks_created": len(chunks)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@documents_bp.route("/documents", methods=["GET"])
def list_documents():
    """Devuelve una lista con todos los documentos subidos."""
    try:
        client = get_minio_client()
        bucket_name = current_app.config["MINIO_BUCKET"]
        
        # Comprobar si el bucket existe, si no, devolvemos lista vacía
        try:
            client.head_bucket(Bucket=bucket_name)
        except Exception:
            return jsonify([]), 200

        response = client.list_objects_v2(Bucket=bucket_name)
        docs = []
        if "Contents" in response:
            for obj in response["Contents"]:
                # El nombre en MinIO lo guardamos como "uuid_nombredelarchivo.pdf"
                key = obj["Key"]
                parts = key.split("_", 1)
                if len(parts) == 2:
                    docs.append({
                        "id": parts[0],
                        "filename": parts[1],
                        "upload_date": obj["LastModified"].isoformat()
                    })
        return jsonify(docs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@documents_bp.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    """Borra un documento de MinIO y sus chunks de ChromaDB."""
    try:
        # 1. Borrar los chunks de ChromaDB
        collection = get_chroma_collection()
        collection.delete(where={"doc_id": doc_id})
        
        # 2. Borrar el archivo original de MinIO
        client = get_minio_client()
        bucket_name = current_app.config["MINIO_BUCKET"]
        
        # Como no sabemos el nombre exacto del archivo, buscamos por el ID (que es el prefijo)
        response = client.list_objects_v2(Bucket=bucket_name, Prefix=f"{doc_id}_")
        if "Contents" in response:
            for obj in response["Contents"]:
                client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                
        return jsonify({"message": f"Documento {doc_id} y sus chunks eliminados con éxito"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500