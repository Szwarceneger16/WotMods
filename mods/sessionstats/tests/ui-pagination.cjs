/* Native pages append to one owned feed; controls revisit loaded boundaries. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
function assertPageBoundarySource(source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8')){
  const start=source.indexOf('    function pageBoundary('),end=source.indexOf('\n    function showFeedPending(',start);
  assert(start>=0&&end>start);
  const node=(className,text)=>({className,text,children:[],attributes:{},setAttribute(name,value){this.attributes[name]=String(value);}});
  const context={element:(tag,className,text)=>node(className,text),append:(parent,child)=>{parent.children.push(child);return child;},
    t:(key,args)=>key+(args?args.join('/') : ''),hasNumber:value=>typeof value==='number'&&isFinite(value),date:(value,short)=>'localized:'+value+':'+short,String};
  vm.createContext(context);vm.runInContext(source.slice(start,end),context);
  const feed={group:'battles',pages:3,cache:{0:[{started_at:1900000000}]}};
  let boundary=context.pageBoundary(feed,0,false),caption=boundary.children.find(child=>child.className==='ss-page-first-battle');
  assert(caption&&caption.text==='localized:1900000000:false','The first battle timestamp uses the existing localized full-date formatter');
  assert.strictEqual(boundary.children[1],caption,'The first battle date sits immediately below its page divider');
  assert.strictEqual(caption.attributes['data-started-at'],'1900000000');
  for(const group of ['maps','vehicles','tiers']){feed.group=group;boundary=context.pageBoundary(feed,0,false);
    assert(!boundary.children.some(child=>child.className==='ss-page-first-battle'),'Aggregate pages do not invent a first battle date: '+group);}
  feed.group='battles';feed.cache[0]=[{started_at:null}];boundary=context.pageBoundary(feed,0,false);
  assert(!boundary.children.some(child=>child.className==='ss-page-first-battle'),'Unavailable timestamps do not become invented dates');
  feed.cache[0]=[{started_at:0}];boundary=context.pageBoundary(feed,0,false);
  assert(boundary.children.some(child=>child.className==='ss-page-first-battle'),'A recorded Unix epoch timestamp remains valid');
  boundary=context.pageBoundary(feed,0,true);assert(!boundary.children.some(child=>child.className==='ss-page-first-battle'),'A loading boundary waits for its actual first result');
}
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
const requests=page=>page.evaluate(()=>__grzCommands.filter(item=>item.action==='page'));
async function emit(page,index,request,reverse=false){
  await page.evaluate(({index,request,reverse})=>{const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
    scope.battles=Array.from({length:index===2?5:40},(_,offset)=>{const number=reverse?84-index*40-offset:index*40+offset,item=JSON.parse(JSON.stringify(__feedSample));
      item.id='synthetic-feed-'+number;item.name='Synthetic battle '+number;item.started_at=1900000000-number;return item;});
    if(reverse)scope.ordering.battles.chronology='oldest';
    scope.pagination.battles={page:index,pages:3,page_size:40,total:85};if(request)scope.pagination.battles.request_id=request.request_id;
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  },{index,request,reverse});await frames(page);
}
module.exports=async({browser,nativeHost,check})=>{
  require('./ui-page-jump.cjs').assertPageJumpSource();check('Actual-source page navigation waits for stable native geometry and yields to newer intent',true);
  await require('./ui-page-navigation.cjs')({browser,nativeHost,check});
  assertPageBoundarySource();check('Actual-source page dividers show only known localized first-battle dates',true);
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:3840,height:2560},viewport:{width:3840,height:2560,scale:1}});
  try{
    for(const scale of [1,2])for(const [language,messages]of Object.entries(languages)){
      const label=language+' at'+(scale*100)+'%';
      await page.evaluate(({language,messages,scale})=>{const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        window.__feedSample=JSON.parse(JSON.stringify(scope.battles[0]));payload.account_key='synthetic-feed-'+language+'-'+scale;
        payload.window_size=[900,1000];payload.viewport={width:3840,height:2560,scale};payload.localization={language,messages};
        scope.period_id='synthetic-feed-period';scope.data_revision=1;scope.summary.battles=85;
        scope.pagination={battles:{page:0,pages:3,page_size:40,total:85}};
        scope.ordering={battles:{metric:'off',statistic:'avg',direction:'desc',chronology:'newest'}};delete scope.battle_focus;
        scope.battles=Array.from({length:40},(_,index)=>({...__feedSample,id:'synthetic-feed-'+index,name:'Synthetic battle '+index,started_at:1900000000-index}));
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{language,messages,scale});await emit(page,0);await page.locator('#ss-scope-launch').click();await page.locator('#ss-group-battles').click();await frames(page);
      const pageLabel=index=>messages['page.status'].replace('{0}',String(index)).replace('{1}','3');
      check('Native feed begins with40 rows and one localized boundary: '+label,
        await page.locator('#ss-groups .ss-group').count()===40 && await page.locator('.ss-continuous-page').count()===1 &&
        await page.locator('.ss-page-divider-label').first().textContent()===pageLabel(1));
      check('Page separators use visible native-compatible tiled dashes: '+label,await page.locator('.ss-page-divider').first().evaluate(node=>{
        const style=getComputedStyle(node,':before');return style.backgroundImage.includes('linear-gradient') &&
          style.backgroundRepeat==='repeat-x' && parseFloat(style.height)>0;
      }));
      await page.locator('#ss-scroll').evaluate((node,scale)=>{node.scrollTop=240*scale;node.dispatchEvent(new Event('scroll'));},scale);await frames(page);
      check('The top action is available before fetching an unloaded page: '+label,
        await page.locator('#ss-scroll').evaluate(node=>node.scrollTop)>100*scale && await page.locator('#ss-scroll-top').isVisible());
      const before=(await requests(page)).length;await page.locator('#ss-page-next').click();await frames(page);
      let sent=await requests(page),request=sent[sent.length-1];
      check('Next requests one missing page with complete reply ownership: '+label+': '+JSON.stringify(request),
        sent.length===before+1 && request.scope==='launch' && request.group==='battles' && request.page==='1' &&
        request.period_id==='synthetic-feed-period' && request.account_key==='synthetic-feed-'+language+'-'+scale && !!request.request_id);
      check('Pending append retains existing cards and shows one spinner: '+label,
        await page.locator('#ss-groups .ss-group').count()===40 && await page.locator('#ss-groups .ss-page-spinner:visible').count()===1 &&
        await page.locator('#ss-groups .ss-page-spinner:visible').getAttribute('aria-label')===messages['page.loading']);
      await page.evaluate(()=>{for(let index=0;index<3;index++)document.getElementById('ss-scroll').dispatchEvent(new Event('scroll'));});
      check('Repeated scroll notifications coalesce an outstanding request: '+label,(await requests(page)).length===before+1);
      await page.locator('#ss-scroll-top').click();await frames(page);
      check('Top supersedes a pending Next jump without cancelling its page fetch: '+label,
        await page.locator('#ss-scroll').evaluate(node=>Math.abs(node.scrollTop)<=1) &&
        (await requests(page)).length===before+1 && await page.locator('#ss-groups .ss-page-spinner:visible').count()===1);
      await emit(page,1,request);
      check('A delayed Next reply appends its page without overriding the newer Top action: '+label,
        await page.locator('#ss-scroll').evaluate(node=>Math.abs(node.scrollTop)<=1) &&
        (await requests(page)).length===before+1);
      const ids=await page.locator('#ss-groups .ss-group').evaluateAll(cards=>cards.map(card=>card.dataset.groupId));
      check('Matching page reply appends40 unique rows while retaining page one: '+label+': '+JSON.stringify(ids),
        ids.length===80 && new Set(ids).size===80 && Array.from({length:80},(_,index)=>'synthetic-feed-'+index).every(id=>ids.includes(id)) &&
        await page.locator('.ss-continuous-page').count()===2 && await page.locator('#ss-groups .ss-page-spinner:visible').count()===0);
      check('Loaded dividers retain localized numbering: '+label,(await page.locator('.ss-page-divider-label').allTextContents()).join('|')===[pageLabel(1),pageLabel(2)].join('|'));
      check('Battle pages show the first result timestamp immediately below each localized divider: '+label,
        await page.locator('.ss-page-first-battle').count()===2&&
        await page.locator('.ss-page-first-battle').first().getAttribute('data-started-at')==='1900000000'&&
        await page.locator('.ss-page-first-battle').first().evaluate(node=>node.previousElementSibling.classList.contains('ss-page-divider')&&node.textContent.trim().length>0));
      await page.locator('#ss-page-next').click();await frames(page);
      const loaded=(await requests(page)).length;await page.locator('#ss-page-previous').click();await frames(page);
      const previous=await page.locator('#ss-scroll').evaluate(node=>node.scrollTop);
      await page.locator('#ss-page-next').click();await frames(page);const next=await page.locator('#ss-scroll').evaluate(node=>node.scrollTop);
      check('Previous and Next revisit loaded boundaries without requests or replacement: '+label+': '+JSON.stringify({previous,next}),
        (await requests(page)).length===loaded && next>previous+100*scale && await page.locator('#ss-groups .ss-group').count()===80);
      await page.locator('#ss-scroll').evaluate(node=>{node.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));node.scrollTop=node.scrollHeight;node.dispatchEvent(new Event('scroll'));});await frames(page);
      sent=await requests(page);request=sent[sent.length-1];
      check('The loaded bottom requests exactly the next missing page: '+label+': '+JSON.stringify(request),sent.length===loaded+1 && request.page==='2');
      const beforeAppend=await page.locator('#ss-scroll').evaluate(node=>node.scrollTop);
      await emit(page,2,request);
      check('Automatic append preserves the viewport at the loading boundary: '+label,
        Math.abs(await page.locator('#ss-scroll').evaluate(node=>node.scrollTop)-beforeAppend)<=1);
      check('Final partial reply extends the same feed to85 rows: '+label,
        await page.locator('#ss-groups .ss-group').count()===85 && await page.locator('.ss-continuous-page[data-page-index="2"] .ss-group').count()===5 &&
        await page.locator('#ss-groups .ss-page-spinner:visible').count()===0);
      const beforeFinal=(await requests(page)).length;
      if (await page.locator('#ss-page-next').isEnabled()) { await page.locator('#ss-page-next').click(); }
      await frames(page);
      check('A cached short final page becomes current at the clamped scroll end: '+label,
        await page.locator('#ss-page-next').isDisabled() && await page.locator('#ss-page-label').textContent()===pageLabel(3) &&
        (await requests(page)).length===beforeFinal);
      const pin=await page.evaluate(()=>{const box=document.getElementById('ss-filter-panel').getBoundingClientRect(),viewport=document.getElementById('ss-scroll').getBoundingClientRect();
        return {top:box.top,bottom:box.bottom,viewportTop:viewport.top,viewportBottom:viewport.bottom};});
      check('The complete filter panel stays visible above the appended feed: '+label+': '+JSON.stringify(pin),pin.top>=pin.viewportTop-1 && pin.bottom<=pin.viewportBottom+1);
      if(language==='en' && scale===1){
        const retained=await page.locator('#ss-scroll').evaluate(node=>node.scrollTop);
        await page.locator('#ss-sort-chronology .ss-select-trigger').click();
        await page.locator('#ss-sort-chronology [data-value="oldest"]').click();await emit(page,0,null,true);
        check('Sorting a loaded feed retains all old rows while its replacement prefix is incomplete',
          await page.locator('#ss-groups .ss-group').count()===85 && await page.locator('#ss-groups .ss-group').first().getAttribute('data-group-id')==='synthetic-feed-0');
        sent=await requests(page);request=sent[sent.length-1];
        check('A sorted replacement fetches the next page of the previously loaded window',request.page==='1');
        await emit(page,1,request,true);sent=await requests(page);request=sent[sent.length-1];
        check('A partially rebuilt sorted prefix keeps the complete old feed visible',
          request.page==='2' && await page.locator('#ss-groups .ss-group').count()===85 && await page.locator('#ss-groups .ss-group').first().getAttribute('data-group-id')==='synthetic-feed-0');
        await emit(page,2,request,true);
        const sorted=await page.locator('#ss-groups .ss-group').evaluateAll(cards=>cards.map(card=>card.dataset.groupId));
        const after=await page.locator('#ss-scroll').evaluate(node=>node.scrollTop);
        check('The complete sorted window swaps atomically at the same pixel offset: '+JSON.stringify({retained,after,first:sorted[0],last:sorted[84]}),
          sorted.length===85 && sorted[0]==='synthetic-feed-84' && sorted[84]==='synthetic-feed-0' && Math.abs(after-retained)<=1);
      }
      const count=(await requests(page)).length;await page.locator('#ss-scroll-top').click();await frames(page);
      check('Top restores the complete summary while retaining cached pages: '+label,
        await page.locator('#ss-scroll').evaluate(node=>Math.abs(node.scrollTop)<=1) && await page.locator('#ss-groups .ss-group').count()===85 && (await requests(page)).length===count);
      check('The top action exposes its localized accessible label: '+label,await page.locator('#ss-scroll-top').getAttribute('aria-label')===messages['page.top']);
    }
    await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.account_key='synthetic-feed-cleanup';model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await emit(page,0);
    const before=(await requests(page)).length;await page.evaluate(()=>{const button=document.getElementById('ss-page-next');GRZSessionStats.destroy();button.onclick();
      const scroll=document.getElementById('ss-scroll');scroll.scrollTop=scroll.scrollHeight;scroll.dispatchEvent(new Event('scroll'));});
    check('Retained feed controls and scroll listeners cannot fetch after cleanup',(await requests(page)).length===before);
  }finally{await page.close();}
};
module.exports.assertPageBoundarySource=assertPageBoundarySource;
if(require.main===module){assertPageBoundarySource();console.log('Actual-source page divider timestamp regressions passed.');}
