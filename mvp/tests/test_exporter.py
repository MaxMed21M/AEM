import gzip
import io
import json
import zipfile
from pathlib import Path

from app.exporter import build_docx, create_zip_bundle, export_json


def test_export_json_variants(tmp_path):
    data = {"S": "Texto", "_meta": {"gerado_em": "2024-01-01T00:00:00"}}
    raw = export_json(data)
    assert json.loads(raw.decode("utf-8")) == data
    gz = export_json(data, compact=True, compress=True)
    decompressed = gzip.decompress(gz)
    assert json.loads(decompressed.decode("utf-8")) == data


def test_docx_and_zip_export(tmp_path):
    texto = "Linha 1\nLinha 2"
    docx_bytes = build_docx(texto, {
        "habilitar": True,
        "nome": "Dra. Teste",
        "crm": "12345",
        "uf": "CE",
        "especialidade": "Medicina de Família",
        "tamanho": 9,
    })
    assert len(docx_bytes) > 0
    json_bytes = export_json({"S": "Texto", "_meta": {"gerado_em": "2024-01-01T00:00:00"}})
    metadata = {"_meta": {"gerado_em": "2024-01-01T00:00:00"}, "payload": {}}
    zip_bytes, zip_path = create_zip_bundle(json_bytes, docx_bytes, metadata, base_name="SOAP")
    assert Path(zip_path).exists()
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        assert set(zf.namelist()) == {"soap.json", "documento.docx", "session.json"}
    Path(zip_path).unlink()
