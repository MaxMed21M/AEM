"""Prompt templates for the medical writing assistant."""
from __future__ import annotations

import json
from textwrap import dedent
from typing import Any, Dict


def build_generation_prompt(
    document_type: str,
    payload: Dict[str, Any],
    schema: Dict[str, Any],
    clinical_context: str,
) -> str:
    schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    instructions = dedent(
        f"""
        Você é um(a) médico(a) redator(a) que gera documentos clínicos estruturados no Brasil.
        Regras obrigatórias:
        - Utilize linguagem clínica clara, impessoal e baseada nos dados fornecidos.
        - Não invente informações; quando algo estiver ausente, use "não informado".
        - Harmonize sinais, sintomas, hipóteses e condutas.
        - Mantenha foco em escrita e documentação (sem diagnósticos novos ou triagem).
        - Responda sempre em duas partes, exatamente no formato:
          TEXTO:\n<documento final em prosa com as seções do tipo solicitado>
          JSON:\n<apenas um JSON válido conforme o esquema abaixo>
        - Certifique-se de que o JSON resultante valida contra o schema e reflita o TEXTO.
        """
    ).strip()
    return (
        f"{instructions}\n\n"
        f"TIPO_DOCUMENTO: {document_type}\n"
        f"CONTEXTO CLÍNICO:\n{clinical_context}\n\n"
        f"DADOS ESTRUTURADOS:\n{payload_json}\n\n"
        f"SCHEMA JSON:\n{schema_json}\n"
        "Finalize seguindo o formato exigido."
    )


def build_revision_prompt(texto: str) -> str:
    instructions = dedent(
        """
        Você é um(a) revisor(a) clínico-linguístico.
        Objetivo: aprimorar a redação, padronizar termos médicos brasileiros e manter o conteúdo factual.
        Regras:
        - Não invente informações novas.
        - Conserve números, nomes próprios e dados clínicos citados.
        - Ajuste coerência, ortografia e terminologia técnica conforme boas práticas da APS.
        - Responda apenas com o texto revisado em português.
        """
    ).strip()
    return f"{instructions}\n\nTEXTO_ORIGINAL:\n{texto.strip()}"
