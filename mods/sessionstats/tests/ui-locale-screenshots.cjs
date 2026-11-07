/* Synthetic locale QA. Captures stay outside release/source inputs; bounded
   log chunks let the existing CI job expose them without changing its workflow. */
const fs=require('fs'),path=require('path'),os=require('os'),zlib=require('zlib'),crypto=require('crypto');
const languages=['en','pl','de','fr','es','ru','uk'];
const groups=['vehicles','maps','tiers','battles'];
const objectives={
  en:'Cause damage to enemy vehicles and finish among the top players in both teams.',
  pl:'Zadaj uszkodzenia pojazdom przeciwnika i znajdź się wśród najlepszych graczy obu drużyn.',
  de:'Füge gegnerischen Fahrzeugen Schaden zu und gehöre zu den besten Spielern beider Teams.',
  fr:'Infligez des dégâts aux véhicules ennemis et terminez parmi les meilleurs joueurs des deux équipes.',
  es:'Causa daño a los vehículos enemigos y termina entre los mejores jugadores de ambos equipos.',
  ru:'Нанесите урон технике противника и войдите в число лучших игроков обеих команд.',
  uk:'Завдайте шкоди ворожій техніці та увійдіть до числа найкращих гравців обох команд.',
};
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));

async function audit(page,scale,group) {
  return page.evaluate(({scale,group})=>{
    const panel=document.getElementById('grz-session-stats'),root=panel.getBoundingClientRect();
    const issues=[];
    const visible=node=>{const box=node.getBoundingClientRect();return box.width>0 && box.height>0;};
    const limit=1.5*scale;
    for(const node of panel.querySelectorAll('*')) {
      const box=node.getBoundingClientRect();
      if(visible(node) && (box.left<root.left-limit || box.right>root.right+limit)) {
        issues.push({kind:'window-overflow',className:node.className,text:node.textContent.slice(0,100)});
      }
    }
    const cards=[...panel.querySelectorAll('#ss-groups .ss-group')];
    for(let i=0;i<cards.length;i++) for(let j=i+1;j<cards.length;j++) {
      const a=cards[i].getBoundingClientRect(),b=cards[j].getBoundingClientRect();
      if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>limit &&
        Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>limit) issues.push({kind:'overlapping-cards',i,j});
    }
    const first=panel.querySelector('[data-list-index="0"]');
    const headerNodes=[...first.querySelector('.ss-group-header').children].filter(visible);
    for(let i=0;i<headerNodes.length;i++) for(let j=i+1;j<headerNodes.length;j++) {
      const a=headerNodes[i].getBoundingClientRect(),b=headerNodes[j].getBoundingClientRect();
      if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>limit &&
        Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>limit) issues.push({kind:'overlapping-header-controls',i,j});
    }
    const selectors=[
      '.ss-control-label','.ss-group-title','.ss-group-subtitle','.ss-more-mission-name strong',
      '.ss-more-mission-status','.ss-more-label','.ss-bonus-number','.ss-bonus-label','.ss-more-amount',
      '.ss-money-label','.ss-metric-row .ss-metric-number','.ss-money-value .ss-cell-value','.ss-cell-coverage','.ss-battle-value',
    ];
    for(const label of panel.querySelectorAll('.ss-more-pass .ss-more-label')) {
      const walker=document.createTreeWalker(label,NodeFilter.SHOW_TEXT);
      let node;
      while((node=walker.nextNode())) for(const word of node.textContent.matchAll(/\S+/g)) {
        const range=document.createRange();range.setStart(node,word.index);range.setEnd(node,word.index+word[0].length);
        const fragments=[...range.getClientRects()];
        if(fragments.some(rect=>Math.abs(rect.top-fragments[0].top)>limit)) issues.push({kind:'split-point-word',text:word[0]});
      }
    }
    for(const row of panel.querySelectorAll('.ss-bonus-row')) {
      const cells=[...row.children].filter(visible);
      for(let i=0;i<cells.length;i++) for(let j=i+1;j<cells.length;j++) {
        const a=cells[i].getBoundingClientRect(),b=cells[j].getBoundingClientRect();
        if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>limit &&
          Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>limit) {
          issues.push({kind:'overlapping-bonus-cells',heading:row.classList.contains('ss-bonus-head'),i,j});
        }
      }
    }
    for(const symbol of panel.querySelectorAll('.ss-info-symbol')) {
      if(!visible(symbol)) continue;
      const range=document.createRange();range.selectNodeContents(symbol);
      const ink=range.getBoundingClientRect(),button=symbol.closest('button').getBoundingClientRect();
      if(ink.width<=0 || ink.height<=0 || ink.left<button.left-limit || ink.right>button.right+limit ||
        ink.top<button.top-limit || ink.bottom>button.bottom+limit) issues.push({kind:'unreadable-info-symbol'});
    }
    for(const node of panel.querySelectorAll(selectors.join(','))) {
      if(!visible(node)) continue;
      // Mission status can contain a second explanatory line; inspect each
      // text node so a wrapped paragraph is not mistaken for a clipped value.
      const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);
      const box=node.getBoundingClientRect(),style=getComputedStyle(node);
      let textNode;
      while((textNode=walker.nextNode())) {
        if(!textNode.textContent.trim()) continue;
        const range=document.createRange();range.selectNodeContents(textNode);
        for(const rect of range.getClientRects()) if(rect.left<box.left-limit || rect.right>box.right+limit) {
          issues.push({kind:'clipped-text',className:node.className,text:textNode.textContent.slice(0,100)});break;
        }
      }
      const minFont=node.matches('.ss-money-value .ss-cell-value') ? 13 :
        node.matches('.ss-metric-row .ss-metric-number') ? 14 : node.matches('.ss-battle-value') ? 16 : 11;
      if(parseFloat(style.fontSize)/scale<minFont) issues.push({kind:'small-text',className:node.className,text:node.textContent.slice(0,100)});
    }
    const more=first.querySelector('.ss-more-panel');
    const matrix=more && more.querySelector('.ss-more-bonuses');
    const normalize=text=>text.replace(/\s/g,'');
    const allText=normalize(first.textContent);
    if(!allText.includes('12345678') || !allText.includes('10420') || !allText.includes('123456')) {
      issues.push({kind:'missing-full-values'});
    }
    if(group==='battles' && (!matrix || !visible(matrix))) issues.push({kind:'missing-bonus-matrix'});
    const credits=first.querySelector('.ss-money-row');
    const values=[...credits.querySelectorAll('.ss-cell-value')].map(node=>normalize(node.textContent));
    const counts=[...credits.querySelectorAll('.ss-cell-coverage')].map(node=>normalize(node.textContent));
    if(values.join('|')!=='24691356|-12345678|+12345678') issues.push({kind:'incomplete-finance-values',values});
    if(group!=='battles' && counts.join('|')!=='1/4|2/4|3/4') issues.push({kind:'missing-finance-coverage',counts});
    const detail=first.querySelector('.ss-details'),performance=detail.querySelector('.ss-performance').getBoundingClientRect(),
      economy=detail.querySelector('.ss-economy').getBoundingClientRect(),detailBox=detail.getBoundingClientRect();
    if(first.getBoundingClientRect().width/scale>=599 &&
      (performance.right>economy.left+limit || economy.width/detailBox.width>=0.55 || performance.width/detailBox.width<=0.45)) {
      issues.push({kind:'unbalanced-card-finance',performance:performance.width/scale,economy:economy.width/scale});
    }
    const columns=panel.querySelector('.ss-card-columns');
    const axis=columns && getComputedStyle(columns,':before');
    const arrow=columns && getComputedStyle(columns,':after');
    const two=document.getElementById('ss-groups').classList.contains('ss-two-columns');
    if(two && (!axis.backgroundImage.includes('linear-gradient') || axis.backgroundRepeat!=='repeat-y' ||
      parseFloat(axis.height)<=0 || arrow.content==='none' || parseFloat(arrow.width)<=0 ||
      cards.some(card=>{const line=getComputedStyle(card,':before');return !line.backgroundImage.includes('linear-gradient') ||
        line.backgroundRepeat!=='repeat-x' || parseFloat(line.width)<=0;}))) issues.push({kind:'missing-card-axis'});
    const canonical=cards.slice().sort((a,b)=>Number(a.dataset.listIndex)-Number(b.dataset.listIndex));
    if(two && canonical[1].getBoundingClientRect().top<=canonical[0].getBoundingClientRect().top+scale) issues.push({kind:'missing-card-stagger'});
    return {issues,language:document.documentElement.lang,cards:cards.length,
      logicalWidth:root.width/scale,columns:two ? 2 : 1,
      expanded:group==='battles' ? first.querySelector('.ss-more-button').getAttribute('aria-expanded')==='true' : null,
      cardWidth:first.getBoundingClientRect().width/scale,
      narrowCards:document.getElementById('ss-groups').classList.contains('ss-narrow-cards')};
  },{scale,group});
}

