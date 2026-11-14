/* Exercise shipped sorting presentation without a browser or private records. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
function run(){
  const source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
  function actual(name){const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }\n',start)+7;
    assert(start>=0&&end>start,'Exercise shipped '+name);return source.slice(start,end);}
  class Node{
    constructor(text=''){this.textContent=text;this.attributes={};this.children=[];this.className='';this.style={};this.selectors={};
      const classes=new Set();this.classList={add:name=>classes.add(name),contains:name=>classes.has(name)};}
    setAttribute(name,value){this.attributes[name]=String(value);}getAttribute(name){return this.attributes[name]||null;}
    querySelectorAll(selector){return this.selectors[selector]||[];}querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
    appendChild(node){node.parentNode=this;this.children.push(node);return node;}
  }
  const messages={'metric.wn8':'WN8','metric.win_rate':'Win rate','metric.battles':'Battles','sort.credits_net_base':'Credits income (net, base)','sort.credits_net_received':'Credits income (net, received)','sort.credits_income_base':'Credits income (base)','sort.credits_income_received':'Credits income (received)','sort.credits_costs':'Credits costs',
    'xp.base':'Base XP','xp.received':'Received XP','sort.avg':'Avg','metric.min':'Min','metric.max':'Max',
    'sort.sum':'All','sort.value_total':'Total {0}: {1}',
    'sort.metric_stat':'{0} {1}','sort.active_value':'Sorting value: {0}','sort.value_per_battle':'{0} {1} / battle: {2}'};
  const context={hasNumber:value=>typeof value==='number'&&Number.isFinite(value),
    append:(parent,node)=>parent.appendChild(node),element:(tag,cls,text)=>{const node=new Node(text);node.className=cls;return node;},
    number:value=>value===null?'—':String(value),explainCoverage:node=>node,
    signed:value=>value===null?'—':String(value),t:(key,args=[])=>messages[key].replace(/\{(\d+)\}/g,(_,index)=>args[index])};
  vm.createContext(context);vm.runInContext(['series','coverage','observedTotal','canonicalMetric','creditMetric','netCreditMetric','metricSeries','groupSortValue','cardSortValue','sortMetricLabel','markSortValue','highlightCardSort'].map(actual).join('\n'),context);
  function fixture(){
    const card=new Node(),meta=new Node(),kpis=[new Node(),new Node(),new Node()],rows=[new Node(),new Node(),new Node()],head=new Node(),money=new Node();
    for(const row of rows.concat([head,money]))row.children=[new Node(),new Node(),new Node(),new Node()];
    card.selectors={'.ss-group-kpi':kpis,'.ss-metric-row':rows,'.ss-metric-head':[head],'.ss-money-row':[money],'.ss-battle-measure':rows};
    ['xp_base','xp_received','battle_wn8'].forEach((metric,index)=>{
      rows[index].setAttribute('data-ss-metric',metric);
      card.selectors['[data-ss-metric=\"'+metric+'\"]']=[rows[index]];
    });
    const credit={};
    for(const metric of ['credits_income_base','credits_income_received','credits_net_base','credits_net_received','credits_costs']){
      const cell=new Node();cell.selectors={'.ss-cell-value':[new Node()],
        '[data-ss-extreme="min"]':[new Node()],'[data-ss-extreme="max"]':[new Node()]};
      credit[metric]=cell;card.selectors['.ss-money-value[data-ss-metric="'+metric+'"]']=[cell];
    }
    return {card,meta,kpis,rows,head,money,credit};
  }
  const options={metric:'battle_wn8',statistic:'max'},item={sort_value:8834,stats:{wn8:2732,battle_wn8:{max:8834},win_rate:0}};
  assert.strictEqual(context.cardSortValue(item,options),8834);
  assert.strictEqual(context.sortMetricLabel(options,false),'Max WN8');
  assert.strictEqual(context.cardSortValue({sort_value:null,stats:{win_rate:100}},{metric:'win_rate'}),null,'An authoritative unknown cannot become a plausible win');
  assert.strictEqual(context.cardSortValue({stats:{win_rate:0}},{metric:'win_rate'}),0,'Zero win rate is known');
  let f=fixture();context.highlightCardSort(f.card,f.meta,item,options,false);
  assert.strictEqual(f.kpis[2].getAttribute('data-ss-sort-active'),'battle_wn8');
  assert.strictEqual(f.rows[2].children[3].getAttribute('data-ss-sort-active'),'battle_wn8');
  assert.strictEqual(f.head.children[3].getAttribute('data-ss-sort-active'),'battle_wn8');
  assert.strictEqual(f.rows[2].children[2].getAttribute('data-ss-sort-active'),null,'Unselected average remains ordinary');
  assert.strictEqual(f.meta.children.length,0,'WN8 reuses the headline and distribution instead of repeating metadata');
  f=fixture();context.highlightCardSort(f.card,f.meta,item,{metric:'xp_received',statistic:'min'},false);
  assert.strictEqual(f.rows[1].children[1].getAttribute('data-ss-sort-active'),'xp_received');assert.strictEqual(f.meta.children.length,0);
  f=fixture();context.highlightCardSort(f.card,f.meta,item,{metric:'battles'},false);
  assert.strictEqual(f.kpis[0].getAttribute('data-ss-sort-active'),'battles');assert.strictEqual(f.meta.children.length,0);
  for(const battle of [false,true]){
    f=fixture();context.highlightCardSort(f.card,f.meta,item,{metric:'win_rate'},battle);
    assert.strictEqual(f.kpis[1].getAttribute('data-ss-sort-active'),battle?null:'win_rate','Only aggregate cards support win-rate highlighting');
    assert.strictEqual(f.kpis[0].getAttribute('data-ss-sort-active'),null);assert.strictEqual(f.meta.children.length,0);
  }
  f=fixture();context.highlightCardSort(f.card,f.meta,{sort_value:5},{metric:'credits_net_received',statistic:'avg'},false);
  assert.strictEqual(f.meta.children.length,1,'Per-battle credit statistics have no equivalent in the aggregate finance table');
  assert.strictEqual(f.meta.children[0].textContent,'Avg Credits income (net, received) / battle: 5');
  assert.strictEqual(f.credit.credits_net_received.querySelector('.ss-cell-value').getAttribute('data-ss-sort-active'),null,'A group total must not pretend to be the sorting average');
  f=fixture();context.highlightCardSort(f.card,f.meta,{sort_value:5},{metric:'credits_net_received'},true);
  assert.strictEqual(f.credit.credits_net_received.querySelector('.ss-cell-value').getAttribute('data-ss-sort-active'),'credits_net_received');assert.strictEqual(f.meta.children.length,0);
  for(const metric of ['credits_income_base','credits_income_received','credits_net_base','credits_net_received','credits_costs']) {
    f=fixture();context.highlightCardSort(f.card,f.meta,{sort_value:5},{metric,statistic:'sum'},false);
    assert.strictEqual(f.credit[metric].querySelector('.ss-cell-value').getAttribute('data-ss-sort-active'),metric,'All credits mark the actual aggregate total');
    assert.strictEqual(f.meta.children.length,0,'An already displayed total needs no duplicate per-battle caption');
  }
  f=fixture();context.highlightCardSort(f.card,f.meta,{sort_value:5},{metric:'credits_income_received',statistic:'avg'},false);
  assert.strictEqual(f.meta.children[0].textContent,'Avg Credits income (received) / battle: 5');
  for(const statistic of ['min','avg','max'])for(const value of [1200,0,null]){
    f=fixture();context.highlightCardSort(f.card,f.meta,{sort_value:value},{metric:'credits_costs',statistic},false);
    assert.strictEqual(f.meta.children[0].textContent,messages[statistic==='avg'?'sort.avg':'metric.'+statistic]+' Credits costs / battle: '+(value===null?'—':value),
      'Cost statistics expose their positive expense magnitude, including known zero and unavailable values');
    assert.strictEqual(f.credit.credits_costs.querySelector('.ss-cell-value').getAttribute('data-ss-sort-active'),null,'A cost average must not mark the total expense cell');
  }
  f=fixture();context.highlightCardSort(f.card,f.meta,{sort_value:900},{metric:'credits_costs'},true);
  assert.strictEqual(f.credit.credits_costs.querySelector('.ss-cell-value').getAttribute('data-ss-sort-active'),'credits_costs','An individual cost uses its existing finance cell');
  f=fixture();context.highlightCardSort(f.card,f.meta,{sort_value:600,stats:{observed_battles:3,xp_base:{count:2,sum:600}}},{metric:'xp_base',statistic:'sum'},false);
  assert.strictEqual(f.meta.children[0].textContent,'Total Base XP: 600');
  assert.strictEqual(f.meta.children[0].children[0].textContent,' (2/3)');
  assert(f.rows[0].children.every(node=>!node.getAttribute('data-ss-sort-active')),'An XP total must not highlight the average distribution cell');
  assert.strictEqual(context.groupSortValue({stats:{xp_base:{count:0,sum:0}}},{metric:'xp_base',statistic:'sum'}),null,'An empty legacy sum is unknown, not zero');
  assert.strictEqual(context.groupSortValue({stats:{xp_base:{count:1,sum:0}}},{metric:'xp_base',statistic:'sum'}),0,'A received zero remains known');
  assert.strictEqual(context.groupSortValue({stats:{credits_gross:{count:1,sum:500}}},{metric:'credits_income_received',statistic:'sum'}),500,'Old gross series remains received');
  assert.strictEqual(context.groupSortValue({stats:{credits_net:{count:1,sum:50}}},{metric:'credits_net_received',statistic:'sum'}),50,'Old net series remains received');
  assert.strictEqual(context.groupSortValue({stats:{credits_gross:{count:1,sum:500}}},{metric:'credits_income_base',statistic:'sum'}),undefined,'Old received income cannot invent base earnings');
  assert.strictEqual(context.groupSortValue({stats:{credits_income_base:{count:1,sum:0}}},{metric:'credits_income_base',statistic:'sum'}),0,'Known zero base earnings stay available');
  f=fixture();context.highlightCardSort(f.card,f.meta,item,{metric:'battle_wn8'},true);
  assert.strictEqual(f.rows[2].getAttribute('data-ss-sort-active'),'battle_wn8');assert.strictEqual(f.meta.children.length,0);
  f=fixture();context.highlightCardSort(f.card,f.meta,item,{metric:'off'},false);
  assert(f.kpis.every(node=>!node.getAttribute('data-ss-sort-active')));assert.strictEqual(f.meta.children.length,0);
  console.log('Actual-source sort headline, selected cells, credit fallback and known/unknown Win-rate presentation passed.');
}
module.exports=run;if(require.main===module)run();
