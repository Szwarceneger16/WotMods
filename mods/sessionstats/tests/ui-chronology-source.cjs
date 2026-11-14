/* Actual preview ordering keeps boundary selection independent of direction. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
module.exports=function(){
  const source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
  function actual(name){const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }\n',start)+7;
    assert(start>=0&&end>start,'Exercise shipped '+name);return source.slice(start,end);}
  const context={state:{group:'maps'},hasNumber:value=>typeof value==='number'&&Number.isFinite(value)};
  vm.createContext(context);vm.runInContext(['canonicalMetric','metricSeries','groupSortValue','ordered'].map(actual).join('\n'),context);
  const rows=[{id:'a',first_started_at:100,started_at:400,stats:{xp_base:{avg:5}}},
    {id:'b',first_started_at:200,started_at:300,stats:{xp_base:{avg:5}}},
    {id:'c',first_started_at:150,started_at:500,stats:{xp_base:{avg:5}}},
    {id:'missing',first_started_at:null,started_at:null,stats:{xp_base:{avg:null}}}];
  for(const group of ['vehicles','maps','tiers']){
    context.state.group=group;
    for(const [chronology,expected] of Object.entries({oldest:['a','c','b','missing'],first_desc:['b','c','a','missing'],
      last_asc:['b','a','c','missing'],newest:['c','a','b','missing']})){
      const options={metric:'off',chronology,statistic:'avg',direction:'desc'};
      assert.deepStrictEqual(Array.from(context.ordered(rows,options),row=>row.id),expected,group+' '+chronology);
      options.metric='xp_base';assert.deepStrictEqual(Array.from(context.ordered(rows,options),row=>row.id),['c','a','b','missing'],'Metric ties ignore saved '+chronology);
    }
  }
};
if(require.main===module){module.exports();console.log('Four chronology boundaries/directions and advanced tie-breakers passed.');}
