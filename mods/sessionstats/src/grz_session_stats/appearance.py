# -*- coding: utf-8 -*-
"""Validated local presentation settings, independent of the WoT client.

Static UI styles remain the fallback. These tokenized copies intentionally keep
all original declarations; the coverage/equivalence tests flag a future style
change that is not carried into this explicit user-facing configuration.
No selector, CSS declaration, file path or script is supplied by the JSON.
"""
from __future__ import absolute_import, unicode_literals

import copy
import errno
import io
import json
import logging
import math
import re

LOG = logging.getLogger('grz.sessionstats')
CONFIG_FILENAME = 'grz.sessionstats.json'
MAX_CONFIG_BYTES = 128 * 1024
MAX_DIAGNOSTICS = 64
SCHEMA_VERSION = 1
try:
    text_type = unicode
    integer_types = (int, long)
except NameError:
    text_type = str
    integer_types = (int,)
NUMBER_TYPES = integer_types + (float,)

DEFAULT_CONFIG = {'schema_version': 1,
 'language': 'auto',
 'colors': {'body_text': '#e5e2cb',
            'body_background': 'transparent',
            'window_border': '#646044',
            'window_background': '#111309',
            'window_shadow_1': '#88805c',
            'window_shadow_2': '#292819',
            'titlebar_background_start': '#343428',
            'titlebar_background_end': '#1c1e12',
            'title_text': '#f0eddc',
            'title_text_shadow': '#000',
            'game_mode_text': '#aaa98f',
            'close_background': 'transparent',
            'close_text': '#bcb693',
            'close_hover_text': '#f5e3a5',
            'session_tabs_border': '#050601',
            'session_tab_background_start': '#383a2c',
            'session_tab_background_middle': '#16190e',
            'session_tab_background_end': '#1c2014',
            'session_tab_text': '#ada98b',
            'session_tab_shadow': '#646149',
            'session_tab_separator_border_left': '#050601',
            'session_tab_hover_text': '#eee1b5',
            'session_tab_active_text': '#f0d392',
            'session_tab_active_background_start': '#494329',
            'session_tab_active_background_middle': '#2e2915',
            'session_tab_active_background_end': '#151309',
            'session_tab_active_text_shadow': '#b77923',
            'session_tab_marker_background': '#e7a23b',
            'session_tab_marker_border_right': '#ffdda0',
            'session_tab_marker_border_bottom': '#ffdda0',
            'period_text': '#aaa68c',
            'xp_picker_border': '#444329',
            'xp_toggle_background': '#0e1008',
            'xp_toggle_text': '#aaa78b',
            'xp_toggle_active_background_start': '#4c482f',
            'xp_toggle_active_background_end': '#292814',
            'xp_toggle_active_text': '#e8d8a7',
            'xp_toggle_active_shadow': '#807446',
            'xp_toggle_hover_text': '#f1e4bb',
            'scrollbar_track_background': '#0b0d05',
            'scrollbar_thumb_background': '#5a5738',
            'scrollbar_thumb_border': '#827747',
            'kpi_separator_border_left': '#30321d',
            'kpi_label_text': '#c2bda2',
            'kpi_value_text': '#e8e5d2',
            'kpi_wn8_text': '#d9dca4',
            'outcome_summary_text': '#bebca3',
            'outcome_summary_value_text': '#e0dcc3',
            'details_separator_border_top': '#303421',
            'economy_separator_border_left': '#2d3220',
            'detail_title_text': '#dfd5b5',
            'table_header_background_start': '#292e1f',
            'table_header_background_end': '#222719',
            'table_header_text': '#c4c1a7',
            'table_row_background': '#181d11',
            'table_row_following_border_top': '#2e3522',
            'table_row_following_background': '#1a1f13',
            'table_row_hover_background': '#252d1b',
            'metric_label_text': '#d4ccb0',
            'metric_value_text': '#ebe7d4',
            'table_header_cell_text': '#c4c1a7',
            'free_xp_label_text': '#c3bea3',
            'free_xp_value_text': '#e6dab3',
            'money_label_text': '#d4ccb0',
            'positive_text': '#c0d889',
            'negative_text': '#e4ad84',
            'unknown_text': '#9a967f',
            'partial_count_text': '#d2b681',
            'battle_measure_background': '#181d11',
            'battle_measure_following_background': '#1c2215',
            'battle_label_text': '#c9c3a7',
            'battle_value_text': '#ebe7d4',
            'battle_wn8_text': '#d9dca4',
            'coverage_notice_text': '#d1b782',
            'data_notice_text': '#d9bf8b',
            'explanation_text': '#b1b49a',
            'group_tabs_border_top': '#393b24',
            'group_tabs_border_bottom': '#655431',
            'group_tab_background': 'transparent',
            'group_tab_text': '#afaa8b',
            'group_tab_hover_background': '#252614',
            'group_tab_hover_text': '#eaddb4',
            'group_tab_active_text': '#f1d195',
            'group_tab_active_background_start': '#292614',
            'group_tab_active_background_end': '#35301b',
            'group_tab_active_shadow': '#b17d2b',
            'list_meta_text': '#b3b69a',
            'group_card_background_start': '#1c2013',
            'group_card_background_end': '#15190e',
            'group_card_shadow': '#303722',
            'group_title_text': '#e8debf',
            'group_subtitle_text': '#b4b599',
            'battle_outcome_background': '#293020',
            'battle_outcome_text': '#c5c4aa',
            'win_background': '#2a351d',
            'win_text': '#cedc9d',
            'loss_background': '#352b1e',
            'loss_text': '#dfb493',
            'draw_background': '#2c2e23',
            'draw_text': '#c4c1a7',
            'empty_text': '#b5b095',
            'panel_footer_border_top': '#3b3c24',
            'panel_footer_background_start': '#171b0d',
            'panel_footer_background_end': '#1f2213',
            'status_text': '#a5a286',
            'button_border': '#555944',
            'button_text': '#dfd4ae',
            'button_background_start': '#45483a',
            'button_background_middle': '#34392a',
            'button_background_end': '#2d3325',
            'button_shadow_1': 'rgba(236,220,174,0.3)',
            'button_shadow_2': 'rgba(213,191,132,0.12)',
            'button_hover_text': '#f1e3b8',
            'button_hover_background_start': '#5b5b45',
            'button_hover_background_end': '#3a412e',
            'button_quiet_border_color': '#3b4026',
            'button_quiet_background': '#1c2412',
            'button_confirm_background_start': '#68542f',
            'button_confirm_background_end': '#3d2e13',
            'button_confirm_text': '#ffe1a4',
            'reset_backdrop_background': 'rgba(4,7,2,0.87)',
            'confirmation_border': '#7b6940',
            'confirmation_background_start': '#313121',
            'confirmation_background_end': '#13170b',
            'confirmation_shadow': '#000',
            'confirmation_title_text': '#f0dfb6',
            'confirmation_message_text': '#c5bea0',
            'economy_separator_border_top': '#282e17',
            'garage_button_background': 'transparent',
            'garage_button_text': '#969a9d',
            'garage_button_hover_background': 'rgba(255,255,255,0.04)',
            'garage_button_hover_text': '#e0ddd2',
            'garage_button_focus_outline': '#d3c79b',
            'garage_bars_background': '#969a9d',
            'garage_bars_hover_background': '#e0ddd2',
            'garage_wn8_text': '#bdc0c2',
            'garage_wn8_text_shadow': '#000',
            'garage_wn8_hover_text': '#eee6c9',
            'garage_spinner_border': 'rgba(207,190,140,0.25)',
            'garage_spinner_border_top_color': '#dfd3a4'},
 'radii': {'window': 8,
           'titlebar': 7,
           'control': 5,
           'scrollbar_thumb': 3,
           'table_header': 5,
           'table_row': 4,
           'battle_measure': 5,
           'group_tabs': 5,
           'group_card': 7,
           'battle_outcome': 5,
           'panel_footer': 7,
           'confirmation': 8,
           'garage_spinner': 5},
 'opacity': {'window': 1.0, 'garage_button': 1.0, 'disabled_controls': 0.45},
 'scroll': {'speed_multiplier': 1.0},
 'cards': {'battles': 620, 'vehicles': 600, 'maps': 560, 'tiers': 520},
 'sessions': {'instance_tab': False}}

