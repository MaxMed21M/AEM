# IA de Escrita Médica — Med Writer

Aplicação offline-first para **assistir a redação médica** em ambiente local.
Gera **SOAP estruturado (JSON + texto)** e documentos clínicos (Atestado, Encaminhamento, Parecer, Laudo).
Suporta modelos **Ollama** (preferencial) e, opcionalmente, **OpenAI API**. Sempre mantém um fallback determinístico.

## Destaques da versão

- Interface Streamlit com layout de duas colunas (Entrada/ Saída) e modo totalmente local.
- Upload de **PDF/DOCX/Imagem** com extração de texto (OCR opcional via `pytesseract`).
- Botão **“Revisar e aprimorar texto”** para polimento linguístico antes da geração.
- Campos de **assinatura/carimbo** na sidebar e aplicação automática em DOCX exportados.
- Exportação rápida para **JSON, JSON compactado (.json.gz), DOCX e ZIP** (ZIP inclui `soap.json`, `documento.docx` e `session.json`).
- **Histórico local** em `history/AAAA-MM-DD/session-<timestamp>.jsonl` com reabertura de sessões.
- Cache inteligente para respostas da IA (LRU 64 itens) e glossário regional (`st.cache_data`).
- Suporte opcional ao provedor OpenAI quando `OPENAI_API_KEY` está configurada.
- Testes básicos com `pytest` (schemas, glossário e exportação).

## Estrutura principal

```
app/
  exporter.py     # exportação DOCX/JSON/ZIP e carimbo
  history.py      # persistência simples em JSONL
  llm.py          # retries, cache, fallback determinístico
  pipeline.py     # orquestração de prompts/validação
  providers.py    # abstrações para Ollama e OpenAI
  prompts.py      # templates de geração e revisão
  schemas.py      # JSON Schemas e validadores
  utils.py        # glossário, hash, utilidades gerais
ui/
  streamlit_app.py  # interface principal
history/             # arquivos .jsonl por sessão
logs/                # `app.log` com chamadas à IA
```

## Requisitos

- Python **3.10+**
- (Opcional) [Ollama](https://ollama.com/) com modelo instruct (`qwen2.5:7b-instruct`, `llama3:8b-instruct`, etc.).
- (Opcional) `tesseract-ocr` instalado no sistema para uso do OCR (`pytesseract`).

### Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> Para OCR, instale o binário `tesseract-ocr` (Linux: `sudo apt install tesseract-ocr`; macOS: `brew install tesseract`).

Para extração de PDF e OCR, instale também (opcional):

```bash
pip install PyMuPDF pytesseract pillow
```

### Configuração opcional (.env)

Crie um arquivo `.env` (veja `.env.example`) com:

```
OPENAI_API_KEY=chave_opcional
```

Sem a variável, apenas o Ollama (quando disponível) e o fallback determinístico são utilizados.

## Execução

```bash
streamlit run ui/streamlit_app.py
```

A aplicação pode ser usada mesmo sem IA (modo determinístico). Quando Ollama ou OpenAI responderem, o histórico registra o provedor utilizado.

## Fluxo de uso (UI)

1. Preencha os dados do paciente e insira texto livre ou anexe arquivos para extração.
2. (Opcional) Clique em **“Revisar e aprimorar texto”** para polimento automático.
3. Clique em **“Gerar documento”** e acompanhe o progresso.
4. Revise o texto produzido, edite o JSON, ajuste notas pessoais e exporte os arquivos desejados.
5. Acesse a aba **Histórico** para reabrir sessões anteriores.

## Testes

```bash
pytest
```

Os testes cobrem validação de schemas JSON, normalização do glossário e rotinas de exportação (DOCX/ZIP/JSON).

## Notas

- Nenhum recurso de teletriagem foi implementado — foco exclusivo em documentação.
- Logs mínimos são registrados em `logs/app.log` para depuração de chamadas à IA.
- O cache em memória evita chamadas repetidas para entradas idênticas (chave SHA-256 dos dados normalizados + parâmetros).
