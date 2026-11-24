'use strict';

const { createReadStream } = require('node:fs');
const fs = require('node:fs/promises');
const path = require('node:path');
const { createInterface } = require('node:readline');
const { interactionResize } = require('./interactions.cjs');

const names = {
  groups: { vehicles: 'Vehicles', maps: 'Maps', tiers: 'Tiers', battles: 'Battles', interactions: 'Interactions' },
  ranges: {
    history: 'Full history', 'since-sunday': 'Since Sunday', 'before-sunday': 'Before Sunday',
    'recent-24h': 'Last 24 hours', 'empty-date': 'Empty date range', launch: 'Since launch',
    'manual-legacy': 'Since reset', sunday: 'Sunday', monday: 'Monday', installation: 'Installation'
  },
  metrics: {
    off: 'Chronology', battles: 'Battle count', win_rate: 'Win rate', xp_base: 'Base XP',
    xp_received: 'Received XP', battle_wn8: 'Battle WN8', credits_income_base: 'Base gross credits',
    credits_income_received: 'Received gross credits', credits_net_base: 'Base net credits',
    credits_net_received: 'Received net credits', credits_costs: 'Credit costs'
  },
  chronology: {
    newest: 'Last battle, newest first', oldest: 'First battle, oldest first', first_desc: 'First battle, newest first',
    last_asc: 'Last battle, oldest first', tier_asc: 'Tier ascending', tier_desc: 'Tier descending'
  },
  statistics: { min: 'Min', avg: 'Avg', max: 'Max', sum: 'Sum' },
  status: { pass: 'Passed', fail: 'Failed', diff: 'Visual difference', missing: 'Missing baseline' },
  interactions: {
    'sort-menu-end': 'Sort menu', calendar: 'Calendar', 'details-vehicles': 'Vehicle details',
    'details-maps': 'Map details', 'battle-selected': 'Selected battle', 'battle-resized': 'Window resized',
    'details-battles': 'Battle details', 'battle-returned': 'Return to source', failure: 'Failure screenshot'
  }
};

const languages = /^(en|pl|ru|fr|de|es|uk)$/;
const dimensions = /^([0-9]{3,4})x([0-9]{3,4})$/;
const numberedRange = /^point-[0-9]{2}-[0-9]{2}$/;
const variants = /^([a-z0-9_]+)-(min|avg|max|sum)-(asc|desc)-([a-z_]+)$/;
const owns = (object, key) => Object.hasOwn(object, key);
const count = value => Number.isSafeInteger(value) && value >= 0 ? value : null;
const safeVersion = value => typeof value === 'string' && /^[0-9]+(?:\.[0-9]+){1,5}(?:[-+][a-zA-Z0-9.-]{1,24})?$/.test(value)
  ? value : '';
const groupRanks = new Map(Object.keys(names.groups).map((name,index)=>[name,index]));
const rangeRanks = new Map(Object.keys(names.ranges).map((name,index)=>[name,index]));
const interactionStages = Object.keys(names.interactions).filter(name=>name!=='failure');
const ciJobs = {'render':'Chromium render shards','contracts':'Detailed Chromium contracts','download':'Shard download'};
const ciResults = {success:'Passed',failure:'Failed',cancelled:'Cancelled',skipped:'Skipped'};
const ciCoverage = ['build','smoke','full','exhaustive'];

function ciOutcomes(state) {
  if(!state.upstream) return [];
  return Object.entries(ciJobs).map(([key,name])=>{
    const result=state.upstream[key];
    const smokeSkip=key==='contracts'&&result==='skipped'&&state.coverage==='smoke';
    return {name,label:smokeSkip?'Skipped for smoke':owns(ciResults,result)?ciResults[result]:'Unavailable',
      failed:result!=='success'&&!smokeSkip};
  });
}

