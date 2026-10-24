import * as THREE from 'three';
import { EntradaVR } from './entrada-vr.mjs';
const entradaVR = new EntradaVR();
let puntoEntrada = null;
import { XRControllerModelFactory } from 'three/addons/webxr/XRControllerModelFactory.js';
import { API } from './api.mjs';
import { TabletOperaciones } from './tablet-ui.mjs';
import { AnimadorTarjetas } from './tarjetas.mjs';
import { POLITICA_CASI, RESTABLECER_TARJETAS } from './config.js';
import { cargarEscenario } from './escenario.js'; // El escenario es independiente de la tablet.
window.GatexDiagnostico?.registrar('Módulos de aplicación cargados; preparando Three.js…');

const inicio = document.getElementById('inicio'); // Pantalla 1: una única acción de entrada.
const entrar = document.getElementById('entrar');
const estado = document.getElementById('estado');
const preview = new URLSearchParams(location.search).has('preview'); // Prueba de escritorio explícita; no simula soporte WebXR.
const scene = new THREE.Scene();
const fondo = document.createElement('canvas'); fondo.width=256; fondo.height=128;
const fondoCtx = fondo.getContext('2d');
const degradado=fondoCtx.createLinearGradient(0,0,0,128);
degradado.addColorStop(0,'#e9edf2');degradado.addColorStop(.48,'#e9edf2');
degradado.addColorStop(.62,'#102a4c');degradado.addColorStop(1,'#102a4c');
fondoCtx.fillStyle=degradado;fondoCtx.fillRect(0,0,256,128);
const fondoTexture=new THREE.CanvasTexture(fondo);
fondoTexture.mapping=THREE.EquirectangularReflectionMapping;fondoTexture.colorSpace=THREE.SRGBColorSpace;
scene.background=fondoTexture; // Azul oscuro abajo y gris claro arriba, sin editar materiales del GLB.
scene.fog = null; // Sin niebla: las tarjetas y los objetos lejanos conservan su visibilidad.
const camera = new THREE.PerspectiveCamera(65, innerWidth / innerHeight, .05, 60);
camera.position.set(0, 1.5, 0); // WebXR sustituye esta pose por la del visor.
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5)); // Limita el coste de la vista convencional.
renderer.setSize(innerWidth, innerHeight);
renderer.xr.enabled = true;
renderer.xr.setReferenceSpaceType('local-floor'); // Sitúa el suelo en el suelo físico del área de juego.
document.body.appendChild(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff, 0xa1aabb, 2.4));
const light = new THREE.DirectionalLight(0xffffff, 2);
light.position.set(2, 6, 3); scene.add(light);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshStandardMaterial({color:'#102a4c', roughness:1}));
floor.rotation.x = -Math.PI / 2; scene.add(floor);
const grid = new THREE.GridHelper(30, 30, '#34567d', '#244363');
grid.position.y = .002; scene.add(grid); // Referencia espacial sin modelos ni texturas pesadas.

const tablet = new THREE.Group();
tablet.position.set(0, 1.5, -1.35); scene.add(tablet); // Centro a la altura de la vista inicial, a 1.35 m de distancia.
let centrarAlEntrar = false;
function centrarTablet(posicion, orientacion) {
    const frente=new THREE.Vector3(0,0,-1).applyQuaternion(orientacion).normalize();
    tablet.position.copy(posicion).addScaledVector(frente,1.35); // Centrada en la mirada completa del punto de entrada, incluida la inclinación.
    tablet.lookAt(posicion); // Reinicia la orientación usando la vista del cono en cada centrado.
    tablet.rotateX(-Math.PI / 4); // Atril a 45° respecto a esa vista: borde superior más lejos y pantalla hacia arriba.
    tablet.scale.setScalar(1.3); // Aumenta marco y pantalla un 30 %, sin acumular escala al volver a entrar.
    tablet.position.y -= 1; // Baja exactamente 1 metro en el eje vertical del mundo, conservando su orientación.
}
function restablecerVistaPC() {
    if(!puntoEntrada)return;
    camera.position.copy(puntoEntrada.position);camera.quaternion.copy(puntoEntrada.orientation);
    camera.updateMatrixWorld(true);centrarTablet(camera.position,camera.quaternion);
}
const shell = new THREE.Mesh(new THREE.BoxGeometry(1.2, .9, .04), new THREE.MeshStandardMaterial({color:'#26344c', roughness:.5}));
tablet.add(shell); // Marco definitivo sencillo, sin soporte ni anclajes externos.
const canvas = document.createElement('canvas'); canvas.width = 1440; canvas.height = 1080;
const ctx = canvas.getContext('2d');
const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace;
const screen = new THREE.Mesh(new THREE.PlaneGeometry(1.15, .8625), new THREE.MeshBasicMaterial({map:texture}));
screen.position.z = .022; tablet.add(screen); // Pantalla interactiva independiente de la carcasa.