PANEL_TEMPLATE = '''/* Native Gameface view. Deliberately limited to block/flex layout. */
html { font-size:1px; }
html, body { width:100%; height:100%; padding:0; margin:0; overflow:hidden; }
/* Native documents follow the panel's flow size, not the initial Wulf surface.
   The browser preview keeps its independent viewport-sized document. */
html.ss-native-document, html.ss-native-document body { width:auto; height:auto; }
body { color:{{colors.body_text}}; font-family:Warhelios, Arial, sans-serif; font-size:14rem; background:{{colors.body_background}}; }
* { box-sizing:border-box; }
/* Gameface has partial button support and its own default text layout.
   Keep captions in explicit boxes, as in the working native footer button. */
.ss-control { display:flex; align-items:center; justify-content:center; flex-shrink:0; font-family:Warhelios, Arial, sans-serif; font-size:14rem; cursor:pointer; }
.ss-control-label { display:block; flex-shrink:1; min-width:0; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-family:Warhelios, Arial, sans-serif; font-size:14rem; line-height:18rem; text-align:center; pointer-events:none; }
.ss-small-toggle .ss-control-label, .ss-button .ss-control-label { font-size:12rem; line-height:17rem; }
.ss-close .ss-control-label { font-size:25rem; line-height:28rem; }
button:disabled { opacity:{{opacity.disabled_controls}}; }
.ss-window { position:relative; display:flex; flex-direction:column; width:700rem; height:620rem; max-width:100%; max-height:100%; min-width:300px; border:1rem solid {{colors.window_border}}; border-radius:{{radii.window}}rem; background:{{colors.window_background}}; background-image:url("session_stats_camo.png"); background-size:560rem 460rem; background-repeat:repeat; box-shadow:inset 0 1rem 1rem {{colors.window_shadow_1}}, inset 0 0 28rem {{colors.window_shadow_2}}; }
.ss-window.is-native { max-width:none; max-height:none; }
.ss-titlebar { position:relative; z-index:30; display:flex; flex-wrap:wrap; align-items:center; flex-shrink:0; min-height:47rem; padding:6rem 45rem 7rem 13rem; border-radius:{{radii.titlebar}}rem {{radii.titlebar}}rem 0 0; background:linear-gradient({{colors.titlebar_background_start}}, {{colors.titlebar_background_end}}); box-shadow:inset 0 1rem {{colors.session_tab_shadow}}, inset 0 -1rem {{colors.session_tabs_border}}; }
.ss-title-identity { display:flex; align-items:center; flex:1 0 220rem; min-width:0; max-width:100%; min-height:32rem; }
.ss-title-actions { display:flex; align-items:center; justify-content:flex-end; flex-wrap:wrap; flex:0 1 416rem; width:416rem; max-width:100%; min-width:0; margin-left:auto; }
.ss-titlebar h1 { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:22rem; line-height:26rem; margin:0; font-weight:bold; color:{{colors.title_text}}; text-shadow:0 1rem 2rem {{colors.title_text_shadow}}; }
.ss-game-mode { display:block; flex-shrink:0; white-space:nowrap; color:{{colors.game_mode_text}}; font-size:12rem; margin-left:12rem; }
.ss-close { position:absolute; top:6rem; right:9rem; border:0; background:{{colors.close_background}}; color:{{colors.close_text}}; width:27rem; height:30rem; margin:0; padding:0; font-size:25rem; border-radius:{{radii.control}}rem; }
.ss-close:hover, .ss-close:focus { color:{{colors.close_hover_text}}; background:{{colors.group_tab_hover_background}}; }
.ss-controls { padding:0 12rem 4rem; flex-shrink:0; }
.ss-scopes { display:flex; flex:0 1 260rem; min-width:0; width:260rem; max-width:100%; margin:0 8rem 4rem 0; border:1rem solid {{colors.session_tabs_border}}; border-radius:{{radii.control}}rem; }
.ss-scope { position:relative; flex:1 1 0rem; min-width:0; width:0; height:30rem; border:0; background:linear-gradient({{colors.session_tab_background_start}}, {{colors.session_tab_background_middle}} 58%, {{colors.session_tab_background_end}}); color:{{colors.session_tab_text}}; padding:4rem 6rem; border-radius:{{radii.control}}rem; box-shadow:inset 0 1rem {{colors.session_tab_shadow}}; }
.ss-scope + .ss-scope { border-left:1rem solid {{colors.session_tab_separator_border_left}}; }
.ss-scope:hover, .ss-scope:focus { color:{{colors.session_tab_hover_text}}; box-shadow:inset 0 1rem {{colors.button_shadow_1}}, inset 0 0 5rem {{colors.button_shadow_2}}; }
.ss-scope.is-active { color:{{colors.session_tab_active_text}}; background:linear-gradient({{colors.session_tab_active_background_start}}, {{colors.session_tab_active_background_middle}} 56%, {{colors.session_tab_active_background_end}}); text-shadow:0 0 7rem {{colors.session_tab_active_text_shadow}}; }
.ss-scope.is-active:after { content:""; position:absolute; left:50%; bottom:-3rem; width:5rem; height:5rem; background:{{colors.session_tab_marker_background}}; border-right:1rem solid {{colors.session_tab_marker_border_right}}; border-bottom:1rem solid {{colors.session_tab_marker_border_bottom}}; transform:rotate(45deg); }
.ss-toolbar { display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-start; min-height:37rem; padding-top:4rem; }
.ss-period { display:block; flex:0 1 184rem; min-width:0; width:184rem; max-width:100%; font-size:12rem; color:{{colors.period_text}}; margin:0 8rem 4rem 0; }
.ss-xp-picker { display:flex; flex:0 0 212rem; width:212rem; max-width:100%; margin-bottom:4rem; border:1rem solid {{colors.xp_picker_border}}; border-radius:{{radii.control}}rem; }
.ss-small-toggle { width:98rem; border:0; background:{{colors.xp_toggle_background}}; color:{{colors.xp_toggle_text}}; font-size:12rem; min-height:25rem; padding:3rem 7rem; border-radius:{{radii.control}}rem; box-shadow:inset 0 1rem {{colors.button_shadow_2}}; }
#ss-xp-received { width:112rem; }
.ss-small-toggle.is-active { background:linear-gradient({{colors.xp_toggle_active_background_start}}, {{colors.xp_toggle_active_background_end}}); color:{{colors.xp_toggle_active_text}}; box-shadow:inset 0 1rem {{colors.xp_toggle_active_shadow}}; }
.ss-small-toggle:hover, .ss-small-toggle:focus { color:{{colors.xp_toggle_hover_text}}; box-shadow:inset 0 1rem {{colors.button_shadow_1}}, inset 0 0 5rem {{colors.button_shadow_2}}; }
.ss-scroll { flex:1; min-height:0; overflow-y:auto; overflow-x:hidden; padding:0 12rem 10rem; }
.ss-scroll::-webkit-scrollbar { width:8rem; background:{{colors.scrollbar_track_background}}; }
.ss-scroll::-webkit-scrollbar-thumb { background:{{colors.scrollbar_thumb_background}}; border:1rem solid {{colors.scrollbar_thumb_border}}; border-radius:{{radii.scrollbar_thumb}}rem; }
.ss-summary { margin:0; padding:0 0 8rem; }
.ss-headline { display:flex; padding:4rem 0 5rem; }
.ss-kpi { width:33.333%; text-align:center; padding:0 5rem; border-left:1rem solid {{colors.kpi_separator_border_left}}; }
.ss-kpi:first-child { border-left:0; }
.ss-kpi-label { display:block; color:{{colors.kpi_label_text}}; font-size:13rem; line-height:17rem; }
.ss-kpi-value { display:block; color:{{colors.kpi_value_text}}; font-size:29rem; line-height:32rem; font-weight:bold; }
.ss-kpi-value.ss-wn8 { color:{{colors.kpi_wn8_text}}; }
.ss-outcomes { display:flex; align-items:center; justify-content:center; flex-wrap:wrap; margin:0 0 6rem; font-size:13rem; line-height:18rem; color:{{colors.outcome_summary_text}}; }
.ss-outcomes span { display:block; margin-right:4rem; }
.ss-outcomes strong { display:block; margin-right:8rem; color:{{colors.outcome_summary_value_text}}; font-weight:normal; }
.ss-details { display:flex; width:100%; padding:4rem 0 2rem; border-top:1rem solid {{colors.details_separator_border_top}}; }
.ss-performance { width:45%; padding-right:9rem; }
.ss-economy { width:55%; padding-left:8rem; border-left:1rem solid {{colors.economy_separator_border_left}}; }
.ss-detail-title { margin:0 0 5rem; color:{{colors.detail_title_text}}; font-size:14rem; line-height:18rem; font-weight:bold; }
/* Summary sections keep useful line lengths and wrap by their actual parent
   width. Their flow is independent of the game viewport and card columns. */
.ss-summary-layout.ss-details { flex-direction:row; flex-wrap:wrap; align-items:flex-start; padding:0; border:0; }
.ss-summary-main { flex:0 1 340rem; width:340rem; max-width:100%; min-width:0; padding:0 12rem 0 0; margin:0 0 8rem; }
.ss-summary-layout > .ss-performance { flex:0 1 310rem; width:310rem; max-width:100%; min-width:0; padding:4rem 12rem 0 0; margin:0 0 8rem; }
.ss-summary-layout > .ss-economy { flex:0 1 420rem; width:420rem; max-width:100%; min-width:0; padding:4rem 0 0; margin:0 0 8rem; border:0; }
.ss-summary-main .ss-headline { display:block; padding:0 0 4rem; }
.ss-summary-main .ss-kpi { display:flex; align-items:center; justify-content:space-between; width:100%; min-height:32rem; padding:0 5rem; border-left:0; }
.ss-summary-main .ss-kpi + .ss-kpi { border-top:1rem solid {{colors.kpi_separator_border_left}}; }
.ss-summary-main .ss-kpi-label { flex:1 1 0rem; min-width:0; margin-right:8rem; text-align:left; }
.ss-summary-main .ss-kpi-value { flex:0 1 auto; min-width:0; max-width:72%; text-align:right; overflow-wrap:break-word; }
.ss-summary-main .ss-outcomes { justify-content:flex-start; margin:0 4rem 4rem; }
.ss-summary-main .ss-summary-meta { margin:0 4rem; }
.ss-summary-layout .ss-money-head, .ss-summary-layout .ss-money-row { flex-wrap:wrap; }
.ss-summary-layout .ss-money-head .ss-money-label { display:none; }
.ss-summary-layout .ss-money-row .ss-money-label { width:100%; padding-bottom:0; line-height:17rem; }
.ss-summary-layout .ss-money-value { width:33.333%; }
/* WoT-style insets and quiet row rules replace the cell grid. Use explicit
   block/flex boxes, supported corner radii and colours for Gameface. */
.ss-metric-head, .ss-metric-row, .ss-money-head, .ss-money-row { display:flex; align-items:stretch; min-height:26rem; }
.ss-metric-head, .ss-money-head { min-height:22rem; margin-bottom:1rem; border-radius:{{radii.table_header}}rem; background:linear-gradient({{colors.table_header_background_start}}, {{colors.table_header_background_end}}); color:{{colors.table_header_text}}; font-size:12rem; line-height:17rem; }
.ss-metric-row, .ss-money-row { border-radius:{{radii.table_row}}rem; background:{{colors.table_row_background}}; }
.ss-metric-row + .ss-metric-row, .ss-money-row + .ss-money-row { border-top:1rem solid {{colors.table_row_following_border_top}}; background:{{colors.table_row_following_background}}; }
.ss-metric-row:hover, .ss-money-row:hover { background:{{colors.table_row_hover_background}}; }
.ss-metric-name, .ss-metric-number, .ss-money-label, .ss-money-value { padding:3rem 4rem; line-height:20rem; }
.ss-metric-name { display:block; width:28%; flex-shrink:0; color:{{colors.metric_label_text}}; font-size:13rem; }
.ss-metric-number { display:block; width:24%; padding-right:3rem; text-align:right; color:{{colors.metric_value_text}}; font-size:16rem; }
/* Right-aligned numbers retain a 3rem metric / 4rem money trailing inset. There is no
   vertical cell rule; spare leading space belongs to the full amount. */
.ss-metric-number, .ss-money-value { padding-left:0; }
.ss-metric-head .ss-metric-name, .ss-metric-head .ss-metric-number, .ss-money-head .ss-money-label, .ss-money-head .ss-money-value { padding-top:2rem; padding-bottom:2rem; font-size:12rem; line-height:17rem; color:{{colors.table_header_cell_text}}; }
.ss-free-xp { display:flex; align-items:center; flex-wrap:wrap; font-size:13rem; color:{{colors.free_xp_label_text}}; margin:0; line-height:17rem; }
.ss-free-xp span { display:block; margin-right:4rem; }
.ss-free-xp strong { display:block; color:{{colors.free_xp_value_text}}; font-size:14rem; font-weight:normal; margin-right:4rem; }
.ss-money-label { display:block; width:19%; font-size:13rem; color:{{colors.money_label_text}}; }
.ss-money-value { display:block; width:27%; text-align:right; font-size:14rem; }
.ss-positive { color:{{colors.positive_text}}; }
.ss-negative { color:{{colors.negative_text}}; }
.ss-unknown { color:{{colors.unknown_text}}; }
.ss-cell-value { display:block; }
.ss-cell-coverage { display:block; color:{{colors.partial_count_text}}; font-size:12rem; line-height:15rem; }
.ss-battle-measure { display:flex; align-items:center; justify-content:space-between; min-height:28rem; padding:2rem 7rem; border-radius:{{radii.battle_measure}}rem; background:{{colors.battle_measure_background}}; }
.ss-battle-measure + .ss-battle-measure { margin-top:3rem; background:{{colors.battle_measure_following_background}}; }
.ss-battle-label { display:block; flex:1; min-width:0; padding-right:10rem; color:{{colors.battle_label_text}}; font-size:13rem; line-height:20rem; }
.ss-battle-value { display:block; flex-shrink:0; color:{{colors.battle_value_text}}; font-size:18rem; font-weight:bold; line-height:24rem; text-align:right; }
.ss-battle-value.ss-wn8 { color:{{colors.battle_wn8_text}}; }

.ss-coverage-note { color:{{colors.coverage_notice_text}}; font-size:12rem; line-height:16rem; padding-top:0; }
.ss-data-notices { padding:5rem 0 0; }
.ss-data-notice { color:{{colors.data_notice_text}}; font-size:13rem; line-height:18rem; margin:2rem 0 0; }
.ss-explainer { color:{{colors.explanation_text}}; font-size:12rem; margin-top:5rem; line-height:17rem; }
.ss-group-tabs { display:flex; min-height:30rem; border-top:1rem solid {{colors.group_tabs_border_top}}; border-bottom:1rem solid {{colors.group_tabs_border_bottom}}; border-radius:{{radii.group_tabs}}rem {{radii.group_tabs}}rem 0 0; }
.ss-group-tab { width:25%; padding:4rem 3rem 6rem; min-height:30rem; border:0; border-radius:{{radii.control}}rem {{radii.control}}rem 0 0; background:{{colors.group_tab_background}}; color:{{colors.group_tab_text}}; font-size:14rem; }
.ss-group-tab:hover, .ss-group-tab:focus { background:{{colors.group_tab_hover_background}}; color:{{colors.group_tab_hover_text}}; }
.ss-group-tab.is-active { color:{{colors.group_tab_active_text}}; background:linear-gradient({{colors.group_tab_active_background_start}}, {{colors.group_tab_active_background_end}}); box-shadow:inset 0 -2rem {{colors.group_tab_active_shadow}}, inset 0 1rem {{colors.session_tab_shadow}}; }
.ss-list-controls { display:flex; flex-wrap:wrap; align-items:flex-end; width:100%; padding-top:5rem; }
.ss-list-meta { display:flex; flex-wrap:wrap; align-items:center; flex:0 1 168rem; min-width:0; width:168rem; max-width:100%; min-height:29rem; margin:0 8rem 5rem 0; font-size:12rem; color:{{colors.list_meta_text}}; }
.ss-list-meta > span + span { margin-left:8rem; }
.ss-group { margin-bottom:5rem; padding:5rem 6rem; border-radius:{{radii.group_card}}rem; background:linear-gradient({{colors.group_card_background_start}}, {{colors.group_card_background_end}}); border:1rem solid {{colors.group_card_shadow}}; box-shadow:inset 0 1rem {{colors.group_card_shadow}}; }
.ss-group-header { display:flex; align-items:center; min-height:35rem; padding-bottom:2rem; }
.ss-group-thumb { display:block; flex-shrink:0; width:54rem; height:32rem; margin-right:8rem; background-repeat:no-repeat; background-position:center; background-size:contain; }
.ss-group-name { flex:1; min-width:0; padding-right:8rem; }
.ss-group-title { color:{{colors.group_title_text}}; font-weight:normal; font-size:17rem; line-height:20rem; margin:0; overflow-wrap:break-word; }
.ss-group-subtitle { color:{{colors.group_subtitle_text}}; font-size:12rem; line-height:16rem; margin-top:1rem; }
.ss-battle-outcome { display:block; flex-shrink:0; margin-left:8rem; padding:2rem 5rem; border-radius:{{radii.battle_outcome}}rem; background:{{colors.battle_outcome_background}}; color:{{colors.battle_outcome_text}}; font-size:13rem; line-height:18rem; }
.ss-outcome-win { background:{{colors.win_background}}; color:{{colors.win_text}}; }
.ss-outcome-loss { background:{{colors.loss_background}}; color:{{colors.loss_text}}; }
.ss-outcome-draw, .ss-outcome-unknown { background:{{colors.draw_background}}; color:{{colors.draw_text}}; }
.ss-group-kpi { flex-shrink:0; width:90rem; text-align:right; padding-left:5rem; }
.ss-group-kpi .ss-kpi-label { font-size:12rem; line-height:16rem; }
.ss-group-kpi .ss-kpi-value { font-size:20rem; line-height:23rem; }
.ss-group .ss-details { border-top:0; padding-top:4rem; }
.ss-group .ss-detail-title { display:none; }
.ss-group .ss-explainer { display:none; }
.ss-empty { color:{{colors.empty_text}}; font-size:14rem; padding:16rem 4rem; margin:0; line-height:20rem; }
.ss-footer { flex-shrink:0; display:flex; align-items:center; min-height:36rem; border-top:1rem solid {{colors.panel_footer_border_top}}; border-radius:0 0 {{radii.panel_footer}}rem {{radii.panel_footer}}rem; padding:5rem 25rem 7rem 10rem; background:linear-gradient({{colors.panel_footer_background_start}},{{colors.panel_footer_background_end}}); box-shadow:inset 0 -2rem {{colors.session_tabs_border}}; }
.ss-status { display:block; flex:1; min-width:0; color:{{colors.status_text}}; font-size:11rem; line-height:14rem; padding-right:8rem; }
.ss-button { flex-shrink:0; min-width:82rem; min-height:28rem; padding:4rem 10rem; font-size:12rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; color:{{colors.button_text}}; background:linear-gradient({{colors.button_background_start}},{{colors.button_background_middle}} 48%,{{colors.button_background_end}}); box-shadow:inset 0 1rem {{colors.button_shadow_1}}, inset 1rem 0 {{colors.button_shadow_2}}, inset -1rem 0 {{colors.button_shadow_2}}; text-shadow:0 1rem 1rem {{colors.title_text_shadow}}; transition:color 120ms, border-color 120ms, box-shadow 120ms; }
.ss-button:hover, .ss-button:focus { color:{{colors.button_hover_text}}; border-color:{{colors.button_shadow_1}}; background:linear-gradient({{colors.button_hover_background_start}},{{colors.button_background_start}} 48%,{{colors.button_hover_background_end}}); box-shadow:inset 0 1rem {{colors.button_shadow_1}}, inset 0 0 7rem {{colors.button_shadow_2}}, 0 0 4rem {{colors.button_shadow_2}}; }
.ss-button:active, .ss-scope:active, .ss-small-toggle:active { background:linear-gradient({{colors.button_background_end}},{{colors.button_background_middle}}); box-shadow:inset 0 2rem 4rem {{colors.title_text_shadow}}, inset 0 -1rem {{colors.button_shadow_2}}; text-shadow:none; }
.ss-button + .ss-button { margin-left:8rem; }
.ss-quiet { border-color:{{colors.button_quiet_border_color}}; background:{{colors.button_quiet_background}}; }
.ss-reset { display:none; min-width:124rem; }
.ss-gold { min-width:124rem; background:linear-gradient({{colors.button_confirm_background_start}},{{colors.button_confirm_background_end}}); color:{{colors.button_confirm_text}}; }
.ss-modal-overlay { position:absolute; left:0; right:0; top:0; bottom:0; z-index:40; align-items:center; justify-content:center; padding:14rem; background:{{colors.reset_backdrop_background}}; }
.ss-confirm { width:390rem; max-width:100%; padding:18rem; border:1rem solid {{colors.confirmation_border}}; border-radius:{{radii.confirmation}}rem; background:linear-gradient({{colors.confirmation_background_start}},{{colors.confirmation_background_end}}); box-shadow:0 3rem 18rem {{colors.confirmation_shadow}}; }
.ss-confirm h2 { margin:0 0 10rem; color:{{colors.confirmation_title_text}}; font-size:20rem; line-height:25rem; }
.ss-confirm p { margin:0 0 14rem; color:{{colors.confirmation_message_text}}; font-size:14rem; line-height:20rem; }
.ss-confirm-actions { display:flex; justify-content:flex-end; }
@media (max-width:680px) {
  .ss-details { flex-direction:column; }
  .ss-performance { width:100%; padding-right:0; }
  .ss-economy { width:100%; padding:5rem 0 0; margin-top:4rem; border-left:0; border-top:1rem solid {{colors.economy_separator_border_top}}; }
}
@media (max-width:560px) {
  .ss-titlebar { padding-left:9rem; padding-right:40rem; }
  .ss-titlebar h1 { font-size:20rem; }
  .ss-game-mode { font-size:11rem; margin-left:8rem; }
  .ss-controls { padding:0 8rem; }
  .ss-scroll { padding-left:8rem; padding-right:8rem; }
  .ss-group-header { flex-wrap:wrap; }
  .ss-group-name { min-width:75%; }
  .ss-battle .ss-group-name { min-width:0; }
  .ss-group-kpi { width:33.333%; margin-top:3rem; }
  .ss-group-kpi .ss-kpi-value { font-size:19rem; }
  .ss-group .ss-detail-title { display:none; }
}
@media (max-width:400px) {
  /* Keep full financial amounts readable even in a narrow game viewport.
     The row label takes a separate line; the three number columns stay equal. */
  .ss-metric-head, .ss-metric-row, .ss-money-head, .ss-money-row { flex-wrap:wrap; }
  .ss-metric-head .ss-metric-name, .ss-money-head .ss-money-label { display:none; }
  .ss-metric-head .ss-metric-count { display:block; width:100%; padding:0 4rem; }
  .ss-metric-name, .ss-money-label { width:100%; padding-bottom:1rem; }
  .ss-metric-number, .ss-money-value { width:33.333%; }
}
@media (max-width:380px) {
  .ss-game-mode { display:none; }
  .ss-group-thumb { width:42rem; height:26rem; margin-right:6rem; }
  .ss-group-title { font-size:14rem; }
  .ss-group-kpi .ss-kpi-value { font-size:17rem; }
  .ss-footer { padding-left:8rem; }
  .ss-footer .ss-button { padding-left:7rem; padding-right:7rem; }
}

.ss-pagination { display:flex; align-items:center; flex:0 1 340rem; min-width:0; width:340rem; max-width:100%; margin:0 8rem 5rem 0; }
.ss-pagination > .ss-button { flex:0 0 auto; min-width:64rem; width:auto; height:27rem; min-height:27rem; padding:3rem 7rem; }
.ss-pagination .ss-button:disabled { cursor:default; pointer-events:none; }
#ss-page-label { display:block; min-width:0; padding:0 2rem; text-align:center; color:{{colors.list_meta_text}}; font-size:12rem; line-height:17rem; }
.ss-language-row { display:flex; align-items:center; flex:0 1 158rem; min-width:0; min-height:29rem; }
.ss-language-caption { display:block; flex-shrink:1; min-width:0; margin-right:6rem; color:{{colors.list_meta_text}}; font-size:12rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ss-select.ss-language-select { flex:1 1 0rem; width:0; }
.ss-language-select .ss-select-options { left:auto; right:0; }
.ss-page-center { flex:1 1 160rem; min-width:0; padding:0 6rem; }
.ss-sorting { display:flex; flex-wrap:nowrap; align-items:flex-end; flex:0 1 362rem; min-width:0; width:362rem; max-width:100%; margin:0 0 5rem; }
.ss-sort-field { min-width:0; }
.ss-sort-statistic { flex:0 1 84rem; width:84rem; max-width:100%; padding-right:5rem; }
.ss-sort-metric { flex:0 1 144rem; width:144rem; max-width:100%; padding-right:5rem; }
.ss-sort-direction { flex:0 1 134rem; width:134rem; max-width:100%; }
.ss-sort-caption { display:block; margin-bottom:2rem; color:{{colors.list_meta_text}}; font-size:11rem; line-height:14rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ss-select { position:relative; width:100%; min-width:0; }
.ss-select-trigger { width:100%; min-width:0; height:29rem; min-height:29rem; padding:4rem 6rem; justify-content:space-between; }
.ss-page-center .ss-select-trigger { height:27rem; min-height:27rem; padding-top:3rem; padding-bottom:3rem; }
.ss-select-trigger .ss-control-label { flex:1; text-align:left; }
.ss-select-arrow { display:block; flex-shrink:0; width:6rem; height:6rem; margin:-3rem 3rem 0 6rem; border-right:1rem solid currentColor; border-bottom:1rem solid currentColor; transform:rotate(45deg); }
.ss-select-options { position:absolute; top:100%; left:0; z-index:20; min-width:100%; width:180rem; max-width:260rem; padding:3rem; border:1rem solid {{colors.list_meta_text}}; border-radius:{{radii.group_tabs}}rem; background:{{colors.window_background}}; box-shadow:0 3rem 8rem {{colors.title_text_shadow}}; }
.ss-sort-direction .ss-select-options { left:auto; right:0; }
.ss-select-option { width:100%; min-height:28rem; padding:4rem 5rem; border:0; border-radius:{{radii.control}}rem; background:{{colors.body_background}}; color:{{colors.list_meta_text}}; justify-content:flex-start; }
.ss-select-option .ss-control-label { font-size:12rem; line-height:18rem; text-align:left; white-space:normal; }
@media (max-width:420px) {
  .ss-sorting .ss-control-label, .ss-page-center .ss-control-label { font-size:11rem; }
  .ss-sorting .ss-select-trigger { padding-left:3rem; padding-right:3rem; }
}
.ss-select-option:hover, .ss-select-option:focus, .ss-select-option[aria-selected="true"] { color:{{colors.group_title_text}}; background:{{colors.window_background}}; box-shadow:inset 2rem 0 {{colors.list_meta_text}}; }
.ss-outcome-art { display:flex; align-items:center; width:auto; max-width:48%; padding:0; background:none; }
.ss-outcome-image { display:block; flex-shrink:0; width:52rem; height:30rem; background-repeat:no-repeat; background-position:center; background-size:contain; }
.ss-outcome-label { display:block; text-align:center; }
.ss-outcome-art .ss-outcome-label { min-width:0; padding:2rem 4rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

/* Keep optional information above the tables, alongside the vehicle identity. */
.ss-group-heading, .ss-group-meta, .ss-summary-meta { display:flex; align-items:center; flex-wrap:wrap; min-width:0; }
.ss-group-heading .ss-coverage-note { margin-left:8rem; }
.ss-group-meta .ss-group-subtitle { margin-right:10rem; }
.ss-group-meta .ss-free-xp { font-size:12rem; }
.ss-group-meta .ss-free-xp strong { font-size:12rem; }
.ss-summary-meta { margin:3rem 4rem; }
.ss-summary-meta .ss-coverage-note { margin-left:10rem; }
.ss-metric-name .ss-cell-value, .ss-metric-name .ss-cell-coverage, .ss-money-label .ss-cell-coverage { display:inline; }
.ss-metric-name .ss-cell-coverage, .ss-money-label .ss-cell-coverage { font-size:11rem; white-space:nowrap; }
.ss-money-label .ss-cell-coverage { margin-left:3rem; }
@media (max-width:560px) {
  .ss-group-heading .ss-coverage-note { width:100%; margin-left:0; }
  .ss-battle .ss-group-name { width:0; flex:1; }
  .ss-outcome-image { width:36rem; height:25rem; }
  .ss-battle-outcome { margin-left:4rem; }
  .ss-outcome-label { font-size:11rem; }
}
@media (max-width:380px) {
  .ss-language-caption { margin-right:4rem; }
}

.ss-time-point-controls { display:flex; align-items:center; flex:1 1 250rem; min-width:0; margin-right:8rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; background:{{colors.window_background}}; box-shadow:inset 0 1rem {{colors.button_shadow_2}}; }
.ss-time-point-name { display:block; flex:1 1 0rem; width:0; min-width:0; height:29rem; padding:4rem 7rem; margin:0; border:0; border-radius:0 {{radii.control}}rem {{radii.control}}rem 0; background:{{colors.close_background}}; color:{{colors.button_text}}; font-family:Warhelios, Arial, sans-serif; font-size:12rem; line-height:18rem; }
.ss-time-point-name:focus { outline:none; box-shadow:inset 0 0 6rem {{colors.button_shadow_2}}; }
.ss-time-point { flex:0 0 122rem; min-width:0; min-height:29rem; padding-left:7rem; padding-right:7rem; border:0; border-right:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem 0 0 {{radii.control}}rem; }
.ss-has-help { cursor:help; }
.ss-help-tooltip { display:none; position:absolute; z-index:60; width:320rem; padding:9rem 11rem; border:1rem solid {{colors.confirmation_border}}; border-radius:{{radii.control}}rem; background:{{colors.window_background}}; color:{{colors.body_text}}; font-family:Warhelios, Arial, sans-serif; font-size:12rem; line-height:17rem; white-space:pre-line; overflow:hidden; box-shadow:0 3rem 14rem {{colors.title_text_shadow}}, inset 0 1rem {{colors.button_shadow_2}}; pointer-events:none; }
.ss-info-button { display:flex; align-items:center; justify-content:center; flex:0 0 14rem; min-width:14rem; width:14rem; height:14rem; padding:0; margin:0 0 0 5rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.window}}rem; color:{{colors.period_text}}; background:{{colors.window_background}}; font-family:Arial, sans-serif; font-size:11rem; font-style:italic; font-weight:bold; line-height:12rem; cursor:help; }
.ss-info-button:hover, .ss-info-button:focus, .ss-info-button[aria-expanded="true"] { outline:none; color:{{colors.button_hover_text}}; border-color:{{colors.button_shadow_1}}; background:{{colors.table_row_hover_background}}; box-shadow:0 0 4rem {{colors.button_shadow_2}}; }
.ss-info-symbol { display:block; width:100%; font:inherit; text-align:center; }
.ss-summary .ss-kpi-label { display:flex; align-items:center; justify-content:center; }
.ss-summary .ss-detail-title { display:flex; align-items:center; }
.ss-wn8-coverage { margin-left:10rem; color:{{colors.coverage_notice_text}}; font-size:12rem; white-space:nowrap; }
.ss-timeline { position:relative; z-index:21; display:flex; flex-wrap:wrap; align-items:center; flex:0 1 452rem; min-width:0; width:452rem; max-width:100%; margin:0 8rem 4rem 0; padding:0; }
.ss-timeline-field { display:flex; flex:1 1 200rem; min-width:0; max-width:222rem; align-items:center; color:{{colors.table_header_text}}; }
.ss-timeline-field:first-child { margin-right:8rem; }
.ss-timeline-field > span { flex-shrink:0; margin-right:6rem; }
.ss-timeline-field .ss-select { flex:1 1 0rem; width:0; }
.ss-timeline-field .ss-select-options { width:100%; min-width:0; max-height:200rem; overflow-y:auto; }
.ss-more-button { margin-left:7rem; }
.ss-more-panel { display:flex; flex-wrap:wrap; align-items:flex-start; padding:5rem 0 2rem; border-top:1rem solid {{colors.group_tabs_border_bottom}}; font-size:13rem; line-height:18rem; overflow-wrap:break-word; }
.ss-more-panel > p { width:100%; margin:3rem 5rem; }
.ss-more-title { margin:4rem 5rem; color:{{colors.session_tab_active_text}}; font-size:13rem; line-height:18rem; }
.ss-more-mission { display:flex; align-items:center; width:100%; padding:5rem 7rem; border-top:1rem solid {{colors.details_separator_border_top}}; }
.ss-more-caption { color:{{colors.period_text}}; font-size:12rem; }
.ss-resize-grip { position:absolute; z-index:31; right:0; bottom:0; width:16rem; height:16rem; padding:0; border:0; background:{{colors.close_background}}; color:{{colors.period_text}}; cursor:nwse-resize; touch-action:none; }
.ss-resize-grip::before { content:""; display:block; margin:5rem 3rem 3rem 5rem; width:9rem; height:9rem; border-right:2rem solid currentColor; border-bottom:2rem solid currentColor; }
.ss-resize-grip:focus, .ss-resize-grip:hover { color:{{colors.session_tab_active_text}}; }
.ss-resize-nw { top:0; left:0; right:auto; bottom:auto; transform:rotate(180deg); }
.ss-resize-ne { top:0; bottom:auto; transform:rotate(-90deg); cursor:nesw-resize; }
.ss-resize-sw { left:0; right:auto; transform:rotate(90deg); cursor:nesw-resize; }
.ss-resize-edge::before { display:none; }
.ss-resize-n, .ss-resize-s { left:16rem; right:16rem; width:auto; height:6rem; cursor:ns-resize; }
.ss-resize-n { top:0; bottom:auto; }
.ss-resize-e, .ss-resize-w { top:16rem; bottom:16rem; width:6rem; height:auto; cursor:ew-resize; }
.ss-resize-w { left:0; right:auto; }
.ss-more-rewards { display:flex; flex-wrap:wrap; align-items:flex-start; flex:1 1 240rem; min-width:0; }
.ss-more-mission-block { flex:1 1 310rem; min-width:0; padding:0 4rem 4rem; }
.ss-more-reward-block { flex:1 1 220rem; min-width:0; padding:0 4rem 4rem; }
.ss-more-table { display:block; width:100%; margin:0; border:1rem solid {{colors.details_separator_border_top}}; border-radius:{{radii.table_row}}rem; background:{{colors.table_row_background}}; }
.ss-more-table .ss-more-body { display:block; width:100%; }
.ss-more-table .ss-more-label, .ss-more-table .ss-more-amount { display:block; min-width:0; padding:0; vertical-align:top; }
.ss-more-value { display:flex; align-items:center; width:100%; min-height:24rem; padding:3rem 7rem; border-bottom:1rem solid {{colors.details_separator_border_top}}; }
.ss-more-value .ss-more-label { flex:1 1 0rem; padding-right:10rem; text-align:left; font-weight:normal; color:{{colors.metric_label_text}}; }
.ss-more-value .ss-more-amount { flex:0 1 46%; text-align:right; color:{{colors.metric_value_text}}; }
.ss-more-value .ss-more-amount.ss-more-total { flex:1; text-align:left; color:{{colors.session_tab_active_text}}; font-weight:bold; }
.ss-more-value:last-child { border-bottom:0; }
.ss-more-value:nth-child(even) { background:{{colors.table_row_following_background}}; }
.ss-more-mission:first-child { border-top:0; }
.ss-more-mission:nth-child(even) { background:{{colors.table_row_following_background}}; }
.ss-more-table .ss-more-mission-name { flex:1 1 0rem; min-width:0; padding-right:12rem; }
.ss-more-table .ss-more-mission-status { flex:0 0 36%; min-width:0; padding-left:8rem; color:{{colors.metric_value_text}}; }
.ss-more-mission-description { width:100%; margin-top:3rem; }
.ss-more-reward-block.ss-more-bonus-block { flex-basis:100%; }
.ss-bonus-matrix { width:100%; }
.ss-bonus-row { display:flex; align-items:center; width:100%; min-height:25rem; padding:3rem 7rem; border-top:1rem solid {{colors.details_separator_border_top}}; }
.ss-bonus-row:first-child { border-top:0; }
.ss-bonus-row:nth-child(even) { background:{{colors.table_row_following_background}}; }
.ss-bonus-label { display:block; flex:0 0 30%; min-width:0; padding-right:8rem; color:{{colors.metric_label_text}}; }
.ss-bonus-number { display:block; flex:1 1 0rem; min-width:0; padding-left:4rem; color:{{colors.metric_value_text}}; text-align:right; white-space:nowrap; }
.ss-bonus-head { min-height:23rem; background:{{colors.table_header_background_start}}; }
.ss-bonus-head .ss-bonus-label, .ss-bonus-head .ss-bonus-number { color:{{colors.table_header_cell_text}}; font-size:11rem; }
.ss-bonus-head .ss-bonus-number { white-space:normal; }
.ss-narrow-cards .ss-bonus-row { flex-wrap:wrap; }
.ss-narrow-cards .ss-bonus-label { flex-basis:100%; width:100%; padding:0 0 2rem; }
.ss-narrow-cards .ss-bonus-head .ss-bonus-label { display:none; }
/* Cards respond to their own configured/available width, independently of the
   full game viewport. Keep complete numbers at the regular reading size. */
.ss-group .ss-details { flex-direction:row; flex-wrap:wrap; }
.ss-group .ss-performance { flex:1 1 260rem; min-width:0; width:auto; }
.ss-group .ss-economy { flex:1 1 310rem; min-width:0; width:auto; }
.ss-narrow-cards .ss-group .ss-performance, .ss-narrow-cards .ss-group .ss-economy { flex-basis:100%; }
.ss-narrow-cards .ss-group .ss-performance { padding-right:0; }
.ss-narrow-cards .ss-group .ss-economy { padding:5rem 0 0; margin-top:3rem; border-left:0; border-top:1rem solid {{colors.details_separator_border_top}}; }
.ss-narrow-cards .ss-group .ss-metric-head, .ss-narrow-cards .ss-group .ss-metric-row, .ss-narrow-cards .ss-group .ss-money-head, .ss-narrow-cards .ss-group .ss-money-row { flex-wrap:wrap; }
.ss-narrow-cards .ss-group .ss-metric-head .ss-metric-name, .ss-narrow-cards .ss-group .ss-money-head .ss-money-label { display:none; }
.ss-narrow-cards .ss-group .ss-metric-head .ss-metric-count { display:block; width:100%; padding:0 4rem; }
.ss-narrow-cards .ss-group .ss-metric-row .ss-metric-name, .ss-narrow-cards .ss-group .ss-money-row .ss-money-label { width:100%; padding-bottom:0; }
.ss-narrow-cards .ss-group .ss-metric-number, .ss-narrow-cards .ss-group .ss-money-value { width:33.333%; }
/* Fixed-width cards use two independent flow columns. Layout never depends on
   reading a just-created card's height from Gameface. */
.ss-card-layout { display:flex; align-items:flex-start; justify-content:center; width:100%; }
.ss-card-columns { position:relative; display:flex; align-items:flex-start; flex:0 1 620rem; min-width:0; width:620rem; max-width:100%; }
.ss-card-column { display:flex; flex-direction:column; flex:1 1 0rem; min-width:0; width:620rem; }
.ss-card-column-right { display:none; }
.ss-card-layout .ss-group { position:relative; flex:0 0 auto; width:100%; margin-bottom:16rem; }
.ss-two-columns .ss-card-columns { flex-basis:1304rem; width:1304rem; }
.ss-two-columns .ss-card-column { flex:0 0 620rem; }
.ss-two-columns .ss-card-column-right { display:flex; margin-left:64rem; }
.ss-battle-stream .ss-card-column-left { padding-top:16rem; }
.ss-battle-stream .ss-card-column-right { padding-top:68rem; }
.ss-battle-stream .ss-card-columns:before { content:""; position:absolute; top:9rem; bottom:12rem; left:50%; width:1rem; background-image:linear-gradient({{colors.button_shadow_1}} 50%, {{colors.body_background}} 50%); background-size:1rem 10rem; background-repeat:repeat-y; pointer-events:none; }
.ss-battle-stream .ss-card-columns:after { content:""; position:absolute; left:50%; top:2rem; width:8rem; height:8rem; margin-left:-4rem; border-left:1rem solid {{colors.button_shadow_1}}; border-top:1rem solid {{colors.button_shadow_1}}; transform:rotate(45deg); pointer-events:none; }
.ss-battle-stream .ss-battle:before { content:""; position:absolute; right:-32rem; top:24rem; width:32rem; height:1rem; background-image:linear-gradient(to right, {{colors.button_shadow_1}} 50%, {{colors.body_background}} 50%); background-size:10rem 1rem; background-repeat:repeat-x; pointer-events:none; }
.ss-battle-stream .ss-battle:after { content:""; position:absolute; right:-36rem; top:20rem; width:7rem; height:7rem; border:1rem solid {{colors.button_shadow_1}}; border-radius:{{radii.control}}rem; background:{{colors.window_background}}; pointer-events:none; }
.ss-battle-stream .ss-card-column-right .ss-battle:before { left:-32rem; right:auto; }
.ss-battle-stream .ss-card-column-right .ss-battle:after { left:-36rem; right:auto; }
@media (max-width:480px) {
  .ss-title-actions { flex:1 1 100%; width:100%; }
  .ss-language-row { margin-left:auto; margin-top:0; }
  .ss-time-point-controls { margin-right:0; }
}
'''

