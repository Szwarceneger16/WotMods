/* Additive aggregate sorting uses totals, never sums of ratings or rates. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{});
  const messages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  async function choose(field,value){
    await page.locator('#ss-sort-'+field+' [role=combobox]').click();
    await page.locator('#ss-sort-'+field+' [data-value="'+value+'"]').click();
    const command=await page.evaluate(()=>{
      const command=__grzCommands.filter(c=>c.action==='sort').pop(),payload=JSON.parse(model.payload);
      payload.scopes[command.scope].ordering[command.group]={metric:command.metric,statistic:command.statistic,direction:command.direction,chronology:command.chronology};
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);return command;
    });await frames(page);return command;
  }
  try{
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
      payload.window_size=[800,950];
      for(const group of ['vehicles','maps','tiers']){
        const item=scope[group][0];delete item.sort_value;
        item.stats.xp_base={count:2,sum:600,min:100,avg:300,max:500};
        item.stats.xp_received={count:1,sum:0,min:0,avg:0,max:0};
        item.stats.credits_net_received={count:2,sum:-500,min:-400,avg:-250,max:-100};
        item.stats.credits_net_base={count:2,sum:-1400,min:-900,avg:-700,max:-500};
        item.stats.credits_income_base={count:2,sum:100,min:0,avg:50,max:100};
        item.stats.credits_income_received={count:2,sum:1000,min:400,avg:500,max:600};
        item.stats.credits_costs={count:2,sum:1500,min:400,avg:750,max:1100};
        item.stats.currencies.credits.income_base=100;item.stats.currencies.credits.income_base_count=2;
        item.stats.currencies.credits.net_base=-1400;item.stats.currencies.credits.net_base_count=2;
        item.stats.currencies.credits.net=-500;item.stats.currencies.credits.income=1000;item.stats.currencies.credits.costs=1500;
        scope[group]=[item];scope.pagination[group]={page:0,pages:1,page_size:40,total:1};
      }
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
    });await frames(page);
    for(const group of ['vehicles','maps','tiers']){
      await page.locator('#ss-group-'+group).click();
      for(const metric of ['xp_base','xp_received','credits_income_base','credits_income_received','credits_net_base','credits_net_received','credits_costs']){
        await choose('metric',metric);
        check('All is available only for an additive aggregate metric '+group+'/'+metric,
          await page.locator('#ss-sort-statistic [data-value="sum"]').evaluate(node=>node.style.display!=='none'));
        const command=await choose('statistic','sum');
        check('All dispatches the owned aggregate sum '+group+'/'+metric,
          command.metric===metric&&command.statistic==='sum'&&command.group===group&&command.account_key&&command.period_id);
        if(metric.startsWith('credits_')){
          check('All '+metric+' highlights its explicit total figure rather than a source action '+group,
            await page.locator('.ss-group .ss-money-value[data-ss-metric="'+metric+'"] > .ss-cell-value').evaluate((figure,metric)=>
              figure.getAttribute('data-ss-sort-active')===metric,metric)&&
            await page.locator('.ss-group-sort-value').count()===0);
        }else{
          const caption=await page.locator('.ss-group-sort-value').getAttribute('aria-label');
          const visible=await page.locator('.ss-group-sort-value .ss-group-sort-number').textContent();
          check('XP All shows an explicit total without highlighting Avg '+group+'/'+metric,
            caption.includes(metric==='xp_base'?'600':'0')&&caption.includes('Total')&&visible===(metric==='xp_base'?'600':'0')&&
            await page.locator('.ss-metric-row [data-ss-sort-active]').count()===0);
        }
      }
      for(const metric of ['battle_wn8','win_rate',...(group==='tiers'?[]:['battles'])]){
        const command=await choose('metric',metric);
        check('Changing from All to '+metric+' restores Avg and hides All '+group,
          command.statistic==='avg'&&await page.locator('#ss-sort-statistic [data-value="sum"]').evaluate(node=>{
            const before=__grzCommands.filter(c=>c.action==='sort').length;node.onclick();
            return node.style.display==='none'&&__grzCommands.filter(c=>c.action==='sort').length===before;
          }));
        if(metric!=='battle_wn8'){await choose('metric','xp_base');await choose('statistic','sum');}
      }
    }
    await page.locator('#ss-group-battles').click();await choose('metric','credits_income_received');
    check('Battles can sort gross income but never expose an aggregate All option',
      await page.locator('#ss-sort-statistic [role=combobox]').isDisabled()&&
      await page.locator('#ss-sort-statistic [data-value="sum"]').evaluate(node=>node.style.display==='none')&&
      await page.locator('.ss-money-row [data-ss-sort-active="credits_income_received"]').count()>0);
    await choose('metric','credits_costs');
    check('Battles sort recorded expense magnitudes and highlight the existing displayed costs',
      await page.locator('#ss-sort-statistic [role=combobox]').isDisabled()&&
      await page.locator('#ss-sort-statistic [data-value="sum"]').evaluate(node=>node.style.display==='none')&&
      await page.locator('.ss-money-row [data-ss-sort-active="credits_costs"]').count()>0);
    for(const [language,catalog]of Object.entries(messages)){
      await page.evaluate(({language,catalog})=>{
        const payload=JSON.parse(model.payload);payload.localization={language,messages:catalog};
        payload.scopes.launch.ordering.maps={metric:'credits_income_received',statistic:'sum',direction:'desc',chronology:'newest'};
        model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
        document.querySelector('#ss-group-maps').onclick();
      },{language,catalog});await frames(page);
      check('All and gross-credit labels follow the selected language '+language,
        await page.locator('#ss-sort-statistic .ss-select-trigger .ss-control-label').textContent()===catalog['sort.sum']&&
        await page.locator('#ss-sort-metric .ss-select-trigger .ss-control-label').textContent()===catalog['sort.credits_income_received.caption']);
    }
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.maps={metric:'battle_wn8',statistic:'sum',direction:'desc',chronology:'newest'};
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
    });
    check('A legacy invalid WN8 sum snapshot normalizes to Avg before presentation',
      await page.locator('#ss-sort-statistic .ss-select-trigger .ss-control-label').textContent()===messages.uk['sort.avg']);
  }finally{await page.close();}
  await require('./ui-credit-labels.cjs')({browser,nativeHost,check});
  await require('./ui-credit-history.cjs')({browser,nativeHost,check});
};
