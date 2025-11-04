from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.pipeline import processar

app = FastAPI(title="IA de Escrita Médica - API MVP v1.1.1")

class Identificacao(BaseModel):
    nome: Optional[str] = None
    cpf: Optional[str] = None
    cns: Optional[str] = None

class Pessoa(BaseModel):
    idade: Optional[int] = None
    sexo: Optional[str] = None

class Payload(BaseModel):
    tipo_documento: str = Field(default="SOAP")
    identificacao: Optional[Identificacao] = None
    pessoa: Optional[Pessoa] = None
    queixa_principal: Optional[str] = ""
    bullets: Optional[List[str]] = []
    sinais_vitais: Optional[Dict[str, Any]] = {}
    achados_exame: Optional[List[str]] = []
    hipoteses_previas: Optional[List[str]] = []
    preferencias_estilo: Optional[Dict[str, Any]] = {}
    # específicos
    cid: Optional[str] = None
    dias_afastamento: Optional[int] = None
    especialidade: Optional[str] = None
    motivo: Optional[str] = None
    achados_texto: Optional[str] = None

@app.post("/api/generate")
def generate(payload: Payload):
    try:
        saida = processar(payload.model_dump())
        return saida
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))