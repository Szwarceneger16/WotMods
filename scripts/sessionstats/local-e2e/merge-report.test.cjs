'use strict';

const assert = require('node:assert/strict');
const { execFileSync, spawnSync } = require('node:child_process');
const { readFileSync } = require('node:fs');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');
const { deflateSync } = require('node:zlib');

const scenario = {key:'625x730/en/history/vehicles/xp_received-sum-desc-newest'};
const interaction = {key:'interactions/625x730'};
const compactInteraction = {key:'interactions/365x730'};
const interactionStages = ['sort-menu-end','calendar','details-vehicles','details-maps','battle-selected',
  'battle-resized','details-battles','battle-returned'];
const failure = 'Synthetic test failure';
const tinyJpeg = Buffer.from(
  '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/'+
  '2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/'+
  '8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAABQf/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/'+
  '9oADAMBAAIRAxEAPwCOALiMf//Z','base64');
// Pillow Image.new('RGB', (645, 750), 'blue').save(..., optimize=True).
// A single solid color generated without any screen, player, or account input.
const blueJpeg = readFileSync(path.join(__dirname,'fixtures','viewport-645x750.jpg'));

function pngChunk(name,data) {
  const length=Buffer.alloc(4), checksum=Buffer.alloc(4);
  const payload=Buffer.concat([Buffer.from(name,'ascii'),data]);
  let crc=-1;
  for(const byte of payload) {
    crc^=byte;
    for(let bit=0;bit<8;bit++) crc=(crc>>>1)^((crc&1)?0xedb88320:0);
  }
  length.writeUInt32BE(data.length);
  checksum.writeUInt32BE((~crc)>>>0);
  return Buffer.concat([length,payload,checksum]);
}

function solidPng(width,height,color) {
  const header=Buffer.alloc(13);
  header.writeUInt32BE(width);
  header.writeUInt32BE(height,4);
  header[8]=8;header[9]=2;
  const stride=width*3+1, pixels=Buffer.alloc(height*stride,color);
  for(let row=0;row<pixels.length;row+=stride) pixels[row]=0;
  return Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),pngChunk('IHDR',header),
    pngChunk('IDAT',deflateSync(pixels)),pngChunk('IEND',Buffer.alloc(0))]);
}

const redPng=solidPng(645,750,0x65), greenPng=solidPng(645,750,0x73);
const compactPng=solidPng(385,750,0x65), tinyPng=solidPng(1,1,0x65);
const captured=(row,stages,ext='png')=>({...row,shots:stages.map(stage=>({image:`${row.key}/${stage}.${ext}`}))});
const capturedInteraction=captured(interaction,interactionStages);
const interactionImages=Object.fromEntries(capturedInteraction.shots.map(({image})=>[image,redPng]));
const manifest = {
  engine:'chromium', fixture:'synthetic', assets:'test-art', version:'0.9.30', suite:'build',
  capture:'failures', shard:'1/1', planned:1, completed:1, failed:0, interactions:1, interactionErrors:0,
  visualFailures:0, missingBaselines:0, finished:true
};

async function merge(t, {state={}, rows=[scenario,interaction], expected=1, missing=false,
  rawManifest, rawLedger, images={}, additional=[], identity={}, coverage, upstream={}, env={}}={}) {
  const directory = await fs.mkdtemp(path.join(await fs.realpath(os.tmpdir()),'sessionstats-merge-'));
  t.after(async()=>fs.rm(directory,{recursive:true,force:true}));
  const output = path.join(directory,'report');
  const args = [path.join(__dirname,'merge-report.cjs'),'--out',output,'--expected-shards',String(expected)];
  for(const [key,value] of Object.entries(identity)) args.push('--expected-'+key,value);
  if(coverage!==undefined) args.push('--coverage',coverage);
  for(const [key,value] of Object.entries(upstream)) args.push('--'+key+'-result',value);
  const inputs=missing ? [] : [{state,rows,rawManifest,rawLedger,images},...additional];
  for(const [index,input] of inputs.entries()) {
    const shard=path.join(directory,'shard-'+index);
    await fs.mkdir(shard);
    await fs.writeFile(path.join(shard,'run.json'),input.rawManifest??JSON.stringify({...manifest,...input.state}));
    const ledger=(input.rows??[scenario,interaction]).map(row=>JSON.stringify(row)+'\n').join('');
    await fs.writeFile(path.join(shard,'results.ndjson'),input.rawLedger??ledger);
    for(const [relative,contents] of Object.entries(input.images??{})) {
      const image=path.join(shard,relative);
      await fs.mkdir(path.dirname(image),{recursive:true});
      await fs.writeFile(image,contents);
    }
    args.push(shard);
  }
  const result = spawnSync(process.execPath,args,{encoding:'utf8',env:{...process.env,...env}});
  assert.ifError(result.error);
  if(inputs.some(input=>input.state?.fixture&&input.state.fixture!=='synthetic')) {
    await assert.rejects(fs.access(output),{code:'ENOENT'});
    return {result};
  }
  const summary = JSON.parse(await fs.readFile(path.join(output,'run.json'),'utf8'));
  const html = await fs.readFile(path.join(output,'index.html'),'utf8');
  const catalogue = await fs.readFile(path.join(output,'catalog.js'),'utf8');
  assert.match(html, /<script src="catalog\.js"><\/script>/);
  assert.match(html, /id="verdict"/);
  assert.ok(!catalogue.includes(failure));
  const data=JSON.parse(catalogue.slice('window.sessionStatsMatrix = '.length).trimEnd().slice(0,-1));
  return {result,summary,data,html,output};
}

