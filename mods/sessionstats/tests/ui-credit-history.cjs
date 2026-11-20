/* Both credit rows remain visible; unavailable base amounts stay unknown. */
const fs=require('fs'),path=require('path'),assert=require('assert'),vm=require('vm');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
function actualAvailability(){
  const source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
  const context={hasNumber:value=>typeof value==='number'&&Number.isFinite(value)};
  vm.createContext(context);
  for (const name of ['observedTotal','canonicalMetric','metricSeries','baseCreditAvailability']) {
    const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }\n',start)+7;
    assert(start>=0&&end>start);vm.runInContext(source.slice(start,end),context);
  }
  function availability(credits,field,battles=1) {
    return context.baseCreditAvailability({battles,currencies:{credits}},'credits_'+field+'_base');
  }
  assert.strictEqual(availability({income_base:0,income_base_count:1},'income').value,0,'A recorded zero is available');
  assert.strictEqual(availability({net_base:0,net_base_count:1},'net').value,0,'A recorded zero net is available');
  assert.strictEqual(availability({income_base:0,income_base_count:0},'income',0).value,null,'An empty zero sum is not an amount');
  assert.strictEqual(availability({income_base:500},'income').value,null,'Amounts without availability do not invent a base comparison');
  const partial=availability({net_base:null,net_base_count:1},'net',2);
  assert(partial.count===1&&partial.value===null,'Known partial samples keep their count even when the total is unavailable');
}
module.exports=async({browser,nativeHost,check})=>{
  actualAvailability();check('Actual source distinguishes recorded base zero from absent or unavailable base amounts',true);
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const scenarios=[
    {name:'legacy-0.9.8',available:false},
    {name:'empty-zero-series',income:0,incomeCount:0,net:0,netCount:0,available:false},
    {name:'known-zero',income:0,incomeCount:1,net:-41385,netCount:1,available:true},
    {name:'complete-zero',income:0,incomeCount:1,net:-41385,netCount:1,available:true,complete:true},
    {name:'partial-masked',income:null,incomeCount:1,net:null,netCount:1,available:true},
    {name:'income-only',income:42000,incomeCount:2,net:null,netCount:0,available:true},
    {name:'net-only',income:null,incomeCount:0,net:500,netCount:1,available:true},
  ];
  const page=await nativeHost(browser,{initialViewport:{width:1920,height:1400},viewport:{width:1920,height:1400,scale:1}});
  const snapshots={};
  try{
    const original=await page.evaluate(()=>JSON.parse(model.payload));
    for(const [language,messages]of Object.entries(languages))for(const scenario of scenarios){
      await page.evaluate(({original,language,messages,scenario})=>{
        const payload=JSON.parse(JSON.stringify(original)),scope=payload.scopes.launch;
        payload.localization={language,selected:language,messages};payload.window_size=[1200,1100];
        function prepare(stats){
          const receivedCount=scenario.complete?1:2;
          stats.battles=receivedCount;stats.observed_battles=scenario.complete?1:3;
          const credits={income:78935,income_count:receivedCount,costs:41385,costs_count:receivedCount,net:37550,net_count:receivedCount};
          if('income'in scenario){credits.income_base=scenario.income;credits.income_base_count=scenario.incomeCount;}
          if('net'in scenario){credits.net_base=scenario.net;credits.net_base_count=scenario.netCount;}
          stats.currencies.credits=credits;
          stats.currencies.bonds={income:14,income_count:2,costs:6,costs_count:2,net:8,net_count:2};
          stats.currencies.gold={income:501,income_count:2,costs:0,costs_count:2,net:501,net_count:2};
          for(const [metric,value,count]of [['credits_income_base',scenario.income,scenario.incomeCount],['credits_net_base',scenario.net,scenario.netCount],['credits_income_received',78935,2],['credits_net_received',37550,2],['credits_costs',41385,2]]){
            const known=typeof value==='number'&&Number.isFinite(value)&&count>0;
            stats[metric]={count:count||0,sum:known?value:null,min:known?value:null,avg:known?value/(count||1):null,max:known?value:null};
          }
        }
        prepare(scope.summary);delete scope.extrema_battles;
        for(const group of ['vehicles','maps','tiers','battles']){
          const item=JSON.parse(JSON.stringify(scope[group][0]));item.id='credit-history-'+group;prepare(item.stats);delete item.extrema_battles;delete item.sort_value;
          scope[group]=[item];scope.pagination[group]={page:0,pages:1,total:1,page_size:40};
          scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:group==='tiers'?'tier_desc':'newest'};
        }
        payload.generated_at+=1;model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{original,language,messages,scenario});await frames(page);
      for(const group of ['vehicles','maps','tiers','battles']){
        await page.locator('#ss-group-'+group).click();await frames(page);
        const result=await page.evaluate(({messages,available})=>{
          function inspect(panel){
            const economy=panel.querySelector('.ss-economy'),pair=economy.querySelector('.ss-credit-pair'),rows=[...economy.querySelectorAll('.ss-money-row:not(.ss-credit-pair)')],find=label=>rows.find(row=>[...row.querySelector('.ss-money-label').childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('')===label),values=row=>[...row.querySelectorAll(':scope > .ss-money-value > .ss-cell-value')].map(n=>n.textContent.replace(/\s/g,''));
            const creditValues=basis=>['credits_income_'+basis,'credits_costs','credits_net_'+basis].map(metric=>pair.querySelector('.ss-money-value[data-ss-metric="'+metric+'"] > .ss-cell-value').textContent.replace(/\s/g,''));
            const base=pair.querySelector('.ss-credit-label-column [data-ss-credit-row="base"]'),received=pair.querySelector('.ss-credit-label-column [data-ss-credit-row="received"]'),bonds=find(messages['finance.bonds']),gold=find(messages['finance.gold']),help=(economy.querySelector('.ss-info-button')||panel.querySelector('.ss-group-heading .ss-info-button')).getAttribute('data-ss-help')||'';
            return {base:base.textContent===messages['finance.credits_base'],baseValues:creditValues('base'),received:received.textContent===messages['finance.credits_received']?creditValues('received'):[],bonds:bonds?values(bonds):[],gold:gold?values(gold):[],costOwners:economy.querySelectorAll('.ss-money-value[data-ss-metric="credits_costs"]').length,help:help.includes(messages['help.credits.base_received'])||help.includes(messages['help.credits.incomplete_brief']),availability:available||help.includes(messages['help.credits.incomplete_brief'])};
          }
          return {summary:inspect(document.querySelector('#ss-summary')),card:inspect(document.querySelector('#ss-groups .ss-group'))};
        },{messages,available:scenario.available});
        check('Both credit rows remain visible while received profits/currencies survive '+language+'/'+scenario.name+'/'+group,
          [result.summary,result.card].every(x=>x.base&&x.received.join('|')==='78935|-41385|+37550'&&x.bonds.join('|')==='14|-6|+8'&&x.gold.join('|')==='501|0|+501'&&x.costOwners===1&&x.help&&x.availability));
        if(!scenario.complete)check('Each base field reports its received total only when reports cover it '+language+'/'+scenario.name+'/'+group,
          [result.summary,result.card].every(x=>x.baseValues.join('|')===(scenario.name==='income-only'?'42000|-41385|—':'—|-41385|—')));
        if(scenario.name==='complete-zero')check('A complete known-zero base result stays visible '+language+'/'+group,
          [result.summary,result.card].every(x=>x.baseValues.join('|')==='0|-41385|-41385'));
      }
      if(language==='en'&&['legacy-0.9.8','known-zero'].includes(scenario.name))snapshots[scenario.name]=await page.evaluate(()=>JSON.parse(model.payload));
    }
    for(const [scenario,payload]of Object.entries(snapshots)){
      await page.evaluate(payload=>{model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},payload);
      await page.locator('#ss-group-maps').click();await frames(page);let baseline;
      for(const metric of ['off','credits_income_base','credits_net_base','xp_received','credits_income_received']){
        await page.evaluate(metric=>{const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.maps={metric,statistic:'max',direction:'desc',chronology:'newest'};payload.generated_at+=1;model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},metric);await frames(page);
        const result=await page.locator('#ss-groups .ss-group').first().evaluate(card=>{
          const bounds=card.getBoundingClientRect(),tables=[...card.querySelectorAll('.ss-performance,.ss-economy')];
          const geometry=tables.map(table=>{
            const box=table.getBoundingClientRect();
            const rows=[...table.querySelectorAll('.ss-metric-head,.ss-metric-row,.ss-money-head,.ss-money-row')].map(row=>{
              const rect=row.getBoundingClientRect();return [rect.left-box.left,rect.top-box.top,rect.width,rect.height];
            });
            return [box.width,box.height,rows];
          });
          const labels=[...card.querySelectorAll('.ss-metric-name .ss-cell-value,.ss-money-label,.ss-credit-inline-label')].filter(label=>{
            const box=label.getBoundingClientRect();return box.width>0&&box.height>0;
          });
          const readable=labels.every(label=>{
            const owner=(label.closest('.ss-metric-name,.ss-money-label')||label).getBoundingClientRect(),range=document.createRange();
            range.selectNodeContents(label);const lines=[...range.getClientRects()].filter(rect=>rect.width>0&&rect.height>0);
            return lines.length>0&&lines.every(rect=>rect.left>=owner.left-1&&rect.right<=owner.right+1&&rect.top>=owner.top-1&&rect.bottom<=owner.bottom+1);
          });
          const contained=tables.every(table=>{
            const box=table.getBoundingClientRect();return box.left>=bounds.left-1&&box.right<=bounds.right+1&&box.top>=bounds.top-1&&box.bottom<=bounds.bottom+1&&
              [...table.querySelectorAll('.ss-metric-head,.ss-metric-row,.ss-money-head,.ss-money-row')].every(row=>{
                const rect=row.getBoundingClientRect();return rect.left>=box.left-1&&rect.right<=box.right+1&&rect.top>=box.top-1&&rect.bottom<=box.bottom+1;
              });
          });
          return {height:bounds.height,base:!!card.querySelector('.ss-money-value[data-ss-metric="credits_net_base"]'),baseNet:card.querySelector('.ss-money-value[data-ss-metric="credits_net_base"] > .ss-cell-value').textContent,
            received:card.querySelector('.ss-money-value[data-ss-metric="credits_income_received"] > .ss-cell-value').textContent,
            selected:card.querySelector('.ss-group-sort-number')?.textContent,geometry,readable,contained,
            finance:[...card.querySelectorAll('.ss-money-row')].map(row=>row.textContent)};
        });
        if(!baseline)baseline=result;
        // The compact header now fits its selected caption and amount. Its
        // natural height can change while the historical tables stay intact.
        const same=(left,right)=>Array.isArray(left)?Array.isArray(right)&&left.length===right.length&&left.every((value,index)=>same(value,right[index])):Math.abs(left-right)<0.1;
        check('Base comparison and received values remain independent of sort '+scenario+'/'+metric,
          result.base===baseline.base&&result.received===baseline.received&&result.finance.join('|')===baseline.finance.join('|'));
        check('Natural sorting headers preserve historical table geometry and readable contained labels '+scenario+'/'+metric+': '+JSON.stringify({height:result.height,baselineHeight:baseline.height,readable:result.readable,contained:result.contained}),
          same(result.geometry,baseline.geometry)&&result.readable&&result.contained);
        if(scenario==='legacy-0.9.8'&&metric==='credits_income_base')check('Selecting an unavailable base metric keeps its row and unknown result without hiding received amounts',result.selected==='—'&&result.base&&result.baseNet==='—');
      }
    }
  }finally{await page.close();}
  await require('./ui-credit-pair-layout.cjs')({browser,nativeHost,check});
  await require('./ui-base-credit-availability.cjs')({browser,nativeHost,check});
  await require('./ui-summary-finance-mode.cjs')({browser,nativeHost,check});
};
