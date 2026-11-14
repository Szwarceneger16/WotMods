/* Compact battle details use two readable mission cells instead of empty sides. */
const fs=require('fs'),path=require('path');
async function settled(page,scale,width){
  await page.waitForFunction(({scale,width})=>{
    const block=document.querySelector('.ss-more-mission-block'),body=block&&block.querySelector('.ss-more-body');
    if(!body||!window.__nativeSize||__nativeSize[0]!==width*scale)return false;
    const bounds=block.getBoundingClientRect(),cards=[...body.querySelectorAll('.ss-more-mission')];
    const count=cards.length>1&&bounds.width/scale>=440?2:1;
    return Number(body.getAttribute('data-mission-columns'))===count&&cards.every(card=>{
      const box=card.getBoundingClientRect();return box.width>100*scale&&box.height>0&&box.left>=bounds.left-scale&&box.right<=bounds.right+scale;
    });
  },{scale,width});
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
}
module.exports=async({browser,nativeHost,check})=>{
  const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:4600,height:2600},viewport:{width:4600,height:2600,scale:1}});
  try{
    const seed=await page.evaluate(()=>JSON.parse(model.payload));
    for(const scale of [1,2])for(const [language,messages]of Object.entries(catalogs)){
      await page.evaluate(({seed,scale,language,messages})=>{
        const data=JSON.parse(JSON.stringify(seed)),scope=data.scopes.launch,battle=scope.battles[0];
        data.account_key='synthetic-mission-grid-'+language+'-'+scale;data.window_size=[2100,1100];
        data.viewport={width:4600,height:2600,scale};data.localization={language,messages};
        data.appearance={wide_card_widths:{battles:500}};
        scope.period_id='synthetic-mission-grid-period';scope.data_revision='same-mission-grid-data';
        scope.pagination.battles={page:0,pages:1,total:1,page_size:40};
        battle.id='synthetic-mission-grid-battle';battle.details={bonuses:{wotPlusCredits:6055,wotPlusXP:74,wotPlusFreeXP:4,wotPlusCrewXP:74,
          appliedPremiumCreditsFactor100:150,appliedPremiumXPFactor100:150},missions:{}};
        for(let index=0;index<4;index++)battle.details.missions['objective-'+index]={kind:'daily',
          name:messages['more.kind.daily']+' '+(index+1)+' — Synthetic objective',status:'completed',
          objectives:[{unit:'damage',label:messages['more.progress.unit.damage'],after:5000,target:5000,delta:2707}]};
        scope.battles=[battle];model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();
        document.getElementById('ss-group-battles').click();document.querySelector('.ss-battle .ss-more-button').click();
      },{seed,scale,language,messages});await settled(page,scale,2100);
      const audit=await page.locator('.ss-more-mission-block').evaluate((block,scale)=>{
        const box=block.getBoundingClientRect(),body=block.querySelector('.ss-more-body'),cards=[...block.querySelectorAll('.ss-more-mission')],rows=[...body.children];
        const bounds=cards.map(card=>card.getBoundingClientRect()),failures=[];
        if(Number(body.getAttribute('data-mission-columns'))!==2||rows.length!==2||rows.some(row=>row.children.length!==2))failures.push('missing-two-columns');
        for(let index=0;index<4;index++){
          const current=bounds[index];
          if(current.width/scale<210||current.left<box.left-scale||current.right>box.right+scale)failures.push('unreadable-cell-width');
          if(!cards[index].textContent.includes('Synthetic objective')||!cards[index].textContent.includes(String(index+1)))failures.push('changed-order');
          if(index%2===0&&Math.abs(current.top-bounds[index+1].top)>scale)failures.push('different-row-top');
          if(index%2===0&&current.right>bounds[index+1].left-scale)failures.push('overlapping-columns');
          for(const node of cards[index].querySelectorAll('.ss-more-mission-name,.ss-more-mission-status')){
            const frame=node.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);
            if([...range.getClientRects()].some(text=>text.width>0&&(text.left<frame.left-scale||text.right>frame.right+scale||text.top<frame.top-scale||text.bottom>frame.bottom+scale)))failures.push('clipped-text');
          }
        }
        const fullHeight=bounds.reduce((total,b)=>total+b.height,0),missionHeight=box.height;
        if(missionHeight>=fullHeight*0.85)failures.push('unreclaimed-space');
        window.__missionGridRows=rows;window.__missionGridCards=cards;
        return {failures,width:box.width/scale,cellWidth:bounds[0].width/scale,height:missionHeight/scale,oneColumnContent:fullHeight/scale};
      },scale);
      check('Compact More fills two mission columns in '+language+' at'+scale*100+'%: '+JSON.stringify(audit),audit.failures.length===0);
      await page.evaluate(()=>window.dispatchEvent(new Event('resize')));await settled(page,scale,2100);
      check('An unchanged mission layout retains its rows and mission nodes in '+language+' at'+scale*100+'%',
        await page.evaluate(()=>__missionGridRows.every(row=>row.isConnected)&&__missionGridCards.every(card=>card.isConnected)&&
          [...document.querySelector('.ss-more-mission-block .ss-more-body').children].every((row,index)=>row===__missionGridRows[index])));
      if(language==='en'){
        for(const width of [720,500,720,500]){
          await page.evaluate(width=>{const data=JSON.parse(model.payload);data.appearance.wide_card_widths.battles=width;
            model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();},width);
          const more=page.locator('.ss-battle .ss-more-button');
          if(await more.getAttribute('aria-expanded')!=='true')await more.click();await settled(page,scale,2100);
          const result=await page.locator('.ss-more-mission-block').evaluate(block=>({width:block.getBoundingClientRect().width/parseFloat(document.documentElement.style.fontSize),
            count:Number(block.querySelector('.ss-more-body').getAttribute('data-mission-columns')),cards:block.querySelectorAll('.ss-more-mission').length}));
          check('Mission rows reflow after a narrow/wide transition at'+width+'px/'+scale+'x: '+JSON.stringify(result),
            result.count===(width===500?2:1)&&result.cards===4);
        }
        await page.evaluate(()=>{const data=JSON.parse(model.payload);data.account_key+='-odd';
          data.scopes.launch.battles[0].details.missions.extra={kind:'daily',name:'Synthetic extra objective',status:'completed'};
          model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();});
        const oddMore=page.locator('.ss-battle .ss-more-button');
        if(await oddMore.getAttribute('aria-expanded')!=='true')await oddMore.click();await settled(page,scale,2100);
        check('An odd last mission uses the complete final row at'+scale*100+'%',await page.locator('.ss-more-mission-block').evaluate((block,scale)=>{
          const body=block.querySelector('.ss-more-body'),last=body.lastElementChild,box=block.getBoundingClientRect(),card=last.firstElementChild.getBoundingClientRect();
          return body.children.length===3&&last.children.length===1&&block.querySelectorAll('.ss-more-mission').length===5&&Math.abs(card.width-box.width)<=scale;
        },scale));
      }
    }
  }finally{await page.close();}
};
