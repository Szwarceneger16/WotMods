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
      active_crucible:'challenge:8:2', bonuses:{dailyXPFactor10:20,eventCrystal:43,eventCredits:50000,
        boosterCredits:26943,boosterXP:136,boosterFreeXP:28,boosterTMenXP:544,
        wotPlusCredits:8083,wotPlusXP:41,wotPlusFreeXP:2,wotPlusCrewXP:164},
    };
    model.payload = JSON.stringify(payload);
    __grzEvents['viewEnv.onDataChanged']();
  });
  await page.locator('#ss-scope-manual').click();
  check('Timeline defaults to all history and replaces manual reset', await page.evaluate(() =>
    document.querySelector('#ss-timeline-from .ss-select-trigger').textContent === 'Beginning of history' &&
    document.querySelector('#ss-timeline-to .ss-select-trigger').textContent === 'Now' &&
    document.querySelector('#ss-reset').style.display === 'none'));
  await page.evaluate(() => { window.__timelineReadySnapshot = JSON.parse(model.payload); });
  for (const scopedState of ['loading', 'error']) {
    await page.evaluate(scopedState => {
      const payload = JSON.parse(JSON.stringify(__timelineReadySnapshot));
      payload.loading = false; payload.load_error = '';
      const timeline = payload.scopes.timeline;
      timeline.loading = scopedState === 'loading';
      timeline.load_error = scopedState === 'error' ? 'Synthetic selected range failure' : '';
      timeline.from_point = scopedState === 'error' ? 'first' : '';
      window.__timelineRangeCount = __grzCommands.filter(command => command.action === 'timeline_range').length;
      model.payload = JSON.stringify(payload); __grzEvents['viewEnv.onDataChanged']();
    }, scopedState);
    check('Selected range ' + scopedState + ' keeps both timeline bounds available',
      await page.locator('#ss-timeline-from .ss-select-trigger').isVisible() &&
      await page.locator('#ss-timeline-to .ss-select-trigger').isVisible() &&
      await page.locator('#ss-timeline-from .ss-select-trigger').isEnabled() &&
      await page.locator('#ss-timeline-to .ss-select-trigger').isEnabled());
    check('Selected range ' + scopedState + ' hides incomplete totals and battle rows',
      await page.locator('#ss-summary .ss-kpi-value').count() === 0 &&
      await page.locator('#ss-groups .ss-group').count() === 0 &&
      await page.locator('#ss-page-label').textContent() === '' &&
      await page.locator('#ss-status').textContent() === (scopedState === 'error' ?
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
      return input.width > 50 && timePoint.right <= input.left &&
        timePoint.left >= frame.left && input.right <= frame.right &&
        Math.abs(input.top - timePoint.top) < 1 && language.right <= close.left &&
        (Math.abs(timePoint.top - language.top) < 1 ? input.right < language.left : language.top >= timePoint.bottom) &&
        (wrapped ? actions.top >= title.bottom : actions.top < title.bottom) &&
        [...document.querySelectorAll('.ss-timeline-field')].every(field => {
          const label = field.firstElementChild.getBoundingClientRect();
          const control = field.querySelector('.ss-select-trigger').getBoundingClientRect();
          return control.width > 0 && label.right < control.left &&
            control.right <= field.getBoundingClientRect().right + 1;
        });
    }, wrapped);
  }
  check('Title actions and both timeline selectors fit at 200 percent', await controlsFit(false));
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
  await page.locator('.ss-more-button').first().click();
  const details = page.locator('.ss-more-panel').first();
  const text = await details.textContent();
  check('More renders confirmed mission, points and bonus as plain text',
    text.includes('33 points earned') && text.includes('shield used') &&
    text.includes('First victory: ×2 XP') && text.includes('<b>Fixture stage</b>') &&
    text.includes('Operation Fossa') && text.includes('Completed with honors') &&
    text.includes('+43') &&
    await details.locator('b').count() === 0);
  const bonusRows=await details.locator('.ss-bonus-row').evaluateAll(rows=>rows.map(row=>({
    label:row.querySelector('.ss-bonus-label').textContent,
    values:[...row.querySelectorAll('.ss-bonus-number')].map(cell=>cell.textContent.replace(/\s/g,'')),
  })));
  check('Bonus amounts align beneath their currency and XP column headers',
    bonusRows[0].values.join('|')==='Credits|XP|FreeXP|CrewXP|Bonds' &&
    bonusRows.find(row=>row.label==='Event').values.join('|')==='+50000|—|—|—|+43');
  check('Reserve and WoT Plus rewards share one row per source without losing or duplicating amounts',
    bonusRows.filter(row=>row.label==='Personal reserve').length===1 &&
    bonusRows.find(row=>row.label==='Personal reserve').values.join('|')==='+26943|+136|+28|+544|—' &&
    bonusRows.filter(row=>row.label==='WoT Plus').length===1 &&
    bonusRows.find(row=>row.label==='WoT Plus').values.join('|')==='+8083|+41|+2|+164|—');
  check('Multipliers keep a separate two-column table from the six-column resource matrix',
    await details.locator('.ss-more-bonuses .ss-bonus-row').evaluateAll(rows=>rows.every(row=>row.children.length===6)) &&
    await details.locator('.ss-more-bonuses .ss-more-value').count()===0 &&
    await details.locator('.ss-more-factors[role="table"] .ss-more-value').count()===1 &&
    await details.locator('.ss-more-factors .ss-more-value').evaluateAll(rows=>rows.every(row=>row.children.length===2)));
  check('More groups rewards and paired mission outcomes into compact tables',
    await details.locator('.ss-more-table[role="table"]').count() >= 3 &&
    await details.locator('.ss-more-mission-name').count() === 2 &&
    await details.locator('.ss-more-mission-status').count() === 2);
  check('More uses supported Gameface elements for every table row and cell',
    await details.locator('table,tbody,tr,th,td,section').count() === 0 &&
    await details.locator('[role="row"] [role="cell"]').count() >= 5);
  await page.locator('.ss-more-button').first().click();
  check('More closes in its own battle card', await details.isHidden());

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
  check('Title actions wrap together and timeline selectors fit in a narrow window', await controlsFit(true));
  await page.close();

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
  const widths={vehicles:600,maps:560,tiers:520,battles:620};
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
      const expanded=await readLayout();
      check('More uses native column flow while card height readings remain stale',
        expanded.cards[2].top>=expanded.cards[0].bottom+15 &&
        Math.abs(expanded.cards[1].top-layout.cards[1].top)<1 &&
        Math.abs(expanded.cards[3].top-layout.cards[3].top)<1);
    }
    await setAvailableWidth(1000);
    layout=await readLayout();
    check('The '+group+' grid collapses below two complete cards without stretching them',
      !layout.two && layout.group.width<2*expectedWidth+64 && layout.cards.every((card,index) =>
        Math.abs(card.width-expectedWidth)<=1 && Math.abs(card.left-layout.cards[0].left)<1 &&
        (!index || card.top>=layout.cards[index-1].bottom+15)));
    await setAvailableWidth(2400);
  }
  await setAvailableWidth(1200);
  await wide.evaluate(()=>{
    const payload=JSON.parse(model.payload);
    payload.appearance={card_widths:{battles:540}};
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  });
  await wide.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const configured=await readLayout();
  check('A card-width configuration change updates fixed widths and the two-column threshold in the open panel',
    configured.two && configured.cards.every(card=>Math.abs(card.width-540)<=1) &&
    configured.group.width>=2*540+64 && configured.group.width<2*620+64);
  check('All eight window corners and edges have reachable resize grips',
    await wide.locator('.ss-resize-grip').count()===8);
  await wide.close();

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
