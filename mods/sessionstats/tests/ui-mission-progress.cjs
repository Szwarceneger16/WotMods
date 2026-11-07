/* A known current counter is distinct from a known delta or missing progress. */
const fs=require('fs'),path=require('path');
module.exports=async ({browser,nativeHost,check})=>{
  const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:1600,height:1200},viewport:{width:1600,height:1200,scale:1},realTimers:true});
  const frames=()=>page.evaluate(()=>new Promise(resolve=>{
    let remaining=10;function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
  }));
  try {
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload);payload.account_key='synthetic-progress-account';payload.window_size=[700,1000];
      const scope=payload.scopes.launch,card=scope.battles[0];card.id='synthetic-progress-battle';
      card.details={pass_points:{credited:0},bonuses:{wotPlusCredits:3456,wotPlusXP:64,wotPlusFreeXP:8,wotPlusCrewXP:96},missions:{
        changed:{kind:'daily',name:'Synthetic changed objective',status:'progress',progress_state:'changed',objectives:[
          {key:'battles',unit:'battles',before:2,after:4,delta:2,target:10},
          {key:'vehicles',unit:'vehicles',before:1,after:2,delta:1,target:5},
          {key:'damage',unit:'damage',label:'<b>Native goal</b>',before:1000,after:3250,delta:2250,target:5000},
          {key:'kills',unit:'kills',before:0,after:3,delta:3,target:8},
          {key:'xp',unit:'xp',before:250,after:1250,delta:1000,target:3000},
          {key:'seconds',unit:'seconds',before:30,after:90,delta:60,target:180},
          {key:'counter',unit:'counter',before:4,after:7,delta:3,target:10}]},
        unchanged:{kind:'daily',name:'Synthetic unchanged objective',status:'progress',progress_state:'unchanged',
          objectives:[{key:'counter',unit:'counter',before:5,after:5,delta:0,target:10}]},
        unavailable:{kind:'weekly',name:'Synthetic unavailable objective',status:'observed',progress_state:'unavailable',objectives:[]},
        current:{kind:'personal',name:'Synthetic current-only objective',status:'progress',progress_state:'unavailable',
          objectives:[{key:'counter',unit:'counter',after:0,target:10}]},
        cached:{kind:'weekly',name:'Synthetic cached objective',status:'observed'},
        negative:{kind:'daily',name:'Synthetic reset counter objective',status:'progress',progress_state:'changed',
          objectives:[{key:'counter',unit:'counter',before:9,after:7,delta:-2}]},
        completed:{kind:'personal',name:'Synthetic completed objective',status:'completed',progress_state:'unavailable',
          objectives:[{key:'counter',unit:'counter',after:3,target:10}]}}};
      scope.battles=[card];if(scope.pagination) scope.pagination.battles={page:0,page_size:40,total:1,pages:1};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });
    await page.locator('#ss-group-battles').click();
    for(const [language,messages] of Object.entries(catalogs)) {
      await page.evaluate(({language,messages})=>{const payload=JSON.parse(model.payload);payload.localization={language,messages};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},{language,messages});
      const more=page.locator('.ss-more-button').first();if(await more.getAttribute('aria-expanded')!=='true') await more.click();
      await frames();
      const value=await page.locator('.ss-more-panel').evaluate(panel=>{
        const rows={};
        for(const row of panel.querySelectorAll('.ss-more-mission')) {
          const name=row.querySelector('.ss-more-mission-name strong').textContent,status=row.querySelector('.ss-more-mission-status');
          rows[name]={text:status.textContent,lines:[...status.querySelectorAll('.ss-more-objective')].map(line=>({unit:line.dataset.unit,text:line.textContent}))};
        }
        const clipped=[];
        for(const node of panel.querySelectorAll('.ss-more-objective')) {
          const range=document.createRange();range.selectNodeContents(node);const box=node.getBoundingClientRect();
          for(const ink of range.getClientRects()) if(ink.left<box.left-1 || ink.right>box.right+1) clipped.push(node.textContent);
        }
        return {rows,clipped,markup:panel.querySelectorAll('b,img').length};
      });
      const compact=text=>text.replace(/\s/g,''),changed=value.rows['Synthetic changed objective'];
      const expected={battles:['4/10','+2'],vehicles:['2/5','+1'],damage:['3250/5000','+2250'],kills:['3/8','+3'],
        xp:['1250/3000','+1000'],seconds:['90/180','+60'],counter:['7/10','+3']};
      check('Mission progress retains all seven units, current values and single signed deltas in '+language,
        changed.lines.length===7 && Object.entries(expected).every(([unit,parts])=>{
          const line=changed.lines.find(line=>line.unit===unit),label=unit==='damage' ? '<b>Native goal</b>' : messages['more.progress.unit.'+unit];
          return line && line.text.includes(label) && parts.every(part=>compact(line.text).includes(part)) && !line.text.includes('++');
        }) && value.markup===0 && value.clipped.length===0);
      const unchanged=value.rows['Synthetic unchanged objective'],unavailable=value.rows['Synthetic unavailable objective'],
        current=value.rows['Synthetic current-only objective'],cached=value.rows['Synthetic cached objective'],
        negative=value.rows['Synthetic reset counter objective'],completed=value.rows['Synthetic completed objective'];
      check('Known unchanged progress differs from missing progress in '+language,
        unchanged.text.includes(messages['more.progress.none']) && compact(unchanged.text).includes('5/10') &&
        !unchanged.text.includes('+0') && unavailable.text===messages['more.progress.unavailable'] && unavailable.lines.length===0 &&
        cached.text===messages['more.progress.unavailable'] && cached.lines.length===0);
      check('A current-only zero is shown without fabricating a delta or no-progress claim in '+language,
        current.lines.length===1 && compact(current.text).includes('0/10') && !current.text.includes('+0') &&
        !current.text.includes('→') && !current.text.includes(messages['more.progress.none']));
      check('Counter reductions keep their sign and terminal mission outcomes remain visible in '+language,
        negative.text.includes('−2') && !negative.text.includes('+−') &&
        completed.text.includes(messages['more.mission.completed']) && compact(completed.text).includes('3/10') && !completed.text.includes('+3'));
    }
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload),objectives=payload.scopes.launch.battles[0].details.missions.changed.objectives;
      for(let index=0;index<5;index++) objectives.push({key:'extra-'+index,unit:'counter',label:'Additional synthetic goal '+index,
        before:9+index,after:10+index,delta:1,target:30});
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });await frames();
    check('All twelve supported mission objectives remain visible',await page.locator('.ss-more-panel').evaluate(panel=>{
      const row=[...panel.querySelectorAll('.ss-more-mission')].find(row=>row.querySelector('.ss-more-mission-name strong').textContent==='Synthetic changed objective'),
        lines=[...row.querySelectorAll('.ss-more-objective')];
      return lines.length===12 && lines[11].textContent.replace(/\s/g,'').includes('14/30') &&
        lines.every(line=>line.getBoundingClientRect().height>0);
    }));
  } finally {await page.close();}
};
