import pytest

from app.business import horarios


@pytest.mark.parametrize(
    "bruto,esperado",
    [
        ("08:00", "08:00"),
        ("8:00", "08:00"),
        ("08h30", "08:30"),
        ("08.15", "08:15"),
        ("23:59", "23:59"),
        ("00:00", "00:00"),
        ("24:00", None),
        ("08:60", None),
        ("O8:OO", None),
        ("08:0O", None),
        ("", None),
        (None, None),
        ("abc", None),
    ],
)
def test_normalizar_horario(bruto, esperado) -> None:
    assert horarios.normalizar_horario(bruto) == esperado


def test_normalizar_horario_nao_inventa() -> None:
    # Letras confundidas pelo OCR não viram dígitos.
    assert horarios.normalizar_horario("l2:3O") is None


@pytest.mark.parametrize(
    "valor,esperado",
    [("08:00", True), ("23:59", True), ("24:00", False), ("8:00", False), (None, False)],
)
def test_horario_valido(valor, esperado) -> None:
    assert horarios.horario_valido(valor) is esperado


def test_minutos_do_dia() -> None:
    assert horarios.minutos_do_dia("00:00") == 0
    assert horarios.minutos_do_dia("08:30") == 510
    assert horarios.minutos_do_dia("23:59") == 1439


def test_minutos_do_dia_invalido() -> None:
    with pytest.raises(ValueError):
        horarios.minutos_do_dia("8:00")


@pytest.mark.parametrize(
    "minutos,esperado",
    [(0, "00:00"), (480, "08:00"), (510, "08:30"), (1500, "25:00"), (-90, "-01:30")],
)
def test_formatar_duracao(minutos, esperado) -> None:
    assert horarios.formatar_duracao(minutos) == esperado
