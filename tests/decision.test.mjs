// Pruebas de las tarjetas interactivas: confirmación de un candidato, alerta de un descartado e informe.
// Usan las respuestas reales guardadas en backend/api/ejemplos/ (datos de prueba) y un backend simulado.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {API} from '../js/api.mjs';
import {DialogoDecision,TITULO_CONFIRMAR,TITULO_ALERTA,informeALineas} from '../js/decision.mjs';
import {AnimadorTarjetas} from '../js/tarjetas.mjs';
import {TARJETAS_PROVEEDOR,vincularProveedores} from '../js/proveedores.mjs';

const leer=n=>JSON.parse(readFileSync(new URL('../backend/api/ejemplos/'+n,import.meta.url),'utf8'));
const evaluacion=leer('evaluacion_respuesta.json');
const informe=leer('informe_decision_ejemplo.json');
const MOTIVO_EJEMPLO=informe.secciones[2].bloques.find(b=>b.tipo==='cita').texto;

function lienzo() {
    const textos=[];
    const ctx=new Proxy({fillText:t=>textos.push(String(t))},{get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>(o[k]=v,true)});
    return {canvas:{getContext:()=>ctx},textos};
}
const respuesta=(status,data)=>({status,ok:status<400,text:async()=>JSON.stringify(data)});
// Backend simulado: cuenta los POST /decisiones; los primeros `fallos` se pierden en la red.
function backendSimulado({fallos=0,repetida=false}={}) {
    const posts=[],gets=[];let guardada=null;
    const fetch=async(url,opciones={})=>{
        const u=new URL(url),ruta=u.pathname+u.search;
        if(ruta==='/decisiones'&&opciones.method==='POST'){
            const body=JSON.parse(opciones.body);posts.push(body);
            if(posts.length<=fallos){if(repetida)guardada=decisionDe(body);throw new TypeError('Failed to fetch');}
            if(guardada)return respuesta(409,{detalle:`La solicitud ${body.solicitud_id} ya tiene la decisión ${guardada.decision_id}`});
            guardada=decisionDe(body);return respuesta(201,guardada);
        }
        gets.push(ruta);
        if(ruta==='/decisiones/DEC-0001')return respuesta(200,guardada);
        if(ruta==='/decisiones/DEC-0001/informe?formato=json')return respuesta(200,informe);
        return respuesta(404,{detalle:'Recurso no encontrado'});
    };
    const decisionDe=body=>{const c=evaluacion.candidatos.find(p=>p.proveedor_id===body.proveedor_id);
        return {decision_id:'DEC-0001',solicitud_id:body.solicitud_id,escenario_id:null,proveedor_id:c.proveedor_id,nombre:c.nombre,
            tipo_vehiculo_id:c.vehiculos.tipo_vehiculo_id,flexibilizado:false,justificacion:body.justificacion,fecha_hora:'2026-10-24T07:13:06Z',snapshot:evaluacion};};
    return {api:new API('https://backend.invalid',fetch),posts,gets};
}
function pulsar(dlg,id) {const z=dlg.zones.find(z=>z.id===id);assert.ok(z,'No se puede pulsar '+id);return z.action();}
const escribir=(dlg,texto)=>{for(const ch of texto)dlg.escribir(ch);};
const tarjeta=(estado,proveedor_id)=>({estado,proveedor_id});

test('(1) Cancelar cierra la confirmación sin registrar nada',()=>{
    const {api,posts}=backendSimulado(),{canvas,textos}=lienzo(),cambios=[];
    const dlg=new DialogoDecision({canvas,api,onCambio:abierto=>cambios.push(abierto)});
    const c=evaluacion.candidatos[0];
    assert.equal(dlg.abrirParaTarjeta(tarjeta('candidato',c.proveedor_id),evaluacion),true);
    assert.equal(dlg.modo,'confirmar');
    for(const t of [TITULO_CONFIRMAR,c.nombre,'3 × Tractomula','Probabilidad de llegar a tiempo','Motivo de la decisión (obligatorio)'])assert.ok(textos.includes(t),t);
    assert.ok(textos.some(t=>t.includes('nivel '+c.confianza.nivel)));
    escribir(dlg,'Lo pienso');
    pulsar(dlg,'dlg-cancelar');
    assert.equal(dlg.abierto,false);assert.equal(posts.length,0);assert.equal(dlg.decisiones.size,0);assert.deepEqual(cambios,[true,false]);
});

