/* Active net-credit sorting exposes its per-battle value at the reading size. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async ({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:3840,height:2300},viewport:{width:3840,height:2300,scale:1}});
  try {
    for(const scale of [1,2]) for(const [language,messages] of Object.entries(languages)) {
      await page.evaluate(({scale,language,messages})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        payload.account_key='synthetic-sort-'+language+'-'+scale;payload.window_size=[550,1000];
        payload.viewport={width:3840,height:2300,scale};payload.localization={language,messages};
        payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));payload.scopes.timeline.time_points=[];
        scope.period_id='synthetic-sort-period';
        for(const group of ['vehicles','maps','tiers']) {
          const sample=scope[group][0];scope[group]=[12500,-23456,0,null].map((value,index)=>{
            const item=JSON.parse(JSON.stringify(sample));item.id='synthetic-sort-'+group+'-'+index;item.name='Synthetic '+index;item.sort_value=value;
            item.stats.currencies.credits.net=999999;item.stats.credits_net={count:0,min:null,avg:null,max:null,sum:null};return item;
          });
          scope.ordering[group]={metric:'credits_net',statistic:'max',direction:'desc',chronology:'newest'};
          scope.pagination[group]={page:0,pages:1,page_size:40,total:4};
        }
        scope.ordering.vehicles.metric='off';
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{scale,language,messages});await page.locator('#ss-scope-launch').click();await page.locator('#ss-group-vehicles').click();await frames(page);
      const controls=await page.evaluate(scale=>{
        const selectors=['.ss-scopes','.ss-xp-picker','#ss-time-point-controls','.ss-background-control','#ss-language .ss-select-trigger',
          '#ss-page-previous','#ss-page-next','#ss-sort-chronology .ss-select-trigger','#ss-sort-direction .ss-select-trigger',
          '#ss-sort-metric .ss-select-trigger','#ss-sort-statistic .ss-select-trigger'];
        const heights=selectors.map(selector=>({selector,height:document.querySelector(selector).getBoundingClientRect().height/scale}));
        const field=document.querySelector('#ss-sort-statistic .ss-select-trigger'),label=field.querySelector('.ss-control-label');
        let opacity=1;for(let node=label;node && node.id!=='grz-session-stats';node=node.parentElement)opacity*=parseFloat(getComputedStyle(node).opacity);
        const frame=getComputedStyle(document.querySelector('.ss-background-control'));
        return {heights,order:[...document.querySelectorAll('#ss-sorting > .ss-sort-field .ss-select')].map(node=>node.id),
          disabled:field.disabled,aria:field.getAttribute('aria-disabled'),opacity,color:getComputedStyle(label).color,
          activeColor:getComputedStyle(document.querySelector('#ss-sort-metric .ss-control-label')).color,
          frame:{border:parseFloat(frame.borderTopWidth)/scale,background:frame.backgroundImage,color:frame.backgroundColor}};
      },scale);
      const caption=language+' at550logical/'+(scale*100)+'%';
      check('Order, Sort by and Statistic keep the requested visual order: '+caption+': '+JSON.stringify(controls.order),
        controls.order.join('|')==='ss-sort-direction|ss-sort-metric|ss-sort-statistic');
      check('Shared control frames have one30px logical height: '+caption+': '+JSON.stringify(controls.heights),
        controls.heights.every(item=>Math.abs(item.height-30)<=1));
      check('Inactive Statistic is visibly distinct and semantically disabled: '+caption+': '+JSON.stringify(controls),
        controls.disabled && controls.aria==='true' && controls.opacity<0.9 && controls.color!==controls.activeColor);
      check('Transparency keeps a visible frame around its controls: '+caption,
        controls.frame.border>=1 && (controls.frame.background!=='none' || !['transparent','rgba(0, 0, 0, 0)'].includes(controls.frame.color)));
      for(const group of ['vehicles','maps','tiers']) for(const statistic of language==='en' && scale===1 ? ['min','avg','max'] : ['max']) {
        await page.evaluate(({group,statistic})=>{const payload=JSON.parse(model.payload);
          payload.scopes.launch.ordering[group]={metric:'credits_net',statistic,direction:'desc',chronology:'newest'};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},{group,statistic});
        await page.locator('#ss-group-'+group).click();await frames(page);
        const values=[12500,-23456,0,null],statLabel=messages[statistic==='avg' ? 'sort.avg' : 'metric.'+statistic];
        const expected=values.map(value=>{
          const amount=value===null ? messages['format.missing'] : (value>0 ? '+' : value<0 ? '-' : '')+
            String(Math.abs(value)).replace(/\B(?=(\d{3})+(?!\d))/g,messages['format.thousands']);
          return messages['sort.value_per_battle'].replace(/\{([0-9])\}/g,(_,index)=>[statLabel,messages['sort.credits'],amount][index]);
        });
        const audit=await page.locator('.ss-group-sort-value').evaluateAll((nodes,scale)=>nodes.map(node=>{
          const box=node.getBoundingClientRect(),card=node.closest('.ss-group').getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);
          return {text:node.textContent,font:parseFloat(getComputedStyle(node).fontSize)/scale,
            fits:box.width>0 && box.left>=card.left-1 && box.right<=card.right+1 && [...range.getClientRects()].every(text=>text.left>=box.left-1 && text.right<=box.right+1)};
        }),scale);
        check('Net sort displays the full per-battle '+statistic+' value rather than its aggregate total for '+group+' '+caption+': '+JSON.stringify(audit),
          audit.length===4 && audit.every((item,index)=>item.text===expected[index] && item.font>=11 && item.fits));
        check('An active aggregate metric restores Statistic access: '+group+' '+caption,
          await page.locator('#ss-sort-statistic .ss-select-trigger').isEnabled() && await page.locator('#ss-sort-statistic .ss-select-trigger').getAttribute('aria-disabled')==='false');
      }
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.tiers.metric='xp_received';
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});
      check('Other sort metrics remove the net-credit caption: '+caption,await page.locator('.ss-group-sort-value').count()===0);
      await page.evaluate(()=>{const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        scope.ordering.tiers={metric:'battle_wn8',statistic:'avg',direction:'desc',chronology:'oldest'};
        scope.tiers.forEach((item,index)=>{item.sort_value=[1968,1889,1593,1592][index];
          item.stats.wn8=[1743,1541,1635,1646][index];item.stats.battle_wn8.avg=item.sort_value;});
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
      const wn8Expected=[1968,1889,1593,1592].map(value=>messages['sort.value_wn8'].replace(/\{([0-9])\}/g,(_,index)=>
        [messages['sort.avg'],String(value)][index]));
      const wn8Captions=await page.locator('.ss-group-sort-value').allTextContents();
      check('WN8 sorting exposes its actual battle-average values separately from aggregate headline ratings: '+caption+': '+JSON.stringify(wn8Captions),
        JSON.stringify(wn8Captions)===JSON.stringify(wn8Expected)&&await page.locator('#ss-sort-chronology .ss-select-trigger').isDisabled());
    }
  } finally {await page.close();}
};
