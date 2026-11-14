/* Wide presets change both fixed-width columns together at one threshold. */
module.exports=async ({browser,nativeHost,check})=>{
  const base={vehicles:560,maps:560,tiers:520,battles:500};
  const frames=page=>page.evaluate(()=>new Promise(resolve=>{
    let remaining=10;function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
  }));
  for(const scale of [1,2]) {
    const height=1400*scale;
    const page=await nativeHost(browser,{initialViewport:{width:2200*scale,height},viewport:{width:2200*scale,height,scale},realTimers:true});
    try {
      await page.evaluate(()=>{
        const payload=JSON.parse(model.payload);payload.window_size=[2200,1120];payload.account_key='synthetic-wide-account';
        payload.appearance={wide_card_widths:{vehicles:800,maps:800,tiers:800,battles:800}};
        const scope=payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));
        scope.from_point=scope.to_point='';scope.time_points=[];
        for(const group of ['vehicles','maps','tiers','battles']) {
          const sample=scope[group][0];scope[group]=Array.from({length:8},(_,index)=>{
            const card=JSON.parse(JSON.stringify(sample));card.id='wide-'+group+'-'+index;card.name='Synthetic tank '+index;
            card.started_at=1900000000-index;
            if(group==='battles') {
              card.details={pass_points:{credited:25,battle:5,missions:20},bonuses:{wotPlusCredits:3456,wotPlusXP:64},missions:{}};
              for(let mission=0;mission<(index===0?5:2);mission++) card.details.missions['daily:'+mission]={kind:'daily',name:'Synthetic objective '+mission,
                status:'completed',description:'Complete this synthetic objective and return to the garage.'};
            }
            return card;
          });
          if(scope.pagination) scope.pagination[group]={page:0,page_size:40,total:8,pages:1};
        }
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      });
      await page.locator('#ss-scope-manual').click();
      async function viewport(wide,offset) {
        // The owned rail replaces the old native gutter. Measure the painted
        // content inset so ±2 targets the real card threshold at either scale.
        const inset=await page.evaluate(scale=>{
          const panel=document.getElementById('grz-session-stats').getBoundingClientRect();
          const groups=document.getElementById('ss-groups').getBoundingClientRect();
          return (panel.width-groups.width)/scale;
        },scale);
        const width=Math.round((2*wide+64+inset+offset)*scale+20);
        await page.setViewportSize({width,height});
        await page.evaluate(width=>{const payload=JSON.parse(model.payload);payload.viewport.width=width;
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},width);
        await frames(page);
      }
      async function verify(group,width,caption) {
        const value=await page.locator('#ss-groups').evaluate((node,scale)=>{
          const cards=[...node.querySelectorAll('.ss-group')].sort((a,b)=>Number(a.dataset.listIndex)-Number(b.dataset.listIndex));
          return {two:node.classList.contains('ss-two-columns'),cards:cards.map(card=>{
            const box=card.getBoundingClientRect(),button=card.querySelector('.ss-more-button');
            return {id:card.dataset.groupId,left:box.left/scale,right:box.right/scale,top:box.top/scale,bottom:box.bottom/scale,width:box.width/scale,
              open:button && button.getAttribute('aria-expanded')==='true'};
          })};
        },scale);
        const cards=value.cards,overlap=cards.some((card,index)=>cards.slice(index+1).some(other=>
          Math.min(card.right,other.right)-Math.max(card.left,other.left)>1 && Math.min(card.bottom,other.bottom)-Math.max(card.top,other.top)>1));
        const correct=value.two && cards.length===8 && cards.every(card=>Math.abs(card.width-width)<=1) &&
          new Set(cards.map(card=>Math.round(card.left))).size===2 && !overlap &&
          cards.every((card,index)=>!index || card.top>=cards[index-1].top-1);
        check('Two '+group+' columns use fixed '+width+'px cards '+caption+' at'+(scale*100)+'%'+(correct?'':' '+JSON.stringify(value)),correct);
        if(group==='battles') check('Wide-preset changes preserve independently opened battle panels '+caption,
          cards.filter(card=>card.open).map(card=>card.id).join('|')==='wide-battles-0|wide-battles-1');
      }
      for(const group of Object.keys(base)) {
        await page.locator('#ss-group-'+group).click();await frames(page);
        if(group==='battles') {
          for(const id of ['wide-battles-0','wide-battles-1']) await page.locator('[data-group-id="'+id+'"] .ss-more-button').click();
          await frames(page);
        }
        await viewport(800,-2);await verify(group,base[group],'just below the wide threshold');
        await viewport(800,2);await verify(group,800,'just above the wide threshold');
        await viewport(800,140);await verify(group,800,'without stretching at a larger viewport');
      }
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.appearance.wide_card_widths.battles=900;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});
      await viewport(900,-2);await verify('battles',base.battles,'below a configured900px threshold');
      await viewport(900,2);await verify('battles',900,'above a configured900px threshold');
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);delete payload.appearance.wide_card_widths;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});
      for(const group of Object.keys(base)) {
        await page.locator('#ss-group-'+group).click();await frames(page);
        await viewport(720,-2);await verify(group,base[group],'below the default720px threshold');
        await viewport(720,2);await verify(group,720,'above the default720px threshold');
        await viewport(720,140);await verify(group,720,'without stretching beyond the default720px threshold');
      }
    } finally {await page.close();}
  }
};