module.exports=async function ({browser,nativeHost,check}) {
  const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'grz-locale-qa-'));
  const screenshots=[],audits=[];
  const modes=[
    {name:'narrow',width:720,scale:1,gameWidth:1920,gameHeight:1300,capture:true,columns:1},
    {name:'wide',width:1400,scale:1,gameWidth:2200,gameHeight:1300,capture:true,columns:2},
    {name:'scaled-200',width:720,scale:2,gameWidth:3840,gameHeight:2560,capture:false,columns:1},
    {name:'floating-470',width:470,scale:1,gameWidth:2400,gameHeight:1300,capture:false,columns:1},
    {name:'configured-480',width:1200,cardWidth:480,scale:1,gameWidth:2400,gameHeight:1300,capture:false,columns:2},
  ];
  try {
    for(const language of languages) for(const mode of modes) {
      const page=await nativeHost(browser,{
        initialViewport:{width:mode.gameWidth,height:mode.gameHeight},
        viewport:{width:mode.gameWidth,height:mode.gameHeight,scale:mode.scale},
      });
      try {
        await page.evaluate(({language,messages,mode,objective})=>{
          const payload=JSON.parse(model.payload);
          payload.window_size=[mode.width,1120];
          if(mode.cardWidth) payload.appearance={card_widths:{vehicles:mode.cardWidth,maps:mode.cardWidth,tiers:mode.cardWidth,battles:mode.cardWidth}};
          payload.localization={language,selected:language,messages};
          const timeline=payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));
          timeline.from_point=timeline.to_point='';timeline.time_points=[];
          const original=timeline.battles[0];
          timeline.battles=Array.from({length:4},(_,index)=>{
            const battle=JSON.parse(JSON.stringify(original));
            battle.id='locale-fixture-'+index;
            battle.name='Pz.Kpfw. Tiger II mit 10,5 cm Kw.K L/68';
            battle.map='Ruinberg · Pearl River · Westfield';
            battle.outcome=index%2 ? 'loss' : 'win';
            battle.stats.xp_base={count:1,min:123456,avg:123456,max:123456,sum:123456};
            battle.stats.wn8=10420;battle.stats.wn8_count=1;
            battle.stats.currencies.credits={income:24691356,costs:12345678,net:index%2 ? -12345678 : 12345678,
              income_count:1,costs_count:1,net_count:1};
            battle.details={pass_points:{credited:33,battle:8,missions:10,vehicle:15},
              missions:{
                'daily:fixture':{kind:'daily',name:messages['more.kind.daily']+' · '+messages['more.mission.completed'],status:'completed',description:objective},
                'weekly:fixture':{kind:'weekly',name:messages['more.kind.weekly']+' · '+messages['more.mission.progress'],status:'progress',description:objective,before:12,after:16},
                'personal:fixture':{kind:'personal',name:'Operation Fossa — '+messages['more.mission.honors'],operation:'Operation Fossa',status:'honors',description:objective},
                'challenge:fixture':{kind:'crucible',name:messages['more.kind.crucible']+' · '+messages['more.stage'].replace('{0}','15'),stage:15,status:'failed',description:objective},
              },active_crucible:'challenge:fixture',
              bonuses:{dailyXPFactor10:20,eventCrystal:43,eventCredits:50000,boosterCredits:26943,boosterXP:136,
                boosterFreeXP:28,boosterTMenXP:544,wotPlusCredits:8083,wotPlusXP:41,wotPlusFreeXP:2,wotPlusCrewXP:164}};
            return battle;
          });
          if(timeline.pagination && timeline.pagination.battles) timeline.pagination.battles={page:0,page_size:40,total:4,pages:1};
          for(const group of ['vehicles','maps','tiers']) {
            const original=timeline[group][0];
            timeline[group]=Array.from({length:4},(_,index)=>{
              const item=JSON.parse(JSON.stringify(original));
              item.id='locale-'+group+'-'+index;
              item.name=group==='vehicles' ? 'Pz.Kpfw. Tiger II mit 10,5 cm Kw.K L/68' :
                group==='maps' ? 'Ruinberg · Pearl River · Westfield' : 'VIII';
              item.stats.battles=item.stats.observed_battles=4;
              item.stats.xp_base={count:3,min:123456,avg:123456,max:123456,sum:370368};
              item.stats.battle_wn8={count:2,min:10420,avg:10420,max:10420,sum:20840};
              item.stats.wn8=10420;item.stats.wn8_count=3;
              item.stats.currencies.credits={income:24691356,costs:12345678,net:12345678,
                income_count:1,costs_count:2,net_count:3};
              for(const field of ['income','costs','net']) item.stats.currencies.bonds[field+'_count']=4;
              return item;
            });
            if(timeline.pagination && timeline.pagination[group]) timeline.pagination[group]={page:0,page_size:40,total:4,pages:1};
          }
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{language,messages:catalogs[language],mode,objective:objectives[language]});
        await page.locator('#ss-scope-manual').click();
        for(const group of groups) {
          await page.locator('#ss-group-'+group).click();
          if(group==='battles') await page.locator('[data-list-index="0"] .ss-more-button').click();
          await page.mouse.move(mode.gameWidth-10,mode.gameHeight-10);
          await frames(page);
          const result=await audit(page,mode.scale,group);
          audits.push({locale:language,group,mode:mode.name,expectedColumns:mode.columns,configuredCardWidth:mode.cardWidth || null,...result});
          if(mode.capture && ['vehicles','battles'].includes(group)) {
            // Show both control bars and the compact summary together with
            // Vehicles or the expanded first battle's details.
            await page.locator('#ss-scroll').evaluate(scroll=>{scroll.scrollTop=0;});
            await frames(page);
            const name='session-stats-'+language+'-'+group+'-'+mode.name+'.jpg';
            const data=await page.locator('#grz-session-stats').screenshot({path:path.join(directory,name),type:'jpeg',quality:74,animations:'disabled'});
            screenshots.push({name,language,group,mode:mode.name,width:mode.width,scale:mode.scale,mime_type:'image/jpeg',bytes:data.length,sha256:sha(data),data:data.toString('base64')});
          }
        }
      } finally { await page.close(); }
    }
    const metadata={schema_version:1,synthetic:true,renderer:'Chromium; native WoT APIs are test doubles',
      screenshot_count:screenshots.length,screenshot_bytes:screenshots.reduce((sum,file)=>sum+file.bytes,0),
      screenshots:screenshots.map(({data,...file})=>file),audits};
    console.log('GRZ_LOCALE_QA_METADATA_V1 '+JSON.stringify(metadata));
    const bundle=zlib.gzipSync(Buffer.from(JSON.stringify({...metadata,screenshots})),{level:9});
    const encoded=bundle.toString('base64'),chunkSize=12000,parts=Math.ceil(encoded.length/chunkSize);
    console.log('GRZ_LOCALE_QA_BUNDLE_V1 BEGIN '+parts+' '+bundle.length+' '+sha(bundle));
    for(let index=0;index<parts;index++) console.log('GRZ_LOCALE_QA_BUNDLE_V1 DATA '+(index+1)+'/'+parts+' '+encoded.slice(index*chunkSize,(index+1)*chunkSize));
    console.log('GRZ_LOCALE_QA_BUNDLE_V1 END');
    check('All seven locales produce vehicle and battle screenshots at narrow and wide widths',screenshots.length===28);
    check('Locale screenshot payload stays below four MiB',metadata.screenshot_bytes<=4*1024*1024);
    check('Encoded locale screenshot log bundle stays below four MiB',encoded.length<=4*1024*1024);
    for(const result of audits) check('Localized '+result.group+' cards remain readable without overflow or overlap: '+result.language+' '+result.mode+
      (result.issues.length ? ' '+JSON.stringify(result.issues.slice(0,8)) : ''),
      result.issues.length===0 && (result.group!=='battles' || result.expanded) && result.cards===4 && result.language===result.locale &&
      result.columns===result.expectedColumns &&
      (!result.configuredCardWidth || Math.abs(result.cardWidth-result.configuredCardWidth)<=1) &&
      (!['floating-470','configured-480'].includes(result.mode) || result.narrowCards));
  } finally { fs.rmSync(directory,{recursive:true,force:true}); }
};
