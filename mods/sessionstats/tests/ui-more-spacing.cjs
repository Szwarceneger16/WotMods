/* Native column flow must size stacked More sections by content, not widths. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=8;
  function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:4600,height:2600},viewport:{width:4600,height:2600,scale:1}});
  try{
    await page.evaluate(()=>{
      window.__moreSpacingFixture=JSON.parse(model.payload);
      // Gameface can retain a vertical flex context when a paired row becomes
      // stacked. A width-valued basis would then reserve that amount as height.
      const style=document.createElement('style');style.textContent='.ss-more-columns-stacked{display:flex!important;flex-direction:column!important}';document.head.appendChild(style);
    });
    for(const scale of [1,2])for(const [language,messages] of Object.entries(languages)){
      await page.setViewportSize({width:2300*scale,height:1300*scale});
      await page.evaluate(({scale,language,messages})=>{
        const snapshot=JSON.parse(JSON.stringify(__moreSpacingFixture)),scope=snapshot.scopes.launch,battle=scope.battles[0];
        snapshot.account_key='more-spacing-'+scale+'-'+language;snapshot.window_size=[2100,1100];
        snapshot.viewport={width:2300*scale,height:1300*scale,scale};snapshot.localization={language,messages};
        snapshot.appearance={wide_card_widths:{battles:720}};scope.pagination.battles={page:0,pages:1,total:1,page_size:40};
        battle.id='more-spacing-battle';battle.name='Synthetic Heavy';battle.details={pass_points:{credited:25,battle:5,missions:20},
          bonuses:{eventCredits:12345678,eventXP:2345,eventFreeXP:1234567,eventCrystal:43,
            boosterCredits:20110,boosterXP:534,boosterFreeXP:108,boosterTMenXP:2134,
            orderCredits:56789,orderXP:345,orderFreeXP:210,orderTMenXP:678,
            wotPlusCredits:6033,wotPlusXP:160,wotPlusFreeXP:8,wotPlusCrewXP:160,
            appliedPremiumCreditsFactor100:150,appliedPremiumXPFactor100:150,dailyXPFactor10:20,additionalXPFactor10:30},
          missions:{daily:{kind:'daily',name:messages['more.kind.daily']+' — Synthetic daily mission with a readable objective',status:'completed'},
            personal:{kind:'personal',name:messages['more.kind.personal']+' — Synthetic personal objective with several readable words',status:'progress',description:'Synthetic mission progress description remains below the objective.'}}};
        scope.battles=[battle];model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);
        document.getElementById('ss-group-battles').click();document.querySelector('.ss-battle .ss-more-button').click();
      },{scale,language,messages});await frames(page);
      const widths=language==='en'?[720,500,800,500]:[720,500,800];
      for(const width of widths){
        await page.evaluate(width=>{const snapshot=JSON.parse(model.payload);snapshot.appearance.wide_card_widths.battles=width;
          model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);},width);await frames(page);
        const audit=await page.locator('.ss-more-panel').evaluate((panel,{scale,width})=>{
          const card=panel.closest('.ss-group'),columns=panel.querySelector('.ss-more-columns'),bonus=panel.querySelector('.ss-more-bonus-block'),missions=panel.querySelector('.ss-more-mission-block');
          const c=card.getBoundingClientRect(),b=bonus.getBoundingClientRect(),m=missions.getBoundingClientRect(),tables=bonus.querySelectorAll('.ss-more-table'),last=tables[tables.length-1].getBoundingClientRect();
          const paired=columns.classList.contains('ss-more-columns-paired'),gap=(m.top-last.bottom)/scale,failures=[];
          if(Math.abs(c.width/scale-width)>1||paired!==(width>=720))failures.push('layout-mode');
          if(paired?(Math.abs(b.top-m.top)>scale||b.right>m.left+scale):(gap<0||gap>12))failures.push('spacing');
          if(m.width/scale<(paired?180:480)||[b,m].some(box=>box.left<c.left-scale||box.right>c.right+scale))failures.push('section-width');
          for(const node of panel.querySelectorAll('.ss-bonus-number,.ss-bonus-label,.ss-more-mission-name strong,.ss-more-mission-status,.ss-more-mission-description')){
            const bounds=node.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);
            if(Array.from(range.getClientRects()).some(text=>text.width>0&&(text.left<bounds.left-scale||text.right>bounds.right+scale||text.top<bounds.top-scale||text.bottom>bounds.bottom+scale)))failures.push('clipped:'+node.textContent);
          }
          if(!panel.textContent.includes('+12\u00a0345\u00a0678')||!panel.textContent.includes('+1\u00a0234\u00a0567'))failures.push('truncated-amount');
          return {passed:!failures.length,paired,gap,bonusHeight:b.height/scale,bonusContentHeight:(last.bottom-b.top)/scale,missionWidth:m.width/scale,failures};
        },{scale,width});
        check('More details use content height and readable columns at '+width+'px, '+language+' '+scale*100+'%'+(audit.passed?'':': '+JSON.stringify(audit)),audit.passed);
      }
    }
  }finally{await page.close();}
};
