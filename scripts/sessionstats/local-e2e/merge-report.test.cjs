'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');

const scenario = {key:'625x730/en/history/vehicles/xp_received-sum-desc-newest'};
const interaction = {key:'interactions/625x730'};
const failure = 'Synthetic test failure';
const manifest = {
  engine:'chromium', fixture:'synthetic', assets:'test-art', version:'0.9.30', suite:'build',
  capture:'all', shard:'1/1', planned:1, completed:1, failed:0, interactions:1, interactionErrors:0,
  visualFailures:0, missingBaselines:0, finished:true
};

async function merge(t, {state={}, rows=[scenario,interaction], expected=1, missing=false}={}) {
  const directory = await fs.mkdtemp(path.join(await fs.realpath(os.tmpdir()),'sessionstats-merge-'));
  t.after(async()=>fs.rm(directory,{recursive:true,force:true}));
  const shard = path.join(directory,'shard');
  const output = path.join(directory,'report');
  const args = [path.join(__dirname,'merge-report.cjs'),'--out',output,'--expected-shards',String(expected)];
  if(!missing) {
    await fs.mkdir(shard);
    await fs.writeFile(path.join(shard,'run.json'),JSON.stringify({...manifest,...state}));
    await fs.writeFile(path.join(shard,'results.ndjson'),rows.map(row=>JSON.stringify(row)+'\n').join(''));
    args.push(shard);
  }
  const result = spawnSync(process.execPath,args,{encoding:'utf8'});
  assert.ifError(result.error);
  if(state.fixture && state.fixture!=='synthetic') {
    await assert.rejects(fs.access(output),{code:'ENOENT'});
    return {result};
  }
  const summary = JSON.parse(await fs.readFile(path.join(output,'run.json'),'utf8'));
  const html = await fs.readFile(path.join(output,'index.html'),'utf8');
  const catalogue = await fs.readFile(path.join(output,'catalog.js'),'utf8');
  assert.match(html, /<script src="catalog\.js"><\/script>/);
  assert.ok(!catalogue.includes(failure));
  return {result,summary};
}

test('succeeds only after matching one scenario and one interaction to the manifest', async t => {
  const {result,summary} = await merge(t);
  assert.equal(result.status,0);
  assert.equal(summary.finished,true);
  assert.equal(summary.completed,1);
  assert.equal(summary.interactions,1);
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
      const {result,summary} = await merge(check,options);
      assert.equal(result.status,1);
      assert.equal(summary.finished,false);
      assert.equal(summary.completed,shards);
      assert.equal(summary.shards,shards);
    });
  }
});

test('rejects a private fixture before creating any output', async t => {
  const {result} = await merge(t,{state:{fixture:'local-aggregate'}});
  assert.equal(result.status,1);
  assert.match(result.stderr,/Only synthetic Chromium/);
});
