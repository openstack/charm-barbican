# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

import reactive.barbican_handlers as handlers

import charms_openstack.test_utils as test_utils


class TestRegisteredHooks(test_utils.TestRegisteredHooks):

    def test_hooks(self):
        defaults = [
            'charm.installed',
            'amqp.connected',
            'shared-db.connected',
            'identity-service.connected',
            'config.changed',
            'update-status',
            'certificates.available']
        hook_set = {
            'when': {
                'render_stuff': ('shared-db.available',
                                 'identity-service.available',
                                 'amqp.available',),
                'secrets_plugin_configure': ('secrets.new-plugin',),
                'cluster_connected': ('ha.connected',),
                'run_db_migration': ('leadership.is_leader',
                                     'charm.installed',
                                     'shared-db.available',
                                     'first-render',),
            },
            'when_not': {
                'cluster_connected': ('ha.available',),
                'run_db_migration': ('db.synced',),
            },
        }
        # test that the hooks were registered via the
        # reactive.barbican_handlers
        self.registered_hooks_test_helper(handlers, hook_set, defaults)


class TestBarbicanHandlers(test_utils.PatchHelper):

    def test_render_stuff(self):
        barbican_charm = mock.MagicMock()
        self.patch_object(handlers.charm, 'provide_charm_instance',
                          new=mock.MagicMock())
        self.provide_charm_instance().__enter__.return_value = barbican_charm
        self.provide_charm_instance().__exit__.return_value = None
        self.patch_object(handlers.charm, 'optional_interfaces')

        def _optional_interfaces(args, *interfaces):
            self.assertEqual(interfaces, ('hsm.available',
                                          'secrets.available', ))
            return args + ('hsm', )

        self.optional_interfaces.side_effect = _optional_interfaces

        handlers.render_stuff('arg1', 'arg2')
        barbican_charm.render_with_interfaces.assert_called_once_with(
            ('arg1', 'arg2', 'hsm'))
        barbican_charm.assess_status.assert_called_once_with()

    def test_secrets_plugin_configure(self):
        self.patch_object(handlers.reactive, 'clear_flag')
        self.patch_object(handlers.reactive, 'set_flag')
        handlers.secrets_plugin_configure()
        self.clear_flag.assert_called_once_with('secrets.new-plugin')
        self.set_flag.assert_has_calls([
            mock.call('secrets.available'),
            mock.call('config.changed'),
        ])

    def test_cluster_connected(self):
        hacluster = mock.MagicMock()
        barbican_charm = mock.MagicMock()
        self.patch_object(handlers.charm, 'provide_charm_instance',
                          new=mock.MagicMock())
        self.provide_charm_instance().__enter__.return_value = barbican_charm
        self.provide_charm_instance().__exit__.return_value = None
        handlers.cluster_connected(hacluster)
        barbican_charm.configure_ha_resources.assert_called_once_with(
            hacluster)
        barbican_charm.assess_status.assert_called_once_with()
