/* Empty native feeds must stay idempotent across refresh and window reuse. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');

// Exercise the shipped rendering function without requiring a browser process.
// The DOM double models ownership/insertion only; browser QA covers geometry.
function assertEmptyStateSource(source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8')) {
  const start=source.indexOf('    function renderGroups(scope) {');
  const end=source.indexOf('    function pinnedFilterHeight()',start);
  assert(start>=0 && end>start,'The regression must exercise the actual shipped renderGroups function');
  class Node {
    constructor(className='',text=''){this.className=className;this.ownText=text;this.children=[];this.style={};this.attributes={};this.parentNode=null;}
    get firstElementChild(){return this.children[0] || null;}
    get nextElementSibling(){if(!this.parentNode)return null;return this.parentNode.children[this.parentNode.children.indexOf(this)+1] || null;}
    get textContent(){return this.ownText+this.children.map(node=>node.textContent).join('');}
    set textContent(text){this.ownText=String(text);this.children=[];}
    appendChild(node){return this.insertBefore(node,null);}
    insertBefore(node,before){if(node===before)return node;if(node.parentNode)node.parentNode.removeChild(node);
      const index=before===null?this.children.length:this.children.indexOf(before);assert(index>=0);
      this.children.splice(index,0,node);node.parentNode=this;return node;}
    removeChild(node){const index=this.children.indexOf(node);assert(index>=0);this.children.splice(index,1);node.parentNode=null;return node;}
    setAttribute(name,value){this.attributes[name]=String(value);}
    removeAttribute(name){delete this.attributes[name];}
    getBoundingClientRect(){return {height:0};}
    querySelectorAll(selector){const result=[];for(const node of this.children){
      if(node.className.split(/\s+/).includes(selector.slice(1)))result.push(node);
      result.push(...node.querySelectorAll(selector));}return result;}
    querySelector(selector){return this.querySelectorAll(selector)[0] || null;}
  }
  const nodes={groups:new Node(),'list-meta':new Node()},controls={};
  const state={xp:'base',language:'en',appearanceCSS:'',group:'vehicles',list:[],loadedCount:40};
  const feed=()=>({start:0,last:0,current:0,total:0,size:40,pages:1,cache:{0:[]},version:0});
  let currentFeed=feed();
  const append=(parent,node)=>parent.appendChild(node);
  const context={state,nodes,document:{getElementById(id){return controls[id] || (controls[id]=new Node());}},
    prepareFeed:()=>currentFeed,renderSelects(){},t:key=>key,number:String,
    invalidateCardFlow(){},clear:node=>node.children.slice().forEach(child=>node.removeChild(child)),
    stageFeedContext(){},feedContextIdentity:()=>state.group,
    createCardPage(index,items,ownedFeed){
      const section=ownedFeed?append(nodes.groups,new Node('ss-continuous-page')):nodes.groups;
      const columns=append(section,new Node('ss-card-columns'));
      return {index,section,columns,items,cards:[],lanes:[append(columns,new Node()),append(columns,new Node())]};
    },
    appendGroupBatch(count,page){page.cards=page.items.slice(0,count).map(()=>append(page.lanes[0],new Node('ss-group')));
      state.groupCards=state.groupCards.concat(page.cards);},
    append,element:(tag,className,text)=>new Node(className,text),
    showFeedPending(){},updateFeedControls(){},ordered:items=>items,getOrder:()=>({}),layoutBattleCards(){},finishFeedAnchor(){},queueResize(){}};
  vm.createContext(context);vm.runInContext(source.slice(start,end),context);
  const render=()=>context.renderGroups({vehicles:currentFeed ? currentFeed.cache[0] : []});
  const emptyCount=()=>nodes.groups.querySelectorAll('.ss-empty').filter(node=>node.textContent==='groups.empty').length;
  render();assert.strictEqual(emptyCount(),1,'An initially empty native feed has one empty notice');
  for(let index=0;index<8;index++) {
    render();assert.strictEqual(emptyCount(),1,'Repeated native refresh/reselection must not duplicate the empty notice (refresh '+(index+1)+')');
  }
  currentFeed.cache[0]=[{id:'synthetic-battle'}];currentFeed.total=1;currentFeed.version++;
  render();assert.strictEqual(emptyCount(),0,'Newly received results remove the empty notice');
  assert.strictEqual(nodes.groups.querySelectorAll('.ss-group').length,1,'The new result is rendered');
  currentFeed.cache[0]=[];currentFeed.total=0;currentFeed.version++;
  render();render();assert.strictEqual(emptyCount(),1,'Results becoming empty again create only one notice');
  currentFeed=feed();currentFeed.cache={};
  render();assert.strictEqual(emptyCount(),0,'A pending uncached page is not presented as completed empty data');
  currentFeed.cache[0]=[];
  render();render();assert.strictEqual(emptyCount(),1,'A completed empty page creates only one notice after pending data');
  for(const group of ['maps','battles','tiers','vehicles']) {
    state.group=group;currentFeed=feed();render();render();
    assert.strictEqual(emptyCount(),1,'Switching to another empty grouping leaves one notice: '+group);
  }
  currentFeed=null;render();render();assert.strictEqual(emptyCount(),1,'Legacy non-paginated snapshots also keep one notice');
}

module.exports=async({browser,nativeHost,check})=>{
  assertEmptyStateSource();check('Actual-source empty-feed regression passes without browser-specific behavior',true);
  for(const scale of [1,2]) {
    const page=await nativeHost(browser,{initialViewport:{width:1800,height:1400},viewport:{width:1800,height:1400,scale}});
    try {
      await page.evaluate(()=>{
        window.__emptyReady=JSON.parse(model.payload);
        const data=JSON.parse(model.payload);data.loading=false;data.load_error='';
        for(const [name,scope]of Object.entries(data.scopes)) {
          scope.period_id='synthetic-empty-'+name;scope.data_revision='synthetic-empty:0';scope.loading=false;scope.load_error='';scope.pending=0;
          scope.summary={battles:0,observed_battles:0,missing_results:0,partial_results:0,wins:0,losses:0,draws:0};
          scope.pagination={};
          for(const group of ['vehicles','maps','battles','tiers']) {
            scope[group]=[];scope.pagination[group]={page:0,page_size:40,pages:1,total:0};
          }
        }
        window.__emptySnapshot=data;model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();
        window.__emptyBindings={engine:__grzEngineOn.length,callbacks:__grzHelperCalls.callback};
      });
      const oneNotice=async label=>check(label+' at '+(scale*100)+'%',
        await page.locator('#ss-groups .ss-groups-empty').count()===1 && await page.locator('#ss-groups .ss-empty').count()===1 &&
        await page.locator('#ss-groups .ss-group').count()===0);
      await oneNotice('Initially empty Since launch has exactly one empty notice');
      await page.evaluate(()=>{
        for(let index=0;index<6;index++) {
          __grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-group-vehicles').onclick();
          document.getElementById('ss-scope-launch').onclick();
          __grzEvents['viewEnv.onDataChanged']();
        }
      });
      await oneNotice('Repeated native refresh, same-tab clicks and window reuse keep one notice');
      check('Empty rerenders keep the original native subscriptions at '+(scale*100)+'%',await page.evaluate(()=>
        __emptyBindings.engine===__grzEngineOn.length && __emptyBindings.callbacks===__grzHelperCalls.callback));
      for(const group of ['maps','battles','tiers','vehicles']) {
        await page.evaluate(group=>{document.getElementById('ss-group-'+group).onclick();__grzEvents['viewEnv.onDataChanged']();},group);
        await oneNotice('Switching empty grouping to '+group+' keeps one notice');
      }
      await page.evaluate(()=>{document.getElementById('ss-scope-manual').onclick();__grzEvents['viewEnv.onDataChanged']();});
      await oneNotice('Switching the empty period keeps one notice');
      await page.evaluate(()=>{model.payload=JSON.stringify(__emptyReady);__grzEvents['viewEnv.onDataChanged']();});
      check('Received results replace the empty notice at '+(scale*100)+'%',
        await page.locator('#ss-groups .ss-group').count()>0 && await page.locator('#ss-groups .ss-groups-empty').count()===0);
      await page.evaluate(()=>{model.payload=JSON.stringify(__emptySnapshot);__grzEvents['viewEnv.onDataChanged']();__grzEvents['viewEnv.onDataChanged']();});
      await oneNotice('Returning from populated results to empty keeps one notice');
      await page.evaluate(()=>{const data=JSON.parse(model.payload);data.loading=true;model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();});
      check('Loading history removes the completed empty notice at '+(scale*100)+'%',await page.locator('#ss-groups .ss-groups-empty').count()===0);
      await page.evaluate(()=>{model.payload=JSON.stringify(__emptySnapshot);__grzEvents['viewEnv.onDataChanged']();__grzEvents['viewEnv.onDataChanged']();});
      await oneNotice('Completed empty loading restores one notice');
    }finally{await page.close();}
  }
};
module.exports.assertEmptyStateSource=assertEmptyStateSource;
if(require.main===module){assertEmptyStateSource();console.log('Actual-source empty-feed render, refresh, transitions and grouping regressions passed.');}
