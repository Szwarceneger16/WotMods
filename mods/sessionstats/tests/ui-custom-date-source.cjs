/* Actual shipped date parsing/masking/range guards, independent of Chromium. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm'),child=require('child_process');
const source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
function actual(name) {
  const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }\n',start);
  assert(start>=0 && end>start,'Missing shipped function '+name);return source.slice(start,end+7);
}
const names=['dateLocale','customDatePlaceholder','customDateSeparator','customDateValue','customDateParts','datePad','customDateText','customDateMask','dateCaret','maskDateInput','deleteDateSeparator','timelineDateBound','customDateBounds','applyTimelineRange'];
const code=names.map(actual).join('\n');
function host(messages) {
  const timeline={from_point:'',to_point:'',from_date:null,to_date:null,time_points:[]},sent=[],errors=[];
  const state={destroyed:false,payload:{account_key:'synthetic',scopes:{timeline}},customDates:{},orderIntent:null};
  class FixtureDate extends Date {}
  FixtureDate.now=()=>new Date(2030,0,1,12,0).getTime();
  const context={state,Date:FixtureDate,Math,Intl:undefined,hasNumber:value=>typeof value==='number' && isFinite(value),t:key=>messages[key]||key,
    timelineError:(field,message)=>errors.push({field,message}),cancelBattleNavigation:()=>{},retireFeed:()=>{},invoke:(action,args)=>{sent.push({action,args});return true;}};
  vm.createContext(context);vm.runInContext(code,context);return {context,state,timeline,sent,errors};
}
module.exports=async({check})=>{
  for(const [language,messages] of Object.entries(catalogs)) {
    const {context:c,state,timeline,sent,errors}=host(messages),separator=language==='fr'||language==='es'?'/':'.';
    const text=value=>value.replace(/\./g,separator),epoch=new Date(2028,1,29,7,5).getTime()/1000;
    check('Date order/separators follow the shipped locale without Intl: '+language,
      c.customDateSeparator()===separator && c.customDateText(epoch)===text('29.02.2028 07:05') && c.customDateValue(text('29.02.2028 07:05'))===epoch);
    let draft='';for(const digit of '290220280705')draft=c.customDateMask(draft+digit);
    check('Uninterrupted twelve-digit input produces a complete local date/time mask: '+language,draft===text('29.02.2028 07:05'));
    const invalid=['29.02.2025 07:05','31.04.2028 07:05','00.02.2028 07:05','29.13.2028 07:05','29.02.2028 24:00','29.02.2028 07:60','29.02.1969 07:05'];
    check('Leap-day/month/day/time/year errors cannot normalize silently: '+language,invalid.every(value=>c.customDateValue(text(value))===null));
    check('Partial digit entry stays a draft until a complete valid date exists: '+language,
      c.customDateValue(c.customDateMask('2902202'))===null && c.customDateValue(text('29.02.2028'))===new Date(2028,1,29).getTime()/1000);
    check('Calendar components use the same strict date validator as typed text: '+language,
      c.customDateParts(2028,2,29,7,5)===epoch && c.customDateParts(2025,2,29,7,5)===null && c.customDateParts(3000,1,1,0,0)!==null);
    state.customDates={from:{value:text('29.02.2028 07:05')},to:{value:text('01.03.2028 16:45')}};
    c.applyTimelineRange(timeline,'to','__custom__','synthetic');
    check('A valid calendar/typed range sends exact account-owned local epochs: '+language,
      sent.length===1 && sent[0].args.from_date===epoch && sent[0].args.to_date===new Date(2028,2,1,16,45).getTime()/1000);
    state.customDates.to.value=state.customDates.from.value;c.applyTimelineRange(timeline,'to','__custom__','synthetic');
    state.customDates.to.value=text('28.02.2028 23:59');c.applyTimelineRange(timeline,'to','__custom__','synthetic');
    check('Equal or inverted custom bounds never dispatch: '+language,sent.length===1 && errors.length===2 && errors.every(error=>error.message===messages['timeline.custom_order']));
    state.customDates.to.value=text('01.03.2028 16:45');state.payload.account_key='replacement';c.applyTimelineRange(timeline,'to','__custom__','synthetic');
    state.payload.account_key='synthetic';state.payload.scopes.timeline={...timeline,to_point:'replacement'};c.applyTimelineRange(timeline,'to','__custom__','synthetic');
    check('Retained date actions cannot mutate a replacement account or range: '+language,sent.length===1);
  }
  {
    const {context:c,state,timeline,sent,errors}=host(catalogs.en),now=new Date(2028,1,29,12,34).getTime()/1000;
    c.Date.now=()=>now*1000+45000;
    state.customDates={from:{value:'29.02.2028 12:35'}};
    c.applyTimelineRange(timeline,'from','__custom__','synthetic');
    check('Manual future minute is rejected before any range command is sent',sent.length===0&&errors[0].message===catalogs.en['timeline.custom_future']);
    state.customDates={from:{value:'29.02.2028 12:33'},to:{value:'29.02.2028 12:35'}};
    c.applyTimelineRange(timeline,'to','__custom__','synthetic');
    check('A future end date cannot bypass the same manual-entry guard',sent.length===0&&errors.length===2);
    state.customDates={from:{value:'29.02.2028 12:33'},to:{value:'29.02.2028 12:34'}};
    c.applyTimelineRange(timeline,'to','__custom__','synthetic');
    check('The current minute remains available when both bounds are ordered',sent.length===1&&sent[0].args.to_date===now);
    const from=c.customDateBounds(timeline,'from'),to=c.customDateBounds(timeline,'to');
    check('Graphical From and To bounds exclude the opposite exact minute',from.maximum===now-60&&to.minimum===now&&to.maximum===now);
    state.customDates={};timeline.time_points=[['other',now-120]];timeline.from_point='other';
    check('Graphical bounds also honor saved time points',c.customDateBounds(timeline,'to').minimum===now-60);
    timeline.from_point='';state.customDates={from:{value:'29.02.2028 12:35'}};
    const empty=c.customDateBounds(timeline,'to');
    check('An impossible opposite draft produces no selectable graphical interval',empty.minimum>empty.maximum);
  }
  for(const [order,separator,digits,expected] of [
    ['MDY','/','022920280705','02/29/2028 07:05'],
    ['YMD','-','202802290705','2028-02-29 07:05'],
    ['DMY','-','290220280705','29-02-2028 07:05']]) {
    const {context:c,state}=host(catalogs.pl),epoch=new Date(2028,1,29,7,5).getTime()/1000;
    state.payload.localization={date_settings:{order,separator,first_weekday:0,hour12:false}};
    check('Native regional '+order+' format overrides UI language in parsing, rendering, digit masks and placeholder',
      c.customDateValue(expected)===epoch && c.customDateText(epoch)===expected && c.customDateMask(digits)===expected &&
      c.customDatePlaceholder().startsWith(order==='YMD'?'yyyy':order==='MDY'?'mm':'dd'));
    check('A native Sunday-first week is retained independently of Polish UI language: '+order,c.dateLocale().first===0);
  }
  {
    const {context:c,state}=host(catalogs.en),epoch=new Date(2028,1,29,19,5).getTime()/1000;
    state.payload.localization={date_settings:{order:'MDY',separator:'/',hour12:true,periods:['AM','PM'],first_weekday:0}};
    check('Twelve-hour native formatting preserves exact afternoon epochs without Intl',
      c.customDateText(epoch)==='02/29/2028 07:05 PM' && c.customDateValue('02/29/2028 07:05 PM')===epoch &&
      c.customDateMask('022920280705PM')==='02/29/2028 07:05 PM');
    check('Twelve-hour midnight/noon and invalid/absent day periods are unambiguous',
      c.customDateValue('02/29/2028 12:00 AM')===new Date(2028,1,29,0,0).getTime()/1000 &&
      c.customDateValue('02/29/2028 12:00 PM')===new Date(2028,1,29,12,0).getTime()/1000 &&
      c.customDateValue('02/29/2028 00:00 AM')===null && c.customDateValue('02/29/2028 13:00 PM')===null &&
      c.customDateValue('02/29/2028 07:05')===null && c.customDateValue('02/29/2028')===new Date(2028,1,29).getTime()/1000);
    function typed(text) {
      const input={value:'',selectionStart:0,selectionEnd:0,setSelectionRange(start,end){this.selectionStart=start;this.selectionEnd=end;}};
      for(const char of text) { const at=input.selectionStart;input.value=input.value.slice(0,at)+char+input.value.slice(input.selectionEnd);input.selectionStart=input.selectionEnd=at+char.length;c.maskDateInput(input); }
      return input;
    }
    const input=typed('022920280705PM');
    check('Sequential PM typing keeps the suffix caret and exact afternoon meaning',
      input.value==='02/29/2028 07:05 PM' && input.selectionStart===19 && c.customDateValue(input.value)===epoch);
    let intercepted=false;input.oninput=()=>c.maskDateInput(input);
    c.deleteDateSeparator(input,{key:'Backspace',preventDefault(){intercepted=true;}});
    const suffixAt=input.selectionStart;input.value=input.value.slice(0,suffixAt-1)+input.value.slice(suffixAt);input.selectionStart=input.selectionEnd=suffixAt-1;c.maskDateInput(input);
    check('Backspace within a day-period suffix edits letters rather than deleting minute digits',
      !intercepted && input.value==='02/29/2028 07:05 P' && input.value.replace(/[^0-9]/g,'').length===12);
    input.value='02/29/2028 07:05 PM';input.selectionStart=input.selectionEnd=16;
    input.value=input.value.slice(0,15)+input.value.slice(16);input.selectionStart=input.selectionEnd=15;c.maskDateInput(input);
    check('Editing a minute digit keeps a pre-existing PM period in the unfinished draft',input.value==='02/29/2028 07:0 PM');
    for(const periods of [['오전','오후'],['π.μ.','μ.μ.']]) {
      state.payload.localization.date_settings.periods=periods;
      const localized=typed('022920280705'+periods[1]);
      check('Sequential localized PM entry survives shared prefixes and punctuation: '+periods[1],
        localized.value==='02/29/2028 07:05 '+periods[1] && c.customDateValue(localized.value)===epoch);
    }
    state.payload.localization.date_settings.periods=['AM','PM'];
    const old=c.dateLocale();state.payload.localization.date_settings={order:'YMD',separator:'-',hour12:false};
    check('A complete regional date draft can be reformatted without changing its timestamp',
      c.customDateText(c.customDateValue('02/29/2028 07:05 PM',old))==='2028-02-29 19:05');
  }
  const c=host(catalogs.en).context;
  const input={value:'011120260915',selectionStart:12,setSelectionRange(start,end){this.selectionStart=start;this.selectionEnd=end;}};
  c.maskDateInput(input);
  check('Masking retains the digit caret at the end of the complete date/time',input.value==='01.11.2026 09:15' && input.selectionStart===16);
  input.selectionStart=input.selectionEnd=3;let prevented=false;
  input.oninput=()=>c.maskDateInput(input);c.deleteDateSeparator(input,{key:'Backspace',preventDefault(){prevented=true;}});
  check('Backspace on an inserted separator deletes a digit instead of trapping the caret',prevented && input.value.replace(/[^0-9]/g,'').length===11 && input.selectionStart<3);
  const dstCode=code+'\nconsole.log(JSON.stringify([customDateValue("29.03.2026 02:30"),customDateParts(2026,3,29,2,30),customDateValue("29.03.2026 03:30")]));';
  const dst=JSON.parse(child.execFileSync(process.execPath,['-e','const t=()=>"{0}.{1}.{2}, {3}:{4}";const state={};const hasNumber=value=>typeof value==="number"&&isFinite(value);'+dstCode],{env:{...process.env,TZ:'Europe/Warsaw'},encoding:'utf8'}));
  check('Typed and calendar component paths reject a Warsaw DST-gap time while accepting the subsequent real time',dst[0]===null && dst[1]===null && typeof dst[2]==='number');
};
if(require.main===module)module.exports({check:(name,passed)=>{assert(passed,name);console.log('PASS '+name);}})
  .catch(error=>{console.error(error);process.exitCode=1;});
