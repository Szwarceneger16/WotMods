/* WoT-Life WN8 swatches color rating text, without coloring a cell's fill. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(__dirname,'..');
const read=name=>fs.readFileSync(path.join(root,'ui',name),'utf8');
const bands=[[0,'#000000'],[300,'#cd3333'],[600,'#d77900'],[900,'#d7b600'],[1250,'#6d9521'],
  [1600,'#4c762e'],[1900,'#4a92b7'],[2350,'#83579d'],[2900,'#5a3175']];
function sourceFunction(source,name){const start=source.indexOf('    function '+name+'('),line=source.indexOf('\n',start);
  const end=source.slice(start,line).endsWith('}')?line:source.indexOf('\n    }\n',start)+7;
  assert(start>=0&&end>start,'Exercise actual shipped '+name);return source.slice(start,end);}
function assertWN8Source(){
  class Node{constructor(tag,cls,text){this.tagName=tag;this.className=cls||'';this.textContent=text;this.children=[];this.style={};this.attributes={};}
    appendChild(child){child.parentNode=this;this.children.push(child);return child;}
    setAttribute(key,value){this.attributes[key]=String(value);}removeAttribute(key){delete this.attributes[key];}}
  let panel;
  for(const file of ['session_stats.js','postbattle.js']){
    const context={};vm.createContext(context);vm.runInContext(['wn8Color','paintWN8'].map(name=>sourceFunction(read(file),name)).join('\n'),context);
    for(let index=0;index<bands.length;index++){
      const [minimum,color]=bands[index];assert.strictEqual(context.wn8Color(minimum),color,file+' lower boundary '+minimum);
      if(index)assert.strictEqual(context.wn8Color(minimum-1),bands[index-1][1],file+' previous band '+minimum);
      const node=new Node('span');context.paintWN8(node,minimum);assert.strictEqual(node.style.color,color);
      assert.strictEqual(node.attributes['data-wn8-value'],String(minimum));
      assert(!Object.keys(node.style).some(key=>/background|border|padding|width|height/i.test(key)),'Rating paint cannot change fill or geometry');
      context.paintWN8(node,null);assert.strictEqual(node.style.color,'');assert.strictEqual(node.style.textShadow,'');
      assert.strictEqual(node.attributes['data-wn8-value'],undefined,'Unavailable results retire a previous rating color');
    }
    for(const value of [null,undefined,NaN,Infinity,-1,true,'1600'])assert.strictEqual(context.wn8Color(value),null,file+' rejects nonratings');
    assert.strictEqual(context.wn8Color(299.49),'#000000');assert.strictEqual(context.wn8Color(299.5),'#cd3333','Color follows the rounded displayed WN8');
    assert.strictEqual(context.wn8Color(2899.5),'#5a3175');
    if(file==='session_stats.js')panel=context;
  }
  Object.assign(panel,{append:(parent,child)=>parent.appendChild(child),element:(tag,cls,text)=>new Node(tag,cls,text),
    integer:value=>String(Math.round(value)),number:String,coverage:()=>null,explainCoverage(){}});
  vm.runInContext(['headlineStat','measureRow','battleMeasure'].map(name=>sourceFunction(read('session_stats.js'),name)).join('\n'),panel);
  const parent=new Node('div'),headline=panel.headlineStat(parent,'WN8','1 550',true,true,1550);
  assert(headline.children.every(node=>node.style.color==='#6d9521'),'The WN8 headline label and value share the rating color');
  panel.measureRow(parent,'WN8',{count:3,min:250,avg:1600,max:3000},true,3,false);
  const row=parent.children[1];assert.strictEqual(row.children[0].children[0].style.color,'#4c762e','A distribution label follows its average');
  assert.deepStrictEqual(row.children.slice(1).map(node=>node.style.color),['#000000','#4c762e','#5a3175'],'Min/Avg/Max retain their individual rating colors');
  panel.battleMeasure(parent,'WN8',2380,true);assert(parent.children[2].children.every(node=>node.style.color==='#83579d'));
  panel.battleMeasure(parent,'Base XP',2380,false);assert(parent.children[3].children.every(node=>node.style.color===undefined),'Other statistics retain their configured text colors');
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
        item.sort_value=899.5;
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
        const css=getComputedStyle(node);return {value:Number(node.dataset.wn8Value),color:css.color,background:css.backgroundColor,
          tag:node.className,styleBackground:node.style.background};}));
      const rgb={0:'rgb(0, 0, 0)',300:'rgb(205, 51, 51)',600:'rgb(215, 121, 0)',900:'rgb(215, 182, 0)',
        1250:'rgb(109, 149, 33)',1600:'rgb(76, 118, 46)',1900:'rgb(74, 146, 183)',2350:'rgb(131, 87, 157)',
        2450:'rgb(131, 87, 157)',299:'rgb(0, 0, 0)',2900:'rgb(90, 49, 117)'};
      check('WN8 labels, headlines and distribution values use exact text-only colors in '+group+': '+JSON.stringify(audit),
        audit.length>3&&audit.every(item=>rgb[item.value]===item.color&&item.styleBackground===''));
      check('The visible WN8 label carries the same color as its headline value in '+group,
        await page.locator('.ss-headline .ss-kpi').last().evaluate(node=>getComputedStyle(node.children[0]).color===getComputedStyle(node.children[1]).color));
      if(group==='vehicles'||group==='maps')check('Every nested history rating is colored without a badge fill in '+group,
        await page.locator('.ss-map-battles').first().locator('.ss-map-battle-wn8[data-wn8-value]').count()===bands.length);
    }
  }finally{await page.close();}
};
module.exports.assertWN8Source=assertWN8Source;
if(require.main===module){assertWN8Source();console.log('Actual-source text-only WN8 palette and semantic rendering regressions passed.');}
