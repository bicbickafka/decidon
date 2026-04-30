# -*- coding: utf-8 -*-
"""
main.py
Entry point for the FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import api_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    :return: FastAPI application
    :rtype: FastAPI
    """
    _app = FastAPI(
        title="Référentiel des parlementaires et membres du gouvernement sous la IIIe République",
        description="Documentation de l'API",
        version="0.1.0",
    )

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _app.include_router(api_router)

    return _app


app = create_app()