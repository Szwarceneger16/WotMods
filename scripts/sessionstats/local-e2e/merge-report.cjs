'use strict';

const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs/promises');
const path=require('node:path');
const {createReadStream,readFileSync}=require('node:fs');
const {createInterface}=require('node:readline');
const {parseArgs}=require('node:util');
const {ciJobs,ciResults,ciCoverage,ciOutcomes,publicCase,writeReport}=require('./report.cjs');
const {validScreenshot,viewportForPanel}=require('./screenshot.cjs');

const resultCounters=['completed','failed','interactions','interactionErrors','visualFailures','missingBaselines'];
const provenance={engine:'chromium',fixture:'synthetic',assets:'test-art'};
const identityFields={
  version:value=>typeof value==='string'&&value.length<=64&&/^\d+\.\d+\.\d+(?:[-+][a-z0-9.-]+)?$/i.test(value),
  suite:value=>['build','smoke','full'].includes(value),
  capture:value=>['all','final','failures'].includes(value),
  commit:value=>typeof value==='string'&&/^[a-f0-9]{40}$/.test(value),
};
const imagePath=/^(?:[a-z0-9_-]+\/)*[a-z0-9_-]+\.(?:png|jpe?g)$/i;

async function transfer(directory,out,relative,viewport) {
  assert(imagePath.test(relative),'Unexpected screenshot filename in shard');
  const source=await fs.realpath(path.join(directory,relative));
  assert(source.startsWith(directory+path.sep),'Screenshot is outside its shard');
  const file=await fs.stat(source);
  assert(file.isFile()&&file.size<=12*1024*1024,'Invalid screenshot file');
  assert(validScreenshot(await fs.readFile(source),relative,viewport),'Invalid screenshot image or viewport');
  const target=path.join(out,relative);
  await fs.mkdir(path.dirname(target),{recursive:true});
  try {await fs.link(source,target);}
  catch(error) {
    if(!['EXDEV','EPERM','ENOTSUP'].includes(error.code)) throw error;
    const {constants}=require('node:fs');
    await fs.copyFile(source,target,constants.COPYFILE_EXCL);
  }
  return target;
}

async function merge({out,input,expected,expectedIdentity,coverage,upstream,legacyComment}) {
  const files=[];
  const seen=new Set();
  const identityKeys=Object.keys(identityFields);
  let metadata, invalidManifest=false;
  for(const sourcePath of input) {
    let directory, state;
    try {
      directory=await fs.realpath(sourcePath);
      state=JSON.parse(await fs.readFile(path.join(directory,'run.json'),'utf8'));
    } catch {
      invalidManifest=true;
      console.error('A shard manifest could not be read');
      continue;
    }
    // A damaged manifest never authorizes reading or copying that shard's
    // data. A manifest declaring private inputs rejects the whole upload.
    assert(!state||!Object.keys(provenance).some(key=>typeof state[key]==='string'&&state[key]&&state[key]!==provenance[key]),
      'Only synthetic Chromium shards are accepted in an uploadable report');
    const shard=typeof state?.shard==='string'&&/^(\d+)\/(\d+)$/.exec(state.shard);
    const number=shard ? Number(shard[1]) : 0;
    if(!shard||number<1||number>expected||Number(shard[2])!==expected||
        !Object.keys(provenance).every(key=>state[key]===provenance[key])||
        !identityKeys.every(key=>(key==='commit'&&state[key]===undefined)||identityFields[key](state[key]))||
        !['planned',...resultCounters].every(key=>Number.isSafeInteger(state[key])&&state[key]>=0)) {
      invalidManifest=true;
      console.error('A shard manifest has invalid or duplicate metadata');
      continue;
    }
    if(Object.entries(expectedIdentity).some(([key,value])=>state[key]!==value)) {
      invalidManifest=true;
      console.error('A shard manifest does not match the requested version, suite, capture mode or commit');
      continue;
    }
    if(seen.has(number)) {
      invalidManifest=true;
      console.error('A shard manifest has invalid or duplicate metadata');
      continue;
    }
    const identity=JSON.stringify(identityKeys.map(key=>state[key]));
    if(metadata===undefined) metadata=identity;
    if(metadata!==identity) {
      invalidManifest=true;
      console.error('A shard manifest has a different version, suite, capture mode or commit');
      continue;
    }
    seen.add(number);
    files.push({directory,state,number});
  }
  const first=files[0]?.state;
  const summary={version:expectedIdentity.version??first?.version??'unknown',engine:'chromium',renderer:first?.renderer||null,
    suite:expectedIdentity.suite??first?.suite??'full',fixture:'synthetic',assets:'test-art',
    capture:expectedIdentity.capture??first?.capture??null,commit:expectedIdentity.commit??first?.commit,
    coverage,upstream,legacyComment,
    expectedShards:expected,shards:files.length,omittedRows:0,
    finished:!invalidManifest&&files.length===expected&&files.every(({state})=>state.finished===true)};
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
          if(!line.trim()) continue;
          let item, row;
          const copied=[];
          try {
            item=JSON.parse(line);
            row=publicCase(item,{capture:state.capture});
            assert(row&&!keys.has(row.key),'Invalid or duplicate case in shard');
            const viewport=viewportForPanel(row.width,row.height);
            for(const frame of row.frames) {
              const image=row.key+'/'+frame.file;
              copied.push(await transfer(directory,out,image,viewport));
              if(frame.reference) copied.push(await transfer(directory,out,'baseline/'+image,viewport));
              if(frame.diff) copied.push(await transfer(directory,out,'differences/'+image,viewport));
            }
          } catch {
            summary.finished=false;
            summary.omittedRows++;
            // A rejected row owns only the files it successfully copied.
            // Release them so a later valid row can recover the same case.
            await Promise.all(copied.map(target=>fs.rm(target,{force:true})));
            continue;
          }
          await ledger.appendFile(JSON.stringify(item)+'\n');
          keys.add(row.key);
          const interaction=row.group==='interactions';
          observed[interaction?'interactions':'completed']++;
          if(row.issues.includes('fail')) observed[interaction?'interactionErrors':'failed']++;
          observed.visualFailures+=row.frames.filter(frame=>frame.changed).length;
          observed.missingBaselines+=row.frames.filter(frame=>frame.missing).length;
        }
      } catch {
        summary.finished=false;
        console.error(`Shard ${number} has an unreadable result ledger`);
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
  const failedJobs=ciOutcomes(summary).filter(job=>job.failed);
  for(const job of failedJobs) console.error(`${job.name}: ${job.label}`);
  if(!summary.finished||summary.failed||summary.interactionErrors||summary.visualFailures||summary.missingBaselines||
      failedJobs.length) {
    process.exitCode=1;
  }
}

