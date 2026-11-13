/* Sorting changes values/decoration, never the logical control or KPI slots. */
const fs=require('fs'),path=require('path');
// Width/mode/native acknowledgements precede each case; metric changes keep that width.
const frames=page=>page.evaluate(()=>new Promise((resolve,reject)=>{let left=6;
  const row=document.getElementById('ss-list-controls'),mode=row.getAttribute('data-filter-layout'),width=row.getAttribute('data-filter-width');
  function next(){
    if(row.getAttribute('data-filter-layout')!==mode||row.getAttribute('data-filter-width')!==width){
      reject(Error('An acknowledged filter layout changed without a new width'));return;
    }
    if(--left)requestAnimationFrame(next);else resolve();
  }requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const metrics=[['battles','avg'],['win_rate','avg'],['battle_wn8','min'],['battle_wn8','max'],['xp_received','avg'],['off','avg']];
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},viewport:{width:3840,height:2400,scale}});
    try{
      for(const [language,messages]of Object.entries(languages))for(const width of [550,1200,1800]){
        await page.evaluate(({language,messages,width,scale})=>{
          const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
          payload.account_key='synthetic-stable-sort-'+language;payload.localization={language,messages};
          payload.viewport={width:3840,height:2400,scale};payload.window_size=[width,950];
          payload.appearance={window_settings:{background_transparency:0,maximized:false,restored_width:width,restored_height:950}};
          for(const group of ['maps','vehicles','tiers']){
            const sample=scope[group][0];scope[group]=[0,1].map(index=>{
              const item=JSON.parse(JSON.stringify(sample));item.id='stable-'+group+'-'+index;item.name='Synthetic '+group;
              item.stats.wn8=2429;item.stats.battle_wn8={count:7,min:334,avg:2300,max:5035,sum:16100};
              item.stats.wn8_count=7;item.stats.battles=123;item.stats.observed_battles=137;item.stats.win_rate=50;
              item.sort_value=8;return item;
            });
            scope.pagination[group]={page:0,pages:1,total:2,page_size:40};
          }
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
          document.getElementById('ss-scope-launch').onclick();document.getElementById('ss-group-maps').onclick();
        },{language,messages,width,scale});
        await page.waitForFunction(({width,scale})=>{
          const row=document.getElementById('ss-list-controls');
          return row.getAttribute('data-filter-layout')===(width-38>=903?'wide':'wrapped')&&
            Number(row.getAttribute('data-filter-width'))===width-38&&window.__nativeSize&&__nativeSize[0]===Math.ceil(width*scale);
        },{width,scale});await frames(page);
        const groups=language==='en'&&width===1200?['maps','vehicles','tiers']:['maps'];
        for(const group of groups){
          let baseline;
          for(const [metric,statistic]of metrics){
            if(group==='tiers'&&metric==='battles')continue;
            await page.evaluate(({group,metric,statistic})=>{
              const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
              scope.ordering[group]={metric,statistic,direction:'desc',chronology:'newest'};
              scope[group].forEach(item=>{item.sort_value=metric==='battle_wn8'?(statistic==='min'?334:5035):8;});
              model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-group-'+group).onclick();
            },{group,metric,statistic});await frames(page);
            const value=await page.evaluate(()=>{
              const bar=document.getElementById('ss-list-controls'),card=document.querySelector('#ss-groups .ss-group');
              const barBox=bar.getBoundingClientRect(),cardBox=card.getBoundingClientRect();
              const rect=(node,origin)=>{const box=node.getBoundingClientRect();return [box.left-origin.left,box.top-origin.top,box.width,box.height];};
              const controls=['#ss-page-previous','#ss-sort-chronology','#ss-page-next','#ss-sort-direction','#ss-sort-metric','#ss-sort-off','#ss-sort-statistic'].map(selector=>rect(document.querySelector(selector),barBox));
              const kpis=[...card.querySelectorAll('.ss-group-kpi')].map(node=>{
                const box=node.getBoundingClientRect(),number=node.querySelector('.ss-kpi-value'),range=document.createRange();range.selectNodeContents(number);
                const text=range.getBoundingClientRect(),label=node.querySelector('.ss-kpi-label'),labelBox=label.getBoundingClientRect(),labelRange=document.createRange();labelRange.selectNodeContents(label);
                const fit=[...labelRange.getClientRects()].every(part=>part.left>=labelBox.left-1&&part.right<=labelBox.right+1&&part.top>=labelBox.top-1&&part.bottom<=labelBox.bottom+1)&&text.left>=box.left-1&&text.right<=box.right+1;return {fits:fit,box:rect(node,cardBox),label:rect(node.querySelector('.ss-kpi-label'),cardBox),value:rect(number,cardBox),centered:Math.abs((text.left+text.right-box.left-box.right)/2)<=1};
              });
              const field=document.querySelector('.ss-sort-statistic'),trigger=document.querySelector('#ss-sort-statistic .ss-select-trigger');
              return {controls,kpis,header:rect(card.querySelector('.ss-group-header'),cardBox),sorting:rect(document.getElementById('ss-sorting'),barBox),
                hidden:getComputedStyle(field).visibility==='hidden',aria:field.getAttribute('aria-hidden'),disabled:trigger.disabled};
            });
            const caption=language+'/'+scale+'x/'+width+'/'+group+'/'+metric+'/'+statistic;
            if(!baseline)baseline=value;
            const same=(left,right)=>left.length===right.length&&left.every((part,index)=>Array.isArray(part)?same(part,right[index]):Math.abs(part-right[index])<=scale*0.1);
            const unchanged=same(value.controls,baseline.controls)&&same(value.sorting,baseline.sorting)&&same(value.header,baseline.header)&&
              value.kpis.every((item,index)=>same(item.box,baseline.kpis[index].box)&&same(item.label,baseline.kpis[index].label)&&same(item.value,baseline.kpis[index].value));
            check('Metric changes preserve filter boxes and aggregate header slots '+caption+(unchanged?'':': '+JSON.stringify(value)),unchanged);
            const centered=value.kpis.every(item=>item.centered&&item.fits);
            check('Every aggregate figure uses the same centered slot before/after highlighting '+caption+(centered?'':': '+JSON.stringify(value)),centered);
            if(metric==='battles'||metric==='win_rate')check('Inapplicable Statistic reserves space without becoming visible or focusable '+caption,
              value.hidden&&value.aria==='true'&&value.disabled);
          }
        }
      }
      // A native update can invalidate an already open statistic menu.
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.maps={metric:'battle_wn8',statistic:'max',direction:'desc',chronology:'newest'};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-group-maps').onclick();});await frames(page);
      await page.locator('#ss-sort-statistic .ss-select-trigger').click();
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.maps.metric='win_rate';model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});
      check('An inapplicable statistic closes its old menu and leaves keyboard navigation',await page.locator('#ss-sort-statistic .ss-select-trigger').getAttribute('aria-expanded')==='false'&&
        await page.locator('#ss-sort-statistic .ss-select-trigger').isDisabled()&&!await page.locator('#ss-sort-statistic .ss-select-options').isVisible());
    }finally{await page.close();}
  }
};
