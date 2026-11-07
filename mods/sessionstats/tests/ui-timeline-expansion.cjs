/* Independent open panels must retain chronological flow across both lanes. */
module.exports=async function ({browser,nativeHost,check}) {
  const page=await nativeHost(browser,{
    initialViewport:{width:2200,height:1400},viewport:{width:2200,height:1400,scale:1},realTimers:true,
  });
  const opened=new Set();
  const settle=()=>page.evaluate(()=>new Promise(resolve=>{
    let remaining=10;function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
  }));
  const button=id=>page.locator('[data-group-id="'+id+'"] .ss-more-button');
  const publish=fn=>page.evaluate(fn);
  async function layout() {
    return page.locator('#ss-groups').evaluate(groups=>{
      const rect=node=>window.__realExpansionRect.call(node),container=groups.querySelector('.ss-card-columns'),
        columnBox=rect(container),axis=columnBox.left+columnBox.width/2;
      const cards=[...groups.querySelectorAll('.ss-group')].sort((a,b)=>Number(a.dataset.listIndex)-Number(b.dataset.listIndex)).map(node=>{
        const box=rect(node),style=getComputedStyle(node,':before'),right=node.parentNode.classList.contains('ss-card-column-right'),
          side=right ? 'right' : 'left',offset=parseFloat(right ? style.left : style.right),width=parseFloat(style.width),
          connection=right ? box.left+offset : box.right-offset;
        const control=node.querySelector('.ss-more-button'),panel=node.querySelector('.ss-more-panel');
        return {id:node.dataset.groupId,index:Number(node.dataset.listIndex),elementId:node.id,side,
          left:box.left,right:box.right,top:box.top,bottom:box.bottom,height:box.height,
          anchor:box.top+(Number.isFinite(parseFloat(style.top)) ? parseFloat(style.top) : 0),position:getComputedStyle(node).position,
          connected:Number.isFinite(connection) && width>0 && Math.abs(connection-axis)<=2,
          expanded:control && control.getAttribute('aria-expanded')==='true',
          visible:panel && getComputedStyle(panel).display!=='none' && rect(panel).height>0,
          pos:Number(node.getAttribute('aria-posinset')),size:Number(node.getAttribute('aria-setsize'))};
      });
      const payload=JSON.parse(model.payload),panel=rect(document.getElementById('grz-session-stats'));
      return {two:groups.classList.contains('ss-two-columns'),cards,
        geometry:{panel:{width:panel.width,height:panel.height},browserViewport:{width:window.innerWidth,height:window.innerHeight},
          modelViewport:payload.viewport,logicalPreference:payload.window_size,nativeSize:window.__nativeSize},
        owns:(groups.getAttribute('aria-owns') || '').split(/\s+/).filter(Boolean),
        lanes:[...groups.querySelectorAll('.ss-card-column')].map(lane=>[...lane.children].map(card=>Number(card.dataset.listIndex))),
        expected:payload.scopes.timeline.battles.map(card=>String(card.id))};
    });
  }
  async function verify(context,options={}) {
    const value=await layout(),cards=value.cards;
    const chronological=cards.every((card,index)=>!index || card.anchor>=cards[index-1].anchor-1);
    const noOverlap=cards.every((card,index)=>cards.slice(index+1).every(other=>
      Math.min(card.right,other.right)-Math.max(card.left,other.left)<=1 ||
      Math.min(card.bottom,other.bottom)-Math.max(card.top,other.top)<=1));
    const states=cards.every(card=>!!card.expanded===opened.has(card.id) && !!card.visible===opened.has(card.id));
    const order=cards.every((card,index)=>card.index===index && card.id===value.expected[index] && card.pos===index+1 && card.size===value.expected.length);
    const aria=value.owns.join('|')===cards.map(card=>card.elementId).join('|');
    const lanes=value.lanes.every(lane=>lane.every((index,position)=>!position || index>lane[position-1]));
    const connections=!value.two || cards.every(card=>card.connected);
    const valid=chronological && noOverlap && states && order && aria && lanes && connections && cards.every(card=>card.position!=='absolute');
    check('Expanded timeline preserves state, chronology, connectors and native flow: '+context+
      (valid ? '' : ' '+JSON.stringify({chronological,noOverlap,states,order,aria,lanes,connections,cards})),valid);
    if(options.two!==undefined) check('Timeline has the expected column count: '+context+
      (value.two===options.two ? '' : ' '+JSON.stringify({expected:options.two,actual:value.two,...value.geometry})),value.two===options.two);
    return value;
  }
  async function open(id) {
    if(await button(id).getAttribute('aria-expanded')!=='true') await button(id).click();
    opened.add(id);await settle();return verify('opening '+id,{two:true});
  }
  try {
    await page.evaluate(()=>{
      window.__realExpansionRect=Element.prototype.getBoundingClientRect;
      window.__staleExpansionReads=0;window.__staleExpansionUsed=0;
      window.__expansionReadsAfterDestroy=0;window.__expansionAfterDestroy=false;
      Element.prototype.getBoundingClientRect=function () {
        const box=__realExpansionRect.call(this);
        if(this.classList.contains('ss-group') && __expansionAfterDestroy) __expansionReadsAfterDestroy++;
        if(this.classList.contains('ss-group') && __staleExpansionReads>0) {
          __staleExpansionReads--;__staleExpansionUsed++;
          return {x:box.x,y:box.y,left:box.left,right:box.right,top:box.top,bottom:box.top+1,width:box.width,height:1};
        }
        return box;
      };
      const payload=JSON.parse(model.payload);payload.account_key='synthetic-expansion-account';payload.window_size=[1500,1120];
      payload.localization={language:'en',messages:{}};
      const timeline=payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual)),sample=timeline.battles[0];
      timeline.period_id='synthetic-expansion-period';timeline.from_point=timeline.to_point='';timeline.time_points=[];
      timeline.battles=Array.from({length:24},(_,index)=>{
        const card=JSON.parse(JSON.stringify(sample));card.id='expansion-'+String(index).padStart(2,'0');
        card.name='Synthetic tank '+index;card.map='Synthetic map';card.started_at=1900000000-index*100;
        card.details={pass_points:{credited:25,battle:5,missions:20},bonuses:{wotPlusCredits:3456,wotPlusXP:64,wotPlusFreeXP:8,wotPlusCrewXP:96},missions:{}};
        const count=index===0 ? 7 : index===1 ? 4 : 1+index%2;
        for(let mission=0;mission<count;mission++) card.details.missions['daily:'+mission]={kind:'daily',name:'Synthetic objective '+mission,status:'completed',
          description:'Complete this synthetic objective and return to the garage. '.repeat(1+index%2)};
        return card;
      });
      timeline.pagination={battles:{page:0,page_size:24,total:48,pages:2}};
      timeline.ordering={battles:{metric:'off',statistic:'avg',direction:'desc',chronology:'newest'}};
      payload.scopes.launch=JSON.parse(JSON.stringify(timeline));payload.scopes.launch.period_id='synthetic-launch-period';
      window.__expansionOriginalRows=JSON.parse(JSON.stringify(timeline.battles));
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });
    await page.locator('#ss-scope-manual').click();await page.locator('#ss-group-battles').click();await settle();
    let value=await verify('24 collapsed cards',{two:true});
    check('Collapsed timeline retains alternating lanes',value.cards.every((card,index)=>card.side===(index%2 ? 'right' : 'left')));
    await page.evaluate(()=>{__staleExpansionReads=2;});
    await open('expansion-00');
    value=await open('expansion-01');
    check('Deferred flow retries replace transient positive stale measurements',await page.evaluate(()=>__staleExpansionUsed===2));
    check('Tall expanded cards place consecutive later results in the opposite lane',
      value.cards.some((card,index)=>index>1 && card.side===value.cards[index-1].side));
    let last=1;
    for(const side of ['left','right','left','right']) {
      value=await layout();
      const candidate=value.cards.find(card=>card.index>last && card.side===side && !opened.has(card.id));
      check('A later '+side+' card is available for independent expansion',!!candidate);
      last=candidate.index;await open(candidate.id);
    }
    value=await layout();
    check('Several panels stay independently expanded in both lanes',
      ['left','right'].every(side=>value.cards.filter(card=>card.side===side && card.expanded).length>=2));
    const tail=value.cards.slice(-4);
    check('Short trailing cards resume alternating after expanded-height differences settle',
      tail.every(card=>!card.expanded) && tail.every((card,index)=>!index || card.side!==tail[index-1].side));
    const focus=value.cards.find(card=>!card.expanded && card.index>last);
    check('A lower card is available for focus preservation',!!focus);
    await open(focus.id);
    check('Moving expanded cards retains focus on the activated More control',await button(focus.id).evaluate(node=>document.activeElement===node));

    const closing=[...opened][2];
    await page.evaluate(()=>{window.__savedExpansionRAF=window.requestAnimationFrame;window.requestAnimationFrame=undefined;});
    await button(closing).evaluate(node=>node.click());opened.delete(closing);
    await page.waitForTimeout(180);
    await page.evaluate(()=>{window.requestAnimationFrame=window.__savedExpansionRAF;});
    await verify('closing one panel without requestAnimationFrame',{two:true});
    await publish(()=>{__grzEvents['viewEnv.onDataChanged']();});await settle();await verify('same-data refresh');

    for(const width of [800,1500,800,1500]) {
      await page.setViewportSize({width,height:1400});
      await page.evaluate(width=>{
        const payload=JSON.parse(model.payload);payload.viewport.width=width;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },width);await settle();await verify('window width '+width,{two:width===1500});
    }
    await page.locator('#ss-group-vehicles').click();await settle();
    await page.locator('#ss-group-battles').click();await settle();await verify('group away and back');
    await page.locator('#ss-scope-launch').click();await settle();await verify('another scope containing the same battle IDs');
    await page.locator('#ss-scope-manual').click();await settle();await verify('timeline scope restored');

    await page.locator('#ss-sort-chronology [role=combobox]').click();
    await page.locator('#ss-sort-chronology [data-value="oldest"]').click();
    await publish(()=>{
      const command=__grzCommands.filter(item=>item.action==='sort').pop(),payload=JSON.parse(model.payload),scope=payload.scopes.timeline;
      scope.ordering.battles={metric:command.metric,statistic:command.statistic,direction:command.direction,chronology:command.chronology};
      scope.battles.reverse();model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });await settle();await verify('native chronology order changes without losing open IDs');
    await page.locator('#ss-page-next').click();
    await publish(()=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.timeline;
      window.__expansionPageZero=JSON.parse(JSON.stringify(scope.battles));
      scope.pagination.battles.page=1;scope.battles=scope.battles.map(card=>({...card,id:'other-page-'+card.id}));
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });await settle();await verify('different page IDs remain closed');
    await page.locator('#ss-page-previous').click();
    await publish(()=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.timeline;
      scope.pagination.battles.page=0;scope.battles=__expansionPageZero;
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });await settle();await verify('returning to a page restores each open battle');
    await publish(()=>{
      const payload=JSON.parse(model.payload);payload.account_key='another-synthetic-account';
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });opened.clear();await settle();await verify('account switch clears all opened IDs');

    await publish(()=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.timeline;
      scope.battles=Array.from({length:52},(_,index)=>({...__expansionOriginalRows[index%24],id:'append-'+String(index).padStart(2,'0'),started_at:1900000000-index}));
      scope.pagination.battles={page:0,page_size:52,total:52,pages:1};
      scope.ordering.battles.chronology='newest';model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });await settle();
    check('Long expanded history still starts with one bounded batch',await page.locator('#ss-groups .ss-group').count()===40);
    await open('append-00');await open('append-01');
    await page.locator('#ss-scroll').evaluate(node=>{node.scrollTop=node.scrollHeight;node.dispatchEvent(new Event('scroll'));});
    await page.waitForFunction(()=>document.querySelectorAll('#ss-groups .ss-group').length===52);
    await settle();value=await verify('appending a later batch retains chronological flow and open IDs');
    check('Every appended battle appears once',value.cards.length===52 && new Set(value.cards.map(card=>card.id)).size===52);
    await page.evaluate(()=>{
      document.querySelector('[data-group-id="append-02"] .ss-more-button').click();
      GRZSessionStats.destroy();__expansionAfterDestroy=true;
      window.__expansionBeforeCleanup={resize:__grzHelperCalls.resize,html:document.getElementById('ss-groups').innerHTML};
    });
    await page.waitForTimeout(180);
    check('Queued card layout is inert after teardown',await page.evaluate(()=>
      __expansionReadsAfterDestroy===0 && __grzHelperCalls.resize===__expansionBeforeCleanup.resize &&
      document.getElementById('ss-groups').innerHTML===__expansionBeforeCleanup.html));
  } finally {await page.close();}
};