test('succeeds only after matching one scenario and one interaction to the manifest', async t => {
  const {result,summary} = await merge(t);
  assert.equal(result.status,0);
  assert.equal(summary.finished,true);
  assert.equal(summary.completed,1);
  assert.equal(summary.interactions,1);
});

test('includes battle WN8 cases and their images in the merged catalogue',async t=>{
  const row=captured({key:'625x730/en/history/tiers/battle_wn8-min-desc-tier_desc'},[3],'jpg');
  const image=row.shots[0].image;
  const {result,summary,data}=await merge(t,{
    state:{capture:'final',interactions:0},rows:[row],images:{[image]:blueJpeg}
  });
  assert.equal(result.status,0,result.stderr);
  assert.equal(summary.omittedRows,0);
  assert.equal(data.rows[0].key,row.key);
  assert.deepEqual(data.rows[0].frames,[{file:'3.jpg'}]);
});

test('reports a failed detailed Chromium job even when every rendered case passed',async t=>{
  const upstream={render:'success',contracts:'failure',download:'success'};
  const {result,summary,data,html}=await merge(t,{upstream,state:{upstream:{...upstream,contracts:'success'}}});
  assert.equal(result.status,1);
  assert.match(result.stderr,/Detailed Chromium contracts: Failed/);
  assert.equal(summary.finished,true);
  assert.equal(data.summary.failures,0);
  assert.deepEqual(data.rows.map(row=>row.issues),[['pass'],['pass']]);
  assert.match(html,/<strong>Run failed<\/strong>/);
  assert.match(html,/<li class="failed">Detailed Chromium contracts · Failed<\/li>/);
});

test('reports other upstream failures and accepts only a skip in the requested smoke coverage',async t=>{
  for(const [suite,upstream,jobStatus,exit] of [
    ['full',{render:'failure',contracts:'success',download:'success'},'Chromium render shards · Failed',1],
    ['full',{render:'success',contracts:'success',download:'failure'},'Shard download · Failed',1],
    ['full',{render:'success',contracts:'cancelled',download:'success'},'Detailed Chromium contracts · Cancelled',1],
    ['full',{render:'success',contracts:'skipped',download:'success'},'Detailed Chromium contracts · Skipped',1],
    ['build',{render:'success',contracts:'skipped',download:'success'},'Detailed Chromium contracts · Skipped for smoke',0],
  ]) {
    await t.test(jobStatus,async check=>{
      const coverage=suite==='build'?'smoke':'full';
      const {result,summary,data,html}=await merge(check,{upstream,coverage,state:{suite}});
      assert.equal(result.status,exit);
      assert.equal(summary.suite,suite);
      assert.equal(summary.coverage,coverage);
      assert.equal(data.summary.coverage,coverage);
      assert.deepEqual(summary.upstream,upstream);
      assert.ok(html.includes(jobStatus));
      assert.match(html,exit?/Run failed/:/Run passed/);
    });
  }
});

test('a shard cannot claim smoke coverage and hide a skipped required job',async t=>{
  const upstream={render:'success',contracts:'skipped',download:'success'};
  const {result,summary,html}=await merge(t,{upstream,coverage:'full',state:{suite:'build',coverage:'smoke'}});
  assert.equal(result.status,1);
  assert.equal(summary.coverage,'full');
  assert.match(html,/<li class="failed">Detailed Chromium contracts · Skipped<\/li>/);
});

