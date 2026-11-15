import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { CATEGORIES, createScenario, createSimulation, toggle, advance } from './simulation.mjs';

const $ = id => document.getElementById(id);
const viewport = $('viewport');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xe9efec);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'low-power' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.6));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.domElement.setAttribute('role', 'img');
renderer.domElement.setAttribute('aria-label', '模拟房间：机器人沿预设路线清理三类污渍。可拖动旋转和滚轮缩放，也可通过视角、缩放按钮和右侧目标列表操作。');
viewport.prepend(renderer.domElement);

const camera = new THREE.PerspectiveCamera(39, 1, 0.1, 100);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.09;
controls.minDistance = 7;
controls.maxDistance = 32;
controls.minPolarAngle = 0.005;
controls.maxPolarAngle = Math.PI / 2.25;
controls.enablePan = false;
controls.target.set(0, 0.05, 0);
let view = 'perspective';

scene.add(new THREE.HemisphereLight(0xffffff, 0xa4b4a5, 1.8));
const sunlight = new THREE.DirectionalLight(0xfff8ed, 2.4);
sunlight.position.set(-3, 10, 6);
sunlight.castShadow = true;
sunlight.shadow.mapSize.set(2048, 2048);
Object.assign(sunlight.shadow.camera, { left: -7, right: 7, top: 7, bottom: -7, near: 1, far: 25 });
sunlight.shadow.normalBias = 0.035;
sunlight.shadow.bias = -0.0001;
sunlight.shadow.radius = 4;
scene.add(sunlight);

function mesh(geometry, color, options = {}) {
  const item = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: 0.72, ...options }));
  item.castShadow = true;
  item.receiveShadow = true;
  return item;
}
function box(parent, x, y, z, sx, sy, sz, color, options) {
  const item = mesh(new THREE.BoxGeometry(sx, sy, sz), color, options);
  item.position.set(x, y, z);
  parent.add(item);
  return item;
}
function cylinder(parent, x, y, z, top, bottom, height, color, segments = 40, options) {
  const item = mesh(new THREE.CylinderGeometry(top, bottom, height, segments), color, options);
  item.position.set(x, y, z);
  parent.add(item);
  return item;
}

// A stylized room. Its dimensions, furniture, and robot are illustrative assets.
const room = new THREE.Group();
scene.add(room);
box(room, 0, -0.15, 0, 8.15, 0.25, 6.15, 0xc3d0c6);
box(room, 0, -0.025, 0, 8, 0.08, 6, 0xf2efe5);
box(room, 0, 0.27, -3.03, 8.12, 0.62, 0.12, 0xe2e8df);
box(room, -4.03, 0.27, 0, 0.12, 0.62, 6.12, 0xe2e8df);
box(room, 0, 0.59, -3.03, 8.13, 0.035, 0.13, 0xf4f4eb);
box(room, -4.03, 0.59, 0, 0.13, 0.035, 6.13, 0xf4f4eb);
const grid = [];
for (let x = -4; x <= 4; x++) grid.push(x, 0.018, -3, x, 0.018, 3);
for (let z = -3; z <= 3; z++) grid.push(-4, 0.018, z, 4, 0.018, z);
const gridGeometry = new THREE.BufferGeometry();
gridGeometry.setAttribute('position', new THREE.Float32BufferAttribute(grid, 3));
room.add(new THREE.LineSegments(gridGeometry, new THREE.LineBasicMaterial({ color: 0xcdd5cb, transparent: true, opacity: 0.53 })));

