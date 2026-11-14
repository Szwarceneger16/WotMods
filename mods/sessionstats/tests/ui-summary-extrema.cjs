/* Summary source actions use real service pages even when Battles is already open. */
const assert=require('assert'),path=require('path'),{spawnSync}=require('child_process');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let count=6;function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
function nativeFixtures(){
  const root=path.resolve(__dirname,'..');
  const output=spawnSync(process.env.GRZ_PYTHON3||'python3',['-c',`
import copy, json, tempfile
from test_core import Clock, EXPECTED, result
from grz_session_stats.core import StatsService
with tempfile.TemporaryDirectory(prefix='grz-summary-navigation-') as directory:
    clock = Clock(100)
    service = StatsService(directory, 'SYNTHETIC:summary', 'fixture-launch', EXPECTED, clock, timeline_enabled=True)
    clock.value = 2000
    rows = {}
    for index in range(125):
        row = result('summary-row-{0:03d}'.format(index), 110 + index, ended_at=500 + index,
                     xp_received=12345 if index == 0 else 0 if index == 121 else 200 + index,
                     vehicle_name='Synthetic vehicle', map_name='Synthetic map')
        if index >= 122:
            row.update(outcome=None, complete=False, xp_base=None, xp_received=None)
        row.update(_manual_id=service._state['current_manual_id'], _launch_id=service.launch_id,
                   _updated_at=1000, _result_seen=True, revision=1)
        rows[row['arena_id']] = row
    service._state['battles'] = rows
    service._rebuild_indexes()
    def snapshot():
        payload = service.snapshot()
        payload['scopes']['timeline'] = service.timeline_snapshot()
        return copy.deepcopy(payload)
    initial = snapshot()
    replies = {}
    for statistic in ('max', 'min'):
        scope = service.timeline_snapshot()
        identifier = scope['extrema_battles']['xp_received'][statistic]['id']
        assert service.select_battle('timeline', identifier, scope['period_id'], 'fixture-' + statistic)
        replies[statistic] = snapshot()
    assert service.record_result(result('summary-row-060', 170, damage=1001, reconcile=True))
    assert service.set_page('timeline', 'battles', 0, initial['scopes']['timeline']['period_id'])
    revised = snapshot()
    scope = service.timeline_snapshot()
    identifier = scope['extrema_battles']['xp_received']['max']['id']
    assert service.select_battle('timeline', identifier, scope['period_id'], 'fixture-revised')
    print(json.dumps({'initial': initial, 'replies': replies, 'revised': revised, 'revisedMax': snapshot()}))
`],{cwd:root,encoding:'utf8',maxBuffer:8*1024*1024,env:{...process.env,PYTHONPATH:[path.join(root,'src'),__dirname].join(path.delimiter)}});
  assert.strictEqual(output.status,0,'Real service summary navigation fixture: '+(output.error||output.stderr));
  return JSON.parse(output.stdout);
}
module.exports=async({browser,nativeHost,check})=>{
  const fixtures=nativeFixtures(),page=await nativeHost(browser,{initialViewport:{width:1800,height:1400},viewport:{width:1800,height:1400,scale:1}});
  const selector=statistic=>'#ss-summary .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="'+statistic+'"]';
  try{
    async function publish(payload){
      await page.evaluate(payload=>{
        const original=JSON.parse(model.payload),fresh=JSON.parse(JSON.stringify(payload));
        fresh.window_size=[1200,1050];fresh.viewport=original.viewport;
        model.payload=JSON.stringify(fresh);GRZSessionStats.update(fresh);
      },payload);await frames(page);
    }
    await publish(fixtures.initial);
    await page.locator('#ss-scope-manual').click();await page.locator('#ss-group-battles').click();await frames(page);
    const scope=fixtures.initial.scopes.timeline;
    check('Summary navigation fixture uses real Beginning-to-Now history and an off-page source',
      scope.from_point===''&&scope.to_point===''&&scope.pagination.battles.pages===4&&
      fixtures.replies.max.scopes.timeline.pagination.battles.page===3&&
      !scope.battles.some(row=>row.id===scope.extrema_battles.xp_received.max.id)&&
      await page.locator('#ss-group-battles').getAttribute('aria-pressed')==='true');
    async function select(statistic,reply){
      const before=await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select').length);
      await page.locator(selector(statistic)).click();
      const commands=await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select'));
      const command=commands[commands.length-1];
      const selected=JSON.parse(JSON.stringify(reply)),destination=selected.scopes.timeline;
      check('Summary '+statistic+' sends its exact real source and current Timeline context',
        commands.length===before+1&&command.id===destination.battle_focus.id&&command.scope==='timeline'&&command.period_id===destination.period_id&&
        command.account_key===selected.account_key);
      destination.battle_focus.request_id=command.request_id;
      await publish(selected);
      check('Summary '+statistic+' mounts and marks the selected native page while Battles stays selected',
        await page.locator('#ss-group-battles').getAttribute('aria-pressed')==='true'&&
        await page.locator('#ss-groups .ss-battle-target[data-group-id="'+command.id+'"]').count()===1&&
        await page.locator('#ss-groups .ss-continuous-page[data-page-index="'+destination.pagination.battles.page+'"]').count()===1);
      const visible=await page.locator('#ss-groups .ss-battle-target').evaluate(card=>{const box=card.getBoundingClientRect(),viewport=document.getElementById('ss-scroll').getBoundingClientRect(),filter=document.getElementById('ss-filter-panel').getBoundingClientRect();return box.top>=viewport.top-1&&box.top<viewport.bottom&&box.bottom>Math.max(viewport.top,filter.bottom);});
      check('Summary '+statistic+' scrolls its actual selected result into the current viewport',visible);
      const numeric=await page.locator('#ss-groups .ss-battle-target [data-ss-metric="xp_received"] .ss-battle-value').textContent();
      check('Selected summary '+statistic+' retains its original numeric result, including zero',
        numeric.replace(/\s/g,'')===String(destination.extrema_battles.xp_received[statistic].value));
      return command;
    }
    await select('max',fixtures.replies.max);
    await select('min',fixtures.replies.min);
    await publish(fixtures.initial);await page.locator('#ss-group-maps').click();await frames(page);
    const retained=await page.evaluate(()=>{
      const node=document.querySelector('#ss-summary .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="max"]'),payload=JSON.parse(model.payload);
      payload.scopes.timeline.maps[0].battle_list={page:0,pages:1,total:1,page_size:10,items:[{id:'synthetic-history-only',name:'Synthetic history'}]};
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
      return document.contains(node)&&document.querySelector('#ss-summary .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="max"]')===node;
    });
    check('Timeline history-only refresh retains its live summary source action',retained);
    await select('max',fixtures.replies.max);
    // A full results revision replaces summary actions. Retired callbacks stay
    // inert, while the newly painted source must navigate immediately.
    await page.evaluate(()=>{window.__retiredSummarySource=document.querySelector('#ss-summary .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="max"]').onclick;});
    await publish(fixtures.revised);
    const retired=await page.evaluate(()=>{const before=__grzCommands.filter(row=>row.action==='battle_select').length;__retiredSummarySource();return __grzCommands.filter(row=>row.action==='battle_select').length===before;});
    check('A retired summary action cannot navigate a later result revision',retired);
    await select('max',fixtures.revisedMax);
    // A delayed acknowledgement from an earlier account/range must not mount
    // its target after the user's context has changed.
    for(const changed of ['account','range']){
      await publish(fixtures.initial);
      await page.locator(selector('max')).click();
      const request=await page.evaluate(()=>__grzCommands.filter(row=>row.action==='battle_select').pop());
      const replacement=JSON.parse(JSON.stringify(fixtures.initial));
      if(changed==='account')replacement.account_key='SYNTHETIC:replacement';
      else{replacement.scopes.timeline.period_id='timeline:other-range';replacement.scopes.timeline.from_point='other-range';}
      await publish(replacement);
      replacement.scopes.timeline.battle_focus={id:request.id,request_id:request.request_id};
      await publish(replacement);
      check('A late summary acknowledgement cannot cross '+changed+' ownership',await page.locator('#ss-groups .ss-battle-target').count()===0);
    }
  }finally{await page.close();}
};
