import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const activos = new WeakMap(); // Mantiene como máximo un escenario gestionado por escena.
export async function cargarEscenario(scene, loader = new GLTFLoader()) {
    const archivo = new URL('../assets/Gatex1.glb', import.meta.url);
    const gltf = await loader.loadAsync(archivo.href);
    const nuevo = gltf.scene;
    if (!nuevo) throw new Error('Gatex1.glb no contiene una escena principal.');
    const prohibidos=[];
    nuevo.traverse(object=>{if(/^(SoporteTablet|AnclajeTablet)(\.\d+)?$/i.test(object.name||''))prohibidos.push(object.name);});
    if(prohibidos.length)throw new Error('El escenario contiene '+prohibidos.join(', ')+'. Hace falta tu confirmación antes de mostrar esos objetos.');
    const anterior = activos.get(scene);
    if(anterior)scene.remove(anterior);
    scene.add(nuevo); activos.set(scene,nuevo); // Sin cambiar transformaciones, materiales, nombres ni jerarquía del GLB.
    return nuevo;
}