const sofa = new THREE.Group();
sofa.position.set(1.5, 0, -2.25);
room.add(sofa);
for (const x of [-1.25, 1.25]) for (const z of [-0.34, 0.34]) box(sofa, x, 0.09, z, 0.11, 0.18, 0.11, 0x758173);
box(sofa, 0, 0.29, 0, 3.15, 0.30, 1.04, 0xb9c4b9);
box(sofa, 0, 0.65, -0.39, 3.15, 0.59, 0.23, 0xb7c3b6);
for (const x of [-1.47, 1.47]) box(sofa, x, 0.56, 0.01, 0.23, 0.39, 1.04, 0xb7c3b6);
for (const x of [-0.94, 0, 0.94]) box(sofa, x, 0.51, 0.10, 0.89, 0.20, 0.76, 0xd1d8ca);
const cushion = box(sofa, -0.98, 0.77, -0.13, 0.43, 0.44, 0.18, 0x95aa94);
cushion.rotation.z = -0.18;
const table = new THREE.Group();
table.position.set(-1.6, 0, -2.25);
room.add(table);
cylinder(table, 0, 0.38, 0, 0.045, 0.055, 0.72, 0xa8ab97, 16);
cylinder(table, 0, 0.73, 0, 0.46, 0.46, 0.08, 0xd9ccb2);
cylinder(table, 0, 0.06, 0, 0.26, 0.27, 0.06, 0xc2bca7);
cylinder(table, 0.08, 0.82, 0.03, 0.085, 0.07, 0.13, 0xe5e4d6, 20);
const plant = new THREE.Group();
plant.position.set(-3.3, 0, -2.3);
room.add(plant);
cylinder(plant, 0, 0.20, 0, 0.24, 0.17, 0.40, 0xdbd1ba, 24);
cylinder(plant, 0, 0.40, 0, 0.21, 0.21, 0.02, 0x777b60, 24);
for (let i = 0; i < 9; i++) {
  const a = i * 2.4, height = 0.75 + (i % 3) * 0.18;
  const leaf = mesh(new THREE.SphereGeometry(1, 12, 8), i % 2 ? 0x678a65 : 0x8aa47c);
  leaf.scale.set(0.12, 0.39, 0.09);
  leaf.position.set(Math.cos(a) * 0.18, height, Math.sin(a) * 0.18);
  leaf.rotation.set(Math.sin(a) * 0.55, a, Math.cos(a) * 0.55);
  plant.add(leaf);
}

const dock = new THREE.Group();
dock.position.set(-3.2, 0, 2.72);
room.add(dock);
box(dock, 0, 0.17, 0, 0.72, 0.34, 0.22, 0x3d5951);
box(dock, 0, 0.03, -0.17, 0.69, 0.05, 0.46, 0x74877c);
box(dock, 0, 0.29, -0.116, 0.14, 0.025, 0.01, 0x9ecab3, { emissive: 0x62896f, emissiveIntensity: 0.35 });

const robot = new THREE.Group();
scene.add(robot);
cylinder(robot, 0, 0.105, 0, 0.32, 0.32, 0.17, 0x3d4d49);
cylinder(robot, 0, 0.175, 0, 0.315, 0.325, 0.10, 0xe9eee7, 64, { roughness: 0.35 });
cylinder(robot, 0, 0.233, 0, 0.27, 0.29, 0.025, 0xf7f8f2, 64);
cylinder(robot, 0, 0.267, 0.065, 0.09, 0.10, 0.065, 0x597c6f, 32, { roughness: 0.42 });
cylinder(robot, 0, 0.304, 0.065, 0.072, 0.08, 0.015, 0xd8e3d8, 32);
box(robot, 0, 0.255, -0.12, 0.045, 0.008, 0.065, 0x4f8a6b);
box(robot, 0, 0.145, -0.299, 0.20, 0.055, 0.028, 0x263b35, { roughness: 0.25 });
const brushes = [];
for (const x of [-0.245, 0.245]) {
  const brush = new THREE.Group();
  brush.position.set(x, 0.035, -0.15);
  for (let i = 0; i < 3; i++) {
    const bristle = box(brush, 0, 0, 0, 0.24, 0.014, 0.022, 0x7b8b72);
    bristle.rotation.y = i * Math.PI * 2 / 3;
  }
  robot.add(brush);
  brushes.push(brush);
}
const robotRing = new THREE.Mesh(new THREE.RingGeometry(0.38, 0.40, 64), new THREE.MeshBasicMaterial({ color: 0x64a584, transparent: true, opacity: 0.45, side: THREE.DoubleSide }));
robotRing.rotation.x = -Math.PI / 2;
robotRing.position.y = 0.025;
robot.add(robotRing);

