import streamlit as st
import json
from typing import Any, Dict
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.pipeline import processar

st.set_page_config(page_title="IA de Escrita Médica - MVP", layout="centered")
st.title("🩺 IA de Escrita Médica — MVP v1.1.1")

with st.form("form"):
    tipo = st.selectbox("Tipo de documento", ["SOAP","ATESTADO","ENCAMINHAMENTO","PARECER","LAUDO"])
    st.markdown("### Identificação do paciente")
    nome = st.text_input("Nome completo", "")
    colid1, colid2 = st.columns(2)
    with colid1:
        cpf = st.text_input("CPF (somente números ou com pontuação)", "")
    with colid2:
        cns = st.text_input("CNS (15 dígitos)", "")

    st.markdown("### Dados clínicos")
    col1, col2 = st.columns(2)
    with col1:
        idade = st.number_input("Idade", min_value=0, max_value=120, value=42)
    with col2:
        sexo = st.selectbox("Sexo", ["F","M","Outro","Prefiro não informar"])
    queixa = st.text_input("Queixa principal", "cefaleia tensional")
    bullets_raw = st.text_area("Bullets (um por linha)", "3x/semana\nsem sinais de alarme\nlosartana 50 mg 12/12h")
    temp = st.number_input("Temperatura (°C)", value=36.6, step=0.1)
    pa = st.text_input("PA (ex.: 124/78)", "124/78")
    fc = st.number_input("FC (bpm)", value=74, step=1)

    # Campos específicos por tipo
    cid = ""
    dias = None
    especialidade = ""
    motivo = ""
    achados_texto = ""
    if tipo == "ATESTADO":
        st.markdown("### Atestado")
        cid = st.text_input("CID (ex.: M54.5)", "")
        dias = st.number_input("Dias de afastamento", min_value=1, max_value=30, value=3)
    elif tipo == "ENCAMINHAMENTO":
        st.markdown("### Encaminhamento")
        especialidade = st.text_input("Especialidade (ex.: Neurologia)", "")
    elif tipo in ("PARECER", "LAUDO"):
        st.markdown("### Motivo/Finalidade & Achados")
        motivo = st.text_input("Motivo/Finalidade", "")
        achados_texto = st.text_area("Achados/Observações (use ';' para separar itens)", "")

    submitted = st.form_submit_button("Gerar")

if submitted:
    bullets = [b.strip() for b in bullets_raw.splitlines() if b.strip()]
    payload: Dict[str, Any] = {
        "tipo_documento": tipo,
        "identificacao": {"nome": nome, "cpf": cpf, "cns": cns},
        "pessoa": {"idade": int(idade), "sexo": sexo},
        "queixa_principal": queixa,
        "bullets": bullets,
        "sinais_vitais": {"temp": float(temp), "pa": pa, "fc": int(fc)},
        "achados_exame": [],
        "hipoteses_previas": [],
        "preferencias_estilo": {"formalidade":"média","extensao":"curto"},
    }
    if tipo == "ATESTADO":
        payload["cid"] = cid
        payload["dias_afastamento"] = int(dias) if dias else None
    if tipo == "ENCAMINHAMENTO":
        payload["especialidade"] = especialidade
    if tipo in ("PARECER", "LAUDO"):
        payload["motivo"] = motivo
        payload["achados_texto"] = achados_texto

    with st.spinner("Gerando..."):
        saida = processar(payload)

    st.subheader("Texto sugerido")
    st.code(saida["texto"], language="markdown")

    st.subheader("JSON estruturado")
    st.json(saida["json"])

    if saida.get("alertas"):
        st.subheader("Alertas")
        for a in saida["alertas"]:
            st.warning(a)

    st.download_button("Baixar JSON", data=json.dumps(saida["json"], ensure_ascii=False, indent=2), file_name="documento.json", mime="application/json")
    st.download_button("Baixar texto (.txt)", data=saida["texto"], file_name="documento.txt", mime="text/plain")

st.caption("MVP offline-first • v1.1.1 • PARECER e LAUDO estruturados mesmo sem IA ativa.")