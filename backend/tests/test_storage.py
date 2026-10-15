from pathlib import Path

import pytest

from app import storage
from app.security.files import CaminhoInseguro, gerar_id_lote

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


def test_salvar_imagem_grava_arquivo(tmp_path: Path) -> None:
    lote_id = gerar_id_lote()
    destino = storage.salvar_imagem(lote_id, "abc.png", PNG, base=tmp_path)
    assert destino.parent == (tmp_path / "lotes" / lote_id / "imagens")
    assert destino.read_bytes() == PNG


def test_salvar_imagem_nao_deixa_temporario(tmp_path: Path) -> None:
    lote_id = gerar_id_lote()
    destino = storage.salvar_imagem(lote_id, "abc.png", PNG, base=tmp_path)
    assert not destino.with_name(destino.name + ".tmp").exists()


def test_salvar_imagem_id_lote_invalido(tmp_path: Path) -> None:
    with pytest.raises(CaminhoInseguro):
        storage.salvar_imagem("../../etc", "abc.png", PNG, base=tmp_path)


def test_salvar_imagem_bloqueia_travessia(tmp_path: Path) -> None:
    lote_id = gerar_id_lote()
    with pytest.raises(CaminhoInseguro):
        storage.salvar_imagem(lote_id, "../escape.png", PNG, base=tmp_path)