const routeGroup = new THREE.Group();
scene.add(routeGroup);
let plannedRoute;
const tracePositions = new Float32Array(4000 * 3);
const traceGeometry = new THREE.BufferGeometry();
traceGeometry.setAttribute('position', new THREE.BufferAttribute(tracePositions, 3));
traceGeometry.setDrawRange(0, 0);
const trace = new THREE.Line(traceGeometry, new THREE.LineBasicMaterial({ color: 0x53846b }));
trace.frustumCulled = false;
routeGroup.add(trace);
let traceCount = 0, lastTrace = null;

let seed = 9, scenario = createScenario(seed), sim = createSimulation(scenario), selected = '01';
let targetsGroup = new THREE.Group();
scene.add(targetsGroup);
const targetObjects = new Map(), targetLabels = new Map(), targetButtons = new Map();
const selectionRing = new THREE.Mesh(new THREE.RingGeometry(0.35, 0.37, 64), new THREE.MeshBasicMaterial({ color: 0x53876a, transparent: true, opacity: 0.78, side: THREE.DoubleSide }));
selectionRing.rotation.x = -Math.PI / 2;
scene.add(selectionRing);

function disposeGroup(group) {
  group.traverse(item => {
    if (item.geometry) item.geometry.dispose();
    if (item.material) for (const m of Array.isArray(item.material) ? item.material : [item.material]) m.dispose();
  });
  scene.remove(group);
}

function makeStain(target) {
  const category = CATEGORIES[target.kind], group = new THREE.Group();
  group.position.set(target.x, 0.027, -target.y);
  const shape = new THREE.Shape();
  for (let i = 0; i < 28; i++) {
    const a = i / 28 * Math.PI * 2;
    const r = category.radius * (1 + 0.16 * Math.sin(a * 3 + target.variation * 4) + 0.10 * Math.cos(a * 5));
    const x = Math.cos(a) * r, y = Math.sin(a) * r * (target.kind === 'water' ? 0.73 : 0.85);
    if (i === 0) shape.moveTo(x, y); else shape.lineTo(x, y);
  }
  shape.closePath();
  const stain = mesh(new THREE.ShapeGeometry(shape), category.color, { transparent: true, opacity: target.kind === 'water' ? 0.75 : 0.55, roughness: target.kind === 'water' ? 0.22 : 0.95, side: THREE.DoubleSide });
  stain.rotation.x = -Math.PI / 2;
  stain.castShadow = false;
  group.add(stain);
  if (target.kind !== 'water') {
    for (let i = 0; i < 7; i++) {
      const a = i * 2.4 + target.variation, r = category.radius * (i % 3 + 1) / 4;
      const grain = mesh(new THREE.IcosahedronGeometry(target.kind === 'bigdirt' ? 0.055 : 0.022, 0), category.color);
      grain.position.set(Math.cos(a) * r, target.kind === 'bigdirt' ? 0.035 : 0.012, Math.sin(a) * r);
      grain.scale.set(1, 0.60, 0.8);
      group.add(grain);
    }
  } else {
    const shine = mesh(new THREE.CircleGeometry(0.06, 20), 0xc2dae0, { transparent: true, opacity: 0.55 });
    shine.rotation.x = -Math.PI / 2;
    shine.position.set(-0.055, 0.003, 0.035);
    shine.scale.y = 0.36;
    shine.castShadow = false;
    group.add(shine);
  }
  group.traverse(child => { child.userData.targetId = target.id; });
  return group;
}

function buildTargets() {
  disposeGroup(targetsGroup);
  targetsGroup = new THREE.Group();
  scene.add(targetsGroup);
  targetObjects.clear(); targetLabels.clear(); targetButtons.clear();
  $('labels').replaceChildren(); $('target-list').replaceChildren();
  for (const target of scenario.targets) {
    const category = CATEGORIES[target.kind];
    const object = makeStain(target);
    targetObjects.set(target.id, object);
    targetsGroup.add(object);
    const label = document.createElement('span');
    label.className = 'target-label'; label.textContent = target.id;
    $('labels').append(label); targetLabels.set(target.id, label);
    const button = document.createElement('button');
    button.className = 'target-item';
    button.setAttribute('aria-pressed', 'false');
    button.innerHTML = `<span class="target-id">${target.id}</span><i class="swatch ${target.kind}" aria-hidden="true"></i><span>${category.label}</span><span class="target-state">待清理</span>`;
    button.addEventListener('click', () => selectTarget(target.id));
    $('target-list').append(button); targetButtons.set(target.id, button);
  }
  selectTarget(selected);
}

