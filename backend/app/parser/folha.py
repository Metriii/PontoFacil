"""Parser da folha de ponto (etapa 6).

Converte o resultado bruto do OCR (``ResultadoOCR``) em uma estrutura de
funcionário, período e registros diários. Regras:

- Nunca inventa: horários ilegíveis/ausentes ficam ``None`` e o texto bruto é
  preservado em ``valor_bruto``.
- A coluna **"Hora Extra"** é ignorada: qualquer horário reconhecido à direita
  do rótulo "Hora" é descartado e não entra na estrutura.
- Não valida nem confirma valores: ``status_validacao`` permanece ``pendente``
  (isso pertence às regras de negócio, etapa 7).
"""

from __future__ import annotations

import re
import secrets
import statistics
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ..ocr.leitura import PalavraOCR, ResultadoOCR
from ..persistence.models import (
    Funcionario,
    FichaPonto,
    RegistroDiario,
)

# --- Padrões -----------------------------------------------------------------

_TEMPO_ESTRITO_RE = re.compile(r"^(?P<h>\d{1,2})[:hH.](?P<m>\d{2})$")
_TEMPO_FROUXO_RE = re.compile(r"^[\dOoIl]{1,2}[:.,hH][\dOoIl]{2}$")

_PERIODO_INTERVALO_RE = re.compile(
    r"(?P<d1>\d{1,2})[/\-](?P<m1>\d{1,2})[/\-](?P<a1>\d{2,4})"
    r"\s*(?:a|ate|até|-|–|—|aos)\s*"
    r"(?P<d2>\d{1,2})[/\-](?P<m2>\d{1,2})[/\-](?P<a2>\d{2,4})",
    re.IGNORECASE,
)
_DATA_RE = re.compile(r"(?P<d>\d{1,2})[/\-](?P<m>\d{1,2})[/\-](?P<a>\d{2,4})")
_DATA_SEM_SEP_RE = re.compile(r"(?P<d>\d{2})(?P<m>\d{2})[/\-](?P<a>\d{4})")
_MES_ANO_RE = re.compile(r"(?<!\d)(?P<m>\d{1,2})[/\-](?P<a>\d{4})(?!\d)")
_FUNCIONARIO_RE = re.compile(
    r"(?P<cod>\d{2,6})\s*[-–—:]\s*(?P<nome>[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ\s.]{2,})"
)
_LINHA_IGNORAR_PERIODO_RE = re.compile(
    r"admiss|ctps|s[eé]rie|nasc|cnpj|cpf|cep|data\b", re.IGNORECASE
)
_ROTULO_PERIODO_RE = re.compile(r"per[ií]odo", re.IGNORECASE)

_ROTULOS_CABECALHO = {
    "empresa": re.compile(r"(?i)empresa\W{0,3}(.+)"),
    "funcao": re.compile(r"(?i)fun[cç][aã]o\W{0,3}(.+)"),
    "departamento": re.compile(r"(?i)departamento\W{0,3}(.+)"),
}

_ROTULOS_COLUNA = {"entrada", "saida", "intervalo", "hora"}

_DIAS_SEMANA = (
    ("segunda", "Seg", "util"),
    ("seg", "Seg", "util"),
    ("ter", "Ter", "util"),
    ("qua", "Qua", "util"),
    ("qui", "Qui", "util"),
    ("sex", "Sex", "util"),
    ("sab", "Sáb", "fim_de_semana"),
    ("dom", "Dom", "fim_de_semana"),
    ("feria", "Férias", "ferias"),
    ("fer", "Feriado", "feriado"),
)

_ORDEM_CAMPOS = ("entrada", "saida_almoco", "volta_almoco", "saida")


# --- Estruturas --------------------------------------------------------------


@dataclass
class Colunas:
    centros: dict[str, float] = field(default_factory=dict)
    limite_hora_extra: float | None = None
    inferidas: bool = False


@dataclass
class FolhaExtraida:
    funcionario: Funcionario
    mes: int | None
    ano: int | None
    registros: list[RegistroDiario]
    confianca_media: float = 0.0
    avisos: list[str] = field(default_factory=list)

    def para_ficha(self) -> FichaPonto:
        return FichaPonto(
            funcionario=self.funcionario,
            mes=self.mes,
            ano=self.ano,
            registros=self.registros,
        )


