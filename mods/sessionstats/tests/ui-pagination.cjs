/* Bounded native payload pages; totals and ownership remain period-wide. */
module.exports = async ({browser,nativeHost,check}) => {
  const page = await nativeHost(browser,{});
  await page.evaluate(() => {
    const snapshot = JSON.parse(model.payload), scope = snapshot.scopes.launch;
    snapshot.account_key = 'EU:pagination';
    scope.period_id = 'launch-pagination';
    const sample = scope.battles[0];
    scope.battles = Array.from({length:40}, (_,i)=>({...sample,id:String(125-i),name:'Battle '+(125-i)}));
    scope.summary.battles = 125;
    scope.pagination = {battles:{page:0,pages:4,page_size:40,total:125}};
    model.payload = JSON.stringify(snapshot); GRZSessionStats.update(model.payload);
    document.getElementById('ss-group-battles').click();
  });
  check('Paged history renders only 40 supplied rows',await page.locator('#ss-groups .ss-group').count()===40);
  check('Pagination reports the whole history count',await page.locator('#ss-list-meta').textContent().then(t=>t.includes('125')));
  check('First page disables Previous and enables Next',await page.evaluate(()=>
    document.getElementById('ss-page-previous').disabled && !document.getElementById('ss-page-next').disabled));
  check('Pagination uses explicit Gameface button labels',await page.locator('#ss-pagination > .ss-button .ss-control-label').count()===2);
  check('Pagination label is visible',await page.locator('#ss-page-label').textContent()==='Page 1 of 4');
  check('Paging buttons share the panel action colors, border and font',await page.evaluate(()=>{
    const next=getComputedStyle(document.getElementById('ss-page-next'));
    // Refresh intentionally uses ss-quiet; compare the existing standard action.
    const action=getComputedStyle(document.getElementById('ss-reset-cancel'));
    return next.backgroundImage!=='none' &&
      ['backgroundImage','color','borderTopColor','borderTopWidth','fontFamily'].every(key=>next[key]===action[key]);
  }));
  for(const width of [320,744]) {
    await page.setViewportSize({width,height:820});
    check('Paging controls and counter fit at width '+width,await page.locator('#ss-pagination').evaluate(bar=>{
      const box=bar.getBoundingClientRect();
      return Array.from(bar.children).every(node=>{const child=node.getBoundingClientRect();
        return child.width>0 && child.left>=box.left-1 && child.right<=box.right+1;});
    }));
  }
  await page.locator('#ss-page-next').click();
  check('Page command carries account, period and grouping ownership',await page.evaluate(()=>{
    const command=__grzCommands.filter(c=>c.action==='page').pop();
    return command.account_key==='EU:pagination' && command.period_id==='launch-pagination' &&
      command.scope==='launch' && command.group==='battles' && command.page==='1';
  }));
  await page.evaluate(()=>{
    const snapshot=JSON.parse(model.payload), scope=snapshot.scopes.launch;
    scope.pagination.battles.page=3; scope.battles=scope.battles.slice(0,5);
    model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);
  });
  check('Last page replaces rows instead of accumulating DOM',await page.locator('#ss-groups .ss-group').count()===5);
  check('Last page disables Next and enables Previous',await page.evaluate(()=>
    document.getElementById('ss-page-next').disabled && !document.getElementById('ss-page-previous').disabled));
  await page.locator('#ss-page-previous').click();
  check('Previous requests the preceding page',await page.evaluate(()=>
    __grzCommands.filter(c=>c.action==='page').pop().page==='2'));
  await page.locator('#ss-scope-manual').click();
  check('Single-page scopes retain chronological sorting between disabled page controls',await page.locator('#ss-pagination').isVisible() && await page.locator('#ss-page-next').isDisabled());
  await page.locator('#ss-scope-launch').click();
  await page.evaluate(()=>{ window.__beforePages=__grzCommands.filter(c=>c.action==='page').length;
    GRZSessionStats.destroy(); document.getElementById('ss-page-previous').onclick(); });
  check('Retained pagination controls cannot dispatch after teardown',await page.evaluate(()=>
    __grzCommands.filter(c=>c.action==='page').length===__beforePages));
  await page.close();
};
