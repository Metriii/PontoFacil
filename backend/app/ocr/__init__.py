"""OCR local (OpenCV + Tesseract)."""

from .leitura import (
    OpcoesOCR,
    PalavraOCR,
    ResultadoOCR,
    TesseractIndisponivel,
    ocr_imagem,
    ocr_multipass,
    tesseract_disponivel,
)
from .pipeline import ler_documento
from .preprocessamento import (
    ErroImagem,
    OpcoesPreprocessamento,
    binarizar,
    carregar_imagem,
    corrigir_inclinacao,
    melhorar_contraste,
    para_escala_cinza,
    preprocessar,
    redimensionar_largura,
    reduzir_ruido,
)

__all__ = [
    "ErroImagem",
    "OpcoesOCR",
    "OpcoesPreprocessamento",
    "PalavraOCR",
    "ResultadoOCR",
    "TesseractIndisponivel",
    "binarizar",
    "carregar_imagem",
    "corrigir_inclinacao",
    "ler_documento",
    "melhorar_contraste",
    "ocr_imagem",
    "ocr_multipass",
    "para_escala_cinza",
    "preprocessar",
    "redimensionar_largura",
    "reduzir_ruido",
    "tesseract_disponivel",
]
