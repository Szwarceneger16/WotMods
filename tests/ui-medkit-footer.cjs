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
    getBoundingClientRect(){return {left:20,top:400,width:40,height:36,bottom:436,right:60};}
  }
  function fixture(options={}) {
    const doc={listeners:{},createElement(tag){return new Element(tag,this);}};
    doc.documentElement=doc.createElement('html');doc.head=doc.createElement('head');doc.body=doc.createElement('body');doc.documentElement.appendChild(doc.head);doc.documentElement.appendChild(doc.body);
    doc.querySelector=selector=>doc.documentElement.querySelector(selector);doc.getElementById=id=>doc.querySelector('#'+id);
    doc.addEventListener=Element.prototype.addEventListener;doc.removeEventListener=Element.prototype.removeEventListener;
    function el(tag,id,cls,parent){const n=doc.createElement(tag);n.id=id;n.className=cls||'';parent.appendChild(n);return n;}
    const footer=el('div','native-footer','App_footer_verified',doc.body),row=el('div','native-row','Footer_controls',footer);
    el('button','native-left','',row);const native=el('button','wg-session','SessionStats_base_original',row);el('button','native-region','',row);el('button','grz-session-stats-footer-button','',row);
    const state={hotkeys:{toggle_mod:['KEY_LCONTROL','KEY_LALT','KEY_M'],toggle_voice:['KEY_LCONTROL','KEY_LALT','KEY_V']},display:{toggle_mod:'Ctrl + Alt + M',toggle_voice:'Ctrl + Alt + V'},capturing:null,preview:[],labels:{},status:'',error:''};
    const events={},actions=[],callbacks=[],warnings=[],frames=[],sizes=[];
    if(options.settings){const view=el('section','grz-medkit-settings','grz-medkit-settings',doc.body);for(const suffix of ['title','close','label-mod','label-voice','mod','voice','clear-mod','clear-voice','hint','feedback','cancel'])el(suffix==='mod'||suffix==='voice'||suffix.indexOf('clear-')===0||suffix==='close'||suffix==='cancel'?'button':'div','grz-medkit-settings-'+suffix,'',view);}
    state.viewport={width:1920,height:1080,scale:1.5};
    const model={state:{value:JSON.stringify(state)},onAction:args=>actions.push(JSON.parse(JSON.stringify(args)))};
    const context={document:doc,innerWidth:1000,console:{warn:message=>warnings.push(message)},isDomBuilt:!options.pendingDom,testID:41,
      engine:{whenReady:Promise.resolve(),on(name,callback){(events[name]||(events[name]=[])).push(callback);},off(name,callback){events[name]=(events[name]||[]).filter(value=>value!==callback);}},
      viewEnv:{resizeViewPx(width,height){sizes.push([width,height]);},addDataChangedCallback(name,id){callbacks.push(['add',id]);if(options.sync)emit();return id+100;},removeDataChangedCallback(callback,id){callbacks.push(['remove',id]);}},
      subViews:{ids(){return context.testID===null?[]:[context.testID];},get(){return {model:{grzMedkitFooter:{value:model}}};}},
      requestAnimationFrame(callback){frames.push(callback);},addEventListener(name,callback){(events[name]||(events[name]=[])).push(callback);},removeEventListener(name,callback){events[name]=(events[name]||[]).filter(value=>value!==callback);}};
    context.window=context;
    if(options.settings){if(options.viewEnvModel)context.viewEnv.model=model;else context.model=model;}
    function emit(){(events['viewEnv.onDataChanged']||[]).slice().forEach(callback=>callback());}
    function patch(value){Object.assign(state,value);model.state={value:JSON.stringify(state)};emit();}
    vm.createContext(context);vm.runInContext(fs.readFileSync(options.settings?settingsScript:script,'utf8'),context);
    return {doc,row,native,state,model,context,actions,callbacks,warnings,events,sizes,emit,patch};
  }
  const f=fixture({sync:true});await Promise.resolve();
  const find=(owner,selector)=>{const node=owner.doc.querySelector(selector);assert(node,selector);return node;};
  assert.deepStrictEqual(f.actions,[],'Binding cannot dispatch commands');
  assert.deepStrictEqual(f.row.children.map(node=>node.id),['grz-medkit-footer-host','native-left','wg-session','native-region','grz-session-stats-footer-button']);
  assert.strictEqual(f.doc.getElementById('grz-medkit-settings'),null,'Footer contains only its icon; it never borrows native hit area');
  find(f,'#grz-medkit-footer-button').click();assert.deepStrictEqual(f.actions,[{action:'open',anchorX:0.04}]);
  f.context.innerWidth=0;find(f,'#grz-medkit-footer-button').click();assert.deepStrictEqual(f.actions.at(-1),{action:'open',anchorX:0});
  f.patch({labels:{title:'<img src=x>'}});assert.strictEqual(find(f,'#grz-medkit-footer-button').getAttribute('aria-label'),'<img src=x>');
  const before=f.actions.length;f.context.testID=42;f.emit();assert.strictEqual(f.actions.length,before);assert.deepStrictEqual(f.callbacks,[['add',41],['remove',41],['add',42]]);
  vm.runInContext(fs.readFileSync(script,'utf8'),f.context);assert.strictEqual(f.row.children.filter(node=>node.id==='grz-medkit-footer-host').length,1);
  assert.strictEqual(f.native,f.doc.getElementById('wg-session'));
  f.context.GRZStaySharpFooter.destroy();f.context.GRZStaySharpFooter.destroy();assert.strictEqual(f.doc.getElementById('grz-medkit-footer-host'),null);assert.deepStrictEqual(f.callbacks.at(-1),['remove',42]);assert.strictEqual(f.actions.length,before);
  const late=fixture({pendingDom:true});await Promise.resolve();assert.strictEqual(late.doc.getElementById('grz-medkit-footer-host'),null);late.context.isDomBuilt=true;late.events['self.onDomBuilt'].slice().forEach(callback=>callback());assert(late.doc.getElementById('grz-medkit-footer-host'));late.context.testID=null;late.emit();assert.strictEqual(late.doc.getElementById('grz-medkit-footer-host'),null);assert.deepStrictEqual(late.actions,[]);late.context.GRZStaySharpFooter.destroy();
  for(const viewEnvModel of [false,true]){
    const s=fixture({settings:true,sync:true,viewEnvModel});await Promise.resolve();
    assert.deepStrictEqual(s.actions,[],'Native Settings binding cannot replay an action');assert.deepStrictEqual(s.callbacks,[['add',0]]);
    assert.deepStrictEqual(s.sizes,[[540,345]],'Texture sizing uses Python GUI scale, never browser DPR');
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
  const html=fs.readFileSync(path.join(root,'source/staysharp_medkit/ui/settings.html'),'utf8');
  for(const suffix of ['title','close','label-mod','label-voice','mod','voice','clear-mod','clear-voice','hint','feedback','cancel'])assert(html.includes('id="grz-medkit-settings-'+suffix+'"'));
  assert(!/\beval\s*\(|innerHTML|https?:\/\//.test(fs.readFileSync(script,'utf8')+fs.readFileSync(settingsScript,'utf8')),'Native frontend has no executable/remote/config-HTML path');
  console.log('PASS: Node DOM contracts cover far-left native footer order, bounded anchor, no commands on binding, standalone Settings model, GUI texture scale, four-key capture preview, input shielding, selected clear/cancel, safe text, recovery, native DOM retention and lifecycle cleanup.');
}
async function browserContracts(){
  const {chromium}=require('playwright');
  const browser=await chromium.launch({executablePath:process.env.GRZ_CHROME||process.env.GRZ_CHROME_EXECUTABLE,headless:true,args:['--no-sandbox']});
  try{
    const page=await browser.newPage({viewport:{width:900,height:450}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.setContent('<html style="font-size:1px"><head><style>.App_footer_test{display:flex}.Footer_controls{display:flex}</style></head><body><div class="App_footer_test"><div class="Footer_controls"><button id="left">Contacts</button><button class="SessionStats_base_test">WG stats</button><button id="wn8">WN8</button></div></div></body></html>');
    await page.evaluate(()=>{window.actions=[];window.isDomBuilt=true;window.engine={whenReady:Promise.resolve(),on(){},off(){}};window.viewEnv={addDataChangedCallback(){return 1;},removeDataChangedCallback(){}};window.subViews={ids(){return[41];},get(){return{model:{grzMedkitFooter:{state:'{}',onAction:args=>actions.push(args)}}};}};});
    await page.addStyleTag({path:path.join(root,'source/staysharp_medkit/ui/footer.css')});await page.addScriptTag({path:script});await page.waitForSelector('#grz-medkit-footer-button');assert.strictEqual(await page.locator('.Footer_controls > :first-child').getAttribute('id'),'grz-medkit-footer-host');await page.locator('#grz-medkit-footer-button').click();assert.strictEqual((await page.evaluate(()=>actions))[0].action,'open');
    await page.setContent(fs.readFileSync(path.join(root,'source/staysharp_medkit/ui/settings.html'),'utf8').replace(/<link[^>]+>|<script[^>]+><\/script>/g,''));
    await page.evaluate(()=>{window.actions=[];window.state={hotkeys:{toggle_mod:['Ctrl','Alt','M'],toggle_voice:['Ctrl','Alt','V']},capturing:'toggle_mod',preview:['Ctrl','Alt','Shift','M'],viewport:{width:1920,height:1080,scale:1}};window.model={state:JSON.stringify(state),onAction:args=>actions.push(args)};window.isDomBuilt=true;window.engine={whenReady:Promise.resolve(),on(){},off(){}};window.viewEnv={addDataChangedCallback(){return 1;},removeDataChangedCallback(){},resizeViewPx(){}};});
    await page.addStyleTag({path:path.join(root,'source/staysharp_medkit/ui/settings.css')});await page.addScriptTag({path:settingsScript});await page.waitForSelector('#grz-medkit-settings-mod');await page.evaluate(()=>Promise.resolve());assert.strictEqual(await page.locator('#grz-medkit-settings-mod').textContent(),'Ctrl + Alt + Shift + M');const dimensions=await page.locator('#grz-medkit-settings').boundingBox();assert.strictEqual(dimensions.width,360);assert.strictEqual(dimensions.height,230);await page.locator('#grz-medkit-settings-mod').focus();await page.keyboard.press('Space');assert.deepStrictEqual(await page.evaluate(()=>actions),[]);await page.locator('#grz-medkit-settings-cancel').click();assert.deepStrictEqual(await page.evaluate(()=>actions),[{action:'cancel_capture'}]);if(process.env.GRZ_MEDKIT_FOOTER_SCREENSHOT)await page.screenshot({path:process.env.GRZ_MEDKIT_FOOTER_SCREENSHOT});assert.deepStrictEqual(errors,[]);console.log('PASS: real-browser native footer icon and 360x230 Settings layout.');
  }finally{await browser.close();}
}
(async()=>{await nodeContracts();if(process.env.GRZ_MEDKIT_BROWSER_TEST==='1')await browserContracts();})().catch(error=>{console.error(error);process.exitCode=1;});