function buildRoute() {
  if (plannedRoute) {
    routeGroup.remove(plannedRoute);
    plannedRoute.geometry.dispose(); plannedRoute.material.dispose();
  }
  const points = scenario.route.map(p => new THREE.Vector3(p.x, 0.035, -p.y));
  plannedRoute = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineDashedMaterial({ color: 0x86a28b, dashSize: 0.10, gapSize: 0.10, transparent: true, opacity: 0.60 }));
  plannedRoute.computeLineDistances();
  routeGroup.add(plannedRoute);
  traceCount = 0; lastTrace = null;
  traceGeometry.setDrawRange(0, 0);
  addTrace();
}

function addTrace() {
  if (lastTrace && Math.hypot(sim.x - lastTrace.x, sim.y - lastTrace.y) < 0.045 && sim.status !== 'complete') return;
  if (traceCount >= 4000) return;
  tracePositions.set([sim.x, 0.044, -sim.y], traceCount * 3);
  traceCount++;
  traceGeometry.attributes.position.needsUpdate = true;
  traceGeometry.setDrawRange(0, traceCount);
  lastTrace = { x: sim.x, y: sim.y };
}

function text(id, value) { if ($(id).textContent !== value) $(id).textContent = value; }
function selectTarget(id) {
  selected = id;
  const target = scenario.targets.find(t => t.id === id);
  if (!target) return;
  selectionRing.position.set(target.x, 0.046, -target.y);
  for (const [key, button] of targetButtons) button.setAttribute('aria-pressed', String(key === id));
  updateUI();
}

function updateUI() {
  const count = sim.cleaned.size;
  $('progress-value').innerHTML = `${Math.round(count / scenario.targets.length * 100)}<span>%</span>`;
  text('cleaned-count', String(count)); text('total-count', String(scenario.targets.length));
  $('progress').max = scenario.targets.length; $('progress').value = count;
  const seconds = Math.floor(sim.elapsed + 1e-7);
  text('elapsed', `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`);
  text('distance', sim.distance.toFixed(1));
  text('play-label', sim.status === 'running' ? '暂停清洁' : sim.status === 'complete' ? '重新演示' : sim.status === 'paused' ? '继续清洁' : '开始清洁');
  text('play-icon', sim.status === 'running' ? 'Ⅱ' : '▶');
  text('status', { ready: '准备就绪', running: '正在清洁', paused: '已暂停', complete: '演示完成' }[sim.status]);
  $('status-dot').classList.toggle('running', sim.status === 'running');
  for (const target of scenario.targets) {
    const done = sim.cleaned.has(target.id), button = targetButtons.get(target.id), label = targetLabels.get(target.id);
    button.classList.toggle('done', done);
    button.querySelector('.target-state').textContent = done ? '已清理 ✓' : '待清理';
    label.classList.toggle('cleaned', done); label.classList.toggle('selected', target.id === selected);
    label.textContent = done ? '✓' : target.id;
  }
  const target = scenario.targets.find(t => t.id === selected);
  if (target) {
    text('selected-title', `${target.id} · ${CATEGORIES[target.kind].label}`);
    text('selected-status', sim.cleaned.has(target.id) ? '已清理' : '待清理');
    text('selected-position', `模拟位置  X ${target.x.toFixed(2)} m  ·  Y ${target.y.toFixed(2)} m`);
  }
}

function reset(newLayout = false) {
  if (newLayout) { seed++; scenario = createScenario(seed); }
  sim = createSimulation(scenario); selected = '01';
  buildTargets(); buildRoute(); updateUI();
}

function setView(next) {
  view = next;
  const factor = Math.max(1, 1.15 / camera.aspect);
  if (view === 'top') camera.position.set(0, 12.4 * factor, 0.04);
  else camera.position.set(6.5 * factor, 7.4 * factor, 9.1 * factor);
  controls.target.set(0, 0.05, 0); controls.update();
  for (const name of ['perspective', 'top']) { $(name).classList.toggle('active', name === view); $(name).setAttribute('aria-pressed', String(name === view)); }
}

function resize() {
  const width = viewport.clientWidth, height = viewport.clientHeight;
  if (!width || !height) return;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height, false);
  setView(view);
}
new ResizeObserver(resize).observe(viewport);

