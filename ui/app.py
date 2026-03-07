import gradio as gr
import requests
import os

API_URL = os.getenv("API_URL", "http://api:5000")

def get_documents_data():
    """Obtains raw data and formatted HTML table of documents."""
    try:
        response = requests.get(f"{API_URL}/documents")
        if response.status_code == 200:
            docs = response.json()
            if not docs:
                return "No documents indexed.", []
            
            html = "<table style='width:100%; border-collapse: collapse;'>"
            html += "<tr style='background-color: #f2f2f2;'><th style='padding:8px; text-align:left;'>Filename</th>"
            html += "<th style='padding:8px; text-align:left;'>Upload Date</th><th style='padding:8px; text-align:left;'>ID</th></tr>"
            for d in docs:
                html += f"<tr style='border-bottom: 1px solid #ddd;'><td style='padding:8px;'>📄 {d['filename']}</td>"
                html += f"<td style='padding:8px;'>{d['upload_date']}</td><td style='padding:8px;'><small>{d['id']}</small></td></tr>"
            html += "</table>"
            
            choices = [(f"{d['filename']} ({d['id'][:8]}...)", d['id']) for d in docs]
            return html, choices
        return "Error fetching documents.", []
    except:
        return "Connection error.", []

def upload_and_refresh(file):
    if file is None:
        table, choices = get_documents_data()
        return "No file selected.", table, gr.update(choices=choices)
    try:
        with open(file.name, "rb") as f:
            files = {"file": (os.path.basename(file.name), f)}
            requests.post(f"{API_URL}/documents", files=files)
        table, choices = get_documents_data()
        return "File indexed!", table, gr.update(choices=choices)
    except:
        table, choices = get_documents_data()
        return "Upload failed.", table, gr.update(choices=choices)

def delete_and_refresh(doc_id):
    if not doc_id:
        table, choices = get_documents_data()
        return "Select a document.", table, gr.update(choices=choices)
    try:
        requests.delete(f"{API_URL}/documents/{doc_id}")
        table, choices = get_documents_data()
        return "Document deleted.", table, gr.update(choices=choices, value=None)
    except:
        table, choices = get_documents_data()
        return "Delete failed.", table, gr.update(choices=choices)

def chat_fn(message, history):
    try:
        response = requests.post(f"{API_URL}/query", json={"query": message})
        return response.json().get("answer", "No answer found.")
    except:
        return "API Error."

with gr.Blocks(title="NLP RAG System") as demo:
    gr.Markdown("# 📚 Local RAG Document Manager")
    
    with gr.Tab("Manage Documents"):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 1. Ingestion")
                file_input = gr.File(label="Upload PDF/DOCX")
                upload_btn = gr.Button("Upload & Index", variant="primary")
                up_status = gr.Textbox(label="Status")
            
            with gr.Column(scale=2):
                gr.Markdown("### 2. Indexed Documents")
                doc_table_html = gr.HTML()
                
                gr.Markdown("---")
                gr.Markdown("### 3. Delete Documents")
                doc_selector = gr.Dropdown(label="Select document to delete")
                delete_btn = gr.Button("🗑️ Delete Selected Document", variant="stop")
                del_status = gr.Textbox(label="Action Result")

        demo.load(lambda: get_documents_data(), outputs=[doc_table_html, doc_selector])
        
        upload_btn.click(
            upload_and_refresh, 
            inputs=file_input, 
            outputs=[up_status, doc_table_html, doc_selector]
        )
        
        delete_btn.click(
            delete_and_refresh, 
            inputs=doc_selector, 
            outputs=[del_status, doc_table_html, doc_selector]
        )

    with gr.Tab("Chat System"):
        gr.ChatInterface(fn=chat_fn)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)