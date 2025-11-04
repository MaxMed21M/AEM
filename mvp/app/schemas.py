from typing import Dict, Any

IDENTIFICACAO_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "nome": {"type": "string"},
        "cpf": {"type": "string"},
        "cns": {"type": "string"},
    }
}

SOAP_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["S", "O", "A", "P"],
    "properties": {
        "S": {"type": "string", "maxLength": 4000},
        "O": {"type": "string", "maxLength": 4000},
        "A": {"type": "array", "items": {"type": "string"}},
        "P": {"type": "array", "items": {"type": "string"}},
        "referencias": {"type": "array", "items": {"type": "string"}},
        "retorno_em_dias": {"type": "integer"},
        "identificacao": IDENTIFICACAO_SCHEMA,
    },
}

ATESTADO_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["texto", "cid", "dias_afastamento"],
    "properties": {
        "texto": {"type": "string", "maxLength": 4000},
        "cid": {"type": "string"},
        "dias_afastamento": {"type": "integer"},
        "identificacao": IDENTIFICACAO_SCHEMA,
    },
}

ENCAMINHAMENTO_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["texto"],
    "properties": {
        "texto": {"type": "string", "maxLength": 5000},
        "especialidade": {"type": "string"},
        "referencias": {"type": "array", "items": {"type": "string"}},
        "identificacao": IDENTIFICACAO_SCHEMA,
    },
}

PARECER_SCHEMA = {
    "type": "object",
    "required": ["texto"],
    "properties": {
        "texto": {"type": "string", "maxLength": 6000},
        "motivo": {"type": "string"},
        "conclusao": {"type": "array", "items": {"type": "string"}},
        "recomendacoes": {"type": "array", "items": {"type": "string"}},
        "anexos": {"type": "array", "items": {"type": "string"}},
        "identificacao": IDENTIFICACAO_SCHEMA
    }
}

LAUDO_SCHEMA = {
    "type": "object",
    "required": ["texto"],
    "properties": {
        "texto": {"type": "string", "maxLength": 6000},
        "motivo": {"type": "string"},
        "achados": {"type": "array", "items": {"type": "string"}},
        "conclusao": {"type": "array", "items": {"type": "string"}},
        "recomendacoes": {"type": "array", "items": {"type": "string"}},
        "anexos": {"type": "array", "items": {"type": "string"}},
        "identificacao": IDENTIFICACAO_SCHEMA
    }
}

SCHEMAS = {
    "SOAP": SOAP_SCHEMA,
    "ATESTADO": ATESTADO_SCHEMA,
    "ENCAMINHAMENTO": ENCAMINHAMENTO_SCHEMA,
    "PARECER": PARECER_SCHEMA,
    "LAUDO": LAUDO_SCHEMA,
}