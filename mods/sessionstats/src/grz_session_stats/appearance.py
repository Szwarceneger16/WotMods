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
 'date_time': {'order': 'auto', 'separator': 'auto', 'hour_format': 'auto', 'first_weekday': 'auto'},
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
            'sort_active_background': '#252a23',
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
            'date_unavailable_text': '#969c96',
            'date_unavailable_border': '#464c46',
            'date_unavailable_background': '#2b302b',
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
            'garage_spinner_border': 'rgba(150,154,157,0.25)',
            'garage_spinner_border_top_color': '#969a9d',
            'loading_scrim_background': 'rgba(17,19,9,0.45)'},
 'radii': {'window': 8,
           'titlebar': 7,
           'control': 5,
           'sort_switch_track': 15,
           'sort_switch_thumb': 8,
           'scrollbar_thumb': 3,
           'table_header': 5,
           'table_row': 4,
           'battle_measure': 5,
           'group_tabs': 5,
           'group_card': 7,
           'battle_outcome': 5,
           'panel_footer': 7,
           'confirmation': 8,
           'garage_spinner': 8},
 'opacity': {'window': 1.0, 'garage_button': 1.0, 'disabled_controls': 0.45, 'target_dimmed': 0.7, 'date_unavailable': 1.0},
 'scroll': {'speed_multiplier': 1.0},
 'maps': {'preview_mode': 'image'},
 'cards': {'battles': 500, 'vehicles': 560, 'maps': 560, 'tiers': 520},
 'wide_cards': {'battles': 720, 'vehicles': 720, 'maps': 720, 'tiers': 720},
 'window': {'background_transparency': 0, 'maximized': False,
            'restored_width': 700, 'restored_height': 620},
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
/* Center actual strokes, not a font-dependent multiplication-sign baseline. */
.ss-close .ss-control-label { position:absolute; left:50%; top:50%; width:14rem; height:14rem; margin:-7rem 0 0 -7rem; font-size:0; line-height:0; }
/* Gameface rejects currentColor backgrounds; keep stroke paint explicit. */
.ss-close .ss-control-label:before, .ss-close .ss-control-label:after { content:""; display:block; position:absolute; left:0; top:6rem; width:14rem; height:2rem; background:{{colors.close_text}}; pointer-events:none; }
.ss-close:hover .ss-control-label:before, .ss-close:hover .ss-control-label:after, .ss-close:focus .ss-control-label:before, .ss-close:focus .ss-control-label:after { background:{{colors.close_hover_text}}; }
.ss-close .ss-control-label:before { transform:rotate(45deg); }
.ss-close .ss-control-label:after { transform:rotate(-45deg); }
button:disabled { opacity:{{opacity.disabled_controls}}; }
.ss-window { position:relative; display:flex; flex-direction:column; width:700rem; height:730rem; max-width:100%; max-height:100%; min-width:550rem; min-height:730rem; border:1rem solid {{colors.window_border}}; border-radius:{{radii.window}}rem; }
.ss-window-background { position:absolute; z-index:0; top:0; right:0; bottom:0; left:0; border-radius:{{radii.window}}rem; background:{{colors.window_background}}; background-image:url("session_stats_camo.png"); background-size:560rem 460rem; background-repeat:repeat; box-shadow:inset 0 1rem 1rem {{colors.window_shadow_1}}, inset 0 0 28rem {{colors.window_shadow_2}}; pointer-events:none; }
/* Positioned flow children paint above the dedicated background without
   creating new stacking contexts for their existing menus and tooltips. */
.ss-controls, .ss-scroll, .ss-footer { position:relative; }
.ss-window.is-native { max-width:none; max-height:none; }
.ss-titlebar { position:relative; z-index:30; display:flex; flex-wrap:wrap; align-items:center; flex-shrink:0; min-height:47rem; padding:6rem 74rem 7rem 13rem; border-radius:{{radii.titlebar}}rem {{radii.titlebar}}rem 0 0; background:linear-gradient({{colors.titlebar_background_start}}, {{colors.titlebar_background_end}}); box-shadow:inset 0 1rem {{colors.session_tab_shadow}}, inset 0 -1rem {{colors.session_tabs_border}}; }
.ss-title-identity { display:flex; align-items:center; flex:1 0 220rem; min-width:0; max-width:100%; min-height:32rem; }
/* Let the complete action group use its intrinsic width. Wide windows keep
   every control on the title row; smaller windows wrap the existing groups. */
.ss-title-actions { display:flex; align-items:center; justify-content:flex-end; flex-wrap:wrap; flex:0 1 auto; width:auto; max-width:100%; min-width:0; margin-left:auto; }
.ss-titlebar h1 { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:22rem; line-height:26rem; margin:0; font-weight:bold; color:{{colors.title_text}}; text-shadow:0 1rem 2rem {{colors.title_text_shadow}}; }
.ss-game-mode { display:block; flex-shrink:0; white-space:nowrap; color:{{colors.game_mode_text}}; font-size:12rem; margin-left:12rem; }
.ss-close, .ss-window-toggle { position:absolute; top:6rem; right:9rem; border:0; background:{{colors.close_background}}; color:{{colors.close_text}}; width:27rem; height:30rem; margin:0; padding:0; font-size:25rem; border-radius:{{radii.control}}rem; }
.ss-close:hover, .ss-close:focus, .ss-window-toggle:hover, .ss-window-toggle:focus { color:{{colors.close_hover_text}}; background:{{colors.group_tab_hover_background}}; }
.ss-window-toggle { right:38rem; }
.ss-window-toggle-symbol { display:block; position:absolute; left:50%; top:50%; width:16rem; height:14rem; margin:-7rem 0 0 -8rem; pointer-events:none; }
.ss-window-toggle-symbol:before, .ss-window-toggle-symbol:after { content:""; display:block; box-sizing:border-box; position:absolute; width:12rem; height:10rem; border:1rem solid currentColor; pointer-events:none; }
.ss-window-toggle-symbol:before { display:none; }
.ss-window-toggle-symbol:after { left:2rem; top:2rem; }
.ss-window-toggle[aria-pressed="true"] .ss-window-toggle-symbol:before { display:block; left:0; top:4rem; }
.ss-window-toggle[aria-pressed="true"] .ss-window-toggle-symbol:after { left:4rem; top:0; }
/* Caption and track share one compact frame, keeping the label next to its
   slider while preserving a single title row in wide windows. */
.ss-background-control { display:flex; position:relative; align-items:center; justify-content:space-between; flex:0 1 auto; min-width:146rem; max-width:100%; height:30rem; margin:0 8rem 0 0; padding:0 5rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; background:{{colors.window_background}}; box-shadow:inset 0 1rem {{colors.button_shadow_2}}; }
.ss-background-caption { display:block; position:absolute; z-index:1; left:9rem; top:1rem; width:86rem; margin:0; color:{{colors.list_meta_text}}; font-size:11rem; line-height:13rem; white-space:nowrap; pointer-events:none; }
.ss-background-slider { display:block; position:relative; flex:0 0 94rem; width:94rem; min-width:94rem; height:28rem; padding:0 4rem; cursor:pointer; touch-action:none; }
.ss-background-track { display:block; position:absolute; left:4rem; right:4rem; bottom:5rem; height:4rem; border-radius:{{radii.control}}rem; background:{{colors.button_border}}; box-shadow:inset 0 1rem {{colors.button_shadow_2}}; pointer-events:none; }
.ss-background-thumb { display:block; position:absolute; left:0; top:50%; width:8rem; height:12rem; margin:-6rem 0 0 -4rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; background:linear-gradient({{colors.button_background_start}}, {{colors.button_background_end}}); box-shadow:0 1rem 3rem {{colors.title_text_shadow}}; pointer-events:none; }
.ss-background-slider:focus { outline:1rem solid {{colors.garage_button_focus_outline}}; outline-offset:-1rem; }
.ss-background-slider:hover .ss-background-thumb, .ss-background-slider:focus .ss-background-thumb { border-color:{{colors.button_shadow_1}}; background:linear-gradient({{colors.button_hover_background_start}}, {{colors.button_hover_background_end}}); }
.ss-background-value { display:block; flex:0 0 38rem; width:38rem; color:{{colors.list_meta_text}}; font-size:14rem; line-height:18rem; text-align:right; }
.ss-controls { padding:0 12rem 4rem; flex-shrink:0; }
.ss-scopes { display:flex; flex:0 1 260rem; min-width:0; width:260rem; max-width:100%; margin:0 8rem 4rem 0; border:1rem solid {{colors.session_tabs_border}}; border-radius:{{radii.control}}rem; }
.ss-scope { position:relative; flex:1 1 auto; min-width:0; width:auto; height:28rem; border:0; background:linear-gradient({{colors.session_tab_background_start}}, {{colors.session_tab_background_middle}} 58%, {{colors.session_tab_background_end}}); color:{{colors.session_tab_text}}; padding:4rem 6rem; border-radius:{{radii.control}}rem; box-shadow:inset 0 1rem {{colors.session_tab_shadow}}; }
.ss-scope + .ss-scope { border-left:1rem solid {{colors.session_tab_separator_border_left}}; }
.ss-scope:hover, .ss-scope:focus { color:{{colors.session_tab_hover_text}}; box-shadow:inset 0 1rem {{colors.button_shadow_1}}, inset 0 0 5rem {{colors.button_shadow_2}}; }
.ss-scope.is-active { color:{{colors.session_tab_active_text}}; background:linear-gradient({{colors.session_tab_active_background_start}}, {{colors.session_tab_active_background_middle}} 56%, {{colors.session_tab_active_background_end}}); text-shadow:0 0 7rem {{colors.session_tab_active_text_shadow}}; }
.ss-scope.is-active:after { content:""; position:absolute; left:50%; bottom:-3rem; width:5rem; height:5rem; background:{{colors.session_tab_marker_background}}; border-right:1rem solid {{colors.session_tab_marker_border_right}}; border-bottom:1rem solid {{colors.session_tab_marker_border_bottom}}; transform:rotate(45deg); }
.ss-toolbar { display:flex; flex-wrap:wrap; align-items:flex-start; justify-content:center; min-height:37rem; padding-top:4rem; }
.ss-period { display:block; flex:0 1 184rem; min-width:0; width:184rem; max-width:100%; font-size:12rem; color:{{colors.period_text}}; margin:0 8rem 4rem 0; }
.ss-xp-picker { display:flex; flex:0 0 auto; min-width:212rem; width:auto; max-width:100%; margin-bottom:4rem; border:1rem solid {{colors.xp_picker_border}}; border-radius:{{radii.control}}rem; }
.ss-small-toggle { flex:1 0 auto; min-width:98rem; width:auto; height:28rem; min-height:28rem; border:0; background:{{colors.xp_toggle_background}}; color:{{colors.xp_toggle_text}}; font-size:12rem; padding:3rem 7rem; border-radius:{{radii.control}}rem; box-shadow:inset 0 1rem {{colors.button_shadow_2}}; }
#ss-xp-received { min-width:112rem; }
.ss-small-toggle.is-active { background:linear-gradient({{colors.xp_toggle_active_background_start}}, {{colors.xp_toggle_active_background_end}}); color:{{colors.xp_toggle_active_text}}; box-shadow:inset 0 1rem {{colors.xp_toggle_active_shadow}}; }
.ss-small-toggle:hover, .ss-small-toggle:focus { color:{{colors.xp_toggle_hover_text}}; box-shadow:inset 0 1rem {{colors.button_shadow_1}}, inset 0 0 5rem {{colors.button_shadow_2}}; }
/* Gameface may omit native scrollbar paint. Reserve an owned visible rail. */
.ss-scroll { flex:1; min-height:0; overflow-y:scroll; overflow-x:hidden; padding:0 24rem 10rem 12rem; }
.ss-scroll::-webkit-scrollbar { width:0; }
.ss-scrollbar { display:block; position:absolute; z-index:26; right:8rem; width:10rem; min-width:10rem; border:1rem solid {{colors.scrollbar_thumb_border}}; border-radius:{{radii.scrollbar_thumb}}rem; background:{{colors.scrollbar_track_background}}; cursor:pointer; touch-action:none; }
.ss-scrollbar:focus { outline:1rem solid {{colors.session_tab_marker_background}}; outline-offset:1rem; }
.ss-scrollbar[aria-disabled="true"] { opacity:{{opacity.disabled_controls}}; cursor:default; }
.ss-scrollbar-thumb { display:block; position:absolute; top:0; left:0; right:0; min-height:1rem; border:1rem solid {{colors.scrollbar_thumb_border}}; border-radius:{{radii.scrollbar_thumb}}rem; background:{{colors.scrollbar_thumb_background}}; cursor:pointer; }
.ss-scrollbar.is-dragging .ss-scrollbar-thumb, .ss-scrollbar:hover .ss-scrollbar-thumb { border-color:{{colors.session_tab_marker_background}}; }
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
/* Keep the three headline values horizontal. The two detail tables move as
   one unit and only split when their own parent cannot fit both tables. */
