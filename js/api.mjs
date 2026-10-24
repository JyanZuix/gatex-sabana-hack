import { API_BASE, API_TIMEOUT_MS } from './config.js';
export class ErrorAPI extends Error {
    constructor(message,status=0,errores=[]) {super(message);this.name='ErrorAPI';this.status=status;this.errores=errores;}
}
export class API {
    constructor(base=API_BASE,fetchImpl=globalThis.fetch,timeout=API_TIMEOUT_MS) {this.base=base.replace(/\/$/,'');this.fetch=(...args)=>fetchImpl(...args);this.timeout=timeout;} // Envuelto: window.fetch llamado como método de otro objeto lanza "Illegal invocation".
    async llamar(method,path,body,signal) {
        let url;
        try {url=new URL(this.base+path);}catch{throw new ErrorAPI('Dirección del backend inválida. Revisa js/config.js.');}
        if(globalThis.location?.protocol==='https:'&&url.protocol!=='https:')throw new ErrorAPI(path+': conexión HTTP bloqueada desde HTTPS. Configura el túnel HTTPS.');
        const controller=new AbortController();
        const abort=()=>controller.abort();if(signal?.aborted)controller.abort();else signal?.addEventListener('abort',abort,{once:true});
        const timer=setTimeout(()=>controller.abort(),this.timeout);
        try {
            const response=await this.fetch(url.href,{method,headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});
            const raw=await response.text();let data;
            try {data=JSON.parse(raw);}catch{throw new ErrorAPI(path+': HTTP '+response.status+'; respuesta no JSON. Revisa el túnel y la ruta.',response.status);}
            if(!response.ok)throw new ErrorAPI(path+': HTTP '+response.status+' · '+(typeof data?.detalle==='string'?data.detalle:'El servidor rechazó la petición.'),response.status,Array.isArray(data?.errores)?data.errores:[]);
            return data;
        } catch(error) {
            if(signal?.aborted)throw new DOMException('Consulta cancelada','AbortError');
            if(error instanceof ErrorAPI)throw error;
            // Fetch no permite distinguir DNS, red o CORS cuando el navegador oculta la respuesta.
            throw new ErrorAPI(path+': '+(controller.signal.aborted?'tiempo de espera agotado. Reintenta.':'sin respuesta accesible. Revisa túnel, red o CORS; el navegador no distingue estas causas. ('+(error?.message||error)+')'));
        } finally {clearTimeout(timer);signal?.removeEventListener('abort',abort);}
    }
    salud(signal) {return this.llamar('GET','/salud',undefined,signal);}
    async catalogos(origen='',fecha='',signal) {
        const query=new URLSearchParams();if(origen)query.set('origen_id',origen);if(fecha)query.set('fecha_servicio',fecha);
        const ruta='/catalogos/formulario'+(query.size?'?'+query:'');
        const comprobarOpciones=(lista,nombre)=>{
            if(!Array.isArray(lista)||lista.some(o=>!o||!(typeof o.id==='string'||o.id===null)||typeof o.nombre!=='string'))throw new ErrorAPI(nombre+': catálogo con formato incompatible.');
        };
        const resultados=await Promise.allSettled([
            this.llamar('GET',ruta,undefined,signal).then(data=>{
                if(!data||typeof data.repositorio!=='string')throw new ErrorAPI(ruta+': falta repositorio en la respuesta.');
                for(const key of ['origenes','destinos','clientes','tipos_carga'])comprobarOpciones(data[key],ruta+' · '+key);
                if(!Array.isArray(data.rutas)||data.rutas.some(r=>typeof r?.origen_id!=='string'||typeof r?.destino_id!=='string')||!Array.isArray(data.proveedores)||data.proveedores.some(p=>typeof p?.proveedor_id!=='string'||typeof p?.nombre!=='string'))throw new ErrorAPI(ruta+': rutas o proveedores incompatibles.');
                return data;
            }),
            this.llamar('GET','/catalogos',undefined,signal).then(data=>{
                if(!Array.isArray(data?.tipos_vehiculo)||data.tipos_vehiculo.some(v=>typeof v?.tipo_vehiculo_id!=='string'||typeof v?.nombre!=='string'))throw new ErrorAPI('/catalogos: catálogo oficial de vehículos incompatible.');
                return data.tipos_vehiculo.map(v=>({id:v.tipo_vehiculo_id,nombre:v.nombre}));
            })
        ]);
        if(signal?.aborted)throw new DOMException('Consulta cancelada','AbortError');
        const [form,vehiculos]=resultados,base=form.status==='fulfilled'?form.value:{repositorio:'',origenes:[],destinos:[],rutas:[],clientes:[],tipos_carga:[],proveedores:[]};
        const errores=resultados.filter(r=>r.status==='rejected').map(r=>r.reason?.message||'Error de catálogo');
        return {...base,tipos_vehiculo:vehiculos.status==='fulfilled'?vehiculos.value:[],catalogosCompletos:errores.length===0,erroresCatalogos:errores,
            estadosCatalogos:{formulario:form.status==='fulfilled'?'disponible':'error',vehiculos:vehiculos.status==='fulfilled'?'disponible':'error'}};
    }
    async evaluar(datos,signal) {
        const data=await this.llamar('POST','/solicitudes/evaluar',datos,signal);
        if(!data.solicitud_id||!Array.isArray(data.candidatos)||!Array.isArray(data.cancelados)||!Array.isArray(data.casi_elegibles))throw new ErrorAPI('La evaluación llegó con un formato no reconocido. No se modificaron las tarjetas.');
        const number=n=>typeof n==='number'&&Number.isFinite(n);
        const text=s=>typeof s==='string';
        const list=values=>Array.isArray(values)&&values.every(text);
        for(const p of data.candidatos) {
            if(!text(p.proveedor_id)||!text(p.nombre)||!text(p.vehiculos?.tipo)||!number(p.vehiculos?.cantidad)||!number(p.costo_cop)||!number(p.profit?.esperado_cop)||!number(p.profit?.p10_cop)||!(p.profit?.margen_pct===null||number(p.profit?.margen_pct))||!number(p.tiempo_h?.p50)||!number(p.tiempo_h?.p90)||!number(p.tiempo_h?.prob_a_tiempo)||(p.prob_incidente!=null&&!number(p.prob_incidente))||!number(p.desempeno?.valor)||!number(p.confianza?.valor)||!text(p.confianza?.nivel)||!text(p.explicacion)||!list(p.riesgos)||!list(p.avisos))throw new ErrorAPI('Un candidato llegó incompleto. No se modificaron las tarjetas.');
        }
        for(const p of data.cancelados)if(!text(p.proveedor_id)||!text(p.nombre)||!Array.isArray(p.razones)||p.razones.some(r=>!text(r.mensaje)))throw new ErrorAPI('La lista de descartados llegó incompleta.');
        for(const p of data.casi_elegibles)if(!text(p.proveedor_id)||!text(p.nombre)||!text(p.razon?.mensaje)||!text(p.flexibilizar))throw new ErrorAPI('La lista de casi elegibles llegó incompleta.');
        return data;
    }
    // Contrato de POST /decisiones: solo estos cuatro campos. El backend guarda el snapshot y la hora.
    async decidir({solicitud_id,proveedor_id,justificacion,escenario_id=null},signal) {
        const data=await this.llamar('POST','/decisiones',{solicitud_id,proveedor_id,justificacion,escenario_id},signal);
        if(typeof data?.decision_id!=='string'||data.solicitud_id!==solicitud_id||data.proveedor_id!==proveedor_id||!Array.isArray(data.snapshot?.candidatos)||!Array.isArray(data.snapshot?.cancelados))
            throw new ErrorAPI('/decisiones: la respuesta no confirma el registro. Si reintentas y ya quedó guardada, el backend lo indicará.',200);
        return data;
    }
    async decision(decision_id,signal) {
        const data=await this.llamar('GET','/decisiones/'+encodeURIComponent(decision_id),undefined,signal);
        if(typeof data?.decision_id!=='string'||typeof data.solicitud_id!=='string'||typeof data.proveedor_id!=='string')throw new ErrorAPI('La decisión llegó con un formato no reconocido.');
        return data;
    }
    async informe(decision_id,signal) {
        const data=await this.llamar('GET','/decisiones/'+encodeURIComponent(decision_id)+'/informe?formato=json',undefined,signal);
        if(!Array.isArray(data?.secciones)||data.secciones.length!==8||data.secciones.some(s=>typeof s?.titulo!=='string'||!Array.isArray(s.bloques)))throw new ErrorAPI('El informe llegó con un formato no reconocido.');
        return data;
    }
    urlInforme(decision_id) {return this.base+'/decisiones/'+encodeURIComponent(decision_id)+'/informe?descargar=false';} // HTML imprimible con "Descargar PDF".
}

