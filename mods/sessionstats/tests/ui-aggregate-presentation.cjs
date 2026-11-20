/* Group/period figures share centered axes, brief help and a stable WN8 frame. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let count=6;
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2600},viewport:{width:3840,height:2600,scale}});
    try{
      await page.evaluate(()=>{window.__presentationFixture=JSON.parse(model.payload);});
      let sequence=0;
      async function publish(language,width){
        await page.evaluate(({language,messages,width,scale,sequence})=>{
          const payload=JSON.parse(JSON.stringify(__presentationFixture)),scope=payload.scopes.launch;
          payload.account_key='synthetic-presentation-'+scale+'-'+sequence;payload.window_size=[width,1100];
          payload.viewport={width:3840,height:2600,scale};payload.localization={language,messages};
          payload.appearance={card_widths:{vehicles:560,maps:560,tiers:560},window_settings:{maximized:false,background_transparency:0,restored_width:width,restored_height:1100}};
          function prepare(stats,owner,total=4,wn8=2450){
            Object.assign(stats,{battles:total,observed_battles:total,wn8,wn8_count:total});
            const ranges={xp_base:[154,558,1403],xp_received:[266,3111,13415],battle_wn8:[78,2016,8834],
              credits_income_base:[1000,40000,60000],credits_income_received:[2000,50000,70000],credits_costs:[1000,30000,50000],
              credits_net_base:[-20000,10000,20000],credits_net_received:[-10000,20000,30000]},references={};
            for(const [metric,[min,avg,max]]of Object.entries(ranges)){
              stats[metric]={count:total,min,avg,max,sum:avg*total};references[metric]={};
              for(const statistic of ['min','max'])references[metric][statistic]={id:owner+'-'+metric+'-'+statistic,
                name:'Synthetic source',map:'Synthetic map',started_at:1794000000,metric,statistic,value:stats[metric][statistic]};
            }
            stats.currencies={credits:{income_base:123456,income_base_count:total,income:1485270,income_count:total,
              costs:1417829,costs_count:total,net_base:-1294373,net_base_count:total,net:67441,net_count:total},
              bonds:{income:50,income_count:total,costs:0,costs_count:total,net:50,net_count:total}};
            return references;
          }
          scope.extrema_battles=prepare(scope.summary,'presentation-summary');
          for(const group of ['vehicles','maps','tiers','battles']){
            const sample=scope[group][0];scope[group]=[0,1].map(index=>{
              const item=JSON.parse(JSON.stringify(sample));item.id='presentation-'+group+'-'+index;item.name='Synthetic '+group;
              item.extrema_battles=prepare(item.stats,item.id,group==='battles'?1:4,index?1600:2450);return item;
            });
            scope.pagination[group]={page:0,pages:1,total:2,page_size:40};
            scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
          }
          scope.data_revision='presentation-'+sequence;model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
        },{language,messages:languages[language],width,scale,sequence:++sequence});await frames(page);
      }
      async function audit(language){return page.evaluate(({scale,language})=>{
        const normalize=text=>text.replace(/\s/g,''),box=node=>node.getBoundingClientRect(),
          ink=node=>{const range=document.createRange();range.selectNodeContents(node);return [...range.getClientRects()].filter(rect=>rect.width>0&&rect.height>0);},
          inside=(part,owner)=>part.left>=owner.left-scale&&part.right<=owner.right+scale&&part.top>=owner.top-scale&&part.bottom<=owner.bottom+scale,
          center=node=>{const rect=box(node),css=getComputedStyle(node);return (rect.left+(parseFloat(css.borderLeftWidth)||0)+(parseFloat(css.paddingLeft)||0)+
            rect.right-(parseFloat(css.borderRightWidth)||0)-(parseFloat(css.paddingRight)||0))/2;},
          centered=(parts,cell)=>parts.length>0&&Math.abs((Math.min(...parts.map(part=>part.left))+Math.max(...parts.map(part=>part.right)))/2-center(cell))<=0.75*scale;
        const panels=[document.querySelector('#ss-summary .ss-summary-details'),...document.querySelectorAll('#ss-groups .ss-aggregate .ss-details')],numbers=[];
        for(const panel of panels){
          const failures=[],cells=[...panel.querySelectorAll('.ss-metric-head > .ss-metric-number,.ss-metric-row > .ss-metric-number,.ss-money-head > .ss-money-value,.ss-money-row .ss-money-value')];
          for(const cell of cells){
            if(!(box(cell).width>0))continue;
            const metric=cell.classList.contains('ss-metric-number'),arrow=cell.querySelector('.ss-metric-battle-link'),
              figure=cell.querySelector(':scope > .ss-extreme-number,:scope > .ss-cell-value')||cell,
              parts=ink(figure),content=metric&&arrow?parts.concat(box(arrow)):parts;
            if(!parts.length||!parts.every(part=>inside(part,box(cell))))failures.push('clipped:'+cell.textContent);
            if(!centered(content,cell))failures.push('number-axis:'+cell.textContent);
            if(metric&&arrow){const cue=arrow.querySelector('.ss-extreme-link-cue');
              if(!inside(box(arrow),box(cell))||!cue||Math.abs(box(cue).width/scale-14)>0.25||
                Math.abs((box(arrow).left-Math.max(...parts.map(part=>part.right)))/scale-5)>0.25)failures.push('source-arrow:'+cell.textContent);
            }
            const actions=[...cell.querySelectorAll('.ss-credit-extreme-actions > .ss-metric-battle-link')];
            if(actions.length&&!centered(actions.map(box),cell))failures.push('finance-action-axis:'+cell.textContent);
          }
          const metrics=[...panel.querySelectorAll('.ss-metric-row > .ss-metric-number')].map(cell=>normalize((cell.querySelector('.ss-extreme-number')||cell).textContent)),
            money=[...panel.querySelectorAll('.ss-credit-pair .ss-money-value[data-ss-metric] > .ss-cell-value')].map(node=>normalize(node.textContent));
          numbers.push({failures,metrics,money,sources:panel.querySelectorAll('.ss-metric-battle-link').length});
        }
        const headings=[...document.querySelectorAll('#ss-summary .ss-summary-table-heading')].map(heading=>{
          const lane=box(heading),title=heading.querySelector('.ss-summary-table-title'),info=heading.querySelector('.ss-info-button'),
            label=heading.querySelector('.ss-table-heading-text'),failures=[];
          for(const node of [title,info,label].filter(Boolean))if(!inside(box(node),lane))failures.push('caption-child-outside:'+node.className);
          if(label)for(const part of ink(label))if(!inside(part,lane))failures.push('caption-ink-outside');
          const overlaps=(a,b)=>Math.min(a.right,b.right)-Math.max(a.left,b.left)>scale&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>scale;
          if(label&&info&&ink(label).some(part=>overlaps(part,box(info))))failures.push('caption-info-overlap');
          for(const numeric of [...heading.parentNode.children].filter(node=>node!==heading&&box(node).width>0))
            if(overlaps(lane,box(numeric)))failures.push('caption-number-lane-overlap');
          return {text:label&&label.textContent,failures};
        });
        const messages=JSON.parse(model.payload).localization.messages,info=[...document.querySelectorAll('#ss-summary .ss-info-button,#ss-groups .ss-group-heading .ss-info-button')].map(node=>{
          const text=node.getAttribute('data-ss-help')||'',lines=text.split('\n').filter(line=>line.trim()),
            sentences=[...new Intl.Segmenter(language,{granularity:'sentence'}).segment(text)].filter(part=>part.segment.trim()).length,
            card=node.closest('.ss-group'),total=card&&card.classList.contains('ss-battle')?1:4,
            expected=messages['help.stats.compact'].replace('{0}',String(total)).replace('{1}',String(total));
          return {text,lines:lines.length,sentences,localized:text.includes(expected)&&text.includes(messages['help.credits.base_received'])||
            text.includes(expected)&&text.includes(messages['explain.wn8']),contract:node.getAttribute('aria-controls')==='ss-help-tooltip'&&node.getAttribute('title')===null};
        });
        const frames=[...document.querySelectorAll('#ss-groups .ss-group')].map(card=>{
          const frame=card.querySelector('.ss-wn8-card-border'),paint=getComputedStyle(frame),rect=box(card),value=Number(card.getAttribute('data-wn8-border-value')),
            rgb=value===2450?'131, 87, 157':'76, 118, 46';
          const halos=[...paint.boxShadow.matchAll(/rgba\(([^)]+)\) (-?[\d.]+)px (-?[\d.]+)px ([\d.]+)px (-?[\d.]+)px/g)].map(match=>{
            const rgba=match[1].split(', '),[x,y,blur,spread]=match.slice(2).map(Number);
            return {color:rgba.slice(0,3).join(', '),alpha:Number(rgba[3]),x,y,blur:blur/scale,spread};
          });
          const tapered=halos.length>=2&&!paint.boxShadow.includes('inset')&&
            halos.every(halo=>halo.color===rgb&&halo.x===0&&halo.y===0&&halo.spread<=0&&halo.blur>0)&&
            halos.slice(1).every((halo,index)=>halo.blur>halos[index].blur&&halo.alpha<halos[index].alpha)&&
            halos[0].blur<=6&&halos[0].alpha>=0.5&&halos.at(-1).blur>=10&&halos.at(-1).blur<=22&&halos.at(-1).alpha<=0.25;
          return {width:rect.width/scale,height:rect.height/scale,border:parseFloat(paint.borderTopWidth)/scale,
            color:paint.borderTopColor,shadow:paint.boxShadow,
            correct:tapered&&paint.borderTopColor==='rgba('+rgb+', 0.62)'&&
              !/currentcolor/i.test(frame.style.cssText)&&paint.position==='absolute'&&paint.pointerEvents==='none'&&Math.abs(parseFloat(paint.borderTopWidth)/scale-1)<=0.1};
        });
        return {numbers,info,frames,headings};
      },{scale,language});}
      const numbersValid=results=>results.length>0&&results.every(result=>result.numbers.every(panel=>!panel.failures.length&&panel.sources===16&&
        panel.metrics.join('|')==='154|558|1403|266|3111|13415|78|2016|8834'&&panel.money.join('|')==='123456|1485270|-1417829|-1294373|+67441')),
        helpsValid=results=>results.every(result=>result.info.length>=3&&result.info.every(help=>help.contract&&help.localized&&help.text.length<=400&&help.lines<=3&&help.sentences<=3)),
        framesValid=results=>results.every(result=>result.frames.length===2&&result.frames.every(frame=>frame.correct)),
        headingsValid=results=>results.every(result=>result.headings.length===2&&result.headings.every(heading=>!heading.failures.length));
      for(const language of Object.keys(languages))for(const width of [1320,1800]){
        await publish(language,width);const results=[];
        for(const group of ['vehicles','maps','tiers','battles']){
          await page.locator('#ss-group-'+group).click();await frames(page);results.push(await audit(language));
          if(group==='vehicles'){
            const info=page.locator('#ss-groups .ss-group-heading .ss-info-button').first();await info.focus();
            check('Localized brief card help opens its exact owned tooltip '+language+'/'+width+'/'+scale+'x',
              await page.locator('#ss-help-tooltip').isVisible()&&await page.locator('#ss-help-tooltip').textContent()===await info.getAttribute('data-ss-help'));
          }
        }
        check('All aggregate and period numbers center full figures and source composites '+language+'/'+width+'/'+scale+'x: '+JSON.stringify(results),numbersValid(results));
        check('Period table titles and info icons remain inside their separate caption lanes '+language+'/'+width+'/'+scale+'x: '+JSON.stringify(results.map(result=>result.headings)),headingsValid(results));
        check('Card and period help remains localized and limited to three short sentences '+language+'/'+width+'/'+scale+'x: '+JSON.stringify(results.map(result=>result.info)),helpsValid(results));
        check('WN8 glow fades outward around the colored one-pixel border '+language+'/'+width+'/'+scale+'x: '+JSON.stringify(results.map(result=>result.frames)),framesValid(results));
      }
      await publish('en',1800);await page.locator('#ss-group-vehicles').click();await frames(page);
      const card=page.locator('#ss-groups .ss-group').first(),before=await card.boundingBox();
      await card.evaluate(node=>node.classList.add('ss-battle-target'));const selected=await card.evaluate(node=>({rect:node.getBoundingClientRect().toJSON(),visibility:getComputedStyle(node.querySelector('.ss-wn8-card-border')).visibility,border:getComputedStyle(node).borderColor}));
      await card.evaluate(node=>node.classList.remove('ss-battle-target'));const after=await card.boundingBox();
      check('Orange source targeting hides the entire WN8 frame without changing card dimensions at '+scale+'x',selected.visibility==='hidden'&&
        selected.border==='rgb(231, 162, 59)'&&[selected.rect,after].every(rect=>Math.abs(rect.width-before.width)<=0.1&&Math.abs(rect.height-before.height)<=0.1)&&framesValid([await audit('en')]));
      const right=await page.addStyleTag({content:'.ss-aggregate .ss-metric-row .ss-metric-number { justify-content:flex-end !important; text-align:right !important; } .ss-summary-details .ss-metric-number { text-align:right !important; justify-content:flex-end !important; }'});
      check('The numeric-axis guard rejects restored right alignment at '+scale+'x',!numbersValid([await audit('en')]));
      await right.evaluate(node=>node.remove());await frames(page);
      check('Removing right alignment restores all centered figure/source axes at '+scale+'x',numbersValid([await audit('en')]));
      const info=page.locator('#ss-groups .ss-group-heading .ss-info-button').first(),brief=await info.getAttribute('data-ss-help');
      await info.evaluate(node=>node.setAttribute('data-ss-help',Array(4).fill('Synthetic excess sentence.').join('\n')));
      check('The brief-help guard rejects accumulated four-line explanations at '+scale+'x',!helpsValid([await audit('en')]));
      await info.evaluate((node,brief)=>node.setAttribute('data-ss-help',brief),brief);
      check('Restoring the brief help recovers its localized contract at '+scale+'x',helpsValid([await audit('en')]));
      const glow=await card.locator('.ss-wn8-card-border').getAttribute('style');
      await card.locator('.ss-wn8-card-border').evaluate(node=>{node.style.borderColor='rgba(131,87,157,0.22)';node.style.boxShadow='none';});
      check('The frame guard rejects the former faint unshaded WN8 overlay at '+scale+'x',!framesValid([await audit('en')]));
      await card.locator('.ss-wn8-card-border').evaluate((node,style)=>node.setAttribute('style',style),glow);
      check('Restoring explicit frame paint preserves the one-pixel geometry at '+scale+'x',framesValid([await audit('en')]));
      const overlap=await page.addStyleTag({content:'#ss-summary .ss-summary-table-heading { width:4rem !important; margin-right:-20rem !important; }'});
      check('The summary caption guard rejects a squeezed lane and overlapping info icon at '+scale+'x',!headingsValid([await audit('en')]));
      await overlap.evaluate(node=>node.remove());await frames(page);
      check('Restoring summary caption lanes contains titles and info icons at '+scale+'x',headingsValid([await audit('en')]));
    }finally{await page.close();}
  }
};
