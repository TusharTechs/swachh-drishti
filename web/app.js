const fmt = new Intl.NumberFormat('en-IN');
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
// Hidden/background tabs don't run animations: show the final state immediately instead of entrance motion.
const STATIC = REDUCED || document.visibilityState !== 'visible';
const state = { sites: null, byId: {}, filtered: [], selected: null, map: null, summary: null };

const STYLES = { light: 'https://tiles.openfreemap.org/styles/positron', dark: 'https://tiles.openfreemap.org/styles/dark' };
const TREND = {
  visible_reduction: { c: '#15803d', label: 'Visible reduction' },
  little_visible_change: { c: '#c2410c', label: 'Little visible change' },
  visible_expansion: { c: '#b91c1c', label: 'Visible expansion' },
  indeterminate: { c: '#64748b', label: 'Indeterminate' },
};
const tcol = (t) => (TREND[t] || { c: '#64748b' }).c;
const name = (p) => p.display_name || `${p.city || 'Unnamed'} dumpsite`;
const place = (p) => [p.city, p.state].filter(Boolean).join(', ') || 'Location pending';
const recentFire = (p) => p.fire_last && p.fire_last >= '2025-01-01';
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* ---------- theme ---------- */
function theme() {
  const t = document.documentElement.dataset.theme;
  if (t) return t;
  return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
$('#theme-btn').onclick = () => {
  const next = theme() === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('sd-theme', next); } catch (e) {}
  if (state.map) state.map.setStyle(STYLES[next], { diff: false });
};

/* ---------- motion helpers ---------- */
function reveal() {
  if (STATIC) document.documentElement.classList.add('static');
  if (!STATIC) $$('.hero-inner > *').forEach((el, i) => { el.classList.add('reveal'); el.style.animationDelay = `${0.15 + i * 0.12}s`; });
  if (REDUCED) $$('svg').forEach((s) => s.pauseAnimations && s.pauseAnimations());
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('on'); io.unobserve(e.target); } }), { threshold: 0.15 });
  if (!STATIC) $$('.step').forEach((el, i) => { el.classList.add('inview'); el.style.transitionDelay = `${i * 80}ms`; io.observe(el); });
}
function countUp(el, to, decimals = 0, suffix = '') {
  const done = () => { el.textContent = (decimals ? to.toFixed(decimals) : fmt.format(Math.round(to))) + suffix; };
  if (STATIC) return done();
  const t0 = performance.now(), dur = 1400;
  const step = (t) => {
    const k = Math.max(0, Math.min(1, (t - t0) / dur)), e = 1 - Math.pow(1 - k, 3), v = to * e;
    el.textContent = (decimals ? v.toFixed(decimals) : fmt.format(Math.round(v))) + suffix;
    if (k < 1) requestAnimationFrame(step); else done();
  };
  requestAnimationFrame(step);
}

/* ---------- data ---------- */
async function load() {
  reveal();
  const [sites, summary] = await Promise.all([
    fetch('data/sites.geojson').then((r) => r.json()),
    fetch('data/summary.json').then((r) => r.json()),
  ]);
  state.sites = sites; state.summary = summary;
  sites.features.forEach((f) => { state.byId[f.properties.site_id] = f; });
  if (summary.repo) {
    $('#repo-link').href = summary.repo;
    window.REPO = summary.repo + '/issues/new?template=right-of-reply.yml&title=Right%20of%20reply%3A%20';
  }
  renderStats(summary);
  const states = [...new Set(sites.features.map((f) => f.properties.state).filter(Boolean))].sort();
  $('#f-state').insertAdjacentHTML('beforeend', states.map((s) => `<option>${esc(s)}</option>`).join(''));
  initMap();
  applyFilters();
  loadMethod();
  const id = location.hash.slice(1);
  if (state.byId[id]) { setTimeout(() => $('#explore').scrollIntoView({ behavior: 'auto' }), 50); select(id); }
}

