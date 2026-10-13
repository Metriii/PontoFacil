from __future__ import annotations

import calendar
import re

HORARIO_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def validar_registro(registro: dict) -> tuple[list[str], str]:
    duvidas: list[str] = []
    critico = False

    mes = registro.get("mes")
    ano = registro.get("ano")
    dia = registro.get("dia")

    if mes is None:
        duvidas.append("mes não identificado")
        critico = True
    elif not (1 <= mes <= 12):
        duvidas.append(f"mes inválido: {mes}")
        critico = True

    if ano is None:
        duvidas.append("ano não identificado")
        critico = True
    elif ano < 1900 or ano > 2100:
        duvidas.append(f"ano inválido: {ano}")
        critico = True

    if dia is None:
        duvidas.append("dia não identificado")
        critico = True
    elif mes is not None and ano is not None and 1 <= mes <= 12:
        dias_no_mes = calendar.monthrange(ano, mes)[1]
        if not (1 <= dia <= dias_no_mes):
            duvidas.append(f"dia {dia} inválido para {mes}/{ano}")
            critico = True

    funcionario = registro.get("funcionario")
    if not funcionario:
        duvidas.append("funcionário não identificado")
        critico = True

    campos_horario = ["entrada", "saida_almoco", "volta_almoco", "saida_final"]
    horarios_presentes = []
    for campo in campos_horario:
        valor = registro.get(campo)
        if valor is not None:
            if not HORARIO_RE.match(valor):
                duvidas.append(f"{campo} com formato inválido: {valor}")
                critico = True
            else:
                horarios_presentes.append((campo, valor))

    if len(horarios_presentes) == 1:
        duvidas.append("apenas um horário identificado — verificar se há mais registros")
    elif len(horarios_presentes) == 2:
        duvidas.append("apenas dois horários identificados — verificar se há mais registros")
    elif len(horarios_presentes) == 3:
        duvidas.append("apenas três horários identificados — verificar se há mais registros")

    if len(horarios_presentes) >= 2:
        valores = [v for _, v in horarios_presentes]
        for i in range(len(valores) - 1):
            if valores[i] >= valores[i + 1]:
                duvidas.append("horários fora de ordem cronológica")
                critico = True
                break

    if critico:
        confianca = "baixa"
    elif not duvidas:
        confianca = "alta"
    else:
        confianca = "media"

    return duvidas, confianca
