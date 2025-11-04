import pytest

from app.schemas import get_schema, validate_document


def test_validate_soap_schema():
    payload = {
        "S": "Paciente refere cefaleia leve.",
        "O": "Exame sem alterações relevantes.",
        "A": ["Cefaleia tensional"],
        "P": ["Orientado repouso e hidratação"],
        "identificacao": {"nome": "Paciente", "cpf": "00000000000"},
    }
    validate_document("SOAP", payload)


@pytest.mark.parametrize(
    "tipo",
    ["ATESTADO", "ENCAMINHAMENTO", "PARECER", "LAUDO"],
)
def test_other_schemas(tipo: str):
    schema = get_schema(tipo)
    assert schema["type"] == "object"


def test_schema_invalid_document():
    with pytest.raises(Exception):
        validate_document("SOAP", {"S": "apenas"})
