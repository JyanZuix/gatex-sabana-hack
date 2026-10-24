"""Ningún archivo del repositorio puede llevar la contraseña de la base (regla 10 del README).

Las credenciales van solo en `.env`, que está en `.gitignore`. Esta prueba falla si una
cadena de conexión con contraseña real aparece en cualquier otro archivo de texto.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
EXCLUIDAS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
# usuario:contraseña@…supabase… — se permite el marcador "<contraseña>" del ejemplo
CADENA_CON_CLAVE = re.compile(r"postgres(?:ql)?://[^:\s/]+:(?!<)[^@\s]+@[^\s/]*supabase\.(?:com|co)")


def _archivos():
    """Todo archivo del repo salvo `.env` y sus variantes ignoradas (sí se revisa `.env.example`)."""
    for ruta in RAIZ.rglob("*"):
        partes = set(ruta.relative_to(RAIZ).parts)
        ignorado = ruta.name.startswith(".env") and ruta.name != ".env.example"
        if ruta.is_file() and not partes & EXCLUIDAS and not ignorado and ruta.stat().st_size < 2_000_000:
            yield ruta


def test_env_esta_ignorado_por_git():
    lineas = (RAIZ / ".gitignore").read_text(encoding="utf-8").split()
    assert ".env" in lineas and ".env.*" in lineas and "!.env.example" in lineas


def test_ningun_archivo_tiene_la_contrasena_de_la_base():
    con_clave = []
    for ruta in _archivos():
        try:
            texto = ruta.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if CADENA_CON_CLAVE.search(texto):
            con_clave.append(str(ruta.relative_to(RAIZ)))
    assert con_clave == [], f"Cadena de conexión con contraseña en: {con_clave}. Muévala a .env"


def test_la_regla_detecta_una_clave_real_y_acepta_el_marcador():
    falsa = "postgresql://postgres.abc:" + "MiClave123" + "@aws-0-us-east-1.pooler." + "supabase.com:5432/x"
    assert CADENA_CON_CLAVE.search(falsa)
    assert not CADENA_CON_CLAVE.search("postgresql://postgres.<ref>:<contraseña>@aws-0-<región>.pooler.supabase.com:5432/x")
