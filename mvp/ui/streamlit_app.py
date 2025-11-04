"""Streamlit UI for the offline-first medical writing assistant."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.exporter import build_docx, create_zip_bundle, export_json
from app.history import HistoryManager
from app.pipeline import DocumentPipeline
from app.utils import make_cache_key, sanitize_text

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
HISTORY_DIR = BASE_DIR / "history"
ensure_dirs = [LOG_DIR, HISTORY_DIR]
for directory in ensure_dirs:
    directory.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Med Writer (offline-first)", layout="wide")
st.title("🩺 Med Writer — Escrita Médica Assistida")
st.caption("Gere SOAP estruturado, documentos clínicos e exportações locais (Ollama opcional).")

if "pipeline" not in st.session_state:
    st.session_state["pipeline"] = DocumentPipeline()
if "session_notes" not in st.session_state:
    st.session_state["session_notes"] = ""
if "json_expanded" not in st.session_state:
    st.session_state["json_expanded"] = False
if "uploaded_ids" not in st.session_state:
    st.session_state["uploaded_ids"] = set()
if "extracted_texts" not in st.session_state:
    st.session_state["extracted_texts"] = []
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
if "payload_snapshot" not in st.session_state:
    st.session_state["payload_snapshot"] = {}

history_manager = HistoryManager(HISTORY_DIR)
if "session_file" not in st.session_state:
    st.session_state["session_file"] = history_manager.new_session_file()

pipeline: DocumentPipeline = st.session_state["pipeline"]


def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        import fitz  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("PyMuPDF não disponível (instale PyMuPDF)") from exc

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    textos = [page.get_text("text") for page in doc]
    return "\n".join(textos)


def extract_docx_text(file_bytes: bytes) -> str:
    import zipfile
    from xml.etree import ElementTree as ET

    with zipfile.ZipFile(BytesIO(file_bytes)) as docx:
        xml = docx.read('word/document.xml')
    root = ET.fromstring(xml)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    textos = [node.text for node in root.findall('.//w:t', ns) if node.text]
    return '
'.join(textos)


def extract_image_text(file_bytes: bytes) -> str:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("OCR não disponível (instale pytesseract + pillow)") from exc

    imagem = Image.open(BytesIO(file_bytes))
    return pytesseract.image_to_string(imagem, lang="por")


def handle_uploads(files: List[Any]) -> None:
    for file in files:
        raw = file.read()
        file_id = make_cache_key(file.name, params={"size": len(raw)})
        if file_id in st.session_state["uploaded_ids"]:
            continue
        texto_extraido = ""
        try:
            if file.type == "application/pdf" or file.name.lower().endswith(".pdf"):
                texto_extraido = extract_pdf_text(raw)
            elif file.type in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"} or file.name.lower().endswith(".docx"):
                texto_extraido = extract_docx_text(raw)
            elif file.type.startswith("image/") or file.name.lower().endswith((".png", ".jpg", ".jpeg")):
                try:
                    texto_extraido = extract_image_text(raw)
                except RuntimeError as exc:
                    st.info(f"OCR não disponível: {exc}")
            else:
                st.warning(f"Formato não suportado: {file.name}")
        except RuntimeError as exc:
            st.info(f"{exc}")
            continue
        except Exception as exc:
            st.error(f"Erro ao processar {file.name}: {exc}")
            continue
        if texto_extraido:
            st.session_state["uploaded_ids"].add(file_id)
            st.session_state["extracted_texts"].append(
                {
                    "id": file_id,
                    "nome": file.name,
                    "texto": sanitize_text(texto_extraido),
                }
            )


def append_to_input(texto: str) -> None:
    atual = st.session_state.get("texto_livre", "")
    st.session_state["texto_livre"] = (atual + "\n" + texto).strip()


def build_payload() -> Dict[str, Any]:
    bullets = [item.strip() for item in st.session_state.get("bullets_raw", "").splitlines() if item.strip()]
    payload: Dict[str, Any] = {
        "tipo_documento": st.session_state.get("tipo_documento", "SOAP"),
        "identificacao": {
            "nome": st.session_state.get("nome", ""),
            "cpf": st.session_state.get("cpf", ""),
            "cns": st.session_state.get("cns", ""),
        },
        "pessoa": {
            "idade": st.session_state.get("idade", 0),
            "sexo": st.session_state.get("sexo", "não informado"),
        },
        "queixa_principal": st.session_state.get("queixa", ""),
        "bullets": bullets,
        "sinais_vitais": {
            "temp": st.session_state.get("temp", ""),
            "pa": st.session_state.get("pa", ""),
            "fc": st.session_state.get("fc", ""),
        },
        "texto_livre": st.session_state.get("texto_livre", ""),
    }
    if st.session_state.get("cid"):
        payload["cid"] = st.session_state.get("cid")
    if st.session_state.get("dias_afastamento"):
        payload["dias_afastamento"] = st.session_state.get("dias_afastamento")
    if st.session_state.get("especialidade"):
        payload["especialidade"] = st.session_state.get("especialidade")
    if st.session_state.get("motivo"):
        payload["motivo"] = st.session_state.get("motivo")
    if st.session_state.get("achados_texto"):
        payload["achados_texto"] = st.session_state.get("achados_texto")
    return payload


def save_history(payload: Dict[str, Any], resultado: Dict[str, Any]) -> None:
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "payload": payload,
        "resultado": resultado,
        "notas": st.session_state.get("session_notes", ""),
        "hash": make_cache_key(json.dumps(payload, ensure_ascii=False, sort_keys=True)),
    }
    history_manager.append_record(Path(st.session_state["session_file"]), record)


def load_history_entry(entry: Dict[str, Any]) -> None:
    st.session_state["tipo_documento"] = entry["payload"].get("tipo_documento", "SOAP")
    ident = entry["payload"].get("identificacao", {})
    st.session_state["nome"] = ident.get("nome", "")
    st.session_state["cpf"] = ident.get("cpf", "")
    st.session_state["cns"] = ident.get("cns", "")
    pessoa = entry["payload"].get("pessoa", {})
    try:
        st.session_state["idade"] = int(pessoa.get("idade", 0))
    except (TypeError, ValueError):
        st.session_state["idade"] = 0
    st.session_state["sexo"] = pessoa.get("sexo", "não informado")
    st.session_state["queixa"] = entry["payload"].get("queixa_principal", "")
    st.session_state["bullets_raw"] = "\n".join(entry["payload"].get("bullets", []))
    sinais = entry["payload"].get("sinais_vitais", {})
    temp_val = sinais.get("temp", 0)
    try:
        st.session_state["temp"] = float(temp_val)
    except (TypeError, ValueError):
        st.session_state["temp"] = 0.0
    st.session_state["pa"] = sinais.get("pa", "")
    fc_val = sinais.get("fc", 0)
    try:
        st.session_state["fc"] = int(fc_val)
    except (TypeError, ValueError):
        st.session_state["fc"] = 0
    st.session_state["texto_livre"] = entry["payload"].get("texto_livre", "")
    st.session_state["cid"] = entry["payload"].get("cid", "")
    try:
        st.session_state["dias_afastamento"] = int(entry["payload"].get("dias_afastamento", 0))
    except (TypeError, ValueError):
        st.session_state["dias_afastamento"] = 0
    st.session_state["especialidade"] = entry["payload"].get("especialidade", "")
    st.session_state["motivo"] = entry["payload"].get("motivo", "")
    st.session_state["achados_texto"] = entry["payload"].get("achados_texto", "")
    st.session_state["session_notes"] = entry.get("notas", "")
    st.session_state["last_result"] = entry.get("resultado")
    if entry.get("resultado"):
        st.session_state["json_editor_text"] = json.dumps(entry["resultado"].get("json", {}), ensure_ascii=False, indent=2)


with st.sidebar:
    st.header("Assinatura e carimbo")
    st.session_state.setdefault("assinatura_habilitada", True)
    st.session_state.setdefault("assinatura_nome", "")
    st.session_state.setdefault("assinatura_crm", "")
    st.session_state.setdefault("assinatura_especialidade", "")
    st.session_state.setdefault("assinatura_uf", "")
    st.session_state.setdefault("assinatura_tamanho", 9)
    st.session_state["assinatura_habilitada"] = st.checkbox("Adicionar carimbo nos documentos", value=st.session_state["assinatura_habilitada"])
    st.session_state["assinatura_nome"] = st.text_input("Nome profissional", value=st.session_state["assinatura_nome"])
    st.session_state["assinatura_crm"] = st.text_input("CRM", value=st.session_state["assinatura_crm"])
    st.session_state["assinatura_uf"] = st.text_input("UF", value=st.session_state["assinatura_uf"])
    st.session_state["assinatura_especialidade"] = st.text_input("Especialidade", value=st.session_state["assinatura_especialidade"])
    st.session_state["assinatura_tamanho"] = st.slider("Tamanho do carimbo", min_value=6, max_value=14, value=int(st.session_state["assinatura_tamanho"]))

main_tab, history_tab = st.tabs(["Assistente", "Histórico"])

with main_tab:
    col_input, col_output = st.columns(2)

    with col_input:
        st.subheader("Entrada clínica")
        st.session_state.setdefault("tipo_documento", "SOAP")
        st.session_state["tipo_documento"] = st.selectbox(
            "Tipo de documento",
            ["SOAP", "ATESTADO", "ENCAMINHAMENTO", "PARECER", "LAUDO"],
            index=["SOAP", "ATESTADO", "ENCAMINHAMENTO", "PARECER", "LAUDO"].index(st.session_state["tipo_documento"]),
        )
        st.session_state.setdefault("nome", "")
        st.session_state.setdefault("cpf", "")
        st.session_state.setdefault("cns", "")
        st.session_state.setdefault("idade", 30)
        st.session_state.setdefault("sexo", "não informado")
        st.session_state.setdefault("queixa", "")
        st.session_state.setdefault("bullets_raw", "")
        st.session_state.setdefault("temp", 36.5)
        st.session_state.setdefault("pa", "")
        st.session_state.setdefault("fc", 72)
        st.session_state.setdefault("cid", "")
        st.session_state.setdefault("dias_afastamento", 3)
        st.session_state.setdefault("especialidade", "")
        st.session_state.setdefault("motivo", "")
        st.session_state.setdefault("achados_texto", "")
        st.text_input("Nome do paciente", key="nome")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("CPF", key="cpf")
            st.number_input("Idade", min_value=0, max_value=120, key="idade")
            st.text_input("PA", key="pa")
        with c2:
            st.text_input("CNS", key="cns")
            st.selectbox("Sexo", ["F", "M", "Outro", "não informado"], key="sexo")
            st.number_input("Temperatura (°C)", step=0.1, key="temp")
            st.number_input("FC (bpm)", step=1, key="fc")
        st.text_input("Queixa principal", key="queixa")
        st.text_area("Bullets clínicos (um por linha)", key="bullets_raw")

        if st.session_state["tipo_documento"] == "ATESTADO":
            st.text_input("CID", key="cid")
            st.number_input("Dias de afastamento", min_value=1, max_value=90, key="dias_afastamento")
        if st.session_state["tipo_documento"] == "ENCAMINHAMENTO":
            st.text_input("Especialidade de destino", key="especialidade")
        if st.session_state["tipo_documento"] in {"PARECER", "LAUDO"}:
            st.text_input("Motivo/Finalidade", key="motivo")
            st.text_area("Achados/Observações", key="achados_texto")

        st.text_area("Resumo clínico / Entrada livre", key="texto_livre", height=160)
        st.text_area("Notas pessoais (não enviadas à IA)", key="session_notes", height=120)

        uploaded_files = st.file_uploader(
            "Anexar PDF, DOCX ou imagem",
            type=["pdf", "docx", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
        )
        if uploaded_files:
            handle_uploads(uploaded_files)
        for item in st.session_state["extracted_texts"]:
            with st.expander(f"Texto extraído — {item['nome']}"):
                st.write(item["texto"])
                if st.button("Inserir na entrada", key=f"insere-{item['id']}"):
                    append_to_input(item["texto"])
                    st.success("Texto adicionado à entrada.")

        if st.button("Revisar e aprimorar texto"):
            if not st.session_state.get("texto_livre"):
                st.info("Inclua texto livre para revisão.")
            else:
                with st.spinner("Enviando para revisão..."):
                    revisado = pipeline.revise_text(st.session_state["texto_livre"])
                st.session_state["texto_livre"] = revisado.get("text", st.session_state["texto_livre"])
                st.success(f"Texto revisado ({revisado.get('provider')}).")

        if st.button("Gerar documento"):
            payload = build_payload()
            progress_bar = st.progress(0)
            progress_bar.progress(20, text="Preparando dados...")
            with st.spinner("Gerando documento..."):
                resultado = pipeline.generate(payload)
            progress_bar.progress(70, text="Aplicando validações...")
            st.session_state["last_result"] = resultado
            st.session_state["json_editor_text"] = json.dumps(resultado["json"], ensure_ascii=False, indent=2)
            st.session_state["payload_snapshot"] = payload
            save_history(payload, resultado)
            progress_bar.progress(100, text="Concluído!")
            st.success("Documento gerado com sucesso.")

    with col_output:
        st.subheader("Saída estruturada")
        if st.session_state.get("last_result"):
            resultado = st.session_state["last_result"]
            st.markdown(f"**Modelo utilizado:** {resultado.get('provider')}")
            st.markdown("### Texto clínico")
            st.text_area("Documento", value=resultado["texto"], height=260)

            st.markdown("### JSON (editável)")
            if st.button("Expandir JSON" if not st.session_state["json_expanded"] else "Colapsar JSON"):
                st.session_state["json_expanded"] = not st.session_state["json_expanded"]
            height = 400 if st.session_state["json_expanded"] else 220
            st.session_state["json_editor_text"] = st.text_area(
                "JSON estruturado",
                value=st.session_state.get("json_editor_text", json.dumps(resultado["json"], ensure_ascii=False, indent=2)),
                height=height,
            )
            try:
                parsed_json = json.loads(st.session_state["json_editor_text"])
            except json.JSONDecodeError:
                st.error("JSON inválido após edição.")
                parsed_json = resultado["json"]

            st.markdown("### Exportações")
            json_bytes = export_json(parsed_json)
            json_gz_bytes = export_json(parsed_json, compact=True, compress=True)
            docx_bytes = build_docx(resultado["texto"], {
                "habilitar": st.session_state["assinatura_habilitada"],
                "nome": st.session_state["assinatura_nome"],
                "crm": st.session_state["assinatura_crm"],
                "uf": st.session_state["assinatura_uf"],
                "especialidade": st.session_state["assinatura_especialidade"],
                "tamanho": st.session_state["assinatura_tamanho"],
            })
            zip_bytes, zip_path = create_zip_bundle(
                json_bytes,
                docx_bytes,
                {
                    "_meta": parsed_json.get("_meta", {}),
                    "payload": st.session_state.get("payload_snapshot", {}),
                    "notas": st.session_state.get("session_notes", ""),
                },
                base_name=st.session_state.get("tipo_documento", "documento"),
            )
            st.download_button("Baixar JSON", data=json_bytes, file_name="documento.json", mime="application/json")
            st.download_button("Baixar JSON compactado (.json.gz)", data=json_gz_bytes, file_name="documento.json.gz", mime="application/gzip")
            st.download_button("Baixar DOCX", data=docx_bytes, file_name="documento.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            st.download_button("Exportação rápida (ZIP)", data=zip_bytes, file_name="documentos.zip", mime="application/zip")
            st.info(f"ZIP também salvo em {zip_path.as_posix()}")

            if resultado.get("alertas"):
                st.markdown("### Alertas")
                for alerta in resultado["alertas"]:
                    st.warning(alerta)
        else:
            st.info("Preencha os dados à esquerda e clique em 'Gerar documento'.")

with history_tab:
    st.subheader("Sessões recentes")
    recentes = history_manager.list_recent()
    if not recentes:
        st.write("Histórico vazio por enquanto.")
    else:
        for idx, item in enumerate(recentes):
            cols = st.columns([3, 1])
            with cols[0]:
                st.write(f"**{item['label']}** — atualizado em {item['updated_at'].strftime('%d/%m %H:%M')}")
            with cols[1]:
                if st.button("Reabrir", key=f"reopen-{idx}"):
                    entry = history_manager.load_last_record(item["path"])
                    if entry:
                        load_history_entry(entry)
                        st.success("Sessão restaurada. Role para a aba principal.")
                        st.experimental_rerun()
