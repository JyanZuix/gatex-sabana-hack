import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { identificarCono } from './referencia-cono.mjs';

const activos=new WeakMap();
export async function cargarEscenario(scene,loader=new GLTFLoader()) {
    const {scene:nuevo}=await loader.loadAsync(new URL('../assets/Gatex2.glb',import.meta.url).href);
    if(!nuevo)throw new Error('Gatex2.glb no contiene una escena principal.');
    const usuarios=[],prohibidos=[];
    nuevo.traverse(object=>{
        if(object.name==='Usuario')usuarios.push(object);
        if(/^(SoporteTablet|AnclajeTablet)(\.\d+)?$/i.test(object.name||''))prohibidos.push(object.name);
    });
    if(prohibidos.length)throw new Error('El modelo contiene '+prohibidos.join(', ')+'. Se necesita confirmación antes de mostrarlos.');
    if(usuarios.length!==1)throw new Error('Debe existir exactamente un objeto llamado Usuario; encontrados: '+usuarios.length);
    const usuario=usuarios[0];nuevo.updateWorldMatrix(true,true);
    const inversaUsuario=usuario.matrixWorld.clone().invert(),vertices=[];
    usuario.traverse(object=>{if(object.isMesh){
        const positions=object.geometry.getAttribute('position');
        for(let i=0;i<positions.count;i++) {
            const p=new THREE.Vector3().fromBufferAttribute(positions,i).applyMatrix4(object.matrixWorld).applyMatrix4(inversaUsuario);
            vertices.push([p.x,p.y,p.z]);
        }
    }});
    const cono=identificarCono(vertices);
    const punta=new THREE.Vector3(...cono.punta).applyMatrix4(usuario.matrixWorld);
    const base=new THREE.Vector3(...cono.base).applyMatrix4(usuario.matrixWorld);
    const direccion=punta.clone().sub(base).normalize();
    const position=punta.clone().addScaledVector(direccion,.01); // Un centímetro después de la punta, en su misma dirección.
    const up=Math.abs(direccion.dot(new THREE.Vector3(0,1,0)))>.999?new THREE.Vector3(0,0,1):new THREE.Vector3(0,1,0);
    const orientation=new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().lookAt(position,position.clone().add(direccion),up));
    usuario.visible=false; // Único cambio de visualización autorizado: el marcador no aparece durante el uso.
    const anterior=activos.get(scene);if(anterior)scene.remove(anterior);
    scene.add(nuevo);activos.set(scene,nuevo); // No desplaza, gira, escala ni recolorea el escenario.
    console.info('Punto de entrada Usuario',{punta:punta.toArray(),base:base.toArray(),posicion:position.toArray(),direccion:direccion.toArray()});
    return {modelo:nuevo,entrada:{position,orientation},referencia:{punta,base,direccion}};
}
