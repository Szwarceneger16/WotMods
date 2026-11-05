/* Notice counts and coverage explanations must reflect the visible data. */
const fs=require('fs'), path=require('path');
module.exports=async({browser,nativeHost,check:reportCheck})=>{
  const failures=[];
  const check=(name,pass)=>{
    if(pass) reportCheck(name,true);
    else failures.push(name);
  };
  // This suite checks elapsed hover time. The default native host freezes
  // window.setTimeout for connection-retry tests, so use its real clock here.
  const page=await nativeHost(browser,{realTimers:true});
  const original=await page.evaluate(()=>JSON.parse(model.payload));
  const render=async payload=>page.evaluate(value=>{model.payload=JSON.stringify(value);GRZSessionStats.update(model.payload);},payload);
  const copy=()=>JSON.parse(JSON.stringify(original));
  let payload=copy();
  payload.warnings=['Deferred credits do not increase this balance.','Deferred credits do not increase this balance.',
    'Synthetic additional notice','Synthetic additional notice'];
  await render(payload);
  check('Repeated errors render once while reserve information uses the finance info icon',
    await page.locator('.ss-data-notices .ss-data-notice').count()===1 &&
    await page.locator('#ss-summary .ss-economy .ss-info-button').getAttribute('data-ss-help').then(t=>
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
  check('Incomplete totals keep their explanation on an explicit overview icon',
    await page.locator('#ss-summary .ss-coverage-legend,.ss-explainer').count()===0 &&
    await page.locator('#ss-summary .ss-summary-main .ss-info-button').getAttribute('data-ss-help').then(t=>
      t.includes('x/y: battles with this value / recorded battles.')));
  check('Zero available metric values keep their honest count and explanation',
    await page.locator('#ss-summary .ss-metric-row').first().locator('.ss-cell-coverage').getAttribute('aria-label')===
      'Data available for 0 of '+stats.observed_battles+' recorded battles.');
  check('Coverage numbers do not create immediate browser hover tooltips',
    await page.locator('#ss-summary .ss-cell-coverage[title],#ss-summary [data-ss-help]:not(.ss-info-button)').count()===0);
  check('Unavailable XP stays unknown instead of becoming zero',
    (await page.locator('#ss-summary .ss-metric-row').first().locator('.ss-metric-number').allTextContents()).every(v=>v==='—'));
  check('Finance coverage explains its own independent available count',
    await page.locator('#ss-summary .ss-money-row').first().locator('.ss-cell-coverage').first().getAttribute('aria-label')===
      'Data available for '+stats.currencies.credits.income_count+' of '+stats.observed_battles+' recorded battles.');
  const performance=page.locator('#ss-summary .ss-performance');
  const info=performance.locator('.ss-info-button');
  await performance.hover({position:{x:5,y:5}});
  await page.waitForTimeout(3100);
  check('Ordinary section hover has no help target or tooltip',
    await performance.evaluate(section=>!section.hasAttribute('data-ss-help') && !section.hasAttribute('tabindex') &&
      !section.hasAttribute('aria-describedby') && getComputedStyle(section).cursor!=='help') &&
    await page.locator('#ss-help-tooltip').isHidden());
  await info.hover({position:{x:3,y:5}});
  await page.waitForTimeout(600);
  check('Info icon hover waits instead of opening immediately',await page.locator('#ss-help-tooltip').isHidden());
  const infoBox=await info.boundingBox();
  await page.mouse.move(infoBox.x+7,infoBox.y+5);
  await page.waitForTimeout(600);
  check('Pointer movement restarts the full hover delay',await page.locator('#ss-help-tooltip').isHidden());
  await page.locator('#ss-help-tooltip').evaluate(tooltip => {
    // A new Gameface tooltip can have no measured size until its next frame.
    // Count production reads, then restore the real method before Playwright
    // checks actual visibility (which also requires a nonempty measured box).
    tooltip.__grzOriginalBounds=tooltip.getBoundingClientRect;
    tooltip.__grzBoundsReads=0;
    tooltip.getBoundingClientRect=function () {
      this.__grzBoundsReads++;
      return {left:0,right:0,top:0,bottom:0,width:0,height:0};
    };
  });
  await page.waitForTimeout(500);
  const tooltipAudit=await page.locator('#ss-help-tooltip').evaluate(tooltip=>{
    const audit={reads:tooltip.__grzBoundsReads,display:getComputedStyle(tooltip).display};
    tooltip.getBoundingClientRect=tooltip.__grzOriginalBounds;
    delete tooltip.__grzOriginalBounds;delete tooltip.__grzBoundsReads;
    return audit;
  });
  check('A stationary info icon opens its own explanation after one second',
    tooltipAudit.reads===0 && tooltipAudit.display==='block' &&
    await info.getAttribute('aria-describedby')==='ss-help-tooltip' && await info.getAttribute('aria-expanded')==='true' &&
    await page.locator('#ss-help-tooltip').isVisible() &&
    await page.locator('#ss-help-tooltip').textContent().then(t=>
      t.includes('Data available for 0 of '+stats.observed_battles+' recorded battles.') &&
      t.includes('Average battle WN8 may differ from period WN8.')));
  const tooltipPosition=await page.locator('#ss-help-tooltip').getAttribute('style');
  await page.mouse.move(infoBox.x+9,infoBox.y+6);
  check('An open tooltip stays anchored when the cursor moves inside its icon',
    await page.locator('#ss-help-tooltip').getAttribute('style')===tooltipPosition);
  const closeCommands=await page.evaluate(()=>__grzCommands.filter(command=>command.action==='close').length);
  await page.keyboard.press('Escape');
  check('Escape dismisses info help without closing the statistics window',
    await page.locator('#ss-help-tooltip').isHidden() &&
    await page.evaluate(()=>__grzCommands.filter(command=>command.action==='close').length)===closeCommands);
  await page.locator('#ss-close').hover();
  check('Leaving the info icon hides its tooltip',await page.locator('#ss-help-tooltip').isHidden());
  await info.focus();
  check('Intentional keyboard focus provides the accessible explanation directly',
    await page.locator('#ss-help-tooltip').isVisible() &&
    await page.locator('#ss-help-tooltip').getAttribute('role')==='tooltip' &&
    await info.getAttribute('aria-label').then(t=>t.startsWith('Information:')));
  await page.locator('#ss-scroll').evaluate(node=>node.scrollTop+=30);
  await page.waitForTimeout(50);
  check('Scrolling dismisses an open info tooltip',await page.locator('#ss-help-tooltip').isHidden());
  await info.click();
  check('An intentional click opens help without an immediate native title tooltip',
    await page.locator('#ss-help-tooltip').isVisible() && await info.getAttribute('title')===null &&
    await info.locator('.ss-info-symbol').getAttribute('aria-hidden')==='true');
  await page.locator('#ss-close').focus();
  await info.hover({position:{x:3,y:5}});
  await page.waitForTimeout(200);
  await page.locator('#ss-close').hover();
  await page.waitForTimeout(900);
  check('Leaving before one second cancels the pending help',await page.locator('#ss-help-tooltip').isHidden());
  await info.hover({position:{x:3,y:5}});
  await page.waitForTimeout(200);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(900);
  check('Escape also cancels pending help without closing the panel',
    await page.locator('#ss-help-tooltip').isHidden() &&
    await page.evaluate(()=>__grzCommands.filter(command=>command.action==='close').length)===closeCommands);
  await info.evaluate(button=>button.setAttribute('data-ss-help','<img src=x onerror=alert(1)>'));
  await info.focus();
  check('Tooltip content stays literal text even when it contains markup',
    await page.locator('#ss-help-tooltip').textContent()==='<img src=x onerror=alert(1)>' &&
    await page.locator('#ss-help-tooltip img').count()===0);
  await page.locator('#ss-close').focus();
  await page.evaluate(()=>{
    const audit=window.__grzHoverTimerAudit={scheduled:[],cleared:[],fired:[],
      originalSet:window.setTimeout,originalClear:window.clearTimeout};
    window.setTimeout=function(callback,delay,...args) {
      let id;
      id=audit.originalSet.call(window,function () {
        if(delay===1000) audit.fired.push(id);
        callback.apply(window,args);
      },delay);
      if(delay===1000) audit.scheduled.push(id);
      return id;
    };
    window.clearTimeout=function(id) {
      audit.cleared.push(id);
      return audit.originalClear.call(window,id);
    };
  });
  await info.hover({position:{x:3,y:5}});
  await page.waitForTimeout(100);
  const pendingTimer=await page.evaluate(()=>{
    const audit=window.__grzHoverTimerAudit;
    return [...audit.scheduled].reverse().find(id=>!audit.cleared.includes(id) && !audit.fired.includes(id));
  });
  check('The update scenario starts with a pending one-second info hover',typeof pendingTimer==='number');
  await render(payload);
  // Replacing an icon beneath a stationary pointer can legitimately generate
  // a new mouseover. Leave the replacement while checking the previous timer.
  await page.locator('#ss-close').hover();
  await page.waitForTimeout(1100);
  const timerAudit=await page.evaluate(()=>{
    const audit=window.__grzHoverTimerAudit;
    window.setTimeout=audit.originalSet;window.clearTimeout=audit.originalClear;
    delete window.__grzHoverTimerAudit;
    return {scheduled:audit.scheduled,cleared:audit.cleared,fired:audit.fired};
  });
  check('Updating data clears the previous hover timer without a ghost popup '+JSON.stringify({pendingTimer,...timerAudit}),
    timerAudit.cleared.includes(pendingTimer) && !timerAudit.fired.includes(pendingTimer) &&
    await page.locator('#ss-help-tooltip').isHidden());
  const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const [language,messages] of Object.entries(catalog)) {
    payload.localization={language,messages};await render(payload);
    check('Coverage help follows the selected language '+language,
      await page.locator('#ss-summary .ss-summary-main .ss-info-button').getAttribute('data-ss-help').then(t=>t.includes(messages['coverage.legend'])) &&
      await page.locator('#ss-summary .ss-performance .ss-info-button').getAttribute('aria-label').then(t=>t.startsWith(messages['help.info']+':')));
  }
  await render(copy());
  check('Complete data removes the temporary coverage explanation',
    await page.locator('#ss-summary .ss-summary-main .ss-info-button').count()===0);
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
    return note && note.textContent==='WN8 3/4' && group.querySelectorAll('.ss-info-button').length===1 &&
      heading.querySelector('.ss-info-button').getAttribute('data-ss-help').includes('Period WN8: data for 3/4 battles.') &&
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
  await page.locator('#ss-close').focus();
  const cleanupIcon=page.locator('#ss-summary .ss-performance .ss-info-button');
  await cleanupIcon.hover({position:{x:3,y:5}});
  await page.waitForTimeout(100);
  await page.evaluate(()=>GRZSessionStats.destroy());
  await page.waitForTimeout(1100);
  await cleanupIcon.focus();
  check('Destroy cancels pending help and removes focus listeners',
    await page.locator('#ss-help-tooltip').isHidden() && await cleanupIcon.getAttribute('aria-expanded')==='false');
  await page.close();
  reportCheck('Notice and information-icon contracts'+(failures.length ? ': '+failures.join(' | ') : ''),failures.length===0);
};
