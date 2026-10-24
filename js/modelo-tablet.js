import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export async function cargarModeloTablet(scene, screen, provisional) {
    const {scene:modelo} = await new GLTFLoader().loadAsync(new URL('../assets/Gatex.glb', import.meta.url).href);
    const anchor = modelo.getObjectByName('AnclajeTablet'); // Nombre comprobado en el GLB proporcionado.
    if (!anchor) throw new Error('No existe AnclajeTablet; se mantiene la tablet provisional.');
    const scale = anchor.scale.clone();
    if (Math.min(Math.abs(scale.x),Math.abs(scale.y),Math.abs(scale.z)) < 1e-6) throw new Error('El anclaje tiene escala cero.');
    anchor.updateWorldMatrix(true,false);
    const basis = new THREE.Matrix4().makeBasis(new THREE.Vector3(0,0,1),new THREE.Vector3(1,0,0),new THREE.Vector3(0,1,0));
    const unscaled = anchor.matrixWorld.clone().multiply(new THREE.Matrix4().makeScale(1/scale.x,1/scale.y,1/scale.z));
    const initialFrame = new THREE.Quaternion().setFromRotationMatrix(unscaled.multiply(basis));
    const desiredFrame = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),-Math.atan(.16));
    modelo.quaternion.premultiply(desiredFrame.multiply(initialFrame.invert())); // Corrige también el giro: texto hacia arriba y normal hacia el usuario.
    const factor = .43; modelo.scale.multiplyScalar(factor); scene.add(modelo);
    modelo.updateWorldMatrix(true,true);
    modelo.position.add(new THREE.Vector3(0,1.48,-1.35).sub(anchor.getWorldPosition(new THREE.Vector3())));
    modelo.updateWorldMatrix(true,true); // Lleva el anclaje al frente del usuario junto al resto del modelo.
    const mount = new THREE.Group(); mount.name = 'PantallaInteractivaGatex';
    mount.matrix.makeScale(1/scale.x,1/scale.y,1/scale.z)
        .multiply(new THREE.Matrix4().makeTranslation(0,.035,0))
        .multiply(basis).multiply(new THREE.Matrix4().makeScale(1/factor,1/factor,1/factor));
    mount.matrixAutoUpdate = false; // Compensa la escala inicial negativa; sigue heredando cambios posteriores.
    anchor.add(mount); mount.add(screen);
    screen.position.set(0,0,0); screen.quaternion.identity(); screen.scale.set(1,1,1);
    provisional.visible = false; modelo.updateWorldMatrix(true,true); // Oculta la carcasa provisional al terminar la carga.
    return {modelo,anchor,mount};
}

