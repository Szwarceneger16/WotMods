/* Sorting frames the exact displayed result while native arrow lanes stay fixed. */
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({page,scale,check})=>{
  const metrics=['xp_base','xp_received','battle_wn8'],groups=['maps','vehicles','tiers'];
  const native=await page.addStyleTag({content:
    '.ss-metric-number > .ss-extreme-link-cue { display:block !important; }'+
    '.ss-metric-battle-link > span:not(.ss-control-label):not(.ss-extreme-link-cue) { width:0 !important; height:0 !important; font-size:0 !important; overflow:hidden !important; }'});
  async function audit(metric,statistic){
    return page.locator('#ss-groups .ss-group').evaluateAll((cards,{metric,statistic,scale})=>cards
      .sort((left,right)=>Number(left.getAttribute('data-list-index'))-Number(right.getAttribute('data-list-index'))).map(card=>{
      const row=card.querySelector('.ss-metric-row[data-ss-metric="'+metric+'"]'),
        index=statistic==='min'?1:statistic==='max'?3:2,cell=row.children[index],style=getComputedStyle(cell),box=cell.getBoundingClientRect();
      const figure=cell.querySelector('.ss-extreme-number')||cell,range=document.createRange();range.selectNodeContents(figure);
      const ink=range.getBoundingClientRect(),button=cell.querySelector('.ss-metric-battle-link'),cue=cell.querySelector('.ss-extreme-link-cue');
      const marks=[...card.querySelectorAll('.ss-metric-row [data-ss-sort-active]')],others=[...card.querySelectorAll('.ss-metric-row > .ss-metric-number')].filter(node=>node!==cell);
      const baseline=window.__selectedCellBaseline[card.getAttribute('data-group-id')][metric][index-1];
      const action=button&&button.getBoundingClientRect(),arrow=cue&&cue.getBoundingClientRect(),
        figureBox=figure.getBoundingClientRect(),rowBox=row.getBoundingClientRect(),line=parseFloat(style.lineHeight);
      const contained=rect=>rect.left>=box.left-scale&&rect.right<=box.right+scale&&rect.top>=box.top-scale&&rect.bottom<=box.bottom+scale;
      return {value:figure.textContent.replace(/\s/g,''),selected:marks.length===1&&marks[0]===cell&&cell.getAttribute('data-ss-sort-active')===metric,
        headerNeutral:card.querySelectorAll('.ss-metric-head [data-ss-sort-active]').length===0,
        paint:style.boxShadow.includes('inset')&&style.boxShadow.includes('rgb(128, 183, 207)')&&style.backgroundColor==='rgb(37, 42, 35)',
        otherCellsNeutral:others.every(node=>getComputedStyle(node).boxShadow==='none'),
        geometry:Math.abs(box.width-baseline[0])<=scale&&Math.abs(box.height-baseline[1])<=scale&&
          ink.left>=box.left-scale&&ink.right<=box.right+scale&&ink.top>=box.top-scale&&ink.bottom<=box.bottom+scale,
        action:!button||figure===cell.firstChild&&figure.nextSibling===button&&!button.contains(figure)&&cue.parentNode===button&&
          style.display==='flex'&&style.flexWrap==='nowrap'&&getComputedStyle(figure).whiteSpace==='nowrap'&&
          Math.abs(action.width/scale-14)<=0.5&&Math.abs(action.height/scale-14)<=0.5&&action.height<=box.height-4*scale&&
          Math.abs((arrow.left-ink.right)/scale-5)<=0.5&&Math.abs((arrow.top+arrow.bottom-ink.top-ink.bottom)/scale)<=4&&
          arrow.right<=box.right-scale&&ink.height<=line+scale&&figureBox.height<=line+scale&&arrow.height<=line+scale&&
          contained(action)&&contained(arrow)&&Math.abs(box.height-rowBox.height)<=scale,
        returned:!button||!button.classList.contains('ss-source-returned')||getComputedStyle(cue).outlineColor==='rgb(231, 162, 59)'&&
          Math.abs(parseFloat(getComputedStyle(cue).outlineWidth)/scale-2)<=0.1};
    }),{metric,statistic,scale});
  }
  const passes=rows=>rows.length===4&&rows.every(row=>row.selected&&row.headerNeutral&&row.paint&&row.otherCellsNeutral&&row.geometry&&row.action&&row.returned)&&
    rows.map(row=>row.value).join('|')==='13289|0|-24|—';
  try{
    for(const width of [550,1200]){
      await page.evaluate(({width,scale,metrics,groups})=>{
        const payload=JSON.parse(JSON.stringify(__statLayoutFixture)),scope=payload.scopes.launch,sample=scope.maps[0];
        payload.account_key='synthetic-selected-cell-'+width+'-'+scale;payload.window_size=[width,1100];
        for(const group of groups){
          scope[group]=[13289,0,-24,null].map((value,index)=>{
            const item=JSON.parse(JSON.stringify(sample));item.id='selected-'+group+'-'+index;item.name='Synthetic '+index;
            item.extrema_battles={};item.stats.wn8=value;item.stats.wn8_count=value===null?0:1;
            for(const metric of metrics){
              item.stats[metric]={count:value===null?0:1,min:value,avg:value,max:value,sum:value};item.extrema_battles[metric]={};
              if(value!==null)for(const statistic of ['min','max'])item.extrema_battles[metric][statistic]={
                id:item.id+'-'+metric+'-'+statistic,metric,statistic,value,name:'Synthetic tank',map:'Synthetic map',started_at:1700000000};
            }
            return item;
          });
          scope.pagination[group]={page:0,pages:1,total:4,page_size:40};
          scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
        }
        model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);document.getElementById('ss-scope-launch').onclick();
      },{width,scale,metrics,groups});
      for(const [metric,group]of metrics.map((metric,index)=>[metric,groups[index]])){
        await page.evaluate(group=>document.getElementById('ss-group-'+group).onclick(),group);await frames(page);
        await page.evaluate(()=>{window.__selectedCellBaseline={};for(const card of document.querySelectorAll('#ss-groups .ss-group')){
          const rows={};for(const row of card.querySelectorAll('.ss-metric-row[data-ss-metric]'))rows[row.getAttribute('data-ss-metric')]=
            [...row.querySelectorAll(':scope > .ss-metric-number')].map(cell=>{const box=cell.getBoundingClientRect();return [box.width,box.height];});
          __selectedCellBaseline[card.getAttribute('data-group-id')]=rows;
        }});
        for(const statistic of ['min','avg','max']){
          await page.evaluate(({group,metric,statistic})=>{const payload=JSON.parse(model.payload);
            payload.scopes.launch.ordering[group]={metric,statistic,direction:'desc',chronology:'newest'};
            model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
          },{group,metric,statistic});await frames(page);
          const result=await audit(metric,statistic);
          check('Selected '+group+'/'+metric+'/'+statistic+' frames the exact zero, signed, missing or ordinary cell at '+width+'/'+scale+'x: '+JSON.stringify(result),passes(result));
        }
      }
      await page.locator('#ss-groups .ss-metric-row[data-ss-metric="battle_wn8"] .ss-sort-active-value .ss-metric-battle-link').first().evaluate(node=>node.classList.add('ss-source-returned'));
      check('The cool sort frame and amber returned-source arrow are distinct at '+width+'/'+scale+'x',passes(await audit('battle_wn8','max')));
    }
    const obsolete=await page.addStyleTag({content:'.ss-group .ss-extreme-cell.ss-sort-active-value { box-shadow:none !important; background:none !important; }'});
    check('The selected-cell guard rejects the obsolete suppression of the actual result frame at '+scale+'x',!passes(await audit('battle_wn8','max')));
    await obsolete.evaluate(node=>node.remove());
    await page.locator('#ss-groups .ss-metric-head .ss-metric-number').first().evaluate(node=>node.setAttribute('data-ss-sort-active','battle_wn8'));
    check('The selected-cell guard rejects a generic statistic heading marker at '+scale+'x',!passes(await audit('battle_wn8','max')));
    await page.locator('#ss-groups .ss-metric-head [data-ss-sort-active]').evaluateAll(nodes=>nodes.forEach(node=>node.removeAttribute('data-ss-sort-active')));
    check('Restoring the cell decoration and neutral headings restores exact selection at '+scale+'x',passes(await audit('battle_wn8','max')));
  }finally{await native.evaluate(node=>node.remove());}
};
