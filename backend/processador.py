from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from backend.arquivos import listar_imagens
from backend.config import JSON_DIR
from backend.estrutura_cartao import identificar_campos
from backend.leitor_imagem import ler_horarios
from backend.schemas import ProcessamentoStatus, ResultadoProcessamento, Registro
from backend.validador import validar_registro

PROCESSAMENTOS: dict[str, ProcessamentoStatus] = {}


async def processar_cartoes(processamento_id: str, imagens: list[Path]) -> None:
    status = PROCESSAMENTOS[processamento_id]
    status.status = "processando"
    status.progresso = {"atual": 0, "total": len(imagens)}

    registros: list[Registro] = []
    erros: list[str] = []

    for i, img_path in enumerate(imagens):
        try:
            resultado_ocr = ler_horarios(img_path)
            if resultado_ocr.erro:
                erros.append(f"{img_path.name}: {resultado_ocr.erro}")
                registros.append(
                    Registro(
                        id=f"{processamento_id}_{i}",
                        funcionario=None,
                        data=None,
                        dia_semana=None,
                        entrada=None,
                        saida_almoco=None,
                        volta_almoco=None,
                        saida=None,
                        confianca=0.0,
                        revisar=True,
                    )
                )
                continue

            campos = identificar_campos(resultado_ocr.palavras)

            for j, reg_data in enumerate(campos.registros):
                registro_dict = {
                    "funcionario": campos.funcionario,
                    "mes": campos.mes,
                    "ano": campos.ano,
                    "dia": reg_data.get("dia"),
                    "entrada": reg_data.get("entrada"),
                    "saida_almoco": reg_data.get("saida_almoco"),
                    "volta_almoco": reg_data.get("volta_almoco"),
                    "saida_final": reg_data.get("saida_final"),
                }
                duvidas, confianca = validar_registro(registro_dict)
                duvidas.extend(campos.duvidas)

                if campos.ano and campos.mes and reg_data.get("dia"):
                    from datetime import date
                    try:
                        d = date(campos.ano, campos.mes, reg_data["dia"])
                        registro_dict["data"] = d.isoformat()
                        registro_dict["dia_semana"] = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"][d.weekday()]
                    except ValueError:
                        pass

                registros.append(
                    Registro(
                        id=f"{processamento_id}_{i}_{j}",
                        funcionario=registro_dict.get("funcionario"),
                        data=registro_dict.get("data"),
                        dia_semana=registro_dict.get("dia_semana"),
                        entrada=registro_dict.get("entrada"),
                        saida_almoco=registro_dict.get("saida_almoco"),
                        volta_almoco=registro_dict.get("volta_almoco"),
                        saida=registro_dict.get("saida_final"),
                        confianca=campos.confianca_geral if confianca == "alta" else (0.5 if confianca == "media" else 0.2),
                        revisar=len(duvidas) > 0,
                    )
                )

            if not campos.registros:
                registros.append(
                    Registro(
                        id=f"{processamento_id}_{i}",
                        funcionario=campos.funcionario,
                        data=None,
                        dia_semana=None,
                        entrada=None,
                        saida_almoco=None,
                        volta_almoco=None,
                        saida=None,
                        confianca=campos.confianca_geral,
                        revisar=True,
                    )
                )

        except Exception as e:
            erros.append(f"{img_path.name}: {str(e)}")
            registros.append(
                Registro(
                    id=f"{processamento_id}_{i}",
                    funcionario=None,
                    data=None,
                    dia_semana=None,
                    entrada=None,
                    saida_almoco=None,
                    volta_almoco=None,
                    saida=None,
                    confianca=0.0,
                    revisar=True,
                )
            )

        status.progresso = {"atual": i + 1, "total": len(imagens)}
        await asyncio.sleep(0)

    status.status = "concluido"
    status.resultado = ResultadoProcessamento(
        total_cartoes=len(imagens),
        processados=len(imagens) - len(erros),
        registros=registros,
        planilhas=[],
    )

    json_path = JSON_DIR / f"{processamento_id}.json"
    json_path.write_text(
        json.dumps(
            {
                "id": processamento_id,
                "status": status.status,
                "progresso": status.progresso,
                "erro": "; ".join(erros) if erros else None,
                "resultado": status.resultado.model_dump() if status.resultado else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def criar_processamento() -> str:
    pid = str(uuid.uuid4())
    PROCESSAMENTOS[pid] = ProcessamentoStatus(id=pid, status="processando")
    return pid


def obter_processamento(pid: str) -> ProcessamentoStatus | None:
    return PROCESSAMENTOS.get(pid)


def listar_imagens_processamento(pasta: Path) -> list[Path]:
    return listar_imagens(pasta)
