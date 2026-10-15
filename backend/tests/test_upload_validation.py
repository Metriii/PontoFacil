import pytest

from app.security import upload
from app.security.files import (
    ArquivoExcedeLimite,
    ArquivoVazio,
    FormatoImagem,
    FormatoNaoPermitido,
    LoteExcedeLimite,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20

LIMITES = upload.LimitesUpload(
    max_arquivo_bytes=32,
    max_arquivos=2,
    max_total_bytes=64,
)


def test_arquivo_valido() -> None:
    arq = upload.validar_arquivo("foto.png", PNG, max_bytes=LIMITES.max_arquivo_bytes)
    assert arq.formato is FormatoImagem.PNG
    assert arq.nome_interno.endswith(".png")
    assert arq.nome_original == "foto.png"
    assert arq.tamanho == len(PNG)


def test_extensao_falsa_rejeitada() -> None:
    with pytest.raises(FormatoNaoPermitido):
        upload.validar_arquivo(
            "malicioso.png",
            b"MZ\x90\x00" + b"\x00" * 20,
            max_bytes=LIMITES.max_arquivo_bytes,
        )


def test_arquivo_vazio_rejeitado() -> None:
    with pytest.raises(ArquivoVazio):
        upload.validar_arquivo("vazio.png", b"", max_bytes=LIMITES.max_arquivo_bytes)


def test_arquivo_excede_limite() -> None:
    with pytest.raises(ArquivoExcedeLimite):
        upload.validar_arquivo(
            "grande.png", PNG + b"\x00" * 100, max_bytes=LIMITES.max_arquivo_bytes
        )


def test_lote_valido() -> None:
    arqs = upload.validar_lote([("a.png", PNG), ("b.jpg", JPEG)], LIMITES)
    assert len(arqs) == 2
    assert {a.formato for a in arqs} == {FormatoImagem.PNG, FormatoImagem.JPEG}


def test_lote_vazio_rejeitado() -> None:
    with pytest.raises(LoteExcedeLimite):
        upload.validar_lote([], LIMITES)


def test_lote_excede_quantidade() -> None:
    with pytest.raises(LoteExcedeLimite):
        upload.validar_lote([("a.png", PNG), ("b.png", PNG), ("c.png", PNG)], LIMITES)


def test_lote_excede_total() -> None:
    limites = upload.LimitesUpload(
        max_arquivo_bytes=32, max_arquivos=3, max_total_bytes=64
    )
    with pytest.raises(LoteExcedeLimite):
        upload.validar_lote(
            [("a.png", PNG), ("b.png", PNG), ("c.png", PNG)], limites
        )
