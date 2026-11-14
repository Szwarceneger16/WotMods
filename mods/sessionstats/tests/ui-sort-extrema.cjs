/* A selected aggregate extremum links to its actual owned battle, not a page guess. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{initialViewport:{width:1800,height:1300},viewport:{width:1800,height:1300,scale:1}});
  const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  let revision=0;
  const metrics=['xp_base','xp_received','battle_wn8','credits_net','credits_gross','credits_costs'];
  async function publish(group,metric,statistic,overrides={}){
    await page.evaluate(({group,metric,statistic,overrides,revision})=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
      payload.window_size=[1200,1050];scope.data_revision='extremum-'+revision;
      scope.ordering=scope.ordering||{};scope.ordering[group]={metric,statistic,direction:'desc',chronology:'newest'};
      const item=scope[group][0];scope[group]=[item];
      scope.pagination[group]={page:0,pages:1,total:1,page_size:40};
      const value=metric==='credits_net'?-500:statistic==='min'?0:12345;
      item.sort_value=value;
      item.sort_battle={id:'synthetic-extreme-'+group+'-'+metric+'-'+statistic,name:'<b>Synthetic tank</b>',
        map:'Synthetic off-page map',map_id:'synthetic-map',started_at:1793514000,outcome:'win',wn8:500,
        metric,statistic,value,...overrides};
      // Deliberately absent from the currently loaded history page.
      item.battle_list={page:0,pages:3,total:30,page_size:10,items:[{id:'different-visible-history',name:'Other tank',map:'Other map',outcome:'win'}]};
      delete scope.battle_focus;
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
    },{group,metric,statistic,overrides,revision:++revision});
    await page.locator('#ss-group-'+group).click();await frames(page);
  }
  try{
    for(const group of ['vehicles','maps','tiers'])for(const metric of metrics)for(const statistic of ['min','max']){
      await publish(group,metric,statistic);
      check('Every supported '+group+'/'+metric+'/'+statistic+' identifies its exact battle, including zero and signed values',
        await page.locator('.ss-sort-battle-link').count()===1&&await page.locator('.ss-sort-battle-link').evaluate((node,{group,metric,statistic})=>{
          const expected='synthetic-extreme-'+group+'-'+metric+'-'+statistic;
          const host=node.closest('.ss-group-sort-host'),source=host&&host.getAttribute('data-ss-sort-display')==='source';
          const sourceTitleMatches=!source||(host.title.startsWith(host.querySelector('.ss-group-sort-caption').textContent+': ')&&host.title.includes('2026'));
          return node.getAttribute('data-battle-id')===expected&&node.getAttribute('aria-label').includes('Show battle')&&
            node.getAttribute('data-ss-help').includes('Synthetic off-page map')&&node.getAttribute('data-ss-help').includes('<b>Synthetic tank</b>')&&
            node.getAttribute('data-ss-help').includes('2026')&&sourceTitleMatches;
        },{group,metric,statistic}));
    }
    for(const group of ['vehicles','maps','tiers']){
      await publish(group,'credits_costs','max');await page.locator('.ss-sort-battle-link').click();
      const command=await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select').pop());
      check('The '+group+' extremum reuses native battle selection with full context ownership',command.id==='synthetic-extreme-'+group+'-credits_costs-max'&&
        command.scope==='launch'&&Boolean(command.account_key)&&Boolean(command.period_id)&&Boolean(command.request_id));
    }
    await page.locator('#ss-group-tiers').focus();
    await page.locator('.ss-sort-battle-link').focus();
    check('Action-link focus uses the owned tooltip safely without interpreting battle markup',
      await page.locator('#ss-help-tooltip').isVisible()&&await page.locator('#ss-help-tooltip').textContent().then(text=>text.includes('<b>Synthetic tank</b>'))&&
      await page.locator('#ss-help-tooltip b').count()===0);
    await page.evaluate(()=>{window.__retiredExtremeClick=document.querySelector('.ss-sort-battle-link').onclick;});
    for(const statistic of ['avg','sum']){
      await publish('tiers','credits_costs',statistic);
      const before=await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select').length);
      await page.evaluate(()=>__retiredExtremeClick());
      check('An '+statistic+' has no fabricated winner and retired link callbacks cannot navigate',
        await page.locator('.ss-sort-battle-link').count()===0&&await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select').length)===before);
    }
    for(const invalid of [{metric:'xp_received'},{statistic:'min'},{value:null},{value:999},{id:''}]){
      await publish('maps','xp_base','max',invalid);
      check('A mismatched or unavailable native extremum reference does not offer a link '+JSON.stringify(invalid),await page.locator('.ss-sort-battle-link').count()===0);
    }
    for(const metric of ['off','battles','win_rate']){
      await publish('maps',metric,'max');
      check('Non-extremum metric '+metric+' never invents a battle winner',await page.locator('.ss-sort-battle-link').count()===0);
    }
    for(const [language,messages]of Object.entries(catalogs)){
      await page.evaluate(({language,messages})=>{const payload=JSON.parse(model.payload);payload.localization={language,messages};model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);},{language,messages});
      await publish('maps','xp_base','max');
      check('Extremum action and explanation use the selected interface language '+language,
        await page.locator('.ss-sort-battle-link').getAttribute('aria-label').then(text=>text.startsWith(messages['maps.open_battle']+': ')&&text.includes(messages['sort.extreme_battle'].split('{0}')[0])));
    }
    await page.evaluate(()=>{window.__retiredExtremeClick=document.querySelector('.ss-sort-battle-link').onclick;const payload=JSON.parse(model.payload);payload.scopes.launch.data_revision='new-correction';model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);});
    const before=await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select').length);
    await page.evaluate(()=>__retiredExtremeClick());
    check('A retained link cannot navigate after a newer data revision',await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select').length)===before);
    await publish('tiers','xp_received','max');await page.locator('.ss-sort-battle-link').click();
    const request=await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select').pop());
    await page.evaluate(request=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope.battles[0];
      scope.battles=[{...sample,id:request.id,name:'Synthetic selected extremum'}];
      scope.pagination.battles={page:2,pages:3,total:85,page_size:40};scope.battle_focus={id:request.id,request_id:request.request_id};
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
    },request);await frames(page);
    check('A tier extremum outside the displayed history opens the native selected page and target marker',
      await page.locator('#ss-group-battles').getAttribute('aria-pressed')==='true'&&
      await page.locator('.ss-battle-target').getAttribute('data-group-id')===request.id);
    await page.evaluate(()=>__retiredExtremeClick());
    check('A retained aggregate link cannot navigate after the group changes',await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select').length)===before+1);
    for(const changed of ['account','period']){
      await publish('maps','xp_base','max');
      const count=await page.evaluate(changed=>{
        window.__retiredExtremeClick=document.querySelector('.ss-sort-battle-link').onclick;
        const before=__grzCommands.filter(row=>row.action==='battle_select').length,payload=JSON.parse(model.payload);
        if(changed==='account')payload.account_key='EU:synthetic-replacement-account';
        else payload.scopes.launch.period_id+='-replaced';
        model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);__retiredExtremeClick();return before;
      },changed);
      check('A retained extremum link cannot cross a replaced '+changed+' owner',await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select').length)===count);
    }
    await publish('maps','xp_base','max');
    const destroyed=await page.evaluate(()=>{
      const click=document.querySelector('.ss-sort-battle-link').onclick,before=__grzCommands.filter(row=>row.action==='battle_select').length;
      GRZSessionStats.destroy();click();return {before,after:__grzCommands.filter(row=>row.action==='battle_select').length};
    });
    check('Destroyed extremum callbacks are inert without touching retired data',destroyed.before===destroyed.after);
  }finally{await page.close();}
};
