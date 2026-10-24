import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export async function cargarModeloTablet(scene, screen, provisional) {
    const {scene:modelo} = await new GLTFLoader().loadAsync(new URL('../assets/Gatex.glb',import.meta.url).href);
    try {
    const anchor=modelo.getObjectByName('AnclajeTablet'), soporte=modelo.getObjectByName('SoporteTablet');
    if(!anchor||!soporte)throw new Error('Falta AnclajeTablet o SoporteTablet.');
    modelo.updateWorldMatrix(true,true);
    const escalaAnchor=anchor.scale.clone();
    if(Math.min(Math.abs(escalaAnchor.x),Math.abs(escalaAnchor.y),Math.abs(escalaAnchor.z))<1e-6)throw new Error('Escala del anclaje no invertible.');

    // Conserva la escala de presentación del soporte de la corrección anterior.
    const altoOriginal=screen.geometry.parameters.height;
    const centroAnterior=.75+altoOriginal*Math.cos(-Math.atan(.16))/2;
    const yAnterior=centroAnterior-Math.sin(Math.atan(.16))*.01505;
    const pieOriginal=new THREE.Box3().setFromObject(soporte,true).min.y;
    const anclajeOriginal=anchor.getWorldPosition(new THREE.Vector3());
    const factor=yAnterior/(anclajeOriginal.y-pieOriginal);
    if(!Number.isFinite(factor)||factor<=0)throw new Error('No se pudo medir el soporte.');

    // Identifica la pieza superior por proximidad al anclaje, entre las mallas reales del soporte.
    const piezas=[];
    soporte.traverse(object=>{if(object.isMesh){
        const box=new THREE.Box3().setFromObject(object,true);
        piezas.push({object,distancia:box.getCenter(new THREE.Vector3()).distanceToSquared(anclajeOriginal)});
    }});
    piezas.sort((a,b)=>a.distancia-b.distancia);
    if(!piezas.length)throw new Error('El soporte no contiene una superficie medible.');
    const superficie=piezas[0].object;

    modelo.scale.multiplyScalar(factor);
    modelo.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),Math.PI/2)); // +90° Z global para base y anclaje.
    scene.add(modelo);modelo.updateWorldMatrix(true,true);
    let cajaBase=new THREE.Box3().setFromObject(soporte,true);
    modelo.position.x-=cajaBase.getCenter(new THREE.Vector3()).x;
    modelo.position.y-=cajaBase.min.y; // Apoya la base ya girada sobre el suelo.
    modelo.updateWorldMatrix(true,true);

    // Extrae la rotación del anclaje sin convertir su escala negativa en un giro adicional.
    const sinEscala=anchor.matrixWorld.clone().multiply(new THREE.Matrix4().makeScale(1/(factor*escalaAnchor.x),1/(factor*escalaAnchor.y),1/(factor*escalaAnchor.z)));
    const orientacion=new THREE.Quaternion().setFromRotationMatrix(sinEscala);
    const inversaRotacion=new THREE.Matrix4().makeRotationFromQuaternion(orientacion.clone().invert());
    const anchoArriba=new THREE.Box3();
    const vertices=superficie.geometry.getAttribute('position');
    for(let i=0;i<vertices.count;i++)anchoArriba.expandByPoint(new THREE.Vector3().fromBufferAttribute(vertices,i).applyMatrix4(superficie.matrixWorld).applyMatrix4(inversaRotacion));
    const dimensiones=anchoArriba.getSize(new THREE.Vector3());
    const ancho=dimensiones.x*1.2; // Ancho de pantalla = 120 % del ancho de la pieza superior, medido en los ejes del anclaje.
    const alto=ancho*1080/1440; // Conserva la proporción 4:3 de la interfaz; no deforma el formulario.
    if(!Number.isFinite(ancho)||ancho<=0)throw new Error('No se pudo determinar el ancho superior.');
    const geometry=new THREE.PlaneGeometry(ancho,alto);
    const normal=new THREE.Vector3(0,0,1).applyQuaternion(orientacion);
    if(normal.z<0){geometry.rotateY(Math.PI);normal.negate();} // Corrige la cara del plano para verla desde el usuario, sin cambiar la rotación del objeto.
    if(Math.abs(normal.z)<.1)throw new Error('El anclaje deja la pantalla de canto al usuario; hay que revisar su orientación en Blender.');
    const ejeX=new THREE.Vector3(1,0,0).applyQuaternion(orientacion);
    const ejeY=new THREE.Vector3(0,1,0).applyQuaternion(orientacion);
    const semialtoY=(Math.abs(ejeX.y)*ancho+Math.abs(ejeY.y)*alto)/2;
    const centro=new THREE.Vector3(0,.75+semialtoY,-1.35); // Borde inferior a 75 cm incluso si el anclaje gira el plano en diagonal.

    // Separa TODO el soporte del plano: su vértice más cercano queda 15 mm detrás de la pantalla.
    let maxFrente=-Infinity;
    soporte.traverse(object=>{if(object.isMesh){
        const positions=object.geometry.getAttribute('position');
        for(let i=0;i<positions.count;i++)maxFrente=Math.max(maxFrente,new THREE.Vector3().fromBufferAttribute(positions,i).applyMatrix4(object.matrixWorld).dot(normal));
    }});
    const trasladoZ=(centro.dot(normal)-.015-maxFrente)/normal.z;
    modelo.position.z+=trasladoZ;modelo.updateWorldMatrix(true,true);

    const mount=new THREE.Group();mount.name='PantallaInteractivaGatex';
    const pose=new THREE.Matrix4().compose(centro,orientacion,new THREE.Vector3(1,1,1));
    mount.matrix.copy(anchor.matrixWorld).invert().multiply(pose);mount.matrixAutoUpdate=false;
    anchor.add(mount);mount.add(screen);
    screen.geometry.dispose();screen.geometry=geometry;
    screen.position.set(0,0,0);screen.quaternion.identity();screen.scale.set(1,1,1);
    modelo.updateWorldMatrix(true,true);provisional.visible=false;
    console.info('Gatex: pantalla anclada',{superficie:superficie.name,ancho,alto,bordeInferior:.75,giroZ:90,separacion:.015});
    return {modelo,anchor,mount};
    } catch(error) { modelo.removeFromParent(); throw error; } // Evita duplicar el modelo y la vista provisional si falla la carga.
}