$('play').addEventListener('click', () => { if (sim.status === 'complete') reset(); toggle(sim); updateUI(); });
$('reset').addEventListener('click', () => reset());
$('shuffle').addEventListener('click', () => reset(true));
$('perspective').addEventListener('click', () => setView('perspective'));
$('top').addEventListener('click', () => setView('top'));
$('route-toggle').addEventListener('change', e => { routeGroup.visible = e.target.checked; });
$('labels-toggle').addEventListener('change', e => { $('labels').hidden = !e.target.checked; });
for (const [id, scale] of [['zoom-in', 0.84], ['zoom-out', 1.18]]) $(id).addEventListener('click', () => {
  camera.position.sub(controls.target).multiplyScalar(scale).add(controls.target); controls.update();
});

const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2();
let pointerDown = null;
renderer.domElement.addEventListener('pointerdown', e => { if (e.isPrimary && e.button === 0) pointerDown = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', e => {
  if (!pointerDown || Math.hypot(e.clientX - pointerDown[0], e.clientY - pointerDown[1]) > 5) { pointerDown = null; return; }
  pointerDown = null;
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.set((e.clientX - rect.left) / rect.width * 2 - 1, -(e.clientY - rect.top) / rect.height * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const intersection = raycaster.intersectObjects(targetsGroup.children, true)[0];
  if (intersection) selectTarget(intersection.object.userData.targetId);
});
renderer.domElement.addEventListener('pointercancel', () => { pointerDown = null; });
renderer.domElement.addEventListener('webglcontextlost', event => {
  event.preventDefault();
  if (sim.status === 'running') sim.status = 'paused';
  updateUI();
  $('loading').hidden = false; $('loading').className = 'loading error';
  $('loading').textContent = '三维显示已中断，请刷新页面恢复演示。';
  $('play').disabled = true;
});

const projected = new THREE.Vector3();
function placeLabel(element, x, y, z, offset = 0) {
  projected.set(x, y, z).project(camera);
  const width = viewport.clientWidth, height = viewport.clientHeight;
  const px = (projected.x + 1) / 2 * width, py = (1 - projected.y) / 2 * height - offset;
  element.style.visibility = projected.z < -1 || projected.z > 1 || px < 13 || px > width - 13 || py < 13 || py > height - 13 ? 'hidden' : 'visible';
  element.style.transform = `translate(${px.toFixed(1)}px,${py.toFixed(1)}px) translate(-50%,-50%)`;
}

let lastTime = performance.now(), uiTime = 0;
function animate(now) {
  requestAnimationFrame(animate);
  const dt = Math.max(0, Math.min((now - lastTime) / 1000, 0.1));
  lastTime = now;
  if (document.hidden) return;
  advance(sim, dt, Number($('speed').value));
  robot.position.set(sim.x, 0, -sim.y);
  const wanted = -sim.heading;
  let turn = Math.atan2(Math.sin(wanted - robot.rotation.y), Math.cos(wanted - robot.rotation.y));
  robot.rotation.y += turn * Math.min(dt * 14, 1);
  if (sim.status === 'running') {
    for (const brush of brushes) brush.rotation.y += dt * 12 * Number($('speed').value);
    addTrace();
  }
  for (const target of scenario.targets) {
    const object = targetObjects.get(target.id), cleanedAt = sim.cleaned.get(target.id);
    const fraction = cleanedAt === undefined ? 1 : Math.max(0, 1 - (sim.elapsed - cleanedAt) * 2.6);
    object.visible = fraction > 0;
    object.scale.setScalar(Math.max(fraction, 0.001));
  }
  controls.update();
  renderer.render(scene, camera);
  for (const target of scenario.targets) placeLabel(targetLabels.get(target.id), target.x, 0.05, -target.y, 18);
  placeLabel($('robot-label'), sim.x, 0.45, -sim.y, 8);
  if (now - uiTime > 100) { updateUI(); uiTime = now; }
}

reset(); resize();
robot.position.set(sim.x, 0, -sim.y); robot.rotation.y = -sim.heading;
for (const id of ['play', 'reset', 'shuffle']) $(id).disabled = false;
$('loading').hidden = true;
requestAnimationFrame(animate);
