import requests
import chromadb
from flask import Blueprint, request, jsonify, current_app
from sentence_transformers import SentenceTransformer

query_bp = Blueprint("query", __name__)

# Cargamos el mismo modelo de embeddings para entender la pregunta
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def get_chroma_collection():
    chroma_client = chromadb.HttpClient(
        host=current_app.config["CHROMA_HOST"],
        port=current_app.config["CHROMA_PORT"]
    )
    return chroma_client.get_or_create_collection(
        name="rag_documents", 
        metadata={"hnsw:space": "cosine"}
    )

@query_bp.route("/query", methods=["POST"])
def query_system():
    data = request.json
    if not data or "query" not in data:
        return jsonify({"error": "Falta el campo 'query' en el JSON"}), 400

    user_query = data["query"]

    try:
        # 1. Convertir la pregunta en un vector (Embedding)
        query_embedding = embedder.encode(user_query).tolist()

        # 2. Buscar en ChromaDB los 3 fragmentos más relevantes (Top-k = 3)
        collection = get_chroma_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=["documents", "metadatas", "distances"]
        )

        # Si ChromaDB no tiene documentos, devolvemos un aviso
        if not results["documents"] or not results["documents"][0]:
            return jsonify({
                "answer": "No hay documentos indexados. Por favor, sube un documento primero.", 
                "sources": []
            }), 200

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        # 3. Preparar el contexto y la lista de fuentes (Requisito de la tarea)
        context_text = ""
        sources = []
        
        for i in range(len(documents)):
            context_text += f"-- Fragmento {i+1} --\n{documents[i]}\n\n"
            
            # La distancia del coseno en ChromaDB va de 0 a 1 (0 es idéntico). 
            # Lo invertimos (1 - distancia) para que sea una puntuación de "similitud".
            relevance_score = 1.0 - distances[i]
            
            sources.append({
                "document_id": metadatas[i].get("doc_id"),
                "filename": metadatas[i].get("filename"),
                "chunk_text": documents[i],
                "relevance_score": round(relevance_score, 4)
            })

        # 4. Construir el Prompt separando System y User
        system_prompt = f"""You are a precise and helpful assistant. 
Your task is to answer the user's question using ONLY the information in the context provided below.
If the context does not contain the exact answer, simply output: "I don't know". Do not invent anything.

Context Information:
{context_text}"""

        # 5. Llamar al servidor local de llama.cpp usando el formato Chat correcto
        llm_url = f"{current_app.config['LLM_URL']}/v1/chat/completions"
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            "temperature": 0.0, # Temperatura a 0 para máxima precisión y cero creatividad
            "max_tokens": 150
        }

        response = requests.post(llm_url, json=payload, timeout=60)
        response.raise_for_status()
        
        # Extraer la respuesta del JSON que devuelve llama.cpp
        llm_data = response.json()
        answer = llm_data["choices"][0]["message"]["content"].strip()

        # Devolver la respuesta final al usuario junto con las fuentes
        return jsonify({
            "answer": answer,
            "sources": sources
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500