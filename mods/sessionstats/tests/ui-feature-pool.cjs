/* Application-test scheduling only; the outer pinned browser runner is unchanged. */
const assert=require('assert');
const fs=require('fs');
const path=require('path');
const {spawn}=require('child_process');
const {performance}=require('node:perf_hooks');

function assertManifest(files){
  assert(Array.isArray(files)&&files.length>0,'A feature manifest must be nonempty');
  assert(files.every(file=>typeof file==='string'&&/^\.\/ui-[a-z0-9-]+\.cjs$/.test(file)),
    'Feature manifests may name only application UI suites');
  assert(new Set(files).size===files.length,'A feature manifest must not contain duplicates');
}

function partitionFeatures(files,hints={},workerCount=2){
  assertManifest(files);
  assert(workerCount===2||workerCount===3,'Feature worker count must be 2 or 3');
  const buckets=Array.from({length:Math.min(workerCount,files.length)},()=>({weight:0,items:[]}));
  const weighted=files.map((file,index)=>{
    const weight=hints[file]===undefined?1:hints[file];
    assert(Number.isFinite(weight)&&weight>0,'Scheduling hints must be finite and positive');
    return {file,index,weight};
  }).sort((a,b)=>b.weight-a.weight||a.index-b.index);
  for(const item of weighted){
    const target=buckets.reduce((best,bucket)=>bucket.weight<best.weight?bucket:best,buckets[0]);
    target.items.push(item);target.weight+=item.weight;
  }
  return buckets.map(bucket=>bucket.items.sort((a,b)=>a.index-b.index).map(item=>item.file));
}

function coverageMatches(expected,actual){
  assertManifest(expected);assertManifest(actual);
  const ordered=[...actual].sort();
  return expected.length===actual.length&&[...expected].sort().every((file,index)=>file===ordered[index]);
}

function validateReport(expected,report,exitCode,signal){
  assertManifest(expected);
  assert(signal===null&&exitCode===0,'Every feature worker must exit successfully');
  assert(report&&report.schema_version===1&&report.completed===true,'A complete worker report is required');
  assert(Array.isArray(report.features)&&report.features.length===expected.length,
    'Every assigned feature must produce exactly one result');
  assert(report.features.every((result,index)=>result&&result.file===expected[index]&&result.passed===true&&
    Number.isInteger(result.checks)&&result.checks>0&&result.error===null),
  'Worker results must preserve the exact assigned manifest and pass every feature');
  assert(Array.isArray(report.checks)&&report.checks.every(value=>typeof value==='string')&&
    report.features.reduce((count,result)=>count+result.checks,0)===report.checks.length,
  'Every worker assertion must be retained in its report');
  assert(Array.isArray(report.errors)&&report.errors.length===0,'Worker browser errors must fail the run');
  assert(Array.isArray(report.featureFailures)&&report.featureFailures.length===0,
    'Worker feature failures must fail the run');
  return report;
}

async function runFeaturePool(files,{script,reportDirectory,hints={},workerCount,phase}){
  const assignments=partitionFeatures(files,hints,workerCount);
  const directory=fs.mkdtempSync(path.join(reportDirectory,'feature-batch-'));
  const results=await Promise.allSettled(assignments.map((expected,index)=>new Promise((resolve,reject)=>{
    const reportPath=path.join(directory,'worker-'+index+'.json');
    const started=performance.now();
    const child=spawn(process.execPath,[script,'--feature-worker',reportPath,JSON.stringify(expected)],
      {stdio:['ignore','inherit','inherit'],env:process.env});
    child.once('error',reject);
    child.once('close',(exitCode,signal)=>{
      let passed=false;
      try{
        const report=JSON.parse(fs.readFileSync(reportPath,'utf8'));
        resolve(validateReport(expected,report,exitCode,signal));
        passed=true;
      }catch(error){reject(new Error('Feature worker '+index+': '+error.message));}
      finally{
        if(phase)console.log('UI worker profile: '+JSON.stringify({
          phase,worker:index+1,workers:assignments.length,passed,
          duration_ms:Math.round(performance.now()-started),suites:expected
        }));
      }
    });
  })));
  const failures=results.filter(result=>result.status==='rejected');
  if(failures.length)throw new Error(failures.map(result=>result.reason.message).join('; '));
  const reports=results.map(result=>result.value);
  assert(coverageMatches(files,reports.flatMap(report=>report.features.map(result=>result.file))),
    'Parallel feature reports must cover the full requested manifest');
  return reports;
}

module.exports={assertManifest,partitionFeatures,coverageMatches,validateReport,runFeaturePool};
