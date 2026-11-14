/* Both recorded XP metrics stay visible without a presentation-mode switch. */
const frames=page=>page.evaluate(()=>new Promise(resolve=>{
  let remaining=12;function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{initialViewport:{width:2800,height:2400},viewport:{width:2800,height:2400,scale:1}});
  try{
    for(const scale of [1,2])for(const width of [550,1200]){
      await page.evaluate(({scale,width})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        payload.account_key='synthetic-dual-xp-'+scale+'-'+width;
        payload.window_size=[width,900];payload.viewport={width:2800,height:2400,scale};
        payload.xp_mode='received';
        scope.summary.xp_base={count:1,min:0,avg:0,max:0,sum:0};
        scope.summary.xp_received={count:2,min:100,avg:150,max:200,sum:300};
        scope.summary.battle_wn8={count:1,min:0,avg:0,max:0,sum:0};
        scope.summary.wn8=0;scope.summary.wn8_count=1;scope.summary.observed_battles=3;scope.summary.battles=2;
        for(const group of ['vehicles','maps','tiers','battles']){
          const item=JSON.parse(JSON.stringify(scope[group][0]));
          item.id='synthetic-dual-'+group;item.stats=JSON.parse(JSON.stringify(scope.summary));
          if(group==='battles'){
            item.stats.xp_received={count:0,min:null,avg:null,max:null,sum:0};
            item.stats.observed_battles=1;item.stats.battles=1;
          }
          scope[group]=[item];scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
          scope.pagination[group]={page:0,pages:1,total:1,page_size:40};
        }
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{scale,width});
      await page.locator('#ss-scope-launch').click();await frames(page);
      const caption=' at '+width+' logical px / '+(scale*100)+'%';
      check('No obsolete XP switch or mode remains in the live interface'+caption,
        await page.locator('.ss-xp-picker,#ss-xp-base,#ss-xp-received').count()===0&&
        await page.evaluate(()=>!Object.prototype.hasOwnProperty.call(GRZSessionStats.getState(),'xp')));
      const summary=await page.locator('#ss-summary .ss-performance').evaluate(panel=>({
        keys:[...panel.querySelectorAll('.ss-metric-row[data-ss-metric]')].map(row=>row.getAttribute('data-ss-metric')),
        rows:[...panel.querySelectorAll('.ss-metric-row')].map(row=>({
          key:row.getAttribute('data-ss-metric'),label:row.querySelector('.ss-metric-name').textContent,
          numbers:[...row.querySelectorAll('.ss-metric-number')].map(node=>node.textContent)})),
        shared:panel.querySelectorAll('.ss-metric-head .ss-metric-count').length}));
      check('Summary permanently displays separate Base XP, Received XP and WN8 distributions'+caption,
        summary.keys.join('|')==='xp_base|xp_received|battle_wn8'&&summary.rows[0].numbers.join('|')==='0|0|0'&&
        summary.rows[1].numbers.join('|')==='100|150|200'&&summary.rows[2].numbers.join('|')==='0|0|0');
      check('Summary retains each XP metric\'s independent missing-result coverage'+caption,
        summary.shared===0&&summary.rows[0].label.includes('1/3')&&summary.rows[1].label.includes('2/3')&&summary.rows[2].label.includes('1/3'));
      for(const group of ['vehicles','maps','tiers','battles']){
        await page.locator('#ss-group-'+group).click();await frames(page);
        const rows=await page.locator('#ss-groups .ss-group').first().locator('.ss-performance .ss-metric-row[data-ss-metric],.ss-performance .ss-battle-measure[data-ss-metric]').evaluateAll(rows=>rows.map(row=>({
          key:row.getAttribute('data-ss-metric'),label:(row.querySelector('.ss-metric-name,.ss-battle-label')||row).textContent,
          values:[...row.querySelectorAll('.ss-metric-number,.ss-battle-value')].map(node=>node.textContent)})));
        check(group+' permanently displays both XP metrics before WN8'+caption,
          rows.map(row=>row.key).join('|')==='xp_base|xp_received|battle_wn8'&&
          rows[0].values.every(value=>value==='0')&&
          rows[1].values.join('|')===(group==='battles'?'—':'100|150|200'));
      }
      for(const metric of ['xp_base','xp_received','battle_wn8']){
        await page.evaluate(metric=>{
          const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
          for(const group of ['vehicles','maps','tiers','battles'])
            scope.ordering[group]={metric,statistic:'max',direction:'desc',chronology:'newest'};
          payload.generated_at+=1;model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },metric);
        for(const group of ['vehicles','battles']){
          await page.locator('#ss-group-'+group).click();await frames(page);
          const marks=await page.locator('#ss-groups .ss-group').first().evaluate(card=>[...card.querySelectorAll(
            '.ss-metric-row .ss-sort-active-value,.ss-battle-measure.ss-sort-active-value')].map(node=>
              node.closest('[data-ss-metric]').getAttribute('data-ss-metric')));
          check('Sorting '+metric+' marks its own displayed '+group+' row'+caption,marks.length===1&&marks[0]===metric);
        }
      }
    }
  }finally{await page.close();}
};
