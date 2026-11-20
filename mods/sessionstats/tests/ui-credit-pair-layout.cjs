/* One physical credit-cost cell spans two independently readable credit rows. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=4;
  function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));

function inspectCreditPairs({messages,scale,group}){
      // Only a marked caption may intentionally clip; numeric ink and source
      // controls still have to fit their original owning cell in full.
      const captionEllipsis=(text,owner)=>{
        const parent=text.nodeType===3?text.parentElement:text,
          caption=parent&&parent.closest('.ss-caption-ellipsis');
        if(!caption||!owner.contains(caption)||!caption.closest('.ss-aggregate')||
          !caption.closest('.ss-metric-name,.ss-credit-row-label,.ss-credit-inline-label,.ss-money-head > .ss-money-label,.ss-money-row > .ss-money-label,.ss-money-head > .ss-money-value,.ss-metric-head > .ss-metric-number,.ss-group-kpi .ss-kpi-label'))return false;
        const style=getComputedStyle(caption),box=caption.getBoundingClientRect(),cell=owner.getBoundingClientRect(),full=caption.textContent,
          inset=['paddingTop','paddingBottom','borderTopWidth','borderBottomWidth'].reduce((sum,key)=>sum+(parseFloat(style[key])||0),0);
        return full.length>0&&caption.classList.contains('ss-hover-help')&&caption.getAttribute('data-ss-help')===full&&
          caption.getAttribute('aria-label')===full&&caption.getAttribute('aria-controls')==='ss-help-tooltip'&&
          style.whiteSpace==='nowrap'&&style.overflowX==='hidden'&&style.textOverflow==='ellipsis'&&
          caption.scrollWidth>caption.clientWidth&&box.width>0&&box.height>0&&box.height<=parseFloat(style.lineHeight)+inset+scale&&
          box.left>=cell.left-scale&&box.right<=cell.right+scale&&box.top>=cell.top-scale&&box.bottom<=cell.bottom+scale;
      };
  const problems={semantics:[],flow:[],readability:[]},compact=text=>text.replace(/\s/g,'');
  const visible=node=>{const box=node.getBoundingClientRect();return box.width>0&&box.height>0;};
  const near=(left,right)=>Math.abs(left-right)<=scale*1.5;
  for(const [owner,panel] of [['summary',document.querySelector('#ss-summary')],['card',document.querySelector('#ss-groups .ss-group')]]){
    const economy=panel.querySelector('.ss-economy'),pair=economy.querySelector('.ss-credit-pair');
    const issue=(kind,name)=>problems[kind].push(owner+':'+name);
    if(!pair){issue('semantics','missing-pair');continue;}
    const cells=[...pair.querySelectorAll('.ss-money-value')],costs=cells.filter(cell=>cell.getAttribute('data-ss-metric')==='credits_costs');
    if(cells.length!==5||costs.length!==1||pair.querySelectorAll('.ss-cell-value').length!==5){issue('semantics','physical-values-or-cost-owner');continue;}
    const cost=costs[0],battle=owner==='card'&&group==='battles',scenario=owner==='summary'?'absent':group==='vehicles'?'zero':group==='maps'?'partial':'absent';
    const expected=scenario==='zero'?['0','0','0','0','0']:['—','90000','-20000','—','+70000'];
    const metrics=['credits_income_base','credits_income_received','credits_costs','credits_net_base','credits_net_received'];
    const actual=metrics.map(metric=>compact(pair.querySelector('[data-ss-metric="'+metric+'"] > .ss-cell-value').textContent));
    if(actual.join('|')!==expected.join('|'))issue('semantics','amounts:'+actual.join('|'));
    const labels=[...pair.querySelectorAll('.ss-credit-label-column [data-ss-credit-row]')],inline=[...pair.querySelectorAll('.ss-credit-inline-label')];
    const inlineAccessible=inline.every(label=>owner==='card'&&!battle?
      label.classList.contains('ss-caption-ellipsis')&&label.classList.contains('ss-hover-help')&&label.getAttribute('aria-hidden')===null&&
      label.getAttribute('data-ss-help')===label.textContent&&label.getAttribute('aria-label')===label.textContent&&
      label.getAttribute('aria-controls')==='ss-help-tooltip'&&label.getAttribute('tabindex')==='0':label.getAttribute('aria-hidden')==='true');
    if(labels.length!==2||inline.length!==2||!inlineAccessible)issue('semantics','labels');
    for(const basis of ['base','received']){
      const income=pair.querySelector('.ss-credit-income-column [data-ss-credit-row="'+basis+'"]'),net=pair.querySelector('.ss-credit-net-column [data-ss-credit-row="'+basis+'"]'),label=pair.querySelector('.ss-credit-label-column [data-ss-credit-row="'+basis+'"]');
      if(!income||!net||!label||!visible(income)||!visible(net)||label.textContent!==messages['finance.credits_'+basis]){issue('semantics','missing-row:'+basis);continue;}
      const a=income.getBoundingClientRect(),b=net.getBoundingClientRect();
      if(!near(a.top,b.top)||!near(a.bottom,b.bottom))issue('flow','row-boundary:'+basis);
      const amountInk=cell=>{const range=document.createRange();range.selectNodeContents(cell.querySelector(':scope > .ss-cell-value'));return range.getBoundingClientRect();};
      const incomeInk=amountInk(income),netInk=amountInk(net);
      if(!near(incomeInk.top,netInk.top)||!near(incomeInk.bottom,netInk.bottom))issue('flow','amount-line:'+basis);
      const verticalInsets=node=>{const css=getComputedStyle(node);return ['paddingTop','paddingBottom','borderTopWidth','borderBottomWidth'].reduce((sum,key)=>sum+(parseFloat(css[key])||0),0);};
      const inlineHeight=cell=>{const caption=cell.querySelector('.ss-credit-inline-label');if(!caption||!visible(caption))return 0;const css=getComputedStyle(caption);return caption.getBoundingClientRect().height+(parseFloat(css.marginTop)||0)+(parseFloat(css.marginBottom)||0);};
      const amountBlockHeight=cell=>{
        const children=[...cell.children].filter(child=>(child.classList.contains('ss-cell-value')||child.classList.contains('ss-credit-extreme-actions'))&&visible(child)),parts=children.map(child=>child.getBoundingClientRect()),amount=children[0];
        const unownedTop=amount.style.marginTop?0:(parseFloat(getComputedStyle(amount).marginTop)||0),bottom=parseFloat(getComputedStyle(children[children.length-1]).marginBottom)||0;
        return Math.max(...parts.map(box=>box.bottom))-Math.min(...parts.map(box=>box.top))+unownedTop+bottom;
      };
      const captionHeight=Math.max(inlineHeight(income),inlineHeight(net));
      const amountHeight=Math.max(...[income,net].map(cell=>captionHeight+amountBlockHeight(cell)+verticalInsets(cell)));
      const labelText=label.querySelector('.ss-credit-label-text'),labelHeight=labelText&&visible(labelText)?labelText.getBoundingClientRect().height+verticalInsets(label):0;
      const naturalHeight=Math.max(amountHeight,labelHeight)/scale;
      if(a.height/scale>Math.ceil(naturalHeight)+1||b.height/scale>Math.ceil(naturalHeight)+1)issue('flow','unused-row-height:'+basis+':'+JSON.stringify({actual:[a.height/scale,b.height/scale],required:naturalHeight}));
      if(visible(label)){const box=label.getBoundingClientRect();if(!near(a.top,box.top)||!near(a.bottom,box.bottom))issue('flow','label-boundary:'+basis);}
      const caption=income.querySelector('.ss-credit-inline-label');
      if(visible(label)===visible(caption)||caption.textContent!==messages['finance.credits_'+basis])issue('semantics','visible-caption:'+basis);
    }
    const costCount=scenario==='partial'?2:3,expectedAria=messages['finance.credits']+' '+messages['finance.costs']+
      (costCount<3?' '+messages['coverage.value'].replace('{0}',costCount).replace('{1}',3):'');
    if(cost.getAttribute('aria-label')!==expectedAria)issue('semantics','neutral-cost-availability');
    const actions=[...cost.querySelectorAll('.ss-metric-battle-link')];
    if(actions.length!==(battle?0:2)||(!battle&&actions.map(node=>node.getAttribute('data-ss-extreme')).join('|')!=='min|max')||
      pair.querySelectorAll('.ss-metric-battle-link[data-ss-source-metric="credits_costs"]').length!==actions.length)issue('semantics','single-cost-action-pair');
    const p=pair.getBoundingClientRect(),c=cost.getBoundingClientRect(),style=getComputedStyle(cost);
    const content=[...cost.children].filter(visible).map(node=>node.getBoundingClientRect());
    if(cost.parentNode!==pair||['absolute','fixed'].includes(style.position)||style.transform!=='none'||
      !near((p.top+p.bottom)/2,(c.top+c.bottom)/2)||c.left<p.left-scale||c.right>p.right+scale||
      !content.length||!near((Math.min(...content.map(box=>box.top))+Math.max(...content.map(box=>box.bottom)))/2,(c.top+c.bottom)/2))issue('flow','normal-centered-cost');
    for(const cell of cells){
      const number=cell.querySelector(':scope > .ss-cell-value');if(!number||!visible(number)){issue('readability','missing-visible-number');continue;}
      const box=cell.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(number);const ink=range.getBoundingClientRect(),css=getComputedStyle(cell);
      if(ink.left<box.left+parseFloat(css.paddingLeft)+parseFloat(css.borderLeftWidth)-scale||ink.right>box.right-parseFloat(css.paddingRight)-parseFloat(css.borderRightWidth)+scale||
        ink.top<box.top-scale||ink.bottom>box.bottom+scale||parseFloat(getComputedStyle(number).fontSize)/scale<13)issue('readability','numeric-ink:'+cell.getAttribute('data-ss-metric'));
      if(cell===cost&&!near((ink.left+ink.right)/2,(box.left+box.right)/2))issue('flow','horizontal-cost-center');
    }
    for(const label of labels.concat(inline).filter(visible)){
      const box=label.getBoundingClientRect(),walker=document.createTreeWalker(label,NodeFilter.SHOW_TEXT);let text,contained=true;
      while((text=walker.nextNode()))if(text.textContent.trim()&&!captionEllipsis(text,label)){
        const range=document.createRange();range.selectNodeContents(text);
        if(![...range.getClientRects()].every(ink=>ink.left>=box.left-scale&&ink.right<=box.right+scale&&ink.top>=box.top-scale&&ink.bottom<=box.bottom+scale))contained=false;
      }
      if(!contained||parseFloat(getComputedStyle(label).fontSize)/scale<12)issue('readability','currency-caption');
    }
  }
  return problems;
}

module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:2400,height:2800},viewport:{width:2400,height:2800,scale}});
    try{
      const original=await page.evaluate(()=>JSON.parse(model.payload));
      for(const [language,messages]of Object.entries(languages))for(const width of [320,550,1200]){
        const gameWidth=(width===320?340:1800)*scale;
        await page.setViewportSize({width:gameWidth,height:1400*scale});
        await page.evaluate(({original,language,messages,width,scale,gameWidth})=>{
          const payload=JSON.parse(JSON.stringify(original)),scope=payload.scopes.launch;
          payload.account_key='synthetic-credit-pair-'+language+'-'+width+'-'+scale;
          payload.localization={language,selected:language,messages};payload.viewport={width:gameWidth,height:1400*scale,scale};payload.window_size=[width,1100];
          payload.appearance={window_settings:{maximized:false,background_transparency:0,restored_width:width,restored_height:1100}};
          function prepare(stats,scenario,owner,battle){
            const total=battle?1:3,zero=scenario==='zero',partial=scenario==='partial';
            stats.battles=total;stats.observed_battles=total;stats.wn8_count=total;
            const credits={income:zero?0:90000,income_count:total,costs:zero?0:20000,costs_count:partial?2:total,net:zero?0:70000,net_count:total};
            if(zero){Object.assign(credits,{income_base:0,income_base_count:total,net_base:0,net_base_count:total});}
            if(partial){Object.assign(credits,{income_base:5000,income_base_count:1,net_base:null,net_base_count:0});}
            stats.currencies={credits,bonds:{income:0,costs:0,net:0,income_count:total,costs_count:total,net_count:total}};
            const references={};
            for(const [metric,field]of [['credits_income_base','income_base'],['credits_income_received','income'],['credits_costs','costs'],['credits_net_base','net_base'],['credits_net_received','net']]){
              const count=credits[field+'_count']||0,value=count>0?credits[field]:null;
              stats[metric]={count,min:value,avg:value,max:value,sum:value};references[metric]={};
              if(count>0&&typeof value==='number')for(const statistic of ['min','max'])references[metric][statistic]={id:owner+'-'+metric+'-'+statistic,metric,statistic,value,name:'Synthetic vehicle',map:'Synthetic map',started_at:1793514000};
            }
            return references;
          }
          scope.extrema_battles=prepare(scope.summary,'absent','summary',false);
          for(const group of ['vehicles','maps','tiers','battles']){
            const item=JSON.parse(JSON.stringify(scope[group][0]));item.id='synthetic-credit-pair-'+group;
            item.extrema_battles=prepare(item.stats,group==='vehicles'?'zero':group==='maps'?'partial':'absent',group,group==='battles');
            scope[group]=[item];scope.pagination[group]={page:0,pages:1,total:1,page_size:40};scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:group==='tiers'?'tier_desc':'newest'};
          }
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{original,language,messages,width,scale,gameWidth});
        for(const group of ['vehicles','maps','tiers','battles']){
          await page.evaluate(group=>document.getElementById('ss-group-'+group).onclick(),group);await frames(page);
          const result=await page.evaluate(inspectCreditPairs,{messages,scale,group}),caption=language+'/'+width+'/'+scale+'x/'+group;
          for(const kind of ['semantics','flow','readability'])check('Shared credit pair '+kind+' '+caption+': '+JSON.stringify(result[kind]),result[kind].length===0);
          if(language==='en'&&width===320&&scale===1&&group==='vehicles'){
            await page.evaluate(()=>{const pair=document.querySelector('#ss-groups .ss-credit-pair');window.__creditProbe=pair.querySelector('.ss-credit-shared-cost');pair.appendChild(__creditProbe.cloneNode(true));});
            const duplicate=await page.evaluate(inspectCreditPairs,{messages,scale,group});
            check('The credit pair guard rejects a duplicated physical cost cell',duplicate.semantics.some(issue=>issue.includes('physical-values-or-cost-owner')));
            await page.evaluate(()=>{const pair=document.querySelector('#ss-groups .ss-credit-pair');pair.removeChild(pair.lastElementChild);__creditProbe.style.position='absolute';});
            const overlay=await page.evaluate(inspectCreditPairs,{messages,scale,group});
            check('The credit pair guard rejects an absolutely positioned shared cost',overlay.flow.some(issue=>issue.includes('normal-centered-cost')));
            await page.evaluate(()=>{__creditProbe.style.removeProperty('position');delete window.__creditProbe;});
            const restored=await page.evaluate(inspectCreditPairs,{messages,scale,group});
            check('Restoring the actual single cost cell recovers every finance invariant',Object.values(restored).every(issues=>issues.length===0));
          }
        }
      }
    }finally{await page.close();}
  }
};
