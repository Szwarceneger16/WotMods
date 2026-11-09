/* A wide floating window must use its title row in every shipped language. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;
  function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async ({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const {width,scale,wide} of [{width:1200,scale:1,wide:true},{width:1600,scale:1,wide:true},
    {width:1200,scale:2,wide:true},{width:700,scale:1},{width:470,scale:1}]) {
    const game={width:3400,height:2200,scale};
    const page=await nativeHost(browser,{initialViewport:{width:game.width,height:game.height},viewport:game});
    try {
      for(const [language,messages] of Object.entries(languages)) {
        await page.evaluate(({width,language,messages})=>{
          const payload=JSON.parse(model.payload);payload.window_size=[width,900];
          payload.account_key='synthetic-header-'+language;
          payload.localization={language,selected:language,messages};
          payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));
          payload.scopes.timeline.time_points=[];
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{width,language,messages});await frames(page);
        const audit=await page.evaluate(scale=>{
          const box=node=>{const r=node.getBoundingClientRect();return {left:r.left/scale,right:r.right/scale,
            top:r.top/scale,bottom:r.bottom/scale,width:r.width/scale,height:r.height/scale};};
          const root=box(document.getElementById('grz-session-stats')),bar=box(document.getElementById('ss-titlebar'));
          const selectors=['.ss-title-identity','#ss-time-point-controls','.ss-background-control','.ss-language-row','#ss-maximize','#ss-close'];
          const items=selectors.map(selector=>({selector,...box(document.querySelector(selector))}));
          const overflow=[],clipped=[];
          for(const node of document.querySelectorAll('#ss-titlebar *')) {
            const r=box(node);if(!r.width || !r.height || node.closest('.ss-select-options'))continue;
            if(r.left<root.left-1 || r.right>root.right+1 || r.top<bar.top-1 || r.bottom>bar.bottom+1)overflow.push(node.id || node.className);
          }
          for(const node of document.querySelectorAll('.ss-titlebar h1,.ss-game-mode,#ss-time-point .ss-control-label,.ss-background-caption,.ss-language-caption,#ss-language .ss-select-trigger .ss-control-label')) {
            const range=document.createRange();range.selectNodeContents(node);const text=range.getBoundingClientRect(),r=node.getBoundingClientRect();
            if(text.width>r.width+1 || text.height>r.height+1)clipped.push({text:node.textContent,width:text.width/scale,available:r.width/scale});
          }
          return {root,bar,items,overflow,clipped};
        },scale);
        const label=language+' at'+width+'px/'+(scale*100)+'%';
        check('Title controls remain visible inside the floating header: '+label+': '+JSON.stringify(audit.overflow),
          audit.items.every(item=>item.width>0 && item.height>0) && audit.overflow.length===0);
        const windowInk=await page.evaluate(()=>{
          function bounds(frame,pseudo) {
            const style=getComputedStyle(frame,pseudo);if(style.display==='none')return null;
            const box=frame.getBoundingClientRect(),width=parseFloat(style.width),height=parseFloat(style.height),
              left=box.left+parseFloat(style.left),top=box.top+parseFloat(style.top),
              origin=style.transformOrigin.split(' ').map(parseFloat),matrix=new DOMMatrix(style.transform==='none'?undefined:style.transform);
            const points=[[0,0],[width,0],[width,height],[0,height]].map(([x,y])=>{
              const point=new DOMPoint(x-origin[0],y-origin[1]).matrixTransform(matrix);
              return {x:left+origin[0]+point.x,y:top+origin[1]+point.y};
            });
            return {left:Math.min(...points.map(p=>p.x)),right:Math.max(...points.map(p=>p.x)),
              top:Math.min(...points.map(p=>p.y)),bottom:Math.max(...points.map(p=>p.y)),
              color:style.backgroundColor,strokeColor:style.borderTopColor,stroke:parseFloat(style.borderTopWidth)};
          }
          function center(pieces) {return {x:(Math.min(...pieces.map(p=>p.left))+Math.max(...pieces.map(p=>p.right)))/2,
            y:(Math.min(...pieces.map(p=>p.top))+Math.max(...pieces.map(p=>p.bottom)))/2};}
          function buttonCenter(button) {const r=button.getBoundingClientRect();return {x:(r.left+r.right)/2,y:(r.top+r.bottom)/2};}
          const close=document.getElementById('ss-close'),label=close.querySelector('.ss-control-label'),toggle=document.getElementById('ss-maximize'),
            symbol=toggle.querySelector('.ss-window-toggle-symbol'),pressed=toggle.getAttribute('aria-pressed'),states=[];
          const closePieces=[':before',':after'].map(pseudo=>bounds(label,pseudo));
          for(const state of ['false','true']) {toggle.setAttribute('aria-pressed',state);
            const pieces=[':before',':after'].map(pseudo=>bounds(symbol,pseudo)).filter(Boolean);
            states.push({state,pieces,center:center(pieces),button:buttonCenter(toggle)});}
          toggle.setAttribute('aria-pressed',pressed);
          return {close:{pieces:closePieces,center:center(closePieces),button:buttonCenter(close),
            font:parseFloat(getComputedStyle(label).fontSize),color:getComputedStyle(close).color,decorative:label.getAttribute('aria-hidden')==='true'},
            states,toggleColor:getComputedStyle(toggle).color};
        });
        const centered=ink=>Math.abs(ink.center.x-ink.button.x)<=0.5 && Math.abs(ink.center.y-ink.button.y)<=0.5;
        check('Close, maximize and restore ink share the centered window-control row: '+label+': '+JSON.stringify(windowInk),
          windowInk.close.decorative && windowInk.close.font===0 && centered(windowInk.close) && windowInk.close.pieces.every(piece=>piece.color===windowInk.close.color) &&
          windowInk.states.every(state=>centered(state) && Math.abs(state.center.y-windowInk.close.center.y)<=0.5 &&
            state.pieces.length===(state.state==='true'?2:1) && state.pieces.every(piece=>piece.stroke>=scale && piece.strokeColor===windowInk.toggleColor)));
        if(wide) {
          check('Wide title, point name, slider, language and window controls share one row: '+label+': '+JSON.stringify(audit.items),
            Math.min(...audit.items.map(item=>item.bottom))-Math.max(...audit.items.map(item=>item.top))>=15 && audit.bar.height<=51);
          check('Wide localized header text remains readable without clipping: '+label+': '+JSON.stringify(audit.clipped),audit.clipped.length===0);
        }
        await page.locator('#ss-group-battles').click();await frames(page);
        if(language==='en') {
          const beforeArrow=await page.locator('#ss-scroll').evaluate(node=>node.scrollTop);
          await page.locator('#ss-scroll').evaluate((node,scale)=>{
            node.scrollTop=Math.min(node.scrollHeight-node.clientHeight,240*scale);node.dispatchEvent(new Event('scroll'));
          },scale);await frames(page);
          check('Top chevron paint is measured on its visible scrolled action: '+label,
            await page.locator('#ss-scroll').evaluate(node=>node.scrollTop)>60*scale && await page.locator('#ss-scroll-top').isVisible());
          const arrow=await page.locator('.ss-scroll-top-icon').evaluate(icon=>({
            image:getComputedStyle(icon).backgroundImage,
            color:getComputedStyle(icon).color,
            chevrons:[':before',':after'].map(pseudo=>{const style=getComputedStyle(icon,pseudo);
              return {content:style.content,display:style.display,width:parseFloat(style.width),height:parseFloat(style.height),
                top:parseFloat(style.top),left:style.borderLeftColor,topColor:style.borderTopColor,
                stroke:parseFloat(style.borderTopWidth),transform:style.transform};})
          }));
          check('Both Top chevrons paint their orange strokes rather than a gray bitmap: '+label+': '+JSON.stringify(arrow),
            arrow.image==='none' && arrow.color==='rgb(231, 162, 59)' &&
            arrow.chevrons.every(piece=>piece.content==='""' && piece.display==='block' && piece.width>=12*scale &&
              piece.height>=12*scale && piece.stroke>=3*scale && piece.left===arrow.color && piece.topColor===arrow.color && piece.transform!=='none') &&
            arrow.chevrons[1].top-arrow.chevrons[0].top===10*scale);
          await page.locator('#ss-scroll').evaluate((node,offset)=>{node.scrollTop=offset;node.dispatchEvent(new Event('scroll'));},beforeArrow);
          await frames(page);
          check('Measuring Top paint restores the titlebar fixture offset: '+label,
            Math.abs(await page.locator('#ss-scroll').evaluate(node=>node.scrollTop)-beforeArrow)<=1);
        }
        const buttons=page.locator('.ss-more-button');
        for(let index=0;index<Math.min(2,await buttons.count());index++) {
          const button=buttons.nth(index);
          check('Collapsed battle details say More in '+label,await button.getAttribute('aria-expanded')==='false' && await button.textContent()===messages['more.button']);
          await button.click();await frames(page);
          check('Expanded battle details say Less in '+label,await button.getAttribute('aria-expanded')==='true' && await button.textContent()===messages['more.less']);
        }
        await buttons.first().click();await frames(page);
        check('Closing one localized detail panel restores More and preserves the other: '+label,
          await buttons.first().textContent()===messages['more.button'] && await buttons.nth(1).getAttribute('aria-expanded')==='true' &&
          await buttons.nth(1).textContent()===messages['more.less']);
      }
    } finally {await page.close();}
  }
};
