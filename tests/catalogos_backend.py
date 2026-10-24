import importlib.util
import sys
from datetime import date
from types import SimpleNamespace as N
from pathlib import Path
root = Path(__file__).resolve().parents[1]
if not (root / 'backend' / 'dominio.py').exists():
    raise SystemExit('Aplica primero los archivos al proyecto completo para probar el backend.')
sys.path.insert(0, str(root))
p = str(root / 'backend' / 'api' / 'catalogos.py')
spec=importlib.util.spec_from_file_location('catalogos_prueba',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Repo:
    def proveedores(self): return [N(proveedor_id='ID-B',nombre='Proveedor B',estado='activo')]
    def cobertura(self): return [N(proveedor_id='ID-B',ruta_id='R-1'),N(proveedor_id='FANTASMA',ruta_id='R-3')]
    def rutas(self): return [N(ruta_id='R-1',origen_id='A',destino_id='B'),N(ruta_id='R-2',origen_id='A',destino_id='C'),N(ruta_id='R-3',origen_id='C',destino_id='B')]
    def ubicaciones(self): return [N(ubicacion_id=i,nombre='Ciudad '+i) for i in ['A','B','C']]
    def clientes(self): return [N(cliente_id='CLIENTE-REAL',nombre='Cliente registrado')]
    def tipos_vehiculo(self): return [N(tipo_vehiculo_id='VEH-XYZ',nombre='Vehículo real')]
r=m.construir_catalogos(Repo(),'A',date(2026,11,3))
assert r['destinos']==[{'id':'B','nombre':'Ciudad B'}]
assert len(r['rutas'])==1
assert r['clientes'][0]['id']=='CLIENTE-REAL'
assert r['tipos_vehiculo'][0]['id']=='VEH-XYZ'
assert r['tipos_carga'][0]['id'] is None
assert m.construir_catalogos(Repo(),'C')['destinos']==[]
assert r['fecha_servicio']=='2026-11-03'
print('PASS: catálogos desde repositorio, IDs reales, rutas cubiertas, origen dirigido, general=null y fechas. Prueba sin servidor HTTP.')

