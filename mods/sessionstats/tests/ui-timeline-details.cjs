module.exports = async function ({browser, nativeHost, check}) {
  const page = await nativeHost(browser, {
    initialViewport: {width:3840, height:2160},
    viewport: {width:3840, height:2160, scale:2}, changedScale:1,
  });
  await page.evaluate(() => {
    const payload = JSON.parse(model.payload);
    payload.account_key = 'fixture-account';
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
  await page.locator('#ss-time-point').click();
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
  await page.close();
};
