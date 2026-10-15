import cv2
import numpy as np
import pytest

from app.ocr import leitura, preprocessamento
from app.ocr.pipeline import ler_documento

TESSERACT_OK = leitura.tesseract_disponivel()
requer_tesseract = pytest.mark.skipif(
    not TESSERACT_OK, reason="Tesseract não disponível neste ambiente."
)


def _imagem_texto(texto: str = "08:00", tamanho: tuple[int, int] = (220, 700)) -> np.ndarray:
    imagem = np.full(tamanho, 255, dtype=np.uint8)
    cv2.putText(
        imagem, texto, (25, 140), cv2.FONT_HERSHEY_SIMPLEX, 3.0, 0, 7, cv2.LINE_AA
    )
    return imagem


def _png_bytes(imagem: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".png", imagem)
    assert ok
    return buffer.tobytes()


def test_carregar_imagem_vazia() -> None:
    with pytest.raises(preprocessamento.ErroImagem):
        preprocessamento.carregar_imagem(b"")


def test_carregar_imagem_invalida() -> None:
    with pytest.raises(preprocessamento.ErroImagem):
        preprocessamento.carregar_imagem(b"isto nao e uma imagem")


def test_carregar_imagem_excede_pixels() -> None:
    dados = _png_bytes(_imagem_texto())
    with pytest.raises(preprocessamento.ErroImagem):
        preprocessamento.carregar_imagem(dados, max_pixels=10)


def test_preprocessar_retorna_escala_cinza() -> None:
    resultado = preprocessamento.preprocessar(_png_bytes(_imagem_texto()))
    assert resultado.ndim == 2
    assert resultado.dtype == np.uint8


def test_binarizar_produz_apenas_preto_e_branco() -> None:
    imagem = preprocessamento.para_escala_cinza(_imagem_texto())
    binaria = preprocessamento.binarizar(imagem)
    assert set(np.unique(binaria)).issubset({0, 255})


def test_redimensionar_largura() -> None:
    larga = np.full((100, 4000), 255, dtype=np.uint8)
    reduzida = preprocessamento.redimensionar_largura(larga, 1000)
    assert reduzida.shape[1] == 1000
    assert reduzida.shape[0] == 25


def test_redimensionar_nao_aumenta() -> None:
    pequena = np.full((100, 200), 255, dtype=np.uint8)
    resultado = preprocessamento.redimensionar_largura(pequena, 1000)
    assert resultado.shape == (100, 200)


def test_corrigir_inclinacao_nao_quebra_imagem_lisa() -> None:
    imagem = np.full((100, 200), 255, dtype=np.uint8)
    resultado = preprocessamento.corrigir_inclinacao(imagem)
    assert resultado.shape == (100, 200)


@requer_tesseract
def test_ocr_reconhece_digitos() -> None:
    resultado = ler_documento(_png_bytes(_imagem_texto("08:00")), lang="eng")
    sem_espacos = resultado.texto.replace(" ", "")
    assert "08" in sem_espacos
    assert resultado.palavras


@requer_tesseract
def test_ocr_confianca_no_intervalo() -> None:
    resultado = ler_documento(_png_bytes(_imagem_texto("08:00")), lang="eng")
    assert 0.0 <= resultado.confianca_media <= 100.0


@requer_tesseract
def test_tesseract_disponivel_sem_erro() -> None:
    assert leitura.tesseract_disponivel() is True
