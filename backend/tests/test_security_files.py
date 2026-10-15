from pathlib import Path

import pytest

from app.security import files

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 8


def test_detectar_formato_por_assinatura() -> None:
    assert files.detectar_formato(PNG) is files.FormatoImagem.PNG
    assert files.detectar_formato(JPEG) is files.FormatoImagem.JPEG
    assert files.detectar_formato(WEBP) is files.FormatoImagem.WEBP


def test_detectar_formato_desconhecido() -> None:
    assert files.detectar_formato(b"GIF89a" + b"\x00" * 10) is None
    assert files.detectar_formato(b"MZ\x90\x00") is None


def test_gerar_nome_interno_e_unico() -> None:
    primeiro = files.gerar_nome_interno(files.FormatoImagem.PNG)
    segundo = files.gerar_nome_interno(files.FormatoImagem.PNG)
    assert primeiro.endswith(".png")
    assert len(primeiro) == 32 + len(".png")
    assert primeiro != segundo


def test_validacao_id_lote() -> None:
    lote_id = files.gerar_id_lote()
    assert files.validar_id_lote(lote_id)
    assert files.exigir_id_lote(lote_id) == lote_id
    assert not files.validar_id_lote("../../etc/passwd")
    assert not files.validar_id_lote("")
    with pytest.raises(files.CaminhoInseguro):
        files.exigir_id_lote("nao-e-valido")


def test_resolver_caminho_seguro_aceita_dentro(tmp_path: Path) -> None:
    base = tmp_path / "lote"
    base.mkdir()
    alvo = files.resolver_caminho_seguro(base, "imagens", "a.jpg")
    assert alvo == (base / "imagens" / "a.jpg").resolve()


def test_resolver_caminho_seguro_bloqueia_travessia(tmp_path: Path) -> None:
    base = tmp_path / "lote"
    base.mkdir()
    with pytest.raises(files.CaminhoInseguro):
        files.resolver_caminho_seguro(base, "..", "fora.jpg")
