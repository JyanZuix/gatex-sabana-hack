const estado=document.getElementById('estado');
window.GatexDiagnostico?.registrar('Arranque JavaScript cargado; descargando módulos…');
function informar(error) {
    console.error(error);
    window.GatexDiagnostico?.error(error);
    if(error?.code==='WEBGL_NO_DISPONIBLE'){estado.textContent=error.message;return;}
    estado.textContent='No se pudo cargar la aplicación: '+(error?.message||error||'error desconocido')+'. Comprueba que se hayan publicado js/ y assets/ completos.';
}
import('./main.js?v=QUEST-GL-03').catch(informar);
