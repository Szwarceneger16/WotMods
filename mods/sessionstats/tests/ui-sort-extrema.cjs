/* Permanent Min/Max values select their exact owned battle in every aggregate. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  await require('./ui-summary-extrema.cjs')({browser,nativeHost,check});
  const page=await nativeHost(browser,{initialViewport:{width:1800,height:1300},viewport:{width:1800,height:1300,scale:1}});
  const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const partialCardHelp=[catalogs.en['help.stats.compact'].replace('{0}','27').replace('{1}','27'),
    catalogs.en['explain.wn8'],catalogs.en['help.credits.incomplete_brief']].join('\n');
  const performance=['xp_base','xp_received','battle_wn8'];
  const financial=['credits_income_base','credits_income_received','credits_net_base','credits_net_received','credits_costs'];
  const metrics=performance.concat(financial);
  let revision=0;
  await page.evaluate(()=>{window.__extremaBase=JSON.parse(model.payload);});
  async function publish(group='maps',metric='off',statistic='avg',options={}){
    await page.evaluate(({group,metric,statistic,options,revision,metrics})=>{
      const payload=JSON.parse(JSON.stringify(__extremaBase)),scope=payload.scopes.launch;
      payload.window_size=[options.width||1200,1050];scope.data_revision='permanent-extrema-'+revision;
      if(options.scale)payload.viewport={width:3600,height:2600,scale:options.scale};
      if(options.width===550)payload.viewport.width=550*(payload.viewport.scale||1)+20;
      // Native logical size is account-owned and intentionally survives snapshots.
      // Give each width case a fresh owner so its requested size is actually used.
      if(options.width)payload.account_key='DEMO:extrema-layout-'+revision;
      scope.ordering[group]={metric,statistic,direction:'desc',chronology:'newest'};
      function fill(stats,owner){
        const references={},total=Math.max(stats.battles||0,stats.observed_battles||0);
        metrics.forEach(key=>{
          const min=key.indexOf('credits_net')===0?-500:0,max=options.maximum||12345;
          const count=key==='credits_income_base'||key==='credits_net_base'?total:3;
          stats[key]={count,min,max,avg:100,sum:100*count};
          references[key]={};
          ['min','max'].forEach(extreme=>{references[key][extreme]={
            id:owner+'-'+key+'-'+extreme,name:'<b>Synthetic tank</b>',map:'Synthetic off-page map',
            map_id:'synthetic-map',started_at:1793514000,outcome:'win',wn8:500,
            metric:key,statistic:extreme,value:extreme==='min'?min:max};});
        });
        // Enabled base-source fixtures need a complete displayed base total.
        // Explicit partial-history cases below replace this availability.
        const credits=stats.currencies.credits;
        for(const [metric,field]of [['credits_income_base','income_base'],['credits_net_base','net_base']]){
          credits[field]=stats[metric].sum;credits[field+'_count']=total;
        }
        return references;
      }
      scope.extrema_battles=fill(scope.summary,'summary');
      for(const grouping of ['vehicles','maps','tiers']){
        const item=scope[grouping][0];scope[grouping]=[item];
        scope.pagination[grouping]={page:0,pages:1,total:1,page_size:40};
        item.extrema_battles=fill(item.stats,grouping);item.sort_value=100;
        // A legacy selected reference must never create a second header action.
        item.sort_battle={...item.extrema_battles.xp_base.max,id:'obsolete-selected-winner'};
        item.battle_list={page:0,pages:3,total:30,page_size:10,items:[{id:'different-visible-history',name:'Other tank',map:'Other map',outcome:'win'}]};
        if(options.twoVehicles&&grouping==='vehicles'){
          const other=JSON.parse(JSON.stringify(item));other.id=String(item.id)+'-second';
          scope.vehicles.push(other);scope.pagination.vehicles.total=2;
        }
      }
      if(options.invalid){
        const item=scope[group][0];
        Object.assign(item.extrema_battles.xp_base.max,options.invalid);
      }
      if(options.empty)scope[group][0].stats.xp_base.count=0;
      if(options.missing)delete scope[group][0].extrema_battles.xp_base;
      if(options.language)payload.localization={language:options.language,messages:options.messages};
      delete scope.battle_focus;model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
      // Geometry setup keeps all cue, number and keyboard routing checks as real actions.
      if(options.width)document.getElementById('ss-group-'+group).onclick();
    },{group,metric,statistic,options,revision:++revision,metrics});
    if(!options.width)await page.locator('#ss-group-'+group).click();await frames(page);
  }
  const link=(owner,metric,statistic)=>page.locator('#ss-'+owner+' .ss-metric-battle-link[data-ss-source-metric="'+metric+'"][data-ss-extreme="'+statistic+'"]');
  const commands=()=>page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select'));
  try{
    for(const group of ['vehicles','maps','tiers']){
      await publish(group);
      for(const metric of performance)for(const statistic of ['min','max']){
        const action=link('groups',metric,statistic);
        check('Permanent '+group+'/'+metric+'/'+statistic+' uses its complete-scope source independently of sorting',
          await action.count()===1&&await action.evaluate((node,{group,metric,statistic})=>{
            const cell=node.parentNode,text=Array.from(cell.childNodes).filter(child=>child!==node).map(child=>child.textContent).join('').replace(/\s/g,''),box=node.getBoundingClientRect(),style=getComputedStyle(cell);
            return node.getAttribute('data-battle-id')===group+'-'+metric+'-'+statistic&&
              text===(statistic==='min'?'0':'12345')&&Math.abs(box.height-14)<=0.5&&Math.abs(box.width-14)<=0.5&&
              style.textAlign==='center'&&cell.classList.contains('ss-extreme-cell')&&node.textContent===''&&
              node.getAttribute('aria-label').includes('Show battle')&&
              node.getAttribute('data-ss-help').includes('Synthetic off-page map')&&
              node.getAttribute('data-ss-help').includes('<b>Synthetic tank</b>')&&
              node.getAttribute('data-ss-help').includes('2026');
          },{group,metric,statistic}));
      }
      for(const metric of financial)for(const statistic of ['min','max']){
        const action=link('groups',metric,statistic);
        check('Permanent '+group+'/'+metric+'/'+statistic+' credit action identifies its actual source value',
          await action.count()===1&&await action.evaluate((node,{group,metric,statistic})=>{
            const box=node.getBoundingClientRect(),text=node.getAttribute('data-ss-help');
            const expected=statistic==='max'?'12\u00a0345':metric.indexOf('credits_net')===0?'-500':'0';
            return node.getAttribute('data-battle-id')===group+'-'+metric+'-'+statistic&&
              node.querySelector('.ss-metric-action-label').textContent===(statistic==='min'?'Min':'Max')&&
              text.includes(expected)&&text.includes('Synthetic off-page map')&&box.width>=20&&box.height>=18&&
              !node.closest('.ss-money-value').querySelector('.ss-cell-value').contains(node);
          },{group,metric,statistic}));
      }
      check('The '+group+' card contains no source/date header filler or old arrow',
        await page.locator('.ss-sort-battle-link,.ss-group-sort-date').count()===0&&
        await page.locator('#ss-groups .ss-group-sort-host').textContent()==='');
      await link('groups','xp_received','max').click();
      const command=(await commands()).pop();
      check('The '+group+' permanent extremum sends exact native selection with owner context',
        command.id===group+'-xp_received-max'&&command.scope==='launch'&&Boolean(command.account_key)&&Boolean(command.period_id)&&Boolean(command.request_id));
    }
    for(const metric of ['off','battles','win_rate','xp_base','credits_costs'])for(const statistic of ['min','avg','max','sum']){
      await publish('maps',metric,statistic);
      check('All permanent performance links survive active '+metric+'/'+statistic+' sorting',
        await page.locator('#ss-groups .ss-metric-row .ss-metric-battle-link').count()===6&&
        await page.locator('#ss-summary .ss-metric-row .ss-metric-battle-link').count()===6&&
        await page.locator('#ss-groups .ss-credit-extreme-actions .ss-metric-battle-link').count()===10&&
        await page.locator('#ss-summary .ss-credit-extreme-actions .ss-metric-battle-link').count()===10);
    }
    for(const metric of financial)for(const statistic of ['min','avg','max','sum']){
      await publish('maps',metric,statistic);
      const active=statistic==='sum'?page.locator('#ss-groups .ss-money-value[data-ss-metric="'+metric+'"] .ss-cell-value.ss-sort-active-value'):
        page.locator('#ss-groups .ss-group-sort-host .ss-group-sort-value.ss-sort-active-value');
      check('Financial '+metric+'/'+statistic+' paints just the sort result and retains its permanent links',
        await active.count()===1&&await active.evaluate(node=>{
          const card=node.closest('.ss-group'), border=card.querySelector('.ss-wn8-card-border')||card;
          return getComputedStyle(node).boxShadow.includes(getComputedStyle(border).borderTopColor);
        })&&
        await page.locator('#ss-groups .ss-credit-extreme-actions .ss-sort-active-value').count()===0&&
        await page.locator('#ss-groups .ss-credit-extreme-actions .ss-metric-battle-link').count()===10);
    }
    await publish('vehicles','credits_net_received','max',{twoVehicles:true});
    const repeated=link('groups','credits_net_received','max');
    check('Max credit sorting paints one comparator per vehicle even when actions share the same battle',
      await page.locator('#ss-groups .ss-group-sort-host .ss-sort-active-value').count()===2&&
      await repeated.count()===2&&await repeated.evaluateAll(nodes=>nodes[0].getAttribute('data-battle-id')===nodes[1].getAttribute('data-battle-id')&&
        nodes.every(node=>!node.classList.contains('ss-sort-active-value')&&!node.classList.contains('ss-source-returned'))));
    await repeated.first().focus();
    check('Focus on a permanent Max action has its own neutral cue',await repeated.first().evaluate(node=>{
      const style=getComputedStyle(node);
      return style.outlineColor==='rgb(196, 199, 172)'&&style.outlineWidth==='1px';
    }));
    await publish('maps');
    for(const metric of financial)for(const statistic of ['min','max']){
      await link('summary',metric,statistic).click();
      check('Global '+metric+'/'+statistic+' source selects the canonical exact battle',
        (await commands()).pop().id==='summary-'+metric+'-'+statistic);
    }
    await link('groups','xp_base','max').focus();
    check('Value focus shows the exact source explanation as escaped text',
      await page.locator('#ss-help-tooltip').isVisible()&&
      await page.locator('#ss-help-tooltip').textContent().then(text=>text.includes('<b>Synthetic tank</b>'))&&
      await page.locator('#ss-help-tooltip b').count()===0);
    check('Focused source keeps its small rounded arrow cue without a cell border or outline',
      await link('groups','xp_base','max').evaluate(button=>{
        const style=getComputedStyle(button),cue=button.parentNode.querySelector('.ss-extreme-link-cue'),visual=getComputedStyle(cue),
          arrow=cue.querySelector('.ss-extreme-link-arrow'),shaft=getComputedStyle(arrow,':before'),head=getComputedStyle(arrow,':after');
        return parseFloat(style.borderWidth)===0&&style.outlineStyle==='none'&&style.boxShadow==='none'&&
          parseFloat(visual.borderRadius)>0&&visual.backgroundColor!=='rgba(0, 0, 0, 0)'&&
          shaft.content!=='none'&&parseFloat(shaft.width)>=8&&parseFloat(shaft.height)===1&&shaft.transform!=='none'&&
          head.content!=='none'&&parseFloat(head.borderTopWidth)===1&&parseFloat(head.borderRightWidth)===1;
      }));
    await page.keyboard.press('Escape');
    const geometry=await page.locator('#ss-groups .ss-metric-row').evaluateAll(rows=>rows.map(row=>{
      const cells=Array.from(row.children).slice(1),numbers=cells.map(cell=>{
        const button=cell.querySelector('button'),figure=cell.querySelector('.ss-extreme-number')||cell,range=document.createRange();range.selectNodeContents(figure);
        const box=range.getBoundingClientRect();
        return {box:{top:box.top,bottom:box.bottom,right:box.right},cell:cell.getBoundingClientRect().right,
          font:parseFloat(getComputedStyle(cell).fontSize)};
      });
      return {metric:row.getAttribute('data-ss-metric'),numbers,pass:
        Math.max(...numbers.map(n=>n.box.top))-Math.min(...numbers.map(n=>n.box.top))<=1&&
        numbers.every(n=>n.box.right<=n.cell+1)&&numbers.every(n=>n.font===numbers[1].font)};
    }));
    check('Clickable figures keep the Min/Average/Max baseline, font size and cell alignment: '+JSON.stringify(geometry.filter(row=>!row.pass)),geometry.every(row=>row.pass));
    // Model the observed native defect: unsupported inline button captions
    // collapse, although the button remains clickable. Explicit native labels
    // and numeric cells' original text must be independent of that path.
    const collapse=await page.addStyleTag({content:
      '.ss-metric-battle-link > span:not(.ss-control-label):not(.ss-extreme-link-cue) { display:block !important; width:0 !important; height:0 !important; font-size:0 !important; line-height:0 !important; overflow:hidden !important; }'});
    const model=await page.evaluate(()=>{
      const sample=document.createElement('button');sample.className='ss-metric-battle-link';
      const label=document.createElement('span');label.className='ss-extreme-figure';label.textContent='12 345';sample.appendChild(label);document.body.appendChild(sample);
      const range=document.createRange();range.selectNodeContents(label);const box=range.getBoundingClientRect();sample.remove();
      window.__extremeOriginalAppend=Node.prototype.appendChild;
      Node.prototype.appendChild=function(child){
        if(this.nodeType===1&&this.classList.contains('ss-metric-number')&&child.nodeType===1&&child.classList.contains('ss-metric-battle-link'))
          this.__originalNativeValue=Array.from(this.childNodes);
        return __extremeOriginalAppend.call(this,child);
      };
      return box.width===0&&box.height===0;
    });
    check('The native paint failure model reproduces the prior inline-caption blank while retaining its button',model);
    for(const [language,messages]of Object.entries(catalogs))for(const width of [550,1200])for(const maximum of [12345,123456,12345678])for(const group of ['maps','vehicles','tiers']){
      await publish(group,'off','avg',{language,messages,width,maximum});
      const painted=await page.evaluate(({maximum,messages,width})=>{
        if(Math.abs(document.querySelector('.ss-window').getBoundingClientRect().width-width)>0.5)return false;
        const rows=Array.from(document.querySelectorAll('#ss-summary .ss-metric-row,#ss-groups .ss-metric-row'));
        const values=rows.length===6&&rows.every(row=>{
          const average=row.children[2];
          if(average.querySelector('button')||average.classList.contains('ss-extreme-cell'))return false;
          return [['min',1,'0'],['max',3,maximum.toLocaleString('en-US').replace(/,/g,'')]].every(([statistic,index,expected])=>{
            const cell=row.children[index],button=cell.querySelector('.ss-metric-battle-link'),paint=cell.querySelector('.ss-extreme-number'),original=cell.__originalNativeValue;
            if(!button||!paint||!original||!original.length||original.some(node=>node.parentNode!==paint)||button.textContent!==''||
              paint.parentNode!==cell||cell.firstChild!==paint||paint.nextSibling!==button||button.contains(paint))return false;
            const actual=original.map(node=>node.textContent).join('').replace(/\s/g,'');
            const range=document.createRange();range.selectNode(original[0]);const ink=range.getBoundingClientRect(),box=cell.getBoundingClientRect(),hit=button.getBoundingClientRect();
            const visual=getComputedStyle(cell),overlay=getComputedStyle(button),cue=cell.querySelector('.ss-extreme-link-cue'),corner=cue.getBoundingClientRect();
            return actual===expected&&ink.width>3&&ink.height>=14&&ink.left>=box.left-1&&ink.right<=box.right+1&&
              Math.abs(hit.width-14)<=0.5&&Math.abs(hit.height-14)<=0.5&&overlay.backgroundImage==='none'&&overlay.backgroundColor==='rgba(0, 0, 0, 0)'&&
              parseFloat(overlay.borderWidth)===0&&overlay.outlineStyle==='none'&&overlay.boxShadow==='none'&&
              visual.boxShadow==='none'&&visual.display==='flex'&&visual.flexWrap==='nowrap'&&getComputedStyle(cue).display==='block'&&
              getComputedStyle(paint).display==='block'&&getComputedStyle(paint).whiteSpace==='nowrap'&&
              cue.parentNode===button&&getComputedStyle(cue).position==='relative'&&overlay.position==='relative'&&overlay.flexShrink==='0'&&
              parseFloat(getComputedStyle(cue).borderWidth)===0&&getComputedStyle(cue).outlineStyle==='none'&&
              getComputedStyle(cue).backgroundColor!=='rgba(0, 0, 0, 0)'&&parseFloat(getComputedStyle(cue).borderRadius)>0&&
              Math.abs(corner.width-14)<=0.5&&Math.abs(corner.height-14)<=0.5&&
              corner.left>=ink.right+4.5&&corner.left<=ink.right+5.5&&corner.right<=box.right-1&&
              Math.abs((corner.top+corner.bottom)-(ink.top+ink.bottom))<=2&&
              (row.getAttribute('data-ss-metric')!=='battle_wn8'||statistic!=='min'||
                original[0].classList.contains('ss-wn8-low-ink')&&getComputedStyle(cell).color==='rgb(0, 0, 0)');
          });
        });
        const captions=Array.from(document.querySelectorAll('.ss-credit-extreme-actions .ss-metric-battle-link'));
        const spaces=Array.from(document.querySelectorAll('.ss-credit-extreme-actions')).every(actions=>{
          const spacers=Array.from(actions.querySelectorAll(':scope > .ss-credit-extreme-spacer'));
          const buttons=Array.from(actions.querySelectorAll(':scope > .ss-metric-battle-link')),
            host=actions.getBoundingClientRect(),first=buttons[0].getBoundingClientRect(),last=buttons[1].getBoundingClientRect();
          return spacers.length===0&&buttons.length===2&&Math.abs(last.left-first.right-3)<=0.5&&
            Math.abs((first.left-host.left)-(host.right-last.right))<=1&&first.left>=host.left&&last.right<=host.right;
        });
        return values&&spaces&&captions.length===20&&captions.every(button=>{
          const label=button.querySelector('.ss-control-label.ss-metric-action-label'),style=getComputedStyle(label),box=label.getBoundingClientRect();
          const range=document.createRange();range.selectNodeContents(label);const ink=range.getBoundingClientRect();
          const action=getComputedStyle(button),hit=button.getBoundingClientRect(),host=button.parentNode.getBoundingClientRect();
          const inset=parseFloat(action.borderLeftWidth)+parseFloat(action.borderRightWidth)+parseFloat(action.paddingLeft)+parseFloat(action.paddingRight),
            expectedPadding=button.closest('.ss-aggregate')?3:4;
          return label.textContent===messages['metric.'+button.getAttribute('data-ss-extreme')]&&style.display==='block'&&
            parseFloat(style.fontSize)===11&&parseFloat(style.lineHeight)===16&&box.width>15&&ink.width>3&&ink.height>=11&&
            action.flexBasis==='auto'&&action.maxWidth==='none'&&Math.abs(hit.width-ink.width-inset)<=1.5&&
            parseFloat(action.paddingLeft)===expectedPadding&&parseFloat(action.paddingRight)===expectedPadding&&
            Math.abs(box.width-(hit.width-inset))<=0.5&&ink.left>=box.left-0.5&&ink.right<=box.right+0.5&&
            ink.top>=box.top-0.5&&ink.bottom<=box.bottom+0.5&&action.borderStyle==='solid'&&action.backgroundImage!=='none';
        });
      },{maximum,messages,width});
      const failure=painted?null:await page.locator('#ss-summary .ss-extreme-cell,#ss-groups .ss-extreme-cell').evaluateAll(cells=>cells.map(cell=>{
        const button=cell.querySelector('button'),cue=cell.querySelector('.ss-extreme-link-cue'),original=cell.__originalNativeValue,
          range=document.createRange();range.selectNode(original[0]);const ink=range.getBoundingClientRect(),corner=cue.getBoundingClientRect(),box=cell.getBoundingClientRect();
        return {text:original.map(n=>n.textContent).join(''),gap:corner.left-ink.right,center:(corner.top+corner.bottom-ink.top-ink.bottom)/2,
          cueDisplay:getComputedStyle(cue).display,position:getComputedStyle(cue).position,parent:cue.parentNode===cell,sibling:cue.previousSibling===button,
          width:box.width,hit:button.getBoundingClientRect().width,ink:ink.width,cornerRight:corner.right-box.right};
      }));
      check('Native-safe original figures have adjacent right arrows and compact paired credit actions '+language+'/'+width+'/'+maximum+'/'+group+(failure?': '+JSON.stringify(failure):''),painted);
    }
    // The live client promoted mixed anonymous cell text/inline cues onto
    // separate lines. Model that block cue behavior together with the older
    // button-caption paint failure: only explicit flex items may own the row.
    const anonymous=await page.addStyleTag({content:
      '.ss-metric-number > .ss-extreme-link-cue { display:block !important; }'});
    check('The anonymous-text native model reproduces the old second-line arrow',await page.evaluate(()=>{
      const row=document.createElement('div');row.className='ss-metric-row';
      row.style.cssText='position:fixed;left:0;top:0;width:180px;';
      const cell=document.createElement('div');cell.className='ss-metric-number ss-extreme-cell';cell.style.cssText='display:block;width:180px;';
      const original=document.createTextNode('123456');cell.appendChild(original);
      const cue=document.createElement('span');cue.className='ss-extreme-link-cue';cell.appendChild(cue);row.appendChild(cell);document.body.appendChild(row);
      const range=document.createRange();range.selectNode(original);const ink=range.getBoundingClientRect(),arrow=cue.getBoundingClientRect();
      row.remove();return arrow.top>=ink.bottom-1;
    }));
    await page.setViewportSize({width:3600,height:2600});
    for(const scale of [1,2])for(const width of [550,860,1600])for(const group of ['maps','vehicles','tiers'])for(const maximum of [123456,12345678]){
      await publish(group,'off','avg',{width,scale,maximum});
      const native=await page.locator('#ss-summary .ss-extreme-cell,#ss-groups .ss-extreme-cell').evaluateAll((cells,scale)=>{
        const failures=[];
        for(const cell of cells){
          const button=cell.querySelector('.ss-metric-battle-link'),cue=cell.querySelector('.ss-extreme-link-cue'),arrow=cue.querySelector('.ss-extreme-link-arrow'),
            paint=cell.querySelector('.ss-extreme-number'),original=cell.__originalNativeValue,range=document.createRange();range.selectNode(original[0]);
          const style=getComputedStyle(cell),action=getComputedStyle(button),ink=range.getBoundingClientRect(),after=cue.getBoundingClientRect(),hit=button.getBoundingClientRect(),bounds=cell.getBoundingClientRect();
          const canvas=document.createRange();canvas.selectNodeContents(cue);const painted=canvas.getBoundingClientRect();
          const line=parseFloat(style.lineHeight)+parseFloat(style.paddingTop)+parseFloat(style.paddingBottom),
            paintBounds=paint.getBoundingClientRect(),rowBounds=cell.closest('.ss-metric-row').getBoundingClientRect();
          // Translated row captions may wrap while the figure and arrow stay
          // on one centered line. The cell must still fill its own table row.
          const contained=[ink,after,paintBounds,hit,painted].every(box=>box.left>=bounds.left-scale&&box.right<=bounds.right+scale&&
            box.top>=bounds.top-scale&&box.bottom<=bounds.bottom+scale);
          if(!paint||paint!==cell.firstChild||paint.nextSibling!==button||cue.parentNode!==button||button.textContent!==''||original.some(node=>node.parentNode!==paint)||
            style.display!=='flex'||style.flexWrap!=='nowrap'||getComputedStyle(paint).whiteSpace!=='nowrap'||action.position!=='relative'||action.flexShrink!=='0'||
            after.left<ink.right+4.5*scale||after.left>ink.right+5.5*scale||after.right>bounds.right-scale||
            Math.abs((after.top+after.bottom-ink.top-ink.bottom)/scale)>4||
            ink.height>line+scale||after.height>line+scale||paintBounds.height>line+scale||
            Math.abs(bounds.height-rowBounds.height)>scale||!contained||
            Math.abs(hit.width-14*scale)>0.5||Math.abs(hit.height-14*scale)>0.5||hit.height>bounds.height-4*scale||!arrow||painted.width<13*scale||painted.height<13*scale||
            painted.left<bounds.left-1||painted.right>bounds.right+1)
            failures.push({value:original.map(node=>node.textContent).join(''),gap:(after.left-ink.right)/scale,height:bounds.height/scale,rowHeight:rowBounds.height/scale,inkHeight:ink.height/scale,paintHeight:paintBounds.height/scale,cueHeight:after.height/scale,line:line/scale,contained});
        }
        return {cells:cells.length,failures};
      },scale);
      check('Explicit native paint/action flex items keep complete figures and arrows on one compact line '+group+'/'+width+'/'+scale+'/'+maximum+': '+JSON.stringify(native),
        native.cells===12&&native.failures.length===0);
      await page.mouse.move(5,5);await frames(page);
      const before=await commands(),cue=await page.locator('#ss-groups .ss-metric-row[data-ss-metric="xp_base"] .ss-extreme-cell').last().locator('.ss-extreme-link-cue').boundingBox();
      await page.mouse.click(cue.x+cue.width/2,cue.y+cue.height/2);await frames(page);
      const after=await commands();
      check('The visible fixed arrow center dispatches exactly one source action '+group+'/'+width+'/'+scale+'/'+maximum,
        after.length===before.length+1&&after[after.length-1].id===group+'-xp_base-max');
      const number=await page.locator('#ss-groups .ss-metric-row[data-ss-metric="xp_base"] .ss-extreme-number').last().boundingBox();
      await page.mouse.click(number.x+number.width/2,number.y+number.height/2);await frames(page);
      const numberCommands=await commands();
      check('Clicking the original numeric paint block dispatches one source action '+group+'/'+width+'/'+scale+'/'+maximum,
        numberCommands.length===after.length+1&&numberCommands[numberCommands.length-1].id===group+'-xp_base-max');
      await link('groups','xp_base','max').press('Enter');await frames(page);
      check('Keyboard action does not double-dispatch through the cell '+group+'/'+width+'/'+scale+'/'+maximum,
        (await commands()).length===numberCommands.length+1);
    }
    await page.setViewportSize({width:1800,height:1300});
    await page.evaluate(()=>{Node.prototype.appendChild=__extremeOriginalAppend;delete window.__extremeOriginalAppend;});await collapse.evaluate(node=>node.remove());await anonymous.evaluate(node=>node.remove());
    // Timeline history can contain old received-only records and a few newer
    // base results. A retained card's cached sorting scalar must never choose
    // the displayed figure for a newly selected statistic.
    for(const count of [3,1,0]){
      await publish('maps','credits_income_base','min');
      await page.evaluate(count=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.launch));
        scope.from_point=scope.to_point='';scope.time_points=[];
        const item=scope.maps[0],data=count===3?{min:1000,avg:2000,max:4000,sum:6000}:
          count===1?{min:51624,avg:51624,max:51624,sum:51624}:{min:null,avg:null,max:null,sum:null};
        item.sort_value=999999;item.stats.battles=item.stats.observed_battles=27;
        item.stats.credits_income_base={count,...data};delete item.extrema_battles;
        Object.assign(item.stats.currencies.credits,{income_base:null,income_base_count:count,net_base:null,net_base_count:count,
          income:2432480,income_count:27,costs:1429892,costs_count:27,net:1002588,net_count:27});
        model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
      },count);
      await page.locator('#ss-scope-manual').click();await frames(page);
      check('Timeline regression uses the full Beginning-to-Now history with '+count+' base samples',
        (await page.locator('#ss-timeline-from .ss-select-trigger').textContent())==='Beginning of history'&&
        (await page.locator('#ss-timeline-to .ss-select-trigger').textContent())==='Now');
      for(const statistic of ['min','avg','max']){
        await page.evaluate(statistic=>{
          const payload=JSON.parse(model.payload),scope=payload.scopes.timeline;
          scope.ordering.maps={metric:'credits_income_base',statistic,direction:'desc',chronology:'newest'};
          scope.data_revision+='-'+statistic;model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
        },statistic);await frames(page);
        const expected=count===3?{min:'1000',avg:'2000',max:'4000'}[statistic]:count===1?'51624':'—';
        const result=await page.locator('#ss-groups .ss-group').evaluate(card=>{
          const badge=card.querySelector('.ss-group-sort-value');
          return {number:badge.querySelector('.ss-group-sort-number').textContent.replace(/\s/g,''),
            caption:badge.querySelector('.ss-group-sort-caption').textContent,
            triangle:badge.querySelectorAll('.ss-group-sort-caption > .ss-warning-icon.ss-sort-partial-icon').length,
            nativeIcon:badge.querySelector('.ss-sort-partial-icon')?getComputedStyle(badge.querySelector('.ss-sort-partial-icon')).backgroundImage:'',
            directHelp:badge.getAttribute('data-ss-help')||'',hoverHelp:badge.classList.contains('ss-hover-help'),
            accessible:badge.getAttribute('aria-label'),help:card.querySelector('.ss-info-button').getAttribute('data-ss-help')||'',
            income:card.querySelector('[data-ss-metric="credits_income_base"] > .ss-cell-value')?.textContent};
        });
        check('Timeline '+statistic+' reads its current series instead of stale sort_value with '+count+' samples',result.number===expected);
        check('Partial timeline '+statistic+' explains its actual sample size without repeating a visible ratio',
          !result.caption.includes('*')&&result.triangle===1&&result.nativeIcon==='url("img://gui/maps/icons/library/alertIcon.png")'&&
          result.hoverHelp&&result.directHelp.includes('Data available for '+count+' of 27 recorded battles.')&&
          result.accessible.includes('Data available for '+count+' of 27 recorded battles.')&&
          result.help===partialCardHelp&&!/\d+\/\d+/.test(result.caption));
        if(count===3&&statistic==='max'){
          const icon=page.locator('#ss-groups .ss-sort-partial-icon');
          check('The partial statistic uses the same decorative native warning triangle at 14px',await icon.evaluate(node=>{
            const box=node.getBoundingClientRect();return node.getAttribute('aria-hidden')==='true'&&node.textContent===''&&
              Math.abs(box.width-14)<=0.5&&Math.abs(box.height-14)<=0.5&&getComputedStyle(node).backgroundSize==='contain';
          }));
          await icon.hover();
          await page.evaluate(()=>{
            for(const [id,timer]of __grzTimers)if(timer.delay===500&&String(timer.callback).includes('helpPending')){
              __grzTimers.delete(id);timer.callback();
            }
          });
          check('Hovering the native partial-data triangle opens its retained sample-size explanation',
            await page.locator('#ss-help-tooltip').isVisible()&&await page.locator('#ss-help-tooltip').textContent().then(text=>
              text.includes('Data available for 3 of 27 recorded battles.')));
          await page.mouse.move(20,20);
        }
        if(count>0)check('Partial base income is not displayed as a complete 27-battle total',result.income==='—');
      }
      await page.locator('#ss-scope-launch').click();
    }
    for(const invalid of [{metric:'xp_received'},{statistic:'min'},{value:null},{value:999},{id:''}]){
      await publish('maps','off','avg',{invalid});
      check('Invalid permanent reference offers no misleading button '+JSON.stringify(invalid),
        await link('groups','xp_base','max').count()===0&&await link('groups','xp_base','min').count()===1);
    }
    for(const flag of ['empty','missing']){
      await publish('maps','off','avg',{[flag]:true});
      check('An '+flag+' series offers neither fabricated zero nor missing winner actions',
        await link('groups','xp_base','max').count()===0&&await link('groups','xp_base','min').count()===0);
    }
    await publish('maps');
    for(const owner of ['groups','summary']){
      const retained=await page.evaluate(owner=>{
        const node=document.querySelector('#ss-'+owner+' .ss-metric-battle-link'),payload=JSON.parse(model.payload);
        payload.scopes.launch.maps[0].battle_list.items=[{id:'new-history-page-item',name:'Updated history',map:'Other map',outcome:'loss'}];
        model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
        const live=document.querySelector('#ss-'+owner+' .ss-metric-battle-link')===node;
        node.onclick();return {live,id:node.getAttribute('data-battle-id')};
      },owner);
      check('A retained '+owner+' source remains live after an unrelated history-only refresh',
        retained.live&&(await commands()).pop().id===retained.id);
    }
    for(const [language,messages]of Object.entries(catalogs)){
      await publish('maps','off','avg',{language,messages});
      check('Financial Min/Max labels remain readable and localized in '+language,
        await page.locator('#ss-summary .ss-credit-extreme-actions .ss-metric-battle-link').evaluateAll((nodes,messages)=>
          nodes.length===10&&nodes.every(node=>{
            const label=node.querySelector('.ss-metric-action-label'),box=node.getBoundingClientRect(),text=label.getBoundingClientRect();
            return label.textContent===messages['metric.'+node.getAttribute('data-ss-extreme')]&&
              text.left>=box.left-1&&text.right<=box.right+1&&text.height<=box.height+1;
          }),messages));
      check('Permanent source explanation uses selected interface language '+language,
        await link('summary','xp_base','max').getAttribute('aria-label').then(text=>
          text.startsWith(messages['maps.open_battle']+': ')&&text.includes(messages['sort.extreme_battle'].split('{0}')[0])));
    }
    await publish('maps');
    await page.locator('#ss-group-tiers').click();
    await link('summary','xp_base','min').click();
    let request=(await commands()).pop();
    check('Global summary source remains correctly owned after an unrelated aggregate tab change',request.id==='summary-xp_base-min');
    await publish('tiers');await link('groups','xp_received','max').click();request=(await commands()).pop();
    await page.evaluate(request=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope.battles[0];
      scope.battles=[{...sample,id:request.id,name:'Synthetic selected extremum'}];
      scope.pagination.battles={page:2,pages:3,total:85,page_size:40};scope.battle_focus={id:request.id,request_id:request.request_id};
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
    },request);await frames(page);
    check('An off-page tier source opens the exact native page and target marker',
      await page.locator('#ss-group-battles').getAttribute('aria-pressed')==='true'&&
      await page.locator('.ss-battle-target').getAttribute('data-group-id')===request.id);
    for(const owner of ['groups','summary'])for(const changed of ['revision','account','period','scope','removed']){
      await publish('maps');
      const before=await page.evaluate(({owner,changed})=>{
        const node=document.querySelector('#ss-'+owner+' .ss-metric-battle-link'),click=node.onclick;
        const before=__grzCommands.filter(row=>row.action==='battle_select').length,payload=JSON.parse(model.payload);
        if(changed==='removed')node.remove();
        else if(changed==='scope')document.getElementById('ss-scope-manual').click();
        else{
          if(changed==='revision')payload.scopes.launch.data_revision='new-correction';
          else if(changed==='account')payload.account_key='EU:replaced';
          else payload.scopes.launch.period_id+='-replaced';
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
        }
        click();return before;
      },{owner,changed});
      check('A retained '+owner+' callback cannot cross '+changed+' ownership', (await commands()).length===before);
      if(changed==='scope')await page.locator('#ss-scope-launch').click();
    }
    await publish('maps');
    const retired=await page.evaluate(()=>{window.__retiredGroupExtreme=document.querySelector('#ss-groups .ss-metric-battle-link').onclick;return __grzCommands.filter(row=>row.action==='battle_select').length;});
    await page.locator('#ss-group-tiers').click();await page.evaluate(()=>__retiredGroupExtreme());
    check('A retained aggregate callback cannot navigate after changing group', (await commands()).length===retired);
    await publish('maps');
    const destroyed=await page.evaluate(()=>{
      const callbacks=Array.from(document.querySelectorAll('.ss-metric-battle-link')).map(node=>node.onclick),before=__grzCommands.filter(row=>row.action==='battle_select').length;
      GRZSessionStats.destroy();callbacks.forEach(click=>click());return {before,after:__grzCommands.filter(row=>row.action==='battle_select').length};
    });
    check('Destroyed permanent source callbacks are inert',destroyed.before===destroyed.after);
  }finally{await page.close();}
};