test('(2) Aceptar llama a POST /decisiones una sola vez con el contrato y abre el informe',async()=>{
    const {api,posts}=backendSimulado(),{canvas,textos}=lienzo(),registradas=[];
    const dlg=new DialogoDecision({canvas,api,onDecision:(d,ev)=>registradas.push({d,ev})});
    const c=evaluacion.candidatos[2];
    dlg.abrirParaTarjeta(tarjeta('candidato',c.proveedor_id),evaluacion);
    assert.ok(!dlg.zones.some(z=>z.id==='dlg-aceptar'),'Sin motivo, «Aceptar» está deshabilitado');
    pulsar(dlg,'frase-0');escribir(dlg,' y buen historial');
    const primera=pulsar(dlg,'dlg-aceptar');
    assert.ok(textos.includes('Registrando…'));
    assert.ok(!dlg.zones.some(z=>['dlg-aceptar','dlg-cancelar'].includes(z.id)),'Mientras registra no se puede aceptar ni cancelar');
    const segunda=dlg.aceptar();                         // Doble clic: no hace otro envío.
    await Promise.all([primera,segunda]);
    assert.equal(posts.length,1);
    assert.deepEqual(posts[0],{solicitud_id:evaluacion.solicitud_id,proveedor_id:c.proveedor_id,justificacion:'Menor costo y buen historial',escenario_id:null});
    assert.equal(registradas.length,1);assert.equal(registradas[0].ev,evaluacion,'La decisión queda ligada a lo que vio el funcionario');
    assert.deepEqual(registradas[0].d.snapshot,evaluacion);
    assert.equal(dlg.modo,'informe');assert.ok(textos.includes('Informe de decisión'));
    dlg.cerrar();                                         // Una sola decisión por solicitud: ya no se abre otra confirmación.
    dlg.abrirParaTarjeta(tarjeta('candidato',evaluacion.candidatos[0].proveedor_id),evaluacion);
    assert.equal(dlg.modo,'decidida');assert.ok(!dlg.zones.some(z=>z.id==='dlg-aceptar'));assert.equal(posts.length,1);
});

test('(3) Un error de red muestra el error, conserva el motivo y permite reintentar',async()=>{
    const {api,posts}=backendSimulado({fallos:1}),{canvas,textos}=lienzo();
    const dlg=new DialogoDecision({canvas,api});
    dlg.abrirParaTarjeta(tarjeta('candidato',evaluacion.candidatos[0].proveedor_id),evaluacion);
    escribir(dlg,'Mejor puntualidad');
    await pulsar(dlg,'dlg-aceptar');
    assert.equal(dlg.modo,'confirmar');assert.equal(dlg.motivo,'Mejor puntualidad');assert.equal(dlg.error.reintentar,true);
    assert.ok(textos.some(t=>t.includes('No se pudo registrar la decisión')));
    assert.ok(textos.includes('Reintentar'));
    await pulsar(dlg,'dlg-aceptar');
    assert.equal(posts.length,2);assert.equal(posts[1].justificacion,'Mejor puntualidad');assert.equal(dlg.modo,'informe');
});