FOOTER_TEMPLATE = '''/* Own compact icon in LobbyFooter. All dimensions follow the native rem scale. */
.grz-session-footer-button {
    position:relative;
    display:block;
    flex:0 0 44rem;
    box-sizing:border-box;
    width:44rem;
    min-width:44rem;
    max-width:44rem;
    height:36rem;
    padding:0;
    margin:0 3rem;
    border:0;
    background:{{colors.garage_button_background}};
    box-shadow:none;
    color:{{colors.garage_button_text}};
    font-family:Warhelios, Arial, sans-serif;
    font-size:12rem;
    line-height:12rem;
    cursor:pointer;
}
.grz-session-footer-button:hover { background:{{colors.garage_button_hover_background}}; color:{{colors.garage_button_hover_text}}; }
.grz-session-footer-button:focus { outline:1rem solid {{colors.garage_button_focus_outline}}; outline-offset:-2rem; }
.grz-session-footer-button:disabled { opacity:{{opacity.disabled_controls}}; }
.grz-session-footer-button .grz-session-footer-icon {
    position:absolute;
    display:block;
    left:8rem;
    bottom:5rem;
    width:18rem;
    height:18rem;
    pointer-events:none;
}
.grz-session-footer-button .grz-session-footer-bar {
    position:absolute;
    bottom:0;
    display:block;
    width:4rem;
    /* Gameface does not support currentColor as a background color. */
    background-color:{{colors.garage_bars_background}};
}
.grz-session-footer-button:hover .grz-session-footer-bar { background-color:{{colors.garage_bars_hover_background}}; }
.grz-session-footer-button .grz-session-footer-bar-0 { left:0; height:9rem; }
.grz-session-footer-button .grz-session-footer-bar-1 { left:6rem; height:13rem; }
.grz-session-footer-button .grz-session-footer-bar-2 { left:12rem; height:18rem; }
.grz-session-footer-button .grz-session-footer-rating {
    position:absolute;
    top:1rem;
    right:1rem;
    display:block;
    width:22rem;
    margin:0;
    color:{{colors.garage_wn8_text}};
    font-family:Warhelios, Arial, sans-serif;
    font-size:9rem;
    font-weight:normal;
    line-height:11rem;
    letter-spacing:0;
    text-align:center;
    white-space:nowrap;
    text-shadow:0 1rem 1rem {{colors.garage_wn8_text_shadow}};
    pointer-events:none;
}
.grz-session-footer-button:hover .grz-session-footer-rating { color:{{colors.garage_wn8_hover_text}}; }

/* CSS animation stays inside the renderer; no Python/JS frame callbacks.
   Fits above the bars and left of WN8 inside the existing 44 x 36 button. */
.grz-session-footer-button .grz-session-footer-spinner {
    position:absolute;
    display:none;
    box-sizing:border-box;
    left:10rem;
    top:2rem;
    width:10rem;
    height:10rem;
    border:2rem solid {{colors.garage_spinner_border}};
    border-top-color:{{colors.garage_spinner_border_top_color}};
    border-radius:{{radii.garage_spinner}}rem;
    pointer-events:none;
    animation:none;
}
.grz-session-footer-busy .grz-session-footer-spinner {
    display:block;
    animation:grz-session-footer-spin 1s linear infinite;
}
@keyframes grz-session-footer-spin {
    from { transform:rotate(0deg); }
    to { transform:rotate(360deg); }
}
'''

