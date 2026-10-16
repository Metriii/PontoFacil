from .conftest import REGISTRO_COMPLETO, enviar_lote, folha_com, montar_cliente


def _primeiro_registro(cliente, lote_id):
    fichas = cliente.get(f"/api/lotes/{lote_id}/resultados").json()["fichas"]
    return fichas[0]["registros"][0]


def test_corrigir_registro_ilegivel_remove_duvida(tmp_path) -> None:
    extrator = folha_com(
        [{"entrada": "08:00", "saida": None, "valor_bruto": {"saida": "O8:OO"}}]
    )
    cliente, servico = montar_cliente(tmp_path, extrator)
    lote_id = enviar_lote(cliente).json()["lote_id"]

    registro = _primeiro_registro(cliente, lote_id)
    assert registro["status_validacao"] == "pendente"
    duvidas = cliente.get(f"/api/lotes/{lote_id}/duvidas").json()
    assert any(d["campo"] == "saida" for d in duvidas)

    resposta = cliente.patch(
        f"/api/registros/{registro['registro_id']}",
        json={"campo": "saida", "valor": "17:00"},
    )
    assert resposta.status_code == 200
    corrigido = resposta.json()
    assert corrigido["saida"] == "17:00"
    assert corrigido["status_validacao"] == "corrigido"
    assert corrigido["correcao"]["campo"] == "saida"
    assert corrigido["correcao"]["valor_anterior"] is None
    assert corrigido["correcao"]["valor_novo"] == "17:00"

    duvidas_apos = cliente.get(f"/api/lotes/{lote_id}/duvidas").json()
    assert all(d["campo"] != "saida" for d in duvidas_apos)

    correcoes = servico.repo.carregar_correcoes(lote_id)
    assert len(correcoes) == 1
    assert correcoes[0].campo == "saida"
    assert correcoes[0].valor_novo == "17:00"


def test_corrigir_valor_invalido(tmp_path) -> None:
    cliente, _ = montar_cliente(tmp_path, folha_com([dict(REGISTRO_COMPLETO)]))
    lote_id = enviar_lote(cliente).json()["lote_id"]
    registro = _primeiro_registro(cliente, lote_id)

    resposta = cliente.patch(
        f"/api/registros/{registro['registro_id']}",
        json={"campo": "entrada", "valor": "abacaxi"},
    )
    assert resposta.status_code == 422


def test_corrigir_campo_invalido(tmp_path) -> None:
    cliente, _ = montar_cliente(tmp_path, folha_com([dict(REGISTRO_COMPLETO)]))
    lote_id = enviar_lote(cliente).json()["lote_id"]
    registro = _primeiro_registro(cliente, lote_id)

    resposta = cliente.patch(
        f"/api/registros/{registro['registro_id']}",
        json={"campo": "hora_extra", "valor": "18:00"},
    )
    assert resposta.status_code == 422


def test_corrigir_registro_inexistente(tmp_path) -> None:
    cliente, _ = montar_cliente(tmp_path, folha_com([dict(REGISTRO_COMPLETO)]))
    resposta = cliente.patch(
        "/api/registros/inexistente", json={"campo": "entrada", "valor": "08:00"}
    )
    assert resposta.status_code == 404


def test_corrigir_pode_limpar_horario(tmp_path) -> None:
    cliente, _ = montar_cliente(tmp_path, folha_com([dict(REGISTRO_COMPLETO)]))
    lote_id = enviar_lote(cliente).json()["lote_id"]
    registro = _primeiro_registro(cliente, lote_id)

    resposta = cliente.patch(
        f"/api/registros/{registro['registro_id']}",
        json={"campo": "saida", "valor": None},
    )
    assert resposta.status_code == 200
    assert resposta.json()["saida"] is None
    assert resposta.json()["status_validacao"] == "corrigido"
