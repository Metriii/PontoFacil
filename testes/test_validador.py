import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.validador import validar_registro


def test_registro_valido_4_horarios():
    reg = {
        "funcionario": "João Silva",
        "mes": 9,
        "ano": 2026,
        "dia": 15,
        "entrada": "08:00",
        "saida_almoco": "12:00",
        "volta_almoco": "13:00",
        "saida_final": "17:30",
    }
    duvidas, confianca = validar_registro(reg)
    assert len(duvidas) == 0
    assert confianca == "alta"


def test_registro_mes_invalido():
    reg = {
        "funcionario": "João",
        "mes": 13,
        "ano": 2026,
        "dia": 1,
        "entrada": "08:00",
        "saida_almoco": None,
        "volta_almoco": None,
        "saida_final": None,
    }
    duvidas, confianca = validar_registro(reg)
    assert any("mes inválido" in d for d in duvidas)
    assert confianca == "baixa"


def test_registro_dia_31_fevereiro():
    reg = {
        "funcionario": "João",
        "mes": 2,
        "ano": 2026,
        "dia": 31,
        "entrada": "08:00",
        "saida_almoco": None,
        "volta_almoco": None,
        "saida_final": None,
    }
    duvidas, confianca = validar_registro(reg)
    assert any("dia 31 inválido" in d for d in duvidas)
    assert confianca == "baixa"


def test_registro_horario_invalido():
    reg = {
        "funcionario": "João",
        "mes": 9,
        "ano": 2026,
        "dia": 15,
        "entrada": "25:00",
        "saida_almoco": None,
        "volta_almoco": None,
        "saida_final": None,
    }
    duvidas, confianca = validar_registro(reg)
    assert any("formato inválido" in d for d in duvidas)
    assert confianca == "baixa"


def test_registro_horario_formato_errado():
    reg = {
        "funcionario": "João",
        "mes": 9,
        "ano": 2026,
        "dia": 15,
        "entrada": "8:5",
        "saida_almoco": None,
        "volta_almoco": None,
        "saida_final": None,
    }
    duvidas, confianca = validar_registro(reg)
    assert any("formato inválido" in d for d in duvidas)


def test_registro_sem_funcionario():
    reg = {
        "funcionario": None,
        "mes": 9,
        "ano": 2026,
        "dia": 15,
        "entrada": "08:00",
        "saida_almoco": "12:00",
        "volta_almoco": "13:00",
        "saida_final": "17:30",
    }
    duvidas, confianca = validar_registro(reg)
    assert any("funcionário não identificado" in d for d in duvidas)
    assert confianca == "baixa"


def test_registro_sem_mes():
    reg = {
        "funcionario": "João",
        "mes": None,
        "ano": 2026,
        "dia": 15,
        "entrada": "08:00",
        "saida_almoco": None,
        "volta_almoco": None,
        "saida_final": None,
    }
    duvidas, confianca = validar_registro(reg)
    assert any("mes não identificado" in d for d in duvidas)
    assert confianca == "baixa"


def test_registro_apenas_2_horarios():
    reg = {
        "funcionario": "João",
        "mes": 9,
        "ano": 2026,
        "dia": 15,
        "entrada": "08:00",
        "saida_almoco": None,
        "volta_almoco": None,
        "saida_final": "17:00",
    }
    duvidas, confianca = validar_registro(reg)
    assert any("dois horários" in d for d in duvidas)
    assert confianca == "media"


def test_registro_horarios_fora_de_ordem():
    reg = {
        "funcionario": "João",
        "mes": 9,
        "ano": 2026,
        "dia": 15,
        "entrada": "17:00",
        "saida_almoco": "08:00",
        "volta_almoco": None,
        "saida_final": None,
    }
    duvidas, confianca = validar_registro(reg)
    assert any("fora de ordem" in d for d in duvidas)
    assert confianca == "baixa"


def test_registro_ano_invalido():
    reg = {
        "funcionario": "João",
        "mes": 9,
        "ano": 0,
        "dia": 15,
        "entrada": "08:00",
        "saida_almoco": None,
        "volta_almoco": None,
        "saida_final": None,
    }
    duvidas, confianca = validar_registro(reg)
    assert any("ano inválido" in d for d in duvidas)
    assert confianca == "baixa"
