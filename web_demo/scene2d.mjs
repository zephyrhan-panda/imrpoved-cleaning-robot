import { CATEGORIES, createScenario, createSimulation, toggle, advance } from './simulation.mjs';

const categoryNames = { bigdirt: 'Debris', dirt: 'Dirt', water: 'Water' };
const colors = { bigdirt: '#bb824a', dirt: '#9c9c60', water: '#6695b1' };
const project = point => ({ x: 280 + point.x * 55, y: 190 - point.y * 55 });
let instance = 0;

/** Mount a self-contained SVG demonstration. It never reads or controls hardware. */
export function mountCleaningScene(root) {
  const uid = `cleaning-${++instance}`;
  root.classList.add('cleaning-widget');
  root.innerHTML = `
    <div class="cw-heading"><span>2D cleaning scene</span><span class="cw-badge">SIMULATION</span></div>
    <div class="cw-map-wrap">
      <svg class="cw-map" viewBox="0 0 560 380" role="img" aria-label="Top-down simulated room with a cleaning robot, nine dirt targets and a preset route. Select targets using the buttons below.">
        <defs><pattern id="${uid}-grid" width="55" height="55" patternUnits="userSpaceOnUse" x="60" y="25"><path d="M55 0H0V55" fill="none" stroke="#e4e6dc" stroke-width="1"/></pattern><filter id="${uid}-shadow" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#233f34" flood-opacity=".17"/></filter></defs>
        <rect x="58" y="23" width="444" height="334" rx="7" fill="#dce2d7"/>
        <rect x="62" y="27" width="436" height="326" rx="4" fill="#f9f8ef"/>
        <rect x="62" y="27" width="436" height="326" fill="url(#${uid}-grid)"/>
        <g aria-hidden="true"><rect x="282" y="38" width="174" height="58" rx="8" fill="#cdd7ca"/><rect x="290" y="47" width="49" height="41" rx="5" fill="#e4e9dc"/><rect x="344" y="47" width="49" height="41" rx="5" fill="#e4e9dc"/><rect x="398" y="47" width="49" height="41" rx="5" fill="#e4e9dc"/><circle cx="187" cy="64" r="24" fill="#ded7c4"/><circle cx="187" cy="64" r="20" fill="#f1ecdd"/><circle cx="100" cy="64" r="16" fill="#c3bda4"/><ellipse cx="100" cy="60" rx="10" ry="22" fill="#9bad8b" transform="rotate(38 100 60)"/><ellipse cx="100" cy="60" rx="10" ry="22" fill="#6e8b69" transform="rotate(-35 100 60)"/><rect x="85" y="326" width="39" height="17" rx="4" fill="#49685c"/><rect x="99" y="329" width="11" height="2" rx="1" fill="#9ed1b3"/></g>
        <path class="cw-route" fill="none" stroke="#c0cbbb" stroke-width="1.5" stroke-dasharray="5 6"/>
        <path class="cw-trace" fill="none" stroke="#658d78" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <g class="cw-spots"></g>
        <circle class="cw-selected" r="23" fill="none" stroke="#4a7563" stroke-width="1.5" stroke-dasharray="3 4"/>
        <g class="cw-robot" filter="url(#${uid}-shadow)"><circle r="20" fill="none" stroke="#8cb6a0" stroke-width="1" opacity=".6"/><circle r="17" fill="#3d5f52"/><circle r="14" fill="#f2f5ed"/><circle cy="3" r="4" fill="#6f9381"/><path d="M-4-10 0-14 4-10" fill="none" stroke="#577867" stroke-width="2" stroke-linecap="round"/><path d="M-19-5-23-9M19-5 23-9" stroke="#7a9074" stroke-width="2"/></g>
      </svg>
    </div>
    <div class="cw-legend"><span><i style="background:${colors.bigdirt}"></i>Debris</span><span><i style="background:${colors.dirt}"></i>Dirt</span><span><i style="background:${colors.water}"></i>Water</span><span class="cw-count">0 / 9 cleared</span></div>
    <div class="cw-controls"><button class="cw-play" type="button">Play simulation</button><button class="cw-reset" type="button">Reset</button><button class="cw-layout" type="button">New layout</button><label>Speed <select class="cw-speed" aria-label="Simulation speed"><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option></select></label></div>
    <div class="cw-state"><span class="cw-status" role="status" aria-live="polite">Ready</span><span class="cw-clock">00:00</span><span class="cw-distance">0.0 m</span></div>
    <div class="cw-targets" aria-label="Select a simulated dirt target"></div>
    <p class="cw-selection" aria-live="polite"></p>
    <p class="cw-note">Illustrative positions and preset motion. Not connected to the detector or a robot.</p>`;

  const q = selector => root.querySelector(selector);
  const svg = q('.cw-map'), namespace = 'http://www.w3.org/2000/svg';
  let seed = 9, scenario = createScenario(seed), sim = createSimulation(scenario), selected = '01';
  let spots = new Map(), buttons = new Map(), trace = [], lastPoint = null, raf = 0, destroyed = false;
  function setText(element, value) { if (element.textContent !== value) element.textContent = value; }
  function select(id) { selected = id; updateUI(); }
  function element(name, attributes) {
    const node = document.createElementNS(namespace, name);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
    return node;
  }
  function build() {
    q('.cw-spots').replaceChildren(); q('.cw-targets').replaceChildren();
    spots = new Map(); buttons = new Map();
    for (const target of scenario.targets) {
      const point = project(target), color = colors[target.kind];
      const group = element('g', { transform: `translate(${point.x} ${point.y})`, 'data-target': target.id });
      const title = element('title', {}); title.textContent = `${target.id} · ${categoryNames[target.kind]}`; group.append(title);
      const r = CATEGORIES[target.kind].radius * 55;
      group.append(element('ellipse', { rx: r + 2, ry: r * 0.78, fill: color, opacity: '.32' }));
      if (target.kind === 'water') {
        group.append(element('path', { d: 'M-8 1q4-5 8-1t8-1', fill: 'none', stroke: color, 'stroke-width': '2' }));
      } else {
        for (let i = 0; i < 5; i++) group.append(element('circle', { cx: Math.cos(i * 2.4) * r * .5, cy: Math.sin(i * 2.4) * r * .5, r: target.kind === 'bigdirt' ? 3 : 1.7, fill: color }));
      }
      const label = element('text', { y: -r - 7, 'text-anchor': 'middle', fill: '#617062', class: 'cw-number', 'font-size': '12' });
      label.textContent = target.id; group.append(label);
      const hit = element('circle', { r: 22, fill: 'transparent', class: 'cw-hit' });
      group.append(hit); group.addEventListener('click', () => select(target.id));
      q('.cw-spots').append(group); spots.set(target.id, group);
      const button = document.createElement('button');
      button.type = 'button'; button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', `Target ${target.id}, ${categoryNames[target.kind]}`);
      button.innerHTML = `<i style="background:${color}"></i><span>${target.id}</span>`;
      button.addEventListener('click', () => select(target.id));
      q('.cw-targets').append(button); buttons.set(target.id, button);
    }
    q('.cw-route').setAttribute('d', scenario.route.map((p, i) => { const v = project(p); return `${i ? 'L' : 'M'}${v.x} ${v.y}`; }).join(' '));
    trace = []; lastPoint = null; q('.cw-trace').setAttribute('d', '');
    fitLabels(); draw(); updateUI();
  }
  function fitLabels() {
    const scale = Math.max(svg.getBoundingClientRect().width / 560, .3);
    q('.cw-spots').querySelectorAll('text').forEach(label => label.setAttribute('font-size', String(Math.max(12, 11 / scale))));
  }
  function draw() {
    const position = project(sim);
    q('.cw-robot').setAttribute('transform', `translate(${position.x} ${position.y}) rotate(${sim.heading * 180 / Math.PI})`);
    if (!lastPoint || Math.hypot(sim.x - lastPoint.x, sim.y - lastPoint.y) > .05) {
      trace.push(`${trace.length ? 'L' : 'M'}${position.x.toFixed(2)} ${position.y.toFixed(2)}`);
      lastPoint = { x: sim.x, y: sim.y };
      q('.cw-trace').setAttribute('d', trace.join(' '));
    }
    for (const target of scenario.targets) spots.get(target.id).classList.toggle('is-cleared', sim.cleaned.has(target.id));
  }
  function updateUI() {
    const statuses = { ready: 'Ready', running: 'Simulation running', paused: 'Paused', complete: 'Simulation complete' };
    setText(q('.cw-status'), statuses[sim.status]);
    setText(q('.cw-play'), sim.status === 'running' ? 'Pause' : sim.status === 'paused' ? 'Resume' : sim.status === 'complete' ? 'Replay' : 'Play simulation');
    setText(q('.cw-count'), `${sim.cleaned.size} / ${scenario.targets.length} cleared`);
    const seconds = Math.floor(sim.elapsed + 1e-7);
    setText(q('.cw-clock'), `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`);
    setText(q('.cw-distance'), `${sim.distance.toFixed(1)} m`);
    const target = scenario.targets.find(t => t.id === selected), p = project(target);
    q('.cw-selected').setAttribute('cx', p.x); q('.cw-selected').setAttribute('cy', p.y);
    for (const [id, button] of buttons) {
      button.setAttribute('aria-pressed', String(id === selected));
      button.classList.toggle('is-cleared', sim.cleaned.has(id));
    }
    setText(q('.cw-selection'), `${target.id} · ${categoryNames[target.kind]} · ${sim.cleaned.has(selected) ? 'Cleared' : 'Pending'} · Simulated (${target.x.toFixed(2)}, ${target.y.toFixed(2)}) m`);
  }
  function reset(newLayout = false) {
    if (newLayout) scenario = createScenario(++seed);
    sim = createSimulation(scenario); selected = '01'; build();
  }
  q('.cw-play').addEventListener('click', () => { if (sim.status === 'complete') reset(); toggle(sim); updateUI(); });
  q('.cw-reset').addEventListener('click', () => reset());
  q('.cw-layout').addEventListener('click', () => reset(true));
  const resize = new ResizeObserver(fitLabels); resize.observe(svg);
  let lastTime = performance.now(), uiTime = 0;
  function frame(now) {
    if (destroyed) return;
    raf = requestAnimationFrame(frame);
    const dt = Math.max(0, Math.min(.1, (now - lastTime) / 1000)); lastTime = now;
    if (document.hidden || sim.status !== 'running') return;
    advance(sim, dt, Number(q('.cw-speed').value)); draw();
    if (now - uiTime > 100 || sim.status === 'complete') { updateUI(); uiTime = now; }
  }
  build(); raf = requestAnimationFrame(frame);
  return { destroy() { destroyed = true; cancelAnimationFrame(raf); resize.disconnect(); } };
}