test('a manual report uses rendered cases and ignores purported job outcomes in the shard',async t=>{
  const {result,data,html}=await merge(t,{state:{upstream:{render:'failure',contracts:'failure',download:'failure'}}});
  assert.equal(result.status,0);
  assert.deepEqual(data.summary.jobs,[]);
  assert.match(html,/Render checks passed/);
  assert.doesNotMatch(html,/Detailed Chromium contracts ·/);
});

test('an older comment workflow uses the actual checkout, never the default-branch event SHA',async t=>{
  const cwd=path.resolve(__dirname,'../../..');
  const stamp=execFileSync('git',['rev-parse','--verify','HEAD'],{cwd,encoding:'utf8'}).trim();
  const version=readFileSync(path.join(cwd,'mods/sessionstats/VERSION'),'utf8').trim();
  const unrelated=stamp==='e'.repeat(40)?'f'.repeat(40):'e'.repeat(40);
  const env={GITHUB_ACTIONS:'true',GITHUB_EVENT_NAME:'issue_comment',GITHUB_SHA:unrelated};
  const {result,summary,data,html}=await merge(t,{env,state:{commit:unrelated,version},additional:[
    {state:{commit:stamp,version}},
  ]});
  assert.equal(result.status,1);
  assert.match(result.stderr,/does not match the requested version, suite, capture mode or commit/);
  assert.equal(summary.commit,stamp);
  assert.equal(summary.shards,1);
  assert.equal(data.summary.commit,stamp);
  assert.equal(data.rows.length,2);
  assert.match(html,/Upstream CI status is unavailable in this report/);
});

test('a recorded failure fails the run while keeping its report', async t => {
  const {result,summary} = await merge(t,{state:{failed:1},rows:[{...scenario,error:failure},interaction]});
  assert.equal(result.status,1);
  assert.equal(summary.finished,true);
  assert.equal(summary.failed,1);
});

test('counts test failures even if the claimed totals say zero', async t => {
  const {result,summary} = await merge(t,{rows:[
    {...scenario,error:failure},
    {...interaction,error:failure},
  ]});
  assert.equal(result.status,1);
  assert.match(result.stderr,/inconsistent test results/);
  assert.equal(summary.finished,false);
  assert.equal(summary.failed,1);
  assert.equal(summary.interactionErrors,1);
});

test('marks missing ledger rows and invalid plans as incomplete', async t => {
  for(const [title,options,completed] of [
    ['missing case', {rows:[interaction]}, 0],
    ['missing interaction', {rows:[scenario]}, 1],
    ['empty plan', {state:{planned:0,completed:0,interactions:0},rows:[]}, 0],
    ['finished before all planned cases', {state:{planned:2}}, 1],
  ]) {
    await t.test(title,async check=>{
      const {result,summary} = await merge(check,options);
      assert.equal(result.status,1);
      assert.equal(summary.finished,false);
      assert.equal(summary.completed,completed);
    });
  }
});

test('publishes an incomplete report if shard artefacts are unavailable', async t => {
  for(const [title,options,shards] of [
    ['all expired', {missing:true}, 0],
    ['one missing', {expected:2,state:{shard:'1/2'}}, 1],
  ]) {
    await t.test(title,async check=>{
      const {result,summary,data} = await merge(check,options);
      assert.equal(result.status,1);
      assert.equal(summary.finished,false);
      assert.equal(summary.completed,shards);
      assert.equal(summary.shards,shards);
      assert.equal(data.summary.incomplete,true);
      assert.equal(data.summary.shards,shards);
      assert.equal(data.summary.expectedShards,options.expected??1);
    });
  }
});

test('rejects a private fixture before creating any output', async t => {
  const {result} = await merge(t,{expected:2,state:{shard:'1/2'},
    additional:[{state:{shard:'2/2',fixture:'local-aggregate'}}]});
  assert.equal(result.status,1);
  assert.match(result.stderr,/Only synthetic Chromium/);
});

test('skips a damaged manifest and publishes healthy shard results', async t => {
  const {result,summary,data}=await merge(t,{expected:2,rawManifest:'{"fixture":',
    rows:[{key:'1220x900/en/history/maps/xp_received-sum-desc-newest'}],
    additional:[{state:{shard:'2/2'}}]});
  assert.equal(result.status,1);
  assert.match(result.stderr,/manifest could not be read/);
  assert.equal(summary.finished,false);
  assert.equal(summary.shards,1);
  assert.equal(summary.completed,1);
  assert.deepEqual(data.rows.map(row=>row.key),[scenario.key,interaction.key]);
  assert.equal(data.summary.incomplete,true);
});

