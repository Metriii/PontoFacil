from pathlib import Path

import pytest

from app.ocr import leitura
from app.ocr.leitura import PalavraOCR, ResultadoOCR
from app.ocr.pipeline import ler_documento
from app.parser import folha

requer_tesseract = pytest.mark.skipif(
    not leitura.tesseract_disponivel(),
    reason="Tesseract não disponível neste ambiente.",
)


def P(texto, esquerda, topo, conf=90.0, largura=None, altura=20):
    return PalavraOCR(
        texto=texto,
        confianca=conf,
        esquerda=esquerda,
        topo=topo,
        largura=largura if largura is not None else max(12, len(texto) * 12),
        altura=altura,
    )


def _folha_sintetica() -> ResultadoOCR:
    texto = "\n".join(
        [
            "Periodo: 01/08/2026 a 31/08/2026",
            "007 - ALESSANY EDUARDA ANDRADE COSTA DA CONCEICAO",
        ]
    )
    palavras = [
        # rótulos de coluna (linha de cabeçalho em y=100)
        P("Entrada", 200, 100),
        P("Saida", 400, 100),
        P("Entrada", 500, 100),
        P("Saida", 600, 100),
        P("Hora", 700, 100),
        # dia 03 com hora extra preenchida
        P("03", 40, 200),
        P("Seg", 110, 200),
        P("08:00", 205, 200),
        P("13:00", 405, 200),
        P("14:00", 505, 200),
        P("17:00", 605, 200),
        P("18:00", 705, 200),
        P("19:00", 760, 200),
        # dia 04 com apenas entrada e saída
        P("04", 40, 230),
        P("Ter", 110, 230),
        P("08:15", 205, 230),
        P("12:00", 605, 230),
        # dia 15 com token ruidoso entre colchetes
        P("[15]", 40, 260),
        P("Qui", 110, 260),
        P("09:00", 205, 260),
        P("O8:OO", 405, 260),
    ]
    return ResultadoOCR(texto=texto, confianca_media=80.0, palavras=palavras)


# --- Cabeçalho ---------------------------------------------------------------


def test_extrair_periodo_intervalo() -> None:
    assert folha.extrair_periodo("Periodo: 01/08/2026 a 31/08/2026") == (8, 2026)


def test_extrair_periodo_sem_separador_ocr() -> None:
    assert folha.extrair_periodo("0108/2026") == (8, 2026)


def test_extrair_periodo_mes_ano() -> None:
    assert folha.extrair_periodo("Periodo 07/2025") == (7, 2025)


def test_extrair_periodo_ausente() -> None:
    assert folha.extrair_periodo("sem datas aqui") == (None, None)


def test_extrair_periodo_ignora_admissao() -> None:
    texto = "Admissao: 27/06/2019\nPeriodo: 01/08/2026 a 31/08/2026"
    assert folha.extrair_periodo(texto) == (8, 2026)


def test_extrair_periodo_intervalo_truncado_pelo_ocr() -> None:
    assert folha.extrair_periodo("Periodo: 01/08/2026 a 31") == (8, 2026)


def test_extrair_periodo_tolera_ano_ruidoso() -> None:
    texto = "01/08/2026 a 31/08/2000\n31/08/2026"
    assert folha.extrair_periodo(texto) == (8, 2026)


def test_extrair_funcionario() -> None:
    funcionario = folha.extrair_funcionario(
        "007 - ALESSANY EDUARDA ANDRADE COSTA DA CONCEICAO"
    )
    assert funcionario.codigo == "007"
    assert funcionario.nome is not None
    assert "ALESSANY" in funcionario.nome


def test_extrair_funcionario_escolhe_nome_mais_longo() -> None:
    texto = "007 - ALESSANY EDUARDA\n007 - ALESSANY EDUARDA ANDRADE COSTA"
    funcionario = folha.extrair_funcionario(texto)
    assert funcionario.nome == "ALESSANY EDUARDA ANDRADE COSTA"


def test_extrair_campos_cabecalho() -> None:
    texto = "Empresa: EMPRESA X LTDA\nFuncao: VENDEDOR(A)\nDepartamento: GERAL"
    campos = folha.extrair_campos_cabecalho(texto)
    assert campos["empresa"] == "EMPRESA X LTDA"
    assert campos["funcao"] == "VENDEDOR(A)"
    assert campos["departamento"] == "GERAL"


# --- Colunas -----------------------------------------------------------------


def test_detectar_colunas_com_cabecalho() -> None:
    colunas = folha.detectar_colunas(_folha_sintetica().palavras)
    assert colunas.inferidas is False
    assert set(colunas.centros) == {
        "entrada",
        "saida_almoco",
        "volta_almoco",
        "saida",
    }
    assert colunas.limite_hora_extra == 700.0


def test_detectar_colunas_sem_cabecalho() -> None:
    colunas = folha.detectar_colunas([P("03", 40, 200), P("08:00", 205, 200)])
    assert colunas.inferidas is True
    assert colunas.limite_hora_extra is None


# --- Normalização de tempo ---------------------------------------------------


@pytest.mark.parametrize(
    "bruto,esperado",
    [
        ("08:00", "08:00"),
        ("8:00", "08:00"),
        ("08h30", "08:30"),
        ("08.15", "08:15"),
        ("24:00", None),
        ("08:60", None),
        ("O8:OO", None),
        ("08:0O", None),
    ],
)
def test_normalizar_tempo(bruto, esperado) -> None:
    assert folha._normalizar_tempo(bruto) == esperado


