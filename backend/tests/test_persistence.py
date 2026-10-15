from pathlib import Path

import pytest

from app.persistence import (
    ArquivoGerado,
    Correcao,
    Duvida,
    FichaPonto,
    Funcionario,
    Imagem,
    LoteNaoEncontrado,
    Progresso,
    RegistroDiario,
    RepositorioLotes,
)
from app.security.files import CaminhoInseguro


def test_criar_e_obter(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    lote = repo.criar()
    assert len(lote.lote_id) == 32
    assert lote.estado == "recebido"
    assert lote.progresso.total == 0
    assert repo.obter(lote.lote_id) == lote
    assert (tmp_path / "lotes" / lote.lote_id / "lote.json").exists()


def test_obter_inexistente(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    with pytest.raises(LoteNaoEncontrado):
        repo.obter("a" * 32)


def test_listar(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    a = repo.criar()
    b = repo.criar()
    assert {lote.lote_id for lote in repo.listar()} == {a.lote_id, b.lote_id}


def test_atualizar_estado_e_progresso(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    lote = repo.criar()
    repo.atualizar(lote.lote_id, estado="processando")
    repo.atualizar(lote.lote_id, progresso=Progresso(total=3, processados=1))
    lido = repo.obter(lote.lote_id)
    assert lido.estado == "processando"
    assert lido.progresso.total == 3
    assert lido.progresso.processados == 1


def test_estado_invalido_rejeitado(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    lote = repo.criar()
    with pytest.raises(ValueError):
        repo.atualizar(lote.lote_id, estado="inexistente")


def test_registrar_imagem(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    lote = repo.criar()
    imagem = Imagem(
        imagem_id="img1",
        nome_interno="a.jpg",
        nome_original="foto.jpg",
        caminho="imagens/a.jpg",
    )
    repo.registrar_imagem(lote.lote_id, imagem)
    assert repo.obter(lote.lote_id).imagens[0].nome_interno == "a.jpg"


def test_registrar_arquivo_gerado(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    lote = repo.criar()
    arquivo = ArquivoGerado(
        arquivo_id="arq1", nome="planilha.xlsx", tipo="consolidado", caminho="exports/p.xlsx"
    )
    repo.registrar_arquivo_gerado(lote.lote_id, arquivo)
    assert repo.obter(lote.lote_id).arquivos_gerados[0].nome == "planilha.xlsx"


def test_fichas_roundtrip_com_aninhamento(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    lote = repo.criar()
    correcao = Correcao(
        correcao_id="c1",
        registro_id="r1",
        campo="entrada",
        corrigido_em="2026-08-01T00:00:00+00:00",
        valor_anterior="08:0O",
        valor_novo="08:00",
    )
    registro = RegistroDiario(
        registro_id="r1",
        dia=3,
        entrada="08:00",
        valor_bruto={"entrada": "08:0O"},
        correcao=correcao,
    )
    ficha = FichaPonto(
        funcionario=Funcionario(funcionario_id="f1", nome="ALESSANY", codigo="007"),
        mes=8,
        ano=2026,
        registros=[registro],
    )
    repo.salvar_fichas(lote.lote_id, [ficha])
    lidas = repo.carregar_fichas(lote.lote_id)
    assert lidas == [ficha]
    assert lidas[0].registros[0].correcao is not None
    assert lidas[0].registros[0].correcao.valor_novo == "08:00"


def test_duvidas_e_correcoes(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    lote = repo.criar()
    repo.salvar_duvidas(
        lote.lote_id,
        [Duvida(duvida_id="d1", registro_id="r1", campo="saida", motivo="ilegivel")],
    )
    assert repo.carregar_duvidas(lote.lote_id)[0].motivo == "ilegivel"

    repo.registrar_correcao(
        lote.lote_id,
        Correcao(
            correcao_id="c1",
            registro_id="r1",
            campo="saida",
            corrigido_em="2026-08-01T00:00:00+00:00",
        ),
    )
    assert len(repo.carregar_correcoes(lote.lote_id)) == 1


def test_arquivos_ausentes_retornam_lista_vazia(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    lote = repo.criar()
    assert repo.carregar_fichas(lote.lote_id) == []
    assert repo.carregar_duvidas(lote.lote_id) == []
    assert repo.carregar_correcoes(lote.lote_id) == []


def test_lote_id_invalido_bloqueado(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    with pytest.raises(CaminhoInseguro):
        repo.obter("../../etc")


def test_recuperacao_apos_reinicio(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    lote = repo.criar()
    repo.atualizar(lote.lote_id, estado="concluido_com_pendencias")
    repo2 = RepositorioLotes(base=tmp_path)
    assert repo2.obter(lote.lote_id).estado == "concluido_com_pendencias"


def test_listar_ignora_lote_corrompido(tmp_path: Path) -> None:
    repo = RepositorioLotes(base=tmp_path)
    lote = repo.criar()
    caminho = tmp_path / "lotes" / lote.lote_id / "lote.json"
    caminho.write_text("{ruim", encoding="utf-8")
    assert repo.listar() == []
