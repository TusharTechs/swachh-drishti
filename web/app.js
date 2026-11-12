const fmt = new Intl.NumberFormat('en-IN');
const $ = (s) => document.querySelector(s);
const state = { sites: null, filtered: [], selected: null, map: null };

const STYLE = 'https://tiles.openfreemap.org/styles/positron';
const COLORS = { visible_reduction: '#15803d', little_visible_change: '#b45309', visible_expansion: '#b91c1c',
                 indeterminate: '#64748b', unassessed: '#0f766e' };

function name(p) { return p.site_name || p.osm_name || `${p.city} dumpsite`; }
function trend(p) { return p.trend || 'unassessed'; }

async function load() {
  const [sites, summary] = await Promise.all([
    fetch('data/sites.geojson').then(r => r.json()),
    fetch('data/summary.json').then(r => r.json()),
  ]);
  state.sites = sites;
  renderKpis(summary);
  if (summary.repo) { $('#repo-link').href = summary.repo; window.REPO = summary.repo + '/issues/new?template=right-of-reply.yml&title=Right%20of%20reply%3A%20'; }
  const states = [...new Set(sites.features.map(f => f.properties.state))].sort();
  $('#f-state').insertAdjacentHTML('beforeend', states.map(s => `<option>${s}</option>`).join(''));
  initMap();
  applyFilters();
  const id = location.hash.slice(1);
  if (id) select(id);
}

function renderKpis(s) {
  const k = [
    [fmt.format(s.sites_total), 'dumpsites in the open gazetteer'],
    [fmt.format(s.sites_mapped), 'with a traced site boundary'],
    [fmt.format(Math.round(s.legacy_waste_t / 1e5) / 10) + ' cr t', 'legacy waste at DRAP priority sites'],
    [fmt.format(s.pop_1km || 0), 'people living within 1 km of a mapped site (GHSL 2025)'],
    [fmt.format(s.sites_with_fire || 0), 'sites with VIIRS fire detections, 2019→'],
    [fmt.format(s.packs_published || 0), 'reviewed evidence packs published'],
  ];
  if (s.sites_with_insar) k.push([fmt.format(s.sites_with_insar), 'mounds screened with Sentinel-1 InSAR']);
  if (s.fire_backtest) k.push([Math.round(s.fire_backtest.recall * 100) + '%', `of ${s.fire_backtest.evaluable_events} documented fires detected (backtest)`]);
  $('#kpis').innerHTML = k.map(([b, t]) => `<div class="kpi"><b>${b}</b><span>${t}</span></div>`).join('');
}

