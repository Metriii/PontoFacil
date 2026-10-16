"""Normalização e aritmética de horários (etapa 7).

Regras (PRD §8):

- O horário normalizado usa o formato ``HH:MM``.
- O valor bruto reconhecido pelo OCR é preservado em ``RegistroDiario.valor_bruto``
  e nunca é sobrescrito nem completado aqui.
- Valores ilegíveis/ausentes permanecem ``None`` — nunca ``00:00`` e nunca
  "inventados" a partir de uma hipótese.

Este módulo é puro (não depende de OCR nem de persistência) para permitir
testes determinísticos e independentes (RNF-008/RNF-010).
"""

from __future__ import annotations

import re

#: Formato normalizado aceito (PRD §9).
HORARIO_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

#: Tolerante a separadores comuns do OCR: ``8:00``, ``08h30``, ``08.15``.
_TOLERANTE_RE = re.compile(r"^(?P<h>\d{1,2})[:hH.](?P<m>\d{2})$")


def normalizar_horario(bruto: str | None) -> str | None:
    """Converte um horário reconhecido em ``HH:MM`` ou ``None``.

    Só aceita dígitos reais: letras confundidas pelo OCR (ex.: ``O8:OO``) não
    são convertidas, pois isso seria inventar um valor.
    """
    if not bruto:
        return None
    m = _TOLERANTE_RE.match(bruto.strip())
    if not m:
        return None
    hora = int(m.group("h"))
    minuto = int(m.group("m"))
    if hora > 23 or minuto > 59:
        return None
    return f"{hora:02d}:{minuto:02d}"


def horario_valido(valor: str | None) -> bool:
    """Indica se o valor já está no formato normalizado ``HH:MM``."""
    return bool(valor) and HORARIO_RE.match(valor) is not None


def minutos_do_dia(valor: str) -> int:
    """Minutos desde a meia-noite de um horário ``HH:MM`` válido."""
    if not horario_valido(valor):
        raise ValueError(f"Horário inválido: {valor!r}")
    hora, minuto = valor.split(":")
    return int(hora) * 60 + int(minuto)


def formatar_duracao(minutos: int) -> str:
    """Formata uma duração em minutos como ``HH:MM`` (horas podem passar de 23)."""
    sinal = "-" if minutos < 0 else ""
    total = abs(int(minutos))
    return f"{sinal}{total // 60:02d}:{total % 60:02d}"
