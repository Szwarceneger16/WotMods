/* Native input-adapter contracts; actual garage/cursor rendering needs in-game QA. */
module.exports = async function ({browser, nativeHost, check}) {
  async function mirroredHitBoxes(page) {
    return page.locator('#grz-session-stats').evaluate(panel => {
      const scale = parseFloat(getComputedStyle(document.documentElement).fontSize);
      const frame = panel.getBoundingClientRect(), boxes = {};
      for (const grip of panel.querySelectorAll('.ss-resize-grip')) {
        const box = grip.getBoundingClientRect();
        boxes[grip.getAttribute('data-corner')] = box;
        if (getComputedStyle(grip).transform !== 'none' || !box.width || !box.height ||
            box.left < frame.left || box.right > frame.right ||
            box.top < frame.top || box.bottom > frame.bottom) return false;
      }
      const equal = (left, right) => Math.abs(left - right) < 0.1;
      if (!equal(boxes.w.width, 6 * scale) || !equal(boxes.e.width, boxes.w.width) ||
          !equal(boxes.n.height, 6 * scale) || !equal(boxes.s.height, boxes.n.height) ||
          !equal(boxes.w.left - frame.left, frame.right - boxes.e.right) ||
          !equal(boxes.n.top - frame.top, frame.bottom - boxes.s.bottom)) return false;
      for (const [left, right] of [['nw','ne'], ['sw','se']]) {
        if (!equal(boxes[left].width, 16 * scale) || !equal(boxes[left].width, boxes[right].width) ||
            !equal(boxes[left].height, boxes[right].height) || !equal(boxes[left].top, boxes[right].top) ||
            !equal(boxes[left].left - frame.left, frame.right - boxes[right].right)) return false;
      }
      for (const [edge, box] of Object.entries(boxes)) {
        const hit = document.elementFromPoint((box.left + box.right) / 2, (box.top + box.bottom) / 2);
        if (!hit || hit.getAttribute('data-corner') !== edge) return false;
      }
      const outside = [[frame.left - scale, frame.top + frame.height / 2],
        [frame.right + scale, frame.top + frame.height / 2],
        [frame.left + frame.width / 2, frame.top - scale],
        [frame.left + frame.width / 2, frame.bottom + scale]];
      return outside.every(([x, y]) => {
        const hit = document.elementFromPoint(x, y);
        return !hit || !hit.classList.contains('ss-resize-grip');
      });
    });
  }
  for (const placeholder of [0, 1]) {
  const zeroMeasurements = await nativeHost({newPage:async options => {
    const masked = await browser.newPage(options);
    await masked.addInitScript(placeholder => {
      const original = HTMLElement.prototype.getBoundingClientRect;
      window.__restoreResizeRootRect = () => { HTMLElement.prototype.getBoundingClientRect = original; };
      HTMLElement.prototype.getBoundingClientRect = function () {
        if (this.id === 'grz-session-stats') {
          return {x:0,y:0,left:0,top:0,right:placeholder,bottom:placeholder,width:placeholder,height:placeholder};
        }
        return original.call(this);
      };
    }, placeholder);
    return masked;
  }}, {initialViewport:{width:1600,height:1100},viewport:{width:1600,height:1100,scale:1}});
  await zeroMeasurements.evaluate(() => {
    if (JSON.parse(model.payload).window_size) throw new Error('Fresh-open regression requires no saved size');
    const sizes = __grzCommands.filter(command => command.action === 'resize');
    if (!sizes.length || sizes.some(command => Number(command.width) < 700 || Number(command.height) < 730)) {
      throw new Error('An empty first layout shrank the native surface below its default size');
    }
    __restoreResizeRootRect();
  });
  check('Fresh-open resize grips stay mirrored and usable after '+placeholder+'px panel measurements without a saved size',
    await mirroredHitBoxes(zeroMeasurements));
  await zeroMeasurements.close();
  }
  const page = await nativeHost(browser, {
    initialViewport:{width:1600,height:1100}, viewport:{width:1600,height:1100,scale:1},
  });
  check('All eight resize hit boxes mirror inside the frame at 100 percent', await mirroredHitBoxes(page));
  const scaled = await nativeHost(browser, {
    initialViewport:{width:2200,height:1600}, viewport:{width:2200,height:1600,scale:2},
  });
  check('All eight resize hit boxes mirror inside the frame at 200 percent', await mirroredHitBoxes(scaled));
  check('Directional CSS cursors remain available independently of the generic native cursor',
    await scaled.locator('.ss-resize-grip').evaluateAll(grips => {
      const names = {nw:'nwse-resize',se:'nwse-resize',ne:'nesw-resize',sw:'nesw-resize',
        n:'ns-resize',s:'ns-resize',e:'ew-resize',w:'ew-resize'};
      return grips.every(grip => getComputedStyle(grip).cursor === names[grip.getAttribute('data-corner')]);
    }));
  await scaled.close();
  await page.evaluate(() => {
    window.__resizeHandled = 0;
    window.__resizeStageTracking = [];
    window.__resizeBubbled = [];
    viewEnv.setEventHandled = () => { __resizeHandled += 1; };
    viewEnv.setTrackMouseOnStage = active => __resizeStageTracking.push(active);
    window.__resizeClock = 1000;
    Date.now = () => __resizeClock;
    document.getElementById('grz-session-stats').addEventListener('mousedown', () => __resizeBubbled.push('down'));
    window.addEventListener('mousemove', () => __resizeBubbled.push('move'));
    for (const grip of document.querySelectorAll('.ss-resize-grip')) {
      // Gameface must also work through its bubbling mouse events.
      grip.dispatchEvent(new MouseEvent('mouseover', {bubbles:true}));
      grip.dispatchEvent(new MouseEvent('mousemove', {bubbles:true,cancelable:true}));
      grip.dispatchEvent(new MouseEvent('mouseout', {bubbles:true}));
    }
  });
  check('All eight native resize grips request the supported cursor and restore it on hover exit',
    await page.evaluate(() => {
      const commands = __grzCommands.filter(command => command.action === 'resize_cursor');
      return commands.length === 16 && ['nw','ne','sw','se','n','e','s','w'].every(corner =>
        commands.some(command => command.corner === corner && command.active === 'true') &&
        commands.some(command => command.corner === corner && command.active === 'false'));
    }));
  check('Native cursor reassertion follows host hover updates, stays bounded and ignores internal transitions',
    await page.evaluate(() => {
      const grip = document.querySelector('[data-corner="w"]');
      const before = __grzCommands.length;
      const send = (type, relatedTarget) => grip.dispatchEvent(new MouseEvent(type, {
        bubbles:true,cancelable:true,relatedTarget:relatedTarget || null,
      }));
      send('mouseover');
      const retry = [...__grzTimers].find(([, timer]) => timer.delay === 0);
      if (!retry) return false;
      __grzTimers.delete(retry[0]);
      retry[1].callback();
      let commands = __grzCommands.slice(before).filter(command => command.action === 'resize_cursor');
      if (commands.length !== 2 || commands.some(command => command.active !== 'true')) return false;
      const child = document.createElement('span');
      grip.appendChild(child);
      send('mouseout', child);
      send('mouseover', child);
      for (let offset = 1; offset < 100; offset += 1) {
        __resizeClock = 1000 + offset;
        send('mousemove');
      }
      commands = __grzCommands.slice(before).filter(command => command.action === 'resize_cursor');
      if (commands.length !== 2) return false;
      __resizeClock = 1100;
      send('mousemove');
      const pending = [...__grzTimers].find(([, timer]) => timer.delay === 0);
      send('mouseout');
      // Simulate failed native timer cancellation followed by re-entering the same grip.
      send('mouseover');
      const beforeStale = __grzCommands.length;
      pending[1].callback();
      const staleIsInert = __grzCommands.length === beforeStale;
      send('mouseout');
      child.remove();
      return staleIsInert;
    }));
  await page.evaluate(() => {
    const grip = document.querySelector('[data-corner="n"]');
    const down = new MouseEvent('mousedown', {button:0,clientX:300,clientY:4,bubbles:true,cancelable:true});
    grip.dispatchEvent(down);
    window.__resizeDownPrevented = down.defaultPrevented;
    window.__resizeToken = __grzCommands.filter(command => command.action === 'resize_begin').pop().token;
    GRZSessionStats.update({resize_gesture:{token:__resizeToken,width:700,height:700,active:true}});
    window.__resizeCursorCountAtCapture = __grzCommands.filter(command => command.action === 'resize_cursor').length;
    const move = new MouseEvent('mousemove', {buttons:1,clientX:300,clientY:2,bubbles:true,cancelable:true});
    grip.dispatchEvent(move);
    window.__resizeMovePrevented = move.defaultPrevented;
    grip.dispatchEvent(new MouseEvent('mouseleave'));
  });
  check('Resize press and movement cancel both DOM propagation and native garage input',
    await page.evaluate(() => __resizeDownPrevented && __resizeMovePrevented &&
      __resizeBubbled.length === 0 && __resizeHandled >= 18 &&
      __resizeStageTracking.length === 1 && __resizeStageTracking[0] === true));
  check('Leaving a grip during a native gesture keeps its cursor captured',
    await page.evaluate(() => __grzCommands.filter(command => command.action === 'resize_cursor').length ===
      __resizeCursorCountAtCapture));
  await page.evaluate(() => {
    window.__resizeStageMove = __grzEvents.mousemove;
    window.__resizeStageUp = __grzEvents.mouseup;
    __resizeStageMove({buttons:1});
    __resizeStageUp({button:2});
    // Client engine stage events are also supported without a payload.
    __resizeStageMove();
    __resizeStageUp();
  });
  check('Stage events with or without payload are consumed while global LEFTMOUSE owns release',
    await page.evaluate(() => __resizeHandled >= 22 &&
      !__grzCommands.some(command => command.action === 'resize_end') &&
      JSON.stringify(__resizeStageTracking) === '[true]'));
  // The global native poll reports the final sample at left-button release.
  await page.evaluate(() => GRZSessionStats.update({
    resize_gesture:{token:__resizeToken,width:700,height:760,active:false},
  }));
  await page.waitForFunction(() => __nativeSize[0] === 700 && __nativeSize[1] === 760);
  check('Outside-stage release is handled, flushes the final size and disables stage tracking',
    await page.evaluate(() => __resizeHandled >= 22 &&
      JSON.stringify(__resizeStageTracking) === '[true,false]' &&
      __grzCommands.some(command => command.action === 'size_preference' &&
        command.width === '700' && command.height === '760') &&
      __grzCommands.filter(command => command.action === 'resize_cursor').pop().active === 'false'));
  check('Retired stage listeners cannot affect a later garage input event',
    await page.evaluate(() => {
      const previous = __resizeHandled;
      __resizeStageMove({buttons:1});
      __resizeStageUp({button:0});
      return __resizeHandled === previous;
    }));
  await page.close();

  const responsive = await nativeHost(browser, {
    initialViewport:{width:1600,height:1100}, viewport:{width:1600,height:1100,scale:1},
  });
  const timing = await responsive.evaluate(() => {
    const originalFrame = window.requestAnimationFrame;
    const frames = [];
    window.requestAnimationFrame = callback => frames.push(callback);
    const grip = document.querySelector('[data-corner="se"]');
    grip.dispatchEvent(new MouseEvent('mousedown', {button:0,clientX:699,clientY:729,
      bubbles:true,cancelable:true}));
    const token = __grzCommands.filter(command => command.action === 'resize_begin').pop().token;
    const sample = (width, height, active) => GRZSessionStats.update({
      resize_gesture:{token,width,height,active},
    });
    const groups = document.getElementById('ss-groups');
    const widthsStart = __grzTimerSequence;
    const tasks = (after, delay) => [...__grzTimers].filter(([id, timer]) => id > after && timer.delay === delay);
    const run = task => {
      __grzTimers.delete(task[0]);
      task[1].callback();
    };
    try {
      sample(900, 830, true);
      const firstLayout = tasks(widthsStart, 120)[0];
      sample(1120, 835, true);
      sample(1300, 840, true);
      const surfaces = tasks(widthsStart, 0), layouts = tasks(widthsStart, 120);
      const coalesced = surfaces.length === 1 && layouts.length === 1 && firstLayout &&
        layouts[0][0] === firstLayout[0];
      if (!coalesced) return {coalesced};
      run(surfaces[0]);
      const latestSurface = __nativeSize[0] === 1300 && __nativeSize[1] === 840;
      run(firstLayout);
      run(tasks(widthsStart, 40)[0]);
      const activeLayout = groups.classList.contains('ss-two-columns');
      const heightStart = __grzTimerSequence;
      sample(1300, 860, true);
      run(tasks(heightStart, 0)[0]);
      const heightOnly = __nativeSize[1] === 860 && tasks(heightStart, 120).length === 0;
      const releaseStart = __grzTimerSequence;
      sample(900, 850, false);
      run(tasks(releaseStart, 0)[0]);
      run(tasks(releaseStart, 40)[0]);
      const releaseLayout = __nativeSize[0] === 900 && __nativeSize[1] === 850 &&
        !groups.classList.contains('ss-two-columns');
      const calls = __grzHelperCalls.resize;
      frames.slice().forEach(callback => callback());
      return {coalesced,latestSurface,activeLayout,heightOnly,releaseLayout,
        staleFramesInert:__grzHelperCalls.resize === calls};
    } finally { window.requestAnimationFrame = originalFrame; }
  });
  check('Continuous native movement retains one surface task and the original layout deadline', timing.coalesced);
  check('The surface takes the newest size and cards reflow during a held gesture without animation frames',
    timing.latestSurface && timing.activeLayout);
  check('Height-only native updates skip card reflow', timing.heightOnly);
  check('Native release applies final dimensions and layout while delayed frame callbacks stay inert',
    timing.releaseLayout && timing.staleFramesInert);
  await responsive.close();

  const feedPage = await nativeHost(browser, {
    initialViewport:{width:1700,height:1150}, viewport:{width:1700,height:1150,scale:1},
  });
  try {
    const settle = () => feedPage.evaluate(() => new Promise(resolve => {
      let remaining = 5;
      function frame() { if (--remaining) requestAnimationFrame(frame); else resolve(); }
      requestAnimationFrame(frame);
    }));
    for (const input of ['wheel', 'uncancelable wheel', 'keyboard', 'scrollbar']) {
      await feedPage.evaluate(input => {
        const payload = JSON.parse(model.payload), scope = payload.scopes.launch;
        const sample = scope.battles[0];
        payload.account_key = 'resize-feed-' + input;
        payload.window_size = [900, 780];
        scope.battles = Array.from({length:10}, (_, index) => ({...sample,id:'resize-feed-card-' + index}));
        scope.pagination = {...scope.pagination,battles:{page:0,pages:2,total:20,page_size:10}};
        model.payload = JSON.stringify(payload);
        __grzEvents['viewEnv.onDataChanged']();
        document.getElementById('ss-group-battles').click();
      }, input);
      await settle();
      await feedPage.evaluate(() => {
        const grip = document.getElementById('ss-resize-grip'), scroll = document.getElementById('ss-scroll');
        window.__resizeFeedPagesBefore = __grzCommands.filter(command => command.action === 'page').length;
        window.__resizeFeedCard = document.querySelector('#ss-groups .ss-group');
        const box = grip.getBoundingClientRect();
        grip.dispatchEvent(new MouseEvent('mousedown', {button:0,clientX:box.left+2,clientY:box.top+2,bubbles:true,cancelable:true}));
        const token = __grzCommands.filter(command => command.action === 'resize_begin').at(-1).token;
        GRZSessionStats.update({resize_gesture:{token,width:1300,height:800,active:true}});
        scroll.scrollTop = scroll.scrollHeight;
        scroll.dispatchEvent(new Event('scroll'));
        GRZSessionStats.update({resize_gesture:{token,width:1300,height:800,active:false}});
      });
      await feedPage.waitForFunction(() => __nativeSize[0] === 1300 && __nativeSize[1] === 800);
      await settle();
      await feedPage.evaluate(() => {
        const scroll = document.getElementById('ss-scroll');
        // Gameface can report the clamped scroll position after release. An
        // incidental horizontal wheel or non-scrolling key must not own it.
        scroll.dispatchEvent(new WheelEvent('wheel', {deltaX:10,bubbles:true,cancelable:true}));
        scroll.dispatchEvent(new KeyboardEvent('keydown', {key:'Tab',bubbles:true}));
        scroll.scrollTop = scroll.scrollHeight;
        scroll.dispatchEvent(new Event('scroll'));
      });
      await settle();
      check('A late resize scroll keeps mounted Battles visible with no page request before '+input,
        await feedPage.evaluate(() => document.getElementById('grz-session-stats').getAttribute('aria-busy') === 'false' &&
          document.querySelector('#ss-groups .ss-group') === __resizeFeedCard &&
          __grzCommands.filter(command => command.action === 'page').length === __resizeFeedPagesBefore));
      await feedPage.evaluate(input => {
        const scroll = document.getElementById('ss-scroll');
        window.__resizeFeedTimersBefore = __grzTimerSequence;
        if (input === 'scrollbar') {
          const rail = document.getElementById('ss-scrollbar'), rect = rail.getBoundingClientRect();
          const mouse = {bubbles:true,cancelable:true,button:0,clientX:rect.left+2,clientY:rect.bottom-4};
          rail.dispatchEvent(new MouseEvent('mousedown', mouse));
          document.dispatchEvent(new MouseEvent('mouseup', mouse));
        } else if (input === 'keyboard') {
          scroll.dispatchEvent(new KeyboardEvent('keydown', {key:'End',bubbles:true}));
        } else {
          scroll.dispatchEvent(new WheelEvent('wheel', {deltaY:-5,bubbles:true,cancelable:input === 'wheel'}));
        }
        scroll.dispatchEvent(new Event('scroll'));
      }, input);
      await feedPage.waitForFunction(() => __grzCommands.filter(command => command.action === 'page').length > __resizeFeedPagesBefore);
      check('Intentional '+input+' still requests the adjacent Battles page and displays its loading state',
        await feedPage.evaluate(() => {
          const pages = __grzCommands.filter(command => command.action === 'page'), request = pages.at(-1);
          return pages.length === __resizeFeedPagesBefore+1 && request.group === 'battles' && request.page === '1' &&
            document.getElementById('grz-session-stats').getAttribute('aria-busy') === 'true';
        }));
      if (input === 'wheel') {
        await feedPage.evaluate(() => {
          const timer = [...__grzTimers].find(([id, entry]) => id > __resizeFeedTimersBefore && entry.delay === 10000);
          __grzTimers.delete(timer[0]);
          timer[1].callback();
        });
        check('A missing page clears the resize view loading state and remains retryable',
          await feedPage.evaluate(() => document.getElementById('grz-session-stats').getAttribute('aria-busy') === 'false' &&
            document.querySelector('.ss-page-pending button').textContent === 'Retry'));
        await feedPage.locator('.ss-page-pending button').click();
        await feedPage.waitForFunction(() => __grzCommands.filter(command => command.action === 'page').length === __resizeFeedPagesBefore+2);
      }
    }
  } finally { await feedPage.close(); }
};
