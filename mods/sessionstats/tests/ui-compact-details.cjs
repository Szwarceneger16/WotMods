/* Small histories use their rows; rich bonus rows keep real aligned columns. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
function sourceChecks(source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8')) {
  class Node {
    constructor(cls='',text=''){this.className=cls;this.ownText=text;this.children=[];this.style={};this.attrs={};this.parentNode=null;this.scrollTop=0;}
    appendChild(node){this.children.push(node);node.parentNode=this;return node;}
    removeChild(node){this.children.splice(this.children.indexOf(node),1);node.parentNode=null;}
    get firstChild(){return this.children[0] || null;}
    get textContent(){return this.ownText+this.children.map(node=>node.textContent).join('');}
    set textContent(value){this.ownText=String(value);this.children=[];}
    setAttribute(key,value){this.attrs[key]=String(value);}
    removeAttribute(key){delete this.attrs[key];}
    getAttribute(key){return this.attrs[key] || null;}
    getBoundingClientRect(){return {width:this.width || 0};}
    contains(node){return node===this || this.children.some(child=>child.contains(node));}
    querySelectorAll(selector){let result=[];for(const node of this.children){if(node.className.split(/\s+/).includes(selector.slice(1)))result.push(node);result=result.concat(node.querySelectorAll(selector));}return result;}
    querySelector(selector){return this.querySelectorAll(selector)[0] || null;}
  }
  const messages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages.en;
  const append=(parent,node)=>parent.appendChild(node),documentRoot=new Node(),commands=[];
  const state={group:'maps',openMaps:{}},nodes={scroll:new Node()};
  const timers=new Map();let nextTimer=0;
  const context={state,nodes,document:{activeElement:null,documentElement:documentRoot},
    window:{setTimeout(callback){const id=++nextTimer;timers.set(id,callback);return id;},clearTimeout:id=>timers.delete(id)},
    append,element:(tag,cls,text)=>new Node(cls,text),clear:node=>node.children.slice().forEach(child=>node.removeChild(child)),
    t:(key,args=[])=>String(messages[key] || key).replace(/\{(\d+)\}/g,(match,index)=>args[index]===undefined?match:args[index]),
    hasNumber:value=>typeof value==='number' && isFinite(value),integer:value=>String(value),
    signed:value=>value>0?'+'+String(value).replace(/\B(?=(\d{3})+(?!\d))/g,'\u00a0'):String(value),
    rewardTable(parent,cls){return append(append(parent,new Node('ss-more-table '+cls)),new Node('ss-more-body'));},
    rewardRow(){},missionProgress(){},viewContext:()=>({account_key:'synthetic',scope:'launch',period_id:'synthetic-period'}),
    currentScope:()=>({ordering:{maps:{chronology:'newest'},vehicles:{chronology:'newest'}}}),
    getOrder:scope=>scope.ordering[state.group],
    sameContext:()=>true,invoke:(action,args)=>{commands.push({action,...args});return true;},
    pinnedFilterHeight:()=>0,date:()=> '09.11, 18:58',focusControl(){},selectMapBattle(){},invalidateCardFlow(){},queueResize(){}};
  vm.createContext(context);
  function extract(startName,endName){const start=source.indexOf(startName),end=source.indexOf(endName,start);assert(start>=0 && end>start);return source.slice(start,end);}
  vm.runInContext(extract('    function wn8Color(value) {','    function headlineStat(')+
    extract('    function battleOutcome(','    var defaultOrder = ')+
    extract('    function nativeVisualSource(','    function appendBattleMap(')+
    extract('    var bonusLabels = {','    function missionProgress(')+
    extract('    function renderBattleMore(panel, battle) {','    function attachBattleMore(')+
    extract('    function cancelUITimer(','    function retireFeed(')+
    extract('    function attachMapMore(card, header, map) {','    function appendGroupBatch('),context);
  const bonusPanel=new Node();
  context.renderBattleMore(bonusPanel,{details:{bonuses:{eventCredits:12345678,eventCrystal:43,wotPlusCredits:3456,wotPlusXP:64,wotPlusFreeXP:8,wotPlusCrewXP:96},missions:{}}});
  const rows=bonusPanel.querySelectorAll('.ss-bonus-row');
  assert.strictEqual(rows.length,3);
  for(const row of rows){assert.strictEqual(row.children.length,2,'Each source owns its label beside one resource strip');
    assert.strictEqual(row.querySelectorAll('.ss-bonus-number').length,5,'All five resource columns remain present');}
  assert(bonusPanel.textContent.includes('+12\u00a0345\u00a0678'),'Eight-digit credits remain complete');
  const widths=rows.map(row=>row.querySelectorAll('.ss-bonus-number').map(cell=>cell.style.flexBasis));
  assert(widths.every(width=>JSON.stringify(width)===JSON.stringify(widths[0])),'Header and all sources share column widths');
  const compactPanel=new Node();context.renderBattleMore(compactPanel,{details:{bonuses:{eventCredits:240},missions:{}}});
  assert.strictEqual(compactPanel.querySelector('.ss-more-bonus-block').style.width,'308rem','Few-resource bonuses retain their compact baseline');
  const missionPanel=new Node();context.renderBattleMore(missionPanel,{details:{
    bonuses:{eventCredits:12345678,wotPlusCredits:3456,wotPlusXP:64,wotPlusFreeXP:8,wotPlusCrewXP:96},
    missions:{personal:{kind:'personal',name:'Synthetic personal mission with a long objective name',status:'progress'}}}});
  const columns=missionPanel.querySelector('.ss-more-columns'),bonus=columns.querySelector('.ss-more-bonus-block'),missions=columns.querySelector('.ss-more-mission-block');
  assert(columns.className.includes('ss-more-columns-stacked'),'New details are readable before the native layout settles');
  assert.strictEqual(bonus.getAttribute('data-resource-count'),'4','The regression also covers a missing bond column');
  for(const scale of [1,2]) {
    state.nativeScale=scale;
    for(const [available,measured,paired,expected] of [[486,486,false,486],[706,706,true,212],[886,886,true,392],[486,886,false,486],[706,706,true,212]]) {
      columns.width=measured*scale;context.layoutMoreColumns(missionPanel,available);
      assert.strictEqual(columns.className.includes('ss-more-columns-paired'),paired,'Pair only when actual card space fits a readable mission column');
      assert.strictEqual(missions.style.width,expected+'rem','Missions receive explicit usable width, including after a narrow resize');
      assert.strictEqual(missions.style.flex,paired?'0 0 '+expected+'rem':'0 0 auto','Only paired missions use their width as a horizontal flex basis');
      assert.strictEqual(bonus.style.flex,paired?'0 0 486rem':'0 0 auto','Stacked bonuses use content height even under native column flex semantics');
      assert.strictEqual(bonus.style.width,'486rem','A long matrix remains capped instead of stretching with the card');
    }
  }
  for(const group of ['maps','vehicles']) {
    state.group=group;state.openMaps={};const card=append(documentRoot,new Node()),header=append(card,new Node());
    context.attachMapMore(card,header,{id:'synthetic-group'});header.querySelector('.ss-map-more-button').onclick();
    const body=card.querySelector('.ss-history-body'),previous=card.querySelector('.ss-map-page-previous'),next=card.querySelector('.ss-map-page-next');
    const item=index=>({id:'synthetic-'+index,name:'Synthetic Heavy',map:'Lakeville',started_at:1794000000-index*600,outcome:'win',wn8:1700});
    card._ssHistoryUpdate({id:'synthetic-group',battle_list:{page:0,pages:1,total:4,page_size:10,items:Array.from({length:4},(_,index)=>item(index))}});
    assert.strictEqual(body.querySelectorAll('.ss-map-battle-row').length,4);
    assert(body.querySelectorAll('.ss-map-battle-wn8-value').every(node=>node.style.color==='#4c762e'),'Nested history values use the shipped WN8 text palette');
    assert(body.querySelectorAll('.ss-map-battle-wn8-label').every(node=>node.style.textShadow==='none'),'Nested history captions never receive numeric halos');
    assert(body.querySelector('.ss-map-battle-info').querySelector('.ss-map-battle-date'),'Name and date share the same flex identity');
    card._ssHistoryUpdate({id:'synthetic-group',battle_list:{page:0,pages:2,total:13,page_size:10,items:Array.from({length:10},(_,index)=>item(index))}});
    assert.strictEqual(body.querySelectorAll('.ss-map-battle-row').length,10);next.onclick();
    assert.strictEqual(timers.size,1,'Only the latest history request owns a timer');
    card._ssHistoryUpdate({id:'synthetic-group',battle_list:{page:1,pages:2,total:13,page_size:10,items:Array.from({length:3},(_,index)=>item(index+10))}});
    assert.strictEqual(timers.size,0,'Receiving the history page releases its timer');
    assert.strictEqual(card.querySelector('.ss-history-body'),body);assert.strictEqual(card.querySelector('.ss-map-page-previous'),previous);
    assert.strictEqual(card.querySelector('.ss-map-page-next'),next);
    assert.strictEqual(body.querySelectorAll('.ss-map-battle-row').length,3);assert(!previous.disabled && next.disabled);
  }
}
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=6;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  sourceChecks();check('Actual shipped compact-history and bonus-column rendering passes source regressions',true);
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2])for(const group of ['maps','vehicles']) {
    const page=await nativeHost(browser,{initialViewport:{width:4600,height:2400},viewport:{width:4600,height:2400,scale}});
    try {
      await page.evaluate(({group,scale})=>{
        const data=JSON.parse(model.payload),scope=data.scopes.launch,sample=scope[group][0];
        data.account_key='synthetic-compact-history-'+group+'-'+scale;data.window_size=[1400,950];
        sample.id='synthetic-compact-group';sample.battle_list={page:0,pages:1,total:4,page_size:10,
          items:Array.from({length:4},(_,index)=>({id:'compact-'+index,name:'Synthetic Heavy',map:'Lakeville',started_at:1794000000-index*600,outcome:'win',wn8:1700+index}))};
        scope[group]=[sample];scope.pagination[group]={page:0,pages:1,total:1,page_size:40};
        model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();
      },{group,scale});
      await page.locator('#ss-group-'+group).click();await page.locator('.ss-map-more-button').click();await frames(page);
      const layout=await page.locator('.ss-map-battles').evaluate((panel,scale)=>{
        const body=panel.querySelector('.ss-history-body'),rows=[...body.querySelectorAll('.ss-map-battle-row')];
        return {height:body.getBoundingClientRect().height/scale,overflow:getComputedStyle(body).overflowY,
          rows:rows.map(row=>{const name=row.querySelector('.ss-map-battle-name').getBoundingClientRect(),date=row.querySelector('.ss-map-battle-date').getBoundingClientRect();
            return {inline:name.right<=date.left+1 && Math.min(name.bottom,date.bottom)>Math.max(name.top,date.top),
              dateFont:parseFloat(getComputedStyle(row.querySelector('.ss-map-battle-date')).fontSize)/scale};})};
      },scale);
      check('Four '+group+' battles use compact rows with readable inline dates at '+(scale*100)+'%: '+JSON.stringify(layout),
        layout.overflow==='visible' && layout.height>0 && layout.height<240 && layout.rows.length===4 && layout.rows.every(row=>row.inline && row.dateFont>=13));
      const language=group==='maps'?(scale===1?'ru':'fr'):(scale===1?'de':'pl');
      await page.evaluate(({group,scale,language,messages})=>{
        const data=JSON.parse(model.payload),sample=data.scopes.launch[group][0];
        data.account_key+='-wide';data.window_size=[1900,950];data.viewport={width:4600,height:2400,scale};
        data.localization={language,messages};
        sample.battle_list={page:0,pages:2,total:13,page_size:10,
          items:Array.from({length:10},(_,index)=>({id:'compact-'+index,name:'Synthetic Long Vehicle Name '+index,map:'Synthetic Long Map Name '+index,
            started_at:1794000000-index*600,outcome:index%2?'unknown':'win',wn8:1700+index,
            visual:index===0?(group==='vehicles'?{kind:'map',src:'img://gui/maps/icons/map/small/07_lakeville.png'}:
              {kind:'vehicle',src:'img://gui/maps/icons/vehicle/uk-GB31_Conqueror_Gun.png'}):undefined,
            outcome_visual:index<2?{kind:'outcome',src:'img://gui/maps/icons/library/BgBattleResultIconVictory-1.png'}:undefined}))};
        model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();
      },{group,scale,language,messages:languages[language]});
      await page.locator('.ss-map-more-button').click();await frames(page);
      const panel=page.locator('.ss-map-battles');
      const layoutWide=await panel.evaluate((panel,scale)=>{
        const body=panel.querySelector('.ss-history-body'),rows=[...body.querySelectorAll('.ss-map-battle-row')],rects=rows.map(row=>row.getBoundingClientRect());
        const bounds=body.getBoundingClientRect();
        const overflow=[...body.querySelectorAll('.ss-map-battle-name,.ss-map-battle-date,.ss-outcome-label,.ss-map-battle-wn8,.ss-map-battle-open .ss-control-label')].filter(node=>{
          const box=node.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);
          return [...range.getClientRects()].some(text=>text.left<box.left-scale||text.right>box.right+scale||text.top<box.top-scale||text.bottom>box.bottom+scale);
        }).map(node=>node.textContent);
        function above(art,caption){return art.getBoundingClientRect().bottom<=caption.getBoundingClientRect().top+scale;}
        const first=rows[0],name=first.querySelector('.ss-map-battle-name'),outcome=first.querySelector('.ss-outcome-label');
        const images=above(first.querySelector('.ss-group-thumb'),name)&&above(first.querySelector('.ss-outcome-image'),outcome)&&
          !rows[1].querySelector('.ss-group-thumb,.ss-outcome-image')&&!!rows[1].querySelector('.ss-outcome-label').textContent;
        const captionStyle=['fontSize','fontWeight','lineHeight','textAlign'].every(key=>getComputedStyle(name)[key]===getComputedStyle(outcome)[key]);
        window.__wideHistory={body,rows};
        return {width:panel.closest('.ss-group').getBoundingClientRect().width/scale,overflow,images,captionStyle,
          natural:getComputedStyle(body).overflowY==='visible'&&rects.every(rect=>rect.bottom<=bounds.bottom+scale),columns:rows.length===10&&rects.every((b,index)=>index%2===0||
          Math.abs(b.top-rects[index-1].top)<=scale&&rects[index-1].right<b.left&&b.right<=bounds.right),
          chronological:rows.every((row,index)=>row.getAttribute('data-battle-id')==='compact-'+index),
          actions:rows.every((row,index)=>row.querySelector('.ss-map-battle-open').getAttribute('data-battle-id')==='compact-'+index)};
      },scale);
      check('Ultra-wide '+group+' history fits ten ordered battles into five readable rows in '+language+' at '+(scale*100)+'%: '+JSON.stringify(layoutWide),
        layoutWide.columns && layoutWide.chronological && layoutWide.actions && layoutWide.natural &&
        layoutWide.images && layoutWide.captionStyle && !layoutWide.overflow.length);
      await page.setViewportSize({width:1100*scale,height:2400});
      await page.evaluate(scale=>{
        const data=JSON.parse(model.payload);data.viewport.width=1100*scale;
        model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();
      },scale);await frames(page);
      const singleLane=await panel.evaluate((panel,scale)=>{
        const body=panel.querySelector('.ss-history-body'),rows=[...body.querySelectorAll('.ss-map-battle-row')];
        const card=panel.closest('.ss-group');
        return {width:card.getBoundingClientRect().width/scale,oneLane:!document.getElementById('ss-groups').classList.contains('ss-two-columns'),
          retained:body===__wideHistory.body&&rows.length===10&&rows.every((row,index)=>row===__wideHistory.rows[index]),
          pairs:rows.every((row,index)=>index%2===0||Math.abs(row.getBoundingClientRect().top-rows[index-1].getBoundingClientRect().top)<=scale)};
      },scale);
      check('A same-width '+group+' card keeps paired history in one outer lane at '+(scale*100)+'%: '+JSON.stringify(singleLane),
        singleLane.oneLane&&singleLane.retained&&singleLane.pairs&&Math.abs(singleLane.width-layoutWide.width)<=1);
      await page.setViewportSize({width:1400*scale,height:2400});
      await page.evaluate(scale=>{
        const data=JSON.parse(model.payload);data.viewport.width=1400*scale;
        model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();
      },scale);await frames(page);
      check('Narrower '+group+' history restores one column without replacing the open rows at '+(scale*100)+'%',await panel.evaluate(panel=>{
        const body=panel.querySelector('.ss-history-body'),rows=[...body.querySelectorAll('.ss-map-battle-row')];
        return body===__wideHistory.body && rows.length===10 && rows.every((row,index)=>row===__wideHistory.rows[index] &&
          (!index || row.getBoundingClientRect().top>=rows[index-1].getBoundingClientRect().bottom-1));
      }));
    }finally{await page.close();}
  }
  await require('./ui-stat-layout-controls.cjs')({browser,nativeHost,check});
  await require('./ui-battle-table-alignment.cjs')({browser,nativeHost,check});
};
module.exports.sourceChecks=sourceChecks;
if(require.main===module){sourceChecks();console.log('Actual-source compact history, stable paging and complete bonus-column checks passed.');}