function initMap() {
  const map = state.map = new maplibregl.Map({ container: 'map', style: STYLE, center: [80, 22.5], zoom: 4.1,
    attributionControl: { compact: true } });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
  map.on('style.load', () => {
    // Omit international boundaries from the basemap (official boundary: Survey of India).
    for (const l of map.getStyle().layers) {
      if (/boundary/i.test(l.id) && /country|admin_level_2|disputed|boundary_2|boundary_3/i.test(l.id + JSON.stringify(l.filter || '')))
        map.setLayoutProperty(l.id, 'visibility', 'none');
    }
    map.addSource('s2', { type: 'raster', tileSize: 256, maxzoom: 15,
      tiles: ['https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2023_3857/default/g/{z}/{y}/{x}.jpg'],
      attribution: 'Sentinel-2 cloudless 2023 by EOX (CC BY-NC-SA 4.0)' });
    map.addLayer({ id: 's2', type: 'raster', source: 's2', minzoom: 11, paint: { 'raster-opacity': 0.9 } });
    const polys = { type: 'FeatureCollection', features: state.sites.features.filter(f => f.geometry && f.geometry.type !== 'Point') };
    const pts = { type: 'FeatureCollection', features: state.sites.features.map(f => ({ type: 'Feature',
      properties: f.properties, geometry: { type: 'Point', coordinates: f.properties.lonlat } })) };
    map.addSource('polys', { type: 'geojson', data: polys });
    map.addSource('pts', { type: 'geojson', data: pts });
    const color = ['match', ['coalesce', ['get', 'trend'], 'unassessed'], ...Object.entries(COLORS).flat(), '#0f766e'];
    map.addLayer({ id: 'poly-fill', type: 'fill', source: 'polys', paint: { 'fill-color': color, 'fill-opacity': 0.28 } });
    map.addLayer({ id: 'poly-line', type: 'line', source: 'polys', paint: { 'line-color': color, 'line-width': 2 } });
    map.addLayer({ id: 'pts', type: 'circle', source: 'pts', maxzoom: 12, paint: {
      'circle-radius': ['interpolate', ['linear'], ['coalesce', ['get', 'legacy_waste_t'], 50000], 0, 4, 2000000, 9, 16000000, 16],
      'circle-color': ['case', ['==', ['get', 'mapped'], true], color, 'rgba(0,0,0,0)'],
      'circle-stroke-color': ['case', ['>', ['coalesce', ['get', 'fire_days'], 0], 0], '#b91c1c', '#0f766e'],
      'circle-stroke-width': ['case', ['>', ['coalesce', ['get', 'fire_days'], 0], 0], 2.5, 1.5], 'circle-opacity': 0.75 } });
    for (const id of ['pts', 'poly-fill']) {
      map.on('click', id, (e) => select(e.features[0].properties.site_id));
      map.on('mouseenter', id, () => map.getCanvas().style.cursor = 'pointer');
      map.on('mouseleave', id, () => map.getCanvas().style.cursor = '');
    }
  });
}

function applyFilters() {
  const q = $('#q').value.trim().toLowerCase(), st = $('#f-state').value, fs = $('#f-status').value;
  state.filtered = state.sites.features.map(f => f.properties).filter(p => {
    if (st && p.state !== st) return false;
    if (fs === 'mapped' && !p.mapped) return false;
    if (fs === 'unmapped' && p.mapped) return false;
    if (fs === 'fire' && !(p.fire_days > 0)) return false;
    if (fs === 'drap' && !p.drap_priority) return false;
    return !q || `${name(p)} ${p.city} ${p.state} ${p.ulb}`.toLowerCase().includes(q);
  }).sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0));
  $('#list').innerHTML = state.filtered.map(p => `<li data-id="${p.site_id}" class="${p.site_id === state.selected ? 'sel' : ''}">
    <div class="t">${name(p)}</div>
    <div class="s">${p.city}, ${p.state}${p.legacy_waste_t ? ' · ' + fmt.format(Math.round(p.legacy_waste_t / 1000)) + 'k t' : ''}</div>
    <div class="s">${p.drap_priority ? '<span class="badge drap">DRAP</span>' : ''}${p.fire_days ? `<span class="badge fire">${p.fire_days} fire days</span>` : ''}${p.mapped ? '' : '<span class="badge trace">needs tracing</span>'}</div></li>`).join('');
}

