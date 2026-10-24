const estado=document.getElementById('estado');
window.GatexDiagnostico?.registrar('Arranque JavaScript cargado; descargando módulos…');
function informar(error) {
    console.error(error);
    window.GatexDiagnostico?.error(error);
    estado.textContent='No se pudo cargar la aplicación: '+(error?.message||error||'error desconocido')+'. Comprueba que se hayan publicado js/ y assets/ completos.';
}
import('./main.js?v=QUEST-CAT-02').catch(informar);
