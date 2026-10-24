import * as THREE from 'three';
import { XRControllerModelFactory } from 'three/addons/webxr/XRControllerModelFactory.js';

const inicio = document.getElementById('inicio'); // Pantalla 1: una única acción de entrada.
const entrar = document.getElementById('entrar');
const estado = document.getElementById('estado');
const preview = new URLSearchParams(location.search).has('preview'); // Prueba de escritorio explícita; no simula soporte WebXR.
const scene = new THREE.Scene();
scene.background = new THREE.Color('#e9edf2');
scene.fog = new THREE.Fog('#e9edf2', 8, 28);
const camera = new THREE.PerspectiveCamera(65, innerWidth / innerHeight, .05, 60);
camera.position.set(0, 1.6, 0); // WebXR sustituye esta pose por la del visor.
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5)); // Limita el coste de la vista convencional.
renderer.setSize(innerWidth, innerHeight);
renderer.xr.enabled = true;
renderer.xr.setReferenceSpaceType('local-floor'); // Sitúa el suelo en el suelo físico del área de juego.
document.body.appendChild(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff, 0xa1aabb, 2.4));
const light = new THREE.DirectionalLight(0xffffff, 2);
light.position.set(2, 6, 3); scene.add(light);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshStandardMaterial({color:'#d7dde5', roughness:1}));
floor.rotation.x = -Math.PI / 2; scene.add(floor);
const grid = new THREE.GridHelper(30, 30, '#b8c6d5', '#cbd3dd');
grid.position.y = .002; scene.add(grid); // Referencia espacial sin modelos ni texturas pesadas.

const tablet = new THREE.Group();
tablet.position.set(0, 1.48, -1.35); scene.add(tablet); // Tablet fija frente al usuario, sin movimiento artificial de cámara.
const shell = new THREE.Mesh(new THREE.BoxGeometry(1.2, .9, .04), new THREE.MeshStandardMaterial({color:'#26344c', roughness:.5}));
tablet.add(shell); // Carcasa provisional sustituible por un GLB de Blender.
const canvas = document.createElement('canvas'); canvas.width = 1440; canvas.height = 1080;
const ctx = canvas.getContext('2d');
const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace;
const screen = new THREE.Mesh(new THREE.PlaneGeometry(1.15, .8625), new THREE.MeshBasicMaterial({map:texture}));
screen.position.z = .022; tablet.add(screen); // Pantalla interactiva independiente de la carcasa.

const fields = [
    {id:'origen', label:'Origen', value:'', hint:'Ciudad o terminal'},
    {id:'destino', label:'Destino', value:'', hint:'Ciudad o bodega'},
    {id:'carga', label:'Tipo de carga', value:'', hint:'Ej. contenedor seco'},
    {id:'vehiculo', label:'Vehículo requerido', value:'', hint:'Ej. tractocamión'},
    {id:'peso', label:'Peso (kg)', value:'', hint:'Ej. 18000'},
    {id:'plazo', label:'Fecha límite (AAAA-MM-DD)', value:'', hint:'Ej. 2026-11-01'}
]; // Borrador local en memoria: no se envía ni persiste información.
let active = -1, focus = 0, zones = [], xrSession = null, starting = false;
const raycaster = new THREE.Raycaster(); const rotation = new THREE.Matrix4();
const controllers = [], selecting = new Set();

