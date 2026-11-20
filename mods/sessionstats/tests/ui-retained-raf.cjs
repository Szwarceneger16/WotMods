/* Exercise retained callbacks from the actual scheduler functions in Chrome. */
const fs=require('fs'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
function actualFunction(name){
  const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }\n',start);
  if(start<0||end<0)throw Error('Missing scheduler function: '+name);
  return source.slice(start,end+7);
}
const functions=['invalidateCardFlow','queueCardFlow','queueResize'].map(actualFunction).join('\n');
module.exports=async({browser,check})=>{
  for(const kind of ['resize','card'])for(const retirement of ['active','stale','destroyed']){
    const page=await browser.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.stack||String(error)));
    try{
      const result=await page.evaluate(({functions,kind,retirement})=>new Promise((resolve,reject)=>{
        const realRAF=window.requestAnimationFrame,realTimeout=window.setTimeout,realClear=window.clearTimeout;
        const pending=[],timers=new Map(),delays=[],effects={measure:0,arrange:0};let nextTimer=0;
        function capture(callback){pending.push(callback);return pending.length;}
        window.requestAnimationFrame=capture;
        window.setTimeout=(callback,delay)=>{delays.push(delay);timers.set(++nextTimer,callback);return nextTimer;};
        window.clearTimeout=id=>timers.delete(id);
        const root=document.createElement('div'),columns=document.createElement('div'),card=document.createElement('div');
        card.style.cssText='width:720px;height:150px';columns.appendChild(card);root.appendChild(columns);document.body.appendChild(root);
        const state={destroyed:false,cardFlowQueued:false,cardFlowAttempts:0,cardLayoutWide:true,
          cardFlowToken:1,cardFlowTimer:null,nativeScale:1,effectiveCardWidth:720,cardPages:[{columns,cards:[card]}],
          resize:null,resizeLast:0,resizeTimer:null,resizeQueued:false,resizeMeasureToken:0,groupMinHeight:false,
          payload:{viewport:{scale:1,width:1800,height:1100},window_size:[1600,900]}};
        const noop=()=>{},scope={window,document,root,state,nodes:{groups:columns},
          hasNumber:value=>typeof value==='number'&&isFinite(value),hasExpandedBattle:()=>true,
          arrangeCardLanes:()=>effects.arrange++,finishFeedAnchor:noop,finishBattleJump:noop,finishPageJump:noop,
          updatePinnedFilters:noop,endResize:noop,endScrollbar:noop,
          windowSizeBounds:()=>({maxWidth:1800,maxHeight:1100,minWidth:320,minHeight:240}),
          resizePanelDimensions:()=>({width:1600,height:900}),layoutResizeGrips:noop,
          layoutSummary:()=>effects.measure++,layoutFilterControls:noop,layoutBattleCards:noop,resizeNative:noop,
          positionDatePicker:noop,restoreViewScroll:noop,syncScrollbar:noop};
        // Only dependencies are supplied by the fixture; both callback bodies
        // and their recursive scheduling execute directly from production.
        const api=new Function('scope','with(scope){'+functions+';return {queueResize,queueCardFlow,invalidateCardFlow};}')(scope);
        const schedule=kind==='resize'?api.queueResize:api.queueCardFlow;
        schedule();const retained=pending.shift();
        if(!retained){reject(Error('Missing retained '+kind+' callback'));return;}
        if(retirement==='stale'){
          if(kind==='card')api.invalidateCardFlow();
          else{state.resizeMeasureToken++;state.resizeQueued=false;}
        }else if(retirement==='destroyed'){state.destroyed=true;}
        window.requestAnimationFrame=undefined;
        // Invoke as a native browser callback so an uncaught scheduler error
        // reaches pageerror independently of this awaited fixture promise.
        realRAF.call(window,()=>retained(performance.now()));
        realRAF.call(window,()=>realRAF.call(window,()=>{
          try{
            let drained=0;
            while(timers.size&&drained<10){const [id,callback]=timers.entries().next().value;timers.delete(id);callback();drained++;}
            const beforeRecovery={...effects,attempts:state.cardFlowAttempts,queued:kind==='card'?state.cardFlowQueued:state.resizeQueued,
              timer:state.cardFlowTimer,timers:timers.size,pending:pending.length,delays:delays.slice()};
            window.requestAnimationFrame=capture;
            let recovered=false;
            if(retirement!=='destroyed'){
              if(kind==='card')api.invalidateCardFlow();
              schedule();let frames=0;
              while(pending.length&&frames++<20)pending.shift()(performance.now());
              recovered=kind==='card'?effects.arrange-beforeRecovery.arrange===3&&state.cardFlowAttempts===3&&!state.cardFlowQueued:
                effects.measure-beforeRecovery.measure===1&&!state.resizeQueued;
            }else{schedule();recovered=pending.length===0&&timers.size===0;}
            window.requestAnimationFrame=realRAF;window.setTimeout=realTimeout;window.clearTimeout=realClear;
            resolve({beforeRecovery,recovered});
          }catch(error){window.requestAnimationFrame=realRAF;window.setTimeout=realTimeout;window.clearTimeout=realClear;reject(error);}
        }));
      }),{functions,kind,retirement});
      const label=kind+' / '+retirement,observed=result.beforeRecovery;
      check('Retained '+label+' callback tolerates RAF removal without a browser error: '+JSON.stringify(errors),errors.length===0);
      if(retirement==='active'){
        check('Retained '+label+' callback completes the existing fallback and releases queued work: '+JSON.stringify(observed),
          kind==='resize'?observed.measure===1&&!observed.queued:
            observed.arrange===3&&observed.attempts===3&&!observed.queued&&observed.timer===null&&
            observed.timers===0&&observed.delays.length===3&&observed.delays.every(delay=>delay===16));
      }else{
        check('Retired '+label+' callback performs no layout and schedules no fallback: '+JSON.stringify(observed),
          observed.measure===0&&observed.arrange===0&&observed.timers===0&&observed.pending===0&&observed.delays.length===0);
      }
      check('Retained '+label+' scheduler preserves lifecycle ownership after RAF restoration',
        result.recovered);
    }finally{await page.close();}
  }
};
