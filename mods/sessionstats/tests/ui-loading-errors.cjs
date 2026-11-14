/* User-action failures reveal recovery UI without discarding loading owners. */
module.exports=async({page,check,caption,frames,publish,geometry})=>{
  await page.evaluate(()=>{window.__loadingAction=model.onAction;window.__loadingFallback=GRZSessionStats.onAction;});
  for(const mode of ['throw','missing']){
    await publish(true);
    check('A live projection owns the overlay before '+mode+' transport failure'+caption,
      await page.locator('#ss-filter-loading').isVisible());
    await page.evaluate(mode=>{
      model.onAction=mode==='throw'?function(){throw new Error('Synthetic action transport failure');}:undefined;
      GRZSessionStats.onAction=undefined;
    },mode);
    await page.locator('#ss-refresh').click();
    const message=mode==='throw'?'Could not complete the action. Try again.':'No connection to the game.';
    check('Refresh '+mode+' failure immediately reveals its error and removes stale busy paint'+caption,
      !await page.locator('#ss-filter-loading').isVisible()&&(await geometry()).rootBusy==='false'&&
      (await geometry()).content==='none'&&await page.locator('#ss-status').textContent()===message);
    await page.evaluate(()=>{model.onAction=__loadingAction;GRZSessionStats.onAction=__loadingFallback;});
    await publish(true);
    check('Fresh data resumes the same pending projection after '+mode+' failure'+caption,
      await page.locator('#ss-filter-loading').isVisible()&&(await geometry()).rootBusy==='true');
    await publish(false);
    check('Completion after '+mode+' recovery clears the overlay'+caption,!await page.locator('#ss-filter-loading').isVisible());
  }
  await publish(true);await page.locator('#ss-maximize').click();await frames(page);
  await page.evaluate(()=>{
    const command=__grzCommands.filter(item=>item.action==='window_settings').pop(),payload=JSON.parse(model.payload);
    if(!command)throw new Error('Expected an owned settings save');
    payload.appearance=payload.appearance||{};
    payload.appearance.window_settings_result={request_id:command.request_id,saved:false};
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  });await frames(page);
  check('A rejected window save reveals its error while history is still loading'+caption,
    !await page.locator('#ss-filter-loading').isVisible()&&(await geometry()).rootBusy==='false'&&
    (await geometry()).content==='none'&&await page.locator('#ss-status').textContent()==='Could not save window settings. Your configuration was preserved.');
  await publish(true);
  check('A later history snapshot retains its pending owner after a window-save error'+caption,
    await page.locator('#ss-filter-loading').isVisible());
  await page.locator('#ss-timeline-from .ss-select-trigger').click();
  await page.locator('#ss-timeline-from [data-value="__custom__"]').click();
  await page.locator('#ss-custom-date-from').fill('invalid');await page.locator('#ss-custom-date-from').press('Enter');
  check('Invalid range input reveals validation instead of leaving a loading veil over it'+caption,
    !await page.locator('#ss-filter-loading').isVisible()&&(await geometry()).rootBusy==='false'&&
    (await geometry()).content==='none'&&await page.locator('#ss-custom-date-from').getAttribute('aria-invalid')==='true'&&
    await page.locator('#ss-status').textContent()==='Enter a valid date and time.');
  await publish(true);
  check('Fresh data resumes its projection after range validation without cancelling that owner'+caption,
    await page.locator('#ss-filter-loading').isVisible());
  await publish(false);
  check('The recovered projection still completes normally after range validation'+caption,
    !await page.locator('#ss-filter-loading').isVisible()&&(await geometry()).rootBusy==='false');
};
