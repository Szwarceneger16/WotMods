# -*- coding: utf-8 -*-
"""Optional owned WN8 child of the native random post-battle Gameface view.

RandomBattleResultsView exposes the displayed result's arenaUniqueID. Capture
that property after its original _onLoading, never infer it from the newest
ledger record or replace any native result model/statistic.
"""
from __future__ import absolute_import, unicode_literals

import json
import logging
import math
import weakref

try:
    number_types = (int, long, float)
    text_types = (basestring,)
except NameError:
    number_types = (int, float)
    text_types = (str,)

LOG = logging.getLogger('grz.sessionstats')
POSITION_ID = 0x47525738
INJECT_NAME = 'grz_session_stats_postbattle'
DATA_PROPERTY = 'grzPostBattleWn8'
MODULE_URL = 'coui://gui/gameface/mods/grz_session_stats/postbattle.js'
STYLE_URL = 'coui://gui/gameface/mods/grz_session_stats/postbattle.css'
UNAVAILABLE = {'state': 'unavailable', 'value': None}
_installed = None


def _rating_json(snapshot, labels=None):
    snapshot = snapshot if isinstance(snapshot, dict) else UNAVAILABLE
    state = snapshot.get('state')
    value = snapshot.get('value')
    try:
        valid = (not isinstance(value, bool) and isinstance(value, number_types) and
                 not math.isnan(value) and not math.isinf(value) and value >= 0)
    except (TypeError, ValueError, OverflowError):
        valid = False
    if state == 'ready' and not valid:
        state = 'unavailable'
    if state not in ('pending', 'ready', 'unavailable'):
        state = 'unavailable'
    payload = {'label': 'WN8', 'state': state, 'value': value if state == 'ready' else None}
    if labels:
        payload['labels'] = labels
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)


def build_child_class(gf_mod_inject):
    from frameworks.wulf import ViewModel
    from gui.impl.pub.view_component import ViewComponent

    class RatingModel(ViewModel):
        def __init__(self):
            self._rating = _rating_json(UNAVAILABLE)
            super(RatingModel, self).__init__(properties=1, commands=0)

        def _initialize(self):
            super(RatingModel, self)._initialize()
            self._addStringProperty(str('rating'), self._rating)

        def setRating(self, payload):
            if payload == self._rating:
                return False
            with self.transaction():
                self._setString(0, payload)
            self._rating = payload
            return True

    class PostBattleHostModel(ViewModel):
        def __init__(self):
            super(PostBattleHostModel, self).__init__(properties=2, commands=0)

        def _initialize(self):
            super(PostBattleHostModel, self)._initialize()
            gf_mod_inject(self, str(INJECT_NAME), styles=[str(STYLE_URL)], modules=[str(MODULE_URL)])
            self._rating_model = RatingModel()
            self._addViewModelProperty(str(DATA_PROPERTY), self._rating_model)

        def setRating(self, payload):
            return self._rating_model.setRating(payload)

    class PostBattleChild(ViewComponent):
        def __init__(self):
            super(PostBattleChild, self).__init__(model=PostBattleHostModel)

        def set_rating(self, payload):
            return self.getViewModel().setRating(payload)

    return PostBattleChild


