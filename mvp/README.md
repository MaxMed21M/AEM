
# IA de Escrita Médica — MVP (Offline-first)

MVP funcional para **assistente de redação clínica** com saída **texto + JSON**.
Focado em **APS**, com dicionário léxico simples e **validadores determinísticos**.

## Componentes
- `app/` — pipeline da IA (normalização, prompt, validadores, integração com LLM local via Ollama)
- `api/` — FastAPI com rota `/api/generate`
- `ui/` — app Streamlit simples para uso rápido em desktop
- `data/` — sinônimos e dicionários básicos

## Requisitos
- Python 3.10+
- (Opcional) **Ollama** rodando localmente (`http://localhost:11434`) com algum modelo *instruct* (ex.: `qwen2.5:7b-instruct` ou `llama3:8b-instruct`).

## Instalação
```bash
cd ia-escrita-medica-mvp
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1) Executar a API (opcional)
```bash
uvicorn api.main:app --reload --port 8008
```

### 2) Executar a UI (recomendado)
```bash
streamlit run ui/streamlit_app.py
```
> A UI usa diretamente o pipeline local (sem depender da API).

## Uso rápido (UI)
1. Escolha o **tipo de documento** (SOAP/ATESTADO/ENCAMINHAMENTO/PARECER/LAUDO).
2. Preencha idade/sexo e bullets (itens soltos).
3. Clique em **Gerar**. Revise o texto, veja alertas e baixe o JSON.

## Observações
- Se **Ollama** não estiver disponível, o sistema faz **fallback** para uma geração rule-based simples (texto determinístico).
- **Este MVP não toma decisão clínica**; apenas auxilia na **redação padronizada**.
- Integração ao PEC: copie o **TEXTO** para o campo apropriado e/ou use o **JSON** para BI.

## Estrutura
```
ia-escrita-medica-mvp/
  app/
    __init__.py
    pipeline.py
    normalizer.py
    templates.py
    validators.py
    llm.py
    schemas.py
  api/
    main.py
  ui/
    streamlit_app.py
  data/
    synonyms_ptbr.json
  requirements.txt
  README.md
```
