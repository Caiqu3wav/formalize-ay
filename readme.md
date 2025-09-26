Converter .docx → Google Forms (automático)

Esse projeto permite que você selecione um arquivo .docx no seu PC, o script em Python lê e formata o questionário e envia automaticamente o JSON para um Google Apps Script WebApp que cria o Google Form pra você.

Abaixo segue tudo: código Python pronto, código do Apps Script, onde pegar a URL do WebApp e passo a passo para deploy, exemplos, troubleshooting e dicas de segurança.

1. Visão geral rápida

Rodar o form_uploader.py localmente.

Abrir o Explorer e selecionar o .docx.

O Python converte o .docx em JSON e faz POST para o WebApp do Apps Script.

O Apps Script cria o Formulário e devolve um JSON com dois links:

editUrl — link de edição (só dono pode editar)

publishedUrl — link público (responder)

2. Estrutura mínima de arquivos
meu_projeto/
 ├─ .env
 ├─ form_uploader.py
 └─ README.md

.env (exemplo)
WEBAPP_URL=https://script.google.com/macros/s/SEU_WEBAPP_ID/exec


IMPORTANTE: não versionar .env — adicione .env no .gitignore.

3. Código do Google Apps Script (WebApp)

Cole esse código numa nova Google Apps Script (https://script.google.com/
):

/**
 * doPost: recebe JSON com perguntas e cria um Google Form.
 * Retorna { editUrl, publishedUrl } em JSON.
 */
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents || "[]");

    // Nome do form (opcional — use data.title se existir)
    var formTitle = data.title || "Formulário Automático";
    var form = FormApp.create(formTitle);

    data.forEach(function(q) {
      var qtext = q.question || "";

      // se tiver opções -> multiple choice (padrão)
      if (q.options && q.options.length > 0) {
        // Se quiser checkbox (multi-resposta) detectar por heurística:
        // var isMulti = q.allowMultiple === true || (q.options.length > 5 && q.options.some(opt => /outra/i.test(opt)));
        // if (isMulti) { form.addCheckboxItem().setTitle(qtext).setChoiceValues(q.options); }
        // else { ...multiple choice... }

        form.addMultipleChoiceItem()
            .setTitle(qtext)
            .setChoiceValues(q.options);
      } else {
        // Pergunta aberta (texto)
        form.addParagraphTextItem().setTitle(qtext);
      }
    });

    var result = {
      editUrl: form.getEditUrl(),
      publishedUrl: form.getPublishedUrl()
    };

    return ContentService
            .createTextOutput(JSON.stringify(result))
            .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    var errObj = { error: err.toString() };
    return ContentService
            .createTextOutput(JSON.stringify(errObj))
            .setMimeType(ContentService.MimeType.JSON);
  }
}

Como implantar (passo a passo)

Acesse: https://script.google.com
 → Novo projeto.

Cole o código acima e salve (nome do projeto).

Clique em Deploy → New deployment.

Tipo: Web app.

Execute as: Me (executar como sua conta).

Who has access: Anyone ou Anyone, even anonymous (se quiser POST sem autenticação).

Clique em Deploy e autorize (vai pedir permissões).

Copie a Web App URL (termina com /exec). Esse é o WEBAPP_URL que você coloca no .env.

Se mudar o script depois, redeploy: Deploy → Manage deployments → Edit → Redeploy (ou criar nova deployment).

4. Código Python (local, abre Explorer e usa .env)

Instale dependências:

pip install python-docx requests python-dotenv


Salve como form_uploader.py:

import json
import requests
import os
import re
from docx import Document
from tkinter import Tk, filedialog
from dotenv import load_dotenv

load_dotenv()
WEBAPP_URL = os.getenv("WEBAPP_URL")

def is_question(text):
    text = text.strip()
    # numerada terminando com ? ou .  OR qualquer frase terminando com ?
    if re.match(r'^\d+\s', text) and (text.endswith('?') or text.endswith('.')):
        return True
    if text.endswith('?'):
        return True
    return False

def is_option(text):
    text = text.strip()
    if text.startswith("( )"):
        return True
    if re.match(r'^\d+\.\s+', text):  # "1. Opção"
        return True
    if re.match(r'^[\-\u2022]\s+', text):  # "- opção" ou "• opção"
        return True
    return False

def clean_option(text):
    # Remove prefixes tipo "( )", "1.", "-", "•"
    t = text.strip()
    t = re.sub(r'^\( ?\)\s*', '', t)            # "( ) "
    t = re.sub(r'^\d+\.\s*', '', t)             # "1. "
    t = re.sub(r'^[\-\u2022]\s*', '', t)        # "- " ou "• "
    return t.strip()

def docx_to_json(path):
    doc = Document(path)
    data = []
    question = None

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        if is_question(text):
            # começa nova pergunta
            if question:
                data.append(question)
            question = {"question": text, "options": [], "type": "multiple_choice"}
            continue

        if is_option(text):
            opt = clean_option(text)
            if not question:
                # cria pergunta implícita se não houver (caso raro)
                question = {"question": "Pergunta sem título", "options": [], "type": "multiple_choice"}
            question["options"].append(opt)
            continue

        # se chega aqui: linha comum / possivelmente continuação de pergunta
        if question and not question["options"]:
            # multiline question (continua a pergunta)
            question["question"] = question["question"] + " " + text
        else:
            # nova pergunta sem número (ex.: questionário sem numeração)
            if question:
                data.append(question)
            question = {"question": text, "options": [], "type": "multiple_choice"}

    if question:
        data.append(question)

    return data

