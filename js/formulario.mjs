import {normalizarNombre} from './proveedores.mjs';
export function numeroES(value) {
    const s=String(value??'').trim().replace(/\s/g,'');
    if(/^\d{1,3}(?:\.\d{3})+(?:,\d+)?$/.test(s))return Number(s.replace(/\./g,'').replace(',','.'));
    if(/^\d+(?:[.,]\d+)?$/.test(s))return Number(s.replace(',','.'));
    return NaN;
}
export function fechaValida(s) {
    if(!/^\d{4}-\d{2}-\d{2}$/.test(s||''))return false;
    const [y,m,d]=s.split('-').map(Number),date=new Date(Date.UTC(y,m-1,d));
    return date.getUTCFullYear()===y&&date.getUTCMonth()===m-1&&date.getUTCDate()===d;
}
export function crearSolicitud(values,catalogos) {
    const errores={};
    const clientes=catalogos.clientes.filter(c=>normalizarNombre(c.nombre)===normalizarNombre(values.cliente));
    if(clientes.length!==1)errores.cliente='Escribe el nombre de un cliente registrado. Puedes consultar el catálogo de clientes.';
    if(!catalogos.origenes.some(o=>o.id===values.origen))errores.origen='Selecciona un origen del catálogo.';
    if(!catalogos.destinos.some(o=>o.id===values.destino))errores.destino='Selecciona un destino disponible para el origen.';
    if(!catalogos.rutas.some(r=>r.origen_id===values.origen&&r.destino_id===values.destino))errores.destino='La ruta elegida no tiene cobertura registrada.';
    if(!catalogos.tipos_carga.some(c=>c.id===values.carga))errores.carga='Selecciona un tipo de carga.';
    if(values.vehiculo!==null&&!catalogos.tipos_vehiculo.some(v=>v.id===values.vehiculo))errores.vehiculo='Selecciona un vehículo del catálogo o la opción automática.';
    if(!fechaValida(values.fecha_servicio))errores.fecha_servicio='Utiliza una fecha válida AAAA-MM-DD.';
    const peso=numeroES(values.peso),plazo=numeroES(values.plazo_h),presupuesto=numeroES(values.presupuesto);
    if(!Number.isFinite(peso)||peso<=0)errores.peso='El peso en kg debe ser mayor que cero.';
    if(!Number.isFinite(plazo)||plazo<=0)errores.plazo_h='El plazo en horas debe ser mayor que cero.';
    if(!Number.isFinite(presupuesto)||presupuesto<0||!Number.isSafeInteger(presupuesto*1000))errores.presupuesto='Introduce un presupuesto en miles de COP que produzca pesos enteros.';
    if(Object.keys(errores).length)return {errores};
    return {errores:{},datos:{cliente_id:clientes[0].id,origen_id:values.origen,destino_id:values.destino,fecha_servicio:values.fecha_servicio,plazo_h:plazo,toneladas:peso/1000,presupuesto_cop:presupuesto*1000,tipo_carga:values.carga,tipo_vehiculo_id:values.vehiculo}};
}
export const CAMPOS_API={cliente_id:'cliente',origen_id:'origen',destino_id:'destino',fecha_servicio:'fecha_servicio',plazo_h:'plazo_h',toneladas:'peso',presupuesto_cop:'presupuesto',tipo_carga:'carga',tipo_vehiculo_id:'vehiculo'};
export class Consultas {
    constructor(api) {this.api=api;this.version=0;this.control=null;this.ocupado=false;}
    cancelar() {this.version++;this.control?.abort();this.control=null;this.ocupado=false;}
    async evaluar(datos) {
        if(this.ocupado)return null;
        const version=++this.version;this.control=new AbortController();this.ocupado=true;
        try {const result=await this.api.evaluar(datos,this.control.signal);return version===this.version?result:null;}
        catch(error) {if(version!==this.version||error.name==='AbortError')return null;throw error;}
        finally {if(version===this.version){this.ocupado=false;this.control=null;}}
    }
}
