# 📚 NLP Assignment 3: Document Retrieval-Augmented Generation System

![Docker](https://img.shields.io/badge/docker-container-blue.svg)
![Flask](https://img.shields.io/badge/flask-api-lightgrey.svg)
![Gradio](https://img.shields.io/badge/gradio-ui-orange.svg)

**Authors:** Maria Goicoechea, Joaquin Orradre, Paula Pina

A complete, high-performance Retrieval-Augmented Generation (RAG) system designed to run entirely locally. This system allows users to upload PDF and Word documents and interact with them through a natural language interface, ensuring **100% data privacy** and **zero cloud costs**.

---

## 🏗️ System Architecture

The system is built using a microservices architecture orchestrated with Docker Compose:

| Service | Role | Port |
|---|---|---|
| **Flask API** | Central orchestrator: ingestion, parsing, RAG logic | `:5000` |
| **Gradio UI** | Web interface for document management and chat | `:7860` |
| **llama-server** | Local LLM inference via llama.cpp | `:8080` |
| **ChromaDB** | Vector database for semantic retrieval | `:8000` |
| **MinIO** | Object storage for raw document persistence | `:9000` |

---

## 🛠️ Prerequisites

- Docker and Docker Compose installed
- Runs entirely on **CPU** using quantized GGUF models

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/joaquinorradre/NLP_Assignment_3.git
cd NLP_Assignment_3
```

### 2. Download the Model

You must manually download the LLM weights in GGUF format:

1. Go to [Hugging Face](https://huggingface.co)
2. Download `Llama-3.2-1B-Instruct-Q4_K_M.gguf`
3. Place the file in the `./models/` directory
```
./models/Llama-3.2-1B-Instruct-Q4_K_M.gguf
```

### 3. Environment Configuration

Create a `.env` file in the root directory:
```env
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=password
MINIO_BUCKET=documents
MODEL_PATH=/models/Llama-3.2-1B-Instruct-Q4_K_M.gguf
```

### 4. Launch the System
```bash
docker compose up --build
```

- 🌐 **Gradio UI:** http://localhost:7860
- 🔌 **Flask API:** http://localhost:5000

---

## 📡 API Usage Examples

### Health Check
```bash
curl http://localhost:5000/health
```

### Upload a Document
Supports `.pdf` and `.docx`.
```bash
curl -X POST http://localhost:5000/documents \
  -F "file=@/path/to/your/document.pdf"
```

### Query the System
```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main findings of the document?"}'
```

### Delete a Document
```bash
curl -X DELETE http://localhost:5000/documents/<doc_id>
```

---

## 🔧 Technical Details

| Component | Details |
|---|---|
| **Ingestion** | `pdfplumber` for PDFs, `python-docx` for Word. Detects empty/scanned PDFs. |
| **Chunking** | Fixed-size (200 words) with 50-word overlap to preserve semantic context |
| **Retrieval** | Dense retrieval using `all-MiniLM-L6-v2` sentence embeddings + ChromaDB |
| **Grounding** | Strict system prompts + temperature `0.1` to prevent hallucinations |

---
