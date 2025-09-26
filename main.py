import json
import requests
from docx import Document
from tkinter import Tk, filedialog
from dotenv import load_dotenv
import os

load_dotenv()
WEBAPP_URL = os.getenv("WEBAPP_URL")

def docx_to_json(path):
    doc = Document(path)
    data = []
    question = None

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        # Pergunta (começa com número e contém ? ou .)
        if (text[0].isdigit() and ("?" in text or text.endswith("."))) or text.endswith("?"):
            if question:
                data.append(question)
            question = {"question": text, "options": [], "type": "multiple_choice"}
        
        # Alternativa (linha que começa com "( )")
        elif text.startswith("( )"):
            option = text.replace("( )", "").strip()
            if question:
                question["options"].append(option)

        else:
            # Caso seja pergunta aberta sem opções
            if question and not text.startswith("( )"):
                if not question["options"]:
                    question["type"] = "open"

    if question:
        data.append(question)

    return data


def main():
    # Abrir janela do Explorer para escolher o DOCX
    Tk().withdraw()  # esconde a janela principal
    file_path = filedialog.askopenfilename(
        title="Selecione o arquivo .docx",
        filetypes=[("Word Documents", "*.docx")]
    )

    if not file_path:
        print("Nenhum arquivo selecionado.")
        return

    questions = docx_to_json(file_path)

    if not WEBAPP_URL:
        print("❌ ERRO: WEBAPP_URL não encontrado no .env")
        return

    # Enviar JSON para o Apps Script
    response = requests.post(WEBAPP_URL, json=questions)

    try:
        data = response.json()
        print("🔗 Link para editar:", data.get("editUrl"))
        print("✅ Link para responder:", data.get("publishedUrl"))
    except Exception:
        print("Resposta inesperada:", response.text)

if __name__ == "__main__":
    main()