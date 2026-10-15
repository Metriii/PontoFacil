"""Pipeline de imagem + OCR (etapa 5).

Une o pré-processamento (OpenCV) e o reconhecimento (Tesseract). A
interpretação da folha (funcionário, período, dias) é responsabilidade da
etapa 6 (parser), mantida separada do OCR.
"""

from __future__ import annotations

from .leitura import OpcoesOCR, ResultadoOCR, ocr_multipass
from .preprocessamento import (
    OpcoesPreprocessamento,
    carregar_imagem,
    para_escala_cinza,
    preprocessar,
)


def ler_documento(
    dados: bytes,
    *,
    opcoes: OpcoesPreprocessamento | None = None,
    lang: str | None = None,
    ocr: OpcoesOCR | None = None,
) -> ResultadoOCR:
    """Pré-processa a imagem e devolve o resultado bruto do OCR.

    Usa a leitura multipassagem (estrutura + cabeçalho) por padrão; pode ser
    desativada via ``ocr=OpcoesOCR(multiplicar_passagens=False)``. O cabeçalho
    impresso é lido também da imagem em escala de cinza original, o que
    melhora a leitura do período e dos rótulos das colunas.
    """
    imagem = preprocessar(dados, opcoes=opcoes)
    cinza = para_escala_cinza(carregar_imagem(dados))
    return ocr_multipass(imagem, lang=lang, opcoes=ocr, imagem_cabecalho=cinza)
