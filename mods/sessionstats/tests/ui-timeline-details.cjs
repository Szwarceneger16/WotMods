module.exports = async function ({browser, nativeHost, check}) {
  const page = await nativeHost(browser, {
    initialViewport: {width:3840, height:2160},
    viewport: {width:3840, height:2160, scale:2}, changedScale:1,
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
      active_crucible:'challenge:8:2', bonuses:{dailyXPFactor10:20, eventCrystal:43},
    };
    model.payload = JSON.stringify(payload);
    __grzEvents['viewEnv.onDataChanged']();
  });
  await page.locator('#ss-scope-manual').click();
  check('Timeline defaults to all history and replaces manual reset', await page.evaluate(() =>
    document.querySelector('#ss-timeline-from .ss-select-trigger').textContent === 'Beginning of history' &&
    document.querySelector('#ss-timeline-to .ss-select-trigger').textContent === 'Now' &&
    document.querySelector('#ss-reset').style.display === 'none'));
  async function controlsFit(wrapped) {
    return page.evaluate(wrapped => {
      const box = selector => document.querySelector(selector).getBoundingClientRect();
      const title = box('.ss-title-identity');
      const actions = box('#ss-title-actions');
      const input = box('#ss-time-point-name');
      const timePoint = box('#ss-time-point');
      const language = box('#ss-language .ss-select-trigger');
      const close = box('#ss-close');
      return input.width > 50 && input.right < timePoint.left &&
        Math.abs(input.top - timePoint.top) < 1 && language.right <= close.left &&
        (Math.abs(timePoint.top - language.top) < 1 ? timePoint.right < language.left : language.top >= timePoint.bottom) &&
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
    text.includes('Mission or event reward: +43 bonds') &&
    await details.locator('b').count() === 0);
  check('More groups rewards and paired mission outcomes into compact tables',
    await details.locator('.ss-more-table').count() >= 3 &&
    await details.locator('.ss-more-mission-name').count() === 2 &&
    await details.locator('.ss-more-mission-status').count() === 2);
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
    initialViewport:{width:1600,height:1100}, viewport:{width:1600,height:1100,scale:1},
  });
  await wide.evaluate(() => {
    const payload = JSON.parse(model.payload);
    payload.window_size = [1460, 980];
    payload.scopes.timeline = JSON.parse(JSON.stringify(payload.scopes.manual));
    payload.scopes.timeline.from_point = payload.scopes.timeline.to_point = '';
    payload.scopes.timeline.time_points = [];
    payload.scopes.timeline.battles.forEach((battle, index) => {
      battle.details = {pass_points:{credited:33,battle:8,missions:10,vehicle:15}, missions:{}, bonuses:{eventCrystal:43}};
      if (index === 0) {
        for (let i=0; i<8; i++) battle.details.missions['fixture:'+i] = {
          kind:'daily',name:'Fixture mission '+i,status:'completed',description:'A compact objective description.'
        };
      }
    });
    model.payload = JSON.stringify(payload);
    __grzEvents['viewEnv.onDataChanged']();
  });
  await wide.locator('#ss-scope-manual').click();
  await wide.locator('#ss-group-battles').click();
  await wide.waitForFunction(() => document.getElementById('ss-groups').classList.contains('ss-battle-stream'));
  const layout = await wide.locator('#ss-groups').evaluate(groups => {
    const cards = [...groups.querySelectorAll('.ss-battle')].map(card => {
      const box = card.getBoundingClientRect();
      return {left:box.left,right:box.right,top:box.top,bottom:box.bottom};
    });
    const group = groups.getBoundingClientRect();
    return {cards,group:{left:group.left,right:group.right},
      line:getComputedStyle(groups,':before').borderLeftStyle,
      arrow:getComputedStyle(groups,':after').content,
      branches:[...groups.querySelectorAll('.ss-battle')].every(card =>
        getComputedStyle(card,':before').borderTopStyle === 'dashed')};
  });
  check('Wide battle history alternates between two columns with a fixed central gutter',
    layout.cards.length >= 4 && layout.cards.every((card,index) =>
      card.left >= layout.group.left - 1 && card.right <= layout.group.right + 1 &&
      (index % 2 ? card.left > layout.cards[0].right : Math.abs(card.left-layout.cards[0].left) < 1)) &&
    Math.abs(layout.cards[1].left-layout.cards[0].right-64) <= 2);
  check('Wide history has a dashed central axis, arrow and dashed card connections',
    layout.line === 'dashed' && layout.arrow !== 'none' && layout.branches);
  await wide.locator('.ss-more-button').first().click();
  await wide.waitForFunction(() => {
    const cards = document.querySelectorAll('#ss-groups .ss-battle');
    return cards[2].getBoundingClientRect().top >= cards[0].getBoundingClientRect().bottom;
  });
  const expanded = await wide.locator('#ss-groups .ss-battle').evaluateAll(cards =>
    cards.slice(0,4).map(card => {const box=card.getBoundingClientRect();return {top:box.top,bottom:box.bottom};}));
  check('Expanding More moves only later cards in its own column without overlaps',
    expanded[2].top >= expanded[0].bottom + 12 &&
    Math.abs(expanded[1].top-layout.cards[1].top) < 1 &&
    Math.abs(expanded[3].top-layout.cards[3].top) < 1);
  check('All four window corners have reachable resize grips',
    await wide.locator('.ss-resize-grip').count() === 4);
  await wide.close();

  for (const corner of ['nw','ne','sw','se']) {
    const resize = await nativeHost(browser, {
      initialViewport:{width:1600,height:1100},viewport:{width:1600,height:1100,scale:1},
    });
    const selector = corner === 'se' ? '#ss-resize-grip' : '[data-corner="'+corner+'"]';
    await resize.locator(selector).dispatchEvent('pointerdown',{
      button:0,pointerId:77,clientX:corner.includes('w') ? 6 : 694,
      clientY:corner.includes('n') ? 6 : 614,
    });
    await resize.evaluate(corner => {
      window.__resizeStart = {x:corner.includes('w') ? 6 : 694,y:corner.includes('n') ? 6 : 614};
      document.dispatchEvent(new PointerEvent('pointermove',{
        pointerId:77,buttons:1,clientX:__resizeStart.x+(corner.includes('w') ? -240 : 240),
        clientY:__resizeStart.y+(corner.includes('n') ? -160 : 160),bubbles:true,
      }));
    },corner);
    await resize.waitForFunction(() => __nativeSize[0] === 940 && __nativeSize[1] === 780);
    await resize.evaluate(corner => document.dispatchEvent(new PointerEvent('pointermove',{
      pointerId:77,buttons:1,clientX:__resizeStart.x+(corner.includes('w') ? -310 : 310),
      clientY:__resizeStart.y+(corner.includes('n') ? -230 : 230),bubbles:true,
    })),corner);
    await resize.waitForFunction(() => __nativeSize[0] === 1010 && __nativeSize[1] === 850);
    check('Fast pointer movement outside the panel keeps resizing from '+corner, await resize.evaluate(corner =>
      __grzCommands.some(command => command.action === 'resize_begin' && command.corner === corner),corner));
    await resize.evaluate(() => document.dispatchEvent(new PointerEvent('pointerup',{pointerId:77,button:0,bubbles:true})));
    await resize.evaluate(() => {
      document.dispatchEvent(new PointerEvent('pointermove',{pointerId:77,buttons:0,clientX:1200,clientY:1000,bubbles:true}));
    });
    check('Releasing the pointer ends the '+corner+' gesture and saves its final dimensions',
      await resize.evaluate(() => __nativeSize[0] === 1010 && __nativeSize[1] === 850 &&
        __grzCommands.some(command => command.action === 'resize_end') &&
        __grzCommands.some(command => command.action === 'size_preference' && command.width === '1010' && command.height === '850')));
    await resize.close();
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