async function select(id) {
  const f = state.sites.features.find(x => x.properties.site_id === id);
  if (!f) return;
  state.selected = id; location.hash = id;
  document.querySelectorAll('#list li').forEach(li => li.classList.toggle('sel', li.dataset.id === id));
  const p = f.properties;
  const wide = window.innerWidth > 860;
  state.map && state.map.flyTo({ center: p.lonlat, zoom: p.mapped ? 15 : 11, speed: 1.6,
    padding: wide ? { right: 460, left: 0, top: 0, bottom: 0 } : { bottom: window.innerHeight * 0.6, top: 0, left: 0, right: 0 } });
  let d = {};
  try { d = await fetch(`data/sites/${id}.json`).then(r => r.ok ? r.json() : {}); } catch (e) {}
  const obs = d.imagery || [];
  const panel = $('#panel');
  panel.classList.remove('hidden');
  panel.innerHTML = `<button class="close" aria-label="Close">×</button>
    <h2>${name(p)}</h2>
    <div class="sub">${p.city}, ${p.state} · ULB: ${p.ulb}${p.drap_priority ? ' · DRAP priority site' : ''}</div>
    <div class="grid2">
      ${stat(p.legacy_waste_t ? fmt.format(p.legacy_waste_t) + ' t' : '—', 'legacy waste (DRAP annexure)')}
      ${stat(p.approved_cost_cr ? '₹' + p.approved_cost_cr + ' cr' : '—', 'approved remediation cost')}
      ${stat(p.area_ha ? p.area_ha + ' ha' : '—', 'traced site area (OSM)')}
      ${stat(p.pop_2km != null ? fmt.format(p.pop_2km) : '—', 'people within 2 km')}
    </div>
    ${p.mapped ? '' : `<p class="note">⚠ No reliable site boundary yet; marker shows the city centre. Help trace it on OpenStreetMap (landuse=landfill).</p>`}
    ${obs.length ? chipsBlock(obs) : '<p class="note">No imagery series yet for this site.</p>'}
    ${fireBlock(d.fires)}
    ${insarBlock(d.insar)}
    ${expoBlock(d.exposure)}
    ${d.assessment ? `<p class="note">Analyst: ${d.assessment.analyst ? d.assessment.analyst.model : 'rules'} · surface: ${(d.assessment.surface_type || '').replace(/_/g, ' ')} · trend: ${(d.assessment.remediation_trend || '').replace(/_/g, ' ')}</p>` : ''}
    ${d.pack_md ? `<div class="pack">${marked.parse(d.pack_md)}</div>` : (d.assessment ? '<p class="note">Evidence pack held for human review by the reviewer gate.</p>' : '<p class="note">Evidence pack pending agent review.</p>')}
    <p class="note">Observations from open satellite data; not a certificate of remediation. <a href="${window.REPO ? window.REPO + encodeURIComponent(p.site_id + ' ' + name(p)) : '#'}" target="_blank" rel="noopener">Right of reply / corrections</a></p>`;
  panel.querySelector('.close').onclick = () => { panel.classList.add('hidden'); history.replaceState(null, '', ' '); };
  if (obs.length) wireChips(panel, obs);
}

function stat(b, s) { return `<div class="stat"><b>${b}</b><span>${s}</span></div>`; }

function chipsBlock(obs) {
  const max = Math.max(...obs.map(o => o.site_area_ha || 0), 1);
  const pts = obs.map((o, i) => `${10 + i * (280 / Math.max(obs.length - 1, 1))},${55 - 45 * (o.exposed_ha / max)}`).join(' ');
  return `<h3>Sentinel-2 record (dry season)</h3>
  <div class="years">${obs.map((o, i) => `<button data-i="${i}" class="${i === obs.length - 1 ? 'on' : ''}">${o.year}</button>`).join('')}
    <button data-mode="swir" title="SWIR false colour: fresh refuse and burn scars stand out">SWIR</button></div>
  <div class="chips"><img alt="Sentinel-2 chip" id="chip"></div>
  <div class="note" id="chip-cap"></div>
  <svg class="spark" viewBox="0 0 300 60" role="img" aria-label="Exposed waste-like area by year">
    <polyline fill="none" stroke="var(--accent)" stroke-width="2.5" points="${pts}"/>
    ${obs.map((o, i) => `<circle cx="${10 + i * (280 / Math.max(obs.length - 1, 1))}" cy="${55 - 45 * (o.exposed_ha / max)}" r="3.5" fill="var(--accent)"><title>${o.year}: ${o.exposed_ha} ha</title></circle>`).join('')}
  </svg>
  <div class="note">Exposed waste-like surface inside the boundary (ha), ${obs[0].year}→${obs[obs.length - 1].year}: ${obs[0].exposed_ha} → ${obs[obs.length - 1].exposed_ha}. Footprint ≠ tonnage.</div>`;
}

