/* Gameface-compatible select menus, native sorting protocol and narrow layouts. */
const fs=require('fs'),path=require('path');
module.exports=async ({browser,nativeHost,check})=>{
  await require('./ui-sort-totals.cjs')({browser,nativeHost,check});
  await require('./ui-chronology.cjs')({browser,nativeHost,check});
  require('./ui-chronology-source.cjs')();check('Actual-source first/last battle ordering supports both directions independently',true);
  const page=await nativeHost(browser,{});
  await page.locator('#ss-group-tiers').click();
  await page.evaluate(()=>{const s=JSON.parse(model.payload);s.localization={language:'en',messages:{'groups.tiers.count':'Legacy count · newest first'}};
    delete s.scopes.launch.ordering.tiers;model.payload=JSON.stringify(s);GRZSessionStats.update(s);});
  check('Legacy count text cannot mislabel the current ordering',!(await page.locator('#ss-list-meta').textContent()).includes('newest first'));
  check('Tiers tab shows the real tier aggregate',await page.locator('#ss-groups .ss-group').count()===1 && await page.locator('#ss-groups .ss-group-title').textContent()==='X');
  check('Off retains chronology and disables statistic/direction only',await page.locator('#ss-sort-statistic button[role=combobox]').isDisabled() && await page.locator('#ss-sort-direction button[role=combobox]').isDisabled() && await page.locator('#ss-sort-chronology button[role=combobox]').isEnabled());
  check('Tiers defaults to highest tier first in the ordinary date/tier selector',
    await page.locator('#ss-sort-chronology .ss-control-label').first().textContent()==='Tier: highest first'&&
    await page.locator('#ss-sort-chronology [data-value="tier_desc"]').evaluate(node=>node.style.display!=='none')&&
    await page.locator('#ss-sort-chronology [data-value="tier_asc"]').evaluate(node=>node.style.display!=='none'));
  for(const group of ['vehicles','maps','tiers','battles']){
    await page.locator('#ss-group-'+group).click();
    const choices=await page.locator('#ss-sort-chronology [role=option]').evaluateAll(nodes=>nodes.filter(node=>node.style.display!=='none').map(node=>({value:node.getAttribute('data-value'),label:node.textContent,description:node.getAttribute('aria-label')})));
    const expected=group==='battles'?['newest','oldest']:group==='tiers'?['newest','last_asc','first_desc','oldest','tier_desc','tier_asc']:['newest','last_asc','first_desc','oldest'];
    check('Ordinary date choices distinguish first/last boundaries only for aggregates in '+group+': '+JSON.stringify(choices),
      JSON.stringify(choices.map(choice=>choice.value))===JSON.stringify(expected)&&choices.every(choice=>choice.description&&choice.label));
    if(group==='battles')check('Retained aggregate date choices cannot sort individual battles',await page.evaluate(()=>{
      const before=__grzCommands.filter(command=>command.action==='sort').length;
      for(const value of ['first_desc','last_asc'])document.querySelector('#ss-sort-chronology [data-value="'+value+'"]').onclick();
      return __grzCommands.filter(command=>command.action==='sort').length===before;
    }));
  }
  await page.locator('#ss-group-tiers').click();
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
  check('Metric sorting disables the independent date selector',await page.locator('#ss-sort-chronology [role=combobox]').isDisabled());
  await choose('statistic','max');
  await choose('direction','asc');
  check('All three selectors dispatch their values with native account and period ownership',await page.evaluate(()=>{
    const c=__grzCommands.filter(c=>c.action==='sort').pop(),s=JSON.parse(model.payload);
    return c.metric==='xp_received' && c.statistic==='max' && c.direction==='asc' && c.chronology==='tier_desc' && c.group==='tiers' && c.scope==='launch' && c.account_key===s.account_key && c.period_id===s.scopes.launch.period_id;
  }));
  for(const group of ['vehicles','maps']){
    await page.locator('#ss-group-'+group).click();
    await choose('metric','battles');
    check('Recorded battle counts are available without Avg/Min/Max for '+group,
      !await page.locator('.ss-sort-statistic').isVisible()&&await page.locator('#ss-sort-statistic [role=combobox]').isDisabled()&&
      await page.locator('#ss-sort-chronology [role=combobox]').isDisabled()&&await page.locator('.ss-group-sort-value').count()===0);
    check('Tier ordering stays out of the ordinary selector in '+group,
      await page.locator('#ss-sort-chronology [data-value="tier_desc"]').evaluate(node=>node.style.display==='none')&&
      await page.locator('#ss-sort-chronology [data-value="tier_asc"]').evaluate(node=>node.style.display==='none'));
  }
  await page.locator('#ss-group-tiers').click();
  check('Tiers hides the recorded battle count metric',await page.locator('#ss-sort-metric [data-value="battles"]').evaluate(node=>node.style.display==='none'));
  check('A retained unsupported count option cannot dispatch',await page.evaluate(()=>{
    const before=__grzCommands.filter(command=>command.action==='sort').length;
    document.querySelector('#ss-sort-metric [data-value="battles"]').onclick();
    return __grzCommands.filter(command=>command.action==='sort').length===before;
  }));
  for(const group of ['vehicles','maps','tiers']){
    await page.locator('#ss-group-'+group).click();await choose('metric','win_rate');
    check('Win rate is available in '+group+' without a meaningless Min/Avg/Max selector',
      await page.locator('#ss-sort-metric [data-value="win_rate"]').evaluate(node=>node.style.display!=='none')&&
      !await page.locator('.ss-sort-statistic').isVisible()&&await page.locator('#ss-sort-statistic [role=combobox]').isDisabled()&&
      await page.locator('.ss-group [data-ss-sort-active="win_rate"]').count()>0&&await page.locator('.ss-group-sort-value').count()===0);
  }
  await page.locator('#ss-group-battles').click();
  check('Battles omits win-rate sorting and rejects retained option callbacks',await page.locator('#ss-sort-metric [data-value="win_rate"]').evaluate(node=>{
    const before=__grzCommands.filter(command=>command.action==='sort').length;
    node.onclick();return node.style.display==='none' && __grzCommands.filter(command=>command.action==='sort').length===before;
  }));
  await page.evaluate(()=>{const snapshot=JSON.parse(model.payload);snapshot.scopes.launch.ordering.battles={metric:'win_rate',statistic:'max',direction:'desc',chronology:'newest'};
    model.payload=JSON.stringify(snapshot);GRZSessionStats.update(snapshot);});
  check('A legacy Battles win-rate selection restores ordinary date sorting',await page.locator('#ss-sort-chronology [role=combobox]').isEnabled()&&
    await page.locator('[data-ss-sort-active="win_rate"]').count()===0);
  await page.locator('#ss-group-tiers').click();
  await choose('metric','off');
  await choose('chronology','oldest');
  check('Chronological ordering is independent when metric sorting is off',await page.evaluate(()=>__grzCommands.filter(c=>c.action==='sort').pop().chronology==='oldest'));
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  // These viewports constrain the actual native panel to 300 and 320 pixels,
  // independently of its preferred 550-pixel minimum.
  for(const width of [320,340,744]) {
    await page.setViewportSize({width,height:820});
    for(const [language,messages] of Object.entries(languages)) {
      await page.evaluate(({language,messages,width})=>{
        const snapshot=JSON.parse(model.payload);snapshot.localization={language,messages};snapshot.viewport.width=width;
        const order=snapshot.scopes.launch.ordering.tiers;
        order.metric='xp_received';order.statistic='avg';order.direction='desc';
        model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);
        document.getElementById('ss-sorting').scrollIntoView({block:'center'});
      },{language,messages,width});
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      const sorting=await page.locator('#ss-sorting').evaluate(bar=>{
        const box=bar.getBoundingClientRect(),triggers=Array.from(bar.querySelectorAll('[role=combobox]'));
        const boxes=triggers.map(n=>n.getBoundingClientRect());
        const overflow=[];
        for(const trigger of triggers){const label=trigger.querySelector('.ss-control-label'),range=document.createRange(),original=label.textContent,available=label.getBoundingClientRect().width;
          for(const option of trigger.parentNode.querySelectorAll('[role=option]')){if(option.style.display==='none')continue;label.textContent=option.textContent;range.selectNodeContents(label);
            const measured=range.getBoundingClientRect().width;if(measured>available+1)overflow.push({field:trigger.parentNode.id,text:option.textContent,measured,available});}
          label.textContent=original;
        }
        return {oneRow:boxes.length===3&&boxes.every(b=>b.left>=box.left-1&&b.right<=box.right+1&&Math.abs(b.top-boxes[0].top)<1),overflow,
          panel:document.getElementById('grz-session-stats').getBoundingClientRect().width,row:box.width};
      });
      check('Sorting fits one row in '+language+' at '+width+': '+JSON.stringify(sorting),sorting.oneRow&&sorting.overflow.length===0);
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
  await require('./ui-sort-extrema.cjs')({browser,nativeHost,check});
};
