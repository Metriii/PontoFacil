"""Ponto de entrada da API PontoFácil.

Sobe a aplicação FastAPI, configura o CORS restrito às origens locais, expõe o
healthcheck e os routers de lote (etapa 8). O processamento em segundo plano usa
um ``ThreadPoolExecutor`` (um worker por lote), sem dependências extras.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import api_router
from .config import settings
from .persistence import RepositorioLotes
from .security import ArquivoExcedeLimite, ErroUpload, LoteExcedeLimite
from .services import ExecutorThreads, ServicoLotes

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API local para leitura, conferência e exportação de folhas de ponto.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)

#: Instância única do serviço de lotes (repositório + executor em segundo plano).
app.state.servico_lotes = ServicoLotes(RepositorioLotes(), ExecutorThreads())


@app.exception_handler(ErroUpload)
async def _erro_upload_handler(_: Request, exc: ErroUpload) -> JSONResponse:
    """Converte erros de upload em respostas 4xx sem vazar detalhes internos."""
    status = 413 if isinstance(exc, (ArquivoExcedeLimite, LoteExcedeLimite)) else 400
    return JSONResponse(
        status_code=status, content={"detail": exc.mensagem, "codigo": exc.codigo}
    )


@app.get("/", tags=["infra"])
def root() -> dict[str, str]:
    """Informações básicas da API."""
    return {
        "app": settings.app_name,
        "version": settings.version,
        "health": "/api/health",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["infra"])
def health() -> dict[str, str]:
    """Healthcheck usado para confirmar que o backend está no ar."""
    return {"status": "ok", "app": settings.app_name, "version": settings.version}
