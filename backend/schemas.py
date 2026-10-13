from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
import re

HORARIO_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class Registro(BaseModel):
    id: str
    funcionario: Optional[str] = None
    data: Optional[str] = None
    dia_semana: Optional[str] = None
    entrada: Optional[str] = None
    saida_almoco: Optional[str] = None
    volta_almoco: Optional[str] = None
    saida: Optional[str] = None
    confianca: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    revisar: Optional[bool] = None

    @field_validator("entrada", "saida_almoco", "volta_almoco", "saida")
    @classmethod
    def validar_horario(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not HORARIO_RE.match(v):
            raise ValueError(f"horário inválido: {v!r}")
        return v


class Planilha(BaseModel):
    arquivo: str
    funcionario: Optional[str] = None
    referencia: Optional[str] = None
    status: str
    url: str


class ResultadoProcessamento(BaseModel):
    total_cartoes: int
    processados: int
    registros: list[Registro] = Field(default_factory=list)
    planilhas: list[Planilha] = Field(default_factory=list)
    consolidado: Optional[Planilha] = None


class Progresso(BaseModel):
    atual: int = 0
    total: int = 0


class ProcessamentoStatus(BaseModel):
    id: str
    status: Literal["processando", "concluido", "erro"]
    progresso: Progresso = Field(default_factory=Progresso)
    erro: Optional[str] = None
    resultado: Optional[ResultadoProcessamento] = None


class Duvida(BaseModel):
    registro_id: str
    campo: str
    motivo: str
    valor_atual: Optional[str] = None


class ListaDuvidas(BaseModel):
    duvidas: list[Duvida] = Field(default_factory=list)


class CorreacaoRegistro(BaseModel):
    campo: Literal["funcionario", "data", "dia_semana", "entrada", "saida_almoco", "volta_almoco", "saida"]
    valor: Optional[str] = None

    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        horarios = {"entrada", "saida_almoco", "volta_almoco", "saida"}
        # Nota: campo é validado no endpoint para saber se é horário
        return v


class HealthResponse(BaseModel):
    status: str
    tesseract: bool
