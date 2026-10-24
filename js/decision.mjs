// Diálogos de decisión en un panel flotante (1440×1080), iguales en las gafas y en la vista web:
// confirmación para un candidato, alerta para un descartado e informe de la decisión registrada.
// Solo muestra y envía: el filtro, los cálculos, el snapshot y el informe salen del backend.
import {LienzoUI,dibujarTeclas} from './lienzo.mjs';

export const TITULO_CONFIRMAR='¿Estás seguro de contratar a este proveedor?';
export const TITULO_ALERTA='Este proveedor no cumple los requerimientos mínimos';
export const FRASES_RAPIDAS=['Menor costo','Mejor tiempo de entrega','Mayor confianza','Mejor desempeño'];
export const MAX_MOTIVO=300;

const numero=(x,dec=1)=>new Intl.NumberFormat('es-CO',{minimumFractionDigits:dec,maximumFractionDigits:dec}).format(x);
export const dinero=n=>n==null?'No disponible':new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(n);
const horas=x=>numero(x)+' h';
const porcentaje=x=>numero(100*x)+' %';
const valor=v=>v===null||v===undefined||v===''?'—':typeof v==='number'?new Intl.NumberFormat('es-CO',{maximumFractionDigits:2}).format(v):String(v);

// Resumen breve del candidato para la confirmación (valores tal como los entrega la API).
export function resumenCandidato(c) {
    return [
        ['Vehículos',`${c.vehiculos.cantidad} × ${c.vehiculos.tipo}`],
        ['Costo',dinero(c.costo_cop)],
        ['Profit esperado',`${dinero(c.profit.esperado_cop)} · P10 ${dinero(c.profit.p10_cop)}`],
        ['Margen',c.profit.margen_pct==null?'No disponible':numero(c.profit.margen_pct)+' %'],
        ['Tiempo P50 / P90',`${horas(c.tiempo_h.p50)} / ${horas(c.tiempo_h.p90)}`],
        ['Probabilidad de llegar a tiempo',porcentaje(c.tiempo_h.prob_a_tiempo)],
        ['Confianza',`${numero(c.confianza.valor)} / 100 · nivel ${c.confianza.nivel}`],
        ['Desempeño',`${numero(c.desempeno.valor)} / 100`],
    ];
}

// Todas las razones de un descartado: mensaje legible y dato requerido frente al disponible.
export function razonesDescarte(cancelado,casi) {
    const razones=cancelado?.razones?.length?cancelado.razones:(casi?.razon?[casi.razon]:[]);
    return razones.map(r=>({codigo:r.codigo??null,mensaje:r.mensaje,detalle:`Requerido: ${valor(r.requerido)} · Disponible: ${valor(r.disponible)} · Código ${r.codigo??'—'}`}));
}

export function describirError(error) {
    const status=error?.status??0,detalle=error?.message||String(error);
    if(status===409){const id=/DEC-\d+/.exec(detalle)?.[0]||null;return {mensaje:'Esta solicitud ya tiene una decisión registrada'+(id?` (${id})`:'')+'. Solo se registra una por solicitud.',reintentar:false,decisionExistente:id};}
    if(status===404)return {mensaje:'El backend ya no tiene esta solicitud (¿se reinició?). Cierra y vuelve a evaluar.',reintentar:false};
    if(status===422)return {mensaje:'El backend rechazó el registro: '+(error.errores?.map(e=>e.mensaje).filter(Boolean).join(' · ')||detalle),reintentar:true};
    return {mensaje:'No se pudo registrar la decisión. Tu motivo se conserva: pulsa «Reintentar». Detalle: '+detalle,reintentar:true};
}

