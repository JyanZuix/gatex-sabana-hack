import importlib.util
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gatex_cors', RAIZ / 'backend/api/cors.py')
cors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cors)


class ConfiguracionCORS(unittest.TestCase):
    def test_origen_netlify_sin_barra(self):
        self.assertEqual(cors.normalizar_origenes(' https://shimmering-mousse-135327.netlify.app/ '), ['https://shimmering-mousse-135327.netlify.app'])

    def test_varios_origenes_y_puertos(self):
        self.assertEqual(cors.normalizar_origenes('https://sitio.netlify.app:443,http://localhost:8080,https://sitio.netlify.app'), ['https://sitio.netlify.app', 'http://localhost:8080'])

    def test_configuracion_invalida(self):
        for valor in ['', 'null', 'https://sitio.netlify.app/ruta', 'https://usuario:clave@sitio.netlify.app', '*,https://sitio.netlify.app', 'https://sitio.netlify.app?x=1', 'http://localhost:xyz']:
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                cors.normalizar_origenes(valor)

    def test_asterisco_existente_se_conserva(self):
        self.assertEqual(cors.normalizar_origenes('*'), ['*'])

    def test_envoltura_global(self):
        fuente = (RAIZ / 'backend/api/app.py').read_text(encoding='utf-8-sig')
        self.assertIn('app = envolver_cors(crear_app())', fuente)
        self.assertNotIn('app.add_middleware(CORSMiddleware', fuente)


DEPENDENCIAS = all(importlib.util.find_spec(m) for m in ['fastapi', 'httpx'])


@unittest.skipUnless(DEPENDENCIAS, 'Requiere dependencias del backend: fastapi y httpx')
class RespuestasCORS(unittest.TestCase):
    def setUp(self):
        from fastapi import FastAPI, HTTPException
        from fastapi.testclient import TestClient
        app = FastAPI()

        @app.get('/salud')
        def salud():
            return {'estado': 'ok'}

        @app.get('/error/{codigo}')
        def error(codigo: int):
            if codigo == 500:
                raise RuntimeError('Fallo interno simulado, sin acceder a la base')
            raise HTTPException(status_code=codigo, detail='Error de prueba')

        self.origen = 'https://shimmering-mousse-135327.netlify.app'
        self.client = TestClient(cors.envolver_cors(app, self.origen), raise_server_exceptions=False)

    def test_get_legible_desde_netlify(self):
        r = self.client.get('/salud', headers={'Origin': self.origen})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers['access-control-allow-origin'], self.origen)
        self.assertNotIn('access-control-allow-credentials', r.headers)

    def test_preflight_json_sin_ejecutar_evaluacion(self):
        r = self.client.options('/solicitudes/evaluar', headers={'Origin': self.origen, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers['access-control-allow-origin'], self.origen)
        self.assertIn('POST', r.headers['access-control-allow-methods'])
        self.assertIn('content-type', r.headers['access-control-allow-headers'].lower())

    def test_errores_tambien_tienen_cors(self):
        for codigo in [404, 422, 503, 500]:
            with self.subTest(codigo=codigo):
                r = self.client.get(f'/error/{codigo}', headers={'Origin': self.origen})
                self.assertEqual(r.status_code, codigo)
                self.assertEqual(r.headers['access-control-allow-origin'], self.origen)

    def test_origen_no_autorizado(self):
        r = self.client.options('/solicitudes/evaluar', headers={'Origin': 'https://otro.invalid', 'Access-Control-Request-Method': 'POST'})
        self.assertEqual(r.status_code, 400)
        self.assertNotIn('access-control-allow-origin', r.headers)


if __name__ == '__main__':
    unittest.main(verbosity=2)
