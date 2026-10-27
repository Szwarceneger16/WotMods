/* Loading must never display an incomplete history as a completed zero total. */
module.exports = async ({browser,nativeHost,check}) => {
  const page = await nativeHost(browser,{});
  await page.evaluate(() => {
    window.__readySnapshot = JSON.parse(model.payload);
    const snapshot = JSON.parse(model.payload);
    snapshot.loading = true;
    model.payload = JSON.stringify(snapshot);
    GRZSessionStats.update(model.payload);
    document.getElementById('ss-scope-manual').click();
  });
  check('History loading replaces totals with a loading notice', await page.locator('#ss-summary').textContent().then(t=>t.includes('Loading history')));
  check('History loading hides all previously rendered battle rows', await page.locator('#ss-groups .ss-group').count()===0);
  check('History loading clears the previous page counter', await page.locator('#ss-page-label').textContent()==='');
  check('History loading preserves the scroll container and groups node', await page.locator('#ss-scroll #ss-groups').count()===1);
  check('History loading disables manual reset', await page.locator('#ss-reset').isDisabled());
  await page.evaluate(()=>document.getElementById('ss-reset').onclick());
  check('Retained reset handler cannot open a loading-period reset', !await page.locator('#ss-reset-overlay').isVisible());
  check('Loading status does not claim completed zero battles', await page.locator('#ss-status').textContent().then(t=>t.includes('Loading history')));
  await page.evaluate(()=>{
    const snapshot=JSON.parse(model.payload);
    snapshot.warnings=['Synthetic receipt write failure'];
    model.payload=JSON.stringify(snapshot); GRZSessionStats.update(model.payload);
  });
  check('Loading retains receipt and timer warnings', await page.locator('#ss-summary').textContent().then(t=>t.includes('Synthetic receipt write failure')));
  await page.evaluate(()=>{
    const snapshot=JSON.parse(model.payload);
    snapshot.loading=false; snapshot.load_error='Synthetic load failure';
    model.payload=JSON.stringify(snapshot); GRZSessionStats.update(model.payload);
  });
  check('Failed loading displays the error and keeps reset disabled', await page.locator('#ss-status').textContent()==='Synthetic load failure' && await page.locator('#ss-reset').isDisabled());
  await page.evaluate(()=>{
    model.payload=JSON.stringify(__readySnapshot); GRZSessionStats.update(model.payload);
  });
  check('Completed loading restores period totals and reset', await page.locator('#ss-summary .ss-kpi-value').count()>0 && !await page.locator('#ss-reset').isDisabled());
  check('Completed loading restores rows in the original scroll container', await page.locator('#ss-scroll #ss-groups .ss-group').count()>0);
  await page.close();
};
