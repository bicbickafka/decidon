# -*- coding: utf-8 -*-
"""
main.py
Entry point for the FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import api_router
from app.api_meta import METADATA
from fastapi.openapi.utils import get_openapi



def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    :return: FastAPI application
    :rtype: FastAPI
    """
    _app = FastAPI(
        title=METADATA["title"],
        description=METADATA["description"],
        version=METADATA["version"],
        openapi_url=METADATA["openapi_url"],
        docs_url=METADATA["docs_url"],
        redoc_url=METADATA["redoc_url"],
        license_info=METADATA.get("license_info"),
        openapi_tags=METADATA.get("openapi_tags"),
        swagger_ui_parameters=METADATA.get("swagger_ui_parameters"),
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
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
