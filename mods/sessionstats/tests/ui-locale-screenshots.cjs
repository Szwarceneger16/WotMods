/* Synthetic locale QA. Captures stay outside release/source inputs; bounded
   log chunks let the existing CI job expose them without changing its workflow. */
const fs=require('fs'),path=require('path'),os=require('os'),zlib=require('zlib'),crypto=require('crypto');
const languages=['en','pl','de','fr','es','ru','uk'];
const groups=['vehicles','maps','tiers','battles'];
const samples={
  ordinary:{xp:456,wn8:1750,income:97531,costs:64321,net:33210},
  stress:{xp:123456,wn8:10420,income:24691356,costs:12345678,net:12345678},
};
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
const frames=page=>page.evaluate(()=>new Promise(resolve=>{
  let remaining=10;function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));

async function audit(page,mode,group) {
  return page.evaluate(({scale,group,sample,stress})=>{
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
      '.ss-control-label','.ss-group-title','.ss-group-subtitle','.ss-more-mission-name strong','.ss-more-mission-description','.ss-more-caption',
      '.ss-more-mission-status','.ss-more-label','.ss-bonus-number','.ss-bonus-label','.ss-more-amount',
      '.ss-money-label','.ss-metric-row .ss-metric-number','.ss-money-value .ss-cell-value','.ss-cell-coverage','.ss-battle-value','.ss-group-kpi .ss-kpi-value',
    ];
    for(const label of panel.querySelectorAll('.ss-more-pass .ss-more-label,.ss-bonus-head .ss-bonus-number')) {
      const walker=document.createTreeWalker(label,NodeFilter.SHOW_TEXT);
      let node;
      while((node=walker.nextNode())) for(const word of node.textContent.matchAll(/[^\s\u002d\u2010-\u2015]+/g)) {
        const range=document.createRange();range.setStart(node,word.index);range.setEnd(node,word.index+word[0].length);
        const fragments=[...range.getClientRects()];
        if(fragments.some(rect=>Math.abs(rect.top-fragments[0].top)>limit)) issues.push({kind:label.closest('.ss-bonus-head') ? 'split-bonus-heading-word' : 'split-point-word',text:word[0]});
      }
    }
    for(const row of panel.querySelectorAll('.ss-bonus-row')) {
      const cells=[...row.querySelectorAll('.ss-bonus-label,.ss-bonus-number')].filter(visible);
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
      if(node.matches('#ss-close > .ss-control-label[aria-hidden="true"]')) {
        const button=node.parentElement,color=getComputedStyle(button).color;
        const strokes=[':before',':after'].map(pseudo=>getComputedStyle(node,pseudo));
        if(!(button.getAttribute('aria-label') || '').trim() || parseFloat(style.fontSize)!==0 ||
          !strokes.every(stroke=>stroke.content==='""' && stroke.display==='block' &&
            parseFloat(stroke.width)>0 && parseFloat(stroke.height)>0 &&
            stroke.backgroundColor===color && stroke.transform!=='none')) {
          issues.push({kind:'unpainted-close-symbol'});
        }
        continue;
      }
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
    if(!allText.includes(String(sample.net)) || !allText.includes(String(sample.wn8)) || !allText.includes(String(sample.xp))) {
      issues.push({kind:'missing-full-values'});
    }
    if(group==='battles' && (!matrix || !visible(matrix))) issues.push({kind:'missing-bonus-matrix'});
    if(group==='battles') {
      const columns=more.querySelector('.ss-more-columns'),missions=more.querySelector('.ss-more-mission-block'),
        pass=more.querySelector('.ss-more-pass-block'),bonus=more.querySelector('.ss-more-bonus-block');
      if(!columns || !pass || !missions || !bonus || pass.parentNode!==more || bonus.parentNode!==columns || missions.parentNode!==columns) {
        issues.push({kind:'missing-more-columns'});
      } else {
        const passBox=pass.getBoundingClientRect(),columnBox=columns.getBoundingClientRect(),moreBox=more.getBoundingClientRect(),
          bonusBox=bonus.getBoundingClientRect(),missionBox=missions.getBoundingClientRect();
        if(Math.abs(passBox.width-moreBox.width)>limit || passBox.bottom>columnBox.top+limit) issues.push({kind:'misplaced-point-strip'});
        const requestedBonus=Number(bonus.getAttribute('data-bonus-width')) || 308;
        const canPair=columnBox.width/scale>=requestedBonus+parseFloat(getComputedStyle(bonus).marginRight)/scale+170-1;
        if(canPair) {
          if(Math.abs(bonusBox.top-missionBox.top)>limit || bonusBox.right>missionBox.left+limit) issues.push({kind:'stacked-wide-more-columns'});
        } else if(missionBox.top<bonusBox.bottom-limit) issues.push({kind:'unwrapped-more-columns'});
        if(!stress) {
          const title=pass.querySelector('.ss-more-title').getBoundingClientRect(),points=pass.querySelector('.ss-more-pass').getBoundingClientRect();
          if(title.right>points.left+limit || Math.min(title.bottom,points.bottom)-Math.max(title.top,points.top)<=0) issues.push({kind:'noninline-point-strip'});
        }
      }
      const missionRows=missions ? [...missions.querySelectorAll('.ss-more-mission')] : [],
        descriptions=missions ? [...missions.querySelectorAll('.ss-more-mission-description')] : [];
      const expectedMissions=stress ? 4 : 3,expectedDescriptions=stress ? 4 : 0;
      if(missionRows.length!==expectedMissions || descriptions.length!==expectedDescriptions || !missionRows.every(visible) || !descriptions.every(visible)) {
        issues.push({kind:'collapsed-mission-details'});
      }
      for(const mission of missionRows) {
        const row=mission.getBoundingClientRect(),identity=mission.querySelector('.ss-more-mission-name').getBoundingClientRect(),
          status=mission.querySelector('.ss-more-mission-status').getBoundingClientRect(),outline=getComputedStyle(mission),
          descriptionNode=mission.querySelector('.ss-more-mission-description'),
          description=descriptionNode && descriptionNode.getBoundingClientRect();
        if(status.top<identity.bottom-limit || identity.left<row.left-limit || identity.right>row.right+limit ||
          status.left<row.left-limit || status.right>row.right+limit || status.bottom>row.bottom+limit ||
          (description && (description.top<status.bottom-limit || description.left<row.left-limit || description.right>row.right+limit ||
          description.bottom>row.bottom+limit)) ||
          ['Top','Right','Bottom','Left'].some(edge=>parseFloat(outline['border'+edge+'Width'])<=0)) {
          issues.push({kind:'fragmented-mission-result'});
        }
      }
      if(!stress && pass && matrix) {
        const pointCells=pass.querySelectorAll('.ss-more-value'),factorCells=matrix.querySelectorAll('.ss-bonus-factor');
        if(pointCells.length!==3 || matrix.querySelectorAll('.ss-bonus-head .ss-bonus-number').length!==5 ||
          matrix.querySelectorAll('.ss-bonus-row').length!==4 || factorCells.length!==2 ||
          [...factorCells].some(cell=>cell.textContent.replace(',','.')!=='×1.5') || more.querySelector('.ss-more-factors')) {
          issues.push({kind:'expanded-ordinary-bonus-layout'});
        }
        const pointValues=[...pointCells].map(cell=>normalize(cell.querySelector('.ss-more-amount').textContent));
        if(!(pointValues[0] || '').includes('25') || pointValues[1]!=='+5' || pointValues[2]!=='+20' ||
          ![...matrix.querySelectorAll('.ss-bonus-number')].some(cell=>normalize(cell.textContent)==='+110000')) issues.push({kind:'missing-reported-shape-values'});
      }
    }
    const credits=first.querySelector('.ss-money-row');
    const values=[...credits.querySelectorAll('.ss-cell-value')].map(node=>normalize(node.textContent));
    const counts=[...credits.querySelectorAll('.ss-cell-coverage')].map(node=>normalize(node.textContent));
    if(values.join('|')!==[sample.income,-sample.costs,'+'+sample.net].join('|')) issues.push({kind:'incomplete-finance-values',values});
    const headerCount=first.querySelector('.ss-money-count .ss-cell-coverage');
    if(group!=='battles' && (stress ? counts.join('|')!=='1/4|2/4|3/4' :
      counts.length!==0 || !headerCount || normalize(headerCount.textContent)!=='123/137')) {
      issues.push({kind:'missing-finance-coverage',counts,header:headerCount && headerCount.textContent});
    }
    const detail=first.querySelector('.ss-details'),performance=detail.querySelector('.ss-performance').getBoundingClientRect(),
      economy=detail.querySelector('.ss-economy').getBoundingClientRect();
    const cardWidth=first.getBoundingClientRect().width/scale;
    if(group==='battles' && cardWidth>=499 && (performance.width/scale>177 || economy.width/scale<296 ||
      performance.right>economy.left+limit)) {
      issues.push({kind:'unbalanced-card-finance',performance:performance.width/scale,economy:economy.width/scale});
    }
    if(group!=='battles' && !stress && cardWidth>=559 && (performance.width/scale<240 || economy.width/scale<296 ||
      performance.right>economy.left+limit)) issues.push({kind:'unbalanced-group-finance',performance:performance.width/scale,economy:economy.width/scale});
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
    if(two && group==='battles') {
      const anchors=canonical.map(card=>card.getBoundingClientRect().top+parseFloat(getComputedStyle(card,':before').top));
      if(anchors.some((anchor,index)=>index && anchor<anchors[index-1]-limit)) issues.push({kind:'reversed-expanded-chronology',anchors});
    }
    return {issues,language:document.documentElement.lang,cards:cards.length,
      logicalWidth:root.width/scale,columns:two ? 2 : 1,
      expanded:group==='battles' ? first.querySelector('.ss-more-button').getAttribute('aria-expanded')==='true' : null,
      cardWidth,
      narrowCards:document.getElementById('ss-groups').classList.contains('ss-narrow-cards')};
  },{scale:mode.scale,group,sample:samples[mode.stress ? 'stress' : 'ordinary'],stress:mode.stress});
}

module.exports=async function ({browser,nativeHost,check}) {
  const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'grz-locale-qa-'));
  const screenshots=[],audits=[];
  const modes=[
    {name:'narrow',width:720,scale:1,gameWidth:1920,gameHeight:1300,capture:true,columns:1,stress:false},
    {name:'wide',width:1800,scale:1,gameWidth:2200,gameHeight:1300,capture:true,columns:2,stress:false},
    {name:'stress-wide',width:1400,scale:1,gameWidth:2200,gameHeight:1300,capture:false,columns:2,stress:true},
    {name:'scaled-200',width:720,scale:2,gameWidth:3840,gameHeight:2560,capture:false,columns:1,stress:true},
    {name:'floating-470',width:470,scale:1,gameWidth:2400,gameHeight:1300,capture:false,columns:1,stress:true},
    {name:'configured-480',width:1200,cardWidth:480,scale:1,gameWidth:2400,gameHeight:1300,capture:false,columns:2,stress:true},
  ];
  try {
    for(const language of languages) for(const mode of modes) {
      const page=await nativeHost(browser,{
        initialViewport:{width:mode.gameWidth,height:mode.gameHeight},
        viewport:{width:mode.gameWidth,height:mode.gameHeight,scale:mode.scale},
      });
      try {
        await page.evaluate(({language,messages,mode,objective,sample})=>{
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
            battle.name=mode.stress ? 'Pz.Kpfw. Tiger II mit 10,5 cm Kw.K L/68' : ['Leox','IS-4','Conqueror GC','TS-54'][index];
            battle.map=mode.stress ? 'Ruinberg · Pearl River · Westfield' : ['Cliff','Berlin','Highway','Westfield'][index];
            battle.outcome=index%2 ? 'loss' : 'win';
            battle.xp_bonus_applied=false;
            battle.stats.xp_base={count:1,min:sample.xp,avg:sample.xp,max:sample.xp,sum:sample.xp};
            battle.stats.wn8=sample.wn8;battle.stats.wn8_count=1;
            const money=index%2 ? (mode.stress ? {income:12345678,costs:24691356,net:-12345678} :
              {income:74321,costs:87654,net:-13333}) : {income:sample.income,costs:sample.costs,net:sample.net};
            battle.stats.currencies.credits={...money,income_count:1,costs_count:1,net_count:1};
            battle.details={pass_points:mode.stress ? {credited:33,battle:8,missions:10,vehicle:15} : {credited:25,battle:5,missions:20,vehicle:0},
              missions:{
                'daily:fixture':{kind:'daily',name:messages['more.kind.daily']+' · '+messages['more.mission.completed'],status:'completed',description:objective},
                'weekly:fixture':{kind:'weekly',name:messages['more.kind.weekly']+' · '+messages['more.mission.progress'],status:'progress',description:objective,before:12,after:16},
                'personal:fixture':{kind:'personal',name:'Operation Fossa — '+messages['more.mission.honors'],operation:'Operation Fossa',status:'honors',description:objective},
                'challenge:fixture':{kind:'crucible',name:messages['more.kind.crucible']+' · '+messages['more.stage'].replace('{0}','15'),stage:15,status:'failed',description:objective},
              },active_crucible:'challenge:fixture',
              bonuses:mode.stress ? {dailyXPFactor10:20,eventCrystal:43,eventCredits:12345678,boosterCredits:26943,boosterXP:136,
                boosterFreeXP:28,boosterTMenXP:544,wotPlusCredits:8083,wotPlusXP:41,wotPlusFreeXP:2,wotPlusCrewXP:164} :
                {eventCredits:110000,eventCrystal:24,wotPlusCredits:3456,wotPlusXP:64,wotPlusFreeXP:8,wotPlusCrewXP:96,
                  appliedPremiumCreditsFactor100:150,appliedPremiumXPFactor100:150}};
            if(!mode.stress) {
              delete battle.details.missions['weekly:fixture'];
              battle.details.missions['daily:fixture'].name=messages['more.kind.daily']+' 1';
              battle.details.missions['personal:fixture'].name='Operation Fossa';
              Object.values(battle.details.missions).forEach(mission=>{delete mission.description;});
            }
            return battle;
          });
          if(timeline.pagination && timeline.pagination.battles) timeline.pagination.battles={page:0,page_size:40,total:4,pages:1};
          for(const group of ['vehicles','maps','tiers']) {
            const original=timeline[group][0];
            timeline[group]=Array.from({length:4},(_,index)=>{
              const item=JSON.parse(JSON.stringify(original));
              item.id='locale-'+group+'-'+index;
              item.name=group==='vehicles' ? (mode.stress ? 'Pz.Kpfw. Tiger II mit 10,5 cm Kw.K L/68' : ['Leox','IS-4','Conqueror GC','TS-54'][index]) :
                group==='maps' ? (mode.stress ? 'Ruinberg · Pearl River · Westfield' : ['Cliff','Berlin','Highway','Westfield'][index]) : 'VIII';
              item.stats.battles=mode.stress ? 4 : 123;item.stats.observed_battles=mode.stress ? 4 : 137;
              if(!mode.stress) {item.stats.wins=61;item.stats.losses=60;item.stats.draws=2;item.stats.win_rate=6100/123;item.stats.free_xp.count=123;}
              const xpCount=mode.stress ? 3 : 123,wn8Count=mode.stress ? 2 : 123;
              item.stats.xp_base={count:xpCount,min:sample.xp,avg:sample.xp,max:sample.xp,sum:sample.xp*xpCount};
              item.stats.battle_wn8={count:wn8Count,min:sample.wn8,avg:sample.wn8,max:sample.wn8,sum:sample.wn8*wn8Count};
              item.stats.wn8=sample.wn8;item.stats.wn8_count=mode.stress ? 3 : 123;
              item.stats.currencies.credits={income:sample.income,costs:sample.costs,net:sample.net,
                income_count:mode.stress ? 1 : 123,costs_count:mode.stress ? 2 : 123,net_count:mode.stress ? 3 : 123};
              for(const field of ['income','costs','net']) item.stats.currencies.bonds[field+'_count']=mode.stress ? 4 : 123;
              return item;
            });
            if(timeline.pagination && timeline.pagination[group]) timeline.pagination[group]={page:0,page_size:40,total:4,pages:1};
          }
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{language,messages:catalogs[language],mode,objective:objectives[language],sample:samples[mode.stress ? 'stress' : 'ordinary']});
        await page.locator('#ss-scope-manual').click();
        for(const group of groups) {
          await page.locator('#ss-group-'+group).click();
          if(group==='battles') await page.locator('[data-list-index="0"] .ss-more-button').click();
          await page.mouse.move(mode.gameWidth-10,mode.gameHeight-10);
          await frames(page);
          const result=await audit(page,mode,group);
          audits.push({locale:language,group,mode:mode.name,fixture:mode.stress ? 'stress' : 'ordinary',expectedColumns:mode.columns,configuredCardWidth:mode.cardWidth || null,...result});
          if(mode.capture && ['vehicles','battles'].includes(group)) {
            // Show both control bars and the compact summary together with
            // Vehicles or the expanded first battle's details.
            await page.locator('#ss-scroll').evaluate(scroll=>{scroll.scrollTop=0;});
            await frames(page);
            const name='session-stats-'+language+'-'+group+'-'+mode.name+'.jpg';
            const data=await page.locator('#grz-session-stats').screenshot({path:path.join(directory,name),type:'jpeg',quality:74,animations:'disabled'});
            screenshots.push({name,language,group,mode:mode.name,fixture:'ordinary',width:mode.width,scale:mode.scale,mime_type:'image/jpeg',bytes:data.length,sha256:sha(data),data:data.toString('base64')});
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
      result.narrowCards===(result.cardWidth<(result.group==='battles' ? 430 : 500)));
  } finally { fs.rmSync(directory,{recursive:true,force:true}); }
};
