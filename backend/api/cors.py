"""CORS para la API publicada, incluidas las respuestas de errores internos."""
from __future__ import annotations

import os
from urllib.parse import urlsplit


def normalizar_origenes(valor: str) -> list[str]:
    """Un origen es esquema + host + puerto: nunca una ruta del frontend."""
    entradas = [parte.strip() for parte in valor.split(",") if parte.strip()]
    if not entradas:
        raise ValueError("CORS_ORIGENES está vacío. Define los orígenes HTTPS del frontend.")
    if "*" in entradas:
        if len(entradas) != 1:
            raise ValueError("CORS_ORIGENES: usa * solo o una lista de orígenes explícitos.")
        return ["*"]
    origenes = []
    for entrada in entradas:
        url = urlsplit(entrada)
        if (url.scheme not in ("http", "https") or not url.hostname
                or url.username is not None or url.password is not None
                or url.path not in ("", "/") or url.query or url.fragment):
            raise ValueError("CORS_ORIGENES debe contener orígenes como https://sitio.netlify.app, sin rutas ni credenciales.")
        try:
            puerto = url.port
        except ValueError as exc:
            raise ValueError("Puerto inválido en CORS_ORIGENES.") from exc
        host = url.hostname.lower()
        if ":" in host:
            host = f"[{host}]"
        predeterminado = 443 if url.scheme == "https" else 80
        origen = f"{url.scheme}://{host}" + (f":{puerto}" if puerto is not None and puerto != predeterminado else "")
        if origen not in origenes:
            origenes.append(origen)
    return origenes


def envolver_cors(app, valor: str | None = None):
    # Importación diferida para probar la configuración sin las dependencias del servidor.
    from starlette.middleware.cors import CORSMiddleware

    origenes = normalizar_origenes(os.environ.get("CORS_ORIGENES", "*") if valor is None else valor)
    # La envoltura EXTERNA incluye también las respuestas 500 de ServerErrorMiddleware.
    return CORSMiddleware(
        app=app,
        allow_origins=origenes,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,  # El frontend actual no utiliza cookies entre sitios.
        max_age=600,
    )
