/* Dependency-free Node DOM contracts. Optional real-browser pass: GRZ_MEDKIT_BROWSER_TEST=1. */
const assert=require('assert');
const fs=require('fs');
const path=require('path');
const vm=require('vm');
const root=path.resolve(__dirname,'..');
const script=path.join(root,'source/staysharp_medkit/ui/footer.js');
const settingsScript=path.join(root,'source/staysharp_medkit/ui/settings.js');
async function nodeContracts(){
  class Element {
    constructor(tag, document) {
      this.tagName=tag.toUpperCase(); this.ownerDocument=document; this.children=[];
      this.parentNode=null; this.attributes={}; this.className=''; this.id='';
      this.style={}; this.textContent=''; this.listeners={};
    }
    get firstChild(){return this.children[0]||null;}
    get nextSibling(){if(!this.parentNode)return null;return this.parentNode.children[this.parentNode.children.indexOf(this)+1]||null;}
    appendChild(child){return this.insertBefore(child,null);}
    insertBefore(child,before){if(child.parentNode)child.parentNode.removeChild(child);const i=before===null?this.children.length:this.children.indexOf(before);assert(i>=0);this.children.splice(i,0,child);child.parentNode=this;return child;}
    removeChild(child){const i=this.children.indexOf(child);assert(i>=0);this.children.splice(i,1);child.parentNode=null;return child;}
    contains(child){return this===child||this.children.some(node=>node.contains(child));}
    setAttribute(name,value){this.attributes[name]=String(value);if(name==='id')this.id=String(value);if(name==='class')this.className=String(value);}
    getAttribute(name){if(name==='class')return this.className;if(name==='id')return this.id;return this.attributes[name]===undefined?null:this.attributes[name];}
    addEventListener(name,callback,capture){(this.listeners[name]||(this.listeners[name]=[])).push({callback,capture:!!capture});}
    removeEventListener(name,callback,capture){this.listeners[name]=(this.listeners[name]||[]).filter(item=>item.callback!==callback||item.capture!==!!capture);}
    querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
    querySelectorAll(selector){const result=[];const selectors=selector.split(',').map(value=>value.trim());function matches(node,s){if(s[0]==='#')return node.id===s.slice(1);if(s[0]==='.')return node.className.split(/\s+/).includes(s.slice(1));const attr=s.match(/^\[([^=*]+)(\*)?="([^"]*)"\]$/);if(attr){const value=node.getAttribute(attr[1]);return value!==null&&(attr[2]?value.includes(attr[3]):value===attr[3]);}return node.tagName.toLowerCase()===s.toLowerCase();}function walk(parent){parent.children.forEach(child=>{if(selectors.some(s=>matches(child,s)))result.push(child);walk(child);});}walk(this);return result;}
    dispatchEvent(event){event.target=event.target||this;event.stopped=false;event.defaultPrevented=false;event.stopPropagation=function(){this.stopped=true;};event.preventDefault=function(){this.defaultPrevented=true;};const doc=this.ownerDocument;for(const item of (doc.listeners[event.type]||[]).slice()){if(item.capture)item.callback(event);if(event.stopped)return !event.defaultPrevented;}let node=this;while(node){const handler=node['on'+event.type];if(handler)handler(event);if(event.stopped)return !event.defaultPrevented;node=node.parentNode;}for(const item of (doc.listeners[event.type]||[]).slice()){if(!item.capture)item.callback(event);if(event.stopped)break;}return !event.defaultPrevented;}
    click(){this.dispatchEvent({type:'click'});}
    getBoundingClientRect(){return this.rect||{left:1750,top:8,width:40,height:36,bottom:44,right:1790};}
  }
  function fixture(options={}) {
    const doc={listeners:{},createElement(tag){return new Element(tag,this);}};
    doc.documentElement=doc.createElement('html');doc.head=doc.createElement('head');doc.body=doc.createElement('body');doc.documentElement.appendChild(doc.head);doc.documentElement.appendChild(doc.body);
    doc.querySelector=selector=>doc.documentElement.querySelector(selector);doc.getElementById=id=>doc.querySelector('#'+id);
    doc.addEventListener=Element.prototype.addEventListener;doc.removeEventListener=Element.prototype.removeEventListener;
    function el(tag,id,cls,parent){const n=doc.createElement(tag);n.id=id;n.className=cls||'';parent.appendChild(n);return n;}
    // Exact native structure: left controls, chats, right controls. The gear
    // follows Ping/EU2 inside the right Footer_section (asset blob fa4f000a).
    const footer=el('div','native-footer','Footer_c3a0f302 App_footer_8633140e',doc.body);
    const left=el('div','native-left-row','Footer_section_9d3d3a12',footer);
    el('button','native-left','',left);el('div','native-chats','Chats_native',footer);
    const row=el('div','native-row','Footer_section_9d3d3a12',footer);
    el('div','native-compare','VehicleCompare_cff2d129 Footer_vehicleCompare_531bca52',row);
    const native=el('div','wg-session','SessionStatistic_2cb87b7d',row);
    el('button','grz-session-stats-footer-button','',row);
    el('div','native-divider','Footer_divider_4ccd0230',row);
    el('div','native-region','Ping_da5c25be',row).textContent='EU2';
    const menu=options.noMenu?null:el('div','native-menu','Footer_icon_6ff60f47',row);
    if(menu)menu.setAttribute('data-test-id','menu');
    el('div','native-divider2','Footer_divider_4ccd0230',row);
    el('div','native-notifications','Footer_icon_6ff60f47 Footer_icon__notification_827f4505',row).setAttribute('data-test-id','notificationCenter');
    doc.documentElement.clientWidth=1920;doc.documentElement.clientHeight=36;doc.body.clientWidth=1920;
    const state={hotkeys:{toggle_mod:['KEY_LCONTROL','KEY_LALT','KEY_M'],toggle_voice:['KEY_LCONTROL','KEY_LALT','KEY_V']},display:{toggle_mod:'Ctrl + Alt + M',toggle_voice:'Ctrl + Alt + V'},capturing:null,preview:[],labels:{},status:'',error:''};
    const events={},actions=[],layouts=[],callbacks=[],warnings=[],frames=[],sizes=[],observers=[];
    if(options.settings){const view=el('section','grz-medkit-settings','grz-medkit-settings',doc.body);for(const suffix of ['title','close','label-mod','label-voice','mod','voice','clear-mod','clear-voice','hint','feedback','cancel'])el(suffix==='mod'||suffix==='voice'||suffix.indexOf('clear-')===0||suffix==='close'||suffix==='cancel'?'button':'div','grz-medkit-settings-'+suffix,'',view);}
    if(options.captions){for(const suffix of ['mod','voice','clear-mod','clear-voice','cancel','close'])el('span','grz-medkit-settings-'+suffix+'-caption','grz-medkit-settings-button-label',doc.getElementById('grz-medkit-settings-'+suffix));}
    state.viewport={width:1920,height:1080,scale:1.5};
    const model={state:{value:JSON.stringify(state)},onAction:args=>{const copy=JSON.parse(JSON.stringify(args));(copy.action==='layout'?layouts:actions).push(copy);}};
    const context={document:doc,innerWidth:1000,innerHeight:36,console:{warn:message=>warnings.push(message)},isDomBuilt:!options.pendingDom,testID:41,
      engine:{whenReady:Promise.resolve(),on(name,callback){(events[name]||(events[name]=[])).push(callback);},off(name,callback){events[name]=(events[name]||[]).filter(value=>value!==callback);}},
      viewEnv:{getClientSizePx(){return {width:1920,height:1080};},getViewGlobalPositionRem(){return {x:0,y:1040};},remToPx(value){return value;},getViewSizePx(){const size=sizes[sizes.length-1]||[256,256];return {width:size[0],height:size[1]};},resizeViewPx(width,height){sizes.push([width,height]);},addDataChangedCallback(name,id){callbacks.push(['add',id]);if(options.sync)emit();return id+100;},removeDataChangedCallback(callback,id){callbacks.push(['remove',id]);}},
      subViews:{ids(){return context.testID===null?[]:[context.testID];},get(){return {model:{grzMedkitFooter:{value:model}}};}},
      requestAnimationFrame(callback){frames.push(callback);},addEventListener(name,callback){(events[name]||(events[name]=[])).push(callback);},removeEventListener(name,callback){events[name]=(events[name]||[]).filter(value=>value!==callback);}};
    context.MutationObserver=class{constructor(callback){this.callback=callback;this.active=false;observers.push(this);}observe(){this.active=true;if(options.observerThrows)throw new Error('observer unavailable');}disconnect(){this.active=false;}};
    if(options.noNativeAnchor){delete context.viewEnv.getClientSizePx;delete context.viewEnv.getViewGlobalPositionRem;delete context.viewEnv.remToPx;}
    context.window=context;
    if(options.settings){if(options.viewEnvModel)context.viewEnv.model=model;else context.model=model;}
    function emit(){(events['viewEnv.onDataChanged']||[]).slice().forEach(callback=>callback());}
    function patch(value){Object.assign(state,value);model.state={value:JSON.stringify(state)};emit();}
    vm.createContext(context);vm.runInContext(fs.readFileSync(options.settings?settingsScript:script,'utf8'),context);
    return {doc,footer,left,row,menu,native,state,model,context,actions,layouts,callbacks,warnings,events,sizes,observers,el,emit,patch,mutate(){observers.filter(observer=>observer.active).forEach(observer=>observer.callback());}};
  }
  const f=fixture({sync:true});await Promise.resolve();
  const find=(owner,selector)=>{const node=owner.doc.querySelector(selector);assert(node,selector);return node;};
  assert.deepStrictEqual(f.actions,[],'Binding cannot dispatch commands');
  assert.deepStrictEqual(f.row.children.map(node=>node.id),['native-compare','wg-session','grz-session-stats-footer-button','native-divider','native-region','grz-medkit-footer-host','native-menu','native-divider2','native-notifications']);
  assert.strictEqual(f.footer.children.length,3,'The outer native space-between footer retains exactly three sections');
  assert.deepStrictEqual(f.left.children.map(node=>node.id),['native-left']);
  assert.strictEqual(f.doc.getElementById('grz-medkit-settings'),null,'Footer contains only its icon; it never borrows native hit area');
  find(f,'#grz-medkit-footer-button').click();assert.deepStrictEqual(f.actions,[{action:'open',anchorX:1770/1920,anchorY:1048/1080}]);
  delete f.context.innerWidth;find(f,'#grz-medkit-footer-button').click();assert.deepStrictEqual(f.actions.at(-1),{action:'open',anchorX:1770/1920,anchorY:1048/1080},'Coherent does not need window.innerWidth to compute a global native anchor');
  find(f,'#grz-medkit-footer-button').click();assert.deepStrictEqual(f.actions.at(-1),f.actions[0],'Every click reaches native open/toggle; no local stale popup state');
  f.patch({labels:{title:'<img src=x>'}});assert.strictEqual(find(f,'#grz-medkit-footer-button').getAttribute('aria-label'),'<img src=x>');
  const before=f.actions.length;f.context.testID=42;f.emit();assert.strictEqual(f.actions.length,before);assert.deepStrictEqual(f.callbacks,[['add',41],['remove',41],['add',42]]);
  vm.runInContext(fs.readFileSync(script,'utf8'),f.context);assert.strictEqual(f.row.children.filter(node=>node.id==='grz-medkit-footer-host').length,1);
  assert.strictEqual(f.native,f.doc.getElementById('wg-session'));
  f.context.GRZStaySharpFooter.destroy();f.context.GRZStaySharpFooter.destroy();assert.strictEqual(f.doc.getElementById('grz-medkit-footer-host'),null);assert.deepStrictEqual(f.callbacks.at(-1),['remove',42]);assert.strictEqual(f.actions.length,before);
  assert.strictEqual(f.observers.filter(observer=>observer.active).length,0,'Native DOM observation ends with the footer');
  const late=fixture({pendingDom:true});await Promise.resolve();assert.strictEqual(late.doc.getElementById('grz-medkit-footer-host'),null);late.context.isDomBuilt=true;late.events['self.onDomBuilt'].slice().forEach(callback=>callback());assert(late.doc.getElementById('grz-medkit-footer-host'));late.context.testID=null;late.emit();assert.strictEqual(late.doc.getElementById('grz-medkit-footer-host'),null);assert.deepStrictEqual(late.actions,[]);late.context.GRZStaySharpFooter.destroy();
  const delayedMenu=fixture({noMenu:true});await Promise.resolve();
  assert.strictEqual(delayedMenu.doc.getElementById('grz-medkit-footer-host'),null,'A missing gear never falls back to a left-side/native root mount');
  const gear=delayedMenu.el('div','native-menu','Footer_icon_6ff60f47',delayedMenu.row);gear.setAttribute('data-test-id','menu');
  delayedMenu.row.insertBefore(gear,delayedMenu.doc.getElementById('native-divider2'));delayedMenu.mutate();
  const mounted=delayedMenu.doc.getElementById('grz-medkit-footer-host');assert(mounted);assert.strictEqual(mounted.nextSibling,gear);
  const newControl=delayedMenu.el('div','native-extra','Native_extra',delayedMenu.row);delayedMenu.row.insertBefore(newControl,gear);delayedMenu.mutate();
  assert.strictEqual(mounted.nextSibling,gear,'Native row changes re-anchor the existing host immediately before the gear');
  assert.strictEqual(delayedMenu.row.children.filter(node=>node.id==='grz-medkit-footer-host').length,1);
  delayedMenu.row.removeChild(gear);delayedMenu.mutate();assert.strictEqual(delayedMenu.doc.getElementById('grz-medkit-footer-host'),null);
  delayedMenu.context.GRZStaySharpFooter.destroy();
  const origin=fixture();await Promise.resolve();
  origin.context.viewEnv.getClientSizePx=()=>({width:3840,height:2160});origin.context.viewEnv.getViewGlobalPositionRem=()=>({x:80,y:1000});origin.context.viewEnv.remToPx=value=>value*2;
  find(origin,'#grz-medkit-footer-button').rect={left:1690,top:20,width:40,height:36};find(origin,'#grz-medkit-footer-button').click();
  assert.deepStrictEqual(origin.actions.at(-1),{action:'open',anchorX:1870/3840,anchorY:2020/2160},'Native view origin converts rem to px before normalization against full client dimensions');
  find(origin,'#grz-medkit-footer-button').rect={left:9000,top:9000,width:40,height:36};find(origin,'#grz-medkit-footer-button').click();assert.deepStrictEqual(origin.actions.at(-1),{action:'open',anchorX:1,anchorY:1});
  find(origin,'#grz-medkit-footer-button').rect={left:-9000,top:-9000,width:40,height:36};find(origin,'#grz-medkit-footer-button').click();assert.deepStrictEqual(origin.actions.at(-1),{action:'open',anchorX:0,anchorY:0});
  origin.context.GRZStaySharpFooter.destroy();
  const fallback=fixture({noNativeAnchor:true});await Promise.resolve();
  delete fallback.context.innerWidth;find(fallback,'#grz-medkit-footer-button').click();assert.deepStrictEqual(fallback.actions.at(-1),{action:'open',anchorX:1770/1920},'documentElement width remains usable when Coherent omits innerWidth');
  fallback.doc.documentElement.clientWidth=0;fallback.doc.body.clientWidth=0;fallback.context.innerWidth=1920;
  find(fallback,'#grz-medkit-footer-button').click();assert.deepStrictEqual(fallback.actions.at(-1),{action:'open',anchorX:1770/1920});
  fallback.context.innerWidth=NaN;fallback.doc.body.clientWidth=1920;find(fallback,'#grz-medkit-footer-button').click();assert.deepStrictEqual(fallback.actions.at(-1),{action:'open',anchorX:1770/1920});
  fallback.doc.body.clientWidth=0;find(fallback,'#grz-medkit-footer-button').click();assert.deepStrictEqual(fallback.actions.at(-1),{action:'open',anchorX:0.5},'An unmeasurable viewport uses the center, not the left edge, and omits unknown Y');
  fallback.context.GRZStaySharpFooter.destroy();
  const unobserved=fixture({observerThrows:true});await Promise.resolve();
  assert.strictEqual(unobserved.observers.filter(observer=>observer.active).length,0,'A failed optional observer cannot leak a partial registration');
  find(unobserved,'#grz-medkit-footer-button').click();assert.strictEqual(unobserved.actions.at(-1).action,'open','Unavailable DOM observation does not disable a valid native gear anchor');
  unobserved.context.GRZStaySharpFooter.destroy();
  for(const viewEnvModel of [false,true]){
    const s=fixture({settings:true,sync:true,viewEnvModel});await Promise.resolve();
    assert.deepStrictEqual(s.actions,[],'Native Settings binding cannot replay an action');assert.deepStrictEqual(s.callbacks,[['add',0]]);
    assert.deepStrictEqual(s.sizes,[[540,420]],'Texture sizing uses Python GUI scale, never browser DPR');
    assert.strictEqual(s.doc.documentElement.style.fontSize,'1.5px');
    assert.strictEqual(find(s,'#grz-medkit-settings-mod').textContent,'Ctrl + Alt + M');
    find(s,'#grz-medkit-settings-mod').click();assert.deepStrictEqual(s.actions.at(-1),{action:'begin_capture',binding:'toggle_mod'});
    s.patch({capturing:'toggle_mod',preview:['Ctrl','Alt','Shift','M']});assert.strictEqual(find(s,'#grz-medkit-settings-mod').textContent,'Ctrl + Alt + Shift + M');assert.strictEqual(find(s,'#grz-medkit-settings-mod').getAttribute('aria-pressed'),'true');
    const longChord=Array.from({length:32},(_,index)=>'Key '+index);s.patch({preview:longChord});assert.strictEqual(find(s,'#grz-medkit-settings-mod').getAttribute('title'),longChord.join(' + '),'The entire supported chord remains available in its title');
    let nativeKeys=0;s.doc.addEventListener('keydown',()=>nativeKeys++);const n=s.actions.length;find(s,'#grz-medkit-settings-mod').dispatchEvent({type:'keydown',key:' '});assert.strictEqual(nativeKeys,0);assert.strictEqual(s.actions.length,n,'DOM keys cannot become toggle actions during binding capture');
    find(s,'#grz-medkit-settings-mod').dispatchEvent({type:'keydown',key:'Escape'});assert.deepStrictEqual(s.actions.at(-1),{action:'cancel_capture'});
    find(s,'#grz-medkit-settings-clear-voice').click();assert.deepStrictEqual(s.actions.at(-1),{action:'clear_binding',binding:'toggle_voice'});
    s.patch({capturing:null,preview:[],hotkeys:{toggle_mod:['Ctrl','Alt','Shift','M'],toggle_voice:[]},display:{toggle_mod:'Ctrl + Alt + Shift + M',toggle_voice:''},status:'Shortcut saved.'});assert.strictEqual(find(s,'#grz-medkit-settings-voice').textContent,'Not assigned');assert.strictEqual(find(s,'#grz-medkit-settings-feedback').textContent,'Shortcut saved.');
    s.patch({labels:{title:'<img src=x>'},error:'<script>literal()</script>'});assert.strictEqual(find(s,'#grz-medkit-settings-title').textContent,'<img src=x>');assert.strictEqual(find(s,'#grz-medkit-settings-feedback').textContent,'<script>literal()</script>');assert.strictEqual(find(s,'#grz-medkit-settings').querySelectorAll('img,script').length,0);
    s.model.state={value:'{broken'};s.emit();assert.strictEqual(find(s,'#grz-medkit-settings-feedback').textContent,'Settings unavailable. Close and reopen this window.');s.patch({labels:{},error:'',status:''});
    find(s,'#grz-medkit-settings-close').click();assert.deepStrictEqual(s.actions.at(-1),{action:'close'});
    find(s,'#grz-medkit-settings-voice').dispatchEvent({type:'keydown',key:'Escape'});assert.deepStrictEqual(s.actions.at(-1),{action:'close'});
    s.patch({capturing:'toggle_voice',preview:['Ctrl','Alt','V']});s.context.GRZStaySharpSettings.destroy();s.context.GRZStaySharpSettings.destroy();assert.deepStrictEqual(s.actions.at(-1),{action:'cancel_capture'});assert.deepStrictEqual(s.callbacks.at(-1),['remove',0]);assert.strictEqual((s.doc.listeners.keydown||[]).filter(item=>item.capture).length,0);
  }
  const labeled=fixture({settings:true,captions:true});await Promise.resolve();
  const originalCaption=find(labeled,'#grz-medkit-settings-mod-caption');
  assert.strictEqual(originalCaption.textContent,'Ctrl + Alt + M');
  labeled.patch({capturing:'toggle_mod',preview:['Ctrl','Alt','Shift','M'],labels:{clear:'Wyczyść',cancel:'Anuluj'}});
  assert.strictEqual(find(labeled,'#grz-medkit-settings-mod-caption'),originalCaption,'Native caption elements survive model changes');
  assert.strictEqual(originalCaption.parentNode,find(labeled,'#grz-medkit-settings-mod'));
  assert.strictEqual(originalCaption.textContent,'Ctrl + Alt + Shift + M');
  assert.strictEqual(find(labeled,'#grz-medkit-settings-clear-mod-caption').textContent,'Wyczyść');
  assert.strictEqual(find(labeled,'#grz-medkit-settings-cancel-caption').textContent,'Anuluj');
  labeled.context.GRZStaySharpSettings.destroy();
  const html=fs.readFileSync(path.join(root,'source/staysharp_medkit/ui/settings.html'),'utf8');
  for(const suffix of ['title','close','label-mod','label-voice','mod','voice','clear-mod','clear-voice','hint','feedback','cancel'])assert(html.includes('id="grz-medkit-settings-'+suffix+'"'));
  assert(!/\beval\s*\(|innerHTML|https?:\/\//.test(fs.readFileSync(script,'utf8')+fs.readFileSync(settingsScript,'utf8')),'Native frontend has no executable/remote/config-HTML path');
  console.log('PASS: Node DOM contracts cover the native gear anchor, global/footer-texture coordinates, bounded fallbacks, rerenders, no commands on binding, Settings model, capture shielding, safe text and cleanup.');
}
async function browserContracts(){
  const {chromium}=require('playwright');
  const browser=await chromium.launch({executablePath:process.env.GRZ_CHROME||process.env.GRZ_CHROME_EXECUTABLE,headless:true,args:['--no-sandbox']});
  try{
    const page=await browser.newPage({viewport:{width:900,height:450}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.setContent('<html style="font-size:1px"><head><style>.App_footer_test{display:flex;justify-content:space-between}.Footer_section_test{display:flex;align-items:center}</style></head><body><div class="App_footer_test"><div class="Footer_section_test"><button id="left">Contacts</button></div><div>Chats</div><div class="Footer_section_test"><button class="SessionStatistic_test">WG stats</button><button id="wn8">WN8</button><span id="server">EU2</span><button data-test-id="menu">Gear</button><button>Notifications</button></div></div></body></html>');
    await page.evaluate(()=>{window.actions=[];window.isDomBuilt=true;window.engine={whenReady:Promise.resolve(),on(){},off(){}};window.viewEnv={addDataChangedCallback(){return 1;},removeDataChangedCallback(){}};window.subViews={ids(){return[41];},get(){return{model:{grzMedkitFooter:{state:'{}',onAction:args=>actions.push(args)}}};}};});
    await page.addStyleTag({path:path.join(root,'source/staysharp_medkit/ui/footer.css')});await page.addScriptTag({path:script});await page.waitForSelector('#grz-medkit-footer-button');assert(await page.evaluate(()=>document.querySelector('#grz-medkit-footer-host').nextElementSibling.getAttribute('data-test-id')==='menu'));assert.strictEqual(await page.locator('.App_footer_test > div').count(),3);await page.locator('#grz-medkit-footer-button').click();assert.strictEqual((await page.evaluate(()=>actions))[0].action,'open');
    await page.setContent(fs.readFileSync(path.join(root,'source/staysharp_medkit/ui/settings.html'),'utf8').replace(/<link[^>]+>|<script[^>]+><\/script>/g,''));
    await page.evaluate(()=>{window.actions=[];window.layouts=[];window.state={hotkeys:{toggle_mod:['Ctrl','Alt','M'],toggle_voice:['Ctrl','Alt','V']},capturing:'toggle_mod',preview:['Ctrl','Alt','Shift','M'],viewport:{width:1920,height:1080,scale:1}};window.model={state:JSON.stringify(state),onAction:args=>(args.action==='layout'?layouts:actions).push(args)};window.isDomBuilt=true;window.engine={whenReady:Promise.resolve(),on(){},off(){}};window.viewEnv={addDataChangedCallback(){return 1;},removeDataChangedCallback(){},resizeViewPx(){}};});
    await page.addStyleTag({path:path.join(root,'source/staysharp_medkit/ui/settings.css')});await page.addScriptTag({path:settingsScript});await page.waitForSelector('#grz-medkit-settings-mod');await page.evaluate(()=>Promise.resolve());assert.strictEqual(await page.locator('#grz-medkit-settings-mod').textContent(),'Ctrl + Alt + Shift + M');const dimensions=await page.locator('#grz-medkit-settings').boundingBox();assert.strictEqual(dimensions.width,360);assert.strictEqual(dimensions.height,280);await page.locator('#grz-medkit-settings-mod').focus();await page.keyboard.press('Space');assert.deepStrictEqual(await page.evaluate(()=>actions),[]);await page.locator('#grz-medkit-settings-cancel').click();assert.deepStrictEqual(await page.evaluate(()=>actions),[{action:'cancel_capture'}]);if(process.env.GRZ_MEDKIT_FOOTER_SCREENSHOT)await page.screenshot({path:process.env.GRZ_MEDKIT_FOOTER_SCREENSHOT});assert.deepStrictEqual(errors,[]);console.log('PASS: real-browser native footer icon and 360x280 Settings layout.');
  }finally{await browser.close();}
}
(async()=>{await nodeContracts();if(process.env.GRZ_MEDKIT_BROWSER_TEST==='1')await browserContracts();})().catch(error=>{console.error(error);process.exitCode=1;});
