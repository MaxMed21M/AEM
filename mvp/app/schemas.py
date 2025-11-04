"""JSON Schemas for generated documents."""
from __future__ import annotations

from typing import Any, Dict

from jsonschema import Draft7Validator

IDENTIFICATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "nome": {"type": "string"},
        "cpf": {"type": "string"},
        "cns": {"type": "string"},
    },
    "additionalProperties": True,
}

SOAP_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["S", "O", "A", "P"],
    "properties": {
        "S": {"type": "string", "maxLength": 6000},
        "O": {"type": "string", "maxLength": 6000},
        "A": {"type": "array", "items": {"type": "string"}},
        "P": {"type": "array", "items": {"type": "string"}},
        "referencias": {"type": "array", "items": {"type": "string"}},
        "retorno_em_dias": {"type": "integer", "minimum": 0},
        "identificacao": IDENTIFICATION_SCHEMA,
    },
    "additionalProperties": True,
}

ATESTADO_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["texto", "cid", "dias_afastamento"],
    "properties": {
        "texto": {"type": "string", "maxLength": 4000},
        "cid": {"type": "string"},
        "dias_afastamento": {"type": "integer", "minimum": 0},
        "identificacao": IDENTIFICATION_SCHEMA,
    },
    "additionalProperties": True,
}

ENCAMINHAMENTO_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["texto"],
    "properties": {
        "texto": {"type": "string", "maxLength": 5000},
        "especialidade": {"type": "string"},
        "referencias": {"type": "array", "items": {"type": "string"}},
        "identificacao": IDENTIFICATION_SCHEMA,
    },
    "additionalProperties": True,
}

PARECER_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["texto"],
    "properties": {
        "texto": {"type": "string", "maxLength": 6000},
        "motivo": {"type": "string"},
        "conclusao": {"type": "array", "items": {"type": "string"}},
        "recomendacoes": {"type": "array", "items": {"type": "string"}},
        "anexos": {"type": "array", "items": {"type": "string"}},
        "identificacao": IDENTIFICATION_SCHEMA,
    },
    "additionalProperties": True,
}

LAUDO_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["texto"],
    "properties": {
        "texto": {"type": "string", "maxLength": 6000},
        "motivo": {"type": "string"},
        "achados": {"type": "array", "items": {"type": "string"}},
        "conclusao": {"type": "array", "items": {"type": "string"}},
        "recomendacoes": {"type": "array", "items": {"type": "string"}},
        "anexos": {"type": "array", "items": {"type": "string"}},
        "identificacao": IDENTIFICATION_SCHEMA,
    },
    "additionalProperties": True,
}

SCHEMA_MAP: Dict[str, Dict[str, Any]] = {
    "SOAP": SOAP_SCHEMA,
    "ATESTADO": ATESTADO_SCHEMA,
    "ENCAMINHAMENTO": ENCAMINHAMENTO_SCHEMA,
    "PARECER": PARECER_SCHEMA,
    "LAUDO": LAUDO_SCHEMA,
}


def get_schema(document_type: str) -> Dict[str, Any]:
    doc_type = document_type.upper()
    if doc_type not in SCHEMA_MAP:
        raise KeyError(f"Schema não encontrado para {document_type}")
    return SCHEMA_MAP[doc_type]


def validate_document(document_type: str, payload: Dict[str, Any]) -> None:
    schema = get_schema(document_type)
    Draft7Validator(schema).validate(payload)
