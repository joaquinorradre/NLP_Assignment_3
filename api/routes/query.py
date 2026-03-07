import requests
import chromadb
from flask import Blueprint, request, jsonify, current_app
from sentence_transformers import SentenceTransformer

query_bp = Blueprint("query", __name__)

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
        query_embedding = embedder.encode(user_query).tolist()

        collection = get_chroma_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=["documents", "metadatas", "distances"]
        )

        if not results["documents"] or not results["documents"][0]:
            return jsonify({
                "answer": "No hay documentos indexados. Por favor, sube un documento primero.", 
                "sources": []
            }), 200

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        context_text = ""
        sources = []
        
        for i in range(len(documents)):
            context_text += f"-- Fragmento {i+1} --\n{documents[i]}\n\n"
            
            relevance_score = 1.0 - distances[i]
            
            sources.append({
                "document_id": metadatas[i].get("doc_id"),
                "filename": metadatas[i].get("filename"),
                "chunk_text": documents[i],
                "relevance_score": round(relevance_score, 4)
            })

        system_prompt = "You are a helpful assistant. Answer the question concisely using ONLY the provided context."
        
        user_message = f"""Here is the context information:
---------------------
{context_text}
---------------------
Based on the context above, answer this question: {user_query}"""

        llm_url = f"{current_app.config['LLM_URL']}/v1/chat/completions"
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.1,
            "max_tokens": 150
        }

        response = requests.post(llm_url, json=payload, timeout=60)
        response.raise_for_status()
        
        llm_data = response.json()
        answer = llm_data["choices"][0]["message"]["content"].strip()

        return jsonify({
            "answer": answer,
            "sources": sources
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500