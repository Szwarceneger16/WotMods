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
  check('Repeated translated notices render once each',await page.locator('.ss-data-notices .ss-data-notice').count()===2);
  check('Notice count matches visible unique messages',await page.locator('#ss-status').textContent().then(t=>t.includes('Data notices: 2')));
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
  check('Incomplete totals explain x/y once in the summary',await page.locator('#ss-summary .ss-coverage-legend').count()===1);
  check('Zero available metric values keep their honest count and explanation',
    await page.locator('#ss-summary .ss-metric-row').first().locator('.ss-cell-coverage').getAttribute('title')===
      'Data available for 0 of '+stats.observed_battles+' recorded battles.');
  check('Unavailable XP stays unknown instead of becoming zero',
    (await page.locator('#ss-summary .ss-metric-row').first().locator('.ss-metric-number').allTextContents()).every(v=>v==='—'));
  check('Finance coverage explains its own independent available count',
    await page.locator('#ss-summary .ss-money-row').first().locator('.ss-cell-coverage').first().getAttribute('aria-label')===
      'Data available for '+stats.currencies.credits.income_count+' of '+stats.observed_battles+' recorded battles.');
  const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const [language,messages] of Object.entries(catalog)) {
    payload.localization={language,messages};await render(payload);
    check('Coverage legend follows the selected language '+language,
      await page.locator('#ss-summary .ss-coverage-legend').textContent()===messages['coverage.legend']);
  }
  await render(copy());
  check('Complete data removes the temporary coverage explanation',await page.locator('#ss-summary .ss-coverage-legend').count()===0);
  check('Cleared notices remove the notice count from the footer',await page.locator('#ss-status').textContent().then(t=>!t.includes('Data notices:')));
  payload=copy();
  const vehicle=payload.scopes.launch.vehicles[0], partial=vehicle.stats;
  vehicle.name='Leox';
  partial.observed_battles=4;partial.battles=3;partial.wn8_count=3;
  partial.xp_base.count=3;partial.battle_wn8.count=3;partial.free_xp.count=3;
  for(const field of ['income','costs','net']) partial.currencies.credits[field+'_count']=3;
  await render(payload);
  check('Partial group keeps its WN8 note beside the name and Free XP above the tables',await page.locator('#ss-groups .ss-group').first().evaluate(group=>{
    const heading=group.querySelector('.ss-group-heading'), note=heading.querySelector('.ss-coverage-note');
    const title=heading.querySelector('.ss-group-title').getBoundingClientRect();
    const free=group.querySelector('.ss-free-xp').getBoundingClientRect();
    return note && note.getBoundingClientRect().left>=title.right && note.getBoundingClientRect().top<title.bottom &&
      free.bottom<=group.querySelector('.ss-details').getBoundingClientRect().top+1;
  }));
  check('Shared financial coverage appears once per row without tall value cells',await page.locator('#ss-groups .ss-group').first().locator('.ss-money-row').first().evaluate(row=>
    row.querySelectorAll('.ss-cell-coverage').length===1 && row.querySelector('.ss-money-label .ss-cell-coverage').textContent==='3/4' && row.getBoundingClientRect().height<=30));
  partial.currencies.credits.net_count=2;await render(payload);
  check('Different financial coverage retains the independent count for each value',await page.locator('#ss-groups .ss-group').first().locator('.ss-money-row').first().locator('.ss-money-value .ss-cell-coverage').allTextContents().then(values=>values.join('|')==='3/4|3/4|2/4'));
  await page.close();
};
