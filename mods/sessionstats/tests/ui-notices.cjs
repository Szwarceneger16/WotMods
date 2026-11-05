/* Notice counts and coverage explanations must reflect the visible data. */
const fs=require('fs'), path=require('path');
module.exports=async({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{});
  const original=await page.evaluate(()=>JSON.parse(model.payload));
  const render=async payload=>page.evaluate(value=>{model.payload=JSON.stringify(value);GRZSessionStats.update(model.payload);},payload);
  const copy=()=>JSON.parse(JSON.stringify(original));
  let payload=copy();
  payload.warnings=['Deferred credits do not increase this balance.','Deferred credits do not increase this balance.',
    'Synthetic additional notice','Synthetic additional notice'];
  await render(payload);
  check('Repeated errors render once while routine reserve information moves to section help',
    await page.locator('.ss-data-notices .ss-data-notice').count()===1 &&
    await page.locator('#ss-summary').getAttribute('data-ss-help').then(t=>
      t.split('\n').filter(line=>line==='Deferred credits do not increase this balance.').length===1));
  check('Notice count matches visible unique errors',await page.locator('#ss-status').textContent().then(t=>t.includes('Data notices: 1')));
  check('Notice presentation does not rewrite the incoming model',await page.evaluate(()=>JSON.parse(model.payload).warnings.length===4));
  payload.warnings=['__proto__','__proto__','<img src=x onerror=alert(1)>'];
  await render(payload);
  check('Unrecognized notice text remains literal and cannot create markup',
    await page.locator('.ss-data-notices .ss-data-notice').count()===2 && await page.locator('.ss-data-notices img').count()===0);
  payload=copy();payload.loading=true;
  payload.warnings=['Loading history. New battle results are being saved.',
    'Loading history. New battle results are being saved.','Synthetic startup error','Synthetic startup error'];
  await render(payload);
  check('Loading displays its primary notice and each additional error once',await page.locator('#ss-summary .ss-data-notice').count()===2);
  payload.loading=false;payload.load_error='Synthetic startup error';
  payload.warnings=['Synthetic startup error','Synthetic startup error'];
  await render(payload);
  check('Failed loading does not repeat the primary error',await page.locator('#ss-summary .ss-data-notice').count()===1);
  payload=copy();payload.warnings=[];
  const stats=payload.scopes.launch.summary;
  stats.observed_battles=stats.battles+1;stats.missing_results=1;
  stats.xp_base.count=0;stats.xp_base.min=stats.xp_base.avg=stats.xp_base.max=null;
  await render(payload);
  check('Incomplete totals keep their explanation in section help without a permanent prose row',
    await page.locator('#ss-summary .ss-coverage-legend,.ss-explainer').count()===0 &&
    await page.locator('#ss-summary').getAttribute('data-ss-help').then(t=>
      t.includes('x/y: battles with this value / recorded battles.')));
  check('Zero available metric values keep their honest count and explanation',
    await page.locator('#ss-summary .ss-metric-row').first().locator('.ss-cell-coverage').getAttribute('title')===
      'Data available for 0 of '+stats.observed_battles+' recorded battles.');
  check('Unavailable XP stays unknown instead of becoming zero',
    (await page.locator('#ss-summary .ss-metric-row').first().locator('.ss-metric-number').allTextContents()).every(v=>v==='—'));
  check('Finance coverage explains its own independent available count',
    await page.locator('#ss-summary .ss-money-row').first().locator('.ss-cell-coverage').first().getAttribute('aria-label')===
      'Data available for '+stats.currencies.credits.income_count+' of '+stats.observed_battles+' recorded battles.');
  const performance=page.locator('#ss-summary .ss-performance');
  await page.locator('#ss-help-tooltip').evaluate(tooltip => {
    // A new Gameface tooltip can have no measured size until its next frame.
    tooltip.getBoundingClientRect=()=>({left:0,right:0,top:0,bottom:0,width:0,height:0});
  });
  await performance.hover({position:{x:5,y:5}});
  check('Hovering the whole performance section opens help and uses the help cursor',
    await performance.evaluate(section=>getComputedStyle(section).cursor==='help' &&
      section.getAttribute('aria-describedby')==='ss-help-tooltip') &&
    await page.locator('#ss-help-tooltip').isVisible() &&
    await page.locator('#ss-help-tooltip').textContent().then(t=>
      t.includes('Data available for 0 of '+stats.observed_battles+' recorded battles.') &&
      t.includes('Average battle WN8 may differ from period WN8.')));
  const closeCommands=await page.evaluate(()=>__grzCommands.filter(command=>command.action==='close').length);
  await page.keyboard.press('Escape');
  check('Escape dismisses section help without closing the statistics window',
    await page.locator('#ss-help-tooltip').isHidden() &&
    await page.evaluate(()=>__grzCommands.filter(command=>command.action==='close').length)===closeCommands);
  await page.locator('#ss-close').hover();
  check('Leaving the explained section hides its tooltip',await page.locator('#ss-help-tooltip').isHidden());
  await performance.focus();
  check('The same explanation is available when its entire section receives keyboard focus',
    await page.locator('#ss-help-tooltip').isVisible() &&
    await page.locator('#ss-help-tooltip').getAttribute('role')==='tooltip');
  const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const [language,messages] of Object.entries(catalog)) {
    payload.localization={language,messages};await render(payload);
    check('Coverage help follows the selected language '+language,
      await page.locator('#ss-summary').getAttribute('data-ss-help').then(t=>t.includes(messages['coverage.legend'])));
  }
  await render(copy());
  check('Complete data removes the temporary coverage explanation',
    await page.locator('#ss-summary').getAttribute('data-ss-help').then(t=>!t || !t.includes('x/y:')));
  check('Cleared notices remove the notice count from the footer',await page.locator('#ss-status').textContent().then(t=>!t.includes('Data notices:')));
  payload=copy();
  const vehicle=payload.scopes.launch.vehicles[0], partial=vehicle.stats;
  vehicle.name='Leox';
  partial.observed_battles=4;partial.battles=3;partial.wn8_count=3;
  partial.xp_base.count=3;partial.battle_wn8.count=3;partial.free_xp.count=3;
  for(const field of ['income','costs','net']) partial.currencies.credits[field+'_count']=3;
  await render(payload);
  check('Partial groups keep numerical WN8 coverage beside the name, explanatory help and Free XP above tables',await page.locator('#ss-groups .ss-group').first().evaluate(group=>{
    const heading=group.querySelector('.ss-group-heading'), note=heading.querySelector('.ss-wn8-coverage');
    const title=heading.querySelector('.ss-group-title').getBoundingClientRect();
    const free=group.querySelector('.ss-free-xp').getBoundingClientRect();
    return note && note.textContent==='WN8 3/4' && group.getAttribute('data-ss-help').includes('Period WN8: data for 3/4 battles.') &&
      group.querySelectorAll('.ss-coverage-note').length===0 &&
      note.getBoundingClientRect().left>=title.right && note.getBoundingClientRect().top<title.bottom &&
      free.bottom<=group.querySelector('.ss-details').getBoundingClientRect().top+1;
  }));
  check('Shared financial coverage appears once per row without tall value cells',await page.locator('#ss-groups .ss-group').first().locator('.ss-money-row').first().evaluate(row=>
    row.querySelectorAll('.ss-cell-coverage').length===1 && row.querySelector('.ss-money-label .ss-cell-coverage').textContent==='3/4' && row.getBoundingClientRect().height<=30));
  check('Shared XP and battle WN8 coverage uses the header and keeps both rows compact',await page.locator('#ss-groups .ss-group').first().locator('.ss-performance').evaluate(table=>
    table.querySelector('.ss-metric-head .ss-cell-coverage').textContent==='3/4' &&
    table.querySelectorAll('.ss-metric-row .ss-cell-coverage').length===0 &&
    Array.from(table.querySelectorAll('.ss-metric-row')).every(row=>row.getBoundingClientRect().height<=30)));
  for(const width of [320,744]) {
    await page.setViewportSize({width,height:820});payload.viewport.width=width;await render(payload);
    check('Shared partial metric count stays visible at width '+width,await page.locator('#ss-groups .ss-group').first().locator('.ss-metric-count .ss-cell-coverage').evaluate(node=>
      node.textContent==='3/4' && node.getBoundingClientRect().height>0 && node.getBoundingClientRect().width>0));
  }
  partial.battle_wn8.count=2;await render(payload);
  check('Different XP and WN8 coverage remains independently visible',await page.locator('#ss-groups .ss-group').first().locator('.ss-metric-row .ss-cell-coverage').allTextContents().then(values=>values.join('|')===' (3/4)| (2/4)'));
  partial.currencies.credits.net_count=2;await render(payload);
  check('Different financial coverage retains the independent count for each value',await page.locator('#ss-groups .ss-group').first().locator('.ss-money-row').first().locator('.ss-money-value .ss-cell-coverage').allTextContents().then(values=>values.join('|')==='3/4|3/4|2/4'));
  await page.close();
};
