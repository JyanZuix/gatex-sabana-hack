# Tablet 30 % mayor y con inclinación de atril

Sustituye únicamente js/main.js por el archivo de esta entrega y recarga completamente la página. Conserva el resto del proyecto. Haz una copia de seguridad del main.js anterior.

La tablet aumenta un 30 % de forma uniforme: la pantalla pasa de 1.15 x 0.8625 m a 1.495 x 1.12125 m. El marco también aumenta. La proporción, el contenido del canvas, sus coordenadas UV y las zonas de interacción no cambian.

Después de orientar la tablet con la referencia de la vista del cono, se añade un giro de -45 grados en su X local: el borde superior se aleja del usuario y la pantalla queda orientada hacia arriba, como un atril. Son 45 grados respecto a la orientación que tenía frente a la vista del cono, no un giro de la cámara ni del escenario.

Se conserva el centro del grupo de la tablet, su descenso de 1 metro y su ubicación delante del punto de entrada. La inclinación y el tamaño se aplican sobre ese centro. Las esquinas y los bordes cambian de altura por el giro y el aumento de tamaño.

La orientación se reinicia con lookAt y la escala se asigna a 1.3 en cada centrado: no acumulan giros ni aumentos al entrar/salir de VR. No cambia la cámara, el escenario Gatex3, la referencia Usuario, el fondo sin niebla, el formulario, los desplegables ni el teclado.

Solo se cambiaron las líneas de orientación/tamaño dentro de centrarTablet. Se verificó que el resto del código permanece idéntico y que pasa node --check. Falta revisar visualmente en las Quest 3 la inclinación, la legibilidad y la selección con los mandos.

La carpeta original de OneDrive no se modificó; esta entrega contiene el archivo listo para copiar.