test('(3b) Si la respuesta se perdió y el reintento da 409, se recupera la decisión ya guardada',async()=>{
    const {api,posts}=backendSimulado({fallos:1,repetida:true}),{canvas}=lienzo(),registradas=[];
    const dlg=new DialogoDecision({canvas,api,onDecision:d=>registradas.push(d)});
    dlg.abrirParaTarjeta(tarjeta('candidato',evaluacion.candidatos[0].proveedor_id),evaluacion);
    escribir(dlg,'Plazo justo');
    await pulsar(dlg,'dlg-aceptar');await pulsar(dlg,'dlg-aceptar');
    assert.equal(posts.length,2);assert.equal(dlg.error.decisionExistente,'DEC-0001');assert.ok(!dlg.zones.some(z=>z.id==='dlg-aceptar'));
    await pulsar(dlg,'dlg-ver-informe');
    assert.equal(registradas[0].decision_id,'DEC-0001');assert.equal(dlg.modo,'informe');assert.equal(posts.length,2);
});

test('(4) Un descartado abre la alerta con todas sus razones y nunca la confirmación',()=>{
    const {api,posts}=backendSimulado(),{canvas,textos}=lienzo();
    const dlg=new DialogoDecision({canvas,api});
    // Mismo camino que main.js: la tarjeta del GLB → animador → diálogo.
    const vinculos=vincularProveedores([...evaluacion.candidatos,...evaluacion.cancelados]);assert.equal(vinculos.errores.length,0);
    class V{constructor(y=0){this.x=0;this.y=y;this.z=0;}clone(){const v=new V(this.y);return v;}copy(p){this.y=p.y;return this;}lerp(p,t){this.y+=(p.y-this.y)*t;return this;}}
    const nodos=TARJETAS_PROVEEDOR.map(([name])=>({name,position:new V(5)}));
    const anim=new AnimadorTarjetas({traverse:f=>nodos.forEach(f)},{descenso_m:3,duracion_ms:1});
    anim.aplicar(evaluacion,vinculos.porId,'panel');
    const varios=evaluacion.cancelados.find(c=>c.razones.length>1&&c.razones.length===Math.max(...evaluacion.cancelados.map(x=>x.razones.length)));
    const item=anim.desdeObjeto(nodos.find(n=>n.name===vinculos.porId.get(varios.proveedor_id).tarjeta));
    assert.equal(item.estado,'cancelado');assert.ok(anim.esSeleccionable(item));
    assert.equal(dlg.abrirParaTarjeta(item,evaluacion),true);
    assert.equal(dlg.modo,'alerta');
    for(const t of [TITULO_ALERTA,varios.nombre,'No elegible','Entendido'])assert.ok(textos.includes(t),t);
    for(const r of varios.razones){assert.ok(textos.includes('• '+r.mensaje),r.mensaje);assert.ok(textos.some(t=>t.startsWith('Requerido: ')&&t.includes(r.codigo)));}
    assert.ok(!textos.some(t=>t.includes('Casi elegible')),'Falla varias reglas: no es casi elegible');
    assert.ok(dlg.zones.every(z=>['dlg-entendido','dlg-subir','dlg-bajar'].includes(z.id)),'No hay ningún botón para contratar');
    for(const z of [...dlg.zones])z.action();             // Pulsar todo lo que hay solo cierra la alerta.
    assert.equal(dlg.abierto,false);assert.equal(posts.length,0);

    const uno=evaluacion.cancelados.find(c=>c.proveedor_id==='PROV-10');textos.length=0;
    dlg.abrirParaTarjeta(tarjeta('cancelado',uno.proveedor_id),evaluacion);
    assert.ok(textos.includes('Casi elegible: falla una sola regla.'));
    assert.ok(textos.includes('• Necesita 3 × Tractomula, solo tiene 2 disponible(s)'));
    assert.ok(textos.includes('Requerido: 3 · Disponible: 2 · Código VEHICULOS_INSUFICIENTES'));
    pulsar(dlg,'dlg-entendido');assert.equal(posts.length,0);
});

