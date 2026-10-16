"""Routers da API REST (etapa 8)."""

from fastapi import APIRouter

from .exportacao import router as exportacao_router
from .lotes import router as lotes_router
from .registros import router as registros_router

api_router = APIRouter()
api_router.include_router(lotes_router)
api_router.include_router(registros_router)
api_router.include_router(exportacao_router)

__all__ = ["api_router"]
