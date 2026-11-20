/* Explicit page controls wait for native layout and follow the divider itself. */
const frames=(page,count=8)=>page.evaluate(count=>new Promise(resolve=>{
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}),count);
const commands=page=>page.evaluate(()=>__grzCommands.filter(command=>command.action==='page'));
async function emit(page,index,request,revision){
  await page.evaluate(({index,request,revision})=>{
    const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
    if(revision)scope.data_revision=revision;
    scope.battles=Array.from({length:index===2?5:40},(_,offset)=>({...__pageJumpSample,
      id:'synthetic-page-navigation-'+(index*40+offset),name:'Synthetic battle '+(index*40+offset)}));
    scope.pagination.battles={page:index,pages:3,page_size:40,total:85};
    if(request)scope.pagination.battles.request_id=request.request_id;
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  },{index,request,revision});await frames(page);
}
async function aligned(page,index){
  try{await page.waitForFunction(index=>{
    const section=document.querySelector('.ss-continuous-page[data-page-index="'+index+'"]');
    if(!section)return false;
    const marker=section.getBoundingClientRect(),filter=document.getElementById('ss-filter-panel').getBoundingClientRect();
    return marker.width>1&&marker.height>1&&marker.top>=filter.bottom-1&&marker.top<=filter.bottom+20;
  },index,{timeout:2500});}catch(error){
    throw Error('Page '+index+' did not align: '+JSON.stringify(await page.evaluate(index=>{
      const section=document.querySelector('.ss-continuous-page[data-page-index="'+index+'"]');
      return {marker:section&&section.getBoundingClientRect().top,
        filter:document.getElementById('ss-filter-panel').getBoundingClientRect().bottom,
        top:document.getElementById('ss-scroll').scrollTop,state:GRZSessionStats.getState()};
    },index)));
  }
}
module.exports=async({browser,nativeHost,check})=>{
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2560},
      viewport:{width:3840,height:2560,scale},realTimers:true});
    try{
      await page.evaluate(scale=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        window.__pageJumpSample=JSON.parse(JSON.stringify(scope.battles[0]));
        payload.account_key='synthetic-page-navigation-'+scale;payload.window_size=[900,1000];
        scope.period_id='synthetic-page-navigation-period';scope.data_revision=1;
        scope.pagination={battles:{page:0,pages:3,page_size:40,total:85}};
        scope.ordering={battles:{metric:'off',statistic:'avg',direction:'desc',chronology:'newest'}};
        scope.battles=Array.from({length:40},(_,index)=>({...__pageJumpSample,id:'synthetic-page-navigation-'+index}));
        delete scope.battle_focus;model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },scale);await page.locator('#ss-group-battles').click();await frames(page);
      await page.locator('#ss-page-next').click();await frames(page);
      let sent=await commands(page),request=sent[sent.length-1];
      check('Next owns an asynchronous page-two request at '+scale+'x',request.page==='1'&&!!request.request_id);
      await page.evaluate(()=>{
        window.__pageJumpRect=Element.prototype.getBoundingClientRect;
        Element.prototype.getBoundingClientRect=function(){
          if(this.classList&&this.classList.contains('ss-continuous-page')&&this.getAttribute('data-page-index')==='1')
            return {top:0,bottom:0,left:0,right:0,width:0,height:0};
          return __pageJumpRect.call(this);
        };
      });
      await emit(page,1,request);await page.waitForTimeout(250);
      const before=await page.locator('#ss-scroll').evaluate(node=>node.scrollTop);
      await page.evaluate(()=>{Element.prototype.getBoundingClientRect=__pageJumpRect;});
      await aligned(page,1);
      check('The accepted page scrolls to its divider after geometry becomes available without another UI event at '+scale+'x',
        await page.locator('#ss-scroll').evaluate(node=>node.scrollTop)>before+100*scale);
      await page.waitForTimeout(650);

      const loaded=(await commands(page)).length;
      await page.locator('#ss-page-previous').click();await aligned(page,0);await page.waitForTimeout(650);
      await page.locator('#ss-page-next').click();
      await page.locator('.ss-continuous-page[data-page-index="0"]').evaluate((section,scale)=>{section.style.paddingBottom=240*scale+'px';},scale);
      await aligned(page,1);await page.waitForTimeout(650);
      check('Cached Next follows a delayed preceding-page height change without fetching again at '+scale+'x',
        (await commands(page)).length===loaded);

      // A result can change the data revision during the owned correction.
      // The replacement feed must retain that destination while rebuilding.
      await page.locator('#ss-page-previous').click();await aligned(page,0);await page.waitForTimeout(650);
      await page.evaluate(()=>{
        Element.prototype.getBoundingClientRect=function(){
          if(this.classList&&this.classList.contains('ss-continuous-page')&&this.getAttribute('data-page-index')==='1')
            return {top:0,bottom:0,left:0,right:0,width:0,height:0};
          return __pageJumpRect.call(this);
        };
      });
      await page.locator('#ss-page-next').click();
      await emit(page,1,null,2);sent=await commands(page);request=sent[sent.length-1];
      check('An active page destination survives a same-period revision while the missing prefix reloads at '+scale+'x',
        request.page==='0'&&(await commands(page)).length===loaded+1);
      await page.evaluate(scale=>{
        const style=document.createElement('style');style.textContent='.ss-continuous-page[data-page-index="0"]{padding-bottom:'+300*scale+'px}';
        document.head.appendChild(style);
      },scale);
      await emit(page,0,request);
      await page.evaluate(()=>{Element.prototype.getBoundingClientRect=__pageJumpRect;});
      await aligned(page,1);await page.waitForTimeout(650);
      check('The rebuilt feed still aligns the explicitly requested page at '+scale+'x',
        await page.locator('#ss-page-label').textContent()==='Page 2 of 3');

      // Top is a newer destination even while a cached jump is correcting.
      await page.locator('#ss-page-previous').click();await aligned(page,0);
      await page.locator('#ss-scroll-top').click();await page.waitForTimeout(750);
      check('Back to top retires page retries instead of being pulled back to a divider at '+scale+'x',
        await page.locator('#ss-scroll').evaluate(node=>Math.abs(node.scrollTop)<=1));
    }finally{await page.close();}
  }
};
