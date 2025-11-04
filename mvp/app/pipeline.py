from typing import Dict, Any, Tuple
from jsonschema import validate, ValidationError
from datetime import datetime
from .schemas import SCHEMAS
from .templates import render_prompt
from .normalizer import normalize_payload
from .validators import validar_regras
from .llm import generate

def _montar_contexto(payload: Dict[str, Any]) -> str:
    pessoa = payload.get("pessoa") or {}
    ident = payload.get("identificacao") or {}
    sv = payload.get("sinais_vitais") or {}
    nome = ident.get("nome", "Paciente")
    idade = pessoa.get("idade", "não informado")
    sexo = pessoa.get("sexo", "não informado")
    queixa = payload.get("queixa_principal", "não informada")
    pa = sv.get("pa", "não informado")
    fc = sv.get("fc", "não informado")
    temp = sv.get("temp", "não informado")
    linhas = [
        f"{nome}, {sexo}, {idade} anos.",
        f"Queixa principal: {queixa}.",
        f"Sinais vitais: PA {pa}, FC {fc} bpm, Temp {temp} °C."
    ]
    return " ".join(linhas)

def processar(payload: Dict[str, Any]) -> Dict[str, Any]:
    tipo = (payload.get("tipo_documento") or "SOAP").upper()
    if tipo not in SCHEMAS:
        raise ValueError(f"Tipo de documento não suportado: {tipo}")

    dados_norm = normalize_payload(payload)
    contexto = _montar_contexto(dados_norm)
    prompt = render_prompt(tipo, dados_norm, SCHEMAS[tipo], contexto)

    texto, json_out = generate(prompt, dados_norm)

    # Validação de schema com reparo mínimo
    try:
        validate(instance=json_out, schema=SCHEMAS[tipo])
    except ValidationError:
        if tipo == "SOAP":
            json_out = {
                "S": json_out.get("S") or texto,
                "O": json_out.get("O") or "Sem alterações relevantes descritas.",
                "A": json_out.get("A") or [dados_norm.get("queixa_principal","")],
                "P": json_out.get("P") or ["Orientações gerais e retorno programado."],
                "referencias": json_out.get("referencias") or [],
                "identificacao": json_out.get("identificacao") or dados_norm.get("identificacao") or {},
            }
        elif tipo == "ATESTADO":
            json_out = {
                "texto": json_out.get("texto") or texto,
                "cid": json_out.get("cid") or (dados_norm.get("cid") or ""),
                "dias_afastamento": int(json_out.get("dias_afastamento") or (dados_norm.get("dias_afastamento") or 1)),
                "identificacao": json_out.get("identificacao") or dados_norm.get("identificacao") or {},
            }
        elif tipo == "ENCAMINHAMENTO":
            json_out = {
                "texto": json_out.get("texto") or texto,
                "especialidade": json_out.get("especialidade") or (dados_norm.get("especialidade") or ""),
                "referencias": json_out.get("referencias") or [],
                "identificacao": json_out.get("identificacao") or dados_norm.get("identificacao") or {},
            }
        else:
            json_out = json_out or {"texto": texto, "identificacao": dados_norm.get("identificacao") or {}}
        validate(instance=json_out, schema=SCHEMAS[tipo])

    alertas = validar_regras(tipo, json_out, dados_norm)

    # Meta padrão (timestamp) sempre acoplada ao JSON
    meta = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "tipo_documento": tipo
    }

    return {"texto": texto, "json": {**json_out, "_meta": meta}, "alertas": alertas}