test('skips malformed provenance without reading the affected shard', async t => {
  const untrusted={key:'1220x900/en/history/maps/xp_received-sum-desc-newest'};
  const {result,summary,data}=await merge(t,{expected:2,state:{shard:'1/2',fixture:null,assets:[]},
    rows:[untrusted],additional:[{state:{shard:'2/2'}}]});
  assert.equal(result.status,1);
  assert.match(result.stderr,/manifest has invalid/);
  assert.equal(summary.shards,1);
  assert.equal(summary.finished,false);
  assert.deepEqual(data.rows.map(row=>row.key),[scenario.key,interaction.key]);
});

test('malformed shard numbers do not coerce objects or claim a healthy shard number', async t => {
  for(const shard of [{toString:'1/2'}, ['1/2'], 12, null]) {
    await t.test(JSON.stringify(shard),async check=>{
      const healthy=await merge(check,{expected:2,state:{shard},rawLedger:'{"key":',
        additional:[{state:{shard:'1/2'}}]});
      assert.equal(healthy.result.status,1);
      assert.match(healthy.result.stderr,/manifest has invalid/);
      assert.equal(healthy.summary.shards,1);
      assert.equal(healthy.summary.finished,false);
      assert.deepEqual(healthy.data.rows.map(row=>row.key),[scenario.key,interaction.key]);
    });
  }
});

test('a stale first artifact cannot set the CI report identity or reserve a shard number', async t => {
  const identity={version:manifest.version,suite:'full',capture:'final',commit:'a'.repeat(40)};
  const image=scenario.key+'/3.jpg';
  for(const [field,value] of [['version','0.9.29'], ['suite','build'], ['capture','failures'],
    ['commit','b'.repeat(40)], ['commit',undefined]]) {
    await t.test(value===undefined?'missing '+field:'different '+field,async check=>{
      const {result,summary,data}=await merge(check,{identity,state:{...identity,[field]:value},
        rawLedger:'{"key":',additional:[{state:identity,rows:[{...scenario,shots:[{image}]},capturedInteraction],
          images:{[image]:blueJpeg,...interactionImages}}]});
      assert.equal(result.status,1);
      assert.match(result.stderr,/does not match the requested version, suite, capture mode or commit/);
      assert.equal(summary.finished,false);
      assert.equal(summary.shards,1);
      assert.equal(summary.completed,1);
      for(const [key,expected] of Object.entries(identity)) assert.equal(summary[key],expected);
      assert.equal(data.summary.commit,identity.commit);
      assert.deepEqual(data.rows.map(row=>row.key),[scenario.key,interaction.key]);
    });
  }
});

test('an empty CI report names the requested run', async t => {
  const identity={version:'1.2.3',suite:'build',capture:'all'};
  const {result,summary,data}=await merge(t,{missing:true,identity});
  assert.equal(result.status,1);
  assert.equal(summary.shards,0);
  assert.equal(summary.finished,false);
  assert.equal(data.summary.version,identity.version);
  assert.equal(data.summary.suite,identity.suite);
});

test('checks run identity fields before accepting a shard as the report identity', async t => {
  for(const damaged of [{version:null},{suite:'unknown'},{capture:false}]) {
    const {result,summary,data}=await merge(t,{expected:2,state:{shard:'1/2',...damaged},
      rawLedger:'{"key":',additional:[{state:{shard:'2/2'}}]});
    assert.equal(result.status,1);
    assert.match(result.stderr,/manifest has invalid/);
    assert.equal(summary.version,manifest.version);
    assert.equal(summary.shards,1);
    assert.equal(summary.finished,false);
    assert.deepEqual(data.rows.map(row=>row.key),[scenario.key,interaction.key]);
  }
});

test('keeps valid ledger rows after a damaged row and continues the other shards', async t => {
  const other={key:'1220x900/en/history/maps/xp_received-sum-desc-newest'};
  const nextInteraction={key:'interactions/1220x900'};
  const {result,summary,data}=await merge(t,{expected:2,state:{shard:'1/2'},
    rawLedger:JSON.stringify(scenario)+'\n{"key":\n'+JSON.stringify(interaction)+'\n',
    additional:[{state:{shard:'2/2'},rows:[other,nextInteraction]}]});
  assert.equal(result.status,1);
  assert.equal(summary.finished,false);
  assert.equal(summary.shards,2);
  assert.equal(summary.completed,2);
  assert.equal(summary.interactions,2);
  assert.equal(data.summary.incomplete,true);
  assert.equal(data.summary.omitted,1);
  assert.deepEqual(data.rows.map(row=>row.key),[scenario.key,other.key,interaction.key,nextInteraction.key]);
});