PANEL_OPACITY_RULE = '\n.ss-window { opacity:{{opacity.window}}; }\n'
FOOTER_OPACITY_RULE = '\n.grz-session-footer-button { opacity:{{opacity.garage_button}}; }\n'


def default_config():
    """Return independent defaults; caller changes never alter the fallback."""
    return copy.deepcopy(DEFAULT_CONFIG)


class _Reporter(object):
    def __init__(self):
        self.count = 0
        self.omitted = False

    def issue(self, path, reason):
        # Only schema labels and fixed reason codes are diagnostic data.
        if self.count >= MAX_DIAGNOSTICS:
            if not self.omitted:
                LOG.warning('CONFIG additional invalid fields omitted after %s diagnostics.',
                            MAX_DIAGNOSTICS)
                self.omitted = True
            return
        self.count += 1
        LOG.warning('CONFIG field=%s reason=%s; using the default or ignoring an unknown field.',
                    path, reason)


def _key_label(value):
    if not isinstance(value, (text_type, bytes)):
        return '<non_text_key>'
    if isinstance(value, bytes) and not isinstance(value, text_type):
        value = value.decode('utf-8', 'replace')
    return re.sub(r'[^a-zA-Z0-9_.-]', '?', value[:80]) or '<empty_key>'


def _number(value, lower, upper):
    if isinstance(value, bool) or not isinstance(value, NUMBER_TYPES):
        return None
    try:
        converted = float(value)
        if math.isnan(converted) or math.isinf(converted) or not lower <= converted <= upper:
            return None
        return converted
    except (ValueError, TypeError, OverflowError):
        return None