function renderStats(s) {
  const lakh = (s.pop_1km || 0) / 1e5;
  const items = [
    { v: s.sites_total, l: 'dumpsites in the open gazetteer', c: 'var(--teal)' },
    { v: lakh, d: 1, suf: ' lakh', l: 'people live within 1 km of a mapped site', c: 'var(--saffron)' },
    { v: s.legacy_waste_t / 1e7, d: 1, suf: ' cr t', l: 'legacy waste at DRAP priority sites', c: 'var(--t-slate)' },
    { v: s.sites_with_fire, l: 'sites with satellite-detected fires since 2019', c: 'var(--fire)' },
    { v: s.sites_with_insar, l: 'mounds measured by Sentinel-1 radar', c: 'var(--radar)' },
    { v: s.packs_published, l: 'reviewed evidence packs published', c: 'var(--t-green)' },
  ];
  $('#stats').innerHTML = items.map((it, i) => `<div class="stat-card"><span class="acc" style="--c:${it.c}"></span><b data-i="${i}">0</b><span>${it.l}</span></div>`).join('');
  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (!e.isIntersecting) return;
    $$('b[data-i]', e.target).forEach((b) => { const it = items[+b.dataset.i]; countUp(b, it.v || 0, it.d || 0, it.suf || ''); });
    io.disconnect();
  }), { threshold: 0.3 });
  io.observe($('#stats'));
}

async function loadMethod() {
  try {
    const md = await fetch('method.md').then((r) => r.text());
    $('#method-body').innerHTML = '<h2 id="method-title">Method, data and limits</h2>' + marked.parse(md);
    const bt = state.summary.fire_backtest;
    if (bt) $('#method-body').insertAdjacentHTML('beforeend', `<p class="callout">Fire backtest: VIIRS detected <b>${bt.detected} of ${bt.evaluable_events}</b> documented dumpsite fires (2019–2025) within ±1 day. Misses are mostly smouldering fires. That is why this is a fire <i>record</i>, not an early warning.</p>`);
  } catch (e) { /* method stays as placeholder */ }
}

