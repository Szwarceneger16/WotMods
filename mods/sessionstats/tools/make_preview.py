#!/usr/bin/env python3
"""Render the actual UI with synthetic input processed by the real stats core.

No fixture or demo data is included in the game .wotmod. This tool is optional.
"""
import copy
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from grz_session_stats.core import StatsService, aggregate_stats
from grz_session_stats.appearance import CONFIG_FILENAME, load_config, build_presentation
from grz_session_stats.localization import Localizer


def snapshots():
    # Deliberately synthetic tank IDs and reference values, never a substitute
    # for the real WG table bundled in data/wn8exp.json.
    expected = {'header': {'version': 'example', 'source': 'synthetic'}, 'data': [
        {'IDNum':101, 'expDamage':1800, 'expFrag':1.0, 'expSpot':1.5, 'expDef':0.8, 'expWinRate':51},
        {'IDNum':202, 'expDamage':1650, 'expFrag':0.95, 'expSpot':1.2, 'expDef':0.8, 'expWinRate':51},
        {'IDNum':303, 'expDamage':1750, 'expFrag':1.0, 'expSpot':1.6, 'expDef':0.75, 'expWinRate':51}]}
    tanks = [(101, 'Leopard 1'), (202, 'E 50 M'), (303, 'Bat.-Châtillon 25 t')]
    maps = [('malinovka','Malinovka'), ('murovanka','Murovanka'), ('prokhorovka','Prokhorovka'),
            ('himmelsdorf','Himmelsdorf'), ('redshire','Redshire')]
    start = datetime(2026,10,20,16,10,tzinfo=timezone.utc).timestamp()
    clock = [start-86400]
    def make_record(i, offset):
        tank = tanks[(i // 3) % 3]
        map_info = maps[i % len(maps)]
        credit_income = 57680+i*1417
        repair, ammo, consumables = 7900+i*163, 21200+(i%4)*2280, 3000
        costs = repair+ammo+consumables
        xp_base = 346+((i*137)%907)
        return {'arena_id':str(offset+i), 'started_at':clock[0], 'ended_at':clock[0]+380,
                'vehicle_id':tank[0], 'vehicle_name':tank[1], 'vehicle_tier':10,
                'vehicle_type':'mediumTank', 'map_id':map_info[0], 'map_name':map_info[1],
                'mode':'random', 'outcome':('draw' if i==14 else ('win' if i%2==0 else 'loss')),
                'damage':870+(i*347)%3030, 'frags':i%4, 'spots':i%5, 'defense':i%3,
                'xp_base':xp_base, 'xp_received':xp_base*(2 if i%3 else 5), 'free_xp':84+i*19,
                'complete':True, 'warnings':[],
                'currencies':{
                    'credits':{'income':credit_income, 'costs':costs,'net':credit_income-costs,
                               'breakdown':{'repair':repair,'ammo':ammo,'consumables':consumables,'directives':0}},
                    'bonds':{'income':7 if i%2==0 else 0, 'costs':6 if i%5==0 else 0,
                             'net':(7 if i%2==0 else 0)-(6 if i%5==0 else 0)},
                    'gold':{'income':0,'costs':0,'net':0}}}
    with tempfile.TemporaryDirectory(prefix='grz-preview-') as directory:
        service = StatsService(directory, 'DEMO:100', 'previous-process', expected, now=lambda:clock[0])
        for i in range(9):
            clock[0] += 420
            record = make_record(i,1000000)
            service.begin_battle(record['arena_id'],record['started_at'],record['vehicle_id'],record['map_id'],'random')
            clock[0] += 390
            service.record_result(record)
        clock[0] = start
        service = StatsService(directory, 'DEMO:100', 'current-process', expected, now=lambda:clock[0])
        for i in range(16):
            clock[0] += 120
            record = make_record(i,2000000)
            service.begin_battle(record['arena_id'],record['started_at'],record['vehicle_id'],record['map_id'],'random')
            clock[0] += 390
            service.record_result(record)
        result = service.snapshot()
        service.reset_manual()
        reset = service.snapshot()
    return result, reset


def main():
    output = ROOT/'preview'
    output.mkdir(exist_ok=True)
    normal, reset = snapshots()
    config = load_config(str(ROOT/CONFIG_FILENAME))
    presentation = build_presentation(config)
    localizer = Localizer(config['language'])
    fixtures = {'normal':normal,'reset':reset}
    (output/'demo_snapshot.json').write_text(json.dumps(fixtures,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    # Keep regression fixtures canonical; localize the generated preview itself.
    for snapshot in fixtures.values():
        localizer.snapshot(snapshot)
    html = (ROOT/'ui'/'SessionStats.html').read_text(encoding='utf-8')
    # The standalone page has an outer demo toolbar/background. Compile the
    # configured panel first, then retain that page's own host styles last.
    # Runtime appearance is separately covered by the native-model UI tests.
    css = presentation['panel_css']
    js = (ROOT/'ui'/'session_stats.js').read_text(encoding='utf-8')
    html = html.replace('<link rel="stylesheet" href="session_stats.css">', '<style>\n'+css+'\n</style>')
    html = re.sub(r'<script(?: type="module")? src="session_stats.js"></script>',
                  lambda m:'<script>\n'+js+'\n</script>', html)
    controller = (output/'controller.js').read_text(encoding='utf-8')
    demo = '<script>window.GRZ_DEMO_FIXTURES = '+json.dumps(fixtures,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';</script>'
    html = html.replace('<body>', '<body>\n<div class="demo-toolbar"><span data-i18n="preview.label">Preview · synthetic data</span><button id="demo-reopen" type="button" data-i18n="preview.open">Open panel</button><button id="demo-restart" type="button" data-i18n="preview.restore">Restore example</button></div>')
    html = html.replace('</body>',demo+'\n<script>\n'+controller+'\n</script>\n</body>')
    preview_css = '''
body { height:auto; min-height:100%; padding:12px; background:#20221c; }
html { overflow:auto; }
.ss-window { margin:0 auto; }
.demo-toolbar { display:flex; align-items:center; max-width:700px; margin:0 auto 8px;
 font:12px Arial,sans-serif; color:#c1bfad; }
.demo-toolbar span { display:block; margin-right:auto; }
.demo-toolbar button { display:block; font:12px Arial,sans-serif; color:#d9d4b8;
 background:#35382b; border:1px solid #616047; padding:5px 8px; margin-left:6px; }
@media(max-width:430px) { body{padding:4px;} .demo-toolbar{font-size:11px;flex-wrap:wrap;}
.demo-toolbar span{width:100%;margin-bottom:5px;} }
'''
    html=html.replace('</head>', '<style>'+preview_css+'</style>\n</head>')
    path = output/'PODGLAD.html'
    path.write_text(html,encoding='utf-8')
    # Keep the independent icon preview on the actual shipped stylesheet.
    footer_path = output/'footer-icon.html'
    footer_css = (ROOT/'ui'/'footer.css').read_text(encoding='utf-8')
    footer_html = footer_path.read_text(encoding='utf-8')
    footer_html = re.sub(r'<html lang="[^"]*">',
                         lambda unused:'<html lang="'+localizer.language+'">', footer_html)
    footer_html = re.sub(r'<title>.*?</title>',
                         lambda unused:'<title>'+escape(localizer.text('title'))+'</title>', footer_html)
    footer_html = re.sub(r'(<button id="grz-session-stats-footer-button"[^>]*)(>)',
        lambda match:re.sub(r'(aria-label|title)="[^"]*"',
            lambda attribute:attribute.group(1)+'="'+escape(localizer.text('footer.idle'), quote=True)+'"',
            match.group(1))+match.group(2), footer_html)
    footer_html = re.sub(r'(<span class="grz-session-footer-rating"[^>]*>).*?(</span>)',
        lambda match:match.group(1)+escape(localizer.text('metric.wn8'))+match.group(2), footer_html)
    footer_html, count = re.subn(r'(<style id="grz-footer-styles">).*?(</style>)',
        lambda m:m.group(1)+'\n'+footer_css+'\n'+m.group(2), footer_html, flags=re.S)
    if count != 1:
        raise ValueError('Static footer preview stylesheet marker is missing')
    marker = '<style id="grz-footer-appearance">'
    appearance_style = marker+'\n'+presentation['footer_css']+'\n</style>'
    if marker in footer_html:
        footer_html = re.sub(r'<style id="grz-footer-appearance">.*?</style>',
            lambda m:appearance_style, footer_html, flags=re.S)
    else:
        footer_html = footer_html.replace('</head>', appearance_style+'\n</head>')
    footer_path.write_text(footer_html, encoding='utf-8')
    print(json.dumps({'preview':str(path),'launch_battles':normal['scopes']['launch']['summary']['battles'],
        'manual_battles':normal['scopes']['manual']['summary']['battles'],
        'wn8':normal['scopes']['launch']['summary']['wn8'],'bytes':path.stat().st_size},ensure_ascii=False))


if __name__=='__main__': main()
