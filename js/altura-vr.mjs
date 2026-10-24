// Calibración al inicio: no fija ni sobrescribe la pose del visor en cada fotograma.
export class AlturaInicialVR {
    constructor(altura = 1.5) { this.altura = altura; this.reset(); }
    reset() { this.base = null; this.pendiente = false; }
    iniciar(base) { this.base = base; this.pendiente = true; }
    actualizar(frame, xr, Transform = globalThis.XRRigidTransform) {
        if (!this.pendiente || !frame || !this.base) return false;
        const pose = frame.getViewerPose(this.base);
        if (!pose) return false; // Espera seguimiento válido, por ejemplo si el visor aún no está puesto.
        const alturaReal = pose.transform.position.y;
        if (!Number.isFinite(alturaReal)) return false;
        const origen = new Transform({x:0,y:alturaReal-this.altura,z:0});
        xr.setReferenceSpace(this.base.getOffsetReferenceSpace(origen)); // Desplaza por igual ojos y mandos.
        this.pendiente = false; return true; // Solo una vez por sesión: conserva todos los movimientos posteriores.
    }
}
