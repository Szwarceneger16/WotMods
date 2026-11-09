/* Pointer help toggles must not inherit keyboard focus or a retained hover. */
module.exports=async ({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{realTimers:true});
  try {
    const info=page.locator('#ss-summary .ss-performance .ss-info-button'),tooltip=page.locator('#ss-help-tooltip');
    await page.locator('#ss-close').focus();await info.hover({position:{x:4,y:5}});
    await page.waitForTimeout(250);
    check('Info hover remains delayed before an intentional pointer click',await tooltip.isHidden());
    await info.click({position:{x:4,y:5}});
    check('One pointer click opens help without leaving the icon keyboard-focused',await tooltip.isVisible() &&
      await info.evaluate(node=>document.activeElement!==node) && await info.getAttribute('aria-expanded')==='true');
    await info.click({position:{x:4,y:5}});
    await page.waitForTimeout(1100);
    check('A second stationary click closes help and retires the previous hover timer',await tooltip.isHidden() &&
      await info.evaluate(node=>document.activeElement!==node) && await info.getAttribute('aria-expanded')==='false');
    await page.locator('#ss-close').hover();await info.hover({position:{x:4,y:5}});
    await page.waitForTimeout(500);
    check('Hover after pointer dismissal begins a fresh full delay',await tooltip.isHidden());
    await page.waitForTimeout(650);
    check('A fresh stationary hover can open help after pointer dismissal',await tooltip.isVisible());
    await page.keyboard.press('Escape');await page.locator('#ss-close').focus();await info.focus();
    check('Keyboard focus still exposes help immediately',await tooltip.isVisible() && await info.evaluate(node=>document.activeElement===node));
    await info.press('Enter');
    check('Keyboard activation can close help while retaining accessible focus',await tooltip.isHidden() && await info.evaluate(node=>document.activeElement===node));
    await info.press('Space');
    check('Keyboard activation can reopen the focused explanation',await tooltip.isVisible() && await info.evaluate(node=>document.activeElement===node));
  } finally {await page.close();}
};