def _css_number(value):
    # Inputs have already passed finite numeric bounds. Avoid locale/exponents
    # and preserve the integer/default spellings used by the static stylesheet.
    return ('%.8f' % value).rstrip('0').rstrip('.') or '0'


_HEX_COLOR = re.compile(r'\A#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\Z')
_RGB_COLOR = re.compile(
    r'\Argb(?P<alpha>a?)\(\s*(?P<r>[0-9]{1,3})\s*,\s*(?P<g>[0-9]{1,3})'
    r'\s*,\s*(?P<b>[0-9]{1,3})(?:\s*,\s*(?P<a>(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)))?\s*\)\Z',
    re.I)


def _color(value):
    if not isinstance(value, (text_type, bytes)):
        return None
    if isinstance(value, bytes) and not isinstance(value, text_type):
        try:
            value = value.decode('ascii')
        except UnicodeError:
            return None
    if len(value) > 96 or any(c in value for c in ('\n', '\r', '\x00')):
        return None
    value = value.strip().lower()
    if value == 'transparent':
        return value
    if _HEX_COLOR.match(value):
        if len(value) == 9:
            channels = [int(value[index:index + 2], 16) for index in (1, 3, 5, 7)]
            return 'rgba(%d,%d,%d,%s)' % tuple(channels[:3] + [_css_number(channels[3] / 255.0)])
        return value
    match = _RGB_COLOR.match(value)
    if match is None:
        return None
    channels = [int(match.group(name)) for name in ('r', 'g', 'b')]
    if any(channel > 255 for channel in channels):
        return None
    has_alpha = bool(match.group('alpha'))
    if has_alpha != (match.group('a') is not None):
        return None
    if has_alpha:
        alpha = _number(float(match.group('a')), 0, 1)
        if alpha is None:
            return None
        return 'rgba(%d,%d,%d,%s)' % tuple(channels + [_css_number(alpha)])
    return 'rgb(%d,%d,%d)' % tuple(channels)