// Informe JSON del backend → líneas con estilo, en el mismo orden de las 8 secciones del HTML.
export function informeALineas(informe) {
    const out=[],add=(texto,estilo='normal')=>out.push({texto:String(texto??''),estilo});
    for(const s of informe.secciones) {
        add(s.numero===1?s.titulo:`${s.numero}. ${s.titulo}`,s.numero===1?'h1':'h2');
        for(const b of s.bloques) {
            if(b.titulo)add(b.titulo,'h3');
            if(b.tipo==='datos')for(const p of b.pares)add(`${p.etiqueta}: ${p.valor}`);
            else if(b.tipo==='cita')add(`«${b.texto}»`,'cita');
            else if(b.tipo==='aviso')add(b.texto,'aviso');
            else if(b.tipo==='texto')add(b.texto);
            else if(b.tipo==='lista')for(const item of b.items)add('• '+item);
            else if(b.tipo==='razones')for(const r of b.razones){add(`• ${r.codigo}: ${r.mensaje}`);add(`Requerido: ${valor(r.requerido)} · Disponible: ${valor(r.disponible)}`,'tenue');}
            else if(b.tipo==='tabla')b.filas.forEach((fila,i)=>{
                const elegida=i===b.resaltada;
                add(elegida?`${fila[0]} · ELEGIDO POR EL FUNCIONARIO`:fila[0],elegida?'resaltada':'fila');
                add(fila.slice(1).map((v,j)=>`${b.encabezados[j+1]??''}: ${v}`).join(' · '),elegida?'resaltada':'normal');
            });
        }
        add('','espacio');
    }
    return out;
}

const ESTILOS={
    h1:{size:32,color:'#16243b',weight:800,alto:50},h2:{size:28,color:'#175cde',weight:700,alto:50},
    h3:{size:24,color:'#334760',weight:700,alto:38},fila:{size:23,color:'#16243b',weight:700,alto:34},
    normal:{size:23,color:'#16243b',weight:400,alto:33},tenue:{size:21,color:'#586a82',weight:400,alto:30},
    cita:{size:24,color:'#23446d',weight:'italic 400',alto:35},aviso:{size:23,color:'#9a3412',weight:600,alto:33},
    resaltada:{size:23,color:'#0b3d91',weight:700,alto:34,fondo:'#e3edff'},espacio:{size:10,weight:400,alto:14}
};
const estilo=l=>ESTILOS[l.estilo]||ESTILOS.normal;
export function ajustarLineas(lineas,ancho,wrap) {
    return lineas.flatMap(l=>{
        const e=estilo(l);if(!l.texto)return [{texto:'',estilo:l.estilo}];
        const factor=typeof e.weight==='number'&&e.weight>=600?.57:.52; // Estimación sin medir: las negritas ocupan más.
        return wrap(l.texto,Math.max(20,Math.floor(ancho/(e.size*factor)))).map(texto=>({texto,estilo:l.estilo}));
    });
}

export class DialogoDecision extends LienzoUI {
    constructor({canvas,api,onDirty,onCambio=()=>{},onDecision=()=>{},abrirURL=()=>{},copiarTexto=null}) {
        super({canvas,onDirty});Object.assign(this,{api,onCambio,onDecision,abrirURL,copiarTexto});
        this.decisiones=new Map(); // solicitud_id → decisión registrada desde este equipo
        this.version=0;this.modo=null;this.areaAlto=780;this.limpiar();
    }
    get abierto() {return this.modo!==null;}
    limpiar() {
        Object.assign(this,{candidato:null,evaluacion:null,descartado:null,motivo:'',mayus:false,enviando:false,error:null,
            decision:null,lineas:[],offset:0,cargandoInforme:false,errorInforme:null,avisoEnlace:'',focus:0,keyboardFocus:false});
    }
    cambiarModo(modo) {const antes=this.modo;this.modo=modo;this.draw();if(antes!==modo)this.onCambio(this.abierto,modo);}

