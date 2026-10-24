// Asociación por nombre validado contra el catálogo de la API; nunca por posición ni número de ID.
export const TARJETAS_PROVEEDOR = [
 ['Tarjeta1','Transportes Andinos del Sur'],['Tarjeta2','Pacifíco Express Logística'],
 ['Tarjeta3','Carga segura del Valle'],['Tarjeta4','FríoCol Transportes'],
 ['Tarjeta5','Tractocargas del Caribe'],['Tarjeta6','Mulas de Oriente'],
 ['Tarjeta7','Transpesados de Colombia'],['Tarjeta8','Químicos y Carga Especial'],
 ['Tarjeta9','Ruta Express Antioquia'],['Tarjeta10','Transportes El Llano'],
 ['Tarjeta11','Integral Cargo SAS'],['Tarjeta12','Cargar Nacional TLC']
];
export const normalizarNombre=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
export function vincularProveedores(proveedores) {
    const porId=new Map(),errores=[];
    for(const [tarjeta,nombre] of TARJETAS_PROVEEDOR) {
        const matches=proveedores.filter(p=>normalizarNombre(p.nombre)===normalizarNombre(nombre));
        if(matches.length!==1){errores.push(tarjeta+': '+(matches.length?'nombre ambiguo':'no se encontró '+nombre));continue;}
        const proveedor=matches[0];if(porId.has(proveedor.proveedor_id)){errores.push('Identificador duplicado: '+proveedor.proveedor_id);continue;}
        porId.set(proveedor.proveedor_id,{tarjeta,nombre:proveedor.nombre});
    }
    for(const proveedor of proveedores)if(!porId.has(proveedor.proveedor_id))errores.push('Proveedor sin tarjeta: '+proveedor.nombre+' ('+proveedor.proveedor_id+')');
    return {porId,errores};
}