def validate_config(raw):
    """Normalize a partial object; independent invalid leaves use defaults."""
    result = default_config()
    reporter = _Reporter()
    if not isinstance(raw, dict):
        reporter.issue('$', 'expected_object')
        return result
    version = raw.get('schema_version', SCHEMA_VERSION)
    if (isinstance(version, bool) or not isinstance(version, integer_types) or
            version != SCHEMA_VERSION):
        reporter.issue('schema_version', 'unsupported_schema')
        return result
    for key in raw:
        if key not in result:
            reporter.issue(_key_label(key), 'unknown_field')
    if 'language' in raw:
        from .localization import LANGUAGE
        value = raw['language']
        if isinstance(value, text_type) and (value == 'auto' or LANGUAGE.match(value)):
            result['language'] = value
        else:
            reporter.issue('language', 'expected_language_code')
    for section in ('colors', 'radii', 'opacity', 'scroll', 'sessions', 'cards'):
        if section not in raw:
            continue
        supplied = raw[section]
        if not isinstance(supplied, dict):
            reporter.issue(section, 'expected_object')
            continue
        for key in supplied:
            if key not in result[section]:
                reporter.issue(section + '.' + _key_label(key), 'unknown_field')
        for key in sorted(result[section]):
            if key not in supplied:
                continue
            value = supplied[key]
            if section == 'sessions':
                checked = value if isinstance(value, bool) else None
                reason = 'expected_boolean'
            elif section == 'cards':
                checked = _number(value, 480, 900)
                reason = 'expected_number_480_to_900'
            elif section == 'colors':
                checked = _color(value)
                reason = 'expected_supported_color'
            elif section == 'radii':
                checked = _number(value, 0, 24)
                reason = 'expected_number_0_to_24'
            elif section == 'opacity':
                checked = _number(value, 0, 1)
                reason = 'expected_number_0_to_1'
            else:
                checked = _number(value, 0.1, 8)
                reason = 'expected_number_0.1_to_8'
            if checked is None:
                reporter.issue(section + '.' + key, reason)
            else:
                result[section][key] = checked
    return result


