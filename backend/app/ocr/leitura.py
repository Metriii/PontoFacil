"""OCR local via Tesseract (CONTEXT §3/§4).

O OCR apenas reconhece e extrai texto e confiança. Não valida, não confirma e
não completa valores: isso pertence às regras de negócio.
"""

from __future__ import annotations

import shutil
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytesseract
from pytesseract import Output, TesseractNotFoundError

from ..config import settings
from .preprocessamento import melhorar_contraste, reduzir_ruido

_CAMINHOS_COMUNS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
)


class TesseractIndisponivel(Exception):
    """Binário do Tesseract não encontrado ou não configurado."""


@dataclass
class PalavraOCR:
    texto: str
    confianca: float
    esquerda: int
    topo: int
    largura: int
    altura: int


@dataclass
class ResultadoOCR:
    texto: str
    confianca_media: float
    palavras: list[PalavraOCR] = field(default_factory=list)


_configurado = False


def _resolver_caminho() -> str | None:
    if settings.tesseract_cmd:
        return settings.tesseract_cmd
    encontrado = shutil.which("tesseract")
    if encontrado:
        return encontrado
    for caminho in _CAMINHOS_COMUNS:
        if Path(caminho).exists():
            return caminho
    return None


def _garantir_configuracao() -> None:
    global _configurado
    if _configurado:
        return
    caminho = _resolver_caminho()
    if not caminho:
        raise TesseractIndisponivel(
            "Tesseract não encontrado. Instale o binário ou defina "
            "PONTOFACIL_TESSERACT_CMD."
        )
    pytesseract.pytesseract.tesseract_cmd = caminho
    _configurado = True


def tesseract_disponivel() -> bool:
    """Indica se o Tesseract pode ser executado neste ambiente."""
    try:
        _garantir_configuracao()
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _texto_por_linha(dados: dict[str, Any]) -> str:
    linhas: dict[tuple[int, int, int, int], list[str]] = {}
    for i, bruto in enumerate(dados["text"]):
        texto = (bruto or "").strip()
        if not texto:
            continue
        chave = (
            dados["page_num"][i],
            dados["block_num"][i],
            dados["par_num"][i],
            dados["line_num"][i],
        )
        linhas.setdefault(chave, []).append(texto)
    return "\n".join(" ".join(palavras) for _, palavras in sorted(linhas.items()))


def ocr_imagem(
    imagem: np.ndarray, *, lang: str | None = None, config: str = ""
) -> ResultadoOCR:
    """Executa o OCR sobre uma imagem já pré-processada."""
    _garantir_configuracao()
    idioma = lang or settings.ocr_langs
    try:
        dados = pytesseract.image_to_data(
            imagem, lang=idioma, config=config, output_type=Output.DICT
        )
    except TesseractNotFoundError as exc:
        raise TesseractIndisponivel("Tesseract não pôde ser executado.") from exc

    palavras: list[PalavraOCR] = []
    confiancas: list[float] = []
    for i, bruto in enumerate(dados["text"]):
        texto = (bruto or "").strip()
        if not texto:
            continue
        try:
            confianca = float(dados["conf"][i])
        except (TypeError, ValueError):
            confianca = -1.0
        palavras.append(
            PalavraOCR(
                texto=texto,
                confianca=confianca,
                esquerda=int(dados["left"][i]),
                topo=int(dados["top"][i]),
                largura=int(dados["width"][i]),
                altura=int(dados["height"][i]),
            )
        )
        if confianca >= 0:
            confiancas.append(confianca)

    media = statistics.fmean(confiancas) if confiancas else 0.0
    return ResultadoOCR(
        texto=_texto_por_linha(dados),
        confianca_media=media,
        palavras=palavras,
    )


@dataclass(frozen=True)
class OpcoesOCR:
    """Estratégia de OCR.

    A folha é um formulário impresso com um cabeçalho textual e uma tabela com
    horários manuscritos. A passagem de "estrutura" (PSM 3) recupera bem a
    tabela e o nome do funcionário; uma passagem dedicada ao cabeçalho,
    ampliada e com PSM 4/6/11, recupera o período e os rótulos das colunas, que
    o PSM 3 costuma perder.
    """

    multiplicar_passagens: bool = True
    psm_estrutura: int = 3
    psm_cabecalho: tuple[int, ...] = (4, 6, 11)
    fracao_cabecalho: float = 0.38
    escala_cabecalho: int = 3


def _recortar_topo(imagem: np.ndarray, fracao: float) -> np.ndarray:
    altura = imagem.shape[0]
    fim = max(1, min(altura, int(round(altura * fracao))))
    return imagem[0:fim, :]


def _ampliar(imagem: np.ndarray, escala: int) -> np.ndarray:
    if escala <= 1:
        return imagem
    return cv2.resize(
        imagem, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC
    )


def _reduzir_palavras(
    palavras: list[PalavraOCR], escala: int
) -> list[PalavraOCR]:
    if escala <= 1:
        return list(palavras)
    return [
        PalavraOCR(
            texto=p.texto,
            confianca=p.confianca,
            esquerda=p.esquerda // escala,
            topo=p.topo // escala,
            largura=max(1, p.largura // escala),
            altura=max(1, p.altura // escala),
        )
        for p in palavras
    ]


def ocr_multipass(
    imagem: np.ndarray,
    *,
    lang: str | None = None,
    opcoes: OpcoesOCR | None = None,
    imagem_cabecalho: np.ndarray | None = None,
) -> ResultadoOCR:
    """Executa o OCR combinando uma passagem de estrutura e uma do cabeçalho.

    As palavras do cabeçalho são reprojetadas para as coordenadas da imagem
    original, de modo que o parser enxergue tanto a tabela quanto os rótulos
    das colunas. ``imagem_cabecalho`` permite usar uma versão menos processada
    (ex.: escala de cinza original) para a leitura do cabeçalho impresso.
    """
    opcoes = opcoes or OpcoesOCR()
    estrutura = ocr_imagem(imagem, lang=lang, config=f"--psm {opcoes.psm_estrutura}")
    if not opcoes.multiplicar_passagens:
        return estrutura

    base = imagem_cabecalho if imagem_cabecalho is not None else imagem
    recorte = _recortar_topo(base, opcoes.fracao_cabecalho)
    ampliado = _ampliar(recorte, opcoes.escala_cabecalho)
    variantes = (ampliado, melhorar_contraste(reduzir_ruido(ampliado)))

    textos = [estrutura.texto]
    palavras = list(estrutura.palavras)
    for variante in variantes:
        for psm in opcoes.psm_cabecalho:
            resultado = ocr_imagem(variante, lang=lang, config=f"--psm {psm}")
            if resultado.texto:
                textos.append(resultado.texto)
            palavras.extend(
                _reduzir_palavras(resultado.palavras, opcoes.escala_cabecalho)
            )

    return ResultadoOCR(
        texto="\n".join(t for t in textos if t),
        confianca_media=estrutura.confianca_media,
        palavras=palavras,
    )
