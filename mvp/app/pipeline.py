"""High-level orchestration for document generation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from jsonschema import ValidationError

from .llm import LLMClient, fallback_rule_based
from .schemas import get_schema, validate_document
from .validators import validar_regras


def _build_context(payload: Dict[str, Any]) -> str:
    pessoa = payload.get("pessoa") or {}
    ident = payload.get("identificacao") or {}
    sinais = payload.get("sinais_vitais") or {}
    nome = ident.get("nome", "Paciente")
    idade = pessoa.get("idade", "não informado")
    sexo = pessoa.get("sexo", "não informado")
    queixa = payload.get("queixa_principal", "não informado")
    pa = sinais.get("pa", "não informado")
    fc = sinais.get("fc", "não informado")
    temp = sinais.get("temp", "não informado")
    linhas = [
        f"{nome}, {sexo}, {idade} anos",
        f"Queixa principal: {queixa}",
        f"Sinais vitais: PA {pa}, FC {fc} bpm, Temp {temp} °C",
    ]
    return " | ".join(str(l) for l in linhas if l)


def _merge_dicts(preferred: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(fallback)
    for key, value in preferred.items():
        if value in (None, "", [], {}):
            continue
        merged[key] = value
    return merged


class DocumentPipeline:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()

    def generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        doc_type = (payload.get("tipo_documento") or "SOAP").upper()
        try:
            get_schema(doc_type)
        except KeyError as exc:
            raise ValueError(f"Tipo de documento não suportado: {doc_type}") from exc
        contexto = _build_context(payload)
        llm_result = self.llm.generate_document(doc_type, payload, contexto)
        text = llm_result.get("text") or ""
        json_out = llm_result.get("json") or {}
        fallback_text, fallback_json = fallback_rule_based(doc_type, payload)
        if not text:
            text = fallback_text
        if not json_out:
            json_out = fallback_json
        else:
            try:
                validate_document(doc_type, json_out)
            except ValidationError:
                json_out = _merge_dicts(json_out, fallback_json)
                validate_document(doc_type, json_out)
        alertas = validar_regras(doc_type, json_out, payload)
        meta = {
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "tipo_documento": doc_type,
            "provider": llm_result.get("provider", "fallback"),
        }
        json_out = {**json_out, "_meta": meta}
        return {
            "texto": text,
            "json": json_out,
            "alertas": alertas,
            "provider": llm_result.get("provider", "fallback"),
        }

    def revise_text(self, texto: str) -> Dict[str, Any]:
        return self.llm.revise_text(texto)
