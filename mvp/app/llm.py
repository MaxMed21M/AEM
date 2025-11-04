from typing import Dict, Any, Tuple
import json, httpx

def _try_ollama(prompt: str, model: str = "qwen2.5:7b-instruct") -> str:
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "top_p": 0.9}
    }
    with httpx.Client(timeout=45) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("response") or ""

def _fallback_rule_based(dados: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    tipo = (dados.get("tipo_documento") or "SOAP").upper()
    pessoa = dados.get("pessoa") or {}
    ident = dados.get("identificacao") or {}
    idade = pessoa.get("idade", "não informado")
    sexo = pessoa.get("sexo", "não informado")
    nome = ident.get("nome", "Paciente")
    cpf = ident.get("cpf", "")
    cns = ident.get("cns", "")

    bullets = dados.get("bullets") or []
    queixa = dados.get("queixa_principal") or "não informado"
    sv = dados.get("sinais_vitais") or {}
    pa = sv.get("pa", "não informado")
    fc = sv.get("fc", "não informado")
    temp = sv.get("temp", "não informado")

    motivo = dados.get("motivo") or dados.get("finalidade") or ""
    achados_texto = dados.get("achados_texto") or ""

    if tipo == "SOAP":
        S = (
            f"{nome}, {sexo}, {idade} anos, refere {queixa}. "
            + (f"Itens relatados: {'; '.join(bullets)}. " if bullets else "")
        ).strip()
        O = f"Exame físico sem alterações relevantes. Sinais vitais: PA {pa}, FC {fc} bpm, Temp {temp} °C."
        A = [f"{queixa.title()} (hipótese principal)"] if isinstance(queixa, str) else ["Hipótese diagnóstica em avaliação"]
        P = ["Orientações gerais, hidratação, analgesia leve se necessário, retorno programado e sinais de alarme esclarecidos."]
        json_out = {
            "S": S, "O": O, "A": A, "P": P, "referencias": [],
            "identificacao": {"nome": nome, "cpf": cpf, "cns": cns}
        }
        texto = f"S: {S}\nO: {O}\nA: {', '.join(A)}\nP: {'; '.join(P)}"
        return texto, json_out

    if tipo == "ATESTADO":
        dias = dados.get("dias_afastamento") or 3
        cid = dados.get("cid") or ""
        texto = (
            f"Atesto, para fins legais, que {nome} (CPF {cpf or 'não informado'}; CNS {cns or 'não informado'}), "
            f"foi atendido(a) nesta data, apresentando condição clínica compatível com CID {cid or 'não informado'}, "
            f"sendo indicado afastamento por {dias} dia(s), a partir desta data, com repouso relativo e retorno "
            f"em caso de piora ou sinais de alarme."
        )
        json_out = {
            "texto": texto, "cid": cid, "dias_afastamento": int(dias),
            "identificacao": {"nome": nome, "cpf": cpf, "cns": cns}
        }
        return texto, json_out

    if tipo == "ENCAMINHAMENTO":
        esp = dados.get("especialidade") or "especialidade pertinente"
        texto = (
            f"Encaminho {nome} (CPF {cpf or 'não informado'}; CNS {cns or 'não informado'}), {sexo}, {idade} anos, "
            f"para avaliação em {esp}, em razão de {queixa}. Anexos conforme disponibilidade. "
            f"Sinais vitais atuais: PA {pa}, FC {fc} bpm, Temp {temp} °C."
        )
        json_out = {
            "texto": texto, "especialidade": esp, "referencias": [],
            "identificacao": {"nome": nome, "cpf": cpf, "cns": cns}
        }
        return texto, json_out

    if tipo == "PARECER":
        texto = (
            f"IDENTIFICAÇÃO: {nome} (CPF {cpf or 'não informado'}; CNS {cns or 'não informado'}), {sexo}, {idade} anos.\n"
            f"MOTIVO: {motivo or 'não informado'}.\n"
            f"SÍNTESE: Queixa principal de {queixa}. "
            + (f"Itens relatados: {'; '.join(bullets)}. " if bullets else "")
            + f"Sinais vitais: PA {pa}, FC {fc} bpm, Temp {temp} °C.\n"
            f"ANÁLISE: {achados_texto or 'não informado'}.\n"
            f"CONCLUSÃO: {('Quadro compatível com ' + queixa) if isinstance(queixa,str) else 'conclusão clínica provável'}.\n"
            f"RECOMENDAÇÕES: acompanhamento na APS; considerar avaliação especializada se persistência ou piora; retorno programado."
        )
        json_out = {
            "texto": texto,
            "motivo": motivo,
            "conclusao": [f"Quadro compatível com {queixa}"] if isinstance(queixa, str) else ["Conclusão clínica provável"],
            "recomendacoes": [
                "Acompanhamento na APS",
                "Considerar avaliação especializada se persistência ou piora",
                "Retorno programado"
            ],
            "anexos": [],
            "identificacao": {"nome": nome, "cpf": cpf, "cns": cns}
        }
        return texto, json_out

    if tipo == "LAUDO":
        texto = (
            f"IDENTIFICAÇÃO: {nome} (CPF {cpf or 'não informado'}; CNS {cns or 'não informado'}), {sexo}, {idade} anos.\n"
            f"MOTIVO: {motivo or 'não informado'}.\n"
            f"PROCEDIMENTO/EXAME: {achados_texto and 'descrição conforme informado' or 'não informado'}.\n"
            f"ACHADOS: {achados_texto or 'não informado'}.\n"
            f"CONCLUSÃO: {('Achados compatíveis com ' + queixa) if isinstance(queixa,str) else 'Conclusão compatível com a suspeita clínica'}.\n"
            f"RECOMENDAÇÕES: correlacionar clinicamente; retorno programado; reavaliar em caso de piora."
        )
        json_out = {
            "texto": texto,
            "motivo": motivo,
            "achados": [a.strip() for a in achados_texto.split(';') if a.strip()] if achados_texto else [],
            "conclusao": [f"Achados compatíveis com {queixa}"] if isinstance(queixa, str) else ["Conclusão clínica provável"],
            "recomendacoes": [
                "Correlacionar clinicamente",
                "Retorno programado",
                "Reavaliar em caso de piora"
            ],
            "anexos": [],
            "identificacao": {"nome": nome, "cpf": cpf, "cns": cns}
        }
        return texto, json_out

    # Default (qualquer outro)
    texto = f"Documento clínico referente a {nome}. Gerado automaticamente a partir de dados resumidos."
    json_out = {"texto": texto, "identificacao": {"nome": nome, "cpf": cpf, "cns": cns}}
    return texto, json_out

def _split_llm_two_parts(resp: str) -> Tuple[str, str]:
    try:
        part_text = resp.split("1)")[1].split("2)")[0].strip()
        part_json = resp.split("2)")[1].strip()
        return part_text, part_json
    except Exception:
        return resp.strip(), "{}"

def generate(prompt: str, dados: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    try:
        resp = _try_ollama(prompt)
        parte_texto, json_str = _split_llm_two_parts(resp)
        try:
            json_out = json.loads(json_str)
        except Exception:
            json_out = {}
        return parte_texto, json_out
    except Exception:
        return _fallback_rule_based(dados)  