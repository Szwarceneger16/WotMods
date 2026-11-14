/* Exercise the MOD window width independently of the full game's viewport.
   Viewport-only media queries cannot fix a small floating native window. */
const fs=require('fs'),path=require('path');
module.exports=async function ({browser,nativeHost,check}) {
  const cases=[
    {width:1200,scale:1,gameWidth:2000,mode:'wide'},
    {width:1600,scale:1,gameWidth:2400,mode:'wide'},
    {width:800,scale:1,gameWidth:2400,mode:'medium'},
    {width:480,scale:1,gameWidth:2400,mode:'narrow'},
    {width:470,scale:1,gameWidth:2400,mode:'narrow'},
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
          stats.battles=stats.observed_battles=4;
          stats.wins=2;stats.losses=stats.draws=1;
          for(const metric of ['xp_base','xp_received']) {
            for(const key of ['min','avg','max','sum']) stats[metric][key]=123456;
            stats[metric].count=3;
          }
          stats.wn8=10420;
          for(const key of ['min','avg','max','sum']) stats.battle_wn8[key]=10420;
          stats.battle_wn8.count=2;
          stats.currencies.credits.income=12345678;
          stats.currencies.credits.costs=12345678;
          stats.currencies.credits.net=-12345678;
          stats.currencies.credits.income_count=1;
          stats.currencies.credits.costs_count=2;
          stats.currencies.credits.net_count=3;
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
        const pair=bounds(document.querySelector('#ss-summary .ss-summary-details'));
        const summary=bounds(document.querySelector('#ss-summary .ss-summary-layout'));
        const kpis=[...document.querySelectorAll('#ss-summary .ss-kpi')].map(bounds);
        const filters=[...document.querySelectorAll('.ss-timeline-field')].map(bounds);
        const xpPickerCount=document.querySelectorAll('.ss-xp-picker,#ss-xp-base,#ss-xp-received').length;
        const scopes=bounds(document.querySelector('.ss-scopes'));
        const lower=['.ss-list-meta','#ss-pagination','#ss-sorting'].map(selector=>bounds(document.querySelector(selector)));
        const lowerTriggers=['#ss-page-previous','#ss-sort-statistic .ss-select-trigger','#ss-sort-metric .ss-select-trigger','#ss-sort-direction .ss-select-trigger'].map(selector=>bounds(document.querySelector(selector)));
        const overflow=[...document.querySelectorAll('.ss-titlebar *,.ss-controls *,#ss-summary *,.ss-list-controls *')].filter(node=>{
          const box=bounds(node);
          return box.width>0 && box.height>0 && (box.left<root.left-1 || box.right>root.right+1);
        }).map(node=>node.className);
        const badNumbers=[];
        for(const node of document.querySelectorAll('#ss-summary .ss-kpi-value,#ss-summary .ss-metric-row .ss-metric-number,#ss-summary .ss-money-value .ss-cell-value,#ss-summary .ss-money-value .ss-cell-coverage')) {
          const box=node.getBoundingClientRect();
          if(!box.width || !box.height) continue;
          const cell=node.closest('.ss-money-value,.ss-metric-number,.ss-kpi-value');
          const cellBox=cell.getBoundingClientRect(),style=getComputedStyle(cell);
          const range=document.createRange();range.selectNodeContents(node);
          const text=range.getBoundingClientRect();
          const insetLeft=parseFloat(style.paddingLeft)+parseFloat(style.borderLeftWidth);
          const insetRight=parseFloat(style.paddingRight)+parseFloat(style.borderRightWidth);
          const minFont=node.classList.contains('ss-cell-coverage') ? 11 : node.classList.contains('ss-kpi-value') ? 24 : cell.classList.contains('ss-metric-number') ? 14 : 13;
          if(text.left<cellBox.left+insetLeft-1 || text.right>cellBox.right-insetRight+1 ||
            parseFloat(getComputedStyle(node).fontSize)/scale<minFont) badNumbers.push(node.textContent);
        }
        const compact=text=>text.replace(/\s/g,'');
        const credits=document.querySelector('#ss-summary .ss-money-value[data-ss-metric="credits_income_received"]').closest('.ss-money-row');
        return {root,panels,pair,summary,kpis,filters,xpPickerCount,scopes,lower,lowerTriggers,overflow,badNumbers,
          periodHidden:document.getElementById('ss-started').getBoundingClientRect().height===0,
          values:[...credits.querySelectorAll('.ss-money-value .ss-cell-value')].map(node=>compact(node.textContent)),
          coverage:[...credits.querySelectorAll('.ss-cell-coverage')].map(node=>compact(node.textContent)),
          xpValues:[...document.querySelectorAll('#ss-summary [data-ss-metric="xp_base"] .ss-metric-number,#ss-summary [data-ss-metric="xp_received"] .ss-metric-number')].map(node=>compact(node.textContent)),
          wn8:document.querySelector('#ss-summary .ss-kpi-value.ss-wn8').textContent,
        };
      },scale);
      const expectedWidth=Math.max(550,width);
      const caption=expectedWidth+' logical pixels at '+(scale*100)+'% in a '+gameWidth+'px game';
      check('Upper controls and summary stay within the floating window: '+caption,
        Math.abs(audit.root.width-expectedWidth)<=1 && audit.overflow.length===0);
      check('Summary sections keep capped widths and readable full values: '+caption,
        audit.panels[0].width<=461 && audit.pair.width<=651 && audit.panels[1].width<=301 && audit.panels[2].width<=351 &&
        audit.badNumbers.length===0 && audit.values.join('|')==='12345678|-12345678|-12345678' &&
        audit.coverage.join('|')==='1/4|2/4|3/4' &&
        audit.xpValues.length===6 && audit.xpValues.every(value=>value==='123456') &&
        audit.wn8==='10420');
      if(width>=470) check('Main battle, win-rate and WN8 KPIs remain horizontal: '+caption,
        audit.kpis.length===3 && Math.max(...audit.kpis.map(box=>box.top))-Math.min(...audit.kpis.map(box=>box.top))<=1 &&
        audit.kpis[0].right<=audit.kpis[1].left+1 && audit.kpis[1].right<=audit.kpis[2].left+1);
      check('Combat and finances remain inside the same wrapping summary pair: '+caption,
        audit.panels.slice(1).every(box=>box.left>=audit.pair.left-1 && box.right<=audit.pair.right+1 &&
          box.top>=audit.pair.top-1 && box.bottom<=audit.pair.bottom+1));
      check('Timeline selectors remain bounded and hide the redundant period line: '+caption,
        audit.periodHidden && audit.filters.every(field=>field.width>0 && field.width<=223));
      if(mode==='wide') {
        check('Wide upper scopes and date filters share a bounded row without an XP toggle: '+caption,
          audit.xpPickerCount===0 && audit.scopes.width<=261 && audit.scopes.right<=audit.filters[0].left &&
          Math.abs(audit.scopes.top-audit.filters[0].top)<=3 &&
          Math.abs(audit.filters[0].top-audit.filters[1].top)<=2);
        check('Wide result count, pagination and sorting share a bounded row: '+caption,
          audit.lower[1].width<=341 && audit.lower[2].width<=425 &&
          audit.lower[0].right<=audit.lower[1].left+1 && audit.lower[1].right<=audit.lower[2].left+1 &&
          Math.min(...audit.lower.map(box=>box.bottom))-Math.max(...audit.lower.map(box=>box.top))>5 &&
          Math.max(...audit.lowerTriggers.map(box=>box.bottom))-Math.min(...audit.lowerTriggers.map(box=>box.bottom))<=2);
        check('Pagination follows the result metadata without a reserved blank column: '+caption,
          Math.abs(audit.lower[1].left-audit.lower[0].right-8)<=1);
        check('Wide summary uses one compact row for main stats, combat and finances: '+caption,
          Math.max(...audit.panels.map(panel=>panel.top))-Math.min(...audit.panels.map(panel=>panel.top))<=1 &&
          audit.panels[0].right<=audit.panels[1].left+1 && audit.panels[1].right<=audit.panels[2].left+1);
        check('The compact wide summary row is centered in the floating window: '+caption,
          Math.abs(audit.panels[0].left+audit.pair.right-audit.summary.left-audit.summary.right)<=2);
      } else if(mode==='medium') {
        check('Medium summary wraps combat and finances together below the main KPIs: '+caption,
          audit.pair.top>=audit.panels[0].bottom-1 && Math.abs(audit.panels[1].top-audit.panels[2].top)<=1 &&
          audit.panels[1].right<=audit.panels[2].left+1);
      } else {
        check('A narrow mod window stacks sections despite the wide game viewport: '+caption,
          audit.panels[1].top>=audit.panels[0].bottom-1 &&
          audit.panels[2].top>=audit.panels[1].bottom-1 && audit.xpPickerCount===0);
      }
      if(mode!=='wide') check('Wrapped summary rows stay centered: '+caption,
        Math.abs(audit.panels[0].left+audit.panels[0].right-audit.summary.left-audit.summary.right)<=2 &&
        Math.abs(audit.pair.left+audit.pair.right-audit.summary.left-audit.summary.right)<=2);
      await page.evaluate(()=>{
        const payload=JSON.parse(model.payload);
        payload.scopes.timeline.summary.currencies.credits.net=12345678;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      });
      check('Positive finance totals retain their full signed amount: '+caption,
        await page.locator('#ss-summary .ss-money-value[data-ss-metric="credits_net_received"] > .ss-cell-value').textContent().then(text=>text.replace(/\s/g,'')==='+12345678'));
    } finally { await page.close(); }
  }
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const transitionCases=[{width:470,scale:1},{width:700,scale:1},{width:1000,scale:1},
    {width:1200,scale:1},{width:700,scale:2}];
  for(const {width,scale} of transitionCases) {
    const page=await nativeHost(browser,{initialViewport:{width:3000,height:2200},
      viewport:{width:3000,height:2200,scale}});
    try {
      for(const [language,messages] of Object.entries(languages)) {
        await page.evaluate(({width,language,messages})=>{
          const payload=JSON.parse(model.payload);
          payload.window_size=[width,1000];payload.localization={language,messages};
          const timeline=payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));
          timeline.from_point=timeline.to_point='';timeline.time_points=[];
          payload.scopes.launch=JSON.parse(JSON.stringify(timeline));
          const empty=payload.scopes.launch;
          empty.battles=[];empty.vehicles=[];empty.maps=[];empty.tiers=[];empty.pending=0;
          const stats=empty.summary;
          stats.battles=stats.observed_battles=stats.wins=stats.losses=stats.draws=stats.wn8_count=0;
          stats.win_rate=stats.wn8=null;
          for(const metric of ['xp_base','xp_received','battle_wn8','free_xp']) {
            stats[metric]={min:null,avg:null,max:null,sum:null,count:0};
          }
          for(const currency of Object.values(stats.currencies)) for(const field of ['income','costs','net']) {
            currency[field]=null;currency[field+'_count']=0;
          }
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{width,language,messages});
        await page.locator('#ss-scope-launch').click();
        const geometry=async()=>{
          await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
          return page.evaluate(scale=>{
            const rect=node=>{const box=node.getBoundingClientRect();return {left:box.left/scale,right:box.right/scale,
              top:box.top/scale,bottom:box.bottom/scale,width:box.width/scale};};
            const summary=document.getElementById('ss-summary');
            return {mode:summary.className,layout:rect(summary.querySelector('.ss-summary-layout')),
              panels:['.ss-summary-main','.ss-summary-details','.ss-performance','.ss-economy'].map(s=>rect(summary.querySelector(s))),
              kpis:[...summary.querySelectorAll('.ss-kpi')].map(rect)};
          },scale);
        };
        const empty=await geometry();
        await page.locator('#ss-scope-manual').click();
        const full=await geometry();
        const caption=language+' at '+width+' logical pixels / '+scale*100+'%';
        check('Empty launch and populated timeline keep deterministic summary widths: '+caption,
          empty.mode===full.mode && empty.panels.every((box,index)=>
            Math.abs(box.left-full.panels[index].left)<=1 && Math.abs(box.width-full.panels[index].width)<=1));
        const center=box=>(box.left+box.right)/2;
        check('Summary rows and horizontal KPIs stay centered across periods: '+caption,
          [empty,full].every(data=>{
            const [main,pair,performance,economy]=data.panels;
            const rows=width<1144 ? [main,pair] : [{left:main.left,right:pair.right}];
            return rows.every(row=>Math.abs(center(row)-center(data.layout))<=1) &&
              (width>=684 || [performance,economy].every(row=>Math.abs(center(row)-center(pair))<=1)) &&
              data.kpis.length===3 && data.kpis.every(box=>Math.abs(box.top-data.kpis[0].top)<=1);
          }));
        check('All localized sort options fit the compact bounded selectors: '+caption,
          await page.locator('#ss-sorting').evaluate(bar=>{
            const box=bar.getBoundingClientRect(),fields=[...bar.querySelectorAll('.ss-sort-field')];
            const scale=parseFloat(getComputedStyle(document.documentElement).fontSize);
            const limits={'ss-sort-statistic':66,'ss-sort-metric':121,'ss-sort-direction':110};
            const wide=bar.parentNode.classList.contains('ss-filters-wide');
            if(box.width<=0 || box.width/scale>(wide?425:295) || fields.length!==3 ||
              fields.some(field=>{const id=field.querySelector('.ss-select').id;
                return !limits[id] || field.getBoundingClientRect().width/scale>limits[id];})) return false;
            return fields.every(field=>{
              const label=field.querySelector('.ss-select-trigger .ss-control-label'),original=label.textContent;
              const available=label.getBoundingClientRect().width,range=document.createRange();
              const fits=[...field.querySelectorAll('[role=option]')].every(option=>{
                label.textContent=option.textContent;range.selectNodeContents(label);
                return range.getBoundingClientRect().width<=available+1;
              });
              label.textContent=original;
              const caption=field.querySelector('.ss-sort-caption');range.selectNodeContents(caption);
              return fits && range.getBoundingClientRect().width<=caption.getBoundingClientRect().width+1;
            });
          }));
        await page.locator('#ss-scope-launch').click();
        const restored=await geometry();
        check('Returning to the empty period restores the centered summary without a layout drift: '+caption,
          restored.mode===empty.mode && restored.panels.every((box,index)=>
            Math.abs(box.left-empty.panels[index].left)<=1 && Math.abs(box.width-empty.panels[index].width)<=1));
      }
    } finally { await page.close(); }
  }
};
