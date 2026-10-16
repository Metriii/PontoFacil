"""Modelos Pydantic (entrada/saída) da API (PRD §10).

Convertem as entidades persistidas (dataclasses) em respostas JSON estáveis,
sem vazar caminhos internos além do necessário. Nenhuma regra de negócio mora
aqui.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..persistence.models import (
    ArquivoGerado,
    Correcao,
    Duvida,
    FichaPonto,
    Imagem,
    Lote,
    RegistroDiario,
)

CampoHorario = Literal["entrada", "saida_almoco", "volta_almoco", "saida"]


class ProgressoSchema(BaseModel):
    total: int
    processados: int
    falhas: int
    revisao: int


class ImagemSchema(BaseModel):
    imagem_id: str
    nome_original: str
    status: str
    erro: str | None = None


class ArquivoGeradoSchema(BaseModel):
    arquivo_id: str
    nome: str
    tipo: str
    funcionario: str | None = None
    referencia: str | None = None
    gerado_em: str


class PlanilhaSchema(BaseModel):
    """Arquivo exportado pronto para download (compatível com ``Planilha`` do frontend)."""

    arquivo: str
    funcionario: str | None = None
    referencia: str | None = None
    status: str
    url: str


class ExportacaoLote(BaseModel):
    lote_id: str
    planilhas: list[PlanilhaSchema] = Field(default_factory=list)
    consolidado: PlanilhaSchema | None = None
    total_registros: int = 0


class LoteCriado(BaseModel):
    lote_id: str
    estado: str


class LoteStatus(BaseModel):
    lote_id: str
    criado_em: str
    estado: str
    progresso: ProgressoSchema
    imagens: list[ImagemSchema] = Field(default_factory=list)
    arquivos_gerados: list[ArquivoGeradoSchema] = Field(default_factory=list)


class CorrecaoSchema(BaseModel):
    correcao_id: str
    campo: str
    valor_anterior: str | None = None
    valor_novo: str | None = None
    corrigido_em: str
    autor: str | None = None


class FuncionarioSchema(BaseModel):
    funcionario_id: str
    nome: str | None = None
    codigo: str | None = None
    empresa: str | None = None
    departamento: str | None = None
    funcao: str | None = None


class RegistroSchema(BaseModel):
    registro_id: str
    dia: int | None = None
    dia_semana: str | None = None
    entrada: str | None = None
    saida_almoco: str | None = None
    volta_almoco: str | None = None
    saida: str | None = None
    tipo_dia: str | None = None
    status_validacao: str
    confianca: float | None = None
    observacao: str | None = None
    origem: str | None = None
    correcao: CorrecaoSchema | None = None


class FichaSchema(BaseModel):
    funcionario: FuncionarioSchema
    mes: int | None = None
    ano: int | None = None
    registros: list[RegistroSchema] = Field(default_factory=list)


class ResultadosLote(BaseModel):
    lote_id: str
    fichas: list[FichaSchema] = Field(default_factory=list)


class DuvidaSchema(BaseModel):
    duvida_id: str
    registro_id: str
    campo: str
    motivo: str
    origem: str | None = None


class CorrecaoEntrada(BaseModel):
    campo: CampoHorario
    valor: str | None = None


# --- Conversores -------------------------------------------------------------


def imagem_schema(imagem: Imagem) -> ImagemSchema:
    return ImagemSchema(
        imagem_id=imagem.imagem_id,
        nome_original=imagem.nome_original,
        status=imagem.status,
        erro=imagem.erro,
    )


def arquivo_schema(arquivo: ArquivoGerado) -> ArquivoGeradoSchema:
    return ArquivoGeradoSchema(
        arquivo_id=arquivo.arquivo_id,
        nome=arquivo.nome,
        tipo=arquivo.tipo,
        funcionario=arquivo.funcionario,
        referencia=arquivo.referencia,
        gerado_em=arquivo.gerado_em,
    )


def lote_status(lote: Lote) -> LoteStatus:
    return LoteStatus(
        lote_id=lote.lote_id,
        criado_em=lote.criado_em,
        estado=lote.estado,
        progresso=ProgressoSchema(
            total=lote.progresso.total,
            processados=lote.progresso.processados,
            falhas=lote.progresso.falhas,
            revisao=lote.progresso.revisao,
        ),
        imagens=[imagem_schema(i) for i in lote.imagens],
        arquivos_gerados=[arquivo_schema(a) for a in lote.arquivos_gerados],
    )


def correcao_schema(correcao: Correcao) -> CorrecaoSchema:
    return CorrecaoSchema(
        correcao_id=correcao.correcao_id,
        campo=correcao.campo,
        valor_anterior=correcao.valor_anterior,
        valor_novo=correcao.valor_novo,
        corrigido_em=correcao.corrigido_em,
        autor=correcao.autor,
    )


def registro_schema(registro: RegistroDiario) -> RegistroSchema:
    return RegistroSchema(
        registro_id=registro.registro_id,
        dia=registro.dia,
        dia_semana=registro.dia_semana,
        entrada=registro.entrada,
        saida_almoco=registro.saida_almoco,
        volta_almoco=registro.volta_almoco,
        saida=registro.saida,
        tipo_dia=registro.tipo_dia,
        status_validacao=registro.status_validacao,
        confianca=registro.confianca,
        observacao=registro.observacao,
        origem=registro.origem,
        correcao=(
            correcao_schema(registro.correcao) if registro.correcao else None
        ),
    )


def ficha_schema(ficha: FichaPonto) -> FichaSchema:
    return FichaSchema(
        funcionario=FuncionarioSchema(**ficha.funcionario.para_dict()),
        mes=ficha.mes,
        ano=ficha.ano,
        registros=[registro_schema(r) for r in ficha.registros],
    )


def resultados_lote(lote_id: str, fichas: list[FichaPonto]) -> ResultadosLote:
    return ResultadosLote(
        lote_id=lote_id, fichas=[ficha_schema(f) for f in fichas]
    )


def duvida_schema(duvida: Duvida) -> DuvidaSchema:
    return DuvidaSchema(
        duvida_id=duvida.duvida_id,
        registro_id=duvida.registro_id,
        campo=duvida.campo,
        motivo=duvida.motivo,
        origem=duvida.origem,
    )


def planilha_schema(arquivo: ArquivoGerado, lote_id: str) -> PlanilhaSchema:
    """Converte um arquivo gerado em planilha baixável (URL relativa ao lote)."""
    return PlanilhaSchema(
        arquivo=arquivo.nome,
        funcionario=arquivo.funcionario,
        referencia=arquivo.referencia,
        status="disponível",
        url=f"/api/lotes/{lote_id}/downloads/{arquivo.arquivo_id}",
    )
