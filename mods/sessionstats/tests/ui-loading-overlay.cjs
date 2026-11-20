/* A visible, pointer-transparent loading layer preserves native recovery paths. */
module.exports=async({page,check,caption,scale,width,acknowledge,frames})=>{
  const publish=async(loading,error)=>{
    await page.evaluate(({loading,error})=>{
      const payload=JSON.parse(model.payload);
      payload.scopes.timeline.loading=loading;payload.scopes.timeline.load_error=error||'';
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    },{loading,error});await frames(page);
  };
  const geometry=()=>page.evaluate(()=>{
    const panel=document.getElementById('grz-session-stats'),overlay=document.getElementById('ss-filter-loading'),
      card=overlay.querySelector('.ss-filter-loading-card')||overlay,spinner=overlay.querySelector('.ss-page-spinner'),
      box=node=>{const r=node.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};};
    return {panel:box(panel),overlay:box(overlay),card:box(card),filters:box(document.getElementById('ss-filter-panel')),
      spinner:parseFloat(getComputedStyle(spinner,':before').width),veil:getComputedStyle(overlay,':before').backgroundColor,
      content:getComputedStyle(document.getElementById('ss-groups')).filter,pointer:getComputedStyle(overlay).pointerEvents,
      rootFont:parseFloat(getComputedStyle(document.documentElement).fontSize),rootBusy:panel.getAttribute('aria-busy'),classBusy:panel.classList.contains('ss-is-loading')};
  });
  for(const logicalWidth of [550,1500]){
    await width(logicalWidth);const before=await geometry();await publish(true);
    const busy=await geometry(),context=' at '+logicalWidth+' logical px'+caption;
    check('Loading covers the complete panel rather than the filter-row corner'+context,
      Math.abs(busy.overlay.left-busy.panel.left)<=scale+0.1&&Math.abs(busy.overlay.right-busy.panel.right)<=scale+0.1&&
      Math.abs(busy.overlay.top-busy.panel.top)<=scale+0.1&&Math.abs(busy.overlay.bottom-busy.panel.bottom)<=scale+0.1);
    check('The large spinner and readable label remain centered in the panel'+context+': '+JSON.stringify(busy),
      Math.abs((busy.card.left+busy.card.right-busy.panel.left-busy.panel.right)/2)<=scale&&
      Math.abs((busy.card.top+busy.card.bottom-busy.panel.top-busy.panel.bottom)/2)<=scale&&busy.spinner>=40*busy.rootFont&&busy.rootFont===scale&&
      await page.locator('.ss-filter-loading-label').textContent()==='Loading page…');
    check('The scrim dims the panel even without backdrop-filter and lightly blurs retained results'+context,
      busy.veil.includes('0.45')&&busy.content.includes('blur(')&&busy.pointer==='none');
    check('Loading announces busy state without moving the filter row'+context,
      busy.rootBusy==='true'&&busy.classBusy&&Math.abs(before.filters.height-busy.filters.height)<=scale);
    await page.locator('#ss-timeline-from .ss-select-trigger').click();
    check('Range replacement controls remain directly reachable through the veil'+context,
      await page.locator('#ss-timeline-from .ss-select-options').isVisible());
    await page.keyboard.press('Escape');
    await page.locator('#ss-scope-launch').click();await frames(page);
    check('A ready scope remains reachable through the scrim and immediately clears it'+context,
      !await page.locator('#ss-filter-loading').isVisible()&&await page.locator('#grz-session-stats').getAttribute('aria-busy')==='false');
    await page.locator('#ss-scope-manual').click();await frames(page);
    check('Returning to a still-loading range restores its owned activity status'+context,
      await page.locator('#ss-filter-loading').isVisible());
    await publish(true,'Synthetic loading-overlay failure');
    check('A projection failure clears both veil and blur so recovery stays readable'+context,
      !await page.locator('#ss-filter-loading').isVisible()&&(await geometry()).content==='none');
    await publish(false);
    check('A completed projection clears panel busy semantics'+context,
      !await page.locator('#ss-filter-loading').isVisible()&&(await geometry()).rootBusy==='false');
  }
  await page.locator('#ss-sort-metric .ss-select-trigger').click();
  await page.locator('#ss-sort-metric [data-value="xp_received"]').click();await frames(page);
  await page.evaluate(()=>__grzEvents['viewEnv.onDataChanged']());await frames(page);
  check('An older sort snapshot cannot dismiss a newer pending sort overlay'+caption,
    await page.locator('#ss-filter-loading').isVisible());
  await acknowledge();
  check('Only the matching sort acknowledgement clears the pending overlay'+caption,
    !await page.locator('#ss-filter-loading').isVisible());
  await page.locator('#ss-sort-metric .ss-select-trigger').click();
  await page.locator('#ss-sort-metric [data-value="xp_base"]').click();await frames(page);
  const malformed=await page.evaluate(()=>GRZSessionStats.update({invalid:'synthetic snapshot'}));
  check('A malformed update releases the failed sort overlay instead of hiding its error'+caption,
    malformed===false&&!await page.locator('#ss-filter-loading').isVisible()&&(await geometry()).content==='none');
  await acknowledge();
  await require('./ui-loading-errors.cjs')({page,check,caption,frames,publish,geometry});
  await publish(true);
  await page.locator('#ss-close').click();
  check('Close remains directly clickable through a full-panel loading veil'+caption,
    await page.evaluate(()=>__grzCommands.some(command=>command.action==='close')));
  await page.evaluate(()=>GRZSessionStats.destroy());
  check('Teardown synchronously clears the loading layer and its busy class'+caption,
    !await page.locator('#ss-filter-loading').isVisible()&&(await geometry()).rootBusy==='false'&&!(await geometry()).classBusy);
};