function caseFromKey(key) {
  if (typeof key !== 'string' || key.length > 132) return null;
  const parts = key.split('/');
  const interaction = parts[0] === 'interactions' && parts.length === 2;
  const size = dimensions.exec(parts[interaction ? 1 : 0]);
  if (!size) return null;
  const width = Number(size[1]), height = Number(size[2]);
  if (interaction) return { width, height, group:'interactions', key };
  if (parts.length !== 5) return null;
  const [, language, range, group, sort] = parts;
  const variant = variants.exec(sort);
  if (!languages.test(language) || !(owns(names.ranges, range) || numberedRange.test(range)) ||
      group === 'interactions' || !owns(names.groups, group) || !variant ||
      !owns(names.metrics, variant[1]) || !owns(names.chronology, variant[4])) return null;
  return { width, height, language, range, group, sort, key };
}

function frameFromShot(shot, row, phase) {
  if (!shot || typeof shot.image !== 'string' || !shot.image.startsWith(row.key + '/')) return null;
  const file = shot.image.slice(row.key.length + 1);
  const match = /^([a-z0-9-]+)\.(png|jpe?g)$/.exec(file);
  if (!match) return null;
  const name = match[1];
  if (row.group === 'interactions' ? !owns(names.interactions,name) : !/^(?:[0-3]|failure)$/.test(name)) return null;

  const ref = shot.reference === 'baseline/' + shot.image;
  const diff = shot.diff === 'differences/' + shot.image;
  const ratio = Number.isFinite(shot.difference) && shot.difference >= 0 && shot.difference <= 1 ? shot.difference : null;
  const frame = {file};
  if (phase) {
    frame.top = count(phase.top);
    frame.visible = count(phase.visible);
    frame.pinned = phase.pinned === true;
    frame.warning = phase.warning === true;
  }
  if (ratio !== null) frame.ratio = ratio;
  if (ref) frame.reference = true;
  if (diff) frame.diff = true;
  if (shot.visualFailure === true) frame.changed = true;
  if (shot.missingBaseline === true) frame.missing = true;
  return frame;
}

function hasRequiredCapture(result,row,capture) {
  const shots=result.shots;
  if(shots!==undefined&&(!Array.isArray(shots)||shots.length!==row.frames.length)) return false;
  const stages=new Set(row.frames.map(frame=>frame.file.split('.')[0]));
  if(stages.size!==row.frames.length) return false;
  if(shots?.some(shot=>(owns(shot,'reference')&&shot.reference!=='baseline/'+shot.image)||
      (owns(shot,'diff')&&shot.diff!=='differences/'+shot.image))) return false;
  if(row.issues.includes('fail')) return true;
  if(capture==='failures') return stages.size===0;
  const required = row.group==='interactions'
    ? interactionStages.filter(stage=>stage!=='battle-resized'||interactionResize(row.width,row.height))
    : capture==='final'?['3']:['0','1','2','3'];
  return required.length===stages.size&&required.every(stage=>stages.has(stage));
}

function publicCase(result,{capture}={}) {
  const row = caseFromKey(result?.key);
  if (!row) return null;
  const phases = Array.isArray(result.phases) ? result.phases.slice(0,4) : [];
  const shots = Array.isArray(result.shots) ? result.shots : [];
  row.frames = shots.slice(0,24).map(shot => frameFromShot(shot,row,phases.find(phase => phase?.image === shot?.image)))
    .filter(Boolean);
  const issues = [];
  if (result.error || result.screenshotError) issues.push('fail');
  if (row.frames.some(frame=>frame.changed)) issues.push('diff');
  if (row.frames.some(frame=>frame.missing)) issues.push('missing');
  row.issues = issues.length ? issues : ['pass'];
  return capture&&!hasRequiredCapture(result,row,capture)?null:row;
}

function compareCases(a,b) {
  const rangeA = rangeRanks.get(a.range) ?? rangeRanks.size;
  const rangeB = rangeRanks.get(b.range) ?? rangeRanks.size;
  return groupRanks.get(a.group)-groupRanks.get(b.group) ||
    rangeA-rangeB || (a.range||'').localeCompare(b.range||'') ||
    a.width-b.width || a.height-b.height || (a.language||'').localeCompare(b.language||'') ||
    (a.sort||'').localeCompare(b.sort||'');
}

