// Un único renderizador exitoso. El segundo intento solo se permite si falla la creación del contexto.
export function crearRenderizador(THREE,{crearCanvas=()=>document.createElement('canvas'),registrar=()=>{}}={}) {
    const fallos=[];
    for(const antialias of [true,false]) {
        const canvas=crearCanvas();let detalle='';
        const falloContexto=event=>{detalle=String(event.statusMessage||'El navegador no informó el motivo.');};
        canvas.addEventListener('webglcontextcreationerror',falloContexto);
        registrar('Iniciando WebGL '+(antialias?'con antialiasing…':'sin antialiasing (segundo y último intento)…'));
        try {
            const renderer=new THREE.WebGLRenderer({canvas,antialias});
            registrar('WebGL iniciado '+(antialias?'con antialiasing.':'sin antialiasing.'));
            return renderer;
        } catch(error) {
            if(!/creating WebGL context/i.test(error?.message||''))throw error;
            const mensaje=error.message+(detalle?' · '+detalle:'');fallos.push(mensaje);registrar('Fallo WebGL: '+mensaje);
        } finally {canvas.removeEventListener('webglcontextcreationerror',falloContexto);}
    }
    const error=new Error('El navegador no pudo iniciar los gráficos WebGL, incluso sin antialiasing. Cierra otras pestañas 3D y reinicia el navegador o las gafas.');
    error.code='WEBGL_NO_DISPONIBLE';error.detalles=fallos;
    throw error;
}
