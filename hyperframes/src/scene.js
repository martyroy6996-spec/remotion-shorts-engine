import * as THREE from "three";
import { gsap } from "gsap";

const stage = document.getElementById("stage");
const canvas = document.getElementById("scene");
const title = document.getElementById("topic");
const duration = Math.max(1, Number(stage?.dataset.duration || 30));

const renderer = new THREE.WebGLRenderer({
  canvas,
  alpha: true,
  antialias: true,
  powerPreference: "high-performance"
});
renderer.setPixelRatio(1);
renderer.setSize(1080, 1920, false);
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(39, 1080 / 1920, 0.1, 100);
camera.position.set(0, 0, 18);
scene.add(new THREE.AmbientLight(0xb9e9ff, 1.4));

const keyLight = new THREE.DirectionalLight(0x8bdfff, 4.2);
keyLight.position.set(-4, 7, 9);
scene.add(keyLight);

const rimLight = new THREE.PointLight(0xffc76b, 42, 24);
rimLight.position.set(5, -3, 6);
scene.add(rimLight);

const group = new THREE.Group();
group.position.set(2.8, 4.0, 0);
scene.add(group);

const core = new THREE.Mesh(
  new THREE.IcosahedronGeometry(1.55, 5),
  new THREE.MeshPhysicalMaterial({
    color: 0x72cfff,
    metalness: 0.78,
    roughness: 0.16,
    clearcoat: 1,
    clearcoatRoughness: 0.12,
    emissive: 0x062c4e,
    emissiveIntensity: 0.85
  })
);
group.add(core);

const wire = new THREE.Mesh(
  new THREE.IcosahedronGeometry(1.68, 2),
  new THREE.MeshBasicMaterial({
    color: 0xb7f0ff,
    wireframe: true,
    transparent: true,
    opacity: 0.25
  })
);
group.add(wire);

const ringA = new THREE.Mesh(
  new THREE.TorusGeometry(2.25, 0.035, 12, 180),
  new THREE.MeshStandardMaterial({
    color: 0xffcc78,
    metalness: 0.88,
    roughness: 0.23,
    emissive: 0x633a0c,
    emissiveIntensity: 0.3
  })
);
ringA.rotation.set(0.85, 0.2, 0.3);
group.add(ringA);

const ringB = new THREE.Mesh(
  new THREE.TorusGeometry(2.55, 0.018, 10, 180),
  new THREE.MeshBasicMaterial({ color: 0x66dfff, transparent: true, opacity: 0.72 })
);
ringB.rotation.set(1.2, 0.85, 0.2);
group.add(ringB);

const seeded = (n) => {
  const value = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return value - Math.floor(value);
};
const particleCount = 420;
const positions = new Float32Array(particleCount * 3);
for (let i = 0; i < particleCount; i++) {
  const radius = 2.8 + seeded(i + 1) * 4.5;
  const angle = seeded(i + 1001) * Math.PI * 2;
  positions[i * 3] = Math.cos(angle) * radius;
  positions[i * 3 + 1] = (seeded(i + 2001) - 0.5) * 8;
  positions[i * 3 + 2] = (seeded(i + 3001) - 0.5) * 5;
}
const particleGeometry = new THREE.BufferGeometry();
particleGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
const particles = new THREE.Points(
  particleGeometry,
  new THREE.PointsMaterial({
    color: 0xa7e8ff,
    size: 2.2,
    transparent: true,
    opacity: 0.52,
    sizeAttenuation: false
  })
);
scene.add(particles);

const grid = new THREE.GridHelper(18, 28, 0x3bc7ed, 0x244b62);
grid.position.set(0, -4.6, -3.5);
grid.material.transparent = true;
grid.material.opacity = 0.18;
scene.add(grid);

function draw(progress) {
  const t = Math.max(0, Math.min(1, progress));
  group.rotation.y = t * Math.PI * 2.7;
  group.rotation.x = Math.sin(t * Math.PI * 2) * 0.28;
  group.rotation.z = Math.cos(t * Math.PI * 2) * 0.10;
  group.position.y = 4.0 + Math.sin(t * Math.PI * 4) * 0.18;
  group.scale.setScalar(0.92 + Math.sin(t * Math.PI * 2) * 0.055);
  ringA.rotation.z = 0.3 + t * Math.PI * 1.8;
  ringB.rotation.x = 1.2 + t * Math.PI * 1.25;
  particles.rotation.y = -t * Math.PI * 0.35;
  particles.rotation.z = t * Math.PI * 0.16;
  rimLight.position.x = 5 + Math.sin(t * Math.PI * 2) * 2;
  renderer.render(scene, camera);
}

const playhead = { value: 0 };
const timeline = gsap.timeline({ paused: true });
timeline.to(playhead, {
  value: 1,
  duration,
  ease: "none",
  onUpdate: () => draw(playhead.value)
});
timeline.fromTo(
  title,
  { opacity: 0, x: -28 },
  { opacity: 1, x: 0, duration: 0.7, ease: "power3.out" },
  0.25
);
timeline.to(title, { opacity: 0.88, duration: 0.5 }, Math.max(0.8, duration - 1));

window.__timelines = window.__timelines || {};
window.__timelines.root = timeline;
draw(0);
