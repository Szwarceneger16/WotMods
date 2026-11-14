/* Exercise the shipped clock geometry and selection without a browser. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
function actual(name) {
  const start=source.indexOf('        function '+name+'('),end=source.indexOf('\n        }\n',start);
  assert(start>=0&&end>start,'Missing shipped clock function '+name);return source.slice(start,end+11);
}
function host(hour12,hour=0,allowed=null) {
  function node(className) {
    return {className,style:{},attributes:{},children:[],setAttribute(key,value){this.attributes[key]=value;},
      getAttribute(key){return this.attributes[key];},getBoundingClientRect(){return {left:0,top:0,width:200,height:200};},
      querySelector(selector){return all(this).find(value=>selector[0]==='.'&&value.className.split(' ').includes(selector.slice(1)));},
      querySelectorAll(selector){return all(this).filter(value=>selector==='[data-clock-value]'&&value.attributes['data-clock-value']!==undefined);}};
  }
  function all(parent){return parent.children.flatMap(value=>[value,...all(value)]);}
  function append(parent,child){parent.children.push(child);return child;}
  const picker={clock:'hours',hour,minute:0},format={hour12,periods:['AM','PM']},clockBody=node('holder');
  const c={picker,format,clockBody,Math,String,live:()=>true,append,element:(tag,className)=>node(className),
    action:(parent,className,label,click)=>{const value=append(parent,node(className));value.textContent=label;value.onclick=()=>{if(!value.disabled)click();};return value;},
    t:key=>key,datePad:value=>String(value).padStart(2,'0'),unavailable:(value,disabled)=>{value.disabled=disabled;},
    hourAvailable:value=>!allowed||allowed.includes(value),hourMinute:(hour,minute)=>hour*60+minute,validTime:()=>true,
    chooseHour:value=>{if(allowed&&!allowed.includes(value))return false;picker.hour=value;return true;},
    updateTime:()=>{},focusControl:()=>{},focusClock:()=>{},draw:()=>{}};
  vm.createContext(c);vm.runInContext(['setClock','updateHand','clockPoint','drawClock'].map(actual).join('\n'),c);
  c.drawClock();return c;
}
module.exports=async({check})=>{
  for(const hour12 of [false,true]) {
    const c=host(hour12),face=c.clockBody.querySelector('.ss-date-clock'),buttons=face.querySelectorAll('[data-clock-value]');
    const midnight=buttons.find(node=>+node.getAttribute('data-clock-value')===(hour12?12:0));
    check((hour12?'12h retains 12':'24h renders 00')+' at the outer top of the clock',
      midnight.textContent===(hour12?'12':'00')&&midnight.style.top==='10%'&&!midnight.className.includes('ss-date-clock-inner'));
    check('The '+(hour12?'12h':'24h')+' hour dial has unique values and keeps its complete range',
      buttons.length===(hour12?12:24)&&new Set(buttons.map(node=>node.getAttribute('data-clock-value'))).size===buttons.length);
    if(!hour12) {
      const noon=buttons.find(node=>+node.getAttribute('data-clock-value')===12);
      check('24h places noon at the inner top of the clock',noon.style.top==='25%'&&noon.className.includes('ss-date-clock-inner'));
    }
    for(let hour=0;hour<24;hour++) {
      c.picker.hour=hour;c.updateHand();
      const expected=hour12?hour%12||12:hour,selected=buttons.filter(node=>node.getAttribute('aria-pressed')==='true');
      check('Hour '+hour+' selects its correct value and hand radius in '+(hour12?'12h':'24h'),
        selected.length===1&&+selected[0].getAttribute('data-clock-value')===expected&&
        c.clockBody.querySelector('.ss-date-clock-hand').style.height===(!hour12&&hour>=12?'25%':'38%'));
      const angle=(hour%12)*Math.PI/6,radius=!hour12&&hour>=12?50:80;
      c.clockPoint({clientX:100+Math.sin(angle)*radius,clientY:100-Math.cos(angle)*radius});
      check('Pointer selects hour '+hour+' on the matching '+(hour12?'12h':'24h')+' ring',c.picker.hour===hour);
    }
  }
  const c=host(false,12,[12]),face=c.clockBody.querySelector('.ss-date-clock');
  check('Midnight availability remains separate from noon after swapping their ring positions',
    face.querySelectorAll('[data-clock-value]').find(node=>node.getAttribute('data-clock-value')==='0').disabled&&
    !face.querySelectorAll('[data-clock-value]').find(node=>node.getAttribute('data-clock-value')==='12').disabled);
  c.clockPoint({clientX:100,clientY:20});
  check('A pointer cannot select unavailable outer midnight',c.picker.hour===12);
  c.clockPoint({clientX:100,clientY:50});
  check('The available inner noon remains selectable',c.picker.hour===12);
};
if(require.main===module){let checks=0;module.exports({check:(name,pass)=>{assert(pass,name);checks++;}}).then(()=>console.log('Clock geometry assertions passed: '+checks));}
