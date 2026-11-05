/* Exercise the MOD window width independently of the full game's viewport.
   Viewport-only media queries cannot fix a small floating native window. */
module.exports=async function ({browser,nativeHost,check}) {
  const cases=[
    {width:1200,scale:1,gameWidth:2000,mode:'wide'},
    {width:1600,scale:1,gameWidth:2400,mode:'wide'},
    {width:800,scale:1,gameWidth:2400,mode:'medium'},
    {width:480,scale:1,gameWidth:2400,mode:'narrow'},
    {width:430,scale:1,gameWidth:2400,mode:'narrow'},
    {width:320,scale:1,gameWidth:2400,mode:'narrow'},
    {width:1200,scale:2,gameWidth:3840,mode:'wide'},
    {width:480,scale:2,gameWidth:3840,mode:'narrow'},
  ];
  for(const testCase of cases) {
    const {width,scale,gameWidth,mode}=testCase;
    const gameHeight=scale===2 ? 2160 : 1300;
    const page=await nativeHost(browser,{
      initialViewport:{width:gameWidth,height:gameHeight},
      viewport:{width:gameWidth,height:gameHeight,scale},
    });
    try {
      await page.evaluate(({width})=>{
        const payload=JSON.parse(model.payload);
        payload.window_size=[width,900];
        payload.localization={language:'en',selected:'auto',messages:{}};
        payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));
        payload.scopes.timeline.from_point=payload.scopes.timeline.to_point='';
        payload.scopes.timeline.time_points=[];
        for(const scope of Object.values(payload.scopes)) {
          const stats=scope.summary;
          for(const metric of ['xp_base','xp_received']) {
            for(const key of ['min','avg','max','sum']) stats[metric][key]=123456;
          }
          stats.wn8=10420;
          for(const key of ['min','avg','max','sum']) stats.battle_wn8[key]=10420;
          stats.currencies.credits.income=12345678;
          stats.currencies.credits.costs=12345678;
          stats.currencies.credits.net=-12345678;
        }
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },testCase);
      await page.locator('#ss-scope-manual').click();
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      const audit=await page.evaluate(scale=>{
        const bounds=node=>{
          const box=node.getBoundingClientRect();
          return {left:box.left/scale,right:box.right/scale,top:box.top/scale,
            bottom:box.bottom/scale,width:box.width/scale,height:box.height/scale};
        };
        const root=bounds(document.getElementById('grz-session-stats'));
        const panels=['.ss-summary-main','#ss-summary .ss-performance','#ss-summary .ss-economy'].map(selector=>bounds(document.querySelector(selector)));
        const filters=[...document.querySelectorAll('.ss-timeline-field')].map(bounds);
        const xp=bounds(document.querySelector('.ss-xp-picker'));
        const scopes=bounds(document.querySelector('.ss-scopes'));
        const lower=['.ss-list-meta','#ss-pagination','#ss-sorting'].map(selector=>bounds(document.querySelector(selector)));
        const lowerTriggers=['#ss-page-previous','#ss-sort-statistic .ss-select-trigger','#ss-sort-metric .ss-select-trigger','#ss-sort-direction .ss-select-trigger'].map(selector=>bounds(document.querySelector(selector)));
        const overflow=[...document.querySelectorAll('.ss-titlebar *,.ss-controls *,#ss-summary *,.ss-list-controls *')].filter(node=>{
          const box=bounds(node);
          return box.width>0 && box.height>0 && (box.left<root.left-1 || box.right>root.right+1);
        }).map(node=>node.className);
        const badNumbers=[];
        for(const node of document.querySelectorAll('#ss-summary .ss-kpi-value,#ss-summary .ss-metric-row .ss-metric-number,#ss-summary .ss-money-value .ss-cell-value')) {
          const box=node.getBoundingClientRect();
          if(!box.width || !box.height) continue;
          const cell=node.closest('.ss-money-value,.ss-metric-number,.ss-kpi-value');
          const cellBox=cell.getBoundingClientRect(),style=getComputedStyle(cell);
          const range=document.createRange();range.selectNodeContents(node);
          const text=range.getBoundingClientRect();
          const insetLeft=parseFloat(style.paddingLeft)+parseFloat(style.borderLeftWidth);
          const insetRight=parseFloat(style.paddingRight)+parseFloat(style.borderRightWidth);
          const minFont=node.classList.contains('ss-kpi-value') ? 24 : cell.classList.contains('ss-metric-number') ? 14 : 13;
          if(text.left<cellBox.left+insetLeft-1 || text.right>cellBox.right-insetRight+1 ||
            parseFloat(getComputedStyle(node).fontSize)/scale<minFont) badNumbers.push(node.textContent);
        }
        const compact=text=>text.replace(/\s/g,'');
        const credits=document.querySelector('#ss-summary .ss-money-row');
        return {root,panels,filters,xp,scopes,lower,lowerTriggers,overflow,badNumbers,
          periodHidden:document.getElementById('ss-started').getBoundingClientRect().height===0,
          values:[...credits.querySelectorAll('.ss-money-value .ss-cell-value')].map(node=>compact(node.textContent)),
          xpValues:[...document.querySelectorAll('#ss-summary .ss-metric-row .ss-metric-number')].slice(0,3).map(node=>compact(node.textContent)),
          wn8:document.querySelector('#ss-summary .ss-kpi-value.ss-wn8').textContent,
        };
      },scale);
      const caption=width+' logical pixels at '+(scale*100)+'% in a '+gameWidth+'px game';
      check('Upper controls and summary stay within the floating window: '+caption,
        Math.abs(audit.root.width-width)<=1 && audit.overflow.length===0);
      check('Summary sections keep capped widths and readable full values: '+caption,
        audit.panels[0].width<=341 && audit.panels[1].width<=311 && audit.panels[2].width<=421 &&
        audit.badNumbers.length===0 && audit.values.join('|')==='12345678|-12345678|-12345678' &&
        audit.xpValues.length===3 && audit.xpValues.every(value=>value==='123456') &&
        audit.wn8==='10420');
      check('Timeline selectors remain bounded and hide the redundant period line: '+caption,
        audit.periodHidden && audit.filters.every(field=>field.width>0 && field.width<=223));
      if(mode==='wide') {
        check('Wide upper scopes, date filters and XP toggle share a bounded row: '+caption,
          audit.scopes.width<=261 && audit.scopes.right<=audit.filters[0].left &&
          Math.abs(audit.scopes.top-audit.xp.top)<=3 &&
          Math.abs(audit.filters[0].top-audit.filters[1].top)<=2 &&
          Math.abs(audit.filters[0].top-audit.xp.top)<=2 &&
          audit.filters[1].right<=audit.xp.left);
        check('Wide result count, pagination and sorting share a bounded row: '+caption,
          audit.lower[0].width<=169 && audit.lower[1].width<=341 && audit.lower[2].width<=363 &&
          audit.lower[0].right<=audit.lower[1].left+1 && audit.lower[1].right<=audit.lower[2].left+1 &&
          Math.min(...audit.lower.map(box=>box.bottom))-Math.max(...audit.lower.map(box=>box.top))>5 &&
          Math.max(...audit.lowerTriggers.map(box=>box.bottom))-Math.min(...audit.lowerTriggers.map(box=>box.bottom))<=2);
        check('Wide summary uses one compact row for main stats, combat and finances: '+caption,
          Math.max(...audit.panels.map(panel=>panel.top))-Math.min(...audit.panels.map(panel=>panel.top))<=1 &&
          audit.panels[0].right<=audit.panels[1].left+1 && audit.panels[1].right<=audit.panels[2].left+1);
      } else if(mode==='medium') {
        check('Medium summary keeps main and combat together and wraps finances: '+caption,
          Math.abs(audit.panels[0].top-audit.panels[1].top)<=1 &&
          audit.panels[2].top>=Math.max(audit.panels[0].bottom,audit.panels[1].bottom)-1);
      } else {
        check('A narrow mod window stacks sections despite the wide game viewport: '+caption,
          audit.panels[1].top>=audit.panels[0].bottom-1 &&
          audit.panels[2].top>=audit.panels[1].bottom-1 &&
          audit.xp.top>=Math.max(...audit.filters.map(field=>field.bottom))-1);
      }
      await page.evaluate(()=>{
        const payload=JSON.parse(model.payload);
        payload.scopes.timeline.summary.currencies.credits.net=12345678;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      });
      check('Positive finance totals retain their full signed amount: '+caption,
        await page.locator('#ss-summary .ss-money-row').first().locator('.ss-money-value .ss-cell-value').last().textContent().then(text=>text.replace(/\s/g,'')==='+12345678'));
    } finally { await page.close(); }
  }
};