function text(value, x, y, size=24, color='#16243b', weight=400) {
    ctx.fillStyle=color; ctx.font=`${weight} ${size}px system-ui, sans-serif`; ctx.textAlign='left'; ctx.fillText(value,x,y);
}
function card(x,y,w,h,color) {
    ctx.fillStyle=color; ctx.beginPath(); ctx.roundRect(x,y,w,h,14); ctx.fill();
}
function zone(id,x,y,w,h,action) {
    zones.push({id,x,y,w,h,action}); // Las mismas zonas sirven para mandos, ratón y teclado.
}
function button(id,label,x,y,w,h,action,color='#edf2fa') {
    card(x,y,w,h,color); text(label,x+16,y+h/2+9,24,color==='#175cde'?'#ffffff':'#16243b',600);
    zone(id,x,y,w,h,action);
}
function draw() {
    zones=[]; ctx.fillStyle='#f5f7fb';ctx.fillRect(0,0,1440,1080);
    text('GATEX',42,60,32,'#175cde',800);text('SIM VR / OPERACIONES',210,58,20,'#5f6e83',600);
    button('exit','Salir de VR',1190,22,205,56,()=>exitVR());
    text('02 / Ingreso de solicitud',42,135,39,'#16243b',700);
    text('Completa el borrador de transporte terrestre.',42,176,23,'#586a82');
    fields.forEach((field,i)=>{
        const x=42+(i%2)*452, y=210+Math.floor(i/2)*130;
        text(field.label,x,y+23,23,'#334760',600);card(x,y+37,425,64,active===i?'#dbe9ff':'#ffffff');
        ctx.save(); ctx.beginPath();ctx.rect(x+10,y+38,401,62);ctx.clip();
        text(field.value||field.hint,x+16,y+78,25,field.value?'#16243b':'#738299');ctx.restore();
        zone(`field-${i}`,x,y+37,425,64,()=>{active=i;draw();});
    });
    card(970,210,425,360,'#ffffff');text('Solicitudes anteriores',996,254,27,'#16243b',700);
    text('Sin solicitudes cargadas.',996,316,23,'#5f6e83');
    text('Backend pendiente de conexión.',996,355,20,'#5f6e83');
    text('El borrador no se guarda al salir.',996,409,20,'#5f6e83');
    card(42,615,1353,63,'#e3ebf7');
    text(active<0?'Selecciona un campo con el gatillo del mando.':`Editando: ${fields[active].label}`,60,655,23,'#23446d',600);
    if(active>=0) drawKeyboard();
    else {text('Teclado virtual disponible al seleccionar un campo.',60,753,26,'#586a82');text('Los datos permanecen en esta sesión. No se envían al backend.',60,803,23,'#586a82');}
    card(42,987,1353,57,'#e4e8ee');text('Análisis de proveedores · Disponible en una próxima versión',62,1024,24,'#617087');
    focus=Math.min(focus,zones.length-1); texture.needsUpdate=true; // Solo actualiza la textura al cambiar la interfaz.
}
function edit(key) {
    if(active<0)return;
    const f=fields[active];
    if(key==='DEL') f.value=Array.from(f.value).slice(0,-1).join('');
    else if(key==='NEXT') active=(active+1)%fields.length;
    else if(key==='DONE') active=-1;
    else if(f.value.length<70)f.value+=key;
    draw();
}
function drawKeyboard() {
    const rows=['1234567890','QWERTYUIOP','ASDFGHJKLÑ','ZXCVBNM.-/'];
    rows.forEach((row,r)=>Array.from(row).forEach((key,c)=>button(`key-${key}`,key,42+c*96,700+r*53,88,46,()=>edit(key))));
    button('space','Espacio',42,918,370,52,()=>edit(' '));
    button('delete','Borrar',427,918,235,52,()=>edit('DEL'));
    button('next','Siguiente campo',677,918,330,52,()=>edit('NEXT'));
    button('done','Listo',1022,918,373,52,()=>edit('DONE'),'#175cde');
}
function findZone(uv) {
    if(!uv)return null;
    const x=uv.x*1440, y=(1-uv.y)*1080;
    return zones.find(z=>x>=z.x&&x<=z.x+z.w&&y>=z.y&&y<=z.y+z.h);
}
function controllerHit(controller) {
    controller.updateWorldMatrix(true,false); rotation.identity().extractRotation(controller.matrixWorld);
    raycaster.ray.origin.setFromMatrixPosition(controller.matrixWorld);
    raycaster.ray.direction.set(0,0,-1).applyMatrix4(rotation);
    return raycaster.intersectObject(screen,false)[0];
}
const factory = new XRControllerModelFactory();
for(let i=0;i<2;i++) {
    const controller=renderer.xr.getController(i);
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3(0,0,-1)]),new THREE.LineBasicMaterial({color:'#175cde'}));
    line.scale.z=3; controller.add(line); scene.add(controller); controllers.push({controller,line});
    controller.addEventListener('selectstart',()=>{
        if(selecting.has(controller))return; selecting.add(controller); // Evita repetición al mantener presionado el gatillo.
        const hit=controllerHit(controller); findZone(hit?.uv)?.action();
    });
    controller.addEventListener('selectend',()=>selecting.delete(controller));
    controller.addEventListener('disconnected',()=>selecting.delete(controller));
    const grip=renderer.xr.getControllerGrip(i);grip.add(factory.createControllerModel(grip));scene.add(grip);
} // Interacción de esta versión: apuntar con cualquiera de los mandos y pulsar el gatillo. No requiere manos.
renderer.domElement.addEventListener('pointerdown',event=>{
    if(!preview||renderer.xr.isPresenting)return;
    const rect=renderer.domElement.getBoundingClientRect();
    raycaster.setFromCamera(new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1),camera);
    findZone(raycaster.intersectObject(screen,false)[0]?.uv)?.action();
});
window.addEventListener('keydown',event=>{
    if(!preview||!inicio.hidden)return;
    if(['Tab','ArrowRight','ArrowLeft','Enter','Backspace','Escape'].includes(event.key))event.preventDefault();
    if(event.key==='Tab'||event.key==='ArrowRight'||event.key==='ArrowLeft') {
        focus=(focus+((event.shiftKey||event.key==='ArrowLeft')?-1:1)+zones.length)%zones.length;
        draw();const z=zones[focus];ctx.strokeStyle='#175cde';ctx.lineWidth=5;ctx.strokeRect(z.x,z.y,z.w,z.h);texture.needsUpdate=true;
    } else if(event.key==='Enter')zones[focus]?.action();
    else if(event.key==='Escape'){active=-1;draw();}
    else if(event.key==='Backspace')edit('DEL');
    else if(event.key.length===1&&!event.ctrlKey&&!event.metaKey&&!event.altKey){event.preventDefault();edit(event.key);}
});
function resetForm() {fields.forEach(f=>f.value='');active=-1;focus=0;draw();} // Limpia el borrador al terminar la sesión.
async function exitVR() {
    if(xrSession) {try{await xrSession.end();}catch(error){console.error(error);}}
    else {resetForm();inicio.hidden=false;document.getElementById('aviso').hidden=true;entrar.focus();}
}
entrar.addEventListener('click',async()=>{
    if(starting)return;
    if(preview) {inicio.hidden=true;document.getElementById('aviso').hidden=false;draw();return;}
    starting=true;entrar.disabled=true;
    let session;
    try {
        session=await navigator.xr.requestSession('immersive-vr',{requiredFeatures:['local-floor']}); // Solicitud dentro del clic: conserva la activación del usuario.
        xrSession=session;
        session.addEventListener('end',()=>{
            xrSession=null;selecting.clear();resetForm();inicio.hidden=false;entrar.disabled=false;
            estado.textContent='Sesión terminada. Puedes volver a entrar.';entrar.focus();
        },{once:true});
        await renderer.xr.setSession(session);inicio.hidden=true;draw(); // Entrada directa a la sección 2.
    } catch(error) {
        console.error(error);if(session)await session.end().catch(()=>{});xrSession=null;
        estado.textContent='No se pudo entrar en VR. Comprueba los permisos del navegador y el área de juego e inténtalo de nuevo.';
        window.alert(estado.textContent);
    } finally {starting=false;entrar.disabled=false;}
});
async function initialize() {
    draw();
    if(preview){entrar.textContent='Abrir prueba en PC';entrar.disabled=false;estado.textContent='Modo de desarrollo. Esta vista no verifica el funcionamiento del visor.';return;}
    if(location.protocol==='file:'||!isSecureContext){estado.textContent='Para usar VR abre esta página desde una dirección HTTPS válida en Meta Quest Browser. No abras index.html con doble clic.';return;}
    try {
        if(!navigator.xr||!await navigator.xr.isSessionSupported('immersive-vr')) {
            estado.textContent='Este dispositivo o navegador no admite VR inmersiva. Abre esta dirección en Meta Quest Browser.';
            window.alert(estado.textContent);return;
        }
        estado.textContent='';entrar.disabled=false;
    } catch(error){console.error(error);estado.textContent='No se pudo comprobar WebXR. Revisa los permisos y abre la página directamente, fuera de una vista previa incrustada.';}
}
window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
renderer.setAnimationLoop(()=>{
    for(const {controller,line} of controllers) {
        const hit=renderer.xr.isPresenting?controllerHit(controller):null;
        line.scale.z=hit?hit.distance:3;line.material.color.set(findZone(hit?.uv)?'#175cde':'#8292a9');
    }
    renderer.render(scene,camera);
}); // Bucle WebXR: permite a la plataforma gestionar la frecuencia de refresco.
initialize();
