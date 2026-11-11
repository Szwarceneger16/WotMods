/* Map previews and the sorting switch keep their decoration out of layout. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const source=()=>fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
function sourceFunction(text,name){const start=text.indexOf('    function '+name+'('),line=text.indexOf('\n',start);
  const end=text.slice(start,line).endsWith('}')?line:text.indexOf('\n    }\n',start)+7;
  assert(start>=0&&end>start,'Exercise shipped '+name);return text.slice(start,end);}
function assertMapPreviewSource(){
  class Node{constructor(){this.style={};this.attributes={};this.nodeType=1;}
    setAttribute(key,value){this.attributes[key]=String(value);}getAttribute(key){return this.attributes[key]||null;}
    hasAttribute(key){return Object.prototype.hasOwnProperty.call(this.attributes,key);}removeAttribute(key){delete this.attributes[key];}}
  const root=new Node(),target=new Node(),preview=new Node(),image=new Node();
  let bounds={left:100,top:50,width:700,height:730},anchor={left:120,top:110,width:54,height:32};
  root.contains=node=>node===target;root.getBoundingClientRect=()=>bounds;
  target.getBoundingClientRect=()=>({...anchor,right:anchor.left+anchor.width,bottom:anchor.top+anchor.height});
  target.setAttribute('data-ss-map-preview','img://gui/maps/icons/map/synthetic.png');target.setAttribute('aria-label','Synthetic map');
  preview.id='ss-map-preview';
  const state={group:'maps',nativeScale:1,destroyed:false},context={state,root,mapPreview:preview,mapPreviewImage:image,mapPreviewTarget:null,
    hideHelp(){},t:(key,args)=>key+': '+args[0]};
  vm.createContext(context);const text=source();
  vm.runInContext(['hideMapPreview','mapPreviewAncestor','showMapPreview','hoverMapPreview','leaveMapPreview','mapPreviewKey'].map(name=>sourceFunction(text,name)).join('\n'),context);
  context.showMapPreview(target);assert.strictEqual(preview.style.width,'216px');assert.strictEqual(preview.style.height,'128px');
  assert.strictEqual(preview.style.display,'block');assert.strictEqual(target.getAttribute('aria-expanded'),'true');
  assert.strictEqual(image.style.backgroundImage,'url("img://gui/maps/icons/map/synthetic.png")');
  context.leaveMapPreview({relatedTarget:new Node()});assert.strictEqual(preview.style.display,'none');
  assert.strictEqual(target.getAttribute('aria-expanded'),'false');assert.strictEqual(target.getAttribute('aria-describedby'),null);
  state.nativeScale=2;bounds={left:40,top:30,width:1100,height:1460};anchor={left:1060,top:1400,width:84,height:52};
  context.showMapPreview(target);assert.strictEqual(preview.style.width,'336px');assert.strictEqual(preview.style.height,'208px');
  assert(parseFloat(preview.style.left)>=16&&parseFloat(preview.style.left)+336<=bounds.width-16);
  assert(parseFloat(preview.style.top)>=16&&parseFloat(preview.style.top)+208<=bounds.height-16);
  let consumed=0;context.mapPreviewKey({key:'Escape',preventDefault(){consumed++;},stopPropagation(){consumed++;}});
  assert.strictEqual(consumed,2);assert.strictEqual(preview.style.display,'none');
  for(const blocked of ['dialog','resize','dragging','destroyed']){state[blocked]=true;context.showMapPreview(target);
    assert.strictEqual(preview.style.display,'none',blocked+' retires the preview');state[blocked]=false;}
  state.group='vehicles';context.showMapPreview(target);assert.strictEqual(preview.style.display,'none');
  assert(text.includes("nodes.scroll.removeEventListener('scroll', hideMapPreview)"));
  assert(text.includes("root.removeEventListener('mouseover', hoverMapPreview)"));
}
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let count=6;function step(){if(--count)requestAnimationFrame(step);else resolve();}requestAnimationFrame(step);}));
module.exports=async({browser,nativeHost,check})=>{
  require('./ui-map-preview-quality.cjs')();check('Actual-source high-resolution and minimap previews preserve safe local fallback and geometry',true);
  assertMapPreviewSource();check('Actual-source map preview scales fourfold, stays bounded and retires on leave/Escape/blocked state',true);
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:2400*scale,height:1400*scale},viewport:{width:2400*scale,height:1400*scale,scale}});
    try{
      await page.evaluate(scale=>{const payload=JSON.parse(model.payload);payload.account_key='synthetic-map-preview-'+scale;
        payload.window_size=[1800,1100];payload.localization={language:'en',messages:{}};
        payload.scopes.launch.maps[0].visual={kind:'map',src:'img://gui/maps/icons/map/synthetic.png',alt:'Synthetic map'};
        payload.scopes.launch.ordering.vehicles={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},scale);
      await page.locator('#ss-group-maps').click();await frames(page);
      const thumb=page.locator('.ss-group-thumb[data-ss-map-preview]').first(),tooltip=page.locator('#ss-map-preview');
      await thumb.evaluate(node=>{window.__mapPreviewProbe=node;});
      const before=await thumb.locator('xpath=..').boundingBox();await thumb.hover();await frames(page);
      const tile=await thumb.boundingBox(),popup=await tooltip.boundingBox(),panel=await page.locator('#grz-session-stats').boundingBox();
      check('Hover shows an adjacent fourfold map image inside the panel at'+scale*100+'%',
        !!popup&&Math.abs(popup.width-tile.width*4)<=1&&Math.abs(popup.height-tile.height*4)<=1&&
        popup.x>=panel.x&&popup.y>=panel.y&&popup.x+popup.width<=panel.x+panel.width&&popup.y+popup.height<=panel.y+panel.height&&
        await tooltip.evaluate(node=>getComputedStyle(node).position==='absolute'&&getComputedStyle(node).pointerEvents==='none'));
      check('Showing map decoration does not change the thumbnail row dimensions at'+scale*100+'%',
        JSON.stringify(before)===JSON.stringify(await thumb.locator('xpath=..').boundingBox()));
      await page.locator('#ss-titlebar h1').hover();check('Leaving the miniature immediately hides its preview at'+scale*100+'%',!await tooltip.isVisible());
      await thumb.focus();check('Keyboard focus can inspect the same map at'+scale*100+'%',await tooltip.isVisible());
      await thumb.press('Escape');check('Escape closes the map preview at'+scale*100+'%',!await tooltip.isVisible());
      await thumb.hover();await page.locator('#ss-scroll').evaluate(node=>node.dispatchEvent(new Event('scroll')));
      check('Scrolling retires a map preview at'+scale*100+'%',!await tooltip.isVisible());
      await page.locator('#ss-group-vehicles').click();await frames(page);
      const toggle=page.locator('#ss-sort-off');
      check('Wide sorting exposes an accessible painted switch at'+scale*100+'%',await toggle.isVisible()&&
        await toggle.getAttribute('role')==='switch'&&await toggle.getAttribute('aria-checked')==='false'&&
        await toggle.locator('.ss-sort-switch-track').evaluate(node=>getComputedStyle(node).borderRadius!=='0px'));
      check('The compact switch keeps a rounded button frame around its inset track at'+scale*100+'%',
        await toggle.evaluate((node,scale)=>{const css=getComputedStyle(node),box=node.getBoundingClientRect();
          const track=node.querySelector('.ss-sort-switch-track').getBoundingClientRect();
          return Math.abs(box.width-46*scale)<=1&&Math.abs(track.width-34*scale)<=1&&
            box.width-track.width>=11*scale&&box.height-track.height>=11*scale&&
            parseFloat(css.borderRadius)>=14*scale&&css.backgroundImage!=='none'&&parseFloat(css.borderTopWidth)>=scale;},scale));
      const start=await toggle.locator('.ss-sort-switch-thumb').boundingBox();await toggle.focus();await toggle.press('Space');
      await page.evaluate(()=>{const command=__grzCommands.filter(item=>item.action==='sort').pop();const payload=JSON.parse(model.payload);
        payload.scopes[command.scope].ordering[command.group]={metric:command.metric,statistic:command.statistic,direction:command.direction,chronology:command.chronology};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);await page.waitForTimeout(160);
      const end=await toggle.locator('.ss-sort-switch-thumb').boundingBox();
      check('Space enables metric sorting and moves the switch thumb without resizing the control at'+scale*100+'%',
        await toggle.getAttribute('aria-checked')==='true'&&end.x>start.x+14*scale&&Math.abs(end.width-start.width)<=1);
      await page.evaluate(()=>GRZSessionStats.destroy());
      await page.evaluate(()=>{document.getElementById('grz-session-stats').appendChild(__mapPreviewProbe);
        __mapPreviewProbe.dispatchEvent(new MouseEvent('mouseover',{bubbles:true}));});
      check('Destroyed map input cannot reopen the tooltip at'+scale*100+'%',!await tooltip.isVisible());
    }finally{await page.close();}
  }
};
module.exports.assertMapPreviewSource=assertMapPreviewSource;
if(require.main===module){assertMapPreviewSource();console.log('Actual-source map hover, bounds, fourfold image and lifecycle checks pass.');}
