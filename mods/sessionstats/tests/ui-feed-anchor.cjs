/* Exercise the shipped native scroll compensation without browser geometry. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
function actualFunction(name) {
  const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }\n',start);
  assert(start>=0 && end>start,'Missing shipped function '+name);
  return source.slice(start,end+7);
}
const actual=['cancelPageJump','retireFeed','captureFeedAnchor','finishFeedAnchor','revealFeedTop','onScrollIntent'].map(actualFunction).join('\n');
function nativeGeometry() {
  let clock=1000,offset=300,position=500,missing=false,precedingMissing=false,owned=true,queued=0;
  const card={getBoundingClientRect:()=>({top:0,width:precedingMissing?0:600,height:precedingMissing?0:1000})};
  const section={getBoundingClientRect:()=>missing?{top:0,width:0,height:0}:{top:100+position-offset,width:600,height:2000}};
  const inserted={section:{},cards:[card]},original={section,cards:[]};
  const feed={start:4,last:4,current:4,version:0,topRequested:false,prependAnchor:null,pending:null,navigationPage:null};
  const scroll={get scrollTop(){return offset;},set scrollTop(value){offset=value;},getBoundingClientRect:()=>({top:100,width:700,height:500})};
  const state={feed,renderedFeed:feed,cardPages:[original],scrollTarget:null,pageJump:null,battleJump:null,bound:false,destroyed:false};
  const context={state,nodes:{scroll,groups:{contains:node=>owned && node===section}},Math,Date:{now:()=>clock},
    cancelUITimer:()=>{},cancelBattleNavigation:()=>{state.battleJump=null;},queueResize:()=>{queued++;},
    resetViewScroll:()=>{state.scrollTarget=0;scroll.scrollTop=0;}};
  vm.createContext(context);vm.runInContext(actual,context);context.captureFeedAnchor(feed);
  return {context,state,feed,scroll,section,
    prepend(){position=1500;state.cardPages=[inserted,original];},
    missing(value){missing=value;},precedingMissing(value){precedingMissing=value;},detach(){owned=false;},
    advance(value){clock+=value;},queued:()=>queued,measure:()=>context.finishFeedAnchor(true)};
}
module.exports=async({check})=>{
  const delayed=nativeGeometry();delayed.prepend();delayed.missing(true);
  for(let sample=0;sample<6;sample++){delayed.advance(25);delayed.measure();}
  check('More than three empty native anchor measurements preserve the pending viewport correction',
    !!delayed.feed.prependAnchor && delayed.scroll.scrollTop===300);
  delayed.missing(false);delayed.measure();
  check('Late native prepend geometry restores the original visible section position',
    delayed.scroll.scrollTop===1300 && delayed.section.getBoundingClientRect().top===300);
  delayed.measure();delayed.measure();
  check('Three valid settled measurements retire the native anchor without further movement',
    delayed.feed.prependAnchor===null && delayed.scroll.scrollTop===1300);

  const columns=nativeGeometry();columns.prepend();columns.precedingMissing(true);
  for(let sample=0;sample<5;sample++)columns.measure();
  check('A measurable anchor waits for empty native cards inserted before it',
    !!columns.feed.prependAnchor && columns.scroll.scrollTop===300);
  columns.precedingMissing(false);columns.measure();
  check('Settled preceding native cards permit the pending compensation',columns.scroll.scrollTop===1300);

  for(const budget of ['deadline','attempts']) {
    const expired=nativeGeometry();expired.prepend();expired.missing(true);
    if(budget==='deadline')expired.advance(2000);
    for(let sample=0;sample<45 && expired.feed.prependAnchor;sample++)expired.measure();
    const calls=expired.queued();expired.missing(false);expired.measure();
    check('Permanently empty native geometry retires its '+budget+' budget and cannot revive on a later resize',
      expired.feed.prependAnchor===null && expired.scroll.scrollTop===300 && expired.queued()===calls);
  }

  for(const cancel of ['user-scroll','top','context','detached-section']) {
    const interrupted=nativeGeometry();interrupted.prepend();
    if(cancel==='user-scroll') {
      interrupted.context.onScrollIntent({type:'mousedown',target:interrupted.scroll});interrupted.scroll.scrollTop=175;
    } else if(cancel==='top')interrupted.context.revealFeedTop(interrupted.feed);
    else if(cancel==='context')interrupted.context.retireFeed();
    else interrupted.detach();
    interrupted.measure();
    check('A newer '+cancel+' intent retires native prepend compensation',
      interrupted.feed.prependAnchor===null && interrupted.scroll.scrollTop===(cancel==='top'?0:cancel==='user-scroll'?175:300));
  }
};
if(require.main===module)module.exports({check:(name,passed)=>{assert(passed,name);console.log('PASS '+name);}})
  .catch(error=>{console.error(error);process.exitCode=1;});
