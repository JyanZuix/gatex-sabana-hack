// Operaciones de poses rígidas independientes de Three.js: posición y cuaternión normalizado.
function producto(a,b) {
    return {x:a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,y:a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,z:a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,w:a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z};
}
function girar(v,q) {
    const t=producto(producto(q,{x:v.x,y:v.y,z:v.z,w:0}),{x:-q.x,y:-q.y,z:-q.z,w:q.w});
    return {x:t.x,y:t.y,z:t.z};
}
export function invertirPose(pose) {
    const q=pose.orientation,orientation={x:-q.x,y:-q.y,z:-q.z,w:q.w};
    return {position:girar({x:-pose.position.x,y:-pose.position.y,z:-pose.position.z},orientation),orientation};
}
export function componerPoses(a,b) {
    const t=girar(b.position,a.orientation);
    return {position:{x:a.position.x+t.x,y:a.position.y+t.y,z:a.position.z+t.z},orientation:producto(a.orientation,b.orientation)};
}
export class EntradaVR {
    constructor() {this.destino=null;this.reset();}
    configurar(destino) {this.destino=destino;}
    reset() {this.base=null;this.pendiente=false;} // Conserva el destino del modelo para la siguiente sesión.
    iniciar(base) {if(!this.destino)throw new Error('Falta la referencia Usuario.');this.base=base;this.pendiente=true;}
    actualizar(frame,xr,Transform=globalThis.XRRigidTransform) {
        if(!this.pendiente||!frame||!this.base)return false;
        const pose=frame.getViewerPose(this.base);
        if(!pose)return false; // Espera seguimiento válido antes de fijar la entrada.
        const offset=componerPoses(pose.transform,invertirPose(this.destino)); // Nuevo espacio = pose real inicial × inversa del destino virtual.
        xr.setReferenceSpace(this.base.getOffsetReferenceSpace(new Transform(offset.position,offset.orientation)));
        this.pendiente=false;return true; // Una vez por sesión; no bloquea ni persigue al visor.
    }
}
