// Apariencia de las tarjetas del GLB según su estado. No cambia el modelo en disco: clona los
// materiales de cada tarjeta (el GLB los comparte) y agrega insignias como hijas de la tarjeta.
import * as THREE from 'three';

const AMBAR_CLARO=new THREE.Color('#fbbf24'),AMBAR_OSCURO=new THREE.Color('#b45309');
const VERDE_CLARO=new THREE.Color('#86efac'),VERDE_OSCURO=new THREE.Color('#15803d');
const BRILLO_AZUL=new THREE.Color('#3b82f6'),BRILLO_AMBAR=new THREE.Color('#f59e0b'),SELECCION=new THREE.Color('#175cde');

function crearInsignia(texto,fondo,icono) {
    const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=256;const g=canvas.getContext('2d');
    g.fillStyle=fondo;g.beginPath();g.roundRect(8,8,1008,240,60);g.fill();g.strokeStyle='#ffffff';g.lineWidth=10;g.stroke();
    let x=60;
    if(icono==='alerta'){ // Triángulo de advertencia dibujado: no depende de que la fuente tenga el símbolo.
        g.fillStyle='#ffffff';g.beginPath();g.moveTo(140,36);g.lineTo(236,212);g.lineTo(44,212);g.closePath();g.fill();
        g.fillStyle=fondo;g.fillRect(130,92,20,66);g.fillRect(130,172,20,20);x=270;
    } else if(icono==='ok'){g.strokeStyle='#ffffff';g.lineWidth=30;g.lineCap='round';g.lineJoin='round';g.beginPath();g.moveTo(66,132);g.lineTo(122,188);g.lineTo(216,72);g.stroke();x=256;}
    g.fillStyle='#ffffff';g.textAlign='left';g.textBaseline='middle';let size=118;g.font=`800 ${size}px system-ui,sans-serif`;
    while(g.measureText(texto).width>1024-x-48&&size>40){size-=6;g.font=`800 ${size}px system-ui,sans-serif`;}
    g.fillText(texto,x,134);
    const textura=new THREE.CanvasTexture(canvas);textura.colorSpace=THREE.SRGBColorSpace;
    const malla=new THREE.Mesh(new THREE.PlaneGeometry(1,.25),new THREE.MeshBasicMaterial({map:textura,transparent:true,side:THREE.DoubleSide}));
    malla.visible=false;
    malla.raycast=function(raycaster,intersects){if(this.visible)THREE.Mesh.prototype.raycast.call(this,raycaster,intersects);}; // Oculta no intercepta el rayo.
    return malla;
}

// mirarHacia: punto desde el que se ven las tarjetas (el punto de entrada Usuario); las insignias lo miran.
export function crearAparienciaTarjetas({mirarHacia}) {
    const datos=new WeakMap();
    return {
        preparar(node) {
            node.updateWorldMatrix(true,true);
            const fondos=[];
            node.traverse(o=>{
                if(!o.isMesh)return;
                const lista=Array.isArray(o.material)?o.material:[o.material],clones=lista.map(m=>m.clone());
                o.material=Array.isArray(o.material)?clones:clones[0];
                for(const m of clones){
                    if(!m.color||!m.emissive||m.metalness>=.99)continue; // Material por defecto del GLB: se ve negro, no se tiñe.
                    const luz=m.color.r*.2126+m.color.g*.7152+m.color.b*.0722;
                    if(luz<.01)continue;                                    // Texto negro: siempre legible.
                    fondos.push({m,color:m.color.clone(),emissive:m.emissive.clone(),intensidad:m.emissiveIntensity,claro:luz>.3});
                }
            });
            const caja=new THREE.Box3().setFromObject(node),tam=caja.getSize(new THREE.Vector3()),centro=caja.getCenter(new THREE.Vector3());
            // Casi del ancho de la tarjeta, sobre el ícono superior y un poco por delante: el nombre sigue visible.
            const ancho=.9*Math.max(tam.x,tam.z),escala=node.getWorldScale(new THREE.Vector3()).x||1;
            const posicion=new THREE.Vector3(centro.x,caja.max.y-tam.y*.22,centro.z);
            posicion.addScaledVector(mirarHacia.clone().sub(posicion).normalize(),.12);
            const insignias={descartado:crearInsignia('NO ELEGIBLE','#b45309','alerta'),elegida:crearInsignia('ELEGIDO POR EL FUNCIONARIO','#15803d','ok')};
            for(const insignia of Object.values(insignias)){
                node.add(insignia);insignia.position.copy(node.worldToLocal(posicion.clone()));
                insignia.scale.set(ancho/escala,ancho/escala,1);insignia.lookAt(mirarHacia);
            }
            datos.set(node,{fondos,insignias,escala:node.scale.clone()});
        },
        aplicar(node,{estado,hover,seleccionada,elegida}) {
            const d=datos.get(node);if(!d)return;
            const descartado=estado==='cancelado'||estado==='casi';
            for(const f of d.fondos){
                f.m.color.copy(f.color);
                if(descartado)f.m.color.lerp(f.claro?AMBAR_CLARO:AMBAR_OSCURO,.7);
                else if(elegida)f.m.color.lerp(f.claro?VERDE_CLARO:VERDE_OSCURO,.7);
                const brillo=seleccionada?SELECCION:hover?(descartado?BRILLO_AMBAR:BRILLO_AZUL):null;
                if(brillo){f.m.emissive.copy(brillo);f.m.emissiveIntensity=seleccionada?.6:.4;}
                else {f.m.emissive.copy(f.emissive);f.m.emissiveIntensity=f.intensidad;}
            }
            node.scale.copy(d.escala).multiplyScalar(seleccionada?1.07:hover?1.04:1);
            d.insignias.descartado.visible=descartado;
            d.insignias.elegida.visible=!!elegida&&!descartado;
        }
    };
}
