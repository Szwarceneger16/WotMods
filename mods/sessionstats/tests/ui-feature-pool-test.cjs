/* Pool failures cannot turn incomplete application-test coverage green. */
const assert=require('assert');
const fs=require('fs');
const os=require('os');
const path=require('path');
const {partitionFeatures,coverageMatches,validateReport,runFeaturePool}=require('./ui-feature-pool.cjs');

module.exports=async function(check){
  const files=['./ui-probe-a.cjs','./ui-probe-b.cjs','./ui-probe-c.cjs','./ui-probe-d.cjs'];
  const parts=partitionFeatures(files,{[files[0]]:10,[files[1]]:9,[files[2]]:2,[files[3]]:1});
  check('Feature scheduling uses at most two nonempty workers and retains every suite',
    parts.length===2&&parts.every(part=>part.length>0)&&coverageMatches(files,parts.flat()));
  check('Duration hints balance workers without changing each assigned suite order',
    parts.map(part=>part.map(file=>files.indexOf(file)).join(',')).join('|')==='0,3|1,2');
  const report={schema_version:1,completed:true,
    features:files.map(file=>({file,passed:true,checks:1,error:null})),checks:files.map(file=>'check '+file),errors:[],featureFailures:[]};
  check('A complete successful worker report retains all assertion labels',validateReport(files,report,0,null)===report);
  const rejects=(label,change,exitCode=0,signal=null)=>{
    const value=JSON.parse(JSON.stringify(report));change(value);
    assert.throws(()=>validateReport(files,value,exitCode,signal));check(label,true);
  };
  rejects('A failed process cannot pass using a successful-looking report',()=>{},1);
  rejects('A terminated process cannot pass using a successful-looking report',()=>{},null,'SIGTERM');
  rejects('An incomplete worker report fails closed',value=>{value.completed=false;});
  rejects('An unknown worker report schema fails closed',value=>{value.schema_version=2;});
  rejects('A missing feature result fails closed',value=>{value.features.pop();});
  rejects('A duplicate feature result fails closed',value=>{value.features[1]=value.features[0];});
  rejects('A reordered feature result fails closed',value=>{value.features.reverse();});
  rejects('A failed feature cannot be hidden by successful process exit',value=>{value.features[0].passed=false;value.features[0].error='probe';});
  rejects('A feature with no completed assertions cannot report success',value=>{value.features[0].checks=0;});
  rejects('A dropped assertion label fails closed',value=>{value.checks.pop();});
  rejects('A malformed assertion label fails closed',value=>{value.checks[0]=null;});
  rejects('A browser error cannot be hidden in a complete report',value=>{value.errors.push('probe pageerror');});
  rejects('A feature failure cannot be hidden in a complete report',value=>{value.featureFailures.push('probe failure');});
  assert.throws(()=>partitionFeatures([files[0],files[0]]));check('Duplicate requested suites are rejected before scheduling',true);
  assert.throws(()=>partitionFeatures(['../outside.cjs']));check('Feature manifests cannot select files outside application UI suites',true);
  assert.throws(()=>partitionFeatures(files,{[files[0]]:0}));check('Invalid scheduling hints cannot silently alter worker allocation',true);

  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'grz-feature-pool-contract-'));
  try{
    const fixture=mode=>{
      const script=path.join(directory,'worker-'+mode+'.cjs');
      fs.writeFileSync(script,`const fs=require('fs');const reportPath=process.argv[3],files=JSON.parse(process.argv[4]);
const report={schema_version:1,completed:true,features:files.map(file=>({file,passed:true,checks:1,error:null})),checks:files.map(file=>'check '+file),errors:[],featureFailures:[]};
const mode=${JSON.stringify(mode)};
if(mode==='missing')process.exit(0);
if(mode==='incomplete')report.features.pop();
setTimeout(()=>{fs.writeFileSync(reportPath,JSON.stringify(report));process.exit(mode==='nonzero'?7:0);},5);
`);
      return script;
    };
    const complete=await runFeaturePool(files,{script:fixture('valid'),reportDirectory:directory});
    check('Real worker processes return the exact full requested feature coverage',
      complete.length===2&&coverageMatches(files,complete.flatMap(value=>value.features.map(result=>result.file))));
    for(const mode of ['missing','nonzero','incomplete']){
      await assert.rejects(runFeaturePool(files,{script:fixture(mode),reportDirectory:directory}));
      check('The process boundary rejects '+mode+' worker reports',true);
    }
  }finally{fs.rmSync(directory,{recursive:true,force:true});}
};

if(require.main===module){
  let checks=0;
  module.exports((label,passed)=>{assert(passed,label);checks++;})
    .then(()=>console.log('Feature pool invariant checks passed: '+checks))
    .catch(error=>{console.error(error);process.exitCode=1;});
}
