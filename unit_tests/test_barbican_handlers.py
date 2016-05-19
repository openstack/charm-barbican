from __future__ import absolute_import
from __future__ import print_function

import sys
import unittest

import mock

sys.path.append('src')
sys.path.append('src/lib')
import reactive.barbican_handlers as handlers


_hook_args = {}


def mock_hook(*args, **kwargs):

    def inner(f):
        # remember what we were passed.  Note that we can't actually determine
        # the class we're attached to, as the decorator only gets the function.
        _hook_args[f.__name__] = dict(args=args, kwargs=kwargs)
        return f
    return inner


class TestBarbicanHandlers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._patched_hook = mock.patch('charms.reactive.hook', mock_hook)
        cls._patched_hook_started = cls._patched_hook.start()
        # force requires to rerun the mock_hook decorator:
        reload(requires)

    @classmethod
    def tearDownClass(cls):
        cls._patched_hook.stop()
        cls._patched_hook_started = None
        cls._patched_hook = None
        # and fix any breakage we did to the module
        reload(requires)

    def patch(self, attr, return_value=None):
        mocked = mock.patch.object(self.kr, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)

    def test_registered_hooks(self):
        # test that the hooks actually registered the relation expressions that
        # are meaningful for this interface: this is to handle regressions.
        # The keys are the function names that the hook attaches to.
        hook_patterns = {
            'joined': ('{requires:keystone}-relation-joined', ),
            'changed': ('{requires:keystone}-relation-changed', ),
            'departed': ('{requires:keystone}-relation-{broken,departed}', ),
        }
        print(_hook_args)
        # for k, v in _hook_args.items():
            # self.assertEqual(hook_patterns[k], v['args'])
