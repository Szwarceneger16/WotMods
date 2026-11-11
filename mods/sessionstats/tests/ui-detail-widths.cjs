/* Wider battle cards give missions space without stretching the bonus matrix. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:5000,height:2600},viewport:{width:5000,height:2600,scale:1}});
  try{
    for(const scale of [1,2])for(const [language,messages]of Object.entries(languages)){
      await page.evaluate(({scale,language,messages})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch,battle=scope.battles[0];
        payload.account_key='synthetic-detail-width-'+language+'-'+scale;payload.window_size=[2200,1100];
        payload.viewport={width:5000,height:2600,scale};payload.localization={language,messages};payload.appearance={wide_card_widths:{battles:720}};
        scope.period_id='synthetic-detail-width-period';scope.pagination.battles={page:0,pages:1,total:1,page_size:40};
        battle.id='synthetic-detail-width-battle';battle.name='Synthetic Heavy';battle.details={pass_points:{credited:25,battle:5,missions:20},
          bonuses:{eventCredits:110000,eventCrystal:24,wotPlusCredits:3456,wotPlusXP:64,wotPlusFreeXP:8,wotPlusCrewXP:96},
          missions:{daily:{kind:'daily',name:'Synthetic daily objective',status:'completed'},
            weekly:{kind:'weekly',name:'Synthetic weekly objective',status:'progress'},personal:{kind:'personal',name:'Synthetic personal objective',status:'honors'}}};
        scope.battles=[battle];model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{scale,language,messages});await page.locator('#ss-scope-launch').click();await page.locator('#ss-group-battles').click();
      await page.locator('.ss-battle .ss-more-button').click();await frames(page);
      const sizes=[];
      for(const width of [720,900]){
        await page.evaluate(width=>{const payload=JSON.parse(model.payload);payload.appearance.wide_card_widths.battles=width;
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},width);await frames(page);
        sizes.push(await page.locator('.ss-more-panel').evaluate((panel,scale)=>{
          const bonus=panel.querySelector('.ss-more-bonus-block').getBoundingClientRect(),missions=panel.querySelector('.ss-more-mission-block').getBoundingClientRect(),
            card=panel.closest('.ss-group').getBoundingClientRect();
          return {card:card.width/scale,bonus:bonus.width/scale,missions:missions.width/scale,
            paired:Math.abs(bonus.top-missions.top)<=1 && bonus.right<=missions.left+1,
            inline:[...panel.querySelectorAll('.ss-bonus-row')].every(row=>{
              const label=row.querySelector('.ss-bonus-label').getBoundingClientRect(),values=row.querySelector('.ss-bonus-values').getBoundingClientRect();
              return label.right<=values.left+1 && Math.min(label.bottom,values.bottom)>Math.max(label.top,values.top);
            }),
            rows:panel.querySelectorAll('.ss-more-mission').length};
        },scale));
      }
      check('Wide cards keep source labels beside fitted bonus columns and allocate extra space to missions in '+language+' at'+(scale*100)+'%: '+JSON.stringify(sizes),
        sizes.every((size,index)=>Math.abs(size.card-[720,900][index])<=1 && size.bonus<=487 && size.bonus>=307 && size.paired && size.inline && size.rows===3) &&
        Math.abs(sizes[1].bonus-sizes[0].bonus)<=1 && sizes[1].missions>=sizes[0].missions+178);
      if(language==='en' && scale===1){
        const longSizes=[];
        for(const width of [720,900]){
          await page.evaluate(width=>{const payload=JSON.parse(model.payload);payload.appearance.wide_card_widths.battles=width;
            payload.scopes.launch.battles[0].details.bonuses.eventCredits=12345678;
            model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},width);await frames(page);
          longSizes.push(await page.locator('.ss-more-panel').evaluate(panel=>{
            const block=panel.querySelector('.ss-more-bonus-block'),bonus=block.getBoundingClientRect(),missions=panel.querySelector('.ss-more-mission-block').getBoundingClientRect();
            return {long:block.classList.contains('ss-long-bonus-values'),bonus:bonus.width,missions:missions.width,
              paired:Math.abs(bonus.top-missions.top)<=1 && bonus.right<=missions.left+1};
          }));
        }
        check('Wide long-value bonuses keep486px while the mission column receives extra width: '+JSON.stringify(longSizes),
          longSizes.every(size=>size.long && Math.abs(size.bonus-486)<=1 && size.paired) &&
          Math.abs(longSizes[1].bonus-longSizes[0].bonus)<=1 && longSizes[1].missions>=longSizes[0].missions+178);
      }
      // Reproduce native engines that fail to wrap a rich bonus matrix and
      // resolve the mission flex basis to zero in a regular 500rem card.
      await page.evaluate(()=>{
        const payload=JSON.parse(model.payload),battle=payload.scopes.launch.battles[0];payload.window_size=[700,1100];payload.account_key+='-narrow';
        battle.details.bonuses.eventCredits=12345678;delete battle.details.bonuses.eventCrystal;
        battle.details.missions.personal.name='A long personal mission objective with several readable words';
        const style=document.createElement('style');style.id='synthetic-native-more-flex';
        style.textContent='.ss-more-columns{flex-wrap:nowrap!important}.ss-more-mission-block{flex-basis:0!important}';document.head.appendChild(style);
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      });await page.locator('.ss-battle .ss-more-button').click();await frames(page);
      const narrow=await page.locator('.ss-more-panel').evaluate((panel,scale)=>{
        const bonus=panel.querySelector('.ss-more-bonus-block').getBoundingClientRect(),missions=panel.querySelector('.ss-more-mission-block').getBoundingClientRect(),card=panel.closest('.ss-group').getBoundingClientRect();
        const name=panel.querySelector('.ss-more-mission-name strong'),range=document.createRange();range.selectNodeContents(name);
        const lines=[...range.getClientRects()];
        return {card:card.width/scale,missions:missions.width/scale,stacked:missions.top>=bonus.bottom-1,
          within:missions.left>=card.left-1 && missions.right<=card.right+1 && bonus.right<=card.right+1,
          readable:lines.length>0 && lines.every(line=>line.width/scale>20),resources:panel.querySelector('.ss-more-bonus-block').getAttribute('data-resource-count')};
      },scale);
      check('A 500rem card stacks long bonuses above readable missions without a bond column in '+language+' at'+(scale*100)+'%: '+JSON.stringify(narrow),
        Math.abs(narrow.card-500)<=1 && narrow.missions>=480 && narrow.stacked && narrow.within && narrow.readable && narrow.resources==='4');
      await page.evaluate(()=>{document.getElementById('synthetic-native-more-flex').remove();});
      await page.locator('#ss-background-transparency').focus();await page.locator('#ss-background-transparency').press('End');
      const percentage=await page.locator('#ss-background-transparency-value').evaluate((node,scale)=>{
        const box=node.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);const text=range.getBoundingClientRect();
        return {value:node.textContent,font:parseFloat(getComputedStyle(node).fontSize)/scale,fits:text.left>=box.left-1 && text.right<=box.right+1 && text.top>=box.top-1 && text.bottom<=box.bottom+1};
      },scale);
      check('The full transparency percentage has a larger readable font in '+language+' at'+(scale*100)+'%: '+JSON.stringify(percentage),
        percentage.value==='100%' && percentage.font>=14 && percentage.fits);
    }
  }finally{await page.close();}
};