    // Candidato → confirmación (o aviso si ya hay decisión). Descartado o casi elegible → alerta, nunca confirmación.
    abrirParaTarjeta(item,evaluacion) {
        if(!item||!evaluacion)return false;
        const id=item.proveedor_id;
        if(item.estado==='candidato') {
            const c=evaluacion.candidatos.find(p=>p.proveedor_id===id);if(!c)return false;
            const previa=this.decisiones.get(evaluacion.solicitud_id);
            return previa?this.abrirYaDecidida(previa):this.abrirConfirmacion(c,evaluacion);
        }
        if(item.estado==='cancelado'||item.estado==='casi') {
            const cancelado=evaluacion.cancelados.find(p=>p.proveedor_id===id),casi=evaluacion.casi_elegibles?.find(p=>p.proveedor_id===id);
            return cancelado||casi?this.abrirAlerta(cancelado,casi):false;
        }
        return false;
    }
    abrirConfirmacion(candidato,evaluacion) {this.version++;this.limpiar();Object.assign(this,{candidato,evaluacion});this.cambiarModo('confirmar');return true;}
    abrirAlerta(cancelado,casi) {
        this.version++;this.limpiar();const p=cancelado||casi,razones=razonesDescarte(cancelado,casi);
        this.descartado={nombre:p.nombre,proveedor_id:p.proveedor_id,razones,casi:razones.length===1,flexibilizar:casi?.flexibilizar||null};
        this.lineas=ajustarLineas(razones.flatMap(r=>[{texto:'• '+r.mensaje,estilo:'fila'},{texto:r.detalle,estilo:'tenue'},{texto:'',estilo:'espacio'}]),1240,(t,w)=>this.wrap(t,w));
        this.cambiarModo('alerta');return true;
    }
    abrirYaDecidida(decision) {this.version++;this.limpiar();this.decision=decision;this.cambiarModo('decidida');return true;}
    cerrar() {this.version++;this.limpiar();this.cambiarModo(null);} // Si había un envío en curso, su resultado se sigue guardando con onDecision.

    async aceptar() {
        if(this.modo!=='confirmar'||this.enviando)return; // Evita dobles envíos.
        const justificacion=this.motivo.trim();
        if(!justificacion){this.error={mensaje:'Escribe el motivo de la decisión: queda registrado en el informe.',reintentar:true,vacio:true};this.draw();return;}
        const {candidato:c,evaluacion:ev}=this,version=this.version;
        this.enviando=true;this.error=null;this.draw();
        let decision;
        try {decision=await this.api.decidir({solicitud_id:ev.solicitud_id,proveedor_id:c.proveedor_id,justificacion,escenario_id:ev.escenario_id??null});}
        catch(error) {if(version===this.version){this.enviando=false;this.error=describirError(error);this.draw();}return;}
        this.decisiones.set(ev.solicitud_id,decision);this.onDecision(decision,ev);
        if(version!==this.version)return;
        return this.abrirInforme(decision);
    }
    // 409 tras un envío cuya respuesta se perdió: se recupera la decisión que ya quedó guardada.
    async recuperarDecision(decision_id) {
        const ev=this.evaluacion,version=++this.version;this.error={mensaje:'Recuperando la decisión registrada…',reintentar:false};this.draw();
        try {
            const decision=await this.api.decision(decision_id);
            if(ev&&decision.solicitud_id===ev.solicitud_id){this.decisiones.set(ev.solicitud_id,decision);this.onDecision(decision,ev);}
            if(version===this.version)return this.abrirInforme(decision);
        } catch {if(version===this.version)return this.abrirInforme({decision_id});}
    }
    async abrirInforme(decision) {
        const version=++this.version;this.limpiar();this.decision=decision;this.cargandoInforme=true;this.cambiarModo('informe');
        try {
            const informe=await this.api.informe(decision.decision_id);
            if(version!==this.version)return;
            this.lineas=ajustarLineas(informeALineas(informe),1240,(t,w)=>this.wrap(t,w));
        } catch(error) {if(version===this.version)this.errorInforme=error?.message||String(error);}
        finally {if(version===this.version){this.cargandoInforme=false;this.draw();}}
    }