# --- Utilidades de texto -----------------------------------------------------


def normalizar(texto: str) -> str:
    """Minúsculas sem acentos, para comparação tolerante a OCR."""
    decomposto = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return sem_acento.lower().strip()


def _limpar_nome(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip(" -–—.")


def _normalizar_ano(bruto: str) -> int | None:
    ano = int(bruto)
    if ano < 100:
        ano += 2000
    return ano if 2000 <= ano <= 2100 else None


def _periodo_valido(mes: int | None, ano: int | None) -> bool:
    return mes is not None and ano is not None and 1 <= mes <= 12


# --- Cabeçalho ---------------------------------------------------------------


def _datas_da_linha(linha: str) -> list[tuple[int, int, int]]:
    """Datas completas (dia, mês, ano) de uma linha, tolerando OCR."""
    datas: list[tuple[int, int, int]] = []
    for m in _DATA_RE.finditer(linha):
        mes = int(m.group("m"))
        ano = _normalizar_ano(m.group("a"))
        if _periodo_valido(mes, ano):
            datas.append((int(m.group("d")), mes, ano or 0))
    for m in _DATA_SEM_SEP_RE.finditer(linha):
        mes = int(m.group("m"))
        ano = _normalizar_ano(m.group("a"))
        if _periodo_valido(mes, ano):
            datas.append((int(m.group("d")), mes, ano or 0))
    return datas


def extrair_periodo(texto: str) -> tuple[int | None, int | None]:
    """Extrai (mês, ano) do período da folha.

    A folha é um formulário: o período é impresso, mas o OCR pode quebrá-lo em
    fragmentos (ex.: ``01/08/2026 a 31``) ou confundir o ano (``.../2000``).
    Por isso combinamos o intervalo explícito com uma votação das datas, dando
    peso extra às linhas rotuladas como "período" e descartando datas de
    admissão/CTPS/CNPJ.
    """
    votos: Counter[tuple[int, int]] = Counter()
    dias: dict[tuple[int, int], set[int]] = defaultdict(set)

    for m in _PERIODO_INTERVALO_RE.finditer(texto):
        mes1 = int(m.group("m1"))
        mes2 = int(m.group("m2"))
        ano1 = _normalizar_ano(m.group("a1"))
        ano2 = _normalizar_ano(m.group("a2"))
        if not (_periodo_valido(mes1, ano1) and _periodo_valido(mes2, ano2)):
            continue
        if mes1 == mes2 and abs((ano1 or 0) - (ano2 or 0)) <= 1:
            votos[(mes2, ano2 or 0)] += 3
            dias[(mes2, ano2 or 0)].update({int(m.group("d1")), int(m.group("d2"))})

    for linha in texto.splitlines():
        if _LINHA_IGNORAR_PERIODO_RE.search(linha):
            continue
        peso = 2 if _ROTULO_PERIODO_RE.search(linha) else 1
        for dia, mes, ano in _datas_da_linha(linha):
            votos[(mes, ano)] += peso
            dias[(mes, ano)].add(dia)
        for m in _MES_ANO_RE.finditer(linha):
            mes = int(m.group("m"))
            ano = _normalizar_ano(m.group("a"))
            if _periodo_valido(mes, ano):
                votos[(mes, ano or 0)] += 1

    if not votos:
        return None, None

    def prioridade(item: tuple[tuple[int, int], int]) -> tuple[int, int, int]:
        (mes, ano), total = item
        presentes = dias.get((mes, ano), set())
        bonus = (1 if 1 in presentes else 0) + (
            1 if any(d >= 28 for d in presentes) else 0
        )
        return total, bonus, ano * 100 + mes

    (mes, ano), _ = max(votos.items(), key=prioridade)
    return mes, ano


def extrair_funcionario(texto: str) -> Funcionario:
    """Extrai código e nome do funcionário.

    Como o OCR pode truncar o nome em uma passagem e completá-lo em outra,
    escolhe a ocorrência mais longa encontrada.
    """
    codigo: str | None = None
    nome: str | None = None
    for linha in texto.splitlines():
        m = _FUNCIONARIO_RE.search(linha)
        if not m:
            continue
        candidato = _limpar_nome(m.group("nome"))
        if nome is None or len(candidato) > len(nome):
            codigo = m.group("cod")
            nome = candidato
    return Funcionario(funcionario_id=secrets.token_hex(8), codigo=codigo, nome=nome)


def extrair_campos_cabecalho(texto: str) -> dict[str, str]:
    encontrados: dict[str, str] = {}
    for linha in texto.splitlines():
        for chave, padrao in _ROTULOS_CABECALHO.items():
            if chave in encontrados:
                continue
            m = padrao.search(linha)
            if m:
                valor = _limpar_nome(m.group(1))
                if valor:
                    encontrados[chave] = valor
    return encontrados


# --- Linhas e colunas --------------------------------------------------------


def agrupar_linhas(
    palavras: list[PalavraOCR], tolerancia: int = 14
) -> list[list[PalavraOCR]]:
    ordenadas = sorted(palavras, key=lambda p: (p.topo, p.esquerda))
    linhas: list[list[PalavraOCR]] = []
    for palavra in ordenadas:
        if linhas and abs(palavra.topo - linhas[-1][0].topo) <= tolerancia:
            linhas[-1].append(palavra)
        else:
            linhas.append([palavra])
    for linha in linhas:
        linha.sort(key=lambda p: p.esquerda)
    return linhas


def detectar_colunas(palavras: list[PalavraOCR]) -> Colunas:
    """Detecta centros das colunas e o limite da coluna "Hora Extra"."""
    rotulos: list[tuple[int, int, str]] = []
    for palavra in palavras:
        chave = normalizar(palavra.texto).strip(".,:;")
        if chave in _ROTULOS_COLUNA:
            rotulos.append((palavra.topo, palavra.esquerda, chave))
    if not rotulos:
        return Colunas(inferidas=True)

    rotulos.sort()
    topo0 = rotulos[0][0]
    banda = sorted(
        (r for r in rotulos if r[0] <= topo0 + 70), key=lambda r: r[1]
    )

    entradas = [x for _, x, t in banda if t == "entrada"]
    saidas = [x for _, x, t in banda if t == "saida"]
    horas = [x for _, x, t in banda if t == "hora"]
    limite = float(min(horas)) if horas else None

    if not entradas or not saidas:
        return Colunas(limite_hora_extra=limite, inferidas=True)

    entrada_x = float(min(entradas))
    saidas_validas = [
        x for x in saidas if x > entrada_x and (limite is None or x < limite)
    ]
    if not saidas_validas:
        return Colunas(limite_hora_extra=limite, inferidas=True)

    saida_x = float(max(saidas_validas))
    meio = sorted(
        float(x)
        for _, x, t in banda
        if t in ("entrada", "saida") and entrada_x < x < saida_x
    )
    if len(meio) == 2:
        return Colunas(
            centros={
                "entrada": entrada_x,
                "saida_almoco": meio[0],
                "volta_almoco": meio[1],
                "saida": saida_x,
            },
            limite_hora_extra=limite,
            inferidas=False,
        )
    return Colunas(limite_hora_extra=limite, inferidas=True)


# --- Registros ---------------------------------------------------------------


def _normalizar_tempo(bruto: str) -> str | None:
    m = _TEMPO_ESTRITO_RE.match(bruto)
    if not m:
        return None
    hora = int(m.group("h"))
    minuto = int(m.group("m"))
    if hora > 23 or minuto > 59:
        return None
    return f"{hora:02d}:{minuto:02d}"


def _detectar_dia(linha: list[PalavraOCR], largura_pagina: int) -> tuple | None:
    if not linha:
        return None
    primeiro = linha[0]
    if largura_pagina and primeiro.esquerda > 0.35 * largura_pagina:
        return None
    digitos = re.sub(r"\D", "", primeiro.texto)
    if not digitos or len(digitos) > 2:
        return None
    dia = int(digitos)
    if not 1 <= dia <= 31:
        return None

    dia_semana: str | None = None
    tipo: str | None = None
    for palavra in linha[1:3]:
        chave = normalizar(palavra.texto).strip(".,;:")
        for prefixo, rotulo, classe in _DIAS_SEMANA:
            if chave.startswith(prefixo):
                dia_semana = rotulo
                tipo = classe
                break
        if dia_semana:
            break
    if tipo is None:
        tipo = "util" if dia_semana else None
    return dia, dia_semana, tipo


def _tempos_da_linha(linha: list[PalavraOCR]) -> list[tuple[float, str, str | None, float]]:
    tempos = []
    for palavra in linha:
        texto = palavra.texto.strip()
        if _TEMPO_FROUXO_RE.match(texto):
            tempos.append(
                (float(palavra.esquerda), texto, _normalizar_tempo(texto), palavra.confianca)
            )
    tempos.sort(key=lambda t: t[0])
    return tempos


def _atribuir_campos(
    tempos: list[tuple[float, str, str | None, float]], colunas: Colunas
) -> tuple[dict[str, str | None], dict[str, str], list[float]]:
    candidatos = [
        t
        for t in tempos
        if colunas.limite_hora_extra is None
        or t[0] < colunas.limite_hora_extra - 5
    ]
    campos: dict[str, str | None] = {nome: None for nome in _ORDEM_CAMPOS}
    bruto: dict[str, str] = {}
    confiancas: list[float] = []

    if not colunas.inferidas and len(colunas.centros) == 4:
        espac = max(20.0, (colunas.centros["saida"] - colunas.centros["entrada"]) / 6.0)
        for x, texto, normalizado, conf in candidatos:
            nome, centro = min(
                ((n, cx) for n, cx in colunas.centros.items()),
                key=lambda t: abs(t[1] - x),
            )
            if abs(centro - x) > espac * 1.6 or campos[nome] is not None:
                continue
            campos[nome] = normalizado
            bruto[nome] = texto
            if conf >= 0:
                confiancas.append(conf)
    else:
        for i, (_, texto, normalizado, conf) in enumerate(candidatos[:4]):
            nome = _ORDEM_CAMPOS[i]
            campos[nome] = normalizado
            bruto[nome] = texto
            if conf >= 0:
                confiancas.append(conf)
    return campos, bruto, confiancas


def extrair_registros(
    palavras: list[PalavraOCR],
    *,
    colunas: Colunas | None = None,
    origem: str | None = None,
    largura_pagina: int | None = None,
) -> list[RegistroDiario]:
    if largura_pagina is None:
        largura_pagina = max(
            (p.esquerda + p.largura for p in palavras), default=0
        )
    if colunas is None:
        colunas = detectar_colunas(palavras)

    registros: list[RegistroDiario] = []
    for linha in agrupar_linhas(palavras):
        detectado = _detectar_dia(linha, largura_pagina)
        if detectado is None:
            continue
        dia, dia_semana, tipo = detectado
        campos, bruto, confiancas = _atribuir_campos(_tempos_da_linha(linha), colunas)
        registros.append(
            RegistroDiario(
                registro_id=secrets.token_hex(8),
                dia=dia,
                dia_semana=dia_semana,
                entrada=campos["entrada"],
                saida_almoco=campos["saida_almoco"],
                volta_almoco=campos["volta_almoco"],
                saida=campos["saida"],
                tipo_dia=tipo,
                status_validacao="pendente",
                confianca=statistics.fmean(confiancas) if confiancas else None,
                valor_bruto=bruto,
                origem=origem,
            )
        )
    registros.sort(key=lambda r: r.dia or 0)
    return registros


# --- Entrada principal -------------------------------------------------------


def parse_folha(resultado: ResultadoOCR, *, origem: str | None = None) -> FolhaExtraida:
    """Interpreta o resultado do OCR como uma folha de ponto estruturada."""
    texto = resultado.texto or ""
    mes, ano = extrair_periodo(texto)
    funcionario = extrair_funcionario(texto)
    for chave, valor in extrair_campos_cabecalho(texto).items():
        if getattr(funcionario, chave, None) is None:
            setattr(funcionario, chave, valor)

    colunas = detectar_colunas(resultado.palavras)
    registros = extrair_registros(
        resultado.palavras, colunas=colunas, origem=origem
    )

    avisos: list[str] = []
    if colunas.inferidas:
        avisos.append("Colunas inferidas por posição; revise os horários.")
    if mes is None or ano is None:
        avisos.append("Período não reconhecido no cabeçalho.")
    if funcionario.nome is None:
        avisos.append("Funcionário não reconhecido no cabeçalho.")

    return FolhaExtraida(
        funcionario=funcionario,
        mes=mes,
        ano=ano,
        registros=registros,
        confianca_media=resultado.confianca_media,
        avisos=avisos,
    )
