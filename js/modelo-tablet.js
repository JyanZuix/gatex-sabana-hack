import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export async function cargarModeloTablet(scene, screen, provisional) {
    const {scene:modelo} = await new GLTFLoader().loadAsync(new URL('../assets/Gatex.glb', import.meta.url).href);
    const anchor = modelo.getObjectByName('AnclajeTablet');
    const soporte = modelo.getObjectByName('SoporteTablet'); // Se conserva la orientación vertical original del GLB.
    if (!anchor || !soporte) throw new Error('Falta AnclajeTablet o SoporteTablet; se mantiene la vista provisional.');
    modelo.updateWorldMatrix(true,true);
    if (Math.abs(anchor.matrixWorld.determinant()) < 1e-10) throw new Error('El anclaje tiene una transformación no invertible.');

    const bordeInferior = .75; // Altura confirmada por el usuario, en metros desde el piso.
    const inclinacion = -Math.atan(.16); // Conserva la orientación de pantalla de la versión anterior.
    const pantallaAlto = screen.geometry.parameters.height;
    const centroY = bordeInferior + pantallaAlto * Math.cos(inclinacion) / 2;
    const posicionPantalla = new THREE.Vector3(0,centroY,-1.35); // Conserva el centrado horizontal y la distancia al usuario.
    const orientacionPantalla = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),inclinacion);

    const normalPantalla = new THREE.Vector3(0,0,1).applyQuaternion(orientacionPantalla);
    const posicionSoporte = posicionPantalla.clone().addScaledVector(normalPantalla,-.01505); // Separa la pantalla del soporte unos 15 mm.

    // Se mide solo el soporte: Tarjeta1 es otro objeto de la escena y no define el piso.
    const pieY = new THREE.Box3().setFromObject(soporte,true).min.y;
    const posicionAnclaje = anchor.getWorldPosition(new THREE.Vector3());
    const altoHastaAnclaje = posicionAnclaje.y-pieY;
    if (!Number.isFinite(altoHastaAnclaje) || altoHastaAnclaje <= 0) throw new Error('No se pudo determinar la altura del soporte.');
    const factor = posicionSoporte.y / altoHastaAnclaje; // Ajusta el soporte para apoyar su pie en el suelo, sin escalar la pantalla.
    modelo.scale.multiplyScalar(factor);
    scene.add(modelo); modelo.updateWorldMatrix(true,true);
    modelo.position.add(posicionSoporte.clone().sub(anchor.getWorldPosition(new THREE.Vector3())));
    modelo.updateWorldMatrix(true,true); // No se gira el conjunto: el piso y la parte superior mantienen su orientación original.

    const mount = new THREE.Group(); mount.name='PantallaInteractivaGatex';
    const posePantalla = new THREE.Matrix4().compose(posicionPantalla,orientacionPantalla,new THREE.Vector3(1,1,1));
    mount.matrix.copy(anchor.matrixWorld).invert().multiply(posePantalla);
    mount.matrixAutoUpdate=false; // Compensa escala y rotación iniciales; sigue heredando cambios posteriores del anclaje.
    anchor.add(mount); mount.add(screen);
    screen.position.set(0,0,0); screen.quaternion.identity(); screen.scale.set(1,1,1);
    modelo.updateWorldMatrix(true,true);
    provisional.visible=false; // Oculta la versión provisional solo después de completar la integración.
    return {modelo,anchor,mount};
}

