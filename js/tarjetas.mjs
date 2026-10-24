import {ANIMACION_TARJETAS} from './config.js';
import {TARJETAS_PROVEEDOR} from './proveedores.mjs';
// Estados que se pueden seleccionar: un candidato abre la confirmación; un descartado o casi elegible, la alerta.
const SELECCIONABLES=new Set(['candidato','cancelado','casi']);
const SIN_APARIENCIA={preparar(){},aplicar(){}}; // Las pruebas no necesitan Three.js.
export class AnimadorTarjetas {
    constructor(modelo,{descenso_m=ANIMACION_TARJETAS.descenso_m,duracion_ms=ANIMACION_TARJETAS.duracion_ms,apariencia=SIN_APARIENCIA}={}) {
        this.items=new Map();this.animaciones=new Map();this.duracion=duracion_ms;this.descenso=descenso_m;
        this.apariencia=apariencia;this.hover=new Set();this.seleccionada=null;this.elegida=null;
        for(const [nombre] of TARJETAS_PROVEEDOR) {
            const matches=[];modelo.traverse(o=>{if(o.name===nombre)matches.push(o);});
            if(matches.length!==1)throw new Error('Debe existir una sola '+nombre+'; encontradas: '+matches.length);
            const node=matches[0];this.items.set(nombre,{node,original:node.position.clone(),estado:'neutral',proveedor_id:null});
        }
        for(const item of this.items.values())this.apariencia.preparar(item.node);
        this.refrescar();
    }
    mover(item,destino) {this.animaciones.set(item.node.name,{item,desde:item.node.position.clone(),hasta:destino.clone(),inicio:null});}
    restaurar() {
        this.animaciones.clear();
        for(const item of this.items.values()){item.estado='neutral';item.proveedor_id=null;this.mover(item,item.original);}
        this.limpiarMarcas();
    }
    aplicar(evaluacion,vinculos,casiPolicy) {
        if(!['panel','arriba'].includes(casiPolicy))throw new Error('Falta definir cómo presentar los casi elegibles.');
        const porProveedor=new Map();
        for(const [lista,estado] of [[evaluacion.cancelados,'cancelado'],[evaluacion.casi_elegibles,'casi'],[evaluacion.candidatos,'candidato']]) {
            for(const proveedor of lista) {
                const binding=vinculos.get(proveedor.proveedor_id);
                if(!binding||!this.items.has(binding.tarjeta))throw new Error('No hay asociación verificada para '+proveedor.proveedor_id+'. No se modificaron las tarjetas.');
                const anterior=porProveedor.get(proveedor.proveedor_id);
                if(anterior&&(anterior.estado===estado||anterior.estado==='candidato'||estado==='candidato'))throw new Error('La API clasificó un proveedor en grupos incompatibles.');
                porProveedor.set(proveedor.proveedor_id,{...binding,estado});
            }
        }
        const clasificadas=new Set([...porProveedor.values()].map(p=>p.tarjeta));
        const faltantes=[...this.items.keys()].filter(key=>!clasificadas.has(key));
        if(faltantes.length)throw new Error('La API no clasificó estas tarjetas: '+faltantes.join(', ')+'. No se modificaron las tarjetas.');
        this.animaciones.clear();
        for(const item of this.items.values()){item.estado='sin_clasificar';item.proveedor_id=null;this.mover(item,item.original);}
        for(const [id,entry] of porProveedor) {
            const item=this.items.get(entry.tarjeta);item.estado=entry.estado;item.proveedor_id=id;
            const target=item.original.clone();
            if(entry.estado==='cancelado'||(entry.estado==='casi'&&casiPolicy==='panel'))target.y-=this.descenso;
            this.mover(item,target);
        }
        this.limpiarMarcas();
    }
    actualizar(tiempo) {
        for(const [key,animation] of this.animaciones){
            if(animation.inicio===null)animation.inicio=tiempo;
            const p=Math.min(1,Math.max(0,(tiempo-animation.inicio)/this.duracion)),ease=1-Math.pow(1-p,3);
            animation.item.node.position.copy(animation.desde).lerp(animation.hasta,ease);
            if(p===1)this.animaciones.delete(key);
        }
    }
    esSeleccionable(item) {return SELECCIONABLES.has(item?.estado);}
    seleccionables() {return [...this.items.values()].filter(i=>this.esSeleccionable(i)).map(i=>i.node);}
    candidatas() {return [...this.items.values()].filter(i=>i.estado==='candidato').map(i=>i.node);}
    desdeObjeto(object) {
        for(let current=object;current;current=current.parent){const item=this.items.get(current.name);if(item)return item;}
        return null;
    }
    // Retroalimentación visual: apuntar (hover), seleccionar y el proveedor que eligió el funcionario.
    resaltar(nombres) {const next=new Set(nombres);if([...next].sort().join('|')===[...this.hover].sort().join('|'))return;this.hover=next;this.refrescar();}
    seleccionar(nombre) {if(this.seleccionada===nombre)return;this.seleccionada=nombre;this.refrescar();}
    marcarElegida(proveedor_id) {
        const item=[...this.items.values()].find(i=>i.proveedor_id===proveedor_id&&i.estado==='candidato');
        this.elegida=item?item.node.name:null;this.refrescar();return !!item;
    }
    limpiarMarcas() {this.hover=new Set();this.seleccionada=null;this.elegida=null;this.refrescar();}
    refrescar() {
        for(const [nombre,item] of this.items)this.apariencia.aplicar(item.node,{estado:item.estado,hover:this.hover.has(nombre),seleccionada:this.seleccionada===nombre,elegida:this.elegida===nombre});
    }
}
