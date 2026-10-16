from fastapi.testclient import TestClient

from app.api import lotes as api_lotes
from app.ocr import ErroImagem
from app.persistence import RepositorioLotes
from app.security import LimitesUpload
from app.services import ExecutorImediato, ServicoLotes

from .conftest import (
    PNG,
    REGISTRO_COMPLETO,
    enviar_lote,
    folha_com,
    montar_cliente,
)


def test_criar_lote_processa_e_disponibiliza_resultados(tmp_path) -> None:
    cliente, servico = montar_cliente(tmp_path, folha_com([dict(REGISTRO_COMPLETO)]))

    resposta = enviar_lote(cliente)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert len(corpo["lote_id"]) == 32
    assert corpo["estado"] == "concluido"

    status = cliente.get(f"/api/lotes/{corpo['lote_id']}")
    assert status.status_code == 200
    dados_status = status.json()
    assert dados_status["progresso"] == {
        "total": 1,
        "processados": 1,
        "falhas": 0,
        "revisao": 0,
    }
    assert dados_status["estado"] == "concluido"
    assert dados_status["imagens"][0]["status"] == "ok"

    resultados = cliente.get(f"/api/lotes/{corpo['lote_id']}/resultados")
    assert resultados.status_code == 200
    fichas = resultados.json()["fichas"]
    assert len(fichas) == 1
    assert fichas[0]["funcionario"]["nome"] == "TESTE"
    assert fichas[0]["mes"] == 8 and fichas[0]["ano"] == 2026
    assert fichas[0]["registros"][0]["entrada"] == "08:00"
    assert fichas[0]["registros"][0]["status_validacao"] == "confirmado"

    assert cliente.get(f"/api/lotes/{corpo['lote_id']}/duvidas").json() == []


def test_lote_com_pendencia_gera_duvidas(tmp_path) -> None:
    extrator = folha_com([{"entrada": "08:00", "saida": "17:00"}])
    cliente, _ = montar_cliente(tmp_path, extrator)

    lote_id = enviar_lote(cliente).json()["lote_id"]
    status = cliente.get(f"/api/lotes/{lote_id}").json()
    assert status["estado"] == "concluido_com_pendencias"
    assert status["progresso"]["revisao"] == 1

    duvidas = cliente.get(f"/api/lotes/{lote_id}/duvidas").json()
    assert any(d["campo"] == "intervalo" for d in duvidas)


def test_criar_lote_arquivo_invalido(tmp_path) -> None:
    cliente, _ = montar_cliente(tmp_path, folha_com([dict(REGISTRO_COMPLETO)]))
    resposta = cliente.post(
        "/api/lotes",
        files=[("arquivos", ("malicioso.png", b"MZ\x90\x00" + b"\x00" * 20, "image/png"))],
    )
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "formato_nao_permitido"


def test_criar_lote_sem_arquivos(tmp_path) -> None:
    cliente, _ = montar_cliente(tmp_path, folha_com([dict(REGISTRO_COMPLETO)]))
    assert cliente.post("/api/lotes").status_code == 422


def test_criar_lote_excede_limite(tmp_path, monkeypatch) -> None:
    cliente, _ = montar_cliente(tmp_path, folha_com([dict(REGISTRO_COMPLETO)]))
    monkeypatch.setattr(
        api_lotes, "_limites", lambda: LimitesUpload(4, 2, 8)
    )
    resposta = cliente.post(
        "/api/lotes", files=[("arquivos", ("grande.png", PNG, "image/png"))]
    )
    assert resposta.status_code == 413


def test_lote_inexistente(tmp_path) -> None:
    cliente, _ = montar_cliente(tmp_path, folha_com([dict(REGISTRO_COMPLETO)]))
    assert cliente.get(f"/api/lotes/{'0' * 32}").status_code == 404


def test_lote_id_invalido(tmp_path) -> None:
    cliente, _ = montar_cliente(tmp_path, folha_com([dict(REGISTRO_COMPLETO)]))
    assert cliente.get("/api/lotes/nao-eh-hex").status_code == 404


def test_erro_de_ocr_isolado_por_imagem(tmp_path) -> None:
    ruim = b"\x89PNG\r\n\x1a\n" + b"\x01" * 10

    def extrator(dados: bytes, *, origem: str):
        if dados == ruim:
            raise ErroImagem("Imagem não pôde ser processada.")
        return folha_com([dict(REGISTRO_COMPLETO)])(dados, origem=origem)

    cliente, servico = montar_cliente(tmp_path, extrator)
    resposta = cliente.post(
        "/api/lotes",
        files=[
            ("arquivos", ("ok.png", PNG, "image/png")),
            ("arquivos", ("ruim.png", ruim, "image/png")),
        ],
    )
    assert resposta.status_code == 201
    lote_id = resposta.json()["lote_id"]

    status = cliente.get(f"/api/lotes/{lote_id}").json()
    assert status["progresso"]["processados"] == 1
    assert status["progresso"]["falhas"] == 1
    assert status["estado"] == "concluido_com_pendencias"
    erros = [i["erro"] for i in status["imagens"] if i["status"] == "falha"]
    assert erros == ["Imagem não pôde ser processada."]


def test_todas_as_imagens_falham(tmp_path) -> None:
    def extrator(dados: bytes, *, origem: str):
        raise ErroImagem("Falha simulada.")

    cliente, _ = montar_cliente(tmp_path, extrator)
    lote_id = enviar_lote(cliente).json()["lote_id"]
    status = cliente.get(f"/api/lotes/{lote_id}").json()
    assert status["estado"] == "falhou"
    assert status["progresso"]["falhas"] == 1