function wireChips(panel, obs) {
  let i = obs.length - 1, swir = false;
  const show = () => {
    const o = obs[i];
    panel.querySelector('#chip').src = `data/chips/${swir ? o.chip_swir : o.chip_rgb}`;
    panel.querySelector('#chip-cap').textContent = `${o.date} · ${o.scene_id} · cloud ${o.cloud_cover}% · exposed ${o.exposed_ha} ha · vegetated ${o.veg_ha} ha`;
    panel.querySelectorAll('.years button[data-i]').forEach(b => b.classList.toggle('on', +b.dataset.i === i));
    panel.querySelector('.years button[data-mode]').classList.toggle('on', swir);
  };
  panel.querySelectorAll('.years button[data-i]').forEach(b => b.onclick = () => { i = +b.dataset.i; show(); });
  panel.querySelector('.years button[data-mode]').onclick = () => { swir = !swir; show(); };
  show();
}

function fireBlock(f) {
  if (!f) return '<h3>Fire record</h3><p class="note">No VIIRS detections attributed in the scanned period.</p>';
  return `<h3>Fire record</h3><p>${f.fire_days} day(s) with VIIRS 375 m detections touching the site (${f.first} → ${f.last}).</p>
  <p class="note">VIIRS misses small or smouldering fires and cannot see under the surface; detections are evidence of heat, not of cause.</p>`;
}

function insarBlock(ins) {
  if (!ins || !ins.series || !ins.series.length) return '';
  const pts = ins.series.filter(x => x.cumulative_mm != null);
  if (!pts.length) return '<h3>Mound movement (Sentinel-1 InSAR)</h3><p class="note">Radar pairs processed but decorrelated over the mound; no reliable measurement.</p>';
  const v = pts.map(x => x.cumulative_mm), lo = Math.min(0, ...v), hi = Math.max(0, ...v), rng = (hi - lo) || 1;
  const X = i => 10 + i * (280 / Math.max(pts.length - 1, 1)), Y = y => 55 - 45 * (y - lo) / rng;
  const d = s => `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
  return `<h3>Mound movement (Sentinel-1 InSAR)</h3>
  <svg class="spark" viewBox="0 0 300 60" role="img" aria-label="Cumulative vertical movement of the mound relative to surroundings">
    <line x1="0" x2="300" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--line)"/>
    <polyline fill="none" stroke="#7c3aed" stroke-width="2.5" points="${pts.map((x, i) => `${X(i)},${Y(x.cumulative_mm)}`).join(' ')}"/>
  </svg>
  <p class="note">Cumulative vertical movement of the mound relative to a 300–800 m ring, ${d(pts[0].d1)} → ${d(pts[pts.length - 1].d2)}: <b>${v[v.length - 1]} mm</b> (${pts.length} radar pairs). Negative = settling/sinking. C-band radar decorrelates on active tipping faces; treat as a screening signal, not a stability verdict.</p>`;
}

function expoBlock(e) {
  if (!e) return '';
  return `<h3>People living nearby (GHSL 2025)</h3><div class="grid2">${stat(fmt.format(e.pop_1km), 'within 1 km')}${stat(fmt.format(e.pop_2km), 'within 2 km')}${stat(fmt.format(e.pop_5km), 'within 5 km')}</div>`;
}

document.querySelectorAll('.tab[data-view]').forEach(t => t.onclick = async () => {
  document.querySelectorAll('.tab[data-view]').forEach(x => x.classList.toggle('active', x === t));
  $('#view-map').classList.toggle('hidden', t.dataset.view !== 'map');
  $('#view-method').classList.toggle('hidden', t.dataset.view !== 'method');
  if (t.dataset.view === 'method' && !$('#method').innerHTML)
    $('#method').innerHTML = marked.parse(await fetch('method.md').then(r => r.text()));
  if (t.dataset.view === 'map') state.map.resize();
});
['#q', '#f-state', '#f-status'].forEach(s => $(s).addEventListener('input', applyFilters));
$('#list').addEventListener('click', e => { const li = e.target.closest('li'); if (li) select(li.dataset.id); });
load();
