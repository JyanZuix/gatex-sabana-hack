const estado=document.getElementById('estado');
function informar(error) {
    console.error(error);
    estado.textContent='No se pudo cargar la aplicación: '+(error?.message||error||'error desconocido')+'. Comprueba que se hayan publicado index.html, js/ y assets/ completos.';
}
window.addEventListener('error',event=>{if(!document.getElementById('inicio').hidden)informar(event.error||event.message);});
window.addEventListener('unhandledrejection',event=>{if(!document.getElementById('inicio').hidden)informar(event.reason);});
import('./main.js').catch(informar);
