'use strict';

const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const {createReadStream}=require('node:fs');
const {createInterface}=require('node:readline');
const {parseArgs}=require('node:util');
const {publicCase,writeReport}=require('./report.cjs');

const resultCounters=['completed','failed','interactions','interactionErrors','visualFailures','missingBaselines'];
const imagePath=/^(?:[a-z0-9_-]+\/)*[a-z0-9_-]+\.(?:png|jpe?g)$/i;
const caseKey=/^[a-z0-9_-]+(?:\/[a-z0-9_-]+)+$/i;

async function transfer(directory,out,relative) {
  assert(imagePath.test(relative),'Unexpected screenshot filename in shard');
  const source=await fs.realpath(path.join(directory,relative));
  assert(source.startsWith(directory+path.sep)&&(await fs.stat(source)).isFile(),'Screenshot is outside its shard');
  const target=path.join(out,relative);
  await fs.mkdir(path.dirname(target),{recursive:true});
  try {await fs.link(source,target);}
  catch(error) {
    if(!['EXDEV','EPERM','ENOTSUP'].includes(error.code)) throw error;
    const {constants}=require('node:fs');
    await fs.copyFile(source,target,constants.COPYFILE_EXCL);
  }
}

async function merge({out,input,expected}) {
  const files=[];
  const seen=new Set();
  let metadata;
  for(const sourcePath of input) {
    const directory=await fs.realpath(sourcePath);
    const state=JSON.parse(await fs.readFile(path.join(directory,'run.json'),'utf8'));
    assert(state.engine==='chromium'&&state.fixture==='synthetic'&&state.assets==='test-art',
      'Only synthetic Chromium shards are accepted in an uploadable report');
    const shard=/^(\d+)\/(\d+)$/.exec(state.shard||'');
    assert(shard&&Number(shard[1])>0&&Number(shard[1])<=expected&&Number(shard[2])===expected,
      'Unexpected shard number');
    const number=Number(shard[1]);
    assert(!seen.has(number),'Duplicate shard number');
    seen.add(number);
    for(const key of ['planned',...resultCounters]) {
      assert(Number.isSafeInteger(state[key])&&state[key]>=0,'Invalid shard counters');
    }
    const identity=JSON.stringify([state.suite,state.version,state.engine,state.capture]);
    if(metadata===undefined) metadata=identity;
    assert.equal(metadata,identity,'Cannot combine different suites or versions');
    files.push({directory,state,number});
  }
  const first=files[0]?.state;
  const summary={version:first?.version||'unknown',engine:'chromium',renderer:first?.renderer||null,
    suite:first?.suite||'full',fixture:'synthetic',assets:'test-art',capture:first?.capture||null,
    expectedShards:expected,shards:files.length,finished:files.length===expected&&files.every(({state})=>state.finished===true)};
  summary.planned=files.reduce((sum,file)=>sum+file.state.planned,0);
  for(const key of resultCounters) summary[key]=0;
  await fs.mkdir(path.dirname(out),{recursive:true});
  await fs.mkdir(out);
  const ledger=await fs.open(path.join(out,'results.ndjson'),'wx');
  const keys=new Set();
  try {
    for(const {directory,state,number} of files) {
      const observed=Object.fromEntries(resultCounters.map(key=>[key,0]));
      const lines=createInterface({input:createReadStream(path.join(directory,'results.ndjson'),{encoding:'utf8'}),crlfDelay:Infinity});
      try {
        for await(const line of lines) {
          const item=JSON.parse(line);
          assert(caseKey.test(item.key)&&!keys.has(item.key),'Invalid or duplicate result key');
          keys.add(item.key);
          const row=publicCase(item);
          assert(row,'Invalid case in shard');
          for(const frame of row.frames) {
            const image=row.key+'/'+frame.file;
            await transfer(directory,out,image);
            if(frame.reference) await transfer(directory,out,'baseline/'+image);
            if(frame.diff) await transfer(directory,out,'differences/'+image);
          }
          await ledger.appendFile(JSON.stringify(item)+'\n');
          const interaction=row.group==='interactions';
          observed[interaction?'interactions':'completed']++;
          if(row.issues.includes('fail')) observed[interaction?'interactionErrors':'failed']++;
          observed.visualFailures+=row.frames.filter(frame=>frame.changed).length;
          observed.missingBaselines+=row.frames.filter(frame=>frame.missing).length;
        }
      } finally {
        for(const key of resultCounters) summary[key]+=observed[key];
      }
      const validPlan=state.planned>0&&state.completed<=state.planned&&
        (state.finished!==true||state.completed===state.planned);
      if(!validPlan||resultCounters.some(key=>state[key]!==observed[key])) {
        summary.finished=false;
        console.error(`Shard ${number} has inconsistent test results or counts`);
      }
    }
  } catch(error) {
    summary.finished=false;
    throw error;
  } finally {
    await ledger.close();
    await fs.writeFile(path.join(out,'run.json'),JSON.stringify(summary,null,2)+'\n');
    await writeReport(out,summary);
  }
  if(!summary.finished||summary.failed||summary.interactionErrors||summary.visualFailures||summary.missingBaselines) {
    process.exitCode=1;
  }
}

const {values,positionals}=parseArgs({allowPositionals:true,
  options:{out:{type:'string'},'expected-shards':{type:'string'}}});
const expected=Number(values['expected-shards']||positionals.length);
assert(values.out&&Number.isInteger(expected)&&expected>=1,'Use --out DIRECTORY [--expected-shards N] [shard directories]');
merge({out:path.resolve(values.out),expected,input:positionals})
  .catch(error=>{console.error(error.message);process.exitCode=1;});