class PostBattleInstallation(object):
    def __init__(self, view_class, child_class, provider):
        for name in ('_onLoading', 'getChildView', '_registerChild', '_unregisterChild'):
            if not callable(getattr(view_class, name, None)):
                raise TypeError('Native post-battle child contract unavailable: ' + name)
        if not callable(provider):
            raise TypeError('Post-battle rating provider unavailable')
        self.view_class, self.child_class, self._provider = view_class, child_class, provider
        self._enabled = True
        self._children = []
        self._labels = None
        self._warned = False
        self._defined_here = '_onLoading' in view_class.__dict__
        self._original = view_class._onLoading
        original, installation = self._original, self

        def on_loading(view, *args, **kwargs):
            result = original(view, *args, **kwargs)
            if installation._enabled:
                try:
                    installation._attach(view)
                except Exception:
                    installation._warn()
            return result

        self._wrapper = on_loading
        view_class._onLoading = on_loading

    def _warn(self):
        if not self._warned:
            self._warned = True
            LOG.warning('Post-battle WN8 unavailable; native result statistics remain unchanged.', exc_info=True)

    def _push(self, entry):
        if not self._enabled:
            return
        view, child = entry['view'](), entry['child']()
        if view is None or child is None:
            return
        try:
            if view.getChildView(POSITION_ID) is not child:
                return
            result = UNAVAILABLE
            if entry['arena_id'] is not None:
                result = self._provider(entry['arena_id'], account_key=entry['account_key'])
                if not isinstance(result, dict):
                    result = UNAVAILABLE
                owner = result.get('account_key')
                if owner is not None and (not isinstance(owner, text_types) or not owner or len(owner) > 256):
                    result = UNAVAILABLE
                    owner = None
                if entry['account_key'] is None and owner is not None:
                    entry['account_key'] = owner
                elif entry['account_key'] is not None and owner != entry['account_key']:
                    result = UNAVAILABLE
                if entry['account_key'] is None and result.get('state') == 'ready':
                    result = UNAVAILABLE
            # Provider code can synchronously stop the runtime or close a view.
            if self._enabled and view.getChildView(POSITION_ID) is child:
                child.set_rating(_rating_json(result, self._labels))
        except Exception:
            self._warn()
            try:
                if self._enabled and view.getChildView(POSITION_ID) is child:
                    child.set_rating(_rating_json(UNAVAILABLE, self._labels))
            except Exception:
                self._warn()

    def set_language(self, labels):
        if not self._enabled or not isinstance(labels, dict):
            return False
        from .localization import valid_text
        keys = ('format.thousands', 'format.missing', 'footer.processing', 'coverage.wn8.battle')
        checked = dict((key, labels[key]) for key in keys if key in labels and valid_text(key, labels[key]))
        if checked == self._labels:
            return False
        self._labels = checked
        self.refresh()
        return True

    def refresh(self):
        if not self._enabled:
            return False
        retained = []
        for entry in self._children:
            view, child = entry['view'](), entry['child']()
            if view is None or child is None:
                continue
            try:
                if view.getChildView(POSITION_ID) is not child:
                    continue
            except Exception:
                retained.append(entry)
                self._warn()
                continue
            retained.append(entry)
            self._push(entry)
            if not self._enabled:
                return False
        self._children = retained
        return True

    def _attach(self, view):
        if view.getChildView(POSITION_ID) is not None:
            return
        child = self.child_class()
        entry = {'view': weakref.ref(view), 'child': weakref.ref(child),
                 'arena_id': getattr(view, 'arenaUniqueID', None), 'account_key': None}
        try:
            if not self._enabled:
                return
            view._registerChild(POSITION_ID, child)
            if self._enabled and view.getChildView(POSITION_ID) is child:
                self._children.append(entry)
                self._push(entry)
                return
        except Exception:
            self._warn()
        if not self._remove_child(view, child):
            self._children.append(entry)

    def _remove_child(self, view, child):
        try:
            if view.getChildView(POSITION_ID) is not child:
                return True
            view._unregisterChild(child.uniqueID, True)
            return view.getChildView(POSITION_ID) is not child
        except Exception:
            self._warn()
            return False

    def uninstall(self):
        global _installed
        self._enabled = False
        self._provider = None
        retained = []
        for entry in self._children:
            view, child = entry['view'](), entry['child']()
            if view is not None and child is not None and not self._remove_child(view, child):
                retained.append(entry)
        self._children = retained
        if self.view_class.__dict__.get('_onLoading') is self._wrapper:
            if self._defined_here:
                self.view_class._onLoading = self._original
            else:
                del self.view_class._onLoading
        if _installed is self and not retained:
            _installed = None
        return not retained


def install(provider):
    global _installed
    if _installed is not None:
        if _installed._enabled:
            return _installed
        if not _installed.uninstall():
            return None
    try:
        from openwg_gameface import gf_mod_inject
        from gui.impl.lobby.battle_results.random_battle_results_view import RandomBattleResultsView
        child_class = build_child_class(gf_mod_inject)
        _installed = PostBattleInstallation(RandomBattleResultsView, child_class, provider)
        return _installed
    except Exception:
        LOG.warning('Optional post-battle WN8 host unavailable; native results remain unchanged.', exc_info=True)
        return None
