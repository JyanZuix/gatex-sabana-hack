import {ANIMACION_TARJETAS} from './config.js';
import {TARJETAS_PROVEEDOR} from './proveedores.mjs';
export class AnimadorTarjetas {
    constructor(modelo,{descenso_m=ANIMACION_TARJETAS.descenso_m,duracion_ms=ANIMACION_TARJETAS.duracion_ms}={}) {
        this.items=new Map();this.animaciones=new Map();this.duracion=duracion_ms;this.descenso=descenso_m;
        for(const [nombre] of TARJETAS_PROVEEDOR) {
            const matches=[];modelo.traverse(o=>{if(o.name===nombre)matches.push(o);});
            if(matches.length!==1)throw new Error('Debe existir una sola '+nombre+'; encontradas: '+matches.length);
            const node=matches[0];this.items.set(nombre,{node,original:node.position.clone(),estado:'neutral',proveedor_id:null,puesto:null,top:false});
        }
    }
    mover(item,destino) {this.animaciones.set(item.node.name,{item,desde:item.node.position.clone(),hasta:destino.clone(),inicio:null});}
    restaurar() {
        this.animaciones.clear();
        for(const item of this.items.values()){item.estado='neutral';item.proveedor_id=null;item.puesto=null;item.top=false;this.mover(item,item.original);}
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
                porProveedor.set(proveedor.proveedor_id,{...binding,estado,puesto:proveedor.puesto??null,top:estado==='candidato'&&proveedor.top===true});
            }
        }
        const clasificadas=new Set([...porProveedor.values()].map(p=>p.tarjeta));
        const faltantes=[...this.items.keys()].filter(key=>!clasificadas.has(key));
        if(faltantes.length)throw new Error('La API no clasificó estas tarjetas: '+faltantes.join(', ')+'. No se modificaron las tarjetas.');
        this.animaciones.clear();
        for(const item of this.items.values()){item.estado='sin_clasificar';item.proveedor_id=null;item.puesto=null;item.top=false;this.mover(item,item.original);}
        for(const [id,entry] of porProveedor) {
            const item=this.items.get(entry.tarjeta);item.estado=entry.estado;item.proveedor_id=id;item.puesto=entry.puesto;item.top=entry.top;
            const target=item.original.clone();
            // Top N sugerido arriba; los demás candidatos, a media altura y seleccionables; descartados abajo.
            if(entry.estado==='cancelado'||(entry.estado==='casi'&&casiPolicy==='panel'))target.y-=this.descenso;
            else if(entry.estado==='candidato'&&!entry.top)target.y-=this.descenso/2;
            this.mover(item,target);
        }
    }
    actualizar(tiempo) {
        for(const [key,animation] of this.animaciones){
            if(animation.inicio===null)animation.inicio=tiempo;
            const p=Math.min(1,Math.max(0,(tiempo-animation.inicio)/this.duracion)),ease=1-Math.pow(1-p,3);
            animation.item.node.position.copy(animation.desde).lerp(animation.hasta,ease);
            if(p===1)this.animaciones.delete(key);
        }
    }
    seleccionables() {return [...this.items.values()].filter(i=>i.estado==='candidato').map(i=>i.node);}
    desdeObjeto(object) {
        for(let current=object;current;current=current.parent){const item=this.items.get(current.name);if(item)return item;}
        return null;
    }
}


