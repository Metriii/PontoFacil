"""Ponto de entrada da API PontoFácil (esqueleto — etapa 2).

Este módulo apenas sobe a aplicação FastAPI, configura o CORS restrito às
origens locais e expõe um healthcheck. Os endpoints de lote, OCR, revisão e
exportação serão adicionados nas etapas seguintes do PRD §17.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings

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