class _InvalidJSON(ValueError):
    pass


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidJSON('duplicate_key')
        result[key] = value
    return result


def _reject_constant(unused):
    raise _InvalidJSON('non_finite_constant')


def load_config(path):
    """Read bounded UTF-8 JSON; malformed files restore the entire baseline."""
    if path is None:
        return default_config()
    try:
        with io.open(path, 'rb') as source:
            raw = source.read(MAX_CONFIG_BYTES + 1)
    except (IOError, OSError) as error:
        if error.errno == errno.ENOENT:
            LOG.info('CONFIG file missing; using the built-in appearance defaults.')
        else:
            LOG.warning('CONFIG file read failed (%s); using the built-in appearance defaults.',
                        type(error).__name__)
        return default_config()
    except Exception as error:
        LOG.warning('CONFIG file read failed (%s); using the built-in appearance defaults.',
                    type(error).__name__)
        return default_config()
    if len(raw) > MAX_CONFIG_BYTES:
        LOG.warning('CONFIG file exceeds %s bytes; using the built-in appearance defaults.',
                    MAX_CONFIG_BYTES)
        return default_config()
    try:
        text = raw.decode('utf-8-sig')
        parsed = json.loads(text, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
    except Exception as error:
        # json exception text may echo the user's file. Keep class and location.
        line, column = getattr(error, 'lineno', None), getattr(error, 'colno', None)
        if line is None and column is None and isinstance(error, ValueError):
            # CPython 2.7 exposes only ValueError text. Extract its fixed numeric
            # suffix; neither the message nor any source excerpt enters the log.
            message = error.args[0] if error.args else None
            if isinstance(message, bytes) and not isinstance(message, text_type):
                message = message.decode('utf-8', 'replace')
            location = (re.search(r'\bline ([0-9]+) column ([0-9]+) \(char [0-9]+\)\Z', message)
                        if isinstance(message, text_type) else None)
            if location is not None:
                line, column = (int(value) for value in location.groups())
        if isinstance(error, _InvalidJSON):
            reason = str(error)
        elif isinstance(error, UnicodeError):
            reason = 'invalid_utf8'
        else:
            reason = 'invalid_json'
        LOG.warning('CONFIG parse failed reason=%s line=%s column=%s; using the built-in appearance defaults.',
                    reason, line, column)
        return default_config()
    return validate_config(parsed)


_TOKEN = re.compile(r'\{\{(colors|radii|opacity)\.([a-z0-9_]+)\}\}')


def _expand(template, config):
    def replace(match):
        section, key = match.groups()
        value = config[section][key]
        return value if section == 'colors' else _css_number(value)
    return _TOKEN.sub(replace, template)


def build_presentation(config):
    """Render only trusted selectors/declarations with validated scalar leaves."""
    normalized = validate_config(config)
    return {
        'panel_css': _expand(PANEL_TEMPLATE + PANEL_OPACITY_RULE, normalized),
        'footer_css': _expand(FOOTER_TEMPLATE + FOOTER_OPACITY_RULE, normalized),
        'scroll_speed': normalized['scroll']['speed_multiplier'],
        'card_widths': copy.deepcopy(normalized['cards']),
    }