const jobKeys=Object.keys(ciJobs);
const {values,positionals}=parseArgs({allowPositionals:true,
  options:{out:{type:'string'},'expected-shards':{type:'string'},'expected-version':{type:'string'},
    'expected-suite':{type:'string'},'expected-capture':{type:'string'},'expected-commit':{type:'string'},
    coverage:{type:'string'},
    ...Object.fromEntries(jobKeys.map(key=>[key+'-result',{type:'string'}]))}});
const expected=Number(values['expected-shards']||positionals.length);
const expectedIdentity=Object.fromEntries(Object.keys(identityFields)
  .filter(key=>values['expected-'+key]!==undefined).map(key=>[key,values['expected-'+key]]));
const upstream=jobKeys.some(key=>values[key+'-result']!==undefined)
  ? Object.fromEntries(jobKeys.map(key=>[key,values[key+'-result']])) : undefined;
assert(!upstream||jobKeys.every(key=>Object.hasOwn(ciResults,upstream[key])),
  'Provide valid render, contracts and download results together');
const coverage=values.coverage;
assert(coverage===undefined||ciCoverage.includes(coverage),'Invalid requested coverage');
assert(values.out&&Number.isSafeInteger(expected)&&expected>=1,
  'Use --out DIRECTORY [--expected-shards N] [--expected-version VERSION] '+
  '[--expected-suite SUITE] [--expected-capture CAPTURE] [--expected-commit SHA] '+
  '[--coverage PROFILE] [--render-result RESULT --contracts-result RESULT --download-result RESULT] [shard directories]');
const legacyComment=!upstream&&process.env.GITHUB_ACTIONS==='true'&&process.env.GITHUB_EVENT_NAME==='issue_comment';
if(legacyComment&&!expectedIdentity.commit) {
  // Older default-branch workflows pin this checkout to the tested PR head.
  // GITHUB_SHA still points at the workflow's default-branch commit.
  const checkout=path.resolve(__dirname,'../../..');
  expectedIdentity.commit=execFileSync('git',['rev-parse','--verify','HEAD'],{cwd:checkout,encoding:'utf8'}).trim();
  expectedIdentity.version??=readFileSync(path.join(checkout,'mods/sessionstats/VERSION'),'utf8').trim();
}
assert(Object.entries(expectedIdentity).every(([key,value])=>identityFields[key](value)),
  'Invalid expected version, suite, capture mode or commit');
merge({out:path.resolve(values.out),expected,expectedIdentity,input:positionals,coverage,upstream,legacyComment})
  .catch(error=>{console.error(error.message);process.exitCode=1;});