def main():
    # Abrir janela do Explorer para escolher o DOCX
    Tk().withdraw()
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
    try:
        response = requests.post(WEBAPP_URL, json=questions, timeout=30)
    except Exception as e:
        print("Erro ao enviar para o Apps Script:", e)
        return

    try:
        data = response.json()
        if 'error' in data:
            print("Erro no Apps Script:", data['error'])
        else:
            print("🔗 Link para editar:", data.get("editUrl"))
            print("✅ Link para responder:", data.get("publishedUrl"))
    except ValueError:
        print("Resposta inesperada:", response.status_code, response.text)

if __name__ == "__main__":
    main()

5. Como deve ser o .docx (formato recomendado)

Para melhores resultados, siga esse padrão (mas o parser foi feito para ser razoavelmente flexível):

Pergunta numerada ou não:

1 Com que frequência você compra produtos na loja física Desafio Natureza?

ou O que você acha do atendimento?

Alternativas (cada alternativa em parágrafo próprio):

( ) 1. Nunca

( ) Raramente

1. Nunca (também detectado)

- Outra opção (também detectado)

Perguntas abertas: sem alternativas abaixo (serão transformadas em campo de texto).

Exemplo (no Word):

1 Com que frequência você compra produtos na loja física Desafio Natureza?

( ) 1. Nunca
( ) 2. Raramente
( ) 3. Ocasionalmente
( ) 4. Frequentemente

O que você gostaria que a Loja Desafio Natureza oferecesse para melhorar sua experiência em produtos e eventos de mountain bike?
( ) Mais opções de produtos e marcas
( ) Descontos e promoções exclusivas
( ) Outro (especifique)

6. Exemplo de saída (JSON) — seu questionario.docx

O script gera algo como:

[
  {
    "question": "1 Com que frequência você compra produtos na loja física Desafio Natureza?",
    "options": ["1. Nunca", "2. Raramente", "3. Ocasionalmente", "4. Frequentemente"],
    "type": "multiple_choice"
  },
  {
    "question": "2 É provável que eu compre produtos da loja antecipadamente ao evento.",
    "options": ["Improvável", "Pouco provável", "Neutro", "Provável", "Muito provável"],
    "type": "multiple_choice"
  },
  {
    "question": "O que você gostaria que a Loja Desafio Natureza oferecesse para melhorar sua experiência em produtos e eventos de mountain bike?",
    "options": ["Mais opções de produtos e marcas", "Descontos e promoções exclusivas", "..."],
    "type": "multiple_choice"
  }
]

7. Troubleshooting — problemas comuns

Resposta do Apps Script com link "inválido"

Verifique se você está usando publishedUrl (/viewform) e não editUrl (edição).

Garanta que o WebApp foi implantado com acesso público (se quer POST sem autenticação, escolha “Anyone, even anonymous” / “Anyone”).

Se receber 403/401: re-deploy e reautorize o Apps Script, ou ajuste o acesso.

Perguntas grudando (opções indo pra pergunta anterior)

Use o padrão sugerido no item 5; o parser tenta detectar linhas que terminam com ? ou linhas numeradas como novas perguntas.

Caso tenha muitos estilos diferentes no .docx, limpe a formatação (colar como texto simples) ou garanta cada item numa linha / parágrafo separado.

Apps Script retorna error

Abra o log (Executar → Ver registros / Executions) e veja o erro. O doPost também retorna { "error": "..." } em JSON.

Recebi status 200 mas sem publishedUrl

Confirme no Apps Script se form.getPublishedUrl() está sendo chamado; replique e redploy se necessário.

8. Segurança e boas práticas

Nunca faça commit do seu .env. Adicione .env ao .gitignore.

Se já adicionou .env no commit local, remova antes de dar push:

git rm --cached .env
echo ".env" >> .gitignore
git commit --amend --no-edit


Se já deu git push com o .env, aí a história precisa ser reescrita (git filter-branch/git filter-repo ou BFG) e trocar as chaves expostas.

O Apps Script cria formulários na conta que executa o script (sua conta). Se quer que um form apareça em outra conta: execute/deploy com essa conta.

9. Melhorias possíveis (sugestões)

Detectar automaticamente se uma pergunta deve ser Checkbox (multi-select) vs MultipleChoice.

Criar seções no Form baseado em títulos/linhas em negrito do .docx.

Suportar imagens e explicações (se o .docx tiver imagens).

Autenticar o POST (OAuth) para maior segurança (se não quiser permitir Anyone, even anonymous).

Interface gráfica simples (Tkinter) para escolher opções (nome do formulário, título).

10. Uso passo-a-passo final (resumido)

No Apps Script: cole o doPost do passo 3 → Deploy → New deployment → Web app → Execute as: Me → Who has access: Anyone, even anonymous → Copie a URL /exec.

No projeto local: crie .env com WEBAPP_URL=... (colado).

Instale libs: pip install python-docx requests python-dotenv.

Rode: python form_uploader.py → selecione o .docx.

Aguarde resposta no terminal — verá os links editUrl e publishedUrl.