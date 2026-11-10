const fs=require('fs'),path=require('path');
module.exports = async function ({browser, nativeHost, check}) {
  check('Timeline line styling uses supported tiled gradients instead of unsupported dashed borders',
    !/border[^;{}]*\bdashed\b/.test(fs.readFileSync(path.join(__dirname,'../ui/session_stats.css'),'utf8')));
  const page = await nativeHost(browser, {
    initialViewport: {width:3840, height:2160},
    viewport: {width:3840, height:2160, scale:2}, changedScale:1, realTimers:true,
  });
  await page.evaluate(() => {
    const payload = JSON.parse(model.payload);
    payload.account_key = 'fixture-account';
    payload.localization = {language:'en', selected:'auto', messages:{}};
    const timeline = payload.scopes.timeline = JSON.parse(JSON.stringify(payload.scopes.manual));
    timeline.from_point = timeline.to_point = '';
    timeline.time_points = [['first', 1700000000], ['last', 1700100000]];
    timeline.battles[0].details = {
      pass_points:{credited:33, battle:8, missions:10, vehicle:15},
      missions:{
        'challenge:8:2':{kind:'crucible', name:'<b>Fixture stage</b>', stage:2, status:'failed'},
        'personal:123':{kind:'personal', name:'Fixture mission', operation:'Operation Fossa', status:'honors'},
      },
      active_crucible:'challenge:8:2', bonuses:{dailyXPFactor10:20,eventCrystal:43,eventCredits:12345678,
        boosterCredits:26943,boosterXP:136,boosterFreeXP:28,boosterTMenXP:544,
        wotPlusCredits:8083,wotPlusXP:41,wotPlusFreeXP:2,wotPlusCrewXP:164,
        appliedPremiumCreditsFactor100:150,appliedPremiumXPFactor100:150},
    };
    model.payload = JSON.stringify(payload);
    __grzEvents['viewEnv.onDataChanged']();
  });
  await page.locator('#ss-scope-manual').click();
  check('Timeline defaults to all history and replaces manual reset', await page.evaluate(() =>
    document.querySelector('#ss-timeline-from .ss-select-trigger').textContent === 'Beginning of history' &&
    document.querySelector('#ss-timeline-to .ss-select-trigger').textContent === 'Now' &&
    document.querySelector('#ss-reset').style.display === 'none'));
  await page.evaluate(() => {
    window.__timelineReadySnapshot = JSON.parse(model.payload);
    window.__timelineDataFingerprint = function () {
      const text = node => {
        const copy = node.cloneNode(true);copy.querySelectorAll('.ss-info-button').forEach(button=>button.remove());
        return copy.textContent.replace(/\s+/g,' ').trim();
      };
      return {summary:text(document.getElementById('ss-summary')),
        cards:[...document.querySelectorAll('#ss-groups .ss-group')].map(card=>({id:card.dataset.groupId,text:text(card)})),
        page:document.getElementById('ss-page-label').textContent};
    };
    window.__timelineCompleteFingerprint = __timelineDataFingerprint();
    window.__timelineCompleteCardNodes = [...document.querySelectorAll('#ss-groups .ss-group')];
  });
  for (const scopedState of ['loading', 'error']) {
    await page.evaluate(scopedState => {
      const payload = JSON.parse(JSON.stringify(__timelineReadySnapshot));
      payload.loading = false; payload.load_error = '';
      const timeline = payload.scopes.timeline;
      timeline.loading = scopedState === 'loading';
      timeline.load_error = scopedState === 'error' ? 'Synthetic selected range failure' : '';
      timeline.from_point = scopedState === 'error' ? 'first' : '';
      timeline.summary.battles = timeline.summary.observed_battles = timeline.summary.wn8 = 9999999;
      for (const key of ['min','avg','max','sum']) timeline.summary.xp_base[key] = 9999999;
      for (const group of ['vehicles','maps','tiers','battles']) timeline[group].forEach(row=>{
        row.name = 'Synthetic incomplete prefix row';row.stats.wn8 = 9999999;
      });
      window.__timelineRangeCount = __grzCommands.filter(command => command.action === 'timeline_range').length;
      model.payload = JSON.stringify(payload); __grzEvents['viewEnv.onDataChanged']();
    }, scopedState);
    check('Selected range ' + scopedState + ' keeps both timeline bounds available',
      await page.locator('#ss-timeline-from .ss-select-trigger').isVisible() &&
      await page.locator('#ss-timeline-to .ss-select-trigger').isVisible() &&
      await page.locator('#ss-timeline-from .ss-select-trigger').isEnabled() &&
      await page.locator('#ss-timeline-to .ss-select-trigger').isEnabled());
    const retained = await page.evaluate(() => {
      const current = __timelineDataFingerprint(),previous = __timelineCompleteFingerprint,
        nodes = [...document.querySelectorAll('#ss-groups .ss-group')];
      const compact = (current.summary + current.cards.map(card=>card.text).join('')).replace(/\s/g,'');
      return {summarySame:current.summary===previous.summary,cardsSame:JSON.stringify(current.cards)===JSON.stringify(previous.cards),
        nodesSame:nodes.length>0 && nodes.length===__timelineCompleteCardNodes.length && nodes.every((node,index)=>node===__timelineCompleteCardNodes[index]),
        pageSame:current.page===previous.page,busy:document.getElementById('ss-groups').getAttribute('aria-busy'),
        prefixRendered:compact.includes('9999999') || compact.includes('Syntheticincompleteprefixrow'),
        status:document.getElementById('ss-status').textContent,ids:current.cards.map(card=>card.id)};
    });
    check('Selected range ' + scopedState + ' retains only the last complete DOM while marking its pending state: '+JSON.stringify(retained),
      retained.summarySame && retained.cardsSame && retained.nodesSame && retained.pageSame && retained.busy==='true' &&
      !retained.prefixRendered && retained.status===(scopedState==='error' ?
        'Synthetic selected range failure' : 'Loading history. New battle results are being saved.'));
    const field = scopedState === 'loading' ? 'from' : 'to';
    const point = scopedState === 'loading' ? 'first' : 'last';
    await page.locator('#ss-timeline-' + field + ' .ss-select-trigger').click();
    await page.locator('#ss-timeline-' + field + ' [data-value="' + point + '"]').click();
    check('Selected range ' + scopedState + ' can be replaced with a newly selected bound',
      await page.evaluate(scopedState => {
        const commands = __grzCommands.filter(command => command.action === 'timeline_range');
        const command = commands[commands.length - 1];
        return commands.length === __timelineRangeCount + 1 && command.account_key === 'fixture-account' &&
          command.from_point === 'first' && command.to_point === (scopedState === 'error' ? 'last' : '');
      }, scopedState));
  }
  async function publishOrderingState(loading, name) {
    await page.evaluate(({loading,name})=>{
      const payload=JSON.parse(JSON.stringify(__timelineReadySnapshot)),timeline=payload.scopes.timeline;
      payload.loading=false;payload.load_error='';timeline.loading=loading;timeline.load_error='';
      if(name)timeline.vehicles[0].name=name;
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    },{loading,name});
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  }
  await publishOrderingState(false);
  await publishOrderingState(true);
  const busyOrder=await page.evaluate(()=>{
    const fields=['chronology','metric','direction','statistic'],before=__grzCommands.filter(command=>command.action==='sort').length;
    const disabled=fields.every(field=>{
      const button=document.querySelector('#ss-sort-'+field+' .ss-select-trigger');
      return button.disabled && button.getAttribute('aria-disabled')==='true';
    });
    // Retained native option callbacks must obey the same unavailable-index gate.
    for(const [field,value]of [['metric','xp_base'],['chronology','oldest'],['direction','asc'],['statistic','max']])
      document.querySelector('#ss-sort-'+field+' [data-value="'+value+'"]').onclick();
    return {disabled,before,after:__grzCommands.filter(command=>command.action==='sort').length};
  });
  check('A rebuilding projection disables all ordering controls and retained option callbacks cannot issue rejected sorts: '+JSON.stringify(busyOrder),
    busyOrder.disabled && busyOrder.after===busyOrder.before);
  await publishOrderingState(false,'Synthetic completed projection after blocked sorting');
  check('Completing a projection after attempted busy sorting renders its new data without tab or group changes',
    await page.locator('#ss-groups').textContent().then(text=>text.includes('Synthetic completed projection after blocked sorting')) &&
    await page.locator('#ss-sort-metric .ss-select-trigger').isEnabled() && await page.locator('#ss-sort-chronology .ss-select-trigger').isEnabled());
  const beforeOrderingRace=await page.evaluate(()=>__grzCommands.filter(command=>command.action==='sort').length);
  await page.evaluate(()=>document.querySelector('#ss-sort-metric [data-value="xp_base"]').onclick());
  check('The readiness race begins with a real pending ordering request',await page.evaluate(before=>{
    const commands=__grzCommands.filter(command=>command.action==='sort');
    return commands.length===before+1 && commands[commands.length-1].metric==='xp_base';
  },beforeOrderingRace));
  await publishOrderingState(true);
  check('An unavailable-index snapshot retires a pre-existing sort intent instead of being discarded',
    await page.locator('#ss-sort-metric .ss-select-trigger').isDisabled() &&
    await page.locator('#ss-status').textContent()==='Loading history. New battle results are being saved.');
  await publishOrderingState(false,'Synthetic completed projection after rejected intent');
  check('A completed projection can render after a ready-to-loading rejected-sort race',
    await page.locator('#ss-groups').textContent().then(text=>text.includes('Synthetic completed projection after rejected intent')) &&
    await page.locator('#ss-sort-metric .ss-select-trigger').isEnabled());
  await page.evaluate(() => {
    const payload = JSON.parse(JSON.stringify(__timelineReadySnapshot));
    payload.loading = true; payload.load_error = '';
    model.payload = JSON.stringify(payload); __grzEvents['viewEnv.onDataChanged']();
  });
  check('Global history loading keeps timeline bounds unavailable and time-point creation disabled',
    !await page.locator('#ss-timeline-from .ss-select-trigger').isVisible() &&
    !await page.locator('#ss-timeline-to .ss-select-trigger').isVisible() &&
    await page.locator('#ss-time-point').isDisabled() &&
    await page.locator('#ss-summary .ss-kpi-value').count() === 0 &&
    await page.locator('#ss-groups .ss-group').count() === 0);
  await page.evaluate(() => {
    model.payload = JSON.stringify(__timelineReadySnapshot); __grzEvents['viewEnv.onDataChanged']();
  });
  check('Completing the scoped request restores the original timeline fixture and totals',
    await page.locator('#ss-timeline-from .ss-select-trigger').textContent() === 'Beginning of history' &&
    await page.locator('#ss-timeline-to .ss-select-trigger').textContent() === 'Now' &&
    await page.locator('#ss-summary .ss-kpi-value').count() > 0 &&
    await page.locator('#ss-groups .ss-group').count() > 0);
  async function controlsFit(wrapped) {
    return page.evaluate(wrapped => {
      const box = selector => document.querySelector(selector).getBoundingClientRect();
      const title = box('.ss-title-identity');
      const actions = box('#ss-title-actions');
      const input = box('#ss-time-point-name');
      const timePoint = box('#ss-time-point');
      const frame = box('#ss-time-point-controls');
      const language = box('#ss-language .ss-select-trigger');
      const close = box('#ss-close');
      const root = box('#grz-session-stats'), barStyle = getComputedStyle(document.getElementById('ss-titlebar'));
      const minimumRow = parseFloat(getComputedStyle(document.querySelector('.ss-title-identity')).flexBasis) +
        actions.width + parseFloat(barStyle.paddingLeft) + parseFloat(barStyle.paddingRight);
      const expectedWrapped = wrapped === undefined ? root.width < minimumRow - 1 : wrapped;
      const pass = input.width > 50 && timePoint.right <= input.left &&
        timePoint.left >= frame.left && input.right <= frame.right &&
        Math.abs(input.top - timePoint.top) < 1 && language.right <= close.left &&
        (Math.abs(frame.top - language.top) < 1 ? input.right < language.left : language.top >= frame.bottom) &&
        (expectedWrapped ? actions.top >= title.bottom : actions.top < title.bottom) &&
        [title,actions,frame,language,close].every(item=>item.left>=root.left-1 && item.right<=root.right+1) &&
        [...document.querySelectorAll('.ss-timeline-field')].every(field => {
          const label = field.firstElementChild.getBoundingClientRect();
          const control = field.querySelector('.ss-select-trigger').getBoundingClientRect();
          return control.width > 0 && label.right < control.left &&
            control.right <= field.getBoundingClientRect().right + 1;
        });
      const serial=rect=>({left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom,width:rect.width,height:rect.height});
      return {pass,expectedWrapped,minimumRow,root:serial(root),title:serial(title),actions:serial(actions),
        input:serial(input),timePoint:serial(timePoint),frame:serial(frame),language:serial(language),close:serial(close),
        fields:[...document.querySelectorAll('.ss-timeline-field')].map(field=>({field:serial(field.getBoundingClientRect()),
          label:serial(field.firstElementChild.getBoundingClientRect()),control:serial(field.querySelector('.ss-select-trigger').getBoundingClientRect())}))};
    }, wrapped);
  }
  const controls200=await controlsFit();
  check('Title actions and both timeline selectors fit at 200 percent'+(controls200.pass ? '' : ': '+JSON.stringify(controls200)),controls200.pass);
  check('The time-point button and name share a visible frame',await page.locator('#ss-time-point-controls').evaluate(frame =>
    frame.firstElementChild.id === 'ss-time-point' &&
    parseFloat(getComputedStyle(frame).borderTopWidth) > 0 &&
    frame.contains(document.getElementById('ss-time-point-name'))));
  const name = page.locator('#ss-time-point-name');
  check('The time-point name starts with the current date and time',
    /^\d{2}\.\d{2}\.\d{4}, \d{2}:\d{2}$/.test(await name.inputValue()));
  await name.fill('Before Frontline <test>');
  await page.evaluate(() => __grzEvents['viewEnv.onDataChanged']());
  check('Refreshing battle data preserves an edited time-point name',
    await name.inputValue() === 'Before Frontline <test>');
  await name.press('Enter');
  check('Enter saves the exact custom time-point name', await page.evaluate(() =>
    __grzCommands.some(x => x.action === 'time_point' && x.name === 'Before Frontline <test>' &&
      x.account_key === 'fixture-account')));
  const timePoint = page.locator('#ss-time-point');
  const buttonShadow = await timePoint.evaluate(button => getComputedStyle(button).boxShadow);
  await timePoint.hover();
  await page.waitForFunction(shadow => getComputedStyle(document.getElementById('ss-time-point')).boxShadow !== shadow,buttonShadow);
  check('Time-point button gains depth on hover',
    await timePoint.evaluate(button => getComputedStyle(button).boxShadow) !== buttonShadow);
  await timePoint.click();
  await page.locator('#ss-timeline-from .ss-select-trigger').click();
  await page.locator('#ss-timeline-from [data-value="first"]').click();
  check('Creating and selecting a time point are account-scoped native actions', await page.evaluate(() =>
    __grzCommands.some(x => x.action === 'time_point' && x.account_key === 'fixture-account') &&
    __grzCommands.some(x => x.action === 'timeline_range' && x.account_key === 'fixture-account' &&
      x.from_point === 'first' && x.to_point === '')));
  await page.locator('#ss-group-battles').click();
  const details = page.locator('.ss-more-panel').first();
  async function ensureMoreOpen(context) {
    const button=page.locator('.ss-more-button').first();
    if(await button.getAttribute('aria-expanded')!=='true') await button.click();
    check('More is expanded and visible for '+context,
      await button.getAttribute('aria-expanded')==='true' && await details.isVisible());
  }
  await ensureMoreOpen('the initial reward fixture');
  const text = await details.textContent();
  check('More renders confirmed mission, points and bonus as plain text',
    text.includes('33 points earned') && text.includes('shield used') &&
    text.includes('First victory') && text.includes('×2') && text.includes('<b>Fixture stage</b>') &&
    text.includes('Operation Fossa') && text.includes('Completed with honors') &&
    text.includes('+43') &&
    await details.locator('b').count() === 0);
  const bonusRows=await details.locator('.ss-bonus-row').evaluateAll(rows=>rows.map(row=>({
    label:row.querySelector('.ss-bonus-label').textContent,
    values:[...row.querySelectorAll('.ss-bonus-number')].map(cell=>cell.textContent.replace(/\s/g,'')),
  })));
  check('Bonus amounts align beneath their currency and XP column headers',
    bonusRows[0].values.join('|')==='Credits|XP|FreeXP|CrewXP|Bonds' &&
    bonusRows.find(row=>row.label==='Event').values.join('|')==='+12345678|—|—|—|+43');
  check('Reserve and WoT Plus rewards share one row per source without losing or duplicating amounts',
    bonusRows.filter(row=>row.label==='Personal reserve').length===1 &&
    bonusRows.find(row=>row.label==='Personal reserve').values.join('|')==='+26943|+136|+28|+544|—' &&
    bonusRows.filter(row=>row.label==='WoT Plus').length===1 &&
    bonusRows.find(row=>row.label==='WoT Plus').values.join('|')==='+8083|+41|+2|+164|—');
  check('Premium and first-victory factors align with resource amounts without full-width factor rows',
    bonusRows.filter(row=>row.label==='Premium account').length===1 &&
    bonusRows.find(row=>row.label==='Premium account').values.join('|')==='×1.5|×1.5|—|—|—' &&
    bonusRows.find(row=>row.label==='First victory').values.join('|')==='—|×2|—|—|—' &&
    await details.locator('.ss-more-bonuses .ss-bonus-row').evaluateAll(rows=>rows.every(row=>
      row.querySelectorAll('[role="rowheader"],[role="columnheader"],[role="cell"]').length===6)) &&
    await details.locator('.ss-more-bonuses .ss-more-value').count()===0 &&
    await details.locator('.ss-more-factors').count()===0);
  check('The full-width point strip precedes separate bonus and mission columns',await details.evaluate(panel=>{
    const points=panel.querySelector('.ss-more-pass-block'),columns=panel.querySelector('.ss-more-columns'),
      bonus=panel.querySelector('.ss-more-bonus-block'),missions=panel.querySelector('.ss-more-mission-block');
    const tolerance=parseFloat(document.documentElement.style.fontSize);
    return points.parentNode===panel && columns.parentNode===panel && columns.firstElementChild===bonus &&
      bonus.parentNode===columns && missions.parentNode===columns &&
      Math.abs(points.getBoundingClientRect().width-panel.getBoundingClientRect().width)<=tolerance &&
      points.getBoundingClientRect().bottom<=columns.getBoundingClientRect().top+tolerance &&
      Array.from(missions.querySelectorAll('.ss-more-mission')).every(row=>{
        const box=row.getBoundingClientRect(),name=row.querySelector('.ss-more-mission-name').getBoundingClientRect(),
          status=row.querySelector('.ss-more-mission-status').getBoundingClientRect(),style=getComputedStyle(row);
        return box.height>0 && status.top>=name.bottom-tolerance && status.bottom<=box.bottom+tolerance &&
          ['Top','Right','Bottom','Left'].every(edge=>parseFloat(style['border'+edge+'Width'])>0);
      });
  }));
  check('More groups rewards and paired mission outcomes into compact tables',
    await details.locator('.ss-more-table[role="table"]').count() >= 3 &&
    await details.locator('.ss-more-mission-name').count() === 2 &&
    await details.locator('.ss-more-mission-status').count() === 2);
  check('More uses supported Gameface elements for every table row and cell',
    await details.locator('table,tbody,tr,th,td,section').count() === 0 &&
    await details.locator('[role="row"] [role="cell"]').count() >= 5);
  await page.locator('.ss-more-button').first().click();
  check('More closes in its own battle card', await details.isHidden());

  await page.evaluate(()=>{
    window.__moreStressSnapshot=JSON.parse(model.payload);
    const payload=JSON.parse(model.payload),battle=payload.scopes.timeline.battles[0];
    battle.name='Leox';battle.map='Cliff';
    battle.xp_bonus_applied=false;
    battle.stats.xp_base={count:1,min:456,avg:456,max:456,sum:456};battle.stats.wn8=1750;battle.stats.wn8_count=1;
    battle.stats.currencies.credits={income:74321,costs:87654,net:-13333,income_count:1,costs_count:1,net_count:1};
    battle.details.pass_points={credited:0,battle:0,missions:0,vehicle:0};
    battle.details.bonuses={wotPlusCredits:3456,wotPlusXP:64,wotPlusFreeXP:8,wotPlusCrewXP:96,
      appliedPremiumCreditsFactor100:150,appliedPremiumXPFactor100:150};
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  });
  await ensureMoreOpen('the ordinary zero-point fixture');
  const ordinaryRows=await details.locator('.ss-bonus-row').evaluateAll(rows=>rows.map(row=>({
    label:row.querySelector('.ss-bonus-label').textContent,
    values:Array.from(row.querySelectorAll('.ss-bonus-number')).map(cell=>cell.textContent.replace(/\s/g,'')),
  })));
  check('An ordinary 500px battle keeps zero points and paired premium factors in a compact matrix',
    ordinaryRows.length===3 && ordinaryRows[0].values.join('|')==='Credits|XP|FreeXP|CrewXP' &&
    ordinaryRows.find(row=>row.label==='WoT Plus').values.join('|')==='+3456|+64|+8|+96' &&
    ordinaryRows.filter(row=>row.label==='Premium account').length===1 &&
    ordinaryRows.find(row=>row.label==='Premium account').values.join('|')==='×1.5|×1.5|—|—' &&
    await details.locator('.ss-more-pass .ss-more-value').count()===1 &&
    await details.locator('.ss-more-pass').textContent()==='0 points earned' &&
    await details.locator('.ss-more-factors').count()===0);
  check('Zero points stay inline with the heading above bonus and mission columns',await details.evaluate(panel=>{
    const scale=parseFloat(document.documentElement.style.fontSize),card=panel.closest('.ss-group').getBoundingClientRect();
    const pass=panel.querySelector('.ss-more-pass-block'),bonus=panel.querySelector('.ss-more-bonus-block'),
      missions=panel.querySelector('.ss-more-mission-block');
    const point=pass.getBoundingClientRect(),columns=panel.querySelector('.ss-more-columns').getBoundingClientRect(),
      title=pass.querySelector('.ss-more-title').getBoundingClientRect(),table=pass.querySelector('.ss-more-pass').getBoundingClientRect(),
      bonusBox=bonus.getBoundingClientRect(),missionBox=missions.getBoundingClientRect();
    return Math.abs(card.width/scale-500)<=1 && Math.abs(point.width-panel.getBoundingClientRect().width)<=scale &&
      title.right<=table.left+scale && Math.min(title.bottom,table.bottom)>Math.max(title.top,table.top) &&
      point.bottom<=columns.top+scale &&
      ((Math.abs(bonusBox.top-missionBox.top)<=scale && bonusBox.right<=missionBox.left+scale) || missionBox.top>=bonusBox.bottom-scale) &&
      Array.from(missions.querySelectorAll('.ss-more-mission')).every(row=>row.getBoundingClientRect().height>0);
  }));
  await page.evaluate(()=>{
    const payload=JSON.parse(model.payload);payload.scopes.timeline.battles[0].details.bonuses.wotPlusXP=1234;
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  });
  await ensureMoreOpen('the four-digit XP fixture');
  const xpLayout=await details.evaluate(panel=>{
    const scale=parseFloat(document.documentElement.style.fontSize),block=panel.querySelector('.ss-more-bonus-block'),
      table=block.querySelector('.ss-more-bonuses'),columns=panel.querySelector('.ss-more-columns').getBoundingClientRect(),
      missions=panel.querySelector('.ss-more-mission-block').getBoundingClientRect(),box=block.getBoundingClientRect();
    const row=Array.from(table.querySelectorAll('.ss-bonus-row')).find(item=>item.querySelector('.ss-bonus-label').textContent==='WoT Plus'),
      cell=row.querySelector('.ss-bonus-column-1'),bounds=cell.getBoundingClientRect(),css=getComputedStyle(cell),range=document.createRange();
    range.selectNodeContents(cell);const text=range.getBoundingClientRect();
    const passed=block.classList.contains('ss-long-bonus-values') && table.classList.contains('ss-long-bonus-values') &&
      Math.abs(box.width-columns.width)<=scale && missions.top>=box.bottom-scale && cell.textContent==='+1\u00a0234' &&
      text.left>=bounds.left+parseFloat(css.paddingLeft)-scale && text.right<=bounds.right-parseFloat(css.paddingRight)+scale;
    return {passed,scale,display:getComputedStyle(panel).display,blockClass:block.className,tableClass:table.className,
      value:cell.textContent,block:{top:box.top,bottom:box.bottom,width:box.width},columnsWidth:columns.width,
      missionTop:missions.top,cell:{left:bounds.left,right:bounds.right,width:bounds.width},
      text:{left:text.left,right:text.right,width:text.width},padding:{left:css.paddingLeft,right:css.paddingRight}};
  });
  check('A four-digit XP bonus uses full-width fallback and preserves its full formatted value'+
    (xpLayout.passed ? '' : ' '+JSON.stringify(xpLayout)),xpLayout.passed);
  await page.evaluate(()=>{
    const payload=JSON.parse(model.payload);payload.scopes.timeline.battles[0].details.pass_points={battle:0};
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  });
  await ensureMoreOpen('the partial zero-point fixture');
  check('A confirmed zero component remains visible without inventing an unknown total',
    await details.locator('.ss-more-pass .ss-more-value').count()===1 &&
    await details.locator('.ss-more-pass .ss-more-label').textContent()==='Battle result:' &&
    await details.locator('.ss-more-pass .ss-more-amount').textContent().then(text=>text.trim()==='+0') &&
    await details.locator('.ss-more-pass .ss-more-total').count()===0);
  await page.evaluate(()=>{
    const payload=JSON.parse(model.payload);payload.scopes.timeline.battles[0].xp_bonus_applied=true;
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  });
  await ensureMoreOpen('the unknown applied-bonus fixture');
  check('An applied bonus with unknown amount remains a notice without inventing a multiplier',
    await details.locator('.ss-more-factors .ss-more-value').count()===1 &&
    await details.locator('.ss-more-factors').textContent()==='Post-battle XP bonus applied' &&
    await details.locator('.ss-bonus-factor').count()===2);
  await page.evaluate(()=>{model.payload=JSON.stringify(__moreStressSnapshot);__grzEvents['viewEnv.onDataChanged']();});

  const grip = await page.locator('#ss-resize-grip').boundingBox();
  check('4K viewport uses the resolved 200 percent game scale',
    await page.evaluate(() => __nativeSize[0] === 1400 && __nativeSize[1] === 1240));
  await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2);
  await page.mouse.down();
  await page.mouse.move(grip.x + grip.width / 2 + 160, grip.y + grip.height / 2 + 120, {steps:4});
  await page.mouse.up();
  await page.waitForFunction(() => __nativeSize[0] === 1560 && __nativeSize[1] === 1360);
  check('Resizing at 200 percent reports physical size and remembers logical size',
    await page.evaluate(() => __grzCommands.some(x => x.action === 'size_preference' &&
      x.width === '780' && x.height === '680')));
  await page.evaluate(() => __grzEvents['self.onScaleUpdated']());
  await page.waitForFunction(() => __nativeSize[0] === 780 && __nativeSize[1] === 680);
  check('A change to 100 percent keeps the same logical window size',
    await page.evaluate(() => document.documentElement.style.fontSize === '1px'));
  await page.setViewportSize({width:480, height:740});
  await page.evaluate(() => {
    const payload = JSON.parse(model.payload);
    payload.viewport = {width:480, height:740, scale:1};
    model.payload = JSON.stringify(payload);
    __grzEvents['viewEnv.onDataChanged']();
  });
  await page.waitForFunction(() => __nativeSize[0] === 460);
  const narrowControls=await controlsFit(true);
  check('Title actions wrap together and timeline selectors fit in a narrow window'+(narrowControls.pass ? '' : ': '+JSON.stringify(narrowControls)),narrowControls.pass);
  await page.close();

  for(const testCase of [{window:700,card:500,label:'500px battle card'},{window:320,label:'320px floating window'}]) {
    const narrowMore=await nativeHost(browser,{
      initialViewport:{width:1600,height:1100},viewport:{width:1600,height:1100,scale:1},
    });
    try {
      await narrowMore.evaluate(width=>{
        const payload=JSON.parse(model.payload);payload.window_size=[width,900];
        payload.localization={language:'en',messages:{}};
        const timeline=payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));
        timeline.from_point=timeline.to_point='';timeline.time_points=[];
        timeline.battles=[timeline.battles[0]];
        timeline.battles[0].name='IS-4';timeline.battles[0].xp_bonus_applied=false;
        timeline.battles[0].details={pass_points:{credited:25,battle:5,missions:20},missions:{
          'daily:fixture':{kind:'daily',name:'Synthetic daily mission',status:'completed',description:'Finish the objective.'},
          'weekly:fixture':{kind:'weekly',name:'Synthetic weekly mission',status:'progress',description:'Finish the objective.'},
          'personal:fixture':{kind:'personal',name:'Synthetic personal mission',status:'observed',description:'Finish the objective.'}},
          bonuses:{eventCredits:12345678,eventCrystal:43,wotPlusCredits:3456,wotPlusXP:64,wotPlusFreeXP:8,wotPlusCrewXP:96}};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },testCase.window);
      await narrowMore.locator('#ss-scope-manual').click();
      await narrowMore.locator('#ss-group-battles').click();
      await narrowMore.locator('.ss-more-button').first().click();
      const bonusAudit=await narrowMore.locator('.ss-more-bonuses').evaluate(table=>{
        const compact=text=>text.replace(/\s/g,'');
        const cells=[...table.querySelectorAll('.ss-bonus-number')],bad=[];
        for(const cell of cells) {
          const box=cell.getBoundingClientRect(),css=getComputedStyle(cell),range=document.createRange();
          range.selectNodeContents(cell);
          for(const text of range.getClientRects()) if(text.left<box.left+parseFloat(css.paddingLeft)-1 ||
            text.right>box.right-parseFloat(css.paddingRight)+1) bad.push(cell.textContent);
        }
        const event=[...table.querySelectorAll('.ss-bonus-row')].find(row=>row.querySelector('.ss-bonus-label').textContent==='Event');
        const bonus=table.closest('.ss-more-bonus-block').getBoundingClientRect(),
          missions=table.closest('.ss-more-panel').querySelector('.ss-more-mission-block').getBoundingClientRect();
        return {long:table.classList.contains('ss-long-bonus-values'),bad,
          panelWidth:document.getElementById('grz-session-stats').getBoundingClientRect().width,
          cardWidth:table.closest('.ss-group').getBoundingClientRect().width,
          paired:Math.abs(bonus.top-missions.top)<=1 && bonus.right<=missions.left+1,
          wrapped:missions.top>=bonus.bottom-1,
          headings:[...table.querySelectorAll('.ss-bonus-head .ss-bonus-number')].map(cell=>compact(cell.textContent)),
          event:[...event.querySelectorAll('.ss-bonus-number')].map(cell=>compact(cell.textContent))};
      });
      check('More preserves all five resource columns and a full eight-digit bonus in a '+testCase.label+
        (bonusAudit.bad.length ? ' '+JSON.stringify(bonusAudit.bad) : ''),
        bonusAudit.long && bonusAudit.bad.length===0 &&
        Math.abs(bonusAudit.panelWidth-testCase.window)<=1 && (!testCase.card || Math.abs(bonusAudit.cardWidth-testCase.card)<=1) &&
        bonusAudit.wrapped &&
        bonusAudit.headings.join('|')==='Credits|XP|FreeXP|CrewXP|Bonds' &&
        bonusAudit.event.join('|')==='+12345678|—|—|—|+43');
    } finally {await narrowMore.close();}
  }

  const wide = await nativeHost(browser, {
    initialViewport:{width:2400,height:1300},viewport:{width:2400,height:1300,scale:1},realTimers:true,
  });
  await wide.evaluate(() => {
    // Gameface can return zero/stale card heights until a later layout pass.
    // Keep that failure active across each initial render and read the real
    // rectangles only from this test, after the browser performs native flow.
    window.__realCardRect = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = function () {
      const box=__realCardRect.call(this);
      if(this.id==='ss-groups') return {
        x:box.x,y:box.y,left:box.left,right:box.left+600,top:box.top,bottom:box.bottom,width:600,height:box.height,
      };
      return this.classList.contains('ss-group') ?
        {x:box.x,y:box.y,left:box.left,right:box.right,top:box.top,bottom:box.top,width:box.width,height:0} : box;
    };
    const payload=JSON.parse(model.payload);
    payload.window_size=[2200,1160];
    // Keep this pre-existing base-width/stale-measurement matrix independent
    // of the separate two-column wide-preset threshold regression.
    payload.appearance={wide_card_widths:{vehicles:560,maps:560,tiers:520,battles:500}};
    const timeline=payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));
    timeline.from_point=timeline.to_point='';timeline.time_points=[];
    for (const group of ['vehicles','maps','tiers','battles']) {
      const source=timeline[group];
      timeline[group]=Array.from({length:6},(_,index) => {
        const item=JSON.parse(JSON.stringify(source[index % source.length]));
        item.id='layout-'+group+'-'+index;
        item.name='Layout fixture '+index;
        if (group==='battles') {
          item.details={pass_points:{credited:33,battle:8,missions:10,vehicle:15},missions:{},bonuses:{eventCrystal:43}};
          if (index===0) for(let i=0;i<8;i++) item.details.missions['fixture:'+i]={
            kind:'daily',name:'Fixture mission '+i,status:'completed',description:'A compact objective description.',
          };
        }
        return item;
      });
      if(timeline.pagination && timeline.pagination[group]) {
        timeline.pagination[group]={page:0,page_size:40,total:6,pages:1};
      }
    }
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  });
  await wide.locator('#ss-scope-manual').click();
  async function readLayout() {
    return wide.locator('#ss-groups').evaluate(groups => {
      const cards=[...groups.querySelectorAll('.ss-group')].sort((a,b) =>
        Number(a.getAttribute('data-list-index'))-Number(b.getAttribute('data-list-index'))).map(card => {
        const box=__realCardRect.call(card);
        return {left:box.left,right:box.right,top:box.top,bottom:box.bottom,width:box.width,
          position:getComputedStyle(card).position,index:Number(card.getAttribute('data-list-index'))};
      });
      const columns=groups.querySelector('.ss-card-columns');
      const group=__realCardRect.call(groups);
      return {cards,two:groups.classList.contains('ss-two-columns'),
        group:{left:group.left,right:group.right,width:group.width},
        axis:columns && {image:getComputedStyle(columns,':before').backgroundImage,
          repeat:getComputedStyle(columns,':before').backgroundRepeat,
          size:getComputedStyle(columns,':before').backgroundSize,
          width:getComputedStyle(columns,':before').width,height:getComputedStyle(columns,':before').height},
        arrow:columns && {content:getComputedStyle(columns,':after').content,
          width:getComputedStyle(columns,':after').width,height:getComputedStyle(columns,':after').height},
        branches:[...groups.querySelectorAll('.ss-group')].every(card => {
          const style=getComputedStyle(card,':before');
          return style.backgroundImage.includes('linear-gradient') && style.backgroundRepeat==='repeat-x' &&
            parseFloat(style.height)>0 && parseFloat(style.width)>0;
        })};
    });
  }
  async function setAvailableWidth(width) {
    await wide.setViewportSize({width,height:1300});
    await wide.evaluate(width => {
      const payload=JSON.parse(model.payload);payload.viewport.width=width;
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    },width);
    await wide.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  }
  const widths={vehicles:560,maps:560,tiers:520,battles:500};
  for(const group of ['vehicles','maps','tiers','battles']) {
    const expectedWidth=widths[group];
    await wide.locator('#ss-group-'+group).click();
    await wide.waitForFunction(() => document.getElementById('ss-groups').classList.contains('ss-two-columns'));
    let layout=await readLayout();
    check('Stale narrow groups and zero card heights cannot overlap fixed-width '+group+' cards',
      layout.cards.length===6 && layout.cards.every((card,index) =>
        Math.abs(card.width-expectedWidth)<=1 && card.position!=='absolute' &&
        card.left>=layout.group.left-1 && card.right<=layout.group.right+1 &&
        (index<2 || card.top>=layout.cards[index-2].bottom+15)) &&
      Math.abs(layout.cards[1].left-layout.cards[0].right-64)<=2);
    check('The '+group+' grid keeps canonical alternating card order',
      layout.cards.every((card,index) => card.index===index &&
        Math.abs(card.left-layout.cards[index%2].left)<1));
    check('Wide '+group+' results share a visible tiled axis, arrow, stagger and card connections',
      layout.axis.image.includes('linear-gradient') && layout.axis.repeat==='repeat-y' &&
      parseFloat(layout.axis.width)>0 && parseFloat(layout.axis.height)>0 &&
      layout.arrow.content!=='none' && parseFloat(layout.arrow.width)>0 && parseFloat(layout.arrow.height)>0 &&
      layout.branches && layout.cards[1].top>layout.cards[0].top+1);
    if(group==='battles') {
      await wide.locator('[data-list-index="0"] .ss-more-button').click();
      await wide.evaluate(()=>new Promise(resolve=>{
        let remaining=10;function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
      }));
      const expanded=await readLayout();
      check('More uses native column flow while card height readings remain stale',
        expanded.cards.every((card,index)=>card.position!=='absolute' && (!index || card.top>=expanded.cards[index-1].top-1)) &&
        expanded.cards.every((card,index)=>expanded.cards.slice(index+1).every(other=>
          Math.min(card.right,other.right)-Math.max(card.left,other.left)<=1 ||
          Math.min(card.bottom,other.bottom)-Math.max(card.top,other.top)<=1)));
    }
    await setAvailableWidth(2*expectedWidth+64+20);
    layout=await readLayout();
    check('The '+group+' grid collapses below two complete cards without stretching them',
      !layout.two && layout.group.width<2*expectedWidth+64 && layout.cards.every((card,index) =>
        Math.abs(card.width-expectedWidth)<=1 && Math.abs(card.left-layout.cards[0].left)<1 &&
        (!index || card.top>=layout.cards[index-1].bottom+15)));
    await setAvailableWidth(2400);
  }
  const configuredWidth=widths.battles+80;
  await setAvailableWidth(2*widths.battles+64+74);
  check('The default battle width still permits two columns before a live width update',(await readLayout()).two);
  await wide.evaluate(configuredWidth=>{
    const payload=JSON.parse(model.payload);
    payload.appearance={card_widths:{battles:configuredWidth}};
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  },configuredWidth);
  await wide.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const configured=await readLayout();
  check('A card-width configuration change updates fixed widths and the two-column threshold in the open panel',
    !configured.two && configured.cards.every(card=>Math.abs(card.width-configuredWidth)<=1) &&
    configured.group.width>=2*widths.battles+64 && configured.group.width<2*configuredWidth+64);
  check('All eight window corners and edges have reachable resize grips',
    await wide.locator('.ss-resize-grip').count()===8);
  await wide.close();
  await require('./ui-timeline-expansion.cjs')({browser,nativeHost,check});

  for(const edge of ['nw','ne','sw','se','n','e','s','w']) {
    const resize=await nativeHost(browser, {
      initialViewport:{width:1600,height:1100},viewport:{width:1600,height:1100,scale:1},
    });
    const horizontal=/[ew]/.test(edge),vertical=/[ns]/.test(edge);
    const x=edge.includes('w') ? 6 : edge.includes('e') ? 694 : 350;
    const y=edge.includes('n') ? 6 : edge.includes('s') ? 614 : 310;
    const selector=edge==='se' ? '#ss-resize-grip' : '[data-corner="'+edge+'"]';
    await resize.evaluate(() => {window.__resizeClock=100000;Date.now=()=>__resizeClock;});
    await resize.locator(selector).dispatchEvent('pointerdown',{button:0,pointerId:77,clientX:x,clientY:y});
    await resize.evaluate(({edge,x,y}) => {
      window.__resizeStart={x,y};
      document.dispatchEvent(new PointerEvent('pointermove',{
        pointerId:77,buttons:1,clientX:x+(edge.includes('w') ? -240 : 240),
        clientY:y+(edge.includes('n') ? -160 : 160),bubbles:true,
      }));
    },{edge,x,y});
    const firstWidth=horizontal ? 940 : 700,firstHeight=vertical ? 780 : 620;
    await resize.waitForFunction(({width,height}) => __nativeSize[0]===width && __nativeSize[1]===height,
      {width:firstWidth,height:firstHeight});
    const beforeBurst=await resize.evaluate(edge => {
      const before=__grzHelperCalls.resize;
      for(const offset of [20,80]) {
        __resizeClock=100000+offset;
        document.dispatchEvent(new PointerEvent('pointermove',{
          pointerId:77,buttons:1,clientX:__resizeStart.x+(edge.includes('w') ? -(240+offset) : 240+offset),
          clientY:__resizeStart.y+(edge.includes('n') ? -(160+offset) : 160+offset),bubbles:true,
        }));
      }
      return before;
    },edge);
    await resize.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    check('Rapid '+edge+' movement coalesces expensive sizing within its 100ms interval',
      await resize.evaluate(() => __grzHelperCalls.resize)===beforeBurst);
    await resize.evaluate(edge => document.dispatchEvent(new PointerEvent('pointerup',{
      pointerId:77,button:0,clientX:__resizeStart.x+(edge.includes('w') ? -320 : 320),
      clientY:__resizeStart.y+(edge.includes('n') ? -240 : 240),bubbles:true,
    })),edge);
    const finalWidth=horizontal ? 1020 : 700,finalHeight=vertical ? 860 : 620;
    await resize.waitForFunction(({width,height}) => __nativeSize[0]===width && __nativeSize[1]===height,
      {width:finalWidth,height:finalHeight});
    check('Releasing '+edge+' flushes the latest movement and preserves the unused edge dimension',
      await resize.evaluate(({edge,width,height}) =>
        __grzCommands.some(command => command.action==='resize_begin' && command.corner===edge) &&
        __grzCommands.some(command => command.action==='resize_end') &&
        __grzCommands.some(command => command.action==='size_preference' && command.width===String(width) && command.height===String(height)),
      {edge,width:finalWidth,height:finalHeight}));
    await resize.evaluate(() => document.dispatchEvent(new PointerEvent('pointermove',{
      pointerId:77,buttons:0,clientX:1200,clientY:1000,bubbles:true,
    })));
    check('Movement after releasing '+edge+' cannot continue the gesture',
      await resize.evaluate(({width,height}) => __nativeSize[0]===width && __nativeSize[1]===height,
        {width:finalWidth,height:finalHeight}));
    await resize.close();
  }

  for(const edge of ['e','w','n','s']) {
    const small=await nativeHost(browser, {
      initialViewport:{width:1600,height:1100},viewport:{width:1600,height:1100,scale:1},
    });
    const horizontal=/[ew]/.test(edge),native=edge==='w' || edge==='s';
    const width=horizontal ? 700 : 430,height=horizontal ? 330 : 620;
    await small.evaluate(({width,height}) => {
      const payload=JSON.parse(model.payload);payload.window_size=[width,height];
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    },{width,height});
    await small.waitForFunction(({width,height}) => __nativeSize[0]===width && __nativeSize[1]===height,{width,height});
    const x=edge==='w' ? 6 : edge==='e' ? width-6 : width/2;
    const y=edge==='n' ? 6 : edge==='s' ? height-6 : height/2;
    await small.locator('[data-corner="'+edge+'"]').dispatchEvent('pointerdown',{
      button:0,pointerId:88,clientX:x,clientY:y,
    });
    if(native) {
      await small.evaluate(({width,height,horizontal}) => {
        const token=__grzCommands.filter(command=>command.action==='resize_begin').pop().token;
        GRZSessionStats.update({resize_gesture:{token,width:width+(horizontal ? 80 : 0),height:height+(horizontal ? 0 : 80),active:true}});
        GRZSessionStats.update({resize_gesture:{token,width:width+(horizontal ? 100 : 0),height:height+(horizontal ? 0 : 100),active:false}});
      },{width,height,horizontal});
    } else {
      await small.evaluate(({edge,x,y}) => {
        document.dispatchEvent(new PointerEvent('pointermove',{
          pointerId:88,buttons:1,clientX:x+(edge==='w' ? -80 : 80),clientY:y+(edge==='n' ? -80 : 80),bubbles:true,
        }));
        document.dispatchEvent(new PointerEvent('pointerup',{
          pointerId:88,button:0,clientX:x+(edge==='w' ? -100 : 100),clientY:y+(edge==='n' ? -100 : 100),bubbles:true,
        }));
      },{edge,x,y});
    }
    const finalWidth=width+(horizontal ? 100 : 0),finalHeight=height+(horizontal ? 0 : 100);
    await small.waitForFunction(({width,height}) => __nativeSize[0]===width && __nativeSize[1]===height,
      {width:finalWidth,height:finalHeight});
    check('The '+edge+' '+(native ? 'native' : 'fallback')+' gesture preserves its saved subminimum inactive dimension',
      await small.evaluate(({width,height}) => __grzCommands.some(command=>command.action==='size_preference' &&
        command.width===String(width) && command.height===String(height)),{width:finalWidth,height:finalHeight}));
    await small.close();
  }

  const captured = await nativeHost(browser, {
    initialViewport:{width:1600,height:1100},viewport:{width:1600,height:1100,scale:1},
  });
  await captured.locator('#ss-resize-grip').dispatchEvent('pointerdown',{
    button:0,pointerId:91,clientX:694,clientY:614,
  });
  await captured.evaluate(() => {
    window.__gestureToken = __grzCommands.filter(command => command.action === 'resize_begin').pop().token;
    GRZSessionStats.update({resize_gesture:{token:__gestureToken,width:860,height:700,active:true}});
  });
  await captured.waitForFunction(() => __nativeSize[0] === 860 && __nativeSize[1] === 700);
  await captured.evaluate(() => {
    document.dispatchEvent(new PointerEvent('pointercancel',{pointerId:91,bubbles:true}));
    window.dispatchEvent(new Event('blur'));
    GRZSessionStats.update({resize_gesture:{token:__gestureToken,width:940,height:780,active:true}});
  });
  await captured.waitForFunction(() => __nativeSize[0] === 940 && __nativeSize[1] === 780);
  check('Game-level captured gestures continue after the pointer leaves the document',
    await captured.evaluate(() => !__grzCommands.some(command => command.action === 'resize_end')));
  await captured.evaluate(() => {
    const original = model.onAction;
    model.onAction = function (command) {
      original.call(this,command);
      if (command.action === 'resize_end') {
        // Final cursor movement arrives during release, after the last poll.
        GRZSessionStats.update({resize_gesture:{token:__gestureToken,width:1010,height:850,active:false}});
      }
    };
    document.dispatchEvent(new PointerEvent('pointerup',{pointerId:91,button:0,bubbles:true}));
  });
  await captured.waitForFunction(() => __nativeSize[0] === 1010 && __nativeSize[1] === 850);
  check('Releasing a native gesture saves the final game sample rather than the previous poll',
    await captured.evaluate(() => __grzCommands.some(command => command.action === 'size_preference' &&
      command.width === '1010' && command.height === '850') && !__grzCommands.some(command =>
        command.action === 'size_preference' && command.width === '940' && command.height === '780')));
  await captured.evaluate(() => {
    GRZSessionStats.update({resize_gesture:{token:__gestureToken,width:1200,height:1000,active:true}});
    return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  check('A released native gesture ignores delayed snapshots with its previous token',
    await captured.evaluate(() => __nativeSize[0] === 1010 && __nativeSize[1] === 850 &&
      __grzCommands.some(command => command.action === 'size_preference' && command.width === '1010' && command.height === '850')));
  await captured.close();
};
