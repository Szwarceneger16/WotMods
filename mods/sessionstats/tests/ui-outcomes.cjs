/* Original client artwork URLs and separate localized captions; no edited art. */
module.exports = async ({browser,nativeHost,check}) => {
  const page = await nativeHost(browser,{});
  await page.evaluate(()=>{
    const snapshot=JSON.parse(model.payload), scope=snapshot.scopes.launch;
    const sample=scope.battles[0];
    scope.battles=['win','loss','draw'].map((outcome,index)=>({
      ...sample,id:'outcome-'+outcome,started_at:1800000000-index,outcome,
      outcome_visual:{kind:'outcome',src:'img://gui/maps/icons/library/BgBattleResultIcon'+
        ['Victory','Defeat','Draw'][index]+'-1.png'}
    }));
    snapshot.localization={language:'pl',messages:{
      'outcome.win':'Zwycięstwo','outcome.loss':'Porażka','outcome.draw':'Remis'}};
    model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);
    document.getElementById('ss-group-battles').click();
  });
  check('All three battle results use their unchanged native artwork URL',await page.evaluate(()=>
    ['Victory','Defeat','Draw'].every((name,index)=>{
      const node=document.querySelectorAll('.ss-outcome-image')[index], style=node&&getComputedStyle(node);
      return style && style.backgroundImage.includes('/BgBattleResultIcon'+name+'-1.png') &&
        style.backgroundSize==='contain' && style.filter==='none' && node.textContent==='';
    })));
  check('WG-localized captions remain separate from the untouched image',await page.evaluate(()=>
    Array.from(document.querySelectorAll('.ss-outcome-label')).map(n=>n.textContent).join('|')===
      'Zwycięstwo|Porażka|Remis' && Array.from(document.querySelectorAll('.ss-outcome-art')).every(node=>{
        const image=node.querySelector('.ss-outcome-image'),label=node.querySelector('.ss-outcome-label');
        return image.getAttribute('aria-hidden')==='true' &&
          label.getBoundingClientRect().top>=image.getBoundingClientRect().bottom-1;
      })));
  for(const width of [320,744]) {
    await page.setViewportSize({width,height:820});
    check('Outcome art and identity fit the panel at width '+width,await page.evaluate(()=>{
      const panel=document.getElementById('grz-session-stats').getBoundingClientRect();
      return Array.from(document.querySelectorAll('.ss-outcome-art,.ss-group-name')).every(node=>{
        const box=node.getBoundingClientRect();return box.width>0 && box.left>=panel.left && box.right<=panel.right;
      });
    }));
  }
  await page.evaluate(()=>{
    const snapshot=JSON.parse(model.payload), rows=snapshot.scopes.launch.battles;
    rows[0].outcome_visual.src='https://example.invalid/banner.png';
    rows[1].outcome_visual.src='img://gui/maps/icons/library/BgBattleResultIconVictory-1.png';
    delete rows[2].outcome_visual;
    GRZSessionStats.update(snapshot);
  });
  check('Missing, remote and mismatched artwork retain readable localized outcomes',
    await page.locator('.ss-outcome-image').count()===0 &&
    (await page.locator('.ss-outcome-label').allTextContents()).join('|')==='Zwycięstwo|Porażka|Remis');
  await page.close();
};
