/* Historical received credits remain visible while unavailable base comparisons stay hidden. */
const fs=require('fs'),path=require('path'),assert=require('assert'),vm=require('vm');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
function actualAvailability(){
  const source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8'),start=source.indexOf('    function hasBaseCredits('),end=source.indexOf('\n    }\n',start)+7;
  assert(start>=0&&end>start);const context={hasNumber:value=>typeof value==='number'&&Number.isFinite(value)};
  vm.createContext(context);vm.runInContext(source.slice(start,end),context);
  assert(context.hasBaseCredits({income_base:0,income_base_count:1}),'A recorded zero is available');
  assert(context.hasBaseCredits({net_base:0,net_base_count:1}),'A recorded zero net is available');
  assert(!context.hasBaseCredits({income_base:0,income_base_count:0,net_base:0,net_base_count:0}),'An empty zero sum is not an amount');
  assert(!context.hasBaseCredits({income_base:500,net_base:200}),'Amounts without availability do not invent a base comparison');
  assert(!context.hasBaseCredits({income_base:null,income_base_count:1,net_base:NaN,net_base_count:1}),'Missing amounts cannot form a comparison');
}
module.exports=async({browser,nativeHost,check})=>{
  actualAvailability();check('Actual source distinguishes recorded base zero from absent or unavailable base amounts',true);
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const scenarios=[
    {name:'legacy-0.9.8',visible:false},
    {name:'empty-zero-series',income:0,incomeCount:0,net:0,netCount:0,visible:false},
    {name:'known-zero',income:0,incomeCount:1,net:-41385,netCount:1,visible:true},
    {name:'income-only',income:42000,incomeCount:2,net:null,netCount:0,visible:true},
    {name:'net-only',income:null,incomeCount:0,net:500,netCount:1,visible:true},
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
          stats.battles=2;stats.observed_battles=3;
          const credits={income:78935,income_count:2,costs:41385,costs_count:2,net:37550,net_count:2};
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
        const result=await page.evaluate(({messages,visible})=>{
          function inspect(panel){
            const economy=panel.querySelector('.ss-economy'),rows=[...economy.querySelectorAll('.ss-money-row')],find=label=>rows.find(row=>[...row.querySelector('.ss-money-label').childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('')===label),values=row=>[...row.querySelectorAll(':scope > .ss-money-value > .ss-cell-value')].map(n=>n.textContent.replace(/\s/g,''));
            const base=find(messages['finance.credits_base']),received=find(messages['finance.credits_received']),bonds=find(messages['finance.bonds']),gold=find(messages['finance.gold']),help=(economy.querySelector('.ss-info-button')||panel.querySelector('.ss-group-heading .ss-info-button')).getAttribute('data-ss-help')||'';
            return {base:!!base,baseValues:base?values(base):[],received:received?values(received):[],bonds:bonds?values(bonds):[],gold:gold?values(gold):[],costOwners:economy.querySelectorAll('.ss-money-value[data-ss-metric="credits_costs"]').length,help:help.includes(messages['help.credits.base_received']),availability:visible||help.includes(messages['sort.credits_income_base']+': '+messages['coverage.value'].replace('{0}','0').replace('{1}','3'))};
          }
          return {summary:inspect(document.querySelector('#ss-summary')),card:inspect(document.querySelector('#ss-groups .ss-group'))};
        },{messages,visible:scenario.visible});
        check('Base comparison follows real availability and received profits/currencies survive '+language+'/'+scenario.name+'/'+group,
          [result.summary,result.card].every(x=>x.base===scenario.visible&&x.received.join('|')==='78935|-41385|+37550'&&x.bonds.join('|')==='14|-6|+8'&&x.gold.join('|')==='501|0|+501'&&x.costOwners===1&&x.help&&x.availability));
        if(scenario.name==='known-zero')check('Known zero base earnings remain visible '+language+'/'+group,result.card.baseValues.join('|')==='0|-41385|-41385');
      }
      if(language==='en'&&['legacy-0.9.8','known-zero'].includes(scenario.name))snapshots[scenario.name]=await page.evaluate(()=>JSON.parse(model.payload));
    }
    for(const [scenario,payload]of Object.entries(snapshots)){
      await page.evaluate(payload=>{model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},payload);
      await page.locator('#ss-group-maps').click();await frames(page);let baseline;
      for(const metric of ['off','credits_income_base','credits_net_base','xp_received','credits_income_received']){
        await page.evaluate(metric=>{const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.maps={metric,statistic:'max',direction:'desc',chronology:'newest'};payload.generated_at+=1;model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},metric);await frames(page);
        const result=await page.locator('#ss-groups .ss-group').first().evaluate(card=>({height:card.getBoundingClientRect().height,base:!!card.querySelector('.ss-money-value[data-ss-metric="credits_net_base"]'),received:card.querySelector('.ss-money-value[data-ss-metric="credits_income_received"] > .ss-cell-value').textContent,selected:card.querySelector('.ss-group-sort-number')?.textContent}));
        if(!baseline)baseline=result;
        check('Base comparison visibility and card height are independent of sort '+scenario+'/'+metric,result.base===baseline.base&&Math.abs(result.height-baseline.height)<0.1&&result.received===baseline.received);
        if(scenario==='legacy-0.9.8'&&metric==='credits_income_base')check('Selecting an unavailable base metric leaves its result unknown without hiding received amounts',result.selected==='—'&&!result.base);
      }
    }
  }finally{await page.close();}
};
