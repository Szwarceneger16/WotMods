'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');
const { writeReport } = require('./report.cjs');

test('the offline catalogue selects portable screenshots and omits raw records and errors', async t => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(),'sessionstats-report-'));
  const file = name => path.join(directory,name);
  t.after(async()=>{
    for(const name of ['results.ndjson','index.html','catalog.js']) {
      try { await fs.unlink(file(name)); } catch(error) { if(error.code!=='ENOENT') throw error; }
    }
    await fs.rmdir(directory);
  });
  const caseKey = '625x730/en/history/vehicles/xp_received-sum-desc-newest';
  const interaction = 'interactions/625x730';
  const marker = 'PRIVATE-ACCOUNT-IDENTIFIER';
  const image = caseKey+'/3.jpg';
  const lines = [
    {key:interaction,error:marker,shots:[{image:interaction+'/failure.png'}]},
    {key:caseKey, phases:[{image,top:30,visible:4,pinned:true,raw:marker}],
      shots:[{image,reference:'baseline/'+image,diff:'differences/'+image,visualFailure:true,difference:.047},
        {image:caseKey+'/../../'+marker+'.png'}, {image:caseKey+'/'+marker+'.png'}]},
    {key:caseKey.replace('history',marker),shots:[]},
    {key:caseKey.replace('xp_received','private_value'),shots:[]},
    {key:'620x730/pl/history/maps/off-avg-desc-oldest',shots:[]},
  ].map(row=>JSON.stringify(row));
  lines.push('invalid '+marker);
  await fs.writeFile(file('results.ndjson'),lines.join('\n')+'\n');
  await writeReport(directory,{version:'0.9.30',engine:'chromium',renderer:'140.0',suite:'full',
    completed:2,planned:2,failed:0,interactionErrors:1,visualFailures:1,profile:marker});
  const html = await fs.readFile(file('index.html'),'utf8');
  const catalogue = await fs.readFile(file('catalog.js'),'utf8');
  for(const output of [html,catalogue]) {
    assert.ok(!output.includes(marker));
    assert.ok(!output.includes('results.ndjson'));
  }
  assert.match(html, /<script src="catalog\.js"><\/script>/);
  assert.match(html, /<html lang="en">/);
  assert.match(html, /Session Stats · Test results/);
  assert.match(html, /No test cases match the selected filters\./);
  const context = {window:{}};
  vm.runInNewContext(catalogue, context);
  const data = JSON.parse(JSON.stringify(context.window.sessionStatsMatrix));
  assert.deepEqual(data.rows.map(row=>row.group),['vehicles','maps','interactions']);
  assert.equal(data.rows[1].language,'pl');
  assert.deepEqual(data.rows[0].frames,[{file:'3.jpg',top:30,visible:4,pinned:true,warning:false,
    ratio:.047,reference:true,diff:true,changed:true}]);
  assert.deepEqual(data.rows.map(row=>row.issues),[['diff'],['pass'],['fail']]);
  assert.equal(data.summary.omitted,3);
  assert.equal(data.summary.frames,2);
});