function showMatrix(names) {
  const { rows, summary } = window.sessionStatsMatrix;
  const byId = id => document.getElementById(id);
  const add = (parent, tag, text) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    parent.append(el);
    return el;
  };
  const link = (parent, title, relative) => {
    const el = add(parent,'a',title);
    el.href = relative.split('/').map(encodeURIComponent).join('/');
    el.target = '_blank';
    el.rel = 'noopener';
    return el;
  };
  const rangeName = value => {
    if (names.ranges[value]) return names.ranges[value];
    const parts = value?.split('-');
    if (!parts) return '—';
    const from = Number(parts[1]), to = Number(parts[2]);
    return (from ? 'Point '+from : 'Start') + ' → ' + (to ? 'Point '+to : 'Now');
  };
  const sortName = value => {
    if (!value) return '—';
    const [metric,stat,direction,chronology] = value.split('-');
    if (metric === 'off') return names.chronology[chronology];
    return [names.metrics[metric],names.statistics[stat],direction==='asc'?'↑':'↓'].join(' ');
  };
  const frameName = (row,frame) => {
    const name=frame.file.split('.')[0];
    if (name === 'failure') return names.interactions.failure;
    if (row.group === 'interactions') return names.interactions[name];
    return name === '0' ? 'Initial view' : 'Scroll ' + name;
  };
  const filters = [];
  let page = 0, found = rows;
  const pageSize = 60;
  function filter(title, key, labels) {
    const label = add(byId('filters'),'label',title);
    const select = add(label,'select');
    const values = [...new Set(rows.flatMap(row=>Array.isArray(row[key]) ? row[key] : [row[key]]))]
      .filter(value=>value!==undefined);
    if (key === 'width' || key === 'height') values.sort((a,b)=>a-b);
    if (key === 'sort' || key === 'language') values.sort((a,b)=>labels(a).localeCompare(labels(b),'en'));
    select.append(new Option('All',''));
    for (const value of values) select.append(new Option(labels(value),String(value)));
    filters.push([key,select]);
    select.addEventListener('change',refresh);
  }

  function refresh() {
    found = rows.filter(row=>filters.every(([key,select]) => !select.value ||
      (Array.isArray(row[key]) ? row[key].includes(select.value) : String(row[key]) === select.value)));
    page = 0;
    render();
  }

  function showFrame(row, selected) {
    const box = byId('viewer');
    const controls = byId('frame-actions');
    const links = byId('frame-links');
    const image = byId('image');
    controls.replaceChildren();
    links.replaceChildren();
    byId('detail-title').textContent = names.groups[row.group] + ' · ' + row.width + ' × ' + row.height;
    byId('detail-context').textContent = [
      row.range ? rangeName(row.range) : '', row.language?.toUpperCase(), row.sort ? sortName(row.sort) : ''
    ].filter(Boolean).join(' · ');
    row.frames.forEach(frame => {
      const button = add(controls,'button',frameName(row,frame));
      button.type = 'button';
      button.setAttribute('aria-pressed',String(frame===selected));
      button.addEventListener('click',()=>showFrame(row,frame));
    });
    const framePath = row.key + '/' + selected.file;
    byId('image-link').href = framePath.split('/').map(encodeURIComponent).join('/');
    image.src = byId('image-link').getAttribute('href');
    image.alt = frameName(row,selected) + ' · ' + names.groups[row.group];
    link(links,'Open image',framePath);
    if (selected.reference) link(links,'Baseline','baseline/'+framePath);
    if (selected.diff) link(links,'Difference','differences/'+framePath);
    const metrics = [];
    if (selected.top != null) metrics.push('Scroll offset '+selected.top+' px');
    if (selected.visible != null) metrics.push('Visible cards '+selected.visible);
    if (selected.pinned) metrics.push('Pinned filters');
    if (selected.warning) metrics.push('Panel warning');
    if (selected.ratio != null) metrics.push('Difference '+(selected.ratio*100).toFixed(3)+'%');
    if (selected.missing) metrics.push(names.status.missing);
    byId('frame-metrics').textContent = metrics.join(' · ');
    if (!box.open) box.showModal();
  }

  function render() {
    const body = byId('rows');
    body.replaceChildren();
    const pageStart = page*pageSize, visible = found.slice(pageStart,pageStart+pageSize);
    let lastGroup, lastRange;
    for (const row of visible) {
      if (lastGroup!==row.group || lastRange!==row.range) {
        const group = add(body,'tr');
        group.className = 'group';
        const label = add(group,'th',[names.groups[row.group],row.range ? rangeName(row.range) : ''].filter(Boolean).join(' · '));
        label.colSpan = 5;
        label.scope = 'row';
        lastGroup = row.group;
        lastRange = row.range;
      }
      const tr = add(body,'tr');
      add(tr,'td',row.width+' × '+row.height);
      add(tr,'td',row.language?.toUpperCase()||'—');
      add(tr,'td',sortName(row.sort));
      const status = add(tr,'td',row.issues.map(issue=>names.status[issue]).join(' · '));
      if (!row.issues.includes('pass')) status.className='failed';
      const frames = add(add(tr,'td'),'div');
      frames.className = 'actions';
      for (const frame of row.frames) {
        const button = add(frames,'button',frameName(row,frame));
        button.type = 'button';
        button.addEventListener('click',()=>showFrame(row,frame));
      }
      if (!row.frames.length) add(frames,'span','—');
    }
    const first = visible.length ? pageStart+1 : 0;
    byId('matches').textContent = String(found.length) + (found.length === 1 ? ' case' : ' cases') +
      (visible.length ? ' · '+first+'–'+(pageStart+visible.length) : '');
    byId('previous').disabled = page===0;
    byId('next').disabled = pageStart+visible.length>=found.length;
    byId('empty').hidden = !!visible.length;
  }

  filter('Tab','group',value=>names.groups[value]);
  filter('Date range','range',rangeName);
  filter('Width','width',value=>value+' px');
  filter('Height','height',value=>value+' px');
  filter('Language','language',value=>value.toUpperCase());
  filter('Sort order','sort',sortName);
  filter('Status','issues',value=>names.status[value]);
  byId('previous').onclick=()=>{page--;render();};
  byId('next').onclick=()=>{page++;render();};
  byId('reset').onclick=()=>{filters.forEach(([,select])=>{select.value='';});refresh();};
  byId('viewer').addEventListener('close',()=>{byId('image').removeAttribute('src');});
  byId('title').textContent = 'Session Stats' + (summary.version ? ' '+summary.version : '');
  byId('summary').textContent = [
    summary.engine, summary.renderer, summary.coverage || summary.suite,
    summary.commit ? `Commit ${summary.commit.slice(0, 12)}` : '',
    summary.expectedShards === null ? '' : 'Shards '+summary.shards+'/'+summary.expectedShards,
    'Cases '+summary.completed+'/'+summary.planned,
    'Case failures '+summary.failures, 'Visual differences '+summary.visualFailures,
    summary.missingBaselines ? 'Missing baselines '+summary.missingBaselines : '',
    'Screenshots '+summary.frames, summary.omitted ? 'Omitted entries '+summary.omitted : ''
  ].filter(Boolean).join(' · ');
  render();
}

