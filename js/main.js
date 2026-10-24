import * as THREE from 'three';
import { VRButton } from 'three/addons/webxr/VRButton.js';

// 1. Configuración básica de la escena
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111827);

const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 1.6, 3); // Altura de los ojos humanos (~1.6m)

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.xr.enabled = true; // Habilitar soporte WebXR para las Quest 3
document.body.appendChild(renderer.domElement);

// 2. Agregar botón nativo de VR ("Enter VR")
document.body.appendChild(VRButton.createButton(renderer));

// 3. Luz ambiental y direccional
const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
dirLight.position.set(5, 10, 5);
scene.add(dirLight);

// 4. Objeto temporal de prueba (un cubo que simula un paquete o pilar)
const geometry = new THREE.BoxGeometry(0.8, 0.8, 0.8);
const material = new THREE.MeshStandardMaterial({ color: 0x3b82f6, roughness: 0.3 });
const testBox = new THREE.Mesh(geometry, material);
testBox.position.set(0, 1.2, -2);
scene.add(testBox);

// Plano de suelo básico
const floorGeo = new THREE.PlaneGeometry(10, 10);
const floorMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.9 });
const floor = new THREE.Mesh(floorGeo, floorMat);
floor.rotation.x = -Math.PI / 2;
scene.add(floor);

// 5. Bucle de animación (necesario para renderizar y actualizar la vista VR)
renderer.setAnimationLoop(() => {
    testBox.rotation.y += 0.01;
    renderer.render(scene, camera);
});

// Ajuste responsivo si cambias el tamaño de ventana en el PC
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});