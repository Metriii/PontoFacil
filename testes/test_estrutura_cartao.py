import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.estrutura_cartao import CamposCartao, identificar_campos
from backend.leitor_imagem import Palavra


def test_identificar_nome_funcionario():
    palavras = [
        Palavra(texto="Nome:", confianca=95.0, x=10, y=10, w=50, h=20),
        Palavra(texto="João", confianca=90.0, x=70, y=10, w=40, h=20),
        Palavra(texto="Silva", confianca=88.0, x=120, y=10, w=50, h=20),
    ]
    campos = identificar_campos(palavras)
    assert campos.funcionario == "João Silva"


def test_identificar_mes_ano():
    palavras = [
        Palavra(texto="Mes:", confianca=95.0, x=10, y=40, w=40, h=20),
        Palavra(texto="9", confianca=90.0, x=60, y=40, w=10, h=20),
        Palavra(texto="Ano:", confianca=95.0, x=100, y=40, w=40, h=20),
        Palavra(texto="2026", confianca=90.0, x=150, y=40, w=50, h=20),
    ]
    campos = identificar_campos(palavras)
    assert campos.mes == 9
    assert campos.ano == 2026


def test_identificar_horarios_linha():
    palavras = [
        Palavra(texto="1", confianca=95.0, x=10, y=10, w=10, h=20),
        Palavra(texto="08:00", confianca=90.0, x=80, y=10, w=50, h=20),
        Palavra(texto="12:00", confianca=88.0, x=150, y=10, w=50, h=20),
        Palavra(texto="13:00", confianca=87.0, x=220, y=10, w=50, h=20),
        Palavra(texto="17:30", confianca=85.0, x=290, y=10, w=50, h=20),
    ]
    campos = identificar_campos(palavras)
    assert len(campos.registros) == 1
    reg = campos.registros[0]
    assert reg["dia"] == 1
    assert reg["entrada"] == "08:00"
    assert reg["saida_almoco"] == "12:00"
    assert reg["volta_almoco"] == "13:00"
    assert reg["saida_final"] == "17:30"


def test_identificar_horario_sem_pontuacao():
    palavras = [
        Palavra(texto="2", confianca=95.0, x=10, y=10, w=10, h=20),
        Palavra(texto="0800", confianca=85.0, x=80, y=10, w=40, h=20),
        Palavra(texto="1700", confianca=84.0, x=150, y=10, w=40, h=20),
    ]
    campos = identificar_campos(palavras)
    assert len(campos.registros) == 1
    reg = campos.registros[0]
    assert reg["entrada"] == "08:00"
    assert reg["saida_almoco"] == "17:00"


def test_sem_palavras():
    campos = identificar_campos([])
    assert campos.funcionario is None
    assert campos.mes is None
    assert campos.ano is None
    assert len(campos.registros) == 0
    assert len(campos.duvidas) > 0


def test_texto_sem_padrao_reconhecivel():
    palavras = [
        Palavra(texto="xyz", confianca=30.0, x=10, y=10, w=30, h=20),
        Palavra(texto="abc", confianca=25.0, x=50, y=10, w=30, h=20),
    ]
    campos = identificar_campos(palavras)
    assert campos.funcionario is None
    assert len(campos.registros) == 0
    assert len(campos.duvidas) > 0


def test_mes_invalido():
    palavras = [
        Palavra(texto="Mes:", confianca=95.0, x=10, y=40, w=40, h=20),
        Palavra(texto="15", confianca=90.0, x=60, y=40, w=20, h=20),
    ]
    campos = identificar_campos(palavras)
    assert campos.mes is None
    assert any("Mês inválido" in d for d in campos.duvidas)


def test_multiplas_linhas_registro():
    palavras = [
        Palavra(texto="1", confianca=95.0, x=10, y=10, w=10, h=20),
        Palavra(texto="08:00", confianca=90.0, x=80, y=10, w=50, h=20),
        Palavra(texto="17:00", confianca=88.0, x=150, y=10, w=50, h=20),
        Palavra(texto="2", confianca=95.0, x=10, y=40, w=10, h=20),
        Palavra(texto="09:00", confianca=90.0, x=80, y=40, w=50, h=20),
        Palavra(texto="18:00", confianca=88.0, x=150, y=40, w=50, h=20),
    ]
    campos = identificar_campos(palavras)
    assert len(campos.registros) == 2
    assert campos.registros[0]["dia"] == 1
    assert campos.registros[1]["dia"] == 2