.ss-summary-layout.ss-details { flex-direction:row; flex-wrap:wrap; align-items:flex-start; justify-content:center; padding:0; border:0; }
.ss-summary-main { flex:0 1 460rem; width:460rem; max-width:100%; min-width:0; padding:0 6rem; margin:0 0 8rem; }
.ss-summary-details { display:flex; flex-wrap:wrap; align-items:flex-start; justify-content:center; flex:0 1 650rem; width:650rem; max-width:100%; min-width:0; }
.ss-summary-details > .ss-performance { flex:0 1 300rem; width:300rem; max-width:100%; min-width:0; padding:4rem 12rem 0 0; margin:0 0 8rem; }
.ss-summary-details > .ss-economy { flex:0 1 350rem; width:350rem; max-width:100%; min-width:0; padding:4rem 0 0; margin:0 0 8rem; border:0; }
.ss-summary-wrap .ss-summary-layout { flex-direction:column; align-items:center; }
.ss-summary-wrap .ss-summary-main, .ss-summary-wrap .ss-summary-details { flex-basis:auto; }
.ss-summary-stacked .ss-summary-details { flex-direction:column; align-items:center; }
.ss-summary-stacked .ss-summary-details > .ss-performance, .ss-summary-stacked .ss-summary-details > .ss-economy { flex-basis:auto; }
.ss-summary-stacked .ss-summary-details > .ss-performance { padding-right:0; }
.ss-summary-main .ss-headline { display:flex; align-items:flex-start; padding:0 0 4rem; }
.ss-summary-main .ss-kpi { flex:1 1 0rem; min-width:0; }
.ss-summary-main .ss-kpi-label { min-height:34rem; text-align:center; }
.ss-summary-main .ss-kpi-value { min-width:0; max-width:100%; text-align:center; }
.ss-summary-main .ss-outcomes { justify-content:center; margin:0 4rem 4rem; }
.ss-summary-main .ss-summary-meta { justify-content:center; margin:0 4rem; }
.ss-summary-details .ss-money-head, .ss-summary-details .ss-money-row { flex-wrap:nowrap; }
.ss-summary-details .ss-money-label { display:block; width:23%; }
.ss-summary-details .ss-money-value { width:25.666%; font-size:14rem; }
.ss-summary-details .ss-money-head .ss-money-value { font-size:12rem; }
/* Reclaim label insets for the permanently visible Received XP row. */
.ss-summary-details .ss-metric-name { padding-left:1rem; padding-right:0; }
.ss-narrow-summary .ss-money-head, .ss-narrow-summary .ss-money-row { flex-wrap:wrap; }
.ss-narrow-summary .ss-money-head .ss-money-label { display:none; }
.ss-narrow-summary .ss-money-head .ss-money-count { display:block; width:100%; padding:0 4rem; }
.ss-narrow-summary .ss-money-row .ss-money-label { width:100%; padding-bottom:0; }
.ss-narrow-summary .ss-money-value { width:33.333%; }
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
/* Base and received credit totals share compact, permanent extrema actions. */
.ss-credit-extreme-actions { display:flex; align-items:center; justify-content:flex-end; min-height:18rem; width:100%; }
.ss-credit-extreme-actions > .ss-metric-battle-link { flex:0 1 50%; width:50%; min-width:0; max-width:50%; height:18rem; min-height:18rem; padding:0 1rem; font-size:11rem; line-height:16rem; }
.ss-credit-extreme-actions .ss-control-label, .ss-credit-extreme-actions .ss-metric-action-label { font-size:11rem; line-height:16rem; white-space:nowrap; }
.ss-credit-cell > .ss-cell-value { white-space:normal; overflow-wrap:break-word; }
.ss-positive { color:{{colors.positive_text}}; }
.ss-negative { color:{{colors.negative_text}}; }
.ss-unknown { color:{{colors.unknown_text}}; }
.ss-cell-value { display:block; }
.ss-battle-measure { display:flex; align-items:center; justify-content:space-between; min-height:28rem; padding:2rem 7rem; border-radius:{{radii.battle_measure}}rem; background:{{colors.battle_measure_background}}; }
.ss-battle-measure + .ss-battle-measure { margin-top:3rem; background:{{colors.battle_measure_following_background}}; }
.ss-battle-label { display:block; flex:1; min-width:0; padding-right:10rem; color:{{colors.battle_label_text}}; font-size:13rem; line-height:20rem; }
.ss-battle-value { display:block; flex-shrink:0; color:{{colors.battle_value_text}}; font-size:18rem; font-weight:bold; line-height:24rem; text-align:right; }
.ss-battle-value.ss-wn8 { color:{{colors.battle_wn8_text}}; }

.ss-coverage-note { color:{{colors.coverage_notice_text}}; font-size:12rem; line-height:16rem; padding-top:0; }
.ss-data-notices { padding:5rem 0 0; }
.ss-data-notice { color:{{colors.data_notice_text}}; font-size:13rem; line-height:18rem; margin:2rem 0 0; }
.ss-explainer { color:{{colors.explanation_text}}; font-size:12rem; margin-top:5rem; line-height:17rem; }
.ss-filter-panel { position:relative; z-index:20; width:100%; }
.ss-filter-panel.is-pinned { background:{{colors.window_background}}; box-shadow:0 5rem 8rem {{colors.title_text_shadow}}, inset 0 -1rem {{colors.group_tabs_border_bottom}}; }
.ss-group-tabs { display:flex; min-height:30rem; border-top:1rem solid {{colors.group_tabs_border_top}}; border-bottom:1rem solid {{colors.group_tabs_border_bottom}}; border-radius:{{radii.group_tabs}}rem {{radii.group_tabs}}rem 0 0; }
.ss-group-tab { width:25%; padding:4rem 3rem 6rem; min-height:30rem; border:0; border-radius:{{radii.control}}rem {{radii.control}}rem 0 0; background:{{colors.group_tab_background}}; color:{{colors.group_tab_text}}; font-size:14rem; }
.ss-group-tab:hover, .ss-group-tab:focus { background:{{colors.group_tab_hover_background}}; color:{{colors.group_tab_hover_text}}; }
.ss-group-tab.is-active { color:{{colors.group_tab_active_text}}; background:linear-gradient({{colors.group_tab_active_background_start}}, {{colors.group_tab_active_background_end}}); box-shadow:inset 0 -2rem {{colors.group_tab_active_shadow}}, inset 0 1rem {{colors.session_tab_shadow}}; }
.ss-list-controls { position:relative; display:flex; flex-wrap:wrap; align-items:flex-end; width:100%; padding:5rem 28rem 0 0; }
.ss-list-controls.ss-filters-wrapped { justify-content:center; padding-left:28rem; }
.ss-list-controls.ss-filters-wide { justify-content:center; }
.ss-filters-wrapped .ss-list-meta, .ss-filters-wrapped .ss-pagination, .ss-filters-wrapped .ss-sorting { margin-left:4rem; margin-right:4rem; }
.ss-filters-wrapped .ss-list-meta { justify-content:center; }
.ss-filters-wrapped .ss-sorting { flex:0 1 294rem; width:294rem; justify-content:center; }
/* The scrim covers the panel without intercepting close or range replacement.
   Blur only result content: filtering a scroll ancestor changes native pinning. */
