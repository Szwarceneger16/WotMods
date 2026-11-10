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
    getAttribute(key){return this.attrs[key] || null;}
    contains(node){return node===this || this.children.some(child=>child.contains(node));}
    querySelectorAll(selector){let result=[];for(const node of this.children){if(node.className.split(/\s+/).includes(selector.slice(1)))result.push(node);result=result.concat(node.querySelectorAll(selector));}return result;}
    querySelector(selector){return this.querySelectorAll(selector)[0] || null;}
  }
  const messages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages.en;
  const append=(parent,node)=>parent.appendChild(node),documentRoot=new Node(),commands=[];
  const state={group:'maps',openMaps:{}},nodes={scroll:new Node()};
  const context={state,nodes,document:{activeElement:null,documentElement:documentRoot},
    append,element:(tag,cls,text)=>new Node(cls,text),clear:node=>node.children.slice().forEach(child=>node.removeChild(child)),
    t:(key,args=[])=>String(messages[key] || key).replace(/\{(\d+)\}/g,(match,index)=>args[index]===undefined?match:args[index]),
    hasNumber:value=>typeof value==='number' && isFinite(value),integer:value=>String(value),
    signed:value=>value>0?'+'+String(value).replace(/\B(?=(\d{3})+(?!\d))/g,'\u00a0'):String(value),
    rewardTable(parent,cls){return append(append(parent,new Node('ss-more-table '+cls)),new Node('ss-more-body'));},
    rewardRow(){},missionProgress(){},viewContext:()=>({account_key:'synthetic',scope:'launch',period_id:'synthetic-period'}),
    sameContext:()=>true,invoke:(action,args)=>{commands.push({action,...args});return true;},
    battleOutcome:outcome=>outcome,date:()=> '09.11, 18:58',focusControl(){},selectMapBattle(){},invalidateCardFlow(){},queueResize(){}};
  vm.createContext(context);
  function extract(startName,endName){const start=source.indexOf(startName),end=source.indexOf(endName,start);assert(start>=0 && end>start);return source.slice(start,end);}
  vm.runInContext(extract('    var bonusLabels = {','    function missionProgress(')+
    extract('    function renderBattleMore(panel, battle) {','    function attachBattleMore(')+
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
  for(const group of ['maps','vehicles']) {
    state.group=group;state.openMaps={};const card=append(documentRoot,new Node()),header=append(card,new Node());
    context.attachMapMore(card,header,{id:'synthetic-group'});header.querySelector('.ss-map-more-button').onclick();
    const body=card.querySelector('.ss-history-body'),previous=card.querySelector('.ss-map-page-previous'),next=card.querySelector('.ss-map-page-next');
    assert(body.className.includes('ss-history-paged'),'Unknown history preserves the paging reservation');
    const item=index=>({id:'synthetic-'+index,name:'Synthetic Heavy',map:'Lakeville',started_at:1794000000-index*600,outcome:'win',wn8:1700});
    card._ssHistoryUpdate({id:'synthetic-group',battle_list:{page:0,pages:1,total:4,page_size:10,items:Array.from({length:4},(_,index)=>item(index))}});
    assert(!body.className.includes('ss-history-paged'),'A known short single page releases the fixed viewport');
    assert.strictEqual(body.querySelectorAll('.ss-map-battle-row').length,4);
    assert(body.querySelector('.ss-map-battle-info').querySelector('.ss-map-battle-date'),'Name and date share the same flex identity');
    card._ssHistoryUpdate({id:'synthetic-group',battle_list:{page:0,pages:2,total:13,page_size:10,items:Array.from({length:10},(_,index)=>item(index))}});
    assert(body.className.includes('ss-history-paged'),'A multi-page history reserves its stable viewport');next.onclick();
    card._ssHistoryUpdate({id:'synthetic-group',battle_list:{page:1,pages:2,total:13,page_size:10,items:Array.from({length:3},(_,index)=>item(index+10))}});
    assert.strictEqual(card.querySelector('.ss-history-body'),body);assert.strictEqual(card.querySelector('.ss-map-page-previous'),previous);
    assert.strictEqual(card.querySelector('.ss-map-page-next'),next);assert(body.className.includes('ss-history-paged'),'A partial last page keeps its reserved height');
    assert.strictEqual(body.querySelectorAll('.ss-map-battle-row').length,3);assert(!previous.disabled && next.disabled);
  }
}
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=6;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  sourceChecks();check('Actual shipped compact-history and bonus-column rendering passes source regressions',true);
  for(const scale of [1,2])for(const group of ['maps','vehicles']) {
    const page=await nativeHost(browser,{initialViewport:{width:3000,height:2200},viewport:{width:3000,height:2200,scale}});
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
        return {height:body.getBoundingClientRect().height/scale,paged:body.classList.contains('ss-history-paged'),
          rows:rows.map(row=>{const name=row.querySelector('.ss-map-battle-name').getBoundingClientRect(),date=row.querySelector('.ss-map-battle-date').getBoundingClientRect();
            return {inline:name.right<=date.left+1 && Math.min(name.bottom,date.bottom)>Math.max(name.top,date.top),
              dateFont:parseFloat(getComputedStyle(row.querySelector('.ss-map-battle-date')).fontSize)/scale};})};
      },scale);
      check('Four '+group+' battles use compact rows with readable inline dates at '+(scale*100)+'%: '+JSON.stringify(layout),
        !layout.paged && layout.height>0 && layout.height<240 && layout.rows.length===4 && layout.rows.every(row=>row.inline && row.dateFont>=13));
    }finally{await page.close();}
  }
};
module.exports.sourceChecks=sourceChecks;
if(require.main===module){sourceChecks();console.log('Actual-source compact history, stable paging and complete bonus-column checks passed.');}