async function writeReport(directory,state) {
  const rows = [];
  let omitted = 0, frames = 0;
  const input = createReadStream(path.join(directory,'results.ndjson'),{encoding:'utf8'});
  const lines = createInterface({input,crlfDelay:Infinity});
  for await (const line of lines) {
    if (!line.trim()) continue;
    let result;
    try { result = JSON.parse(line); }
    catch { omitted++; continue; }
    const row = publicCase(result);
    if (!row) { omitted++; continue; }
    rows.push(row);
    frames += row.frames.length;
  }
  rows.sort(compareCases);
  omitted += count(state.omittedRows) ?? 0;
  const jobs=ciOutcomes(state);
  const summary = {
    version:safeVersion(state.version),
    commit:typeof state.commit==='string'&&/^[a-f0-9]{40}$/.test(state.commit)?state.commit:undefined,
    engine:['chromium','gameface'].includes(state.engine) ? state.engine : '',
    renderer:safeVersion(state.renderer),
    suite:['smoke','full','build','quick'].includes(state.suite) ? state.suite : '',
    coverage:ciCoverage.includes(state.coverage) ? state.coverage : undefined,
    planned:count(state.planned) ?? rows.length, completed:count(state.completed) ?? rows.length,
    failures:(count(state.failed) ?? 0)+(count(state.interactionErrors) ?? 0),
    visualFailures:count(state.visualFailures) ?? 0, missingBaselines:count(state.missingBaselines) ?? 0, frames, omitted,
    incomplete:state.finished===false||omitted>0,
    shards:count(state.shards), expectedShards:count(state.expectedShards),
    jobs
  };
  const failed=Boolean(summary.failures||summary.visualFailures||summary.missingBaselines||jobs.some(job=>job.failed));
  const verdict=failed?'Run failed':summary.incomplete?'Run incomplete':jobs.length?'Run passed':'Render checks passed';
  const jobStatus=jobs.length
    ? `<ul aria-label="CI jobs">${jobs.map(job=>`<li${job.failed?' class="failed"':''}>${job.name} · ${job.label}</li>`).join('')}</ul>`
    : state.legacyComment ? '<p>Upstream CI status is unavailable in this report. See the GitHub Actions run for the overall result.</p>' : '';

  await fs.writeFile(path.join(directory,'catalog.js'),
    'window.sessionStatsMatrix = '+JSON.stringify({rows,summary})+';\n');
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Session Stats · Test results</title>
<style>
:root{color-scheme:dark;background:#151910;color:#eeeada;font:15px/1.45 system-ui,sans-serif}
body{margin:0 auto;padding:1rem;max-width:88rem}h1,h2{margin:.2rem 0}a{color:#a8d8ff}
#summary,#detail-context,#frame-metrics{color:#c4c9b8}#filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(9rem,1fr));gap:.6rem;margin:1rem 0}
label{display:grid;gap:.25rem}button,select{font:inherit;padding:.35rem .55rem;min-width:0;background:#252b20;border:1px solid #676f5d;border-radius:.25rem;color:inherit}
button[aria-pressed=true]{background:#424c35;border-color:#abb989}button:disabled{opacity:.55}button:not(:disabled){cursor:pointer}
.pager,.actions{display:flex;align-items:center;flex-wrap:wrap;gap:.4rem}.pager{margin:1rem 0}
main{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left}th,td{border-bottom:1px solid #3c4736;padding:.45rem .6rem;vertical-align:top}
.group{background:#272f22}.failed{color:#ff9da7}dialog{padding:1rem;background:#20271c;border:1px solid #626d51;border-radius:.45rem;width:min(72rem,calc(100% - 3rem));max-height:90vh}dialog::backdrop{background:#000a}
dialog form{float:right}dialog img{display:block;max-width:100%;max-height:65vh;margin:auto;object-fit:contain}dialog #image-link{display:block;margin:1rem 0}
</style>
</head>
<body>
<h1 id="title">Session Stats</h1>
<p id="verdict"${failed||summary.incomplete?' class="failed"':''}><strong>${verdict}</strong></p>
${failed&&summary.incomplete?'<p>Partial case coverage</p>':''}
${jobStatus}
<p id="summary"></p>
<div id="filters"></div>
<nav class="pager" aria-label="Test case pages">
<button id="previous" type="button">Previous</button><span id="matches" aria-live="polite"></span><button id="next" type="button">Next</button>
<button id="reset" type="button">Clear filters</button>
</nav>
<main>
<table>
<thead><tr><th scope="col">Window</th><th scope="col">Language</th><th scope="col">Sort order</th><th scope="col">Status</th><th scope="col">Screenshots</th></tr></thead>
<tbody id="rows"></tbody>
</table>
<p id="empty" hidden>No test cases match the selected filters.</p>
</main>
<dialog id="viewer" aria-labelledby="detail-title">
<form method="dialog"><button>Close</button></form>
<h2 id="detail-title"></h2>
<p id="detail-context"></p>
<div id="frame-actions" class="actions"></div>
<a id="image-link" target="_blank" rel="noopener"><img id="image" alt=""></a>
<div id="frame-links" class="actions"></div>
<p id="frame-metrics"></p>
</dialog>
<script src="catalog.js"></script>
<script>(${showMatrix.toString()})(${JSON.stringify(names)});</script>
</body>
</html>`;
  await fs.writeFile(path.join(directory,'index.html'),html);
}

module.exports = { ciJobs, ciResults, ciCoverage, ciOutcomes, publicCase, writeReport };
