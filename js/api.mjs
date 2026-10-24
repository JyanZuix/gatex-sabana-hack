import { API_BASE, API_TIMEOUT_MS } from './config.js';
export class ErrorAPI extends Error {
    constructor(message,status=0,errores=[]) {super(message);this.name='ErrorAPI';this.status=status;this.errores=errores;}
}
export class API {
    constructor(base=API_BASE,fetchImpl=globalThis.fetch,timeout=API_TIMEOUT_MS) {this.base=base.replace(/\/$/,'');this.fetch=fetchImpl;this.timeout=timeout;}
    async llamar(method,path,body,signal) {
        const controller=new AbortController();
        const abort=()=>controller.abort();if(signal?.aborted)controller.abort();else signal?.addEventListener('abort',abort,{once:true});
        const timer=setTimeout(()=>controller.abort(new Error('Tiempo de espera agotado')),this.timeout);
        try {
            const response=await this.fetch(this.base+path,{method,headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});
            const raw=await response.text();let data;
            try {data=JSON.parse(raw);}catch{throw new ErrorAPI('El servidor no devolvió JSON. Revisa que la dirección del backend siga vigente.',response.status);}
            if(!response.ok)throw new ErrorAPI(typeof data.detalle==='string'?data.detalle:'El servidor rechazó la petición.',response.status,Array.isArray(data.errores)?data.errores:[]);
            return data;
        } catch(error) {
            if(signal?.aborted)throw new DOMException('Consulta cancelada','AbortError');
            if(error instanceof ErrorAPI)throw error;
            throw new ErrorAPI(controller.signal.aborted?'La petición agotó su tiempo de espera. Puedes reintentar.':'No se pudo conectar con el backend. Comprueba la conexión y la dirección del servidor.');
        } finally {clearTimeout(timer);signal?.removeEventListener('abort',abort);}
    }
    salud(signal) {return this.llamar('GET','/salud',undefined,signal);}
    async catalogos(origen='',fecha='',signal) {
        const query=new URLSearchParams();if(origen)query.set('origen_id',origen);if(fecha)query.set('fecha_servicio',fecha);
        const [formulario,oficiales]=await Promise.all([
            this.llamar('GET','/catalogos/formulario'+(query.size?'?'+query:''),undefined,signal),
            this.llamar('GET','/catalogos',undefined,signal)
        ]);
        if(!Array.isArray(oficiales?.tipos_vehiculo))throw new ErrorAPI('El catálogo oficial de vehículos llegó incompleto.');
        return {...formulario,tipos_vehiculo:oficiales.tipos_vehiculo.map(v=>({id:v.tipo_vehiculo_id,nombre:v.nombre}))}; // Catálogo oficial: el backend define qué vehículos siguen vigentes.
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
}

