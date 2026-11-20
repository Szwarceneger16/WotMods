/* Premium resource deltas use saved/original values, independent of received totals. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:4200,height:2600},viewport:{width:4200,height:2600,scale:1}});
  const seed=await page.evaluate(()=>JSON.parse(model.payload));
  const cases=[
    {name:'new-explicit',original:false,absolute:{premiumCredits:6614,premiumXP:113,premiumFreeXP:6,premiumCrewXP:113},expected:['+6614','+113','+6','+113']},
    {name:'historical-originals',original:true,absolute:{},expected:['+6614','+113','—','—']},
    {name:'factor-only-unknown',original:false,absolute:{},expected:['—','—','—','—']},
    {name:'known-zero',original:false,absolute:{premiumCredits:0,premiumXP:0,premiumFreeXP:0,premiumCrewXP:0},expected:['0','0','0','0']},
    {name:'stored-authoritative',original:true,absolute:{premiumCredits:7,premiumXP:9,premiumFreeXP:2,premiumCrewXP:3},expected:['+7','+9','+2','+3']},
  ];
  try{
    for(const scale of [1,2])for(const language of ['en','pl'])for(const scenario of cases){
      const messages=catalogs[language];
      await page.evaluate(({seed,scale,language,messages,scenario})=>{
        const payload=JSON.parse(JSON.stringify(seed)),scope=payload.scopes.launch,battle=scope.battles[0];
        payload.account_key='synthetic-premium-'+language+'-'+scale+'-'+scenario.name;
        payload.localization={language,messages};payload.window_size=[1900,1050];
        payload.viewport={width:4200,height:2600,scale};payload.appearance={wide_card_widths:{battles:500}};
        scope.period_id='synthetic-premium-period';scope.data_revision='synthetic-premium-revision-'+scenario.name;
        scope.ordering.battles={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
        scope.pagination.battles={page:0,pages:1,total:1,page_size:40};
        battle.id='synthetic-premium-battle';battle.xp_bonus_applied=false;
        battle.stats.battles=battle.stats.observed_battles=1;
        battle.stats.xp_base=scenario.original?{count:1,min:225,avg:225,max:225,sum:225}:{count:0,min:null,avg:null,max:null,sum:null};
        battle.stats.xp_received={count:1,min:999999,avg:999999,max:999999,sum:999999};
        battle.stats.free_xp=99999;
        battle.stats.currencies.credits={income:999999999,income_count:1,costs:100,costs_count:1,net:999999899,net_count:1,
          income_base:scenario.original?13228:null,income_base_count:scenario.original?1:0};
        battle.details={bonuses:Object.assign({appliedPremiumCreditsFactor100:150,appliedPremiumXPFactor100:150,
          appliedPremiumTmenXPFactor100:150,wotPlusCredits:2976,wotPlusXP:51,wotPlusFreeXP:3,wotPlusCrewXP:51},scenario.absolute)};
        scope.battles=[battle];model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        document.getElementById('ss-group-battles').click();document.querySelector('.ss-battle .ss-more-button').click();
      },{seed,scale,language,messages,scenario});await frames(page);
      const result=await page.locator('.ss-more-bonuses').evaluate(table=>{
        const row=table.querySelector('[data-bonus-source="premium"]');
        const plus=table.querySelector('[data-bonus-source="wotPlusCredits"]');
        const values=node=>Array.from(node.querySelectorAll('.ss-bonus-number')).map(cell=>cell.textContent.replace(/\s/g,''));
        const cells=Array.from(row.querySelectorAll('.ss-bonus-number'));
        return {premium:values(row),plus:values(plus),count:table.querySelectorAll('[data-bonus-source="premium"]').length,
          label:row.querySelector('.ss-bonus-label').textContent,factors:row.querySelectorAll('.ss-bonus-factor').length,
          fits:cells.every(cell=>{const box=cell.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(cell);const ink=range.getBoundingClientRect();
            return ink.left>=box.left-1&&ink.right<=box.right+1&&ink.top>=box.top-1&&ink.bottom<=box.bottom+1;}),
          saved:JSON.parse(model.payload).scopes.launch.battles[0].details.bonuses};
      });
      const caption=language+'/'+scale+'x/'+scenario.name;
      check('Premium row shows absolute deltas or honest unknowns '+caption+' '+JSON.stringify(result.premium),
        result.count===1&&result.premium.join('|')===scenario.expected.join('|')&&result.factors===0&&result.fits);
      check('Premium calculation leaves distinct Plus rewards and stored details intact '+caption,
        result.plus.join('|')==='+2976|+51|+3|+51'&&result.label===messages['more.bonus.premium.credits'].split(':')[0]&&
        Object.keys(scenario.absolute).every(key=>result.saved[key]===scenario.absolute[key])&&
        Object.keys(result.saved).filter(key=>key.indexOf('premium')===0).length===Object.keys(scenario.absolute).length);
    }
  }finally{await page.close();}
};
