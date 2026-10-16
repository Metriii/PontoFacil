from app.ocr import ErroImagem
from app.persistence import RepositorioLotes
from app.security import ArquivoRecebido, FormatoImagem
from app.services import ServicoLotes, processar_lote

from .conftest import PNG, REGISTRO_COMPLETO, folha_com


def _criar_lote(tmp_path, quantidade: int = 1):
    repo = RepositorioLotes(base=tmp_path)
    servico = ServicoLotes(repo, None, extrator=folha_com([dict(REGISTRO_COMPLETO)]))
    arquivos = [
        ArquivoRecebido(
            nome_original=f"foto{i}.png",
            nome_interno=f"foto{i}.png",
            formato=FormatoImagem.PNG,
            tamanho=len(PNG),
            conteudo=PNG,
        )
        for i in range(quantidade)
    ]
    return repo, servico.criar_lote(arquivos)


def test_processar_lote_grava_fichas_e_duvidas(tmp_path) -> None:
    repo, lote = _criar_lote(tmp_path)
    processar_lote(lote.lote_id, repo=repo, extrator=folha_com([dict(REGISTRO_COMPLETO)]))

    atual = repo.obter(lote.lote_id)
    assert atual.estado == "concluido"
    assert atual.progresso.processados == 1
    assert repo.carregar_fichas(lote.lote_id)[0].registros[0].entrada == "08:00"
    assert repo.carregar_duvidas(lote.lote_id) == []


def test_processar_lote_erro_isolado(tmp_path) -> None:
    repo, lote = _criar_lote(tmp_path, quantidade=2)
    chamadas = {"n": 0}

    def extrator(dados: bytes, *, origem: str):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise ErroImagem("Imagem ilegível.")
        return folha_com([dict(REGISTRO_COMPLETO)])(dados, origem=origem)

    processar_lote(lote.lote_id, repo=repo, extrator=extrator)
    atual = repo.obter(lote.lote_id)
    assert atual.estado == "concluido_com_pendencias"
    assert atual.progresso.processados == 1
    assert atual.progresso.falhas == 1
    assert [i.status for i in atual.imagens] == ["falha", "ok"]


def test_processar_lote_todas_falham(tmp_path) -> None:
    repo, lote = _criar_lote(tmp_path)

    def extrator(dados: bytes, *, origem: str):
        raise ErroImagem("Falha.")

    processar_lote(lote.lote_id, repo=repo, extrator=extrator)
    atual = repo.obter(lote.lote_id)
    assert atual.estado == "falhou"
    assert atual.progresso.falhas == 1
