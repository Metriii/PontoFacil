from pathlib import Path

import pytest

from app.persistence import json_store


def test_gravar_e_ler(tmp_path: Path) -> None:
    caminho = tmp_path / "dados.json"
    json_store.gravar_json(caminho, {"a": 1, "b": ["x", "y"]})
    assert json_store.ler_json(caminho) == {"a": 1, "b": ["x", "y"]}


def test_escrita_atomica_nao_deixa_temporario(tmp_path: Path) -> None:
    caminho = tmp_path / "dados.json"
    json_store.gravar_json(caminho, {"a": 1})
    assert not caminho.with_name(caminho.name + ".tmp").exists()


def test_gravar_cria_diretorios(tmp_path: Path) -> None:
    caminho = tmp_path / "sub" / "dir" / "dados.json"
    json_store.gravar_json(caminho, {"ok": True})
    assert caminho.exists()


def test_ler_json_ou_retorna_padrao(tmp_path: Path) -> None:
    assert json_store.ler_json_ou(tmp_path / "ausente.json", []) == []


def test_json_corrompido_levanta_erro(tmp_path: Path) -> None:
    caminho = tmp_path / "ruim.json"
    caminho.write_text("{invalido", encoding="utf-8")
    with pytest.raises(json_store.DadosCorrompidos):
        json_store.ler_json(caminho)
