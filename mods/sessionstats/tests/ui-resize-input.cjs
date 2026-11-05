/* Native input-adapter contracts; actual garage/cursor rendering needs in-game QA. */
module.exports = async function ({browser, nativeHost, check}) {
  const page = await nativeHost(browser, {
    initialViewport:{width:1600,height:1100}, viewport:{width:1600,height:1100,scale:1},
  });
  await page.evaluate(() => {
    window.__resizeHandled = 0;
    window.__resizeStageTracking = [];
    window.__resizeBubbled = [];
    viewEnv.setEventHandled = () => { __resizeHandled += 1; };
    viewEnv.setTrackMouseOnStage = active => __resizeStageTracking.push(active);
    document.getElementById('grz-session-stats').addEventListener('mousedown', () => __resizeBubbled.push('down'));
    window.addEventListener('mousemove', () => __resizeBubbled.push('move'));
    for (const grip of document.querySelectorAll('.ss-resize-grip')) {
      grip.dispatchEvent(new MouseEvent('mouseenter'));
      grip.dispatchEvent(new MouseEvent('mousemove', {bubbles:true,cancelable:true}));
      grip.dispatchEvent(new MouseEvent('mouseleave'));
    }
  });
  check('All eight native resize grips request the supported cursor and restore it on hover exit',
    await page.evaluate(() => {
      const commands = __grzCommands.filter(command => command.action === 'resize_cursor');
      return commands.length === 16 && ['nw','ne','sw','se','n','e','s','w'].every(corner =>
        commands.some(command => command.corner === corner && command.active === 'true') &&
        commands.some(command => command.corner === corner && command.active === 'false'));
    }));
  await page.evaluate(() => {
    const grip = document.querySelector('[data-corner="n"]');
    const down = new MouseEvent('mousedown', {button:0,clientX:300,clientY:4,bubbles:true,cancelable:true});
    grip.dispatchEvent(down);
    window.__resizeDownPrevented = down.defaultPrevented;
    window.__resizeToken = __grzCommands.filter(command => command.action === 'resize_begin').pop().token;
    GRZSessionStats.update({resize_gesture:{token:__resizeToken,width:700,height:700,active:true}});
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
    await page.evaluate(() => __grzCommands.filter(command => command.action === 'resize_cursor').length === 16));
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
};
