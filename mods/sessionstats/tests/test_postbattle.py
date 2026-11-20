# -*- coding: utf-8 -*-
"""Owned post-battle child lifecycle with strict native Wulf model doubles."""
from __future__ import unicode_literals

import gc
import json
import unittest
import weakref

import test_runtime as fixtures
from grz_session_stats import postbattle


class PostBattleTests(unittest.TestCase):
    inject_module = fixtures.NativeBindingTests.__dict__['inject_module']

    def setUp(self):
        fixtures.NativeBindingTests.__dict__['setUp'](self)
        self.calls = []
        self.answer = {'account_key': 'EU:7', 'state': 'pending', 'value': None}
        self.handles = []
        self.injections = []

    def tearDown(self):
        for handle in self.handles:
            handle.uninstall()
        if postbattle._installed is not None:
            postbattle._installed.uninstall()
        fixtures.NativeBindingTests.__dict__['tearDown'](self)

    def fake_inject(self, model, name, styles, modules):
        self.assertEqual(name, 'grz_session_stats_postbattle')
        self.assertEqual(styles, ['coui://gui/gameface/mods/grz_session_stats/postbattle.css'])
        self.assertEqual(modules, ['coui://gui/gameface/mods/grz_session_stats/postbattle.js'])
        self.injections.append((name, styles, modules))
        model._addViewModelProperty('ModInjectModel', object())

    def provider(self, arena_id, account_key=None):
        self.calls.append((arena_id, account_key))
        return dict(self.answer)

    def native_class(self, defined_loading=False):
        class Component(self.component):
            def getViewModel(self):
                return self.model

        class RandomBattleResultsView(Component):
            pass

        if defined_loading:
            def on_loading(view, *args, **kwargs):
                view.original_calls += 1
                view.arenaUniqueID = view.loaded_arena
                return 'native-loaded'
            RandomBattleResultsView._onLoading = on_loading
        self.inject_module('gui.impl.pub.view_component', ViewComponent=Component)
        return RandomBattleResultsView

    def install(self, provider=None, native_class=None, through_import=False):
        native_class = native_class or self.native_class()
        provider = provider or self.provider
        if through_import:
            self.inject_module('openwg_gameface', gf_mod_inject=self.fake_inject)
            self.inject_module('gui.impl.lobby.battle_results.random_battle_results_view',
                               RandomBattleResultsView=native_class)
            handle = postbattle.install(provider)
        else:
            child = postbattle.build_child_class(self.fake_inject)
            handle = postbattle.PostBattleInstallation(native_class, child, provider)
        self.assertIsNotNone(handle)
        self.handles.append(handle)
        return handle, native_class

    def attach(self, native_class, arena='arena-42'):
        view = native_class()
        if arena is not None:
            view.arenaUniqueID = arena
        view._onLoading()
        child = view.getChildView(postbattle.POSITION_ID)
        self.assertIsNotNone(child)
        return view, child, child.model.props[1][1]

    def state(self, model):
        self.assertEqual(model.props[0][0], 'rating')
        return json.loads(model.props[0][1])

    def assert_rating(self, model, state, value):
        self.assertEqual(self.state(model), {'label': 'WN8', 'state': state, 'value': value})

    def test_separate_two_property_host_and_one_property_child_never_publish_identity(self):
        self.answer.update(state='ready', value=1565, arena_id='private-arena', token='private-token')
        handle, native_class = self.install(through_import=True)
        view, child, model = self.attach(native_class)
        self.assertEqual(postbattle.POSITION_ID, 0x47525738)
        self.assertEqual(postbattle.INJECT_NAME, 'grz_session_stats_postbattle')
        self.assertEqual(postbattle.DATA_PROPERTY, 'grzPostBattleWn8')
        self.assertEqual([prop[0] for prop in child.model.props], ['ModInjectModel', 'grzPostBattleWn8'])
        self.assertEqual(len(model.props), 1)
        self.assertEqual(model.commands, [])
        self.assertEqual(child.model.commands, [])
        self.assert_rating(model, 'ready', 1565)
        self.assertEqual(set(self.state(model)), set(['label', 'state', 'value']))
        self.assertNotIn('EU:7', model.props[0][1])
        self.assertNotIn('private', model.props[0][1])
        self.assertEqual(self.calls, [('arena-42', None)])
        self.assertIs(postbattle.install(lambda *args, **kwargs: None), handle)
        self.assertEqual(view.original_calls, 1)

    def test_arena_is_captured_after_original_loading_and_is_not_read_from_later_view_state(self):
        native_class = self.native_class(defined_loading=True)
        original = native_class._onLoading
        handle, native_class = self.install(native_class=native_class)
        view = native_class()
        view.arenaUniqueID = 'stale-before-native-loading'
        view.loaded_arena = 'displayed-native-arena'
        self.assertEqual(view._onLoading(), 'native-loaded')
        self.assertEqual(self.calls, [('displayed-native-arena', None)])
        view.arenaUniqueID = 'later-unrelated-arena'
        handle.refresh()
        self.assertEqual(self.calls[-1], ('displayed-native-arena', 'EU:7'))
        self.assertEqual(view.original_calls, 1)
        self.assertTrue(handle.uninstall())
        self.assertEqual(native_class._onLoading, original)

    def test_unknown_initial_account_can_retry_then_remains_bound_even_when_unavailable(self):
        self.answer = {'account_key': None, 'state': 'pending', 'value': None}
        handle, native_class = self.install()
        view, child, model = self.attach(native_class)
        self.assert_rating(model, 'pending', None)
        self.answer = {'account_key': 'EU:7', 'state': 'unavailable', 'value': None}
        handle.refresh()
        self.assertEqual(self.calls[-1], ('arena-42', None))
        self.assert_rating(model, 'unavailable', None)
        self.answer = {'account_key': 'EU:8', 'state': 'ready', 'value': 9999}
        handle.refresh()
        self.assertEqual(self.calls[-1], ('arena-42', 'EU:7'))
        self.assert_rating(model, 'unavailable', None)
        self.answer = {'account_key': None, 'state': 'ready', 'value': 9999}
        handle.refresh()
        self.assert_rating(model, 'unavailable', None)
        self.answer = {'account_key': 'EU:7', 'state': 'ready', 'value': 0}
        handle.refresh()
        self.assert_rating(model, 'ready', 0)
        self.assertEqual(self.calls[-1], ('arena-42', 'EU:7'))

    def test_ready_without_known_account_is_unavailable_until_authoritative_owner_arrives(self):
        self.answer = {'account_key': None, 'state': 'ready', 'value': 1565}
        handle, native_class = self.install()
        view, child, model = self.attach(native_class)
        self.assert_rating(model, 'unavailable', None)
        self.answer['account_key'] = 'EU:7'
        handle.refresh()
        self.assertEqual(self.calls[-1], ('arena-42', None))
        self.assert_rating(model, 'ready', 1565)

    def test_missing_native_arena_never_uses_provider_or_guesses_a_recent_result(self):
        handle, native_class = self.install()
        view, child, model = self.attach(native_class, arena=None)
        self.assert_rating(model, 'unavailable', None)
        view.arenaUniqueID = 'a-later-result'
        handle.refresh()
        self.assertEqual(self.calls, [])
        self.assert_rating(model, 'unavailable', None)

    def test_only_finite_nonnegative_numeric_values_can_be_ready_and_zero_is_preserved(self):
        handle, native_class = self.install()
        view, child, model = self.attach(native_class)
        for value in [True, False, None, -1, '1565', float('nan'), float('inf'), float('-inf'), 10 ** 400, {}, []]:
            self.answer.update(state='ready', value=value)
            handle.refresh()
            self.assert_rating(model, 'unavailable', None)
        for value in [0, 1565, 1565.25]:
            self.answer.update(state='ready', value=value)
            handle.refresh()
            self.assert_rating(model, 'ready', value)
        for state in ['pending', 'unavailable', 'unknown']:
            self.answer.update(state=state, value=1565)
            handle.refresh()
            self.assert_rating(model, state if state != 'unknown' else 'unavailable', None)

    def test_unchanged_state_is_deduplicated_but_failed_native_write_retries_same_rating(self):
        handle, native_class = self.install()
        bad_view, bad_child, bad_model = self.attach(native_class, 'bad-arena')
        good_view, good_child, good_model = self.attach(native_class, 'good-arena')
        original = bad_model._setString
        calls = []

        def rejected(*args):
            calls.append(args)
            raise RuntimeError('Synthetic native write failure')

        bad_model._setString = rejected
        self.answer.update(state='ready', value=2500)
        handle.refresh()
        self.assert_rating(good_model, 'ready', 2500)
        self.assert_rating(bad_model, 'pending', None)
        self.assertTrue(calls)
        bad_model._setString = original
        handle.refresh()
        self.assert_rating(bad_model, 'ready', 2500)
        writes = []

        def counted(index, value):
            writes.append(value)
            return original(index, value)

        bad_model._setString = counted
        handle.refresh()
        self.assertEqual(writes, [])
        self.assertIs(bad_view.getChildView(postbattle.POSITION_ID), bad_child)
        self.assertIs(good_view.getChildView(postbattle.POSITION_ID), good_child)

    def test_transaction_exit_failure_does_not_commit_model_cache_before_retry(self):
        handle, native_class = self.install()
        view, child, model = self.attach(native_class)
        original_transaction = model.transaction
        previous = list(model.props)
        writes = []
        original_write = model._setString

        def counted(index, value):
            writes.append(value)
            return original_write(index, value)

        class RejectedTransaction(object):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                model.props[:] = previous
                raise RuntimeError('Synthetic native transaction rollback')

        model._setString = counted
        model.transaction = lambda: RejectedTransaction()
        payload = json.dumps({'label': 'WN8', 'state': 'ready', 'value': 1800}, sort_keys=True)
        with self.assertRaises(RuntimeError):
            child.set_rating(payload)
        self.assert_rating(model, 'pending', None)
        model.transaction = original_transaction
        self.assertTrue(child.set_rating(payload))
        self.assert_rating(model, 'ready', 1800)
        self.assertEqual(len(writes), 2)
        self.assertFalse(child.set_rating(payload))

    def test_language_uses_only_valid_public_labels_and_deduplicates_unchanged_payload(self):
        self.answer.update(state='ready', value=1565)
        handle, native_class = self.install()
        view, child, model = self.attach(native_class)
        labels = {'format.thousands': '\u00a0', 'format.missing': '\u2014',
                  'footer.processing': 'Przetwarzanie wynik\u00f3w',
                  'coverage.wn8.battle': 'Brak danych do obliczenia WN8.',
                  'metric.wn8': 'must not rename WN8', 'account_key': 'private-account'}
        self.assertTrue(handle.set_language(labels))
        payload = self.state(model)
        self.assertEqual(payload['label'], 'WN8')
        self.assertEqual((payload['state'], payload['value']), ('ready', 1565))
        self.assertEqual(set(payload), set(['label', 'state', 'value', 'labels']))
        self.assertEqual(payload['labels'], dict((key, labels[key]) for key in
                                               ('format.thousands', 'format.missing',
                                                'footer.processing', 'coverage.wn8.battle')))
        writes = []
        original = model._setString

        def counted(index, value):
            writes.append(value)
            return original(index, value)

        model._setString = counted
        self.assertFalse(handle.set_language(dict(labels)))
        handle.refresh()
        self.assertEqual(writes, [])
        self.assertTrue(handle.set_language({'format.thousands': '.', 'format.missing': '{0}',
                                            'footer.processing': 'invalid\nline',
                                            'coverage.wn8.battle': True}))
        self.assertEqual(self.state(model)['labels'], {'format.thousands': '.'})
        self.assertTrue(handle.set_language({}))
        self.assertNotIn('labels', self.state(model))
        handle.uninstall()
        self.assertFalse(handle.set_language(labels))

    def test_provider_exception_and_parent_query_failure_do_not_block_other_owned_children(self):
        fail = set()

        def provider(arena_id, account_key=None):
            self.calls.append((arena_id, account_key))
            if arena_id in fail:
                raise RuntimeError('Synthetic provider failure')
            return dict(self.answer)

        handle, native_class = self.install(provider)
        bad_view, bad_child, bad_model = self.attach(native_class, 'bad-arena')
        good_view, good_child, good_model = self.attach(native_class, 'good-arena')
        fail.add('bad-arena')
        self.answer.update(state='ready', value=1700)
        handle.refresh()
        self.assert_rating(bad_model, 'unavailable', None)
        self.assert_rating(good_model, 'ready', 1700)
        original = bad_view.getChildView

        def rejected(*args):
            raise RuntimeError('Synthetic native ownership query failure')

        bad_view.getChildView = rejected
        self.answer['value'] = 1900
        handle.refresh()
        self.assert_rating(good_model, 'ready', 1900)
        bad_view.getChildView = original
        fail.clear()
        handle.refresh()
        self.assert_rating(bad_model, 'ready', 1900)
        self.assertEqual(self.calls[-2:], [('bad-arena', 'EU:7'), ('good-arena', 'EU:7')])

    def test_occupied_position_and_detached_child_are_never_replaced_or_updated(self):
        handle, native_class = self.install()
        occupied = native_class()
        occupied.arenaUniqueID = 'foreign-arena'
        foreign = self.component()
        occupied.children[postbattle.POSITION_ID] = foreign
        occupied._onLoading()
        self.assertIs(occupied.getChildView(postbattle.POSITION_ID), foreign)
        self.assertEqual(self.calls, [])
        view, child, model = self.attach(native_class)
        before = self.state(model)
        replacement = self.component()
        view.children[postbattle.POSITION_ID] = replacement
        handle.refresh()
        self.assertEqual(self.state(model), before)
        self.assertEqual(self.calls, [('arena-42', None)])
        self.assertTrue(handle.uninstall())
        self.assertNotIn('_onLoading', native_class.__dict__)
        self.assertIs(view.getChildView(postbattle.POSITION_ID), replacement)
        self.assertIs(occupied.getChildView(postbattle.POSITION_ID), foreign)

    def test_partial_registration_is_rolled_back_and_failed_cleanup_remains_owned_for_retry(self):
        handle, native_class = self.install()
        view = native_class()
        view.arenaUniqueID = 'partially-registered'
        register, remove = view._registerChild, view._unregisterChild

        def partial(position, child):
            register(position, child)
            raise RuntimeError('Synthetic registration failure after attachment')

        view._registerChild = partial
        view._onLoading()
        self.assertIsNone(view.getChildView(postbattle.POSITION_ID))
        self.assertEqual(handle._children, [])
        view._unregisterChild = lambda *args: None
        view._onLoading()
        child = view.getChildView(postbattle.POSITION_ID)
        self.assertIsNotNone(child)
        self.assertEqual(len(handle._children), 1)
        self.assertFalse(handle.uninstall())
        view._unregisterChild = remove
        self.assertTrue(handle.uninstall())
        self.assertIsNone(view.getChildView(postbattle.POSITION_ID))
        self.assertEqual(handle._children, [])
        self.assertEqual(self.calls, [])

    def test_weak_ownership_does_not_retain_destroyed_views_or_models(self):
        handle, native_class = self.install()
        view, child, model = self.attach(native_class)
        view_ref, child_ref, model_ref = weakref.ref(view), weakref.ref(child), weakref.ref(model)
        del view, child, model
        gc.collect()
        self.assertIsNone(view_ref())
        self.assertIsNone(child_ref())
        self.assertIsNone(model_ref())
        handle.refresh()
        self.assertEqual(handle._children, [])

    def test_incomplete_uninstall_blocks_replacement_until_exact_child_cleanup_succeeds(self):
        handle, native_class = self.install(through_import=True)
        view, child, model = self.attach(native_class)
        remove = view._unregisterChild
        view._unregisterChild = lambda *args: None
        self.assertFalse(handle.uninstall())
        self.assertIs(postbattle._installed, handle)
        self.assertIsNone(postbattle.install(self.provider))
        self.assertIs(view.getChildView(postbattle.POSITION_ID), child)
        self.assertIs(postbattle._installed, handle)
        view._unregisterChild = remove
        replacement = postbattle.install(self.provider)
        self.assertIsNotNone(replacement)
        self.handles.append(replacement)
        self.assertIsNot(replacement, handle)
        self.assertIsNone(view.getChildView(postbattle.POSITION_ID))
        view._onLoading()
        self.assertIsNot(view.getChildView(postbattle.POSITION_ID), child)
        self.assertFalse(handle.refresh())

    def test_uninstall_preserves_later_wrapper_and_retained_callbacks_are_inert(self):
        handle, native_class = self.install()
        view, child, model = self.attach(native_class)
        ours = native_class._onLoading

        def later_wrapper(view, *args, **kwargs):
            return ours(view, *args, **kwargs)

        native_class._onLoading = later_wrapper
        retained_refresh = handle.refresh
        before = self.state(model)
        self.assertTrue(handle.uninstall())
        self.assertIs(native_class.__dict__['_onLoading'], later_wrapper)
        self.assertIsNone(view.getChildView(postbattle.POSITION_ID))
        self.assertFalse(retained_refresh())
        next_view = native_class()
        next_view.arenaUniqueID = 'must-not-read'
        next_view._onLoading()
        self.assertEqual(next_view.original_calls, 1)
        self.assertEqual(next_view.children, {})
        self.assertEqual(self.calls, [('arena-42', None)])
        self.assertEqual(self.state(model), before)

    def test_provider_can_stop_installation_reentrantly_without_publishing_or_reviving_child(self):
        holder = {}

        def provider(arena_id, account_key=None):
            holder['handle'].uninstall()
            return {'account_key': 'EU:7', 'state': 'ready', 'value': 9999}

        handle, native_class = self.install(provider)
        holder['handle'] = handle
        view = native_class()
        view.arenaUniqueID = 'stop-during-provider'
        view._onLoading()
        self.assertEqual(view.original_calls, 1)
        self.assertEqual(view.children, {})
        self.assertEqual(handle._children, [])
        self.assertFalse(handle.refresh())

    def test_invalid_native_contract_or_provider_does_not_patch_original_loading(self):
        native_class = self.native_class()
        original = native_class._onLoading
        child_class = postbattle.build_child_class(self.fake_inject)
        with self.assertRaises(TypeError):
            postbattle.PostBattleInstallation(native_class, child_class, None)
        self.assertNotIn('_onLoading', native_class.__dict__)
        self.assertEqual(native_class._onLoading, original)


if __name__ == '__main__':
    unittest.main()
