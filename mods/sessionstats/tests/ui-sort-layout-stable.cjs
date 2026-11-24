/* Filter controls stay stable while aggregate headers fit their actual content. */
const fs=require('fs'),path=require('path');
// Width/mode/native acknowledgements precede each case; metric changes keep that width.
const frames=page=>page.evaluate(()=>new Promise((resolve,reject)=>{let left=6;
  const row=document.getElementById('ss-list-controls'),mode=row.getAttribute('data-filter-layout'),width=row.getAttribute('data-filter-width');
  function next(){
    if(row.getAttribute('data-filter-layout')!==mode||row.getAttribute('data-filter-width')!==width){
      reject(Error('An acknowledged filter layout changed without a new width'));return;
    }
    if(--left)requestAnimationFrame(next);else resolve();
  }requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const metrics=[['battles','avg'],['win_rate','avg'],['off','avg'],['battle_wn8','min'],['battle_wn8','max'],['xp_received','avg'],['credits_net_received','avg'],['credits_costs','max'],['xp_received','sum'],['off','avg']];
  const scaleResults=await Promise.allSettled([1,2].map(async scale=>{
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},viewport:{width:3840,height:2400,scale}});
    try{
      for(const [language,messages]of Object.entries(languages))for(const width of [550,1200,1800]){
        await page.evaluate(({language,messages,width,scale})=>{
          const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
          payload.account_key='synthetic-stable-sort-'+language;payload.localization={language,messages};
          payload.viewport={width:width===550 ? width*scale+20 : 3840,height:2400,scale};payload.window_size=[width,950];
          payload.appearance={window_settings:{background_transparency:0,maximized:false,restored_width:width,restored_height:950}};
          for(const group of ['maps','vehicles','tiers']){
            const sample=scope[group][0];scope[group]=[0,1].map(index=>{
              const item=JSON.parse(JSON.stringify(sample));item.id='stable-'+group+'-'+index;item.name='Synthetic '+group;
              item.stats.wn8=2429;item.stats.battle_wn8={count:7,min:334,avg:2300,max:5035,sum:16100};
              item.stats.wn8_count=7;item.stats.battles=123;item.stats.observed_battles=137;item.stats.win_rate=50;
              item.sort_value=8;return item;
            });
            scope.pagination[group]={page:0,pages:1,total:2,page_size:40};
          }
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
          document.getElementById('ss-scope-launch').onclick();document.getElementById('ss-group-maps').onclick();
        },{language,messages,width,scale});
        await page.waitForFunction(({width,scale})=>{
          const row=document.getElementById('ss-list-controls');
          return row.getAttribute('data-filter-layout')===(width-38>=875?'wide':'wrapped')&&
            Number(row.getAttribute('data-filter-width'))===width-38&&window.__nativeSize&&__nativeSize[0]===Math.ceil(width*scale);
        },{width,scale});await frames(page);
        const groups=language==='en'&&width===1200?['maps','vehicles','tiers']:['maps'];
        for(const group of groups){
          const baselines=new Map();
          let remembered='xp_base';
          for(const [metric,statistic]of metrics){
            if(group==='tiers'&&metric==='battles')continue;
            if(metric!=='off')remembered=metric;
            const hasStatistic=remembered!=='battles'&&remembered!=='win_rate';
            await page.evaluate(({group,metric,statistic})=>{
              const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
              scope.ordering[group]={metric,statistic,direction:'desc',chronology:'newest'};
              scope[group].forEach(item=>{item.sort_value=metric==='battle_wn8'?(statistic==='min'?334:5035):metric==='xp_received'&&statistic==='sum'?12345678:metric.indexOf('credits_')===0?149678:8;});
              model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-group-'+group).onclick();
            },{group,metric,statistic});await frames(page);
            const audit=()=>page.evaluate(()=>{
              const bar=document.getElementById('ss-list-controls'),card=document.querySelector('#ss-groups .ss-group');
              const barBox=bar.getBoundingClientRect(),cardBox=card.getBoundingClientRect();
              const rect=(node,origin)=>{const box=node.getBoundingClientRect();return [box.left-origin.left,box.top-origin.top,box.width,box.height];};
              const controls=['#ss-page-previous','#ss-sort-chronology','#ss-page-next','#ss-sort-direction','#ss-sort-metric','#ss-sort-off','#ss-sort-statistic']
                .map(selector=>rect(document.querySelector(selector),barBox)).filter(box=>box[2]>0);
              const kpis=[...card.querySelectorAll('.ss-group-kpi')].map(node=>{
                const box=node.getBoundingClientRect(),number=node.querySelector('.ss-kpi-value'),range=document.createRange();range.selectNodeContents(number);
                const text=range.getBoundingClientRect(),label=node.querySelector('.ss-kpi-label'),labelBox=label.getBoundingClientRect(),labelRange=document.createRange();labelRange.selectNodeContents(label);
                const inside=(part,owner)=>part.left>=owner.left-1&&part.right<=owner.right+1&&part.top>=owner.top-1&&part.bottom<=owner.bottom+1,
                  style=getComputedStyle(label),full=label.textContent,
                  inset=['paddingTop','paddingBottom','borderTopWidth','borderBottomWidth'].reduce((sum,key)=>sum+(parseFloat(style[key])||0),0),
                  labelParts=[...labelRange.getClientRects()].filter(part=>part.width>0&&part.height>0),lineTops=[];
                for(const part of labelParts)if(!lineTops.some(top=>Math.abs(top-part.top)<=1))lineTops.push(part.top);
                // Only a marked aggregate caption may clip its own full text.
                // KPI figures must remain inside their own visible value box.
                const ellipsis=label.classList.contains('ss-caption-ellipsis')&&label.classList.contains('ss-hover-help')&&
                  label.closest('.ss-aggregate')&&full.length>0&&label.getAttribute('data-ss-help')===full&&
                  label.getAttribute('aria-label')===full&&label.getAttribute('aria-controls')==='ss-help-tooltip'&&
                  label.getAttribute('title')===null&&style.whiteSpace==='nowrap'&&style.overflowX==='hidden'&&style.textOverflow==='ellipsis'&&
                  label.scrollWidth>label.clientWidth&&lineTops.length===1&&labelBox.width>0&&labelBox.height>0&&
                  labelBox.height<=parseFloat(style.lineHeight)+inset+1&&inside(labelBox,box),numberBox=number.getBoundingClientRect();
                const fit=(labelParts.every(part=>inside(part,labelBox))||ellipsis)&&inside(numberBox,box)&&
                  [...range.getClientRects()].every(part=>inside(part,numberBox));
                return {fits:!!fit,box:rect(node,cardBox),label:rect(label,cardBox),value:rect(number,cardBox),centered:Math.abs((text.left+text.right-box.left-box.right)/2)<=1};
              });
              const field=document.querySelector('.ss-sort-statistic'),trigger=document.querySelector('#ss-sort-statistic .ss-select-trigger');
              const host=card.querySelector('.ss-group-sort-host');
              const hostBox=host.getBoundingClientRect(),badge=host.querySelector('.ss-group-sort-value');
              const inside=(part,owner)=>part.left>=owner.left-1&&part.right<=owner.right+1&&part.top>=owner.top-1&&part.bottom<=owner.bottom+1;
              const ink=node=>{const range=document.createRange();range.selectNodeContents(node);return [...range.getClientRects()];};
              let hostFits=true;
              if(badge&&hostBox.width){
                const badgeBox=badge.getBoundingClientRect(),caption=badge.querySelector('.ss-group-sort-caption-text'),number=badge.querySelector('.ss-group-sort-number');
                const captionBox=caption.getBoundingClientRect(),captionInk=ink(caption),numberBox=number.getBoundingClientRect(),numberInk=ink(number);
                const icon=badge.querySelector('.ss-sort-partial-icon'),style=getComputedStyle(caption),help=badge.getAttribute('data-ss-help');
                const scale=parseFloat(getComputedStyle(document.documentElement).fontSize)||1;
                const ellipsis=caption.scrollWidth>caption.clientWidth&&style.whiteSpace==='nowrap'&&style.overflowX==='hidden'&&style.textOverflow==='ellipsis'&&
                  !!help&&badge.getAttribute('aria-label')===help&&badge.getAttribute('aria-controls')==='ss-help-tooltip'&&badge.getAttribute('title')===null;
                const maxBadgeWidth=card.classList.contains('ss-ultra-wide-headline')?190:132;
                hostFits=badgeBox.width<=maxBadgeWidth*scale&&inside(badgeBox,hostBox)&&inside(captionBox,badgeBox)&&inside(numberBox,badgeBox)&&
                  (!icon||inside(icon.getBoundingClientRect(),badgeBox))&&new Set(captionInk.map(part=>part.top)).size===1&&
                  (captionInk.every(part=>inside(part,captionBox))||ellipsis)&&
                  numberInk.length===1&&numberInk.every(part=>inside(part,numberBox));
              }
              const header=card.querySelector('.ss-group-header'),headerBox=header.getBoundingClientRect();
              const contained=nodes=>nodes.filter(node=>node.getBoundingClientRect().width>0).every(node=>{
                const box=node.getBoundingClientRect();
                if(card.classList.contains('ss-card-border-more')&&node.classList.contains('ss-more-button')){
                  const unit=parseFloat(getComputedStyle(document.documentElement).fontSize)||1,range=document.createRange();range.selectNodeContents(node);
                  return box.left>=cardBox.left-unit&&box.right<=cardBox.right+unit&&Math.abs((box.top+box.bottom)/2-cardBox.top)<=2*unit&&
                    Math.abs(cardBox.right-box.right-6*unit)<=2*unit&&Math.abs(box.width-82*unit)<=0.5*unit&&
                    Math.abs(box.height-20*unit)<=0.5*unit&&headerBox.top>=box.bottom+2*unit&&
                    [...range.getClientRects()].every(part=>part.left>=box.left-unit&&part.right<=box.right+unit&&part.top>=box.top-unit&&part.bottom<=box.bottom+unit);
                }
                return box.left>=headerBox.left-1&&box.right<=headerBox.right+1&&box.top>=headerBox.top-1&&box.bottom<=headerBox.bottom+1;
              });
              const separate=nodes=>{const boxes=nodes.map(node=>node.getBoundingClientRect()).filter(box=>box.width>0&&box.height>0);
                return boxes.every((a,index)=>boxes.slice(index+1).every(b=>Math.min(a.right,b.right)-Math.max(a.left,b.left)<=1||Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)<=1));};
              const siblings=[...header.children],statistics=[...card.querySelector('.ss-group-stats').children];
              const sorting=document.getElementById('ss-sorting'),sortingBox=sorting.getBoundingClientRect();
              const lastRight=Math.max(...[...sorting.querySelectorAll('.ss-select-trigger, #ss-sort-off')]
                .map(node=>node.getBoundingClientRect()).filter(box=>box.width>0).map(box=>box.right));
              return {controls,kpis,host:rect(host,cardBox),hostFits,headerFits:contained(siblings)&&contained(statistics)&&separate(siblings)&&separate(statistics),
                card:rect(card,cardBox),header:rect(header,cardBox),sorting:rect(sorting,barBox),
                trailing:sortingBox.right-lastRight,statisticWidth:field.getBoundingClientRect().width,
                hidden:getComputedStyle(field).display==='none',aria:field.getAttribute('aria-hidden'),disabled:trigger.disabled};
            });
            const value=await audit();
            const caption=language+'/'+scale+'x/'+width+'/'+group+'/'+metric+'/'+statistic;
            if(!baselines.has(hasStatistic))baselines.set(hasStatistic,value);
            const baseline=baselines.get(hasStatistic);
            const same=(left,right)=>left.length===right.length&&left.every((part,index)=>Array.isArray(part)?same(part,right[index]):Math.abs(part-right[index])<=scale*0.1);
            const unchanged=same(value.controls,baseline.controls)&&same(value.sorting,baseline.sorting);
            check('Metrics with the same available controls preserve the filter geometry '+caption+(unchanged?'':': '+JSON.stringify(value)),unchanged);
            const centered=value.kpis.every(item=>item.centered&&item.fits)&&value.hostFits&&value.headerFits&&
              Math.max(...value.kpis.map(item=>item.label[1]))-Math.min(...value.kpis.map(item=>item.label[1]))<=scale&&
              Math.max(...value.kpis.map(item=>item.value[1]+item.value[3]))-Math.min(...value.kpis.map(item=>item.value[1]+item.value[3]))<=scale;
            check('Aggregate text stays aligned, readable and contained in its natural header '+caption+(centered?'':': '+JSON.stringify(value)),centered);
            if(language==='en'&&width===550&&group==='maps'&&metric==='battles'){
              const cropped=await page.addStyleTag({content:'#ss-groups .ss-group:first-child .ss-group-kpi .ss-kpi-value { width:1rem !important; max-width:1rem !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; }'});
              const invalid=await audit();
              check('Caption ellipsis never permits cropped unmarked KPI figures at '+scale+'x',invalid.kpis.some(item=>!item.fits));
              await cropped.evaluate(node=>node.remove());
              check('Removing cropped KPI figures restores strict header containment at '+scale+'x',(await audit()).kpis.every(item=>item.fits));
            }
            if(language==='en'&&width===1200&&group==='maps'&&metric==='credits_costs'){
              await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.maps.direction='asc';
                model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
              const repeated=await audit();
              check('Unchanged header content keeps the same geometry when only ordering direction changes '+caption,
                same(value.header,repeated.header)&&same(value.host,repeated.host)&&same(value.card,repeated.card)&&
                value.kpis.every((item,index)=>same(item.box,repeated.kpis[index].box)&&same(item.label,repeated.kpis[index].label)&&same(item.value,repeated.kpis[index].value)));
            }
            const wide=width-38>=875, expectedWidth=wide?(hasStatistic?357:287):(hasStatistic?294:229);
            check('Statistic availability matches the measured sorting footprint '+caption+': '+JSON.stringify({
              sorting:value.sorting,statisticWidth:value.statisticWidth,trailing:value.trailing,hidden:value.hidden,aria:value.aria,disabled:value.disabled}),
              value.hidden===!hasStatistic&&value.aria===String(!hasStatistic)&&value.disabled===(!hasStatistic||metric==='off')&&
              (value.statisticWidth>0)===hasStatistic&&Math.abs(value.sorting[2]/scale-expectedWidth)<=0.5&&
              value.trailing>=-0.5*scale&&value.trailing<=6.5*scale);
          }
        }
      }
      // A native update can invalidate an already open statistic menu.
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.maps={metric:'battle_wn8',statistic:'max',direction:'desc',chronology:'newest'};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-group-maps').onclick();});await frames(page);
      await page.locator('#ss-sort-statistic .ss-select-trigger').click();
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.maps.metric='win_rate';model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});
      check('An inapplicable statistic closes its old menu and leaves keyboard navigation',await page.locator('#ss-sort-statistic .ss-select-trigger').getAttribute('aria-expanded')==='false'&&
        await page.locator('#ss-sort-statistic .ss-select-trigger').isDisabled()&&!await page.locator('#ss-sort-statistic .ss-select-options').isVisible());
      for(const [language,messages] of Object.entries(languages))for(const [confirmed,total] of
        [[0,137],[38,39],[999,1000],[9999,10000],[99999,100000],[123456,137000],[99999,99999]]){
        await page.evaluate(({confirmed,total,language,messages})=>{const payload=JSON.parse(model.payload);
          payload.localization={language,messages};payload.scopes.launch.maps.forEach(item=>{
            item.stats.battles=confirmed;item.stats.observed_battles=total;
          });model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{confirmed,total,language,messages});await frames(page);
        const count=await page.locator('.ss-group-count').first().evaluate(node=>{
          const value=node.querySelector('.ss-kpi-value'),parts=[...value.children],box=value.getBoundingClientRect(),
            range=document.createRange();range.selectNodeContents(value);
          const content=parts.length?parts.map(part=>part.getBoundingClientRect()):[range.getBoundingClientRect()],
            center=(Math.min(...content.map(r=>r.top))+Math.max(...content.map(r=>r.bottom)))/2;
          return {text:value.textContent,parts:parts.length,centerDelta:Math.abs(center-(box.top+box.bottom)/2),
            peerCenters:[...node.parentElement.querySelectorAll('.ss-kpi-value')].map(peer=>{
              const r=peer.getBoundingClientRect();return Math.abs((r.top+r.bottom)/2-(box.top+box.bottom)/2);
            }),metricCoverage:node.closest('.ss-group').querySelectorAll('.ss-cell-coverage,.ss-count-coverage,.ss-wn8-coverage').length,
            badge:node.closest('.ss-group').querySelector('.ss-group-coverage')?.textContent.replace(/[^\d/]/g,''),fits:(parts.length?parts:[value]).every(part=>{
              const owner=part.getBoundingClientRect(),ink=document.createRange();ink.selectNodeContents(part);
              const rects=[...ink.getClientRects()];
              return rects.length===1&&rects.every(text=>text.left>=owner.left-1&&text.right<=owner.right+1&&text.top>=owner.top-1&&text.bottom<=owner.bottom+1);
            })};
        });
        check('Recorded battle totals stay centered without repeating result coverage: '+language+'/'+scale+'x/'+confirmed+'/'+total+': '+JSON.stringify(count),
          count.parts===0&&count.fits&&count.metricCoverage===0&&count.centerDelta<=scale*1.25&&count.peerCenters.every(delta=>delta<=scale*0.5)&&
          count.text.replace(/[^\d/]/g,'')===String(total)&&count.badge===(confirmed<total?confirmed+'/'+total:undefined));
      }

    }finally{await page.close();}
  }));
  const rejectedScale=scaleResults.find(result=>result.status==='rejected');
  if(rejectedScale)throw rejectedScale.reason;
};
