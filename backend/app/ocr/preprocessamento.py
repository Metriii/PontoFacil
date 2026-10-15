"""Pré-processamento de imagens com OpenCV (CONTEXT §3/§4).

Esta camada apenas condiciona a imagem para o OCR: escala de cinza, redução de
ruído, contraste, correção de inclinação, binarização e redimensionamento.
Não interpreta conteúdo nem decide valores reconhecidos.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from ..config import settings


class ErroImagem(Exception):
    """Imagem ausente, inválida ou grande demais para processar."""


@dataclass(frozen=True)
class OpcoesPreprocessamento:
    reduzir_ruido: bool = True
    melhorar_contraste: bool = True
    corrigir_inclinacao: bool = True
    binarizar: bool = False
    largura_max: int | None = None


def carregar_imagem(dados: bytes, *, max_pixels: int | None = None) -> np.ndarray:
    """Decodifica bytes de imagem, validando antes o número de pixels."""
    if not dados:
        raise ErroImagem("Dados de imagem vazios.")

    limite = max_pixels if max_pixels is not None else settings.max_pixels_imagem
    try:
        with Image.open(io.BytesIO(dados)) as imagem:
            largura, altura = imagem.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ErroImagem("Formato de imagem não reconhecido.") from exc

    if largura <= 0 or altura <= 0:
        raise ErroImagem("Dimensões de imagem inválidas.")
    if largura * altura > limite:
        raise ErroImagem("Imagem excede o número máximo de pixels permitido.")

    buffer = np.frombuffer(dados, dtype=np.uint8)
    imagem = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if imagem is None:
        raise ErroImagem("Não foi possível decodificar a imagem.")
    return imagem


def para_escala_cinza(imagem: np.ndarray) -> np.ndarray:
    if imagem.ndim == 2:
        return imagem
    if imagem.shape[2] == 4:
        return cv2.cvtColor(imagem, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)


def reduzir_ruido(imagem: np.ndarray) -> np.ndarray:
    return cv2.medianBlur(imagem, 3)


def melhorar_contraste(imagem: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(imagem)


def redimensionar_largura(imagem: np.ndarray, largura_max: int) -> np.ndarray:
    altura, largura = imagem.shape[:2]
    if largura <= largura_max:
        return imagem
    escala = largura_max / float(largura)
    nova_altura = max(1, int(round(altura * escala)))
    return cv2.resize(imagem, (largura_max, nova_altura), interpolation=cv2.INTER_AREA)


def corrigir_inclinacao(imagem: np.ndarray) -> np.ndarray:
    binaria = cv2.threshold(
        imagem, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )[1]
    coords = cv2.findNonZero(binaria)
    if coords is None or len(coords) < 10:
        return imagem

    angulo = cv2.minAreaRect(coords)[-1]
    if angulo < -45:
        angulo = -(90 + angulo)
    else:
        angulo = -angulo
    if abs(angulo) < 0.1 or abs(angulo) > 45:
        return imagem

    altura, largura = imagem.shape[:2]
    centro = (largura // 2, altura // 2)
    matriz = cv2.getRotationMatrix2D(centro, angulo, 1.0)
    return cv2.warpAffine(
        imagem,
        matriz,
        (largura, altura),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def binarizar(imagem: np.ndarray) -> np.ndarray:
    return cv2.threshold(imagem, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def preprocessar(
    dados: bytes, *, opcoes: OpcoesPreprocessamento | None = None
) -> np.ndarray:
    """Aplica o pipeline de pré-processamento e devolve a imagem resultante."""
    opcoes = opcoes or OpcoesPreprocessamento()
    imagem = para_escala_cinza(carregar_imagem(dados))
    if opcoes.largura_max:
        imagem = redimensionar_largura(imagem, opcoes.largura_max)
    if opcoes.reduzir_ruido:
        imagem = reduzir_ruido(imagem)
    if opcoes.melhorar_contraste:
        imagem = melhorar_contraste(imagem)
    if opcoes.corrigir_inclinacao:
        imagem = corrigir_inclinacao(imagem)
    if opcoes.binarizar:
        imagem = binarizar(imagem)
    return imagem