.ss-filter-loading { display:flex; position:absolute; z-index:35; left:0; right:0; top:0; bottom:0; align-items:center; justify-content:center; overflow:hidden; border-radius:{{radii.titlebar}}rem; pointer-events:none; }
.ss-filter-loading:before { content:""; display:block; position:absolute; left:0; right:0; top:0; bottom:0; background:{{colors.loading_scrim_background}}; pointer-events:none; }
.ss-filter-loading-card { position:relative; display:flex; flex-direction:column; align-items:center; justify-content:center; max-width:90%; padding:16rem 24rem; border:1rem solid {{colors.session_tab_marker_background}}; border-radius:{{radii.titlebar}}rem; background:{{colors.window_background}}; color:{{colors.body_text}}; text-align:center; }
.ss-filter-loading .ss-page-spinner { flex-shrink:0; width:58rem; height:58rem; }
.ss-filter-loading .ss-page-spinner:before { width:44rem; height:44rem; border-width:4rem; border-radius:{{radii.garage_spinner}}em; }
.ss-filter-loading-label { display:block; max-width:260rem; margin-top:6rem; font-size:16rem; line-height:21rem; }
.ss-is-loading #ss-summary, .ss-is-loading #ss-groups { filter:blur(1.25rem); }
.ss-filters-wide .ss-list-meta { flex:0 0 150rem; width:150rem; max-width:150rem; }
.ss-filters-wide .ss-list-meta > span { white-space:nowrap; }
.ss-filters-wide .ss-pagination { flex:0 0 340rem; }
.ss-filters-wide .ss-sorting { flex:0 0 357rem; width:357rem; max-width:357rem; padding:0 5rem; border:1rem solid {{colors.details_separator_border_top}}; border-radius:{{radii.control}}rem; background:{{colors.group_card_background_end}}; }
.ss-filters-wide .ss-sort-field { flex-shrink:0; }
.ss-filters-wide .ss-sort-direction { flex-basis:109rem; }
.ss-filters-wide .ss-sort-metric { flex-basis:120rem; }
.ss-filters-wide .ss-sort-statistic { flex-basis:65rem; }
.ss-button.ss-sort-off, .ss-button.ss-sort-off.is-active { position:relative; flex:0 0 46rem; width:46rem; min-width:46rem; height:30rem; min-height:30rem; margin:0 5rem 0 0; padding:0; border:1rem solid {{colors.button_border}}; border-radius:{{radii.sort_switch_track}}rem; background:linear-gradient({{colors.button_background_start}},{{colors.button_background_middle}} 48%,{{colors.button_background_end}}); box-shadow:inset 0 1rem {{colors.button_shadow_1}}, inset 1rem 0 {{colors.button_shadow_2}}, inset -1rem 0 {{colors.button_shadow_2}}; }
.ss-button.ss-sort-off:hover, .ss-button.ss-sort-off:focus { border-color:{{colors.button_shadow_1}}; background:linear-gradient({{colors.button_hover_background_start}},{{colors.button_background_start}} 48%,{{colors.button_hover_background_end}}); }
.ss-button.ss-sort-off:active { background:linear-gradient({{colors.button_background_end}},{{colors.button_background_middle}}); }
.ss-sort-off .ss-control-label { position:absolute; width:1rem; height:1rem; padding:0; overflow:hidden; clip:rect(0, 0, 0, 0); white-space:nowrap; }
.ss-sort-switch-track { display:block; position:absolute; left:5rem; top:5rem; width:34rem; height:18rem; border:1rem solid {{colors.window_border}}; border-radius:{{radii.sort_switch_track}}rem; background:{{colors.group_card_background_end}}; box-shadow:inset 0 1rem 3rem {{colors.group_card_shadow}}; }
.ss-sort-switch-thumb { display:block; position:absolute; left:2rem; top:2rem; width:12rem; height:12rem; border:1rem solid {{colors.period_text}}; border-radius:{{radii.sort_switch_thumb}}rem; background:{{colors.list_meta_text}}; box-shadow:0 1rem 2rem {{colors.group_card_shadow}}; transition:transform 0.12s ease; }
.ss-sort-off.is-active .ss-sort-switch-track { border-color:{{colors.session_tab_marker_background}}; background:{{colors.group_card_background_start}}; }
.ss-sort-off.is-active .ss-sort-switch-thumb { transform:translateX(16rem); border-color:{{colors.session_tab_marker_background}}; background:{{colors.session_tab_marker_background}}; }
.ss-sort-off:hover .ss-sort-switch-track, .ss-sort-off:focus .ss-sort-switch-track { border-color:{{colors.group_tab_active_text}}; box-shadow:0 0 3rem {{colors.session_tab_marker_background}}; }
.ss-sort-off:disabled { opacity:{{opacity.disabled_controls}}; cursor:default; }
@media (prefers-reduced-motion:reduce) { .ss-sort-switch-thumb { transition:none; } }
.ss-list-meta { display:flex; flex-wrap:wrap; align-items:center; flex:0 1 auto; min-width:0; width:auto; max-width:100%; min-height:30rem; margin:0 8rem 5rem 0; font-size:12rem; color:{{colors.list_meta_text}}; }
.ss-list-meta > span + span { margin-left:8rem; }
.ss-group { margin-bottom:5rem; padding:5rem 6rem; border-radius:{{radii.group_card}}rem; background:linear-gradient({{colors.group_card_background_start}}, {{colors.group_card_background_end}}); border:1rem solid {{colors.group_card_shadow}}; box-shadow:inset 0 1rem {{colors.group_card_shadow}}; }
.ss-group[data-wn8-border-value] { position:relative; }
.ss-wn8-card-border { display:block; position:absolute; z-index:1; top:-1rem; right:-1rem; bottom:-1rem; left:-1rem; border:1rem solid {{colors.group_card_shadow}}; border-radius:{{radii.group_card}}rem; pointer-events:none; }
.ss-group.ss-battle-target .ss-wn8-card-border { visibility:hidden; }
.ss-group-header { display:flex; align-items:center; min-height:35rem; padding-bottom:2rem; }
.ss-group-thumb { display:block; flex-shrink:0; width:54rem; height:32rem; margin-right:8rem; background-repeat:no-repeat; background-position:center; background-size:contain; }
.ss-group-thumb[data-ss-map-preview]:focus { outline:1rem solid {{colors.session_tab_marker_background}}; outline-offset:2rem; }
.ss-map-preview { display:none; position:absolute; z-index:70; pointer-events:none; overflow:hidden; border:1rem solid {{colors.window_border}}; border-radius:{{radii.control}}rem; background:{{colors.window_background}}; box-shadow:0 3rem 10rem {{colors.group_card_shadow}}; }
.ss-map-preview-image { display:block; width:100%; height:100%; background-position:center; background-repeat:no-repeat; background-size:contain; }
.ss-group-name { flex:1; min-width:0; padding-right:8rem; }
.ss-group-title { color:{{colors.group_title_text}}; font-weight:normal; font-size:17rem; line-height:20rem; margin:0; overflow-wrap:break-word; }
.ss-group-subtitle { color:{{colors.group_subtitle_text}}; font-size:12rem; line-height:16rem; margin-top:1rem; }
.ss-battle-outcome { display:block; flex-shrink:0; margin-left:8rem; padding:2rem 5rem; border-radius:{{radii.battle_outcome}}rem; background:{{colors.battle_outcome_background}}; color:{{colors.battle_outcome_text}}; font-size:13rem; line-height:18rem; }
.ss-outcome-win { background:{{colors.win_background}}; color:{{colors.win_text}}; }
.ss-outcome-loss { background:{{colors.loss_background}}; color:{{colors.loss_text}}; }
.ss-outcome-draw, .ss-outcome-unknown { background:{{colors.draw_background}}; color:{{colors.draw_text}}; }
.ss-group-kpi { flex:0 0 80rem; min-width:0; width:80rem; text-align:center; padding:0 2.5rem; }
.ss-group-kpi.ss-group-count { flex-basis:90rem; width:90rem; }
.ss-group-kpi .ss-kpi-label { display:block; height:32rem; min-height:32rem; font-size:12rem; line-height:16rem; text-align:center; }
.ss-group-kpi .ss-kpi-value { font-size:20rem; line-height:23rem; text-align:center; }
.ss-group .ss-details { border-top:0; padding-top:4rem; }
.ss-group .ss-detail-title { display:none; }
.ss-group .ss-explainer { display:none; }
.ss-empty { color:{{colors.empty_text}}; font-size:14rem; padding:16rem 4rem; margin:0; line-height:20rem; }
.ss-footer { flex-shrink:0; display:flex; align-items:center; min-height:36rem; border-top:1rem solid {{colors.panel_footer_border_top}}; border-radius:0 0 {{radii.panel_footer}}rem {{radii.panel_footer}}rem; padding:5rem 25rem 7rem 10rem; background:linear-gradient({{colors.panel_footer_background_start}},{{colors.panel_footer_background_end}}); box-shadow:inset 0 -2rem {{colors.session_tabs_border}}; }
.ss-status { display:block; flex:1; min-width:0; color:{{colors.status_text}}; font-size:11rem; line-height:14rem; padding-right:8rem; }
.ss-version { display:block; flex:0 0 auto; color:{{colors.status_text}}; font-size:11rem; line-height:14rem; padding-right:8rem; white-space:nowrap; }
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
  .ss-titlebar { padding-left:9rem; padding-right:70rem; }
  .ss-titlebar h1 { font-size:20rem; }
  .ss-game-mode { font-size:11rem; margin-left:8rem; }
  .ss-controls { padding:0 8rem; }
  .ss-scroll { padding-left:8rem; padding-right:20rem; }
  .ss-group-header { flex-wrap:wrap; }
  .ss-group-name { min-width:75%; }
  .ss-battle .ss-group-name { min-width:0; }
  .ss-group-kpi { flex-basis:33.333%; width:33.333%; margin-top:3rem; }
  .ss-group-kpi.ss-group-count { flex-basis:33.333%; width:33.333%; }
  .ss-group-kpi .ss-kpi-value { font-size:19rem; }
  .ss-group .ss-detail-title { display:none; }
}
@media (max-width:400px) {
  /* Keep full financial amounts readable even in a narrow game viewport.
     The row label takes a separate line; the three number columns stay equal. */
  .ss-metric-head, .ss-metric-row, .ss-money-head, .ss-money-row { flex-wrap:wrap; }
  .ss-metric-head .ss-metric-name, .ss-money-head .ss-money-label { display:none; }
  .ss-metric-head .ss-metric-count, .ss-money-head .ss-money-label.ss-money-count { display:block; width:100%; padding:0 4rem; }
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
.ss-pagination > .ss-button { flex:0 0 auto; min-width:64rem; width:auto; height:30rem; min-height:30rem; padding:4rem 7rem; }
.ss-pagination .ss-button:disabled { cursor:default; pointer-events:none; }
#ss-page-label { display:block; min-width:0; padding:0 2rem; text-align:center; color:{{colors.list_meta_text}}; font-size:12rem; line-height:17rem; }
.ss-language-row { display:flex; align-items:center; flex:0 1 158rem; min-width:0; width:158rem; max-width:100%; min-height:30rem; }
.ss-language-caption { display:block; flex-shrink:1; min-width:0; margin-right:6rem; color:{{colors.list_meta_text}}; font-size:12rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ss-select.ss-language-select { flex:1 1 0rem; width:0; }
.ss-language-select .ss-select-options { left:auto; right:0; }
.ss-page-center { flex:1 1 160rem; min-width:0; padding:0 6rem; }
.ss-sorting { display:flex; flex-wrap:nowrap; align-items:flex-end; flex:0 1 294rem; min-width:0; width:294rem; max-width:100%; margin:0 0 5rem; }
.ss-sort-field { min-width:0; }
.ss-sort-statistic { flex:0 1 65rem; width:65rem; max-width:100%; }
.ss-sort-metric { flex:0 1 120rem; width:120rem; max-width:100%; padding-right:5rem; }
.ss-sort-direction { flex:0 1 109rem; width:109rem; max-width:100%; padding-right:5rem; }
.ss-sort-caption { display:block; margin-bottom:2rem; color:{{colors.list_meta_text}}; font-size:11rem; line-height:14rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ss-select { position:relative; width:100%; min-width:0; }
.ss-select-trigger { width:100%; min-width:0; height:30rem; min-height:30rem; padding:4rem 6rem; justify-content:space-between; }
.ss-page-center .ss-select-trigger { height:30rem; min-height:30rem; }
/* Both the battle boundary and date direction remain visible without relying
   on arrow glyphs in the native font. Keep the existing pagination budget. */
#ss-sort-chronology .ss-select-trigger { padding-top:2rem; padding-bottom:2rem; }
#ss-sort-chronology .ss-select-trigger .ss-control-label { font-size:11rem; line-height:12rem; white-space:normal; }
#ss-sort-chronology .ss-select-options { width:260rem; }
.ss-select-trigger.ss-select-disabled, .ss-select-trigger[aria-disabled="true"] { opacity:{{opacity.disabled_controls}}; color:{{colors.garage_button_text}}; border-color:{{colors.button_border}}; background:{{colors.xp_toggle_background}}; box-shadow:none; text-shadow:none; cursor:default; }
.ss-select-trigger.ss-select-disabled .ss-control-label, .ss-select-trigger[aria-disabled="true"] .ss-control-label { color:{{colors.garage_button_text}}; text-shadow:none; }
.ss-select-trigger.ss-select-disabled .ss-select-arrow, .ss-select-trigger[aria-disabled="true"] .ss-select-arrow { border-right-color:{{colors.garage_button_text}}; border-bottom-color:{{colors.garage_button_text}}; }
.ss-select-trigger .ss-control-label { flex:1; text-align:left; }
/* Full financial metric names use two lines inside the existing fixed slot. */
.ss-sort-metric .ss-select-trigger { padding-top:1rem; padding-bottom:1rem; }
.ss-sort-metric .ss-select-trigger .ss-control-label { font-size:11rem; line-height:13rem; white-space:normal; }
.ss-select-arrow { display:block; flex-shrink:0; width:6rem; height:6rem; margin:-3rem 3rem 0 6rem; border-right:1rem solid currentColor; border-bottom:1rem solid currentColor; transform:rotate(45deg); }
.ss-select-options { position:absolute; top:100%; left:0; z-index:20; min-width:100%; width:180rem; max-width:260rem; padding:3rem; border:1rem solid {{colors.list_meta_text}}; border-radius:{{radii.group_tabs}}rem; background:{{colors.window_background}}; box-shadow:0 3rem 8rem {{colors.title_text_shadow}}; }
.ss-sorting .ss-select-options { width:100%; }
.ss-sort-direction .ss-select-options { left:auto; right:0; }
.ss-select-option { width:100%; min-height:28rem; padding:4rem 5rem; border:0; border-radius:{{radii.control}}rem; background:{{colors.body_background}}; color:{{colors.list_meta_text}}; justify-content:flex-start; }
.ss-select-option .ss-control-label { font-size:12rem; line-height:18rem; text-align:left; white-space:normal; }
@media (max-width:420px) {
  .ss-sorting .ss-control-label, .ss-page-center .ss-control-label { font-size:11rem; }
  .ss-sorting .ss-select-trigger { padding-left:2rem; padding-right:2rem; }
  .ss-sorting .ss-select-arrow { width:5rem; height:5rem; margin-left:2rem; margin-right:1rem; }
  .ss-sorting .ss-sort-metric { flex-basis:126rem; width:126rem; }
  .ss-sorting .ss-sort-statistic { flex-basis:59rem; width:59rem; }
}
.ss-filters-compact .ss-sorting .ss-control-label, .ss-filters-compact .ss-page-center .ss-control-label { font-size:11rem; }
.ss-filters-compact .ss-sorting .ss-select-trigger { padding-left:0; padding-right:0; }
.ss-filters-compact .ss-sorting .ss-select-arrow { width:4rem; height:4rem; margin-left:1rem; margin-right:0; }
.ss-filters-compact .ss-sorting .ss-sort-metric { flex-basis:126rem; width:126rem; }
.ss-filters-compact .ss-sorting .ss-sort-statistic { flex-basis:59rem; width:59rem; }
.ss-select-option:hover, .ss-select-option:focus, .ss-select-option[aria-selected="true"] { color:{{colors.group_title_text}}; background:{{colors.window_background}}; box-shadow:inset 2rem 0 {{colors.list_meta_text}}; }
/* Off is a selectable state, not a disabled dropdown. Keep its arrow and
   normal text contrast; the neutral diagonal pattern communicates its value. */
.ss-select-trigger.ss-sort-off-choice, .ss-select-option.ss-sort-off-choice { background-color:{{colors.date_unavailable_background}}; background-image:linear-gradient(135deg,{{colors.date_unavailable_background}} 0%,{{colors.date_unavailable_background}} 42%,{{colors.date_unavailable_border}} 42%,{{colors.date_unavailable_border}} 56%,{{colors.date_unavailable_background}} 56%); background-size:9rem 9rem; background-repeat:repeat; }
.ss-outcome-art { display:flex; align-items:center; width:auto; max-width:48%; padding:0; background:none; }
.ss-outcome-image { display:block; position:relative; overflow:hidden; flex-shrink:0; width:64rem; height:38rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; background:{{colors.battle_outcome_background}}; }
.ss-outcome-win .ss-outcome-image { border-color:{{colors.win_text}}; background:{{colors.win_background}}; }
.ss-outcome-loss .ss-outcome-image { border-color:{{colors.loss_text}}; background:{{colors.loss_background}}; }
.ss-outcome-draw .ss-outcome-image { border-color:{{colors.draw_text}}; background:{{colors.draw_background}}; }
.ss-outcome-image-layer { display:block; position:absolute; left:0; right:0; top:0; bottom:0; background-repeat:no-repeat; background-position:center; background-size:cover; pointer-events:none; }
.ss-battle-map-thumb { margin:0 0 0 8rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; background-color:{{colors.window_background}}; }
.ss-outcome-label { display:block; text-align:center; }
.ss-outcome-art .ss-outcome-label { min-width:0; padding:2rem 4rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

/* Keep optional information above the tables, alongside the vehicle identity. */
.ss-group-heading, .ss-group-meta, .ss-summary-meta { display:flex; align-items:center; flex-wrap:wrap; min-width:0; }
.ss-group-meta .ss-group-subtitle { margin-right:10rem; }
.ss-vehicle-meta { display:flex; flex:0 1 auto; flex-wrap:nowrap; align-items:center; min-width:0; line-height:16rem; }
.ss-vehicle-tier { display:block; flex-shrink:0; margin-right:3rem; }
.ss-vehicle-icon { display:block; flex:0 0 16rem; width:16rem; height:16rem; margin-right:3rem; background-repeat:no-repeat; background-position:center; background-size:contain; cursor:help; }
.ss-vehicle-class-icon { flex-basis:24rem; width:24rem; height:24rem; background-size:24rem 24rem; }

.ss-group-meta .ss-free-xp { font-size:12rem; }
.ss-group-meta .ss-free-xp strong { font-size:12rem; }
.ss-group-sort-value { display:block; flex:0 1 auto; min-width:0; max-width:100%; margin:2rem 8rem 2rem 0; padding:2rem 5rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; background:{{colors.table_header_background_start}}; color:{{colors.session_tab_active_text}}; font-size:12rem; line-height:16rem; white-space:normal; overflow-wrap:normal; }
/* Sorting decorates the existing KPI slots without changing their geometry. */
.ss-group .ss-sort-active-value { border-radius:{{radii.control}}rem; background:{{colors.sort_active_background}}; box-shadow:inset 0 0 0 1rem {{colors.session_tab_marker_background}}; }
.ss-summary-meta { margin:3rem 4rem; }
.ss-summary-main .ss-summary-meta { display:block; }
/* Explicit header/value rows keep all three totals horizontal in native flex. */
.ss-summary-xp-totals { display:block; width:100%; min-width:0; max-width:100%; min-height:51rem; margin:0 auto; }
.ss-summary-xp-head, .ss-summary-xp-values { display:flex; flex-wrap:nowrap; width:100%; min-width:0; }
.ss-summary-xp-head { height:34rem; min-height:34rem; }
.ss-summary-xp-values { height:17rem; min-height:17rem; }
.ss-summary-xp-head .ss-xp-total-label, .ss-summary-xp-total { display:block; flex:0 0 33.333%; width:33.333%; min-width:0; max-width:33.333%; padding:0 4rem; margin:0; text-align:center; }
.ss-summary-xp-head .ss-xp-total-label { display:flex; flex-direction:column; justify-content:flex-end; height:34rem; min-height:34rem; line-height:17rem; }
.ss-xp-total-caption { display:block; width:100%; min-width:0; }
.ss-summary-xp-total .ss-xp-total-amount { display:block; height:17rem; min-height:17rem; line-height:17rem; text-align:center; }
.ss-summary-xp-total .ss-xp-total-value { display:block; min-height:17rem; line-height:17rem; white-space:nowrap; margin:0; }
.ss-narrow-summary .ss-summary-xp-totals { min-height:68rem; }
.ss-narrow-summary .ss-summary-xp-head, .ss-narrow-summary .ss-xp-total-label { height:51rem; min-height:51rem; }

@media (max-width:560px) {
  .ss-battle .ss-group-name { width:0; flex:1; }
  .ss-outcome-image { width:48rem; height:29rem; }
  .ss-battle-map-thumb { width:42rem; height:26rem; margin-left:4rem; }
  .ss-battle-outcome { margin-left:4rem; }
  .ss-outcome-label { font-size:11rem; }
}
@media (max-width:380px) {
  .ss-language-caption { margin-right:4rem; }
}

/* Result/map slots have the same footprint for every card in a caption mode.
   Fixed artwork and caption boxes keep columns aligned across short/long
   localized results and map names without measuring or probing their text. */
.ss-battle .ss-group-header { flex-wrap:nowrap; }
.ss-battle .ss-battle-outcome { display:flex; align-items:center; justify-content:center; flex:0 0 64rem; width:64rem; max-width:64rem; height:59rem; margin-left:6rem; padding:0; }
.ss-battle .ss-outcome-art { flex-direction:column; background:none; }
.ss-battle .ss-outcome-image { width:54rem; height:30rem; }
.ss-battle .ss-outcome-label { width:100%; min-width:0; max-width:100%; padding:0; font-size:11rem; line-height:14rem; text-align:center; white-space:normal; overflow-wrap:break-word; }
.ss-battle .ss-outcome-art .ss-outcome-label { flex:0 0 28rem; height:28rem; margin-top:1rem; overflow:visible; }
.ss-battle-map-visual { display:flex; flex-direction:column; align-items:center; justify-content:center; flex:0 0 84rem; width:84rem; min-width:0; max-width:84rem; height:59rem; margin-left:6rem; }
.ss-battle-map-visual .ss-battle-map-thumb { width:54rem; height:30rem; margin:0; }
.ss-battle-map-label { display:block; flex:0 0 28rem; height:28rem; min-width:0; width:100%; max-width:100%; margin-top:1rem; color:{{colors.group_subtitle_text}}; font-size:11rem; line-height:14rem; text-align:center; white-space:normal; overflow-wrap:break-word; }
.ss-battle .ss-more-button { flex:0 0 82rem; width:82rem; min-width:82rem; max-width:82rem; padding-left:5rem; padding-right:5rem; }
.ss-battle.ss-battle-inline-captions .ss-battle-outcome { flex:0 0 160rem; width:160rem; max-width:160rem; height:38rem; }
.ss-battle.ss-battle-inline-captions .ss-outcome-art { flex-direction:row; }
.ss-battle.ss-battle-inline-captions .ss-outcome-image { width:64rem; height:38rem; }
.ss-battle.ss-battle-inline-captions .ss-outcome-label { display:block; width:96rem; max-width:100%; height:auto; margin-top:0; padding:0 4rem; font-size:12rem; line-height:16rem; white-space:normal; }
.ss-battle.ss-battle-inline-captions .ss-outcome-art .ss-outcome-label { flex:0 0 96rem; }
.ss-battle-inline-captions .ss-battle-map-visual { flex-direction:row; flex:0 0 166rem; width:166rem; max-width:166rem; height:38rem; margin-left:8rem; }
.ss-battle-inline-captions .ss-battle-map-thumb { width:54rem; height:32rem; }
.ss-battle-inline-captions .ss-battle-map-label { display:block; flex:0 0 112rem; width:112rem; max-width:112rem; height:auto; margin-top:0; padding-left:6rem; font-size:12rem; line-height:16rem; text-align:left; }
.ss-narrow-cards .ss-battle .ss-group-header { flex-wrap:wrap; }
.ss-narrow-cards .ss-battle .ss-group-name { flex:1 1 180rem; min-width:0; }
.ss-narrow-cards .ss-battle .ss-battle-outcome { flex-basis:64rem; width:64rem; max-width:64rem; height:55rem; }
.ss-narrow-cards .ss-battle-map-visual { flex-basis:76rem; width:76rem; max-width:76rem; height:55rem; }
.ss-narrow-cards .ss-battle .ss-outcome-image, .ss-narrow-cards .ss-battle-map-thumb { width:48rem; height:28rem; }
.ss-narrow-cards .ss-battle .ss-outcome-label, .ss-narrow-cards .ss-battle-map-label { font-size:11rem; line-height:13rem; }
.ss-narrow-cards .ss-battle .ss-outcome-art .ss-outcome-label, .ss-narrow-cards .ss-battle-map-label { flex-basis:26rem; height:26rem; }

.ss-time-point-controls { display:flex; align-items:center; flex:1 1 266rem; min-width:0; width:266rem; max-width:100%; margin-right:8rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; background:{{colors.window_background}}; box-shadow:inset 0 1rem {{colors.button_shadow_2}}; }
.ss-time-point-name { display:block; flex:1 1 0rem; width:0; min-width:0; height:28rem; padding:4rem 7rem; margin:0; border:0; border-radius:0 {{radii.control}}rem {{radii.control}}rem 0; background:{{colors.close_background}}; color:{{colors.button_text}}; font-family:Warhelios, Arial, sans-serif; font-size:12rem; line-height:18rem; }
.ss-time-point-name:focus { outline:none; box-shadow:inset 0 0 6rem {{colors.button_shadow_2}}; }
.ss-time-point { flex:0 0 auto; min-width:122rem; width:auto; min-height:28rem; padding-left:7rem; padding-right:7rem; border:0; border-right:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem 0 0 {{radii.control}}rem; }
.ss-has-help { cursor:help; }
.ss-help-tooltip { display:none; position:absolute; z-index:95; width:320rem; padding:9rem 11rem; border:1rem solid {{colors.confirmation_border}}; border-radius:{{radii.control}}rem; background:{{colors.window_background}}; color:{{colors.body_text}}; font-family:Warhelios, Arial, sans-serif; font-size:12rem; line-height:17rem; white-space:pre-line; overflow:hidden; box-shadow:0 3rem 14rem {{colors.title_text_shadow}}, inset 0 1rem {{colors.button_shadow_2}}; pointer-events:none; }
.ss-info-button { display:flex; align-items:center; justify-content:center; flex:0 0 16rem; min-width:16rem; width:16rem; height:16rem; padding:0; margin:0 0 0 5rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.window}}rem; color:{{colors.button_text}}; background:{{colors.window_background}}; box-shadow:none; text-shadow:none; font-family:Warhelios, Arial, sans-serif; font-size:12rem; font-style:normal; font-weight:normal; line-height:14rem; cursor:help; }
.ss-info-button:hover, .ss-info-button:focus, .ss-info-button[aria-expanded="true"] { outline:1rem solid {{colors.session_tab_marker_background}}; outline-offset:1rem; color:{{colors.button_hover_text}}; border-color:{{colors.session_tab_marker_background}}; background:{{colors.table_row_hover_background}}; box-shadow:0 0 5rem {{colors.session_tab_marker_background}}; }
/* Gameface captions need an explicit text box and individual font properties;
   the font shorthand/inherited italic Arial can leave the native icon blank. */
.ss-info-symbol { display:block; width:14rem; height:14rem; margin:0; padding:0; color:{{colors.button_text}}; font-family:Warhelios, Arial, sans-serif; font-size:12rem; font-style:normal; font-weight:normal; line-height:14rem; text-align:center; pointer-events:none; }
.ss-info-button:hover .ss-info-symbol, .ss-info-button:focus .ss-info-symbol, .ss-info-button[aria-expanded="true"] .ss-info-symbol { color:{{colors.button_hover_text}}; }
.ss-summary .ss-kpi-label { display:flex; align-items:center; justify-content:center; }
.ss-summary .ss-detail-title { display:flex; align-items:center; }
/* Header labels own their full caption boxes. Compensating margins retain the
   original starts and widths of the right-aligned numeric columns. */
.ss-summary-details .ss-metric-head, .ss-summary-details .ss-money-head { align-items:center; }
.ss-summary-details .ss-summary-table-heading { display:block; min-width:0; }
.ss-summary-details .ss-metric-head .ss-summary-table-heading { width:40%; margin-right:-12%; }
.ss-summary-details .ss-money-head .ss-summary-table-heading { width:30.8%; margin-right:-7.8%; }
.ss-summary-details .ss-summary-table-title { position:relative; z-index:1; display:flex; align-items:center; width:100%; min-width:0; height:26rem; margin:0; font-size:11rem; line-height:13rem; }
.ss-summary-details .ss-economy .ss-summary-table-title { width:100%; }
.ss-summary-table-title .ss-table-heading-text { display:block; flex:1 1 0rem; min-width:0; overflow-wrap:break-word; }
.ss-summary-table-title .ss-info-button { margin-left:3rem; }
.ss-narrow-summary .ss-summary-details .ss-money-head .ss-summary-table-heading { display:block; width:100%; margin-right:0; }
.ss-narrow-summary .ss-summary-details .ss-money-head .ss-summary-table-title { width:100%; height:26rem; }
@media (max-width:400px) {
  .ss-summary-details .ss-metric-head .ss-summary-table-heading, .ss-summary-details .ss-money-head .ss-summary-table-heading { width:100%; margin-right:0; }
}

.ss-group-coverage { display:block; flex:0 0 auto; max-width:100%; margin-left:6rem; color:{{colors.partial_count_text}}; font-size:12rem; line-height:16rem; white-space:nowrap; }
.ss-timeline { position:relative; z-index:21; display:flex; flex-wrap:wrap; align-items:center; justify-content:center; flex:0 1 452rem; min-width:0; width:452rem; max-width:100%; margin:0 8rem 4rem 0; padding:0; }
.ss-timeline-field { display:flex; flex:1 1 200rem; min-width:0; max-width:222rem; align-items:flex-start; margin:0 4rem; color:{{colors.table_header_text}}; }
.ss-timeline-field > span { flex-shrink:0; margin-right:6rem; line-height:30rem; }
.ss-timeline-field .ss-select { flex:1 1 0rem; width:0; }
.ss-timeline-field .ss-select-options { top:30rem; width:100%; min-width:0; max-height:200rem; overflow-y:auto; }
.ss-date-editor { display:flex; align-items:center; width:100%; min-width:0; height:30rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; background:{{colors.window_background}}; }
.ss-custom-date { display:block; flex:1 1 100rem; min-width:0; width:0; height:28rem; padding:3rem 4rem; margin:0; border:0; background:{{colors.body_background}}; color:{{colors.button_text}}; font-family:Warhelios, Arial, sans-serif; font-size:11rem; line-height:18rem; }
.ss-custom-date:focus { outline:none; box-shadow:inset 0 0 0 1rem {{colors.button_shadow_1}}; }
.ss-date-editor > .ss-date-menu, .ss-date-editor > .ss-date-calendar { flex:0 0 24rem; width:24rem; min-width:24rem; height:28rem; min-height:28rem; padding:0; margin:0; border:0; border-left:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; justify-content:center; }
.ss-date-menu .ss-control-label { display:none; }
.ss-date-menu .ss-select-arrow { margin-left:0; margin-right:0; }
.ss-date-calendar-icon { display:block; position:relative; width:12rem; height:12rem; border:1rem solid {{colors.button_text}}; border-top:3rem solid {{colors.button_text}}; }
.ss-date-calendar-icon:after { content:""; position:absolute; left:2rem; right:2rem; top:3rem; height:0; border-top:2rem solid {{colors.button_text}}; }
.ss-date-picker { position:absolute; z-index:90; display:block; width:286rem; max-width:100%; padding:8rem; overflow-y:auto; border:1rem solid {{colors.confirmation_border}}; border-radius:{{radii.group_card}}rem; background:{{colors.window_background}}; background-image:url("session_stats_camo.png"); background-size:420rem 345rem; background-repeat:repeat; color:{{colors.button_text}}; box-shadow:0 3rem 8rem {{colors.title_text_shadow}}, inset 0 1rem {{colors.button_shadow_2}}; }
.ss-date-picker-heading { display:flex; align-items:center; justify-content:space-between; min-width:0; margin-bottom:4rem; }
.ss-date-picker-title { display:flex; flex:1; min-width:0; align-items:center; justify-content:center; text-align:center; font-size:14rem; line-height:20rem; }
.ss-date-picker .ss-date-heading-month, .ss-date-picker .ss-date-heading-year { flex:0 1 auto; min-width:0; min-height:28rem; margin:0; padding:3rem 5rem; border-color:{{colors.body_background}}; background:{{colors.body_background}}; box-shadow:none; }
.ss-date-picker .ss-date-heading-month:hover, .ss-date-picker .ss-date-heading-year:hover, .ss-date-picker .ss-date-heading-month[aria-expanded="true"], .ss-date-picker .ss-date-heading-year[aria-expanded="true"] { border-color:{{colors.button_border}}; background:{{colors.table_row_hover_background}}; color:{{colors.session_tab_active_text}}; }
.ss-date-picker .ss-date-heading-month .ss-control-label, .ss-date-picker .ss-date-heading-year .ss-control-label { font-size:14rem; line-height:20rem; }
.ss-date-month-arrow { flex:0 0 24rem; width:24rem; min-width:24rem; height:24rem; min-height:24rem; margin:0; padding:0; }
.ss-date-month-arrow .ss-control-label { display:none; }
.ss-date-chevron { display:block; width:7rem; height:7rem; border-right:1rem solid {{colors.button_text}}; border-bottom:1rem solid {{colors.button_text}}; transform:rotate(-45deg); }
.ss-date-month-previous .ss-date-chevron { transform:rotate(135deg); }
.ss-date-picker-body { min-width:0; width:100%; }
.ss-date-week { display:flex; width:100%; min-width:0; }
.ss-date-weekday, .ss-date-day { display:flex; flex:0 0 14.2857%; width:14.2857%; min-width:0; height:24rem; min-height:24rem; margin:0; padding:2rem; align-items:center; justify-content:center; font-size:11rem; line-height:18rem; text-align:center; }
.ss-date-picker .ss-date-day { margin:0; border:1rem solid {{colors.body_background}}; border-radius:{{radii.control}}rem; background:{{colors.body_background}}; box-shadow:none; }
.ss-date-weekday { color:{{colors.table_header_text}}; }
.ss-date-picker .ss-date-day[aria-selected="true"], .ss-date-picker .ss-date-option[aria-selected="true"] { border-color:{{colors.session_tab_marker_background}}; color:{{colors.session_tab_active_text}}; background:{{colors.button_confirm_background_end}}; box-shadow:inset 0 0 4rem {{colors.button_shadow_2}}; }
.ss-date-day .ss-control-label { font-size:12rem; line-height:18rem; }
.ss-date-options { display:flex; flex-wrap:wrap; width:100%; max-height:190rem; overflow-y:auto; }
.ss-date-picker .ss-date-option { flex:0 0 33.3333%; width:33.3333%; min-width:0; height:30rem; min-height:30rem; margin:0; padding:3rem; border-color:{{colors.body_background}}; background:{{colors.body_background}}; box-shadow:none; }
.ss-date-option .ss-control-label { font-size:12rem; line-height:18rem; }
.ss-date-time { display:flex; align-items:center; justify-content:center; min-width:0; margin-top:5rem; padding-top:5rem; border-top:1rem solid {{colors.button_border}}; }
.ss-date-clock-info { margin-left:8rem; }
.ss-date-picker .ss-date-time-part { flex:0 0 33rem; min-width:33rem; width:33rem; min-height:28rem; height:28rem; margin:0; padding:2rem; }
.ss-date-time-part .ss-control-label { font-size:18rem; line-height:22rem; }
.ss-date-time-colon { margin:0 4rem; font-size:18rem; line-height:24rem; }
.ss-date-picker .ss-date-time-part[aria-pressed="true"], .ss-date-picker .ss-date-period[aria-pressed="true"] { color:{{colors.session_tab_active_text}}; border-color:{{colors.session_tab_marker_background}}; }
.ss-date-periods { display:flex; flex:0 1 auto; min-width:0; margin-left:8rem; }
.ss-date-picker .ss-date-period { flex:0 1 auto; min-width:27rem; min-height:28rem; height:28rem; margin:0; padding:2rem 3rem; }
.ss-date-period .ss-control-label { font-size:11rem; line-height:18rem; }
.ss-date-clock-container { display:block; position:relative; width:100%; height:180rem; margin:5rem 0; }
.ss-date-clock { display:block; position:absolute; left:50%; top:0; width:180rem; height:180rem; margin:0 0 0 -90rem; border:1rem solid {{colors.button_border}}; border-radius:{{radii.sort_switch_track}}em; background:{{colors.window_background}}; box-shadow:inset 0 1rem 6rem {{colors.title_text_shadow}}; cursor:pointer; }
.ss-date-clock:focus { outline:1rem solid {{colors.session_tab_marker_background}}; outline-offset:1rem; }
.ss-date-clock-hand { display:block; position:absolute; z-index:1; left:50%; bottom:50%; width:2rem; margin-left:-1rem; background:{{colors.session_tab_marker_background}}; transform-origin:center bottom; pointer-events:none; }
.ss-date-clock-pivot { display:block; position:absolute; z-index:2; left:50%; top:50%; width:5rem; height:5rem; margin:-2.5rem 0 0 -2.5rem; border-radius:{{radii.sort_switch_track}}rem; background:{{colors.session_tab_marker_background}}; pointer-events:none; }
.ss-date-picker .ss-date-clock-number { display:flex; position:absolute; z-index:3; width:26rem; min-width:26rem; height:26rem; min-height:26rem; margin:-13rem 0 0 -13rem; padding:0; border:1rem solid {{colors.body_background}}; border-radius:{{radii.sort_switch_track}}em; background:{{colors.body_background}}; box-shadow:none; }
.ss-date-clock-number .ss-control-label { font-size:12rem; line-height:18rem; }
.ss-date-picker .ss-date-clock-inner { width:22rem; min-width:22rem; height:22rem; min-height:22rem; margin:-11rem 0 0 -11rem; color:{{colors.table_header_text}}; }
.ss-date-clock-inner .ss-control-label { font-size:10rem; line-height:14rem; }
.ss-date-picker .ss-date-clock-number[aria-pressed="true"] { border-color:{{colors.session_tab_marker_background}}; background:{{colors.button_confirm_background_end}}; color:{{colors.session_tab_active_text}}; }
/* Explicit neutral paint survives native disabled-button rendering. Keep the
   numbers readable; opacity alone can leave an unavailable date looking live. */
.ss-date-picker .ss-date-unavailable { opacity:{{opacity.date_unavailable}}; color:{{colors.date_unavailable_text}}; border-color:{{colors.date_unavailable_border}}; background:{{colors.date_unavailable_background}}; box-shadow:none; text-shadow:none; cursor:default; }
.ss-date-picker .ss-date-unavailable .ss-control-label { color:{{colors.date_unavailable_text}}; text-shadow:none; }
.ss-date-picker .ss-date-unavailable .ss-date-chevron { border-color:{{colors.date_unavailable_text}}; }
.ss-date-picker-actions { display:flex; justify-content:flex-end; min-width:0; margin-top:6rem; }
.ss-date-picker-actions > .ss-control { margin-left:5rem; }
.ss-custom-date-apply { flex:0 0 auto; min-width:40rem; max-width:100%; height:30rem; min-height:30rem; padding:3rem 6rem; }
.ss-custom-date-apply .ss-control-label { font-size:11rem; line-height:16rem; }
.ss-custom-date-error { display:block; min-width:0; width:100%; padding-top:3rem; color:{{colors.negative_text}}; font-size:11rem; line-height:15rem; overflow-wrap:break-word; }
.ss-more-button { margin-left:7rem; }
.ss-map-more-button { min-width:48rem; padding:3rem 7rem; margin-left:6rem; }
.ss-narrow-cards [id^="ss-card-maps-"] .ss-group-header, .ss-narrow-cards [id^="ss-card-vehicles-"] .ss-group-header { flex-wrap:wrap; }
.ss-narrow-cards [id^="ss-card-maps-"] .ss-group-name, .ss-narrow-cards [id^="ss-card-vehicles-"] .ss-group-name { flex:1 1 340rem; min-width:0; }
/* Aggregate cards keep one compact statistical row across sort modes. */
.ss-group-stats { display:flex; flex:0 0 290rem; align-items:center; min-width:0; width:290rem; }
.ss-group-stats.ss-group-stats-more { flex-basis:366rem; width:366rem; }
.ss-aggregate .ss-group-header { min-height:66rem; flex-wrap:nowrap; }
.ss-aggregate .ss-group-name { min-width:0; padding-right:4rem; }
.ss-aggregate .ss-group-kpi { flex:0 0 62rem; width:62rem; min-width:0; margin-top:0; padding:0 2rem; }
.ss-aggregate .ss-group-count { flex-basis:60rem; width:60rem; }
.ss-aggregate .ss-group-wn8-kpi { flex-basis:72rem; width:72rem; }
.ss-aggregate .ss-group-kpi .ss-kpi-label { height:26rem; min-height:26rem; font-size:11rem; line-height:13rem; overflow-wrap:break-word; }
.ss-aggregate .ss-group-kpi .ss-kpi-value { display:flex; flex-direction:column; align-items:center; justify-content:center; height:38rem; min-height:38rem; font-size:20rem; line-height:23rem; overflow-wrap:break-word; }
.ss-aggregate .ss-group-count .ss-kpi-value { font-size:18rem; }
.ss-aggregate .ss-group-rate .ss-kpi-value { font-size:17rem; }
.ss-group-sort-host { position:relative; flex:0 0 96rem; width:96rem; min-width:0; height:64rem; padding:0 3rem; text-align:center; }
.ss-group-sort-caption { display:block; width:100%; height:26rem; min-height:26rem; color:{{colors.list_meta_text}}; font-size:11rem; font-weight:normal; line-height:13rem; overflow-wrap:break-word; }
.ss-group-sort-number { display:block; width:100%; height:38rem; min-height:38rem; margin:0; color:{{colors.kpi_value_text}}; font-size:16rem; line-height:19rem; white-space:normal; overflow-wrap:break-word; }
.ss-group-sort-host .ss-group-sort-value { width:100%; height:64rem; min-height:64rem; margin:0; padding:0; border:0; }
/* Keep numeric text in its native cell; only the transparent hit target overlays it. */
.ss-metric-battle-link { display:block; min-width:0; width:100%; min-height:26rem; margin:0; padding:3rem 0; border:1rem solid {{colors.button_border}}; border-radius:{{radii.control}}rem; background:linear-gradient({{colors.button_background_start}},{{colors.button_background_middle}} 48%,{{colors.button_background_end}}); color:{{colors.button_text}}; font-family:Warhelios, Arial, sans-serif; font-size:14rem; font-weight:normal; line-height:20rem; text-align:center; cursor:pointer; }
.ss-metric-battle-link:hover, .ss-metric-battle-link:focus { outline:1rem solid {{colors.session_tab_marker_background}}; outline-offset:-1rem; border-color:{{colors.session_tab_marker_background}}; }
.ss-metric-extreme-action .ss-metric-action-label { display:block; width:100%; min-width:0; height:16rem; font-size:11rem; line-height:16rem; text-align:center; }
.ss-metric-number.ss-extreme-cell { position:relative; border-radius:{{radii.control}}rem; background:linear-gradient({{colors.table_header_background_start}},{{colors.table_header_background_end}}); }
.ss-group .ss-extreme-cell.ss-sort-active-value { background:{{colors.sort_active_background}}; box-shadow:inset 0 0 0 1rem {{colors.session_tab_marker_background}}; }
.ss-extreme-cell > .ss-metric-battle-link { position:absolute; left:0; top:0; width:100%; height:100%; min-height:22rem; padding:0; background:none; }
.ss-group .ss-extreme-cell.ss-sort-active-value > .ss-metric-battle-link { border-color:{{colors.session_tab_marker_background}}; }
.ss-extreme-link-cue { display:block; position:absolute; left:2rem; bottom:0; width:3rem; height:3rem; pointer-events:none; }
.ss-extreme-link-cue:before { content:""; display:block; position:absolute; left:0; top:1rem; width:4rem; height:1rem; background:{{colors.list_meta_text}}; transform:rotate(-45deg); }
.ss-extreme-link-cue:after { content:""; display:block; position:absolute; right:0; top:0; width:3rem; height:3rem; border-top:1rem solid {{colors.list_meta_text}}; border-right:1rem solid {{colors.list_meta_text}}; }
.ss-extreme-cell > .ss-metric-battle-link:hover, .ss-extreme-cell > .ss-metric-battle-link:focus { background:none; }
.ss-group-stats > .ss-map-more-button { flex:0 0 72rem; width:72rem; min-width:72rem; margin-left:4rem; padding:3rem 4rem; font-size:11rem; line-height:16rem; }
.ss-group-stats > .ss-map-more-button .ss-control-label { font-size:11rem; line-height:16rem; }
.ss-aggregate.ss-compact-headline .ss-group-header { flex-wrap:wrap; }
.ss-aggregate.ss-compact-headline .ss-group-name { flex:1 1 340rem; min-width:0; }
.ss-aggregate.ss-compact-headline .ss-group-stats { flex:1 1 100%; width:100%; max-width:100%; flex-wrap:wrap; justify-content:flex-end; }
.ss-more-panel { display:flex; flex-wrap:wrap; align-items:flex-start; padding:5rem 0 2rem; border-top:1rem solid {{colors.group_tabs_border_bottom}}; font-size:13rem; line-height:18rem; overflow-wrap:break-word; }
.ss-more-panel > p { width:100%; margin:3rem 5rem; }
.ss-more-title { margin:4rem 5rem; color:{{colors.session_tab_active_text}}; font-size:13rem; line-height:18rem; }
.ss-more-mission { display:block; width:100%; margin:0 0 6rem; padding:6rem 7rem; border:1rem solid {{colors.details_separator_border_top}}; border-radius:{{radii.table_row}}rem; background:{{colors.table_row_background}}; }
.ss-more-caption { color:{{colors.period_text}}; font-size:12rem; line-height:16rem; }
/* Map history stays a small native flex list. Each owned jump action remains
   separate from the row's name, date, rating and result text. */
.ss-map-battles { display:block; min-width:0; width:100%; margin-top:3rem; border:1rem solid {{colors.details_separator_border_top}}; border-radius:{{radii.table_row}}rem; background:{{colors.table_row_background}}; }
.ss-history-body { display:block; min-width:0; width:100%; height:auto; max-height:460rem; overflow-y:auto; overflow-x:hidden; }
.ss-history-body.ss-history-paged { height:460rem; }
.ss-map-battle-row { display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-end; min-width:0; width:100%; padding:5rem 6rem; border-top:1rem solid {{colors.details_separator_border_top}}; }
.ss-map-battle-row:first-child { border-top:0; }
.ss-map-battle-row:nth-child(even) { background:{{colors.table_row_following_background}}; }
.ss-map-battle-info { display:flex; flex-wrap:wrap; align-items:center; flex:1 1 230rem; min-width:0; margin-right:6rem; }
.ss-map-battle-name { display:block; flex:1 1 110rem; min-width:0; margin-right:8rem; color:{{colors.group_title_text}}; font-size:13rem; line-height:18rem; font-weight:normal; overflow-wrap:break-word; }
.ss-map-battle-row > .ss-map-battle-name { flex:1 1 120rem; margin-right:8rem; }
.ss-map-battle-meta { display:flex; flex-wrap:wrap; align-items:center; min-width:0; }
.ss-map-battle-date { display:block; flex:0 0 auto; color:{{colors.period_text}}; font-size:13rem; line-height:18rem; white-space:nowrap; }
.ss-map-battle-row > .ss-map-battle-date { flex:0 0 106rem; margin-right:8rem; }
.ss-map-battle-meta .ss-map-battle-date { margin-right:8rem; }
.ss-map-battle-outcome { display:block; flex:0 0 100rem; min-width:0; margin-right:8rem; font-size:12rem; line-height:16rem; overflow-wrap:break-word; }
.ss-map-battle-wn8 { display:block; flex:0 0 auto; min-width:68rem; margin-right:8rem; color:{{colors.kpi_wn8_text}}; font-size:12rem; line-height:16rem; text-align:right; white-space:nowrap; }
.ss-map-battle-wn8-label { color:{{colors.kpi_label_text}}; }
.ss-map-battle-open { flex:0 0 auto; min-width:64rem; max-width:100%; height:26rem; min-height:26rem; padding:3rem 7rem; }
.ss-map-battles-pagination, .ss-map-pagination { display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-end; min-width:0; width:100%; padding:6rem; border-top:1rem solid {{colors.details_separator_border_top}}; }
.ss-map-battles-pagination > .ss-control, .ss-map-pagination > .ss-control { flex:0 0 auto; min-width:64rem; max-width:100%; height:26rem; min-height:26rem; padding:3rem 7rem; }
.ss-map-battles-page, .ss-map-page-status { display:block; flex:1 1 80rem; min-width:0; margin:0 4rem; color:{{colors.list_meta_text}}; font-size:11rem; line-height:16rem; text-align:center; }
.ss-map-battles .ss-empty { margin:0; padding:6rem; font-size:12rem; line-height:18rem; }
.ss-map-empty { margin:0; padding:6rem; color:{{colors.period_text}}; font-size:12rem; line-height:18rem; }
/* The card's ordinary border is the native-safe selection baseline. Preserve
   its width/layout; optional overlay effects never control visibility. */
.ss-group.ss-battle-target { outline:none; border-color:{{colors.session_tab_marker_background}}; }
.ss-battle-selection-banner { display:block; position:absolute; z-index:4; top:-10rem; right:6rem; max-width:95%; margin:0; padding:1rem 6rem; border:1rem solid {{colors.session_tab_marker_background}}; border-radius:{{radii.control}}rem; background:{{colors.table_header_background_start}}; color:{{colors.session_tab_marker_background}}; font-size:12rem; font-weight:bold; line-height:16rem; pointer-events:none; }
.ss-battle-target-outline { display:block; position:absolute; z-index:3; top:-3rem; right:-3rem; bottom:-3rem; left:-3rem; border:3rem solid {{colors.session_tab_marker_background}}; border-radius:{{radii.group_card}}rem; box-shadow:0 0 9rem {{colors.session_tab_marker_background}}, inset 0 0 0 1rem {{colors.session_tab_marker_background}}; pointer-events:none; }
.ss-target-pulsing .ss-battle-target-outline { animation:ss-battle-target-pulse 1s ease-in-out 5; }
.ss-target-muted .ss-battle-target-outline { opacity:{{opacity.target_dimmed}}; }
@keyframes ss-battle-target-pulse {
  0%, 100% { box-shadow:0 0 3rem {{colors.session_tab_marker_background}}, inset 0 0 0 1rem {{colors.session_tab_marker_background}}; }
  50% { box-shadow:0 0 14rem {{colors.session_tab_marker_background}}, inset 0 0 0 1rem {{colors.session_tab_marker_background}}; }
}
.ss-resize-grip { display:block; position:absolute; z-index:31; right:0; bottom:0; width:16rem; height:16rem; min-width:0; min-height:0; margin:0; padding:0; border:0; background:{{colors.close_background}}; color:{{colors.period_text}}; cursor:nwse-resize; touch-action:none; }
.ss-resize-grip::before { content:""; display:block; position:absolute; right:3rem; bottom:3rem; width:9rem; height:9rem; border-right:2rem solid currentColor; border-bottom:2rem solid currentColor; pointer-events:none; }
.ss-resize-grip:focus, .ss-resize-grip:hover { color:{{colors.session_tab_active_text}}; }
.ss-resize-nw { top:0; left:0; right:auto; bottom:auto; }
.ss-resize-nw::before { top:3rem; left:3rem; right:auto; bottom:auto; border-top:2rem solid currentColor; border-left:2rem solid currentColor; border-right:0; border-bottom:0; }
.ss-resize-ne { top:0; bottom:auto; cursor:nesw-resize; }
.ss-resize-ne::before { top:3rem; bottom:auto; border-top:2rem solid currentColor; border-bottom:0; }
.ss-resize-sw { left:0; right:auto; cursor:nesw-resize; }
.ss-resize-sw::before { left:3rem; right:auto; border-left:2rem solid currentColor; border-right:0; }
.ss-resize-edge { width:0; height:0; }
.ss-resize-edge::before { display:none; }
.ss-window-maximized .ss-resize-grip { display:none; }
.ss-resize-n, .ss-resize-s { height:6rem; cursor:ns-resize; }
.ss-resize-e, .ss-resize-w { width:6rem; cursor:ew-resize; }
.ss-more-columns { display:block; width:100%; min-width:0; }
.ss-more-columns-paired { display:flex; flex-wrap:nowrap; align-items:flex-start; }
.ss-more-mission-block { flex:0 0 auto; min-width:0; max-width:100%; width:100%; padding:0 0 4rem; }
.ss-more-reward-block { flex:1 1 220rem; min-width:0; max-width:100%; padding:0 0 4rem; }
/* The current point total stays beside its heading. Additional point sources
   wrap as complete cells, keeping the numerical strip above both columns. */
.ss-more-pass-block { display:flex; flex-wrap:wrap; align-items:center; flex:0 1 100%; width:100%; margin:0 0 3rem; padding:0 0 5rem; border-bottom:1rem solid {{colors.details_separator_border_top}}; }
.ss-more-pass-block .ss-more-title { flex:0 0 auto; margin:2rem 8rem 2rem 0; }
.ss-more-pass-block .ss-more-table { flex:1 1 200rem; min-width:0; width:auto; max-width:100%; border:0; background:{{colors.close_background}}; }
.ss-more-table { display:block; width:100%; margin:0; border:1rem solid {{colors.details_separator_border_top}}; border-radius:{{radii.table_row}}rem; background:{{colors.table_row_background}}; }
.ss-more-table .ss-more-body { display:block; width:100%; }
.ss-more-table .ss-more-label, .ss-more-table .ss-more-amount { display:block; min-width:0; padding:0; vertical-align:top; }
.ss-more-value { display:flex; align-items:center; width:100%; min-height:24rem; padding:3rem 7rem; border-bottom:1rem solid {{colors.details_separator_border_top}}; }
.ss-more-value .ss-more-label { flex:1 1 0rem; padding-right:10rem; text-align:left; font-weight:normal; color:{{colors.metric_label_text}}; }
.ss-more-value .ss-more-amount { flex:0 1 46%; text-align:right; color:{{colors.metric_value_text}}; }
.ss-more-value .ss-more-amount.ss-more-total { flex:1; text-align:left; color:{{colors.session_tab_active_text}}; font-weight:bold; }
.ss-more-value:last-child { border-bottom:0; }
.ss-more-pass .ss-more-body { display:flex; flex-wrap:wrap; align-items:stretch; }
.ss-more-pass .ss-more-value { align-items:center; flex:0 1 auto; min-width:0; max-width:100%; width:auto; padding:2rem 5rem; border-right:1rem solid {{colors.details_separator_border_top}}; border-bottom:0; overflow-wrap:normal; }
.ss-more-pass .ss-more-value:last-child { border-right:0; }
.ss-more-pass .ss-more-value .ss-more-label { flex:0 1 auto; width:auto; padding-right:5rem; }
.ss-more-pass .ss-more-value .ss-more-amount { flex:0 0 auto; width:auto; margin-top:0; text-align:right; white-space:nowrap; }
.ss-more-pass .ss-more-value .ss-more-total { padding:2rem 6rem; border:1rem solid {{colors.details_separator_border_top}}; border-radius:{{radii.control}}rem; background:{{colors.table_header_background_start}}; text-align:left; white-space:normal; }
.ss-more-value:nth-child(even) { background:{{colors.table_row_following_background}}; }
.ss-more-pass .ss-more-value { background:{{colors.close_background}}; }
.ss-more-mission-row { display:flex; flex-direction:row; flex-wrap:nowrap; align-items:stretch; width:100%; min-width:0; margin-bottom:6rem; }
.ss-more-mission-row:last-child { margin-bottom:0; }
.ss-more-mission-row .ss-more-mission { min-width:0; max-width:100%; margin-bottom:0; }
.ss-more-mission:last-child { margin-bottom:0; }
.ss-more-mission.ss-more-mission-even { background:{{colors.table_row_following_background}}; }
.ss-more-table.ss-more-missions { border:0; background:{{colors.close_background}}; }
.ss-more-table .ss-more-mission-name { display:block; min-width:0; width:100%; padding:0; }
.ss-more-mission-name strong { display:block; }
.ss-more-table .ss-more-mission-status { display:block; min-width:0; width:100%; margin-top:4rem; padding:4rem 0 0; border-top:1rem solid {{colors.details_separator_border_top}}; color:{{colors.metric_value_text}}; font-size:12rem; line-height:16rem; }
.ss-more-mission-description { width:100%; margin-top:4rem; }
/* Keep small matrices compact; richer translated columns request only the
   width they need before the mission block receives the remaining space. */
.ss-more-reward-block.ss-more-bonus-block { flex:0 0 auto; width:308rem; margin-right:0; }
.ss-more-reward-block.ss-more-bonus-block.ss-long-bonus-values { width:486rem; max-width:100%; }
.ss-bonus-matrix { width:100%; }
.ss-bonus-row { display:flex; flex-wrap:wrap; align-items:center; width:100%; min-height:25rem; padding:3rem 4rem; border-top:1rem solid {{colors.details_separator_border_top}}; }
.ss-bonus-row:first-child { border-top:0; }
.ss-bonus-row:nth-child(even) { background:{{colors.table_row_following_background}}; }
.ss-bonus-label { display:block; flex:1 1 112rem; min-width:0; max-width:100%; width:auto; padding:0 6rem 0 0; color:{{colors.metric_label_text}}; font-size:12rem; line-height:16rem; overflow-wrap:break-word; }
.ss-bonus-values { display:flex; flex-wrap:wrap; flex:1 1 auto; min-width:0; max-width:100%; }
.ss-bonus-number { display:block; flex:1 0 42rem; min-width:0; padding-left:3rem; color:{{colors.metric_value_text}}; text-align:right; white-space:nowrap; }
.ss-bonus-head { min-height:23rem; background:{{colors.table_header_background_start}}; }
.ss-bonus-head .ss-bonus-label { color:{{colors.table_header_cell_text}}; }
.ss-bonus-head .ss-bonus-number { color:{{colors.table_header_cell_text}}; font-size:11rem; white-space:normal; overflow-wrap:normal; }
/* Cards respond to their own configured/available width, independently of the
   full game viewport. Keep complete numbers at the regular reading size. */
.ss-group .ss-details { flex-direction:row; flex-wrap:wrap; }
.ss-group .ss-performance { flex:1 1 246rem; min-width:0; width:auto; }
.ss-group .ss-economy { flex:1 1 296rem; min-width:0; width:auto; }
.ss-group .ss-economy.ss-long-finance { flex-basis:304rem; }
.ss-group .ss-metric-name { width:32%; padding-left:1rem; padding-right:0; }
.ss-group .ss-metric-number { width:22.666%; padding-right:2rem; }
.ss-group .ss-long-metrics .ss-metric-row .ss-metric-number { font-size:14rem; }
.ss-group .ss-battle-performance { flex:0 0 176rem; padding-right:7rem; }
/* Reclaim cell insets before widening a table: translated currency names and
   complete signed eight-digit amounts must fit the same compact card. */
.ss-group .ss-money-label { width:24.5%; padding-left:2rem; padding-right:0; font-size:12rem; }
.ss-group .ss-money-value { width:25.166%; padding-right:1rem; }
.ss-group .ss-money-row .ss-money-value { font-size:13rem; }
.ss-narrow-cards .ss-group .ss-performance, .ss-narrow-cards .ss-group .ss-economy { flex-basis:100%; }
.ss-narrow-cards .ss-group .ss-performance { padding-right:0; }
.ss-narrow-cards .ss-group .ss-economy { padding:5rem 0 0; margin-top:3rem; border-left:0; border-top:1rem solid {{colors.details_separator_border_top}}; }
.ss-narrow-cards .ss-group .ss-metric-head, .ss-narrow-cards .ss-group .ss-metric-row, .ss-narrow-cards .ss-group .ss-money-head, .ss-narrow-cards .ss-group .ss-money-row { flex-wrap:wrap; }
.ss-narrow-cards .ss-group .ss-metric-head .ss-metric-name, .ss-narrow-cards .ss-group .ss-money-head .ss-money-label { display:none; }
.ss-narrow-cards .ss-group .ss-metric-head .ss-metric-count, .ss-narrow-cards .ss-group .ss-money-head .ss-money-count { display:block; width:100%; padding:0 4rem; }
.ss-narrow-cards .ss-group .ss-metric-row .ss-metric-name, .ss-narrow-cards .ss-group .ss-money-row .ss-money-label { width:100%; padding-bottom:0; }
.ss-narrow-cards .ss-group .ss-metric-number, .ss-narrow-cards .ss-group .ss-money-value { width:33.333%; }
/* Fixed-width cards stay in native column flow. Expanded battle heights are
   sampled after layout to choose chronological lanes, never absolute offsets. */
.ss-card-layout { display:flex; align-items:flex-start; justify-content:center; width:100%; }
.ss-feed-layout { display:block; }
.ss-feed-staging .ss-continuous-page { visibility:hidden; }
.ss-feed-staging .ss-page-pending { visibility:visible; }
.ss-page-status { display:flex; flex-wrap:wrap; align-items:center; justify-content:center; min-height:30rem; padding:5rem; color:{{colors.list_meta_text}}; }
.ss-page-status .ss-button { margin-left:8rem; }
.ss-continuous-page { display:block; min-width:0; width:100%; }
.ss-page-cards { display:flex; align-items:flex-start; justify-content:center; min-width:0; width:100%; }
.ss-page-divider { position:relative; display:flex; align-items:center; justify-content:center; width:100%; min-height:32rem; margin:6rem 0 2rem; }
.ss-page-divider:before { content:""; display:block; position:absolute; top:50%; left:0; right:0; height:1rem; background-image:linear-gradient(to right, {{colors.button_shadow_1}} 62.5%, {{colors.body_background}} 62.5%); background-size:32rem 1rem; background-repeat:repeat-x; pointer-events:none; }
.ss-page-divider-label { position:relative; display:block; max-width:100%; padding:3rem 10rem; border:1rem solid {{colors.details_separator_border_top}}; border-radius:{{radii.control}}rem; background:{{colors.window_background}}; color:{{colors.list_meta_text}}; font-size:12rem; line-height:18rem; text-align:center; }
.ss-page-first-battle { display:block; width:100%; margin:0 0 3rem; color:{{colors.group_subtitle_text}}; font-size:12rem; line-height:16rem; text-align:center; }
.ss-page-spinner { display:flex; align-items:center; justify-content:center; width:100%; height:26rem; }
.ss-page-spinner:before { content:""; display:block; width:16rem; height:16rem; border:2rem solid {{colors.garage_spinner_border}}; border-top-color:{{colors.session_tab_marker_background}}; border-radius:{{radii.garage_spinner}}rem; animation:ss-page-spin 1s linear infinite; pointer-events:none; }
@keyframes ss-page-spin {
  from { transform:rotate(0deg); }
  to { transform:rotate(360deg); }
}
.ss-scroll-top { position:absolute; z-index:25; right:24rem; bottom:48rem; width:42rem; min-width:42rem; height:42rem; margin:0; padding:4rem; border:1rem solid {{colors.session_tab_marker_background}}; border-radius:{{radii.control}}rem; color:{{colors.session_tab_marker_background}}; background:linear-gradient({{colors.button_background_start}}, {{colors.button_background_end}}); box-shadow:0 0 8rem {{colors.session_tab_marker_background}}, inset 0 1rem {{colors.button_shadow_1}}; }
.ss-scroll-top:hover, .ss-scroll-top:focus { outline:1rem solid {{colors.session_tab_marker_background}}; outline-offset:2rem; box-shadow:0 0 14rem {{colors.session_tab_marker_background}}, inset 0 1rem {{colors.button_shadow_1}}; }
/* Paint the chevrons themselves with the control's accent. Native bitmap
   pixels do not inherit color, so an orange frame cannot tint a gray texture. */
.ss-scroll-top-icon { display:block; position:relative; width:32rem; height:32rem; color:inherit; pointer-events:none; }
.ss-scroll-top-icon:before, .ss-scroll-top-icon:after { content:""; display:block; box-sizing:border-box; position:absolute; left:10rem; width:12rem; height:12rem; border-top:3rem solid currentColor; border-left:3rem solid currentColor; transform:rotate(45deg); pointer-events:none; }
.ss-scroll-top-icon:before { top:8rem; }
.ss-scroll-top-icon:after { top:18rem; }
.ss-card-columns { position:relative; display:flex; align-items:flex-start; flex:0 1 620rem; min-width:0; width:620rem; max-width:100%; }
.ss-card-column { display:flex; flex-direction:column; flex:1 1 0rem; min-width:0; width:620rem; }
.ss-card-column-right { display:none; }
.ss-card-layout .ss-group { position:relative; flex:0 0 auto; width:100%; margin-bottom:16rem; }
.ss-two-columns .ss-card-columns { flex-basis:1304rem; width:1304rem; }
.ss-two-columns .ss-card-column { flex:0 0 620rem; }
.ss-two-columns .ss-card-column-right { display:flex; margin-left:64rem; }
.ss-card-stream .ss-card-column-left { padding-top:16rem; }
.ss-card-stream .ss-card-column-right { padding-top:68rem; }
.ss-card-stream .ss-card-columns:before { content:""; position:absolute; top:9rem; bottom:12rem; left:50%; width:1rem; background-image:linear-gradient({{colors.button_shadow_1}} 50%, {{colors.body_background}} 50%); background-size:1rem 10rem; background-repeat:repeat-y; pointer-events:none; }
.ss-card-stream .ss-card-columns:after { content:""; position:absolute; left:50%; top:2rem; width:8rem; height:8rem; margin-left:-4rem; border-left:1rem solid {{colors.button_shadow_1}}; border-top:1rem solid {{colors.button_shadow_1}}; transform:rotate(45deg); pointer-events:none; }
.ss-card-stream .ss-group:before { content:""; position:absolute; right:-32rem; top:24rem; width:32rem; height:1rem; background-image:linear-gradient(to right, {{colors.button_shadow_1}} 50%, {{colors.body_background}} 50%); background-size:10rem 1rem; background-repeat:repeat-x; pointer-events:none; }
.ss-card-stream .ss-group:after { content:""; position:absolute; right:-36rem; top:20rem; width:7rem; height:7rem; border:1rem solid {{colors.button_shadow_1}}; border-radius:{{radii.control}}rem; background:{{colors.window_background}}; pointer-events:none; }
.ss-card-stream .ss-card-column-right .ss-group:before { left:-32rem; right:auto; }
.ss-card-stream .ss-card-column-right .ss-group:after { left:-36rem; right:auto; }
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
    min-height:36rem;
    max-height:36rem;
    padding:0;
    margin:0;
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
    left:24rem;
    top:7rem;
    width:16rem;
    height:22rem;
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
.grz-session-footer-button .grz-session-footer-bar-0 { left:0; height:10rem; }
.grz-session-footer-button .grz-session-footer-bar-1 { left:6rem; height:15rem; }
.grz-session-footer-button .grz-session-footer-bar-2 { left:12rem; height:22rem; }
.grz-session-footer-button .grz-session-footer-rating {
    position:absolute;
    top:12rem;
    left:0;
    display:block;
    width:21rem;
    height:12rem;
    margin:0;
    color:{{colors.garage_wn8_text}};
    font-family:Warhelios, Arial, sans-serif;
    font-size:9rem;
    font-weight:normal;
    line-height:12rem;
    letter-spacing:0;
    text-align:center;
    white-space:nowrap;
    overflow:hidden;
    text-shadow:0 1rem 1rem {{colors.garage_wn8_text_shadow}};
    pointer-events:none;
}
.grz-session-footer-button:hover .grz-session-footer-rating { color:{{colors.garage_wn8_hover_text}}; }

/* CSS animation stays inside the renderer; no Python/JS frame callbacks.
   The spinner replaces the bars at their shared center, inside the fixed slot. */
.grz-session-footer-button .grz-session-footer-spinner {
    position:absolute;
    display:none;
    box-sizing:border-box;
    left:0;
    top:3rem;
    width:16rem;
    height:16rem;
    border:2rem solid {{colors.garage_spinner_border}};
    border-top-color:{{colors.garage_spinner_border_top_color}};
    border-radius:{{radii.garage_spinner}}rem;
    pointer-events:none;
    animation:none;
}
.grz-session-footer-busy .grz-session-footer-bar { visibility:hidden; }
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
    for section in ('colors', 'radii', 'opacity', 'scroll', 'maps', 'sessions', 'cards', 'wide_cards', 'window', 'date_time'):
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
            if section == 'date_time':
                if key == 'order':
                    checked = value if isinstance(value, text_type) and value in ('auto', 'DMY', 'MDY', 'YMD') else None
                elif key == 'separator':
                    checked = value if isinstance(value, text_type) and value in ('auto', '.', '/', '-') else None
                elif key == 'hour_format':
                    checked = value if isinstance(value, text_type) and value in ('auto', '12h', '24h') else None
                else:
                    checked = value if value == 'auto' or isinstance(value, integer_types) and not isinstance(value, bool) and 0 <= value <= 6 else None
                reason = 'expected_date_time_option'
            elif section == 'maps':
                checked = value if isinstance(value, text_type) and value in ('image', 'minimap') else None
                reason = 'expected_image_or_minimap'
            elif section == 'sessions':
                checked = value if isinstance(value, bool) else None
                reason = 'expected_boolean'
            elif section == 'window':
                checked = _window_setting(key, value)
                reason = ('expected_boolean' if key == 'maximized' else
                          'expected_integer_0_to_100' if key == 'background_transparency' else
                          'expected_integer_1_to_32768')
            elif section == 'wide_cards':
                checked = _number(value, 480, 1200)
                reason = 'expected_number_480_to_1200'
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


def _window_setting(key, value):
    if key == 'maximized':
        return value if isinstance(value, bool) else None
    if key == 'background_transparency':
        checked = _number(value, 0, 100)
    elif key in ('restored_width', 'restored_height'):
        checked = _number(value, 1, 32768)
    else:
        return None
    return int(checked) if checked is not None and int(checked) == checked else None


def window_settings_patch(values, command=False):
    """Validate a complete partial update; invalid leaves never become defaults."""
    if not isinstance(values, dict) or not values or any(key not in DEFAULT_CONFIG['window'] for key in values):
        return None
    checked = {}
    for key, value in values.items():
        if command and isinstance(value, (text_type, bytes)):
            if isinstance(value, bytes) and not isinstance(value, text_type):
                try:
                    value = value.decode('ascii')
                except UnicodeError:
                    return None
            if key == 'maximized':
                if value not in ('true', 'false'):
                    return None
                value = value == 'true'
            else:
                if len(value) > 32:
                    return None
                try:
                    value = float(value)
                except (ValueError, TypeError, OverflowError):
                    return None
        value = _window_setting(key, value)
        if value is None:
            return None
        checked[key] = value
    return checked


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
    # Earlier installations saved this complete default preset. Update only
    # that exact map in memory; custom/partial maps and the file stay intact.
    if isinstance(parsed, dict) and parsed.get('cards') == {
            'battles': 620, 'vehicles': 600, 'maps': 560, 'tiers': 520}:
        parsed['cards'] = copy.deepcopy(DEFAULT_CONFIG['cards'])
    if isinstance(parsed, dict) and parsed.get('wide_cards') == {
            'battles': 800, 'vehicles': 800, 'maps': 800, 'tiers': 800}:
        parsed['wide_cards'] = copy.deepcopy(DEFAULT_CONFIG['wide_cards'])
    colors = parsed.get('colors') if isinstance(parsed, dict) else None
    if (isinstance(colors, dict) and colors.get('garage_spinner_border') == 'rgba(207,190,140,0.25)' and
            colors.get('garage_spinner_border_top_color') == '#dfd3a4'):
        for key in ('garage_spinner_border', 'garage_spinner_border_top_color'):
            colors[key] = DEFAULT_CONFIG['colors'][key]
    radii = parsed.get('radii') if isinstance(parsed, dict) else None
    # The original 8px indicator clamped radius 5 to a circle. Preserve that
    # default shape for its 16px overlay while retaining custom radii.
    if isinstance(radii, dict) and radii.get('garage_spinner') == 5:
        radii['garage_spinner'] = DEFAULT_CONFIG['radii']['garage_spinner']
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
        'map_preview_mode': normalized['maps']['preview_mode'],
        'card_widths': copy.deepcopy(normalized['cards']),
        'wide_card_widths': copy.deepcopy(normalized['wide_cards']),
        'window_settings': copy.deepcopy(normalized['window']),
    }

