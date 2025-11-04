from app.utils import load_glossary, normalize_bullets, normalize_text


def test_glossary_normalization():
    glossary = load_glossary()
    assert "dor de cabeça" in glossary
    normalized = normalize_text("Paciente com dor de cabeça constante")
    assert "cefaleia" in normalized.lower()


def test_bullet_normalization():
    bullets = ["pressão alta", "gripe"]
    normalized = normalize_bullets(bullets)
    assert any("hipertensão" in item.lower() for item in normalized)
    assert any("síndrome gripal" in item.lower() for item in normalized)