# --- Linhas ------------------------------------------------------------------


def test_agrupar_linhas() -> None:
    palavras = [P("a", 10, 100), P("b", 50, 104), P("c", 10, 200)]
    linhas = folha.agrupar_linhas(palavras, tolerancia=14)
    assert len(linhas) == 2
    assert [p.texto for p in linhas[0]] == ["a", "b"]


# --- Registros ---------------------------------------------------------------


def test_extrair_registros_mapeia_colunas_e_ignora_hora_extra() -> None:
    registros = folha.extrair_registros(_folha_sintetica().palavras)
    por_dia = {r.dia: r for r in registros}

    assert set(por_dia) == {3, 4, 15}

    dia3 = por_dia[3]
    assert dia3.dia_semana == "Seg"
    assert dia3.entrada == "08:00"
    assert dia3.saida_almoco == "13:00"
    assert dia3.volta_almoco == "14:00"
    assert dia3.saida == "17:00"
    # hora extra não é persistida em lugar algum
    assert "18:00" not in dia3.valor_bruto.values()
    assert "19:00" not in dia3.valor_bruto.values()
    assert set(dia3.valor_bruto) == {"entrada", "saida_almoco", "volta_almoco", "saida"}

    dia4 = por_dia[4]
    assert dia4.entrada == "08:15"
    assert dia4.saida == "12:00"
    assert dia4.saida_almoco is None
    assert dia4.volta_almoco is None

    dia15 = por_dia[15]
    assert dia15.dia == 15
    assert dia15.entrada == "09:00"
    assert dia15.saida_almoco is None  # "O8:OO" não é normalizável
    assert dia15.valor_bruto.get("saida_almoco") == "O8:OO"


def test_registros_ficam_pendentes() -> None:
    registros = folha.extrair_registros(_folha_sintetica().palavras)
    assert all(r.status_validacao == "pendente" for r in registros)
    assert all(r.tipo_dia in {"util", "fim_de_semana"} for r in registros)


def test_fallback_posicional_sem_cabecalho() -> None:
    palavras = [
        P("03", 40, 200),
        P("Seg", 110, 200),
        P("08:00", 205, 200),
        P("13:00", 405, 200),
        P("14:00", 505, 200),
        P("17:00", 605, 200),
        P("18:00", 705, 200),
        P("19:00", 760, 200),
    ]
    registros = folha.extrair_registros(palavras)
    assert len(registros) == 1
    assert registros[0].entrada == "08:00"
    assert registros[0].saida == "17:00"


# --- Entrada principal -------------------------------------------------------


def test_parse_folha_completa() -> None:
    resultado = folha.parse_folha(_folha_sintetica(), origem="foto.jpg")
    assert resultado.mes == 8
    assert resultado.ano == 2026
    assert resultado.funcionario.codigo == "007"
    assert len(resultado.registros) == 3
    assert resultado.registros[0].origem == "foto.jpg"
    assert resultado.avisos == []

    ficha = resultado.para_ficha()
    assert ficha.mes == 8 and ficha.ano == 2026
    assert len(ficha.registros) == 3


def test_parse_folha_sem_cabecalho_gera_avisos() -> None:
    resultado = folha.parse_folha(
        ResultadoOCR(texto="", confianca_media=0.0, palavras=[P("03", 40, 200)])
    )
    assert resultado.mes is None and resultado.ano is None
    assert resultado.funcionario.nome is None
    assert len(resultado.avisos) == 3


# --- Integração com a imagem real -------------------------------------------


@requer_tesseract
def test_parse_folha_imagem_real_nao_quebra() -> None:
    dados = Path(__file__).resolve().parents[2].joinpath("ALESSANY.jpg").read_bytes()
    resultado = ler_documento(dados)
    folha_extraida = folha.parse_folha(resultado, origem="ALESSANY.jpg")
    assert isinstance(folha_extraida.funcionario, folha.Funcionario)
    assert isinstance(folha_extraida.registros, list)
    assert len(folha_extraida.registros) >= 1
    assert all(r.status_validacao == "pendente" for r in folha_extraida.registros)


@requer_tesseract
def test_ler_documento_multipass_le_cabecalho_real() -> None:
    dados = Path(__file__).resolve().parents[2].joinpath("ALESSANY.jpg").read_bytes()
    resultado = ler_documento(dados)
    folha_extraida = folha.parse_folha(resultado, origem="ALESSANY.jpg")

    assert (folha_extraida.mes, folha_extraida.ano) == (8, 2026)
    assert folha_extraida.funcionario.nome is not None
    assert "ALESSANY" in folha_extraida.funcionario.nome

    colunas = folha.detectar_colunas(resultado.palavras)
    assert colunas.limite_hora_extra is not None


@requer_tesseract
def test_multipass_pode_ser_desativado() -> None:
    from app.ocr.leitura import OpcoesOCR

    dados = Path(__file__).resolve().parents[2].joinpath("ALESSANY.jpg").read_bytes()
    simples = ler_documento(dados, ocr=OpcoesOCR(multiplicar_passagens=False))
    assert simples.palavras
    assert isinstance(simples.texto, str)
