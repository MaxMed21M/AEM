"""LLM orchestration with caching, retries and fallbacks."""
from __future__ import annotations

import json
import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from .prompts import build_generation_prompt, build_revision_prompt
from .providers import BaseProvider, ProviderError, build_providers
from .schemas import get_schema, validate_document
from .utils import make_cache_key, normalize_bullets, normalize_text, sanitize_text

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGER = logging.getLogger("app.llm")
if not LOGGER.handlers:
    handler = logging.FileHandler(LOG_DIR / "app.log")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)


class LLMClient:
    """Wrapper responsible for calling providers with retries and caching."""

    def __init__(
        self,
        providers: Dict[str, BaseProvider] | None = None,
        timeout_s: float = 45.0,
        max_retries: int = 2,
        retry_backoff_s: float = 2.0,
        cache_size: int = 64,
    ) -> None:
        self.providers = providers or build_providers()
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.retry_backoff_s = retry_backoff_s
        self.cache_size = cache_size
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    # ------------------------------------------------------------------
    # Cache helpers
    def _cache_get(self, key: str) -> Dict[str, Any] | None:
        value = self.cache.get(key)
        if value is not None:
            self.cache.move_to_end(key)
        return value

    def _cache_set(self, key: str, value: Dict[str, Any]) -> None:
        self.cache[key] = value
        self.cache.move_to_end(key)
        while len(self.cache) > self.cache_size:
            self.cache.popitem(last=False)

    # ------------------------------------------------------------------
    def _available_providers(self) -> Iterable[BaseProvider]:
        if not self.providers:
            self.providers = build_providers()
        for provider in self.providers.values():
            yield provider

    def _call_provider(self, provider: BaseProvider, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                LOGGER.info("Provider %s - tentativa %s", provider.name, attempt + 1)
                response = provider.generate(prompt, timeout_s=self.timeout_s)
                return response
            except ProviderError as exc:  # pragma: no cover - depends on provider
                last_error = exc
                LOGGER.warning("ProviderError: %s", exc)
            except Exception as exc:  # pragma: no cover - depends on provider
                last_error = exc
                LOGGER.exception("Erro ao chamar provider %s", provider.name)
            if attempt < self.max_retries:
                time.sleep(self.retry_backoff_s * (2**attempt))
        if last_error is not None:
            raise last_error
        raise RuntimeError("Provider não respondeu")

    # ------------------------------------------------------------------
    def generate_document(
        self,
        document_type: str,
        payload: Dict[str, Any],
        clinical_context: str,
    ) -> Dict[str, Any]:
        doc_type = document_type.upper()
        normalized_payload = self._normalize_payload(payload)
        schema = get_schema(doc_type)
        prompt = build_generation_prompt(doc_type, normalized_payload, schema, clinical_context)
        cache_key = make_cache_key(doc_type, sanitize_text(json.dumps(normalized_payload, sort_keys=True, ensure_ascii=False)), params={"context": clinical_context})
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        for provider in self._available_providers():
            try:
                raw_response = self._call_provider(provider, prompt)
                text, json_payload = self._parse_completion(raw_response)
                if json_payload:
                    try:
                        validate_document(doc_type, json_payload)
                    except Exception as exc:
                        LOGGER.warning("JSON inválido de %s: %s", provider.name, exc)
                        raise
                result = {
                    "text": text,
                    "json": json_payload,
                    "provider": provider.name,
                }
                if not json_payload:
                    raise ValueError("Resposta sem JSON estruturado")
                self._cache_set(cache_key, result)
                return result
            except Exception as exc:
                LOGGER.warning("Falha com provider %s: %s", provider.name, exc)
                continue

        LOGGER.info("Aplicando fallback determinístico")
        text, json_payload = fallback_rule_based(doc_type, normalized_payload)
        result = {"text": text, "json": json_payload, "provider": "fallback"}
        self._cache_set(cache_key, result)
        return result

    def revise_text(self, texto: str) -> Dict[str, Any]:
        prompt = build_revision_prompt(texto)
        cache_key = make_cache_key("revision", sanitize_text(texto))
        cached = self._cache_get(cache_key)
        if cached:
            return cached
        for provider in self._available_providers():
            try:
                revised = self._call_provider(provider, prompt)
                result = {"text": revised.strip(), "provider": provider.name}
                self._cache_set(cache_key, result)
                return result
            except Exception as exc:
                LOGGER.warning("Revisão falhou com %s: %s", provider.name, exc)
        LOGGER.info("Revisão usando fallback (texto original)")
        result = {"text": sanitize_text(texto), "provider": "fallback"}
        self._cache_set(cache_key, result)
        return result

    # ------------------------------------------------------------------
    def _parse_completion(self, response: str) -> Tuple[str, Dict[str, Any]]:
        text_block = response
        json_block = ""
        if "JSON:" in response:
            parts = response.split("JSON:", maxsplit=1)
            text_block = parts[0]
            json_block = parts[1]
        elif "{" in response and "}" in response:
            start = response.find("{")
            end = response.rfind("}") + 1
            json_block = response[start:end]
            text_block = response[:start]
        text_block = text_block.replace("TEXTO:", "").strip()
        json_payload: Dict[str, Any] = {}
        if json_block:
            candidate = json_block.strip().strip("`\n")
            try:
                json_payload = json.loads(candidate)
            except json.JSONDecodeError:
                LOGGER.warning("Falha ao decodificar JSON da IA")
                json_payload = {}
        return text_block, json_payload

    def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(payload)
        normalized["queixa_principal"] = normalize_text(payload.get("queixa_principal", ""))
        normalized["bullets"] = normalize_bullets(payload.get("bullets"))
        return normalized


# ----------------------------------------------------------------------
# Deterministic fallback implementation

def fallback_rule_based(document_type: str, dados: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    tipo = document_type.upper()
    pessoa = dados.get("pessoa") or {}
    ident = dados.get("identificacao") or {}
    idade = pessoa.get("idade", "não informado")
    sexo = pessoa.get("sexo", "não informado")
    nome = ident.get("nome", "Paciente")
    cpf = ident.get("cpf", "")
    cns = ident.get("cns", "")
    bullets = dados.get("bullets") or []
    queixa = dados.get("queixa_principal") or "não informado"
    sinais = dados.get("sinais_vitais") or {}
    pa = sinais.get("pa", "não informado")
    fc = sinais.get("fc", "não informado")
    temp = sinais.get("temp", "não informado")
    motivo = dados.get("motivo") or dados.get("finalidade") or "não informado"
    achados_texto = dados.get("achados_texto") or "não informado"

    if tipo == "SOAP":
        subjetivo = (
            f"{nome}, {sexo}, {idade} anos, refere {queixa}. "
            + (f"Itens adicionais: {'; '.join(bullets)}. " if bullets else "")
        ).strip()
        objetivo = f"Exame físico sem alterações importantes. Sinais vitais: PA {pa}, FC {fc} bpm, Temp {temp} °C."
        avaliacao = [f"{queixa}" if isinstance(queixa, str) else "Avaliação clínica em andamento"]
        plano = [
            "Orientações gerais fornecidas",
            "Sinais de alarme esclarecidos",
            "Retorno programado conforme disponibilidade",
        ]
        json_out = {
            "S": subjetivo,
            "O": objetivo,
            "A": avaliacao,
            "P": plano,
            "referencias": [],
            "identificacao": {"nome": nome, "cpf": cpf, "cns": cns},
        }
        texto = f"S: {subjetivo}\nO: {objetivo}\nA: {', '.join(avaliacao)}\nP: {'; '.join(plano)}"
        return texto, json_out

    if tipo == "ATESTADO":
        dias = dados.get("dias_afastamento") or 3
        cid = dados.get("cid") or "não informado"
        texto = (
            f"Atesto para fins legais que {nome} (CPF {cpf or 'não informado'}, CNS {cns or 'não informado'}) "
            f"foi avaliado(a) nesta unidade em {motivo or 'consulta'}. Condição compatível com CID {cid}, "
            f"com necessidade de afastamento por {dias} dia(s)."
        )
        json_out = {
            "texto": texto,
            "cid": cid,
            "dias_afastamento": int(dias),
            "identificacao": {"nome": nome, "cpf": cpf, "cns": cns},
        }
        return texto, json_out

    if tipo == "ENCAMINHAMENTO":
        especialidade = dados.get("especialidade") or "especialidade pertinente"
        texto = (
            f"Encaminho {nome}, {sexo}, {idade} anos, para avaliação em {especialidade}. "
            f"Motivo: {queixa}. Sinais vitais atuais: PA {pa}, FC {fc} bpm, Temp {temp} °C."
        )
        json_out = {
            "texto": texto,
            "especialidade": especialidade,
            "referencias": [],
            "identificacao": {"nome": nome, "cpf": cpf, "cns": cns},
        }
        return texto, json_out

    if tipo == "PARECER":
        texto = (
            f"IDENTIFICAÇÃO: {nome} (CPF {cpf or 'não informado'}; CNS {cns or 'não informado'}), {sexo}, {idade} anos.\n"
            f"MOTIVO: {motivo}.\n"
            f"SÍNTESE: {queixa}. " + (f"Itens adicionais: {'; '.join(bullets)}.\n" if bullets else "\n")
            f"ANÁLISE: {achados_texto}.\n"
            f"CONCLUSÃO: quadro compatível com {queixa}.\n"
            "RECOMENDAÇÕES: acompanhamento na APS, retorno programado e orientações reforçadas."
        )
        json_out = {
            "texto": texto,
            "motivo": motivo,
            "conclusao": [f"Quadro compatível com {queixa}"],
            "recomendacoes": [
                "Acompanhamento na APS",
                "Retorno programado",
                "Sinais de alarme esclarecidos",
            ],
            "anexos": [],
            "identificacao": {"nome": nome, "cpf": cpf, "cns": cns},
        }
        return texto, json_out

    if tipo == "LAUDO":
        texto = (
            f"IDENTIFICAÇÃO: {nome} (CPF {cpf or 'não informado'}; CNS {cns or 'não informado'}), {sexo}, {idade} anos.\n"
            f"MOTIVO: {motivo}.\n"
            f"PROCEDIMENTO/EXAME: conforme avaliação clínica.\n"
            f"ACHADOS: {achados_texto}.\n"
            f"CONCLUSÃO: achados compatíveis com {queixa}.\n"
            "RECOMENDAÇÕES: correlacionar com quadro clínico e manter acompanhamento na APS."
        )
        json_out = {
            "texto": texto,
            "motivo": motivo,
            "achados": [item.strip() for item in achados_texto.split(";") if item.strip()],
            "conclusao": [f"Achados compatíveis com {queixa}"],
            "recomendacoes": [
                "Correlacionar clinicamente",
                "Retorno programado",
                "Orientações de sinais de alarme",
            ],
            "anexos": [],
            "identificacao": {"nome": nome, "cpf": cpf, "cns": cns},
        }
        return texto, json_out

    texto = f"Documento clínico referente a {nome}. Gerado automaticamente." \
        f" Dados fornecidos: {sanitize_text(json.dumps(dados, ensure_ascii=False))}"
    json_out = {"texto": texto, "identificacao": {"nome": nome, "cpf": cpf, "cns": cns}}
    return texto, json_out
