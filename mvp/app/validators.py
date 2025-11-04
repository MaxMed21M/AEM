from typing import Dict, List, Any

def _digits_only(s: str) -> str:
    return "".join([c for c in s if c.isdigit()])

def validar_regras(tipo: str, saida_json: Dict[str, Any], entrada: Dict[str, Any]) -> List[str]:
    alertas: List[str] = []

    # Temperatura plausível
    vitais = entrada.get("sinais_vitais") or {}
    temp = vitais.get("temp")
    try:
        if temp is not None and (float(temp) < 30 or float(temp) > 43):
            alertas.append("Temperatura fora de faixa plausível (30–43 °C).")
    except Exception:
        pass

    # Identificação: CPF e CNS
    ident = (saida_json.get("identificacao") or entrada.get("identificacao")) or {}
    cpf = ident.get("cpf") or ""
    cns = ident.get("cns") or ""
    if cpf:
        cpf_digits = _digits_only(cpf)
        if len(cpf_digits) != 11:
            alertas.append("CPF com formato/quantidade de dígitos inválido (esperado: 11).")
    if cns:
        cns_digits = _digits_only(cns)
        if len(cns_digits) != 15:
            alertas.append("CNS com formato/quantidade de dígitos inválido (esperado: 15).")

    # Regras específicas por tipo
    if tipo == "ATESTADO":
        dias = saida_json.get("dias_afastamento")
        if dias is None:
            alertas.append("Atestado sem 'dias_afastamento'.")
        else:
            try:
                d = int(dias)
                if d < 1 or d > 30:
                    alertas.append("Dias de afastamento fora do intervalo usual (1–30).")
            except Exception:
                alertas.append("Dias de afastamento inválido (não numérico).")
        if not saida_json.get("cid"):
            alertas.append("Atestado sem CID informado.")
    elif tipo == "SOAP":
        for campo in ["S", "O", "A", "P"]:
            if campo not in saida_json:
                alertas.append(f"Campo SOAP ausente: {campo}.")
        # retorno_em_dias (se existir)
        if "retorno_em_dias" in saida_json:
            try:
                r = int(saida_json["retorno_em_dias"])
                if r < 1 or r > 180:
                    alertas.append("retorno_em_dias fora do intervalo (1–180).")
            except Exception:
                alertas.append("retorno_em_dias inválido (não numérico).")

    return alertas