test('a damaged row releases its copied screenshots so a later valid case can be recovered', async t => {
  const first=scenario.key+'/0.png';
  const missing=scenario.key+'/1.png';
  const row=captured(scenario,['0','1','2','3']);
  const {result,summary,data,output}=await merge(t,{expected:2,state:{shard:'1/2',interactions:0,capture:'all'},
    rows:[row],
    images:{[first]:redPng},
    additional:[{state:{shard:'2/2',interactions:0,capture:'all'},rows:[row],
      images:Object.fromEntries(row.shots.map(({image})=>[image,greenPng]))}]});
  assert.equal(result.status,1);
  assert.equal(summary.finished,false);
  assert.equal(summary.completed,1);
  assert.equal(data.summary.omitted,1);
  assert.deepEqual(data.rows.map(row=>row.key),[scenario.key]);
  assert.deepEqual(await fs.readFile(path.join(output,first)),greenPng);
  assert.deepEqual(await fs.readFile(path.join(output,missing)),greenPng);
});

test('rejects a duplicate without replacing a committed case or its screenshot', async t => {
  const image=scenario.key+'/3.png';
  const rows=[{...scenario,shots:[{image}]}];
  const {result,summary,data,output}=await merge(t,{expected:2,state:{shard:'1/2',interactions:0,capture:'final'},
    rows,images:{[image]:redPng},
    additional:[{state:{shard:'2/2',interactions:0,capture:'final'},rows,images:{[image]:greenPng}}]});
  assert.equal(result.status,1);
  assert.equal(summary.finished,false);
  assert.equal(summary.completed,1);
  assert.equal(data.summary.omitted,1);
  assert.deepEqual(data.rows.map(row=>row.key),[scenario.key]);
  assert.deepEqual(await fs.readFile(path.join(output,image)),redPng);
});

test('final capture accepts the last screenshot and named interaction screenshots', async t => {
  const image=scenario.key+'/3.jpg', action=interaction.key+'/calendar.png';
  const {result,summary,data,output}=await merge(t,{state:{capture:'final'},
    rows:[{...scenario,shots:[{image}]},capturedInteraction],
    images:{[image]:blueJpeg,...interactionImages}});
  assert.equal(result.status,0);
  assert.equal(summary.finished,true);
  assert.deepEqual(data.rows.map(row=>row.frames.map(frame=>frame.file)),[['3.jpg'],interactionStages.map(stage=>stage+'.png')]);
  assert.deepEqual(await fs.readFile(path.join(output,image)),blueJpeg);
  assert.deepEqual(await fs.readFile(path.join(output,action)),redPng);
});

test('all capture accepts four screenshot phases', async t => {
  const shots=Array.from({length:4},(_,index)=>({image:`${scenario.key}/${index}.png`}));
  const images={...Object.fromEntries(shots.map(({image})=>[image,redPng])),...interactionImages};
  const {result,summary,data}=await merge(t,{state:{capture:'all'},rows:[{...scenario,shots},capturedInteraction],images});
  assert.equal(result.status,0);
  assert.equal(summary.finished,true);
  assert.equal(data.rows[0].frames.length,4);
});

test('a successful matrix case cannot pass with missing, malformed or incomplete screenshots', async t => {
  const image=scenario.key+'/3.jpg', wrongPhase=scenario.key+'/2.jpg';
  for(const [title,capture,shots,images] of [
    ['no screenshot', 'final', [], {}],
    ['non-array screenshots', 'final', {image}, {}],
    ['wrong phase', 'final', [{image:wrongPhase}], {[wrongPhase]:blueJpeg}],
    ['malformed filename', 'final', [{image:scenario.key+'/../3.jpg'}], {}],
    ['malformed extra screenshot', 'final', [{image},{image:'outside/shot.jpg'}], {[image]:blueJpeg}],
    ['malformed optional reference', 'final', [{image,reference:'private.png'}], {[image]:blueJpeg}],
    ['file missing', 'final', [{image}], {}],
    ['file invalid', 'final', [{image}], {[image]:'not a JPEG'}],
    ['file truncated', 'final', [{image}], {[image]:blueJpeg.subarray(0,blueJpeg.length-2)}],
    ['file wrong dimensions', 'final', [{image}], {[image]:tinyJpeg}],
    ['early phases missing', 'all', [{image}], {[image]:blueJpeg}],
  ]) {
    await t.test(title,async check=>{
      const {result,summary,data}=await merge(check,{state:{capture},rows:[{...scenario,shots},capturedInteraction],
        images:{...images,...interactionImages}});
      assert.equal(result.status,1);
      assert.equal(summary.finished,false);
      assert.equal(summary.omittedRows,1);
      assert.deepEqual(data.rows.map(row=>row.key),[interaction.key]);
    });
  }
});