let animador=null;
let xrSession=null,starting=false; // Estado compartido por el botón de entrada y la salida de VR.
const raycaster=new THREE.Raycaster(),rotation=new THREE.Matrix4();
const controllers=[],selecting=new Set();
const ui=new TabletOperaciones({canvas,api:new API(),onDirty:()=>{texture.needsUpdate=true;},politicaCasi:POLITICA_CASI,
    onResultados:(evaluacion,vinculos,politica)=>{if(!animador)throw new Error('No se cargaron las tarjetas.');animador.aplicar(evaluacion,vinculos,politica);},
    onNuevaConsulta:()=>{if(RESTABLECER_TARJETAS!=='original')throw new Error('Falta confirmar la distribución de regreso de las tarjetas.');animador?.restaurar();}
});
ui.onSalir=()=>exitVR();
function draw(){ui.draw();}
function resetForm(){ui.nuevaConsulta();}
function objetosInteractivos(){return [screen,...(animador?.seleccionables()||[])];}
function idImpacto(hit){if(!hit)return null;if(hit.object===screen){const z=ui.hit(hit.uv);return z?.id==='dismiss'?null:z?.id;}if(ui.menu.isOpen)return null;const item=animador?.desdeObjeto(hit.object);return item?.estado==='candidato'?'card-'+item.node.name:null;}
function activarImpacto(hit){if(ui.menu.isOpen&&hit?.object!==screen){ui.activate(undefined);return;}if(!hit||hit.object===screen){ui.activate(hit?.uv);return;}const item=animador?.desdeObjeto(hit.object);if(item?.estado==='candidato')ui.seleccionarProveedor(item.proveedor_id);}
function controllerHit(controller) {
    controller.updateWorldMatrix(true,false); rotation.identity().extractRotation(controller.matrixWorld);
    raycaster.ray.origin.setFromMatrixPosition(controller.matrixWorld);
    raycaster.ray.direction.set(0,0,-1).applyMatrix4(rotation);
    screen.updateWorldMatrix(true,false);return raycaster.intersectObjects(objetosInteractivos(),true)[0];
}
const factory = new XRControllerModelFactory();
for(let i=0;i<2;i++) {
    const controller=renderer.xr.getController(i);
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3(0,0,-1)]),new THREE.LineBasicMaterial({color:'#175cde'}));
    line.scale.z=3; controller.add(line); scene.add(controller); controllers.push({controller,line});
    controller.addEventListener('selectstart',()=>{
        if(selecting.has(controller))return; selecting.add(controller); // Evita repetición al mantener presionado el gatillo.
        const hit=controllerHit(controller); activarImpacto(hit);
    });
    controller.addEventListener('selectend',()=>selecting.delete(controller));
    controller.addEventListener('disconnected',()=>selecting.delete(controller));
    const grip=renderer.xr.getControllerGrip(i);grip.add(factory.createControllerModel(grip));scene.add(grip);
} // Interacción de esta versión: apuntar con cualquiera de los mandos y pulsar el gatillo. No requiere manos.
function impactoPuntero(event){
    const rect=renderer.domElement.getBoundingClientRect();
    raycaster.setFromCamera(new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1),camera);
    scene.updateMatrixWorld(true);return raycaster.intersectObjects(objetosInteractivos(),true)[0];
}
renderer.domElement.addEventListener('pointerdown',event=>{if(preview&&!renderer.xr.isPresenting&&inicio.hidden)activarImpacto(impactoPuntero(event));});
renderer.domElement.addEventListener('pointermove',event=>{if(!preview||renderer.xr.isPresenting||!inicio.hidden)return;const id=idImpacto(impactoPuntero(event));renderer.domElement.style.cursor=id?'pointer':'default';ui.setHover(id?[id]:[]);});
renderer.domElement.addEventListener('pointerleave',()=>ui.setHover([]));
renderer.domElement.addEventListener('wheel',event=>{if(preview&&inicio.hidden&&ui.menu.isOpen){event.preventDefault();ui.scroll(event.deltaY);}},{passive:false});
window.addEventListener('keydown',event=>{if(preview&&inicio.hidden)ui.key(event);});
async function exitVR() {
    if(xrSession) {try{await xrSession.end();}catch(error){console.error(error);}}
    else {resetForm();inicio.hidden=false;document.getElementById('aviso').hidden=true;entrar.focus();}
}
function registrarEntrada(mensaje){window.GatexDiagnostico?.registrar(mensaje);}
function marcarEntradaLista(){if(window.GatexDiagnostico)window.GatexDiagnostico.appLista=true;}
entrar.addEventListener('click',async()=>{
    registrarEntrada('Controlador del botón ejecutado');
    if(starting)return;
    if(preview) {inicio.hidden=true;document.getElementById('aviso').hidden=false;draw();return;}
    starting=true;entrar.disabled=true;estado.textContent='Solicitando acceso a VR…';
    registrarEntrada('Solicitando immersive-vr · gesto activo: '+(navigator.userActivation?.isActive??'sin dato'));
    let session;
    try {
        session=await navigator.xr.requestSession('immersive-vr',{requiredFeatures:['local-floor']}); // Solicitud dentro del clic: conserva la activación del usuario.
        xrSession=session;registrarEntrada('WebXR aceptó la sesión; configurando el visor…');
        session.addEventListener('end',()=>{
            xrSession=null;entradaVR.reset();centrarAlEntrar=false;restablecerVistaPC();selecting.clear();resetForm();inicio.hidden=false;entrar.disabled=false;
            marcarEntradaLista();registrarEntrada('Sesión terminada; puede volver a entrar');
            estado.textContent='Sesión terminada. Puedes volver a entrar.';entrar.focus();
        },{once:true});
        estado.textContent='Preparando la sesión VR…';
        await renderer.xr.setSession(session);entradaVR.iniciar(renderer.xr.getReferenceSpace());centrarAlEntrar=true;registrarEntrada('Sesión VR iniciada');inicio.hidden=true;draw(); // Entrada directa a la sección 2.
    } catch(error) {
        console.error(error);if(session)await session.end().catch(()=>{});xrSession=null;
        inicio.hidden=false;
        estado.textContent='No se pudo entrar en VR: '+(error.message||error.name||'error desconocido')+'. Revisa los permisos de Meta Quest Browser e inténtalo otra vez.';
        registrarEntrada('ERROR de entrada: '+(error.name||'Error')+' · '+(error.message||error));
    } finally {starting=false;entrar.disabled=false;}
});
async function initialize() {
    draw();
    // Se espera el marcador Usuario antes de fijar la vista y centrar la tablet.
    estado.textContent='Cargando el nuevo escenario…';registrarEntrada('Descargando Gatex5.glb…');
    try {
        const resultado=await cargarEscenario(scene);
        registrarEntrada('Escenario cargado; comprobando las doce tarjetas…');
        animador=new AnimadorTarjetas(resultado.modelo);
        puntoEntrada=resultado.entrada;entradaVR.configurar(puntoEntrada);restablecerVistaPC();
    } catch(error) {
        console.error('No se pudo cargar Gatex5.glb:',error);
        estado.textContent='No se pudo cargar assets/Gatex5.glb. Comprueba que copiaste el archivo y sirve la página por HTTP/HTTPS. Detalle: '+error.message;
        registrarEntrada('ERROR de escenario: '+error.message);
        entrar.disabled=true;return; // Error explícito: no carga otro modelo ni permite entrar fingiendo que terminó.
    }
    ui.conectar(); // Catálogos reales; un fallo se informa dentro de la tablet y no simula datos.
    if(preview){marcarEntradaLista();registrarEntrada('Vista de prueba PC lista');entrar.textContent='Abrir prueba en PC';entrar.disabled=false;estado.textContent='Modo de desarrollo. Esta vista no verifica el funcionamiento del visor.';return;}
    if(location.protocol==='file:'||!isSecureContext){estado.textContent='Para usar VR abre esta página desde una dirección HTTPS válida en Meta Quest Browser. No abras index.html con doble clic.';return;}
    try {
        registrarEntrada('Comprobando compatibilidad WebXR…');
        if(!navigator.xr||!await navigator.xr.isSessionSupported('immersive-vr')) {
            estado.textContent='Este dispositivo o navegador no admite VR inmersiva. Abre esta dirección en Meta Quest Browser.';
            window.alert(estado.textContent);return;
        }
        marcarEntradaLista();registrarEntrada('Aplicación lista para VR · botón habilitado');
        estado.textContent='Escenario listo. Pulsa Entrar a VR.';entrar.disabled=false;
    } catch(error){console.error(error);estado.textContent='No se pudo comprobar WebXR. Revisa los permisos y abre la página directamente, fuera de una vista previa incrustada.';}
}
window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
renderer.setAnimationLoop((tiempo,frame)=>{
    const entradaAplicada=entradaVR.actualizar(frame,renderer.xr); // Una vez por sesión: posición y orientación completas tomadas del cono Usuario.
    if(entradaAplicada)return; // Espera al siguiente fotograma, cuando ojos y mandos ya usan el espacio nuevo.
    if(centrarAlEntrar && frame && !entradaVR.pendiente) {
        const pose=frame.getViewerPose(renderer.xr.getReferenceSpace());
        if(pose) {
            centrarTablet(new THREE.Vector3().copy(pose.transform.position),new THREE.Quaternion().copy(pose.transform.orientation));
            centrarAlEntrar=false; // Se centra una vez: no persigue al visor al mirar a otro lado.
        }
    }
    animador?.actualizar(tiempo);scene.updateMatrixWorld(true);
    const hoverIds=[];
    for(const {controller,line} of controllers) {
        const hit=renderer.xr.isPresenting?controllerHit(controller):null;
        const id=idImpacto(hit);const interactive=!!id;
        line.scale.z=hit?hit.distance:3;line.material.color.set(interactive?'#175cde':'#8292a9');
        if(interactive)hoverIds.push(id);
    }
    if(renderer.xr.isPresenting)ui.setHover(hoverIds);
    renderer.render(scene,camera);
}); // Bucle WebXR: permite a la plataforma gestionar la frecuencia de refresco.
initialize().catch(error=>{
    console.error('Error de inicio:',error);window.GatexDiagnostico?.error(error);
    inicio.hidden=false;entrar.disabled=true;estado.textContent='No se pudo iniciar la aplicación: '+(error.message||error);
});









