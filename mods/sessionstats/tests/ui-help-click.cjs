/* Pointer help toggles must not inherit keyboard focus or a retained hover. */
module.exports=async ({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{});
  const helpTimers=()=>page.evaluate(()=>[...__grzTimers]
    .filter(([,timer])=>String(timer.callback).includes('helpPending'))
    .map(([id,timer])=>({id,delay:timer.delay})));
  try {
    const info=page.locator('#ss-summary .ss-performance .ss-info-button'),tooltip=page.locator('#ss-help-tooltip');
    await page.locator('#ss-close').focus();await info.hover({position:{x:4,y:5}});
    check('Info hover paints its orange outline before opening help',await tooltip.isHidden() &&
      await info.evaluate(node=>{const style=getComputedStyle(node);return style.outlineStyle==='solid' &&
        parseFloat(style.outlineWidth)>=1 && style.outlineColor==='rgb(231, 162, 59)';}));
    const pending=await helpTimers();
    check('Info hover remains delayed before an intentional pointer click',
      pending.length===1 && pending[0].delay===500 && await tooltip.isHidden());
    await info.click({position:{x:4,y:5}});
    check('One pointer click opens help without leaving the icon keyboard-focused',await tooltip.isVisible() &&
      await info.evaluate(node=>document.activeElement!==node) && await info.getAttribute('aria-expanded')==='true');
    await info.click({position:{x:4,y:5}});
    check('A second stationary click closes help and retires the previous hover timer',await tooltip.isHidden() &&
      (await helpTimers()).length===0 && await info.evaluate(node=>document.activeElement!==node) &&
      await info.getAttribute('aria-expanded')==='false');
    await page.locator('#ss-close').hover();await info.hover({position:{x:4,y:5}});
    const fresh=await helpTimers();
    check('Hover after pointer dismissal begins a fresh full delay',
      fresh.length===1 && fresh[0].id!==pending[0].id && fresh[0].delay===500 && await tooltip.isHidden());
    await page.evaluate(id=>{
      const timer=__grzTimers.get(id);
      __grzTimers.delete(id);
      timer.callback();
    },fresh[0].id);
    check('A fresh stationary hover can open help after pointer dismissal',await tooltip.isVisible());
    await page.keyboard.press('Escape');await page.locator('#ss-close').focus();await info.focus();
    check('Keyboard focus still exposes help immediately',await tooltip.isVisible() && await info.evaluate(node=>document.activeElement===node));
    await info.press('Enter');
    check('Keyboard activation can close help while retaining accessible focus',await tooltip.isHidden() && await info.evaluate(node=>document.activeElement===node));
    await info.press('Space');
    check('Keyboard activation can reopen the focused explanation',await tooltip.isVisible() && await info.evaluate(node=>document.activeElement===node));
  } finally {await page.close();}
  await require('./ui-tooltip-delay.cjs')({browser,nativeHost,check});
};
