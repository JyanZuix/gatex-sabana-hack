const estado = document.getElementById('estado'); // El mensaje también funciona si falla la descarga de Three.js.
import('./main.js').catch(error => {
    console.error(error);
    estado.textContent = 'No se pudo cargar la escena. Comprueba internet y el acceso a unpkg.com. Abre la página desde un servidor web, no con doble clic.';
});
