/* WoT-Life WN8 swatches color rating text, without coloring a cell's fill. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(__dirname,'..');
const read=name=>fs.readFileSync(path.join(root,'ui',name),'utf8');
const bands=[[0,'#000000'],[300,'#cd3333'],[600,'#d77900'],[900,'#d7b600'],[1250,'#6d9521'],
  [1600,'#4c762e'],[1900,'#4a92b7'],[2350,'#83579d'],[2900,'#5a3175']];
function hasBlackOutline(shadow){
  const parts=String(shadow).split(/,(?![^()]*\))/),directions=[];
  if(parts.length!==4)return false;
  for(const part of parts){
    if(!/rgba\(224,\s*216,\s*191,\s*0\.85\)/.test(part))return false;
    const offsets=part.replace(/rgba\([^)]+\)/,'').match(/-?\d+(?:\.\d+)?(?:px|rem)?/g)||[];
    const values=offsets.map(parseFloat);
    if(values.length!==3||values[2]!==0||Math.abs(values[0])+Math.abs(values[1])!==0.75)return false;
    directions.push(values.slice(0,2).join(','));
  }
  return new Set(directions).size===4;
}
function sourceFunction(source,name){const start=source.indexOf('    function '+name+'('),line=source.indexOf('\n',start);
  const end=source.slice(start,line).endsWith('}')?line:source.indexOf('\n    }\n',start)+7;
  assert(start>=0&&end>start,'Exercise actual shipped '+name);return source.slice(start,end);}
function assertWN8Source(){
  class Node{constructor(tag,cls,text){this.tagName=tag;this.className=cls||'';this.textContent=text;this.children=[];this.style={};this.attributes={};}
    appendChild(child){child.parentNode=this;this.children.push(child);return child;}
    removeChild(child){this.children.splice(this.children.indexOf(child),1);child.parentNode=null;return child;}
    querySelector(selector){return this.children.find(child=>child.className.split(/\s+/).includes(selector.slice(1)))||null;}
    setAttribute(key,value){this.attributes[key]=String(value);}removeAttribute(key){delete this.attributes[key];}}
  let panel;
  for(const file of ['session_stats.js','postbattle.js']){
    const context={};vm.createContext(context);vm.runInContext(['wn8Color','paintWN8','paintWN8Caption'].map(name=>sourceFunction(read(file),name)).join('\n'),context);
    for(let index=0;index<bands.length;index++){
      const [minimum,color]=bands[index];assert.strictEqual(context.wn8Color(minimum),color,file+' lower boundary '+minimum);
      if(index)assert.strictEqual(context.wn8Color(minimum-1),bands[index-1][1],file+' previous band '+minimum);
      const node=new Node('span');context.paintWN8(node,minimum);assert.strictEqual(node.style.color,color);
      if(color==='#000000')assert(hasBlackOutline(node.style.textShadow),file+' gives black ink a fine zero-blur light outline');
      else assert.strictEqual(node.style.textShadow,'0 0 0.7rem rgba(212,204,176,0.35)',file+' keeps colored rating halos unchanged');
      assert.strictEqual(node.attributes['data-wn8-value'],String(minimum));
      assert(!Object.keys(node.style).some(key=>/background|border|padding|width|height/i.test(key)),'Rating paint cannot change fill or geometry');
      const caption=new Node('span');context.paintWN8(caption,0);context.paintWN8Caption(caption,minimum);
      assert.strictEqual(caption.style.color,color==='#000000'?'':color,file+' black captions use their configured label color');
      assert.strictEqual(caption.style.textShadow,'none',file+' captions never inherit a numeric halo');
      assert.strictEqual(caption.attributes['data-wn8-caption-value'],String(minimum));
      assert.strictEqual(caption.attributes['data-wn8-value'],undefined,'A caption is not a rating figure');
      context.paintWN8Caption(caption,null);assert.strictEqual(caption.style.color,'');assert.strictEqual(caption.style.textShadow,'none');
      assert.strictEqual(caption.attributes['data-wn8-caption-value'],undefined,'Unknown captions retire an earlier rating color');
      context.paintWN8(node,null);assert.strictEqual(node.style.color,'');assert.strictEqual(node.style.textShadow,'');
      assert.strictEqual(node.attributes['data-wn8-value'],undefined,'Unavailable results retire a previous rating color');
    }
    for(const value of [null,undefined,NaN,Infinity,-1,true,'1600'])assert.strictEqual(context.wn8Color(value),null,file+' rejects nonratings');
    assert.strictEqual(context.wn8Color(299.49),'#000000');assert.strictEqual(context.wn8Color(299.5),'#cd3333','Color follows the rounded displayed WN8');
    const correction=new Node('span');
    for(const value of [0,245,299.49]){context.paintWN8(correction,value);assert(hasBlackOutline(correction.style.textShadow),file+' outlines small black values including '+value);}
    context.paintWN8(correction,299.5);assert.strictEqual(correction.style.textShadow,'0 0 0.7rem rgba(212,204,176,0.35)',file+' retires the outline at the displayed red boundary');
    context.paintWN8(correction,0);context.paintWN8(correction,null);assert.strictEqual(correction.style.textShadow,'',file+' clears a stale black outline for unknown results');
    assert.strictEqual(context.wn8Color(2899.5),'#5a3175');
    if(file==='session_stats.js')panel=context;
  }
  Object.assign(panel,{append:(parent,child)=>parent.appendChild(child),element:(tag,cls,text)=>new Node(tag,cls,text),
    integer:value=>String(Math.round(value)),number:String,coverage:()=>null,explainCoverage(){}});
  vm.runInContext(['headlineStat','measureRow','battleMeasure','paintWN8Card'].map(name=>sourceFunction(read('session_stats.js'),name)).join('\n'),panel);
  const parent=new Node('div'),headline=panel.headlineStat(parent,'WN8','1 550',true,true,1550);
  assert(headline.children.every(node=>node.style.color==='#6d9521'),'The WN8 headline label and value share the rating color');
  panel.measureRow(parent,'WN8',{count:3,min:250,avg:1600,max:3000},true,3,false);
  const row=parent.children[1],label=row.children[0].children[0];
  assert.strictEqual(label.style.color,undefined,'A shared Min/Avg/Max WN8 label retains its neutral configured color');
  assert.strictEqual(label.attributes['data-wn8-value'],undefined,'A distribution label cannot imply one of its several rating values');
  assert.deepStrictEqual(row.children.slice(1).map(node=>node.style.color),['#000000','#4c762e','#5a3175'],'Min/Avg/Max retain their individual rating colors');
  panel.battleMeasure(parent,'WN8',2380,true);assert(parent.children[2].children.every(node=>node.style.color==='#83579d'));
  panel.battleMeasure(parent,'Base XP',2380,false);assert(parent.children[3].children.every(node=>node.style.color===undefined),'Other statistics retain their configured text colors');
  const card=new Node('div','ss-group');panel.paintWN8Card(card,1600);
  assert.strictEqual(card.children.length,1);assert.strictEqual(card.children[0].style.borderColor,'rgba(76,118,46,0.22)');
  assert.strictEqual(card.children[0].attributes['aria-hidden'],'true');assert.deepStrictEqual(card.style,{},'Rating border cannot mutate card dimensions or padding');
  panel.paintWN8Card(card,0);assert.strictEqual(card.children.length,1,'Rating corrections reuse one owned border');
  assert.strictEqual(card.children[0].style.borderColor,'rgba(0,0,0,0.22)','Zero retains its own rating tint');
  panel.paintWN8Card(card,null);assert.strictEqual(card.children.length,0);assert.strictEqual(card.attributes['data-wn8-border-value'],undefined,'Unknown ratings retire a stale card border');
}
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  assertWN8Source();check('Actual-source WN8 palette boundaries, rounding, unknown states and label/value rendering pass',true);
  const page=await nativeHost(browser,{initialViewport:{width:2200,height:1300},viewport:{width:2200,height:1300,scale:1}});
  try{
    await page.evaluate(bands=>{const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
      payload.window_size=[1800,1100];scope.summary.wn8=2450;
      scope.summary.battle_wn8={count:3,min:299.4,avg:899.5,max:2899.5,sum:4098.4};
      for(const group of ['vehicles','maps','tiers','battles'])for(const item of scope[group]){
        item.stats.wn8=1599.5;item.stats.wn8_count=1;
        item.stats.battle_wn8={count:3,min:299.4,avg:899.5,max:2899.5,sum:4098.4};
        item.sort_value=2450;
        if(group==='maps'||group==='vehicles')item.battle_list={page:0,pages:1,total:bands.length,page_size:10,
          items:bands.map(([value],index)=>({id:'synthetic-color-history-'+index,name:'Synthetic tank '+index,map:'Synthetic map',
            started_at:1700000000-index,wn8:value,outcome:'win'}))};
      }
      scope.ordering=scope.ordering||{};
      for(const group of ['vehicles','maps','tiers'])scope.ordering[group]={metric:'battle_wn8',statistic:'avg',direction:'desc',chronology:'newest'};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    },bands);
    for(const group of ['vehicles','maps','tiers','battles']){
      await page.locator('#ss-group-'+group).click();await frames(page);
      if(group==='vehicles'||group==='maps'){await page.locator('.ss-map-more-button').first().click();await frames(page);}
      const audit=await page.evaluate(()=>[...document.querySelectorAll('[data-wn8-value]')].map(node=>{
        const css=getComputedStyle(node);return {value:Number(node.dataset.wn8Value),color:css.color,background:css.backgroundColor,halo:css.textShadow,
          tag:node.className,styleBackground:node.style.background};}));
      const rgb={0:'rgb(0, 0, 0)',300:'rgb(205, 51, 51)',600:'rgb(215, 121, 0)',900:'rgb(215, 182, 0)',
        1250:'rgb(109, 149, 33)',1600:'rgb(76, 118, 46)',1900:'rgb(74, 146, 183)',2350:'rgb(131, 87, 157)',
        2450:'rgb(131, 87, 157)',299:'rgb(0, 0, 0)',2900:'rgb(90, 49, 117)'};
      check('Single-value WN8 labels, headlines and distribution values use exact text-only colors in '+group+': '+JSON.stringify(audit),
        audit.length>3&&audit.every(item=>rgb[item.value]===item.color&&item.styleBackground===''&&
          (item.value<300?hasBlackOutline(item.halo):item.halo.includes('0.35'))));
      check('All WN8 captions, including coverage and nested histories, remain free of numeric halos in '+group,
        await page.locator('[data-wn8-caption-value]').evaluateAll(nodes=>nodes.length>0&&nodes.every(node=>{
          const css=getComputedStyle(node),black=Number(node.getAttribute('data-wn8-caption-value'))<300;
          return css.textShadow==='none'&&!node.hasAttribute('data-wn8-value')&&
            (!black||(node.style.color===''&&css.color!=='rgb(0, 0, 0)'));
        })));
      check('Shared distribution WN8 labels retain neutral configured paint in '+group,await page.locator('.ss-performance .ss-metric-row:last-child .ss-metric-name .ss-cell-value').evaluateAll(nodes=>
        nodes.length>0 && nodes.every(node=>!node.hasAttribute('data-wn8-value') && node.style.color==='' && node.style.textShadow==='')));
      check('Black WN8 has a visible crisp edge without changing text bounds in '+group,await page.locator('[data-wn8-value="299"]').first().evaluate(node=>{
        const before=node.getBoundingClientRect(),shadow=node.style.textShadow;node.style.textShadow='none';
        const after=node.getBoundingClientRect();node.style.textShadow=shadow;
        return before.width===after.width&&before.height===after.height;
      }));
      check('The visible WN8 label carries the same color as its headline value in '+group,
        await page.locator('.ss-headline .ss-kpi').last().evaluate(node=>getComputedStyle(node.children[0]).color===getComputedStyle(node.children[1]).color));
      if(group==='vehicles'||group==='maps')check('Every nested history rating is colored without a badge fill in '+group,
        await page.locator('.ss-map-battles').first().locator('.ss-map-battle-wn8-value[data-wn8-value]').count()===bands.length);
      if(group!=='battles')check('Purple WN8 stays on a neutral olive sorting fill with its orange edge in '+group,
        await page.locator('.ss-group-wn8-kpi.ss-sort-active-value').first().evaluate(node=>{
          const css=getComputedStyle(node),figure=node.querySelector('.ss-kpi-value');
          return css.backgroundColor==='rgb(37, 42, 35)'&&css.boxShadow.includes('rgb(231, 162, 59)')&&
            getComputedStyle(figure).color==='rgb(131, 87, 157)';
        }));
      if(group==='vehicles')console.log('GRZ_BLACK_WN8_QA_V1 '+(await page.locator('.ss-map-battles').first().screenshot({type:'png'})).toString('base64'));
      const borders=await page.locator('.ss-group').first().evaluate(card=>{
        const border=card.querySelector('.ss-wn8-card-border'),rect=card.getBoundingClientRect();
        const original={width:rect.width,height:rect.height,color:getComputedStyle(border).borderColor,
          position:getComputedStyle(border).position,pointer:getComputedStyle(border).pointerEvents};
        card.classList.add('ss-battle-target');const selected={rect:card.getBoundingClientRect().toJSON(),visibility:getComputedStyle(border).visibility,color:getComputedStyle(card).borderColor};
        card.classList.remove('ss-battle-target');const restored={rect:card.getBoundingClientRect().toJSON(),visibility:getComputedStyle(border).visibility,color:getComputedStyle(border).borderColor};
        return {original,selected,restored};
      });
      const borderColor=group==='battles'?'rgba(76, 118, 46, 0.22)':'rgba(131, 87, 157, 0.22)';
      check('The faint WN8 border follows the displayed headline and yields to selection without moving '+group+': '+JSON.stringify(borders),
        borders.original.position==='absolute'&&borders.original.pointer==='none'&&borders.original.color===borderColor&&
        borders.selected.visibility==='hidden'&&borders.restored.visibility==='visible'&&borders.restored.color===borders.original.color&&
        borders.selected.color!==borders.original.color&&[borders.selected.rect,borders.restored.rect].every(rect=>rect.width===borders.original.width&&rect.height===borders.original.height));
    }
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
      scope.summary.wn8=0;scope.summary.wn8_count=1;scope.summary.observed_battles=scope.summary.battles+1;
      for(const group of ['vehicles','maps','tiers','battles']){
        scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
        for(const item of scope[group]){item.stats.wn8=0;item.stats.wn8_count=1;item.stats.observed_battles=item.stats.battles+1;}
      }
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });
    await page.addStyleTag({content:'.ss-kpi-label,.ss-battle-label,.ss-map-battle-wn8-label { color:#aabbcc; }'});
    for(const group of ['vehicles','maps','tiers','battles']){
      await page.locator('#ss-group-'+group).click();await frames(page);
      check('Black WN8 keeps readable unoutlined captions in the summary and '+group,await page.evaluate(()=>{
        const captions=[...document.querySelectorAll('[data-wn8-caption-value="0"]')];
        return captions.length>1&&captions.every(node=>node.style.color===''&&getComputedStyle(node).color!=='rgb(0, 0, 0)'&&
          getComputedStyle(node).textShadow==='none');
      }));
      check('Black WN8 numeric figures retain their crisp edge in '+group,
        await page.locator('[data-wn8-value="0"]').evaluateAll(nodes=>nodes.length>1&&nodes.every(node=>
          node.style.color==='rgb(0, 0, 0)'&&node.style.textShadow.includes('0.85'))));
      check('Black WN8 captions honor the interface label color in '+group,
        await page.locator('.ss-kpi-label[data-wn8-caption-value="0"],.ss-battle-label[data-wn8-caption-value="0"],.ss-map-battle-wn8-label[data-wn8-caption-value="0"]').evaluateAll(nodes=>
          nodes.length>0&&nodes.every(node=>getComputedStyle(node).color==='rgb(170, 187, 204)')));
    }
  }finally{await page.close();}
};
module.exports.assertWN8Source=assertWN8Source;
module.exports.hasBlackOutline=hasBlackOutline;
if(require.main===module){assertWN8Source();console.log('Actual-source text-only WN8 palette and semantic rendering regressions passed.');}
