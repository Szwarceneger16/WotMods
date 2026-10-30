/* Gameface-compatible select menus, native sorting protocol and narrow layouts. */
const fs=require('fs'),path=require('path');
module.exports=async ({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{});
  await page.locator('#ss-group-tiers').click();
  await page.evaluate(()=>{const s=JSON.parse(model.payload);s.localization={language:'en',messages:{'groups.tiers.count':'Legacy count · newest first'}};GRZSessionStats.update(s);});
  check('Legacy count text cannot mislabel the current ordering',!(await page.locator('#ss-list-meta').textContent()).includes('newest first'));
  check('Tiers tab shows the real tier aggregate',await page.locator('#ss-groups .ss-group').count()===1 && await page.locator('#ss-groups .ss-group-title').textContent()==='X');
  check('Off retains chronology and disables statistic/direction only',await page.locator('#ss-sort-statistic button[role=combobox]').isDisabled() && await page.locator('#ss-sort-direction button[role=combobox]').isDisabled() && await page.locator('#ss-sort-chronology button[role=combobox]').isEnabled());
  async function choose(field,value){
    await page.locator('#ss-sort-'+field+' [role=combobox]').click();
    await page.locator('#ss-sort-'+field+' [data-value="'+value+'"]').click();
    await page.evaluate(()=>{
      const command=__grzCommands.filter(c=>c.action==='sort').pop();
      const snapshot=JSON.parse(model.payload),scope=snapshot.scopes[command.scope];
      scope.ordering[command.group]={metric:command.metric,statistic:command.statistic,direction:command.direction,chronology:command.chronology};
      scope.pagination[command.group].page=0;
      model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);
    });
  }
  await choose('metric','xp_received');
  await choose('statistic','max');
  await choose('direction','asc');
  check('All three selectors dispatch their values with native account and period ownership',await page.evaluate(()=>{
    const c=__grzCommands.filter(c=>c.action==='sort').pop(),s=JSON.parse(model.payload);
    return c.metric==='xp_received' && c.statistic==='max' && c.direction==='asc' && c.chronology==='newest' && c.group==='tiers' && c.scope==='launch' && c.account_key===s.account_key && c.period_id===s.scopes.launch.period_id;
  }));
  await choose('metric','off');
  await choose('chronology','oldest');
  check('Chronological ordering is independent when metric sorting is off',await page.evaluate(()=>__grzCommands.filter(c=>c.action==='sort').pop().chronology==='oldest'));
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const width of [320,744]) {
    await page.setViewportSize({width,height:820});
    for(const [language,messages] of Object.entries(languages)) {
      await page.evaluate(({language,messages,width})=>{
        const snapshot=JSON.parse(model.payload);snapshot.localization={language,messages};snapshot.viewport.width=width;
        const order=snapshot.scopes.launch.ordering.tiers;
        order.metric='xp_received';order.statistic='avg';order.direction='desc';
        model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);
        document.getElementById('ss-sorting').scrollIntoView({block:'center'});
      },{language,messages,width});
      check('Sorting fits one row in '+language+' at '+width,await page.locator('#ss-sorting').evaluate(bar=>{
        const box=bar.getBoundingClientRect(),triggers=Array.from(bar.querySelectorAll('[role=combobox]'));
        const boxes=triggers.map(n=>n.getBoundingClientRect());
        return boxes.length===3 && boxes.every(b=>b.left>=box.left-1 && b.right<=box.right+1 && Math.abs(b.top-boxes[0].top)<1) && triggers.every(trigger=>{const label=trigger.querySelector('.ss-control-label'),range=document.createRange();range.selectNodeContents(label);const original=label.textContent,available=label.getBoundingClientRect().width;const fits=Array.from(trigger.parentNode.querySelectorAll('[role=option]')).every(option=>{label.textContent=option.textContent;range.selectNodeContents(label);return range.getBoundingClientRect().width<=available+1;});label.textContent=original;return fits;});
      }));
      await page.locator('#ss-sort-direction [role=combobox]').click();
      check('Open menu stays inside the panel in '+language+' at '+width,await page.locator('#ss-options-direction').evaluate(menu=>{
        const m=menu.getBoundingClientRect(),p=document.getElementById('grz-session-stats').getBoundingClientRect();
        return m.left>=p.left && m.right<=p.right;
      }));
      await page.keyboard.press('Escape');
      check('Escape closes the select before closing the panel',await page.locator('#ss-sort-direction [role=combobox]').getAttribute('aria-expanded')==='false');
    }
  }
  await page.locator('#ss-sort-metric [role=combobox]').focus();
  await page.keyboard.press('ArrowDown');await page.keyboard.press('Home');await page.keyboard.press('Enter');
  check('Keyboard selection emits a sorting command',await page.evaluate(()=>__grzCommands.filter(c=>c.action==='sort').pop().metric==='off'));
  check('The native document contains no unsupported select elements',await page.locator('select').count()===0);
  await page.close();
};