/* ---------- map ---------- */
function initMap() {
  const map = state.map = new maplibregl.Map({
    container: 'map', style: STYLES[theme()], center: [80.5, 22.6], zoom: 4.2, attributionControl: { compact: true },
    cooperativeGestures: matchMedia('(max-width: 900px)').matches,
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
  map.addControl(new maplibregl.FullscreenControl(), 'top-left');
  map.on('style.load', () => addLayers(map));
  const pop = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
  for (const id of ['pts', 'poly-fill']) {
    map.on('click', id, (e) => select(e.features[0].properties.site_id));
    map.on('mousemove', id, (e) => {
      map.getCanvas().style.cursor = 'pointer';
      const p = e.features[0].properties;
      pop.setLngLat(e.lngLat).setHTML(`<b>${esc(name(p))}</b><br><span style="color:var(--muted)">${esc(place(p))}</span>`).addTo(map);
    });
    map.on('mouseleave', id, () => { map.getCanvas().style.cursor = ''; pop.remove(); });
  }
  $('#t-sat').onchange = (e) => map.getLayer('s2') && map.setLayoutProperty('s2', 'visibility', e.target.checked ? 'visible' : 'none');
  if (!REDUCED) pulse();
}

function addLayers(map) {
  if (map.getSource('pts')) return;
  for (const l of map.getStyle().layers) {  // omit international boundaries (official boundary: Survey of India)
    if (/boundary/i.test(l.id) && /country|admin_level_2|disputed|boundary_2|boundary_3|maritime/i.test(l.id + JSON.stringify(l.filter || '')))
      map.setLayoutProperty(l.id, 'visibility', 'none');
  }
  map.addSource('s2', { type: 'raster', tileSize: 256, maxzoom: 15,
    tiles: ['https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2023_3857/default/g/{z}/{y}/{x}.jpg'],
    attribution: 'Sentinel-2 cloudless 2023 by EOX (CC BY-NC-SA 4.0)' });
  map.addLayer({ id: 's2', type: 'raster', source: 's2', minzoom: 11, layout: { visibility: $('#t-sat').checked ? 'visible' : 'none' },
    paint: { 'raster-opacity': ['interpolate', ['linear'], ['zoom'], 11, 0, 12.5, 0.95] } });
  const feats = state.sites.features;
  map.addSource('polys', { type: 'geojson', data: { type: 'FeatureCollection', features: feats.filter((f) => f.geometry && f.geometry.type !== 'Point') } });
  map.addSource('pts', { type: 'geojson', data: { type: 'FeatureCollection', features: feats.map((f) => ({ type: 'Feature', properties: f.properties, geometry: { type: 'Point', coordinates: f.properties.lonlat } })) } });
  const color = ['match', ['coalesce', ['get', 'trend'], 'none'], ...Object.entries(TREND).flatMap(([k, v]) => [k, v.c]), '#64748b'];
  map.addLayer({ id: 'poly-fill', type: 'fill', source: 'polys', minzoom: 9, paint: { 'fill-color': color, 'fill-opacity': ['case', ['boolean', ['feature-state', 'sel'], false], 0.42, 0.24] } });
  map.addLayer({ id: 'poly-line', type: 'line', source: 'polys', minzoom: 9, paint: { 'line-color': color, 'line-width': ['interpolate', ['linear'], ['zoom'], 9, 1, 15, 3] } });
  map.addLayer({ id: 'fire-pulse', type: 'circle', source: 'pts', maxzoom: 12, filter: ['>=', ['coalesce', ['get', 'fire_last'], ''], '2025-01-01'],
    paint: { 'circle-radius': 10, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': '#dc2626', 'circle-stroke-width': 2, 'circle-stroke-opacity': 0.5 } });
  map.addLayer({ id: 'pts', type: 'circle', source: 'pts', maxzoom: 12, paint: {
    'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, ['interpolate', ['linear'], ['coalesce', ['get', 'pop_1km'], 0], 0, 3, 200000, 7, 600000, 11],
                      10, ['interpolate', ['linear'], ['coalesce', ['get', 'pop_1km'], 0], 0, 6, 200000, 12, 600000, 18]],
    'circle-color': ['case', ['==', ['get', 'mapped'], true], color, 'rgba(0,0,0,0)'],
    'circle-stroke-color': ['case', ['==', ['get', 'mapped'], true], '#ffffff', '#0f766e'],
    'circle-stroke-width': ['case', ['==', ['get', 'mapped'], true], 1, 1.5], 'circle-opacity': 0.88 } });
}

function pulse() {
  const t0 = performance.now();
  const frame = (t) => {
    const k = ((t - t0) % 2000) / 2000;
    const m = state.map;
    if (m && m.getLayer('fire-pulse')) {
      const z = m.getZoom(), base = z < 6 ? 6 : 10;
      m.setPaintProperty('fire-pulse', 'circle-radius', base + k * (z < 6 ? 10 : 16));
      m.setPaintProperty('fire-pulse', 'circle-stroke-opacity', 0.7 * (1 - k));
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

/* ---------- list ---------- */
function applyFilters() {
  const q = $('#q').value.trim().toLowerCase(), st = $('#f-state').value, fs = $('#f-status').value, sort = $('#f-sort').value;
  const sorters = {
    priority: (a, b) => (b.priority_score || 0) - (a.priority_score || 0),
    people: (a, b) => (b.pop_1km || 0) - (a.pop_1km || 0),
    fire: (a, b) => (b.fire_days || 0) - (a.fire_days || 0),
    waste: (a, b) => (b.legacy_waste_t || 0) - (a.legacy_waste_t || 0),
  };
  state.filtered = state.sites.features.map((f) => f.properties).filter((p) => {
    if (st && p.state !== st) return false;
    if (fs === 'mapped' && !p.mapped) return false;
    if (fs === 'unmapped' && p.mapped) return false;
    if (fs === 'fire' && !(p.fire_days > 0)) return false;
    if (fs === 'drap' && !p.drap_priority) return false;
    if (fs === 'radar' && !p.insar) return false;
    return !q || `${name(p)} ${p.city} ${p.state} ${p.ulb}`.toLowerCase().includes(q);
  }).sort(sorters[sort]);
  $('#count').textContent = `${fmt.format(state.filtered.length)} sites`;
  $('#list').innerHTML = state.filtered.slice(0, 400).map((p) => `<li data-id="${p.site_id}" class="${p.site_id === state.selected ? 'sel' : ''}" tabindex="0">
    <span class="dot ${p.mapped ? '' : 'hollow'}" style="--c:${tcol(p.trend)}"></span>
    <div><div class="t">${esc(name(p))}</div>
      <div class="s">${esc(place(p))}${p.pop_1km ? ' · ' + fmt.format(p.pop_1km) + ' people ≤1 km' : ''}</div>
      <div class="badges">${p.drap_priority ? '<span class="badge drap">DRAP</span>' : ''}${p.fire_days ? `<span class="badge fire">🔥 ${p.fire_days} fire days</span>` : ''}${p.insar ? `<span class="badge radar">radar ${p.insar_mm} mm</span>` : ''}${p.mapped ? '' : '<span class="badge trace">needs tracing</span>'}</div>
    </div></li>`).join('') + (state.filtered.length > 400 ? `<li class="s" style="cursor:default">Showing 400 of ${fmt.format(state.filtered.length)}; refine the search.</li>` : '');
}

/* ---------- panel ---------- */
let selFeatureId = null;
async function select(id) {
  const f = state.byId[id];
  if (!f) return;
  state.selected = id; history.replaceState(null, '', '#' + id);
  $$('#list li').forEach((li) => li.classList.toggle('sel', li.dataset.id === id));
  const p = f.properties, m = state.map;
  const wide = matchMedia('(min-width: 901px)').matches;
  m && m.flyTo({ center: p.lonlat, zoom: p.mapped ? 15 : 11, speed: 1.4, curve: 1.6, essential: true,
    padding: wide ? { right: 480, left: 0, top: 0, bottom: 0 } : { bottom: innerHeight * 0.55, top: 0, left: 0, right: 0 } });
  const panel = $('#panel');
  panel.hidden = false;
  panel.innerHTML = head(p) + `<div class="p-body"><div class="skeleton" style="width:70%"></div><div class="skeleton"></div><div class="skeleton" style="width:50%"></div></div>`;
  wireClose(panel);
  let d = {};
  try { d = await fetch(`data/sites/${id}.json`).then((r) => (r.ok ? r.json() : {})); } catch (e) {}
  if (state.selected !== id) return;
  const tabs = [['overview', 'Overview'], ['imagery', 'Imagery'], ['risk', 'Fire & radar'], ['pack', 'Evidence pack']];
  panel.innerHTML = head(p) + `<div class="p-tabs" role="tablist">${tabs.map(([k, l], i) => `<button role="tab" data-tab="${k}" aria-selected="${i === 0}">${l}</button>`).join('')}</div><div class="p-body" id="p-body"></div>`;
  wireClose(panel);
  const render = (k) => {
    $$('.p-tabs button', panel).forEach((b) => b.setAttribute('aria-selected', b.dataset.tab === k));
    const body = $('#p-body', panel);
    body.innerHTML = { overview: overview(p, d), imagery: imagery(d.imagery || []), risk: risk(d), pack: packTab(p, d) }[k];
    body.scrollTop = 0;
    if (k === 'imagery' && (d.imagery || []).length) wireBA(body, d.imagery);
  };
  $$('.p-tabs button', panel).forEach((b) => (b.onclick = () => render(b.dataset.tab)));
  render('overview');
}

function head(p) {
  const t = TREND[p.trend];
  return `<div class="p-head"><button class="p-close" aria-label="Close panel">×</button>
    <h2>${esc(name(p))}</h2><div class="sub">${esc(place(p))}${p.ulb ? ' · ULB: ' + esc(p.ulb) : ''}</div>
    <div class="badges" style="margin-top:8px">${t ? `<span class="trend-pill" style="--c:${t.c}">${t.label}</span>` : ''}${p.drap_priority ? '<span class="badge drap">DRAP priority</span>' : ''}${recentFire(p) ? '<span class="badge fire">fire since 2025</span>' : ''}${p.insar ? '<span class="badge radar">radar measured</span>' : ''}${p.status === 'auto-traced' ? '<span class="badge trace">auto-traced boundary</span>' : ''}</div></div>`;
}
function wireClose(panel) {
  $('.p-close', panel).onclick = () => { panel.hidden = true; state.selected = null; history.replaceState(null, '', location.pathname); $$('#list li.sel').forEach((li) => li.classList.remove('sel')); };
}
const stat = (b, s) => `<div class="stat"><b>${b}</b><span>${s}</span></div>`;

function overview(p, d) {
  const obs = d.imagery || [];
  const line = obs.length >= 2 && TREND[p.trend]
    ? `<p class="callout">Between <b>${obs[0].date}</b> and <b>${obs[obs.length - 1].date}</b>, the exposed waste-like surface went from <b>${obs[0].exposed_ha} ha</b> to <b>${obs[obs.length - 1].exposed_ha} ha</b>: ${TREND[p.trend].label.toLowerCase()}. Footprint is not tonnage.</p>` : '';
  return `${line}
    <h3>Site</h3><div class="grid2">
      ${stat(p.legacy_waste_t ? fmt.format(Math.round(p.legacy_waste_t)) + ' t' : '—', 'legacy waste (DRAP annexure)')}
      ${stat(p.approved_cost_cr ? '₹' + p.approved_cost_cr + ' cr' : '—', 'approved remediation cost')}
      ${stat(p.area_ha ? p.area_ha + ' ha' : '—', p.status === 'auto-traced' ? 'area (auto-traced)' : 'area (OSM boundary)')}
      ${stat(p.max_height_m_glo30 ? p.max_height_m_glo30 + ' m' : '—', 'mound height (DEM, 2011–2015)')}
    </div>
    <h3>People living nearby · GHSL 2025</h3>${d.exposure ? `<div class="grid3">${stat(fmt.format(d.exposure.pop_1km), 'within 1 km')}${stat(fmt.format(d.exposure.pop_2km), 'within 2 km')}${stat(fmt.format(d.exposure.pop_5km), 'within 5 km')}</div>` : '<p class="note">Not computed.</p>'}
    ${p.mapped ? '' : '<p class="callout">No reliable boundary yet: the marker shows the city centre. Help trace this site on OpenStreetMap (<code>landuse=landfill</code>).</p>'}`;
}

function chart(values, labels, color, unit, zero = false) {
  const W = 320, H = 110, P = { l: 48, r: 12, t: 10, b: 20 };
  if (!values.length) return '';
  const lo = Math.min(zero ? 0 : Infinity, ...values), hi = Math.max(zero ? 0 : -Infinity, ...values), rng = hi - lo || 1;
  const X = (i) => P.l + i * ((W - P.l - P.r) / Math.max(values.length - 1, 1));
  const Y = (v) => P.t + (H - P.t - P.b) * (1 - (v - lo) / rng);
  const pts = values.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`);
  let len = 0; for (let i = 1; i < values.length; i++) len += Math.hypot(X(i) - X(i - 1), Y(values[i]) - Y(values[i - 1]));
  const base = zero ? Y(0) : H - P.b;
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="chart">
    <line class="axis" x1="${P.l}" x2="${W - P.r}" y1="${base}" y2="${base}"/>
    <text x="${P.l - 6}" y="${Y(hi) + 4}" text-anchor="end">${Math.round(hi)}${unit}</text><text x="${P.l - 6}" y="${Y(lo) + 4}" text-anchor="end">${Math.round(lo)}${unit}</text>
    <path class="area" fill="${color}" d="M${X(0)},${base} L${pts.join(' L')} L${X(values.length - 1)},${base} Z"/>
    <polyline class="line" style="--len:${Math.ceil(len)}" stroke="${color}" points="${pts.join(' ')}"/>
    ${values.map((v, i) => `<circle cx="${X(i)}" cy="${Y(v)}" r="3" fill="${color}"><title>${labels[i]}: ${v}${unit}</title></circle>`).join('')}
    <text x="${X(0)}" y="${H - 4}" text-anchor="start">${labels[0]}</text><text x="${X(values.length - 1)}" y="${H - 4}" text-anchor="end">${labels[labels.length - 1]}</text>
  </svg>`;
}

function imagery(obs) {
  if (!obs.length) return '<p class="note">No Sentinel-2 series for this site yet (it needs a boundary first).</p>';
  const opts = (sel) => obs.map((o, i) => `<option value="${i}" ${i === sel ? 'selected' : ''}>${o.year}</option>`).join('');
  return `<h3>Before / after · Sentinel-2 (10 m, dry season)</h3>
    <div class="years"><label>Left <select id="ba-l">${opts(0)}</select></label><label>Right <select id="ba-r">${opts(obs.length - 1)}</select></label>
      <span class="seg" role="group" aria-label="Band combination"><button data-m="rgb" class="on">True colour</button><button data-m="swir">SWIR</button></span></div>
    <div class="ba" id="ba"><img class="before" alt=""><img class="after" alt=""><div class="handle"></div>
      <span class="lbl l" id="ba-ll"></span><span class="lbl r" id="ba-rl"></span>
      <input type="range" min="0" max="100" value="50" aria-label="Drag to compare years"></div>
    <p class="note" id="ba-cap"></p>
    <h3>Exposed waste-like surface (ha)</h3>${chart(obs.map((o) => o.exposed_ha), obs.map((o) => o.year), '#0f766e', ' ha')}
    <p class="note">Measured inside the site boundary on the clearest dry-season scene each year. SWIR false colour makes fresh refuse and burn scars stand out. Footprint is not tonnage.</p>`;
}

function wireBA(body, obs) {
  let mode = 'rgb';
  const ba = $('#ba', body), l = $('#ba-l', body), r = $('#ba-r', body);
  const show = () => {
    const a = obs[+l.value], b = obs[+r.value];
    $('.before', ba).src = `data/chips/${mode === 'rgb' ? a.chip_rgb : a.chip_swir}`;
    $('.after', ba).src = `data/chips/${mode === 'rgb' ? b.chip_rgb : b.chip_swir}`;
    $('#ba-ll', body).textContent = a.date; $('#ba-rl', body).textContent = b.date;
    $('#ba-cap', body).textContent = `${a.date}: exposed ${a.exposed_ha} ha · ${b.date}: exposed ${b.exposed_ha} ha (scenes ${a.scene_id}, ${b.scene_id})`;
  };
  $('input', ba).oninput = (e) => ba.style.setProperty('--x', e.target.value + '%');
  l.onchange = r.onchange = show;
  $$('.seg button', body).forEach((btn) => (btn.onclick = () => { mode = btn.dataset.m; $$('.seg button', body).forEach((x) => x.classList.toggle('on', x === btn)); show(); }));
  show();
  if (!REDUCED) {  // gentle hint animation of the divider
    let x = 50, dir = -1, n = 0; const h = setInterval(() => { x += dir * 2; if (x < 30 || x > 70) { dir *= -1; n++; } ba.style.setProperty('--x', x + '%'); if (n >= 2 && Math.abs(x - 50) < 2) { clearInterval(h); ba.style.setProperty('--x', '50%'); } }, 16);
    $('input', ba).addEventListener('pointerdown', () => clearInterval(h), { once: true });
  }
}

function risk(d) {
  const f = d.fires;
  const fire = f ? `<div class="grid2">${stat(f.fire_days, 'days with VIIRS fire detections')}${stat(f.last, 'latest detection')}</div>
      <p class="note">First detection in the record: ${f.first}. VIIRS (375 m) misses small and smouldering fires and cannot see below the surface; a detection is evidence of heat, not of its cause.</p>`
    : '<p class="note">No VIIRS detections attributed to this site since 2019.</p>';
  const ins = d.insar;
  let radar = '<p class="note">Not in the radar pilot yet. Ten large mounds were measured first.</p>';
  if (ins && ins.series) {
    const pts = ins.series.filter((x) => x.cumulative_mm != null);
    const dd = (s) => `${s.slice(6, 8)}/${s.slice(4, 6)}`;
    radar = pts.length ? `${chart(pts.map((x) => x.cumulative_mm), pts.map((x) => dd(x.d2)), '#7c3aed', ' mm', true)}
      <p class="callout">Cumulative vertical movement of the mound relative to the ground 300–800 m around it: <b>${pts[pts.length - 1].cumulative_mm} mm</b> over ${pts.length} Sentinel-1 pairs (${pts[0].d1.slice(0, 4)}). Negative means settling.</p>
      <p class="note">ASF HyP3 InSAR (40 m). C-band radar decorrelates on active tipping faces; this is a screening signal, not a stability verdict.</p>`
      : '<p class="note">Radar pairs processed but decorrelated over the mound; no reliable measurement.</p>';
  }
  return `<h3>Fire record · NASA FIRMS VIIRS</h3>${fire}<h3>Mound movement · Sentinel-1 InSAR</h3>${radar}`;
}

function packTab(p, d) {
  const a = d.assessment;
  const reply = `<a class="reply" target="_blank" rel="noopener" href="${window.REPO ? window.REPO + encodeURIComponent(p.site_id + ' ' + name(p)) : '#'}">✍︎ Right of reply / corrections</a>`;
  if (!d.pack_md) return `<p class="note">${a ? 'This pack is held for human review by the reviewer gate.' : 'No evidence pack yet: this site needs a boundary first.'}</p>${reply}`;
  return `<p class="note">Drafted by the evidence agent (analyst: ${esc(a && a.analyst ? a.analyst.model : 'rules')}), passed the reviewer gate. It is an observation record, not a certificate.</p>
    <div class="pack">${marked.parse(d.pack_md)}</div>${reply}`;
}

/* ---------- events ---------- */
['#q', '#f-state', '#f-status', '#f-sort'].forEach((s) => $(s).addEventListener('input', applyFilters));
$('#list').addEventListener('click', (e) => { const li = e.target.closest('li[data-id]'); if (li) select(li.dataset.id); });
$('#list').addEventListener('keydown', (e) => { const li = e.target.closest('li[data-id]'); if (li && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); select(li.dataset.id); } });
document.addEventListener('keydown', (e) => {
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT') { e.preventDefault(); $('#explore').scrollIntoView(); $('#q').focus(); }
  if (e.key === 'Escape' && !$('#panel').hidden) $('.p-close').click();
});
load();