test('rejects undersized PNGs and forged PNG or JPEG image bodies', async t => {
  const forgedPng=Buffer.concat([redPng.subarray(0,24),Buffer.from('xx'),redPng.subarray(-12)]);
  const badCompressedPng=Buffer.concat([redPng.subarray(0,33),pngChunk('IDAT',Buffer.from('garbage')),
    redPng.subarray(-12)]);
  const badCrcPng=Buffer.from(redPng);
  badCrcPng[42]^=1;
  const scan=blueJpeg.indexOf(Buffer.from([0xff,0xda]));
  const emptyScanJpeg=Buffer.concat([blueJpeg.subarray(0,scan+2+blueJpeg.readUInt16BE(scan+2)),
    Buffer.from('xx'),blueJpeg.subarray(-2)]);
  for(const [name,ext,bytes] of [
    ['valid but 1x1 PNG','png',tinyPng], ['forged PNG envelope','png',forgedPng],
    ['CRC-correct PNG with invalid compressed data','png',badCompressedPng],
    ['PNG with an invalid checksum','png',badCrcPng], ['JPEG with a forged scan','jpg',emptyScanJpeg],
  ]) {
    await t.test(name,async check=>{
      const row=captured(scenario,['3'],ext), image=row.shots[0].image;
      const {result,summary,data,output}=await merge(check,{state:{suite:'full',capture:'final'},
        rows:[row,capturedInteraction],images:{...interactionImages,[image]:bytes}});
      assert.equal(result.status,1);
      assert.equal(summary.finished,false);
      assert.equal(summary.omittedRows,1);
      assert.deepEqual(data.rows.map(item=>item.key),[interaction.key]);
      await assert.rejects(fs.access(path.join(output,image)),{code:'ENOENT'});
    });
  }
});

test('interaction capture requires all named screenshots and a resize only when the panel can resize', async t => {
  const compactStages=interactionStages.filter(stage=>stage!=='battle-resized');
  const finalScenario=captured(scenario,['3']);
  const image=finalScenario.shots[0].image;
  for(const [title,capture,row,stages,bytes,expected] of [
    ['all screenshots missing','final',interaction,[],redPng,false],
    ['missing calendar','all',interaction,interactionStages.filter(stage=>stage!=='calendar'),redPng,false],
    ['missing expected resize','final',interaction,compactStages,redPng,false],
    ['smallest panel does not resize','final',compactInteraction,compactStages,compactPng,true],
    ['unexpected resize in smallest panel','final',compactInteraction,interactionStages,compactPng,false],
    ['resize retains the original viewport','final',interaction,interactionStages,redPng,true],
  ]) {
    await t.test(title, async check=>{
      const interactionRow=captured(row,stages);
      const scenarioRow=capture==='all'?captured(scenario,['0','1','2','3']):finalScenario;
      const images=Object.fromEntries(scenarioRow.shots.map(shot=>[shot.image,redPng]));
      for(const shot of interactionRow.shots) images[shot.image]=bytes;
      const {result,summary,data}=await merge(check,{state:{capture},rows:[scenarioRow,interactionRow],images});
      assert.equal(result.status,expected?0:1);
      assert.equal(summary.finished,expected);
      assert.equal(summary.completed,1);
      assert.equal(data.rows[0].frames.some(frame=>scenario.key+'/'+frame.file===image),true);
      assert.equal(summary.interactions,expected?1:0);
    });
  }
});

test('a failed case remains reportable when its failure screenshot also failed', async t => {
  const {result,summary,data}=await merge(t,{state:{capture:'final',failed:1},
    rows:[{...scenario,error:failure,screenshotError:failure,shots:[]},capturedInteraction],images:interactionImages});
  assert.equal(result.status,1);
  assert.equal(summary.finished,true);
  assert.equal(summary.failed,1);
  assert.deepEqual(data.rows[0].issues,['fail']);
});
