from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.leitor_imagem import Palavra


@dataclass
class CamposCartao:
    funcionario: str | None = None
    mes: int | None = None
    ano: int | None = None
    registros: list[dict] = field(default_factory=list)
    confianca_geral: float = 0.0
    duvidas: list[str] = field(default_factory=list)


_HORARIO_RE = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")
_MES_RE = re.compile(r"(?:m[eê]s|refer[êe]ncia)[\s:]*(\d{1,2})", re.IGNORECASE)
_ANO_RE = re.compile(r"(?:ano)[\s:]*(\d{4})", re.IGNORECASE)
_ANO_RE_2 = re.compile(r"\b(20\d{2})\b")
_NOME_RE = re.compile(r"(?:nome|funcion[áa]rio)[\s:]*([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)", re.IGNORECASE)


def _normalizar_horario(texto: str) -> str | None:
    texto = texto.strip().replace(".", ":").replace(";", ":").replace(",", ":")
    m = re.match(r"^(\d{1,2}):(\d{2})$", texto)
    if m:
        h, min_ = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= min_ <= 59:
            return f"{h:02d}:{min_:02d}"
    m = re.match(r"^(\d{1,2})(\d{2})$", texto)
    if m:
        h, min_ = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= min_ <= 59:
            return f"{h:02d}:{min_:02d}"
    return None


def identificar_campos(palavras: list[Palavra]) -> CamposCartao:
    campos = CamposCartao()
    if not palavras:
        campos.duvidas.append("Nenhum texto reconhecido na imagem")
        return campos

    texto_completo = " ".join(p.texto for p in palavras)
    linhas: dict[int, list[Palavra]] = {}
    for p in palavras:
        chave = p.y // 20
        linhas.setdefault(chave, []).append(p)

    m_nome = _NOME_RE.search(texto_completo)
    if m_nome:
        campos.funcionario = m_nome.group(1).strip()
    else:
        palavras_ordenadas = sorted(palavras, key=lambda p: (p.y, p.x))
        for p in palavras_ordenadas[:5]:
            if len(p.texto) > 3 and p.texto[0].isupper() and " " not in p.texto:
                campos.funcionario = p.texto
                break
        if not campos.funcionario:
            campos.duvidas.append("Nome do funcionário não identificado")

    m_mes = _MES_RE.search(texto_completo)
    if m_mes:
        mes = int(m_mes.group(1))
        if 1 <= mes <= 12:
            campos.mes = mes
        else:
            campos.duvidas.append(f"Mês inválido: {mes}")
    else:
        campos.duvidas.append("Mês não identificado")

    m_ano = _ANO_RE.search(texto_completo)
    if m_ano:
        campos.ano = int(m_ano.group(1))
    else:
        m_ano2 = _ANO_RE_2.search(texto_completo)
        if m_ano2:
            campos.ano = int(m_ano2.group(1))
        else:
            campos.duvidas.append("Ano não identificado")

    registros: list[dict] = []
    for chave_linha in sorted(linhas.keys()):
        linha_palavras = sorted(linhas[chave_linha], key=lambda p: p.x)
        numeros: list[tuple[int, Palavra]] = []
        horarios: list[tuple[str, Palavra]] = []
        for p in linha_palavras:
            num = p.texto.strip()
            if num.isdigit() and 1 <= int(num) <= 31:
                numeros.append((int(num), p))
            hor = _normalizar_horario(p.texto)
            if hor:
                horarios.append((hor, p))

        if numeros and horarios:
            dia = numeros[0][0]
            reg = {"dia": dia, "entrada": None, "saida_almoco": None, "volta_almoco": None, "saida_final": None}
            if len(horarios) >= 1:
                reg["entrada"] = horarios[0][0]
            if len(horarios) >= 2:
                reg["saida_almoco"] = horarios[1][0]
            if len(horarios) >= 3:
                reg["volta_almoco"] = horarios[2][0]
            if len(horarios) >= 4:
                reg["saida_final"] = horarios[3][0]
            registros.append(reg)

    campos.registros = registros
    if not registros:
        campos.duvidas.append("Nenhum registro de horário identificado")

    confiancas = [p.confianca for p in palavras if p.confianca > 0]
    campos.confianca_geral = sum(confiancas) / len(confiancas) if confiancas else 0.0

    return campos
