/* The selected battle has a textual cue even without decorative frame paint. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
function assertSelectedBattleSource(source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8')) {
  function extract(name){const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }',start)+6;
    assert(start>=0&&end>start,'Exercise actual shipped '+name);return source.slice(start,end);}
  class Node {
    constructor(tag='div',className='',text=''){this.tagName=tag.toUpperCase();this.className=className;this.textContent=text;this.children=[];this.attributes={};this.parentNode=null;this.id='';
      this.classList={add:name=>this.setClass(name,true),remove:name=>this.setClass(name,false),contains:name=>this.className.split(/\s+/).includes(name)};}
    setClass(name,on){const names=new Set(this.className.split(/\s+/).filter(Boolean));on?names.add(name):names.delete(name);this.className=[...names].join(' ');}
    get firstChild(){return this.children[0]||null;}
    appendChild(node){return this.insertBefore(node,null);}
    insertBefore(node,before){if(node.parentNode)node.parentNode.removeChild(node);const index=before?this.children.indexOf(before):this.children.length;assert(index>=0);this.children.splice(index,0,node);node.parentNode=this;return node;}
    removeChild(node){const index=this.children.indexOf(node);assert(index>=0);this.children.splice(index,1);node.parentNode=null;return node;}
    contains(node){return node===this||this.children.some(child=>child.contains(node));}
    setAttribute(name,value){this.attributes[name]=String(value);}
    getAttribute(name){return Object.prototype.hasOwnProperty.call(this.attributes,name)?this.attributes[name]:null;}
    removeAttribute(name){delete this.attributes[name];}
    querySelectorAll(selector){return this.children.flatMap(child=>(child.classList.contains(selector.slice(1))?[child]:[]).concat(child.querySelectorAll(selector)));}
    querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  }
  const card=new Node('div','ss-group ss-battle'),neighbor=new Node('div','ss-group ss-battle');
  card.id='synthetic-selected';card.setAttribute('data-group-id','selected');neighbor.setAttribute('data-group-id','neighbor');
  const more=card.appendChild(new Node('button','ss-more-button','More'));
  const state={highlightedBattle:{id:'selected',context:{},until:Number.MAX_SAFE_INTEGER},targetSequence:1,targetTimer:123,groupCards:[card,neighbor]};
  let layoutChanges=0;
  const context={state,Date,sameContext:()=>true,t:key=>key==='battle.selected'?'Selected battle':key,
    element:(tag,className,text)=>new Node(tag,className,text),append:(parent,node)=>parent.appendChild(node),
    cancelUITimer(){},invalidateCardFlow(){layoutChanges++;},queueResize(){}};
  vm.createContext(context);vm.runInContext(['clearBattleTarget','paintBattleTarget','targetClick'].map(extract).join('\n'),context);
  context.paintBattleTarget(card);context.paintBattleTarget(card);context.paintBattleTarget(neighbor);
  assert.strictEqual(card.querySelectorAll('.ss-battle-selection-banner').length,1,'Repeated paints retain one selected-battle banner');
  const banner=card.querySelector('.ss-battle-selection-banner');
  assert.strictEqual(banner.textContent,'Selected battle','Selection has an explicit text label');
  assert.strictEqual(card.getAttribute('aria-describedby'),banner.id,'The selected card describes its cue accessibly');
  assert.strictEqual(neighbor.querySelector('.ss-battle-selection-banner'),null,'Only the exact selected battle is marked');
  const outline=card.querySelector('.ss-battle-target-outline');card.removeChild(outline);
  assert.strictEqual(card.firstChild,banner,'Missing decorative outline cannot remove the visible textual cue');
  context.targetClick({target:more});assert.strictEqual(card.firstChild,banner,'More inside the selected card preserves its cue');
  context.paintBattleTarget(card);assert.strictEqual(card.querySelectorAll('.ss-battle-selection-banner').length,1);
  context.targetClick({target:new Node('button')});
  assert.strictEqual(card.querySelector('.ss-battle-selection-banner'),null,'An explicit outside click dismisses its text cue');
  assert.strictEqual(card.querySelector('.ss-battle-target-outline'),null);
  assert.strictEqual(card.getAttribute('aria-describedby'),null,'Dismissal removes only the owned description');
  assert.strictEqual(state.highlightedBattle,null);assert.strictEqual(layoutChanges,0,'Removing selection overlays does not invalidate card heights or lane layout');
}
module.exports={assertSelectedBattleSource};
if(require.main===module){assertSelectedBattleSource();console.log('Actual-source selected-battle text, exact identity, More and dismissal regressions passed.');}
