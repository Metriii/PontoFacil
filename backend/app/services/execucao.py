"""Execução de tarefas em segundo plano (etapa 8, ARQUITETURA §7).

O processamento de um lote não pode bloquear a requisição HTTP. Abstraímos o
envio da tarefa em um :class:`ExecutorLotes`: em produção usa-se uma thread
(``concurrent.futures``, sem dependências novas); nos testes, uma execução
imediata e determinística.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Protocol

Tarefa = Callable[[], None]


class ExecutorLotes(Protocol):
    """Envia uma tarefa de processamento de lote."""

    def enviar(self, lote_id: str, tarefa: Tarefa) -> None: ...

    def desligar(self) -> None: ...


class ExecutorThreads:
    """Executa as tarefas em um ``ThreadPoolExecutor`` (um worker por lote)."""

    def __init__(self, max_workers: int = 1) -> None:
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="ponto-lote"
        )

    def enviar(self, lote_id: str, tarefa: Tarefa) -> None:
        self._pool.submit(tarefa)

    def desligar(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)


class ExecutorImediato:
    """Executa a tarefa na hora (usado em testes para determinismo)."""

    def enviar(self, lote_id: str, tarefa: Tarefa) -> None:
        tarefa()

    def desligar(self) -> None:
        return None