    debeMayuscula() {return this.mayus||!this.motivo.trim()||/[.!?]\s*$/.test(this.motivo);}
    escribir(k) {
        if(this.modo!=='confirmar'||this.enviando)return;
        if(k==='DEL')this.motivo=Array.from(this.motivo).slice(0,-1).join('');
        else if(Array.from(this.motivo).length<MAX_MOTIVO){this.motivo+=k;this.mayus=false;}
        if(this.error?.vacio)this.error=null;
        this.draw();
    }
    agregarFrase(frase) {
        if(this.enviando)return;const base=this.motivo.trimEnd();
        const texto=base?base+(/[.,;:]$/.test(base)?' ':'. ')+frase:frase;
        this.motivo=Array.from(texto).slice(0,MAX_MOTIVO).join('');if(this.error?.vacio)this.error=null;this.draw();
    }
    copiar(url) {
        Promise.resolve().then(()=>{if(!this.copiarTexto)throw new Error('sin portapapeles');return this.copiarTexto(url);})
            .then(()=>{this.avisoEnlace='Enlace copiado. Pégalo en la tableta o en la web para abrir el informe.';},()=>{this.avisoEnlace='No se pudo copiar automáticamente: escribe el enlace de arriba en la tableta o la web.';})
            .finally(()=>{if(this.modo==='informe')this.draw();});
    }

    // --- Desplazamiento de listas largas (razones e informe) ---
    maxOffset(alto=this.areaAlto) {let suma=0;for(let i=this.lineas.length-1;i>=0;i--){suma+=estilo(this.lineas[i]).alto;if(suma>alto)return i+1;}return 0;}
    scroll(n) {const next=Math.max(0,Math.min(this.maxOffset(),this.offset+Math.trunc(n)));if(next!==this.offset){this.offset=next;this.draw();}}
    dibujarLineas(x,y,ancho,alto) {
        this.areaAlto=alto;this.offset=Math.min(this.offset,this.maxOffset(alto));let yy=y,visibles=0;
        for(let i=this.offset;i<this.lineas.length;i++){
            const l=this.lineas[i],e=estilo(l);if(yy+e.alto>y+alto)break;
            if(e.fondo)this.rect(x-10,yy,ancho+20,e.alto,e.fondo,4);
            if(l.texto)this.texto(l.texto,x,yy+e.alto*.72,e.size,e.color,e.weight);
            yy+=e.alto;visibles++;
        }
        if(this.maxOffset(alto)>0){
            const bx=x+ancho+16;
            this.button('dlg-subir','Arriba',bx,y,120,90,()=>this.scroll(-6),this.offset>0);
            this.button('dlg-bajar','Abajo',bx,y+alto-90,120,90,()=>this.scroll(6),this.offset<this.maxOffset(alto));
            this.texto(`${this.offset+1}–${this.offset+visibles}`,bx+6,y+alto/2-4,18,'#586a82',600);this.texto(`de ${this.lineas.length}`,bx+6,y+alto/2+22,18,'#586a82');
        }
    }
    iconoAlerta(x,y,s,color='#ffffff',fondo='#b45309') {
        const c=this.ctx;c.fillStyle=color;c.beginPath();c.moveTo(x+s/2,y);c.lineTo(x+s,y+s*.92);c.lineTo(x,y+s*.92);c.closePath();c.fill();
        c.fillStyle=fondo;c.fillRect(x+s*.45,y+s*.3,s*.1,s*.34);c.fillRect(x+s*.45,y+s*.7,s*.1,s*.1);
    }

