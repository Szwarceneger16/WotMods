/* Native texture negotiation can lag behind the first model update. */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../source/staysharp_medkit/ui/settings.js'), 'utf8');
function fixture(options = {}) {
    const nodes = {}, events = {}, actions = [], requests = [], timers = new Map();
    let nextTimer = 0, nativeReady = false, actual = {width:256, height:256};
    const state = {viewport:options.viewport || {width:1920, height:1080, scale:1}, hotkeys:{}, labels:{}};
    function node(id) { return nodes[id] || (nodes[id] = {style:{}, setAttribute(){}, textContent:''}); }
    const document = {documentElement:node('html'), body:node('body'), getElementById:node, addEventListener(){}, removeEventListener(){}};
    const model = {state:JSON.stringify(state), onAction(arg){ actions.push(arg); }};
    const context = {document, model, isDomBuilt:true,
        engine:{whenReady:Promise.resolve(), on(name, fn){ (events[name] || (events[name] = new Set())).add(fn); }, off(name, fn){ if(events[name]) events[name].delete(fn); }},
        viewEnv:{addDataChangedCallback(){return 1;}, removeDataChangedCallback(){},
            getViewSizePx(){ if(options.badMeasurement) throw Error('measurement unavailable'); return actual; },
            resizeViewPx(width, height){ requests.push([width,height]); if(options.textureEvent) emit('self.onTextureReady'); if(options.throwBeforeReady && !nativeReady) throw Error('texture not loaded'); if(nativeReady) actual = {width,height}; }},
        setTimeout(fn){ const id = ++nextTimer; timers.set(id,fn); return id; }, clearTimeout(id){timers.delete(id);}, addEventListener(){}, removeEventListener(){}
    };
    context.window = context;
    vm.createContext(context); vm.runInContext(source, context);
    function emit(name){ for(const fn of [...(events[name] || [])]) fn(); }
    return {context, nodes, actions, requests, events, timers, state, model,
        ready(){ nativeReady=true; }, emit,
        tick(){ const pending=[...timers.values()]; timers.clear(); pending.forEach(fn=>fn()); },
        patch(values){Object.assign(state,values); model.state=JSON.stringify(state); emit('viewEnv.onDataChanged');},
        actual(){return actual;}
    };
}
(async()=>{
    for(const options of [{}, {throwBeforeReady:true}, {badMeasurement:true}]) {
        const f=fixture(options); await Promise.resolve();
        assert.deepStrictEqual(f.requests, [[360,232]]);
        assert.strictEqual(f.timers.size,1,'An ignored or failed initial resize must be checked again');
        assert.strictEqual(f.actions[0].action,'layout');
        assert.strictEqual(f.actions[0].width,360); assert.strictEqual(f.actions[0].height,232);
        f.ready(); f.tick();
        assert.deepStrictEqual(f.actual(), {width:360,height:232}, 'The 256-pixel initial surface must expand');
        for(let i=0;i<8;i++) f.tick();
        assert.strictEqual(f.timers.size,0,'Verification retries are bounded even if measurement fails');
        f.patch({status:'Shortcut saved.'});
        assert.deepStrictEqual(f.actual(),{width:360,height:232},'Saving must not move or resize the panel');
        const previous=f.requests.length;
        f.patch({status:'Shortcut saved.'});
        assert.strictEqual(f.requests.length,previous+(options.badMeasurement?1:0),'A confirmed surface is not resized again');
        f.patch({viewport:{width:1920,height:1080,scale:1.5}});
        assert.deepStrictEqual(f.actual(), {width:540,height:348});
        f.patch({status:'',capturing:null,error:''});assert.deepStrictEqual(f.actual(),{width:540,height:348},'Idle panel removes the empty feedback area');
        const beforeCapture=f.requests.length;
        f.patch({capturing:'toggle_mod'});assert.deepStrictEqual(f.actual(),{width:540,height:348},'Capture keeps the panel and cancel control stationary');
        f.patch({capturing:null,error:'Could not save'});assert.deepStrictEqual(f.actual(),{width:540,height:348},'Errors use the existing description area without a layout jump');
        if(!options.badMeasurement) assert.strictEqual(f.requests.length,beforeCapture,'Capture and error transitions cannot request another native resize');
        assert.strictEqual(f.nodes['grz-medkit-settings-hint'].style.display,'none');
        assert.strictEqual(f.nodes['grz-medkit-settings-feedback'].style.display,'block');
        f.context.GRZStaySharpSettings.destroy();
        assert.strictEqual(f.timers.size,0); f.tick();
        for(const event of ['self.onLoaded','self.onTextureReady','clientResized','self.onScaleUpdated']) assert.strictEqual(f.events[event].size,0,'Native readiness listener must be released');
    }
    for(const record of JSON.parse(process.env.MEDKIT_LAYOUT_CASES || '[]')) {
        const f=fixture({viewport:record.viewport}); await Promise.resolve();
        assert.deepStrictEqual(f.requests[0],record.size,'DOM/native fit disagreement: '+JSON.stringify(record.viewport));
        assert.strictEqual(f.nodes['grz-medkit-settings'].style.width,record.size[0]+'px');
        assert.strictEqual(f.nodes['grz-medkit-settings'].style.height,record.size[1]+'px');
        assert.strictEqual(f.nodes.body.style.width,record.size[0]+'px');
        assert.strictEqual(f.nodes.body.style.height,record.size[1]+'px');
        const effective=Number(f.nodes.html.style.fontSize.replace('px',''));
        assert(effective>0 && effective<=record.viewport.scale);
        f.context.GRZStaySharpSettings.destroy();
    }
    const live=fixture(); await Promise.resolve(); live.ready();
    let client={width:320,height:200}, nativeScale=2;
    live.context.viewEnv.getClientSizePx=()=>client; live.context.viewEnv.getScale=()=>nativeScale;
    live.emit('clientResized'); assert.deepStrictEqual(live.actual(),{width:211,height:136});
    client={width:600,height:900}; live.emit('clientResized');
    assert.deepStrictEqual(live.actual(),{width:536,height:345},'A second client resize must not be deduplicated');
    nativeScale=1.25; live.emit('self.onScaleUpdated');
    assert.deepStrictEqual(live.actual(),{width:450,height:290});
    nativeScale=1.5; live.emit('self.onScaleUpdated');
    assert.deepStrictEqual(live.actual(),{width:540,height:348},'A second GUI-scale change must recalculate the physical surface');
    live.patch({viewport:{width:600,height:900,scale:1.5}});
    assert.deepStrictEqual(live.actual(),{width:540,height:348},'Delayed model geometry must converge to the same native bounds');
    live.context.GRZStaySharpSettings.destroy();
    const recurrent=fixture({textureEvent:true}); await Promise.resolve();
    for(let i=0;i<20;i++) { recurrent.tick(); recurrent.emit('self.onTextureReady'); }
    assert(recurrent.requests.length <= 8, 'Texture-ready events caused by our resize cannot restart the retry budget');
    assert.strictEqual(recurrent.timers.size,0); recurrent.context.GRZStaySharpSettings.destroy();
    const limited=fixture(); await Promise.resolve();
    for(let i=0;i<10;i++) limited.tick();
    assert.strictEqual(limited.requests.length,7,'An unavailable renderer cannot cause an unbounded retry loop');
    limited.ready(); limited.emit('self.onLoaded');
    assert.deepStrictEqual(limited.actual(),{width:360,height:232},'Native loaded notification retries a previously exhausted resize');
    limited.context.GRZStaySharpSettings.destroy();
    console.log('PASS: native 256px surface, delayed/throwing resize, broken measurement, readiness retry, GUI scaling, responsive Python/DOM parity, successive resize/scale events and bounded lifecycle cleanup.');
})().catch(error=>{console.error(error);process.exitCode=1;});