test('Retroalimentación visual: apuntar, seleccionar y marcar al elegido solo entre candidatos',()=>{
    const vinculos=vincularProveedores([...evaluacion.candidatos,...evaluacion.cancelados]),estados=new Map();
    const nodos=TARJETAS_PROVEEDOR.map(([name])=>({name,position:{clone(){return this;},copy(){return this;},lerp(){return this;},y:0}}));
    const anim=new AnimadorTarjetas({traverse:f=>nodos.forEach(f)},{apariencia:{preparar(){},aplicar:(n,e)=>estados.set(n.name,e)}});
    anim.aplicar(evaluacion,vinculos.porId,'panel');
    const candidata=vinculos.porId.get(evaluacion.candidatos[0].proveedor_id).tarjeta,descartada=vinculos.porId.get('PROV-02').tarjeta;
    anim.resaltar([candidata]);assert.equal(estados.get(candidata).hover,true);assert.equal(estados.get(descartada).hover,false);
    anim.seleccionar(descartada);assert.equal(estados.get(descartada).seleccionada,true);assert.equal(estados.get(descartada).estado,'cancelado');
    assert.equal(anim.marcarElegida('PROV-02'),false,'Un descartado nunca se marca como elegido');
    assert.equal(anim.marcarElegida(evaluacion.candidatos[0].proveedor_id),true);assert.equal(estados.get(candidata).elegida,true);
    anim.restaurar();assert.ok([...estados.values()].every(e=>!e.hover&&!e.seleccionada&&!e.elegida&&e.estado==='neutral'));
});

test('(5) El informe del backend se muestra en el panel con sus 8 secciones en orden',async()=>{
    const lineas=informeALineas(informe);
    assert.deepEqual(lineas.filter(l=>l.estilo==='h1'||l.estilo==='h2').map(l=>l.texto),[
        'COSCO SHIPPING – Informe de decisión de proveedor','2. La solicitud','3. Decisión final','4. Resultados predichos para la opción elegida',
        '5. Comparación con los demás candidatos','6. Proveedores descartados','7. Parámetros de la simulación','8. Nota']);
    const texto=lineas.map(l=>l.texto).join('\n');
    for(const t of ['ID de la solicitud: REQ-0496','Origen → destino: Buenaventura → Bogotá','Plazo: 33,0 h',`«${MOTIVO_EJEMPLO}»`,
        'Profit en mal escenario (P10): $15.280.000','Probabilidad de llegar a tiempo: 71,6 %','Puntualidad (pesa 75 %): 69,8 %',
        'Simulaciones (N): 2.000','Semilla: 42','Penalidad por hora de retraso: $50.000',
        'Recomendaciones generadas por el sistema; la decisión fue tomada por el funcionario.'])assert.ok(texto.includes(t),t);
    for(const c of evaluacion.cancelados)for(const r of c.razones)assert.ok(texto.includes(`• ${r.codigo}: ${r.mensaje}`),r.codigo);
    for(const c of evaluacion.candidatos)assert.ok(texto.includes(c.nombre));
    assert.equal(lineas.filter(l=>l.estilo==='resaltada').length,2,'Solo la fila elegida va resaltada');

    const {api,gets}=backendSimulado(),{canvas}=lienzo(),abiertos=[],copiados=[];
    const dlg=new DialogoDecision({canvas,api,abrirURL:u=>abiertos.push(u),copiarTexto:async t=>{copiados.push(t);}});
    await dlg.abrirInforme({decision_id:'DEC-0001',solicitud_id:'REQ-0496',nombre:'Transportes Andinos del Sur'});
    assert.ok(gets.includes('/decisiones/DEC-0001/informe?formato=json'));
    assert.equal(dlg.modo,'informe');assert.ok(dlg.lineas.length>25);
    pulsar(dlg,'dlg-bajar');assert.ok(dlg.offset>0,'El panel tiene desplazamiento');pulsar(dlg,'dlg-subir');assert.equal(dlg.offset,0);
    pulsar(dlg,'dlg-abrir');assert.deepEqual(abiertos,['https://backend.invalid/decisiones/DEC-0001/informe?descargar=false']);
    pulsar(dlg,'dlg-copiar');await new Promise(r=>setTimeout(r,0));assert.deepEqual(copiados,abiertos);assert.match(dlg.avisoEnlace,/copiado/);
    pulsar(dlg,'dlg-cerrar');assert.equal(dlg.abierto,false);
});