    draw() {
        const c=this.ctx;this.zones=[];c.fillStyle='#ffffff';c.fillRect(0,0,1440,1080);
        if(this.modo==='confirmar')this.dibujarConfirmacion();
        else if(this.modo==='alerta')this.dibujarAlerta();
        else if(this.modo==='informe')this.dibujarInforme();
        else if(this.modo==='decidida')this.dibujarDecidida();
        this.marcarFoco();this.onDirty();
    }
    dibujarConfirmacion() {
        const c=this.candidato,editable=!this.enviando;
        this.rect(0,0,1440,104,'#175cde',0);this.texto(TITULO_CONFIRMAR,48,68,38,'#ffffff',800);
        this.texto(c.nombre,48,156,34,'#16243b',700);
        this.texto(`${c.proveedor_id} · Solicitud ${this.evaluacion.solicitud_id} · Proveedor elegible`,48,192,20,'#586a82',600);
        resumenCandidato(c).forEach(([etiqueta,texto],i)=>{const x=48+(i%2)*690,y=212+Math.floor(i/2)*70;this.texto(etiqueta,x,y+22,19,'#586a82',600);this.texto(texto,x,y+54,27,'#16243b',700);});
        this.texto('Motivo de la decisión (obligatorio)',48,526,23,'#16243b',700);
        this.texto(`${Array.from(this.motivo).length}/${MAX_MOTIVO}`,1290,526,19,'#586a82');
        this.rect(48,540,1344,82,'#eef3fb');
        const lineas=this.motivo?this.wrap(this.motivo+(editable?'|':''),104).slice(-2):['Escribe por qué eliges a este proveedor; queda en el informe.'];
        lineas.forEach((l,i)=>this.texto(l,66,574+i*32,23,this.motivo?'#16243b':'#738299'));
        FRASES_RAPIDAS.forEach((f,i)=>this.button('frase-'+i,'+ '+f,48+i*338,636,326,48,()=>this.agregarFrase(f),editable,false,{size:19}));
        if(editable){
            dibujarTeclas(this,48,698,k=>this.escribir(k),!this.debeMayuscula());
            this.button('dlg-borrar','Borrar',1020,698,372,46,()=>this.escribir('DEL'));
            this.button('dlg-mayus','Mayús',1020,751,372,46,()=>{this.mayus=!this.mayus;this.draw();},true,this.mayus);
            this.button('dlg-espacio','Espacio',1020,804,372,99,()=>this.escribir(' '));
        } else {this.rect(48,698,1344,205,'#eef3fb');this.texto('Registrando la decisión en el backend…',90,812,30,'#175cde',700);}
        if(this.enviando)this.texto('Registrando… no cierres el panel ni repitas el envío.',48,940,22,'#175cde',700);
        else if(this.error)this.wrap(this.error.mensaje,118).slice(0,2).forEach((l,i)=>this.texto(l,48,930+i*26,20,'#b42318',600));
        else if(!this.motivo.trim())this.texto('Escribe el motivo para habilitar «Aceptar».',48,940,20,'#586a82');
        this.button('dlg-cancelar','Cancelar',48,972,560,80,()=>this.cerrar(),editable,false,{size:28});
        const existente=this.error?.decisionExistente;
        if(existente)this.button('dlg-ver-informe','Ver informe',832,972,560,80,()=>this.recuperarDecision(existente),true,true,{size:28});
        else this.button('dlg-aceptar',this.enviando?'Registrando…':this.error&&!this.error.vacio?'Reintentar':'Aceptar',832,972,560,80,()=>this.aceptar(),editable&&!!this.motivo.trim()&&this.error?.reintentar!==false,true,{size:28});
    }
    dibujarAlerta() {
        const d=this.descartado;
        this.rect(0,0,1440,112,'#b45309',0);this.iconoAlerta(48,20,74);this.texto(TITULO_ALERTA,146,72,34,'#ffffff',800);
        this.texto(d.nombre,48,166,32,'#16243b',700);
        this.rect(1150,130,242,50,'#fde68a');this.iconoAlerta(1164,137,36,'#9a3412','#fde68a');this.texto('No elegible',1212,165,24,'#7c2d12',800);
        this.texto(`${d.proveedor_id} · ${d.razones.length} ${d.razones.length===1?'razón':'razones'} de descarte · no se puede contratar desde aquí`,48,202,20,'#586a82',600);
        let y=226;
        if(d.casi){
            const alto=d.flexibilizar?96:58;this.rect(48,y,1344,alto,'#fff4dc');
            this.texto('Casi elegible: falla una sola regla.',68,y+38,23,'#9a3412',700);
            if(d.flexibilizar)this.texto(this.wrap('Qué habría que flexibilizar: '+d.flexibilizar,110)[0],68,y+76,20,'#704512');
            y+=alto+14;
        }
        this.texto('Razones de descarte',48,y+28,24,'#16243b',700);
        this.dibujarLineas(48,y+48,1240,940-(y+48));
        this.button('dlg-entendido','Entendido',440,972,560,80,()=>this.cerrar(),true,true,{size:28}); // Único botón: no hay camino para contratar.
    }
    dibujarInforme() {
        const d=this.decision,url=this.api.urlInforme(d.decision_id);
        this.rect(0,0,1440,100,'#16243b',0);this.texto('Informe de decisión',48,62,34,'#ffffff',800);
        this.texto([d.decision_id,d.solicitud_id,d.nombre].filter(Boolean).join(' · '),480,62,24,'#c7d5ee',600);
        if(this.cargandoInforme)this.texto('Cargando el informe desde el backend…',48,180,26,'#175cde',700);
        else if(this.errorInforme){
            this.texto(`La decisión ${d.decision_id} quedó registrada, pero no se pudo cargar el informe.`,48,180,26,'#b42318',700);
            this.wrap(this.errorInforme,100).slice(0,3).forEach((l,i)=>this.texto(l,48,225+i*30,21,'#9a3412'));
            this.button('dlg-reintentar-informe','Reintentar',48,340,360,70,()=>this.abrirInforme(d),true,true,{size:26});
        } else this.dibujarLineas(48,124,1240,770);
        this.texto('Enlace: '+(url.length>130?url.slice(0,127)+'…':url),48,918,19,'#586a82',600);
        if(this.avisoEnlace)this.texto(this.avisoEnlace,48,946,19,'#15803d',700);
        this.button('dlg-abrir','Abrir en el navegador',48,960,520,80,()=>{this.abrirURL(url);this.avisoEnlace='Se abrió el informe en el navegador: allí está «Descargar PDF».';this.draw();},true,true,{size:26});
        this.button('dlg-copiar','Copiar enlace',590,960,380,80,()=>this.copiar(url),true,false,{size:26});
        this.button('dlg-cerrar','Cerrar',992,960,400,80,()=>this.cerrar(),true,false,{size:26});
    }
    dibujarDecidida() {
        const d=this.decision;
        this.rect(0,0,1440,104,'#15803d',0);this.texto('Decisión ya registrada',48,68,38,'#ffffff',800);
        [`La solicitud ${d.solicitud_id} ya tiene la decisión ${d.decision_id}.`,`Proveedor elegido por el funcionario: ${d.nombre}.`,`Motivo: ${d.justificacion}`,
         'Solo se registra una decisión por solicitud. Para decidir otra, haz una nueva consulta en la tablet.']
            .flatMap(t=>this.wrap(t,88)).slice(0,14).forEach((l,i)=>this.texto(l,48,180+i*42,27));
        this.button('dlg-ver-informe','Ver informe',48,972,660,80,()=>this.abrirInforme(d),true,true,{size:28});
        this.button('dlg-cerrar','Cerrar',732,972,660,80,()=>this.cerrar(),true,false,{size:28});
    }

    activate(uv) {const z=this.hit(uv);if(z)z.action();}
    key(event) {
        if(!this.abierto||event.ctrlKey||event.metaKey||event.altKey)return;
        const k=event.key;
        if(['Tab','Enter','Escape','Backspace','ArrowUp','ArrowDown','PageUp','PageDown'].includes(k)||(this.modo==='confirmar'&&k.length===1))event.preventDefault();
        if(k==='Tab'){if(this.zones.length){this.focus=(this.focus+(event.shiftKey?-1:1)+this.zones.length)%this.zones.length;this.keyboardFocus=true;this.draw();}return;}
        if(k==='Enter'){if(this.keyboardFocus&&!event.repeat)this.zones[this.focus]?.action();return;} // Solo el botón enfocado: escribir no confirma.
        if(k==='Escape'){if(!this.enviando)this.cerrar();return;}
        if(k==='ArrowDown'||k==='PageDown'){this.scroll(k==='PageDown'?10:2);return;}
        if(k==='ArrowUp'||k==='PageUp'){this.scroll(k==='PageUp'?-10:-2);return;}
        if(this.modo==='confirmar'){if(k==='Backspace')this.escribir('DEL');else if(k.length===1)this.escribir(k);}
    }
}
