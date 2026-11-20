/* Custom help owns a 500 ms entry delay, including source cells and sort badges. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  const messages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages.en;
  const page=await nativeHost(browser,{initialViewport:{width:1800,height:1300},viewport:{width:1800,height:1300,scale:1}});
  const tooltip=page.locator('#ss-help-tooltip');
  const timers=()=>page.evaluate(()=>[...__grzTimers].filter(([,timer])=>String(timer.callback).includes('helpPending')).map(([id,timer])=>({id,delay:timer.delay})));
  async function fire(id){await page.evaluate(id=>{const timer=__grzTimers.get(id);if(!timer)throw Error('Expected owned help timer');__grzTimers.delete(id);timer.callback();},id);}
  async function leave(){await page.locator('#ss-titlebar h1').hover();await page.locator('#ss-close').focus();}
  async function publish(observed=27,width=1500){
    await page.evaluate(({observed,messages,width})=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
      payload.account_key='SYNTHETIC:tooltip-entry-'+observed+'-'+width;
      payload.viewport.width=width===550?570:1800;
      payload.window_size=[width,1050];payload.localization={language:'en',messages};
      scope.summary.battles=24;scope.summary.observed_battles=observed;
      scope.summary.credits_income_received={count:24,min:10,avg:100,max:200,sum:2400};
      const item=scope.maps[0];item.stats=JSON.parse(JSON.stringify(scope.summary));item.stats.credits_income_received={count:24,min:10,avg:100,max:200,sum:2400};
      scope.maps=[item];scope.ordering.maps={metric:'credits_income_received',statistic:'avg',direction:'desc',chronology:'newest'};
      scope.pagination.maps={page:0,pages:1,total:1,page_size:40};
      item.extrema_battles={};
      for(const metric of ['xp_base','xp_received','battle_wn8']){
        const data=item.stats[metric];if(!data||!data.count)continue;
        item.extrema_battles[metric]={};
        for(const statistic of ['min','max'])if(typeof data[statistic]==='number')item.extrema_battles[metric][statistic]={
          id:'synthetic-tooltip-'+metric+'-'+statistic,metric,statistic,value:data[statistic],
          name:'Synthetic vehicle',map:'Synthetic map',started_at:1793514000};
      }
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
    },{observed,messages,width});
    await page.locator('#ss-scope-launch').click();await page.locator('#ss-group-maps').click();await frames(page);
  }
  try{
    await publish();
    const badge=page.locator('#ss-groups .ss-group-sort-value').first(),info=page.locator('#ss-summary .ss-performance .ss-info-button');
    check('A pending-only sorting value keeps custom help without a missing-field triangle',await badge.evaluate(node=>
      node.classList.contains('ss-hover-help')&&!node.querySelector('.ss-sort-partial-icon')&&
      node.getAttribute('data-ss-help').includes('24 of 27 recorded battles')&&node.getAttribute('data-ss-help').includes('Pending: 3')&&
      !node.getAttribute('data-ss-help').includes('Available results only')&&node.getAttribute('title')===null&&node.parentNode.getAttribute('title')===null));
    await leave();await badge.hover({position:{x:5,y:5}});let pending=await timers();
    check('A sort caption schedules exactly one custom 500 ms timer and remains closed before it fires',pending.length===1&&pending[0].delay===500&&await tooltip.isHidden());
    const first=pending[0].id;
    await badge.hover({position:{x:9,y:7}});await badge.hover({position:{x:13,y:8}});
    pending=await timers();
    check('Pointer jitter within the same sorting result does not restart its entry timer',pending.length===1&&pending[0].id===first);
    await fire(first);
    check('The sorting result opens its own custom explanation when the 500 ms timer fires',await tooltip.isVisible()&&
      (await tooltip.textContent()).includes('24 of 27 recorded battles')&&await badge.getAttribute('aria-expanded')==='true'&&await badge.getAttribute('aria-describedby')==='ss-help-tooltip');
    await leave();await info.hover({position:{x:3,y:4}});pending=await timers();const cancelled=pending[0].id;
    await leave();
    check('Leaving another custom target cancels the pending 500 ms timer',!(await timers()).some(timer=>timer.id===cancelled)&&await tooltip.isHidden());
    await badge.focus();
    check('Keyboard focus still opens the same sorting explanation immediately',await tooltip.isVisible()&&await badge.getAttribute('aria-expanded')==='true');
    await leave();
    const cell=page.locator('#ss-groups .ss-metric-row[data-ss-metric="xp_base"] .ss-extreme-cell').first(),button=cell.locator('.ss-metric-battle-link');
    const number=await cell.evaluate(cell=>{
      const button=cell.querySelector('.ss-metric-battle-link'),value=[...cell.childNodes].find(node=>node!==button&&node.textContent.trim());
      const range=document.createRange();range.selectNodeContents(value);const box=range.getBoundingClientRect();return{x:box.x+box.width/2,y:box.y+box.height/2};
    });
    await page.mouse.move(number.x,number.y);pending=await timers();
    check('Hovering a source number schedules the action button\'s 500 ms help',pending.length===1&&pending[0].delay===500&&await button.getAttribute('aria-expanded')==='false');
    const source=pending[0].id;await button.hover();pending=await timers();
    check('Moving from the number to its arrow retains the same action-owned entry timer',pending.length===1&&pending[0].id===source);
    await fire(source);
    check('The actual source button owns expanded/described-by state for number and arrow help',await tooltip.isVisible()&&
      await button.getAttribute('aria-expanded')==='true'&&await button.getAttribute('aria-describedby')==='ss-help-tooltip'&&
      await button.getAttribute('title')===null&&await cell.getAttribute('title')===null);
    await leave();await publish(24);
    check('A completely known sorting result also uses custom help rather than a late native title',await badge.evaluate(node=>
      node.classList.contains('ss-hover-help')&&!!node.getAttribute('data-ss-help')&&!node.querySelector('.ss-sort-partial-icon')&&
      node.getAttribute('title')===null&&node.parentNode.getAttribute('title')===null));
    await badge.hover();pending=await timers();
    check('Complete and partial sorting captions share the 500 ms custom entry delay',pending.length===1&&pending[0].delay===500);
    await leave();await page.evaluate(()=>{
      const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.maps={metric:'xp_base',statistic:'max',direction:'desc',chronology:'newest'};
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
    });await frames(page);
    const active=page.locator('#ss-groups .ss-metric-row[data-ss-metric="xp_base"] .ss-extreme-cell.ss-sort-active-value');
    await active.locator('.ss-metric-battle-link').hover();
    check('Source help removes a sorting cell\'s ancestor native title as well as the action title',
      await active.getAttribute('title')===null&&await active.locator('.ss-metric-battle-link').getAttribute('title')===null);

    await leave();
    const edgeHelp=page.locator('#ss-test-edge-help');
    await page.evaluate(()=>{
      const target=document.createElement('button');
      target.id='ss-test-edge-help';target.className='ss-hover-help';
      target.style.cssText='position:absolute;right:14rem;bottom:14rem;width:36rem;height:20rem';
      target.setAttribute('aria-controls','ss-help-tooltip');
      document.getElementById('grz-session-stats').appendChild(target);
    });
    async function auditText(text,side='right'){
      await leave();
      await edgeHelp.evaluate((target,text)=>target.setAttribute('data-ss-help',text),text);
      await edgeHelp.focus();await frames(page);
      return tooltip.evaluate((node,side)=>{
        const panel=node.closest('#grz-session-stats').getBoundingClientRect(),box=node.getBoundingClientRect(),
          anchor=document.getElementById('ss-test-edge-help').getBoundingClientRect(),range=document.createRange();
        range.selectNodeContents(node);
        const ink=[...range.getClientRects()].filter(part=>part.width>0),inside=(part,owner)=>
          part.left>=owner.left-1&&part.right<=owner.right+1&&part.top>=owner.top-1&&part.bottom<=owner.bottom+1;
        return {width:box.width,height:box.height,text:node.textContent,lines:ink.length,
          longest:Math.max(...ink.map(part=>part.width)),inside:inside(box,panel)&&ink.every(part=>inside(part,box)),
          anchored:Math.abs(box[side]-anchor[side])<=1&&Math.abs(anchor.top-box.bottom-12)<=1};
      },side);
    }
    const short=await auditText('Combined WN8');
    check('Short tooltip fits its text and stays anchored at the bottom-right edge: '+JSON.stringify(short),
      short.text==='Combined WN8'&&short.lines===1&&short.width>=short.longest&&short.width<=short.longest+30&&short.inside&&short.anchored);
    const multiline=await auditText('WN8\nFree XP');
    check('Explicit help line breaks size the box to the longest line: '+JSON.stringify(multiline),
      multiline.lines===2&&multiline.height>short.height&&multiline.width>=multiline.longest&&multiline.width<=multiline.longest+30&&multiline.inside);
    const explanation='Battle statistics report confirmed results and the fields available in each result. '.repeat(6).trim();
    const long=await auditText(explanation);
    check('Long help wraps within its width cap and fits near the bottom-right edge: '+JSON.stringify(long),
      long.text===explanation&&long.lines>2&&long.width>short.width&&long.width<=321&&long.inside&&long.anchored);

    await publish(24,550);
    await edgeHelp.evaluate(target=>{target.style.left='48%';target.style.right='auto';target.style.width='18rem';});
    const centered=await auditText('Combined WN8','left');
    check('Short help stays attached to its anchor when the full width cap fits on neither side: '+JSON.stringify(centered),
      centered.lines===1&&centered.width>=centered.longest&&centered.width<=centered.longest+30&&centered.inside&&centered.anchored);
  }finally{await page.close();}
};
