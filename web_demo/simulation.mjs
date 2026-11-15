/** Deterministic visual demonstration only: no perception, planning, or robot control. */
export const CATEGORIES = Object.freeze({
  bigdirt: { label: '大块污渍', classId: 0, color: 0xc78b55, radius: 0.20 },
  dirt: { label: '普通污渍', classId: 1, color: 0xa9a568, radius: 0.16 },
  water: { label: '积水', classId: 2, color: 0x6c9cb8, radius: 0.26 },
});

export function randomGenerator(seed) {
  let s = seed >>> 0;
  return () => { s = (Math.imul(1664525, s) + 1013904223) >>> 0; return s / 4294967296; };
}

export function createScenario(seed = 9) {
  const random = randomGenerator(seed);
  const rows = [-2, -1.2, -0.4, 0.4, 1.2];
  const route = [{ x: -3.2, y: rows[0] }];
  for (let i = 0; i < rows.length; i++) {
    route.push({ x: i % 2 ? -3.2 : 3.2, y: rows[i] });
    if (i < rows.length - 1) route.push({ x: i % 2 ? -3.2 : 3.2, y: rows[i + 1] });
  }
  const positions = [[-1.8, 0], [1.4, 0], [-0.8, 1], [2.1, 1], [-2.0, 2], [0.6, 2], [-1.1, 3], [2.1, 3], [0.0, 4]];
  const kinds = ['bigdirt', 'water', 'dirt', 'bigdirt', 'dirt', 'water', 'water', 'bigdirt', 'dirt'];
  const targets = positions.map(([x, row], i) => ({
    id: String(i + 1).padStart(2, '0'), kind: kinds[i],
    x: x + (random() - 0.5) * 0.55, y: rows[row] + (random() - 0.5) * 0.14,
    variation: random(),
  }));
  return { seed, route, targets, dataSource: 'simulation' };
}

export function createSimulation(scenario) {
  return { scenario, status: 'ready', x: scenario.route[0].x, y: scenario.route[0].y,
    heading: Math.PI / 2, waypoint: 1, elapsed: 0, distance: 0, cleaned: new Map() };
}

export function toggle(sim) {
  if (sim.status === 'complete') return;
  sim.status = sim.status === 'running' ? 'paused' : 'running';
}

function segmentDistance(point, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const length2 = dx * dx + dy * dy;
  const t = length2 === 0 ? 0 : Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / length2));
  return Math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy);
}

export function advance(sim, seconds, speed = 1) {
  if (sim.status !== 'running' || !Number.isFinite(seconds) || seconds <= 0) return;
  if (!Number.isFinite(speed) || speed <= 0) return;
  const velocity = 0.8;
  let budget = Math.min(seconds, 0.1) * Math.min(speed, 4) * velocity;
  while (budget > 1e-9 && sim.waypoint < sim.scenario.route.length) {
    const next = sim.scenario.route[sim.waypoint];
    const dx = next.x - sim.x, dy = next.y - sim.y, remaining = Math.hypot(dx, dy);
    if (remaining < 1e-9) { sim.waypoint++; continue; }
    const move = Math.min(budget, remaining), before = { x: sim.x, y: sim.y };
    sim.heading = Math.atan2(dx, dy);
    sim.x += dx / remaining * move;
    sim.y += dy / remaining * move;
    sim.distance += move;
    sim.elapsed += move / velocity;
    budget -= move;
    // A prescribed footprint crossing a synthetic target marks it clean in this demo.
    for (const target of sim.scenario.targets) {
      if (!sim.cleaned.has(target.id) && segmentDistance(target, before, sim) <= 0.29) {
        sim.cleaned.set(target.id, sim.elapsed);
      }
    }
    if (move >= remaining - 1e-9) sim.waypoint++;
  }
  if (sim.waypoint >= sim.scenario.route.length) sim.status = 'complete';
}
