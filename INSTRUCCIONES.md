# Nuevo escenario Gatex1

## Instalar en tu proyecto
Guarda una copia de seguridad de js/main.js. Copia estos archivos de la entrega a tu proyecto:
- js/main.js: sustituye el actual.
- js/escenario.js: archivo nuevo.
- assets/Gatex1.glb: archivo nuevo.

Conserva index.html, inicio.js, altura-vr.mjs, catalogos.js, desplegables.mjs y los demás archivos del proyecto. No es necesario borrar los GLB anteriores: ya no se importan ni se cargan. Recarga completamente la página después de copiar los archivos. Esta sesión preparó la entrega dentro de outputs, sin modificar la carpeta original de OneDrive.

## Modelo
El archivo contiene 10 nodos: Tarjeta1 a Tarjeta5, Flecha, Barco, Auto, Signos y Cylinder. No contiene SoporteTablet ni AnclajeTablet. Todos los recursos están incluidos en el binario; no requiere texturas externas.

Se carga exclusivamente assets/Gatex1.glb, mediante GLTFLoader, y se añade su escena principal sin cambiar transformaciones, escalas, materiales, nombres ni jerarquía. No se normaliza ni se centra el modelo. El archivo original permanece intacto y su copia entregada coincide byte a byte.

La versión actual del proyecto ya no estaba cargando un GLB. Esta integración no vuelve a importar modelo-tablet.js ni Gatex.glb. El nuevo cargador mantiene una única instancia de escenario por escena: si vuelve a cargarse con éxito, retira la instancia anterior gestionada por él antes de añadir la nueva.

## Tablet
No cambia su geometría, tamaño, posición, centrado, interfaz, formulario, teclado, desplegables, selección con mandos ni su calibración inicial a 1,50 m. Se verificó por comparación literal que el bloque de código de tablet/formulario/sesión y el bucle de calibración son idénticos a los de tu main.js actual.

## Color del entorno
Se utiliza azul oscuro #102a4c para el suelo externo al GLB y para la mitad inferior del fondo. La parte superior del fondo continúa en gris claro #e9edf2. La cuadrícula exterior utiliza tonos azules. Se conserva la niebla gris y las luces existentes.

No se recolorea ninguna malla del GLB: la plataforma Cylinder conserva su material original y puede verse gris sobre el suelo azul. Esto respeta la condición de mantener los materiales del nuevo modelo. No se alteró el modelo para ocultarla o pintarla.

## Errores
Si falta Gatex1.glb, falla la carga o no tiene una escena principal, se muestra un mensaje explícito en el inicio y se mantiene deshabilitada la entrada. No se utiliza otro modelo como sustituto. Si se detectan SoporteTablet o AnclajeTablet en una futura sustitución del archivo, se rechaza la carga con un mensaje que solicita confirmación antes de mostrarlos.

## Posiciones originales
Las cinco tarjetas están aproximadamente a y=4,89 m. Flecha, Barco, Auto y Signos están a distancias y alturas mayores (varios entre y=10 y 13,5 m y x=22 a 25 m). No se movieron para acercarlos a la cámara ni a la tablet. La niebla y el alcance de cámara existentes pueden limitar la visibilidad de los objetos lejanos. Cualquier ajuste de esas posiciones, de cámara o de tablet requiere tu confirmación.

## Ejecutar
Desde la carpeta completa del proyecto, con Python instalado:

    py -m http.server 8000

En Ubuntu/WSL:

    python3 -m http.server 8000 --bind 0.0.0.0

Prueba en PC con http://localhost:8000/?preview=1. Para Quest 3 utiliza una dirección HTTPS válida sin preview=1. No abras index.html mediante doble clic. La dependencia Three.js sigue descargándose desde unpkg.com.

## Verificación
Pasaron node --check, las pruebas de rutas, conservación de datos del modelo, sustitución sin duplicados y propagación de errores con un cargador simulado. Se verificó la igualdad binaria del GLB original y el entregado, su cabecera, sus 10 nodos y la ausencia de recursos externos. Las pruebas de regresión de formulario y desplegables también pasaron.

No se ha realizado renderizado WebGL de esta entrega ni prueba física en Quest 3. Falta comprobar colores, encuadre con las posiciones originales, legibilidad, fluidez, entrada/salida y selección con ambos mandos. El azul no altera los materiales propios del GLB.
