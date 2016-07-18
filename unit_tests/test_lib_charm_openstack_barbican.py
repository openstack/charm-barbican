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

from __future__ import absolute_import
from __future__ import print_function

import unittest

import mock

import charm.openstack.barbican as barbican


class Helper(unittest.TestCase):

    def setUp(self):
        self._patches = {}
        self._patches_start = {}
        # patch out the select_release to always return 'mitaka'
        self.patch(barbican.unitdata, 'kv')
        _getter = mock.MagicMock()
        _getter.get.return_value = barbican.BarbicanCharm.release
        self.kv.return_value = _getter

    def tearDown(self):
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch(self, obj, attr, return_value=None, **kwargs):
        mocked = mock.patch.object(obj, attr, **kwargs)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)


class TestOpenStackBarbican(Helper):

    def test_install(self):
        self.patch(barbican.BarbicanCharm, 'set_config_defined_certs_and_keys')
        self.patch(barbican.BarbicanCharm.singleton, 'install')
        barbican.install()
        self.install.assert_called_once_with()

    def test_setup_endpoint(self):
        self.patch(barbican.BarbicanCharm, 'set_config_defined_certs_and_keys')
        self.patch(barbican.BarbicanCharm, 'service_type',
                   new_callable=mock.PropertyMock)
        self.patch(barbican.BarbicanCharm, 'region',
                   new_callable=mock.PropertyMock)
        self.patch(barbican.BarbicanCharm, 'public_url',
                   new_callable=mock.PropertyMock)
        self.patch(barbican.BarbicanCharm, 'internal_url',
                   new_callable=mock.PropertyMock)
        self.patch(barbican.BarbicanCharm, 'admin_url',
                   new_callable=mock.PropertyMock)
        self.service_type.return_value = 'type1'
        self.region.return_value = 'region1'
        self.public_url.return_value = 'public_url'
        self.internal_url.return_value = 'internal_url'
        self.admin_url.return_value = 'admin_url'
        keystone = mock.MagicMock()
        barbican.setup_endpoint(keystone)
        keystone.register_endpoints.assert_called_once_with(
            'type1', 'region1', 'public_url', 'internal_url', 'admin_url')

    def test_render_configs(self):
        self.patch(barbican.BarbicanCharm, 'set_config_defined_certs_and_keys')
        self.patch(barbican.BarbicanCharm.singleton, 'render_with_interfaces')
        barbican.render_configs('interfaces-list')
        self.render_with_interfaces.assert_called_once_with(
            'interfaces-list')


class TestBarbicanConfigurationAdapter(Helper):

    @mock.patch('charmhelpers.core.hookenv.config')
    def test_barbican_configuration_adapter(self, config):
        self.patch(
            barbican.charms_openstack.adapters.APIConfigurationAdapter,
            'get_network_addresses')
        reply = {
            'keystone-api-version': '2',
        }
        config.side_effect = lambda: reply
        # Make one with no errors, api version 2
        a = barbican.BarbicanConfigurationAdapter()
        self.assertEqual(a.barbican_api_keystone_pipeline,
                         'cors keystone_authtoken context apiapp')
        self.assertEqual(a.barbican_api_pipeline,
                         'cors keystone_authtoken context apiapp')
        # Now test it with api version 3
        reply['keystone-api-version'] = '3'
        a = barbican.BarbicanConfigurationAdapter()
        self.assertEqual(a.barbican_api_keystone_pipeline,
                         'cors keystone_v3_authtoken context apiapp')
        self.assertEqual(a.barbican_api_pipeline,
                         'cors keystone_v3_authtoken context apiapp')
        # and a 'none' version
        reply['keystone-api-version'] = 'none'
        a = barbican.BarbicanConfigurationAdapter()
        self.assertEqual(a.barbican_api_keystone_pipeline,
                         'cors keystone_v3_authtoken context apiapp')
        self.assertEqual(a.barbican_api_pipeline,
                         'cors unauthenticated-context apiapp')
        # finally, try to create an invalid one.
        reply['keystone-api-version'] = None
        with self.assertRaises(ValueError):
            a = barbican.BarbicanConfigurationAdapter()


class TestBarbicanAdapters(Helper):

    @mock.patch('charmhelpers.core.hookenv.config')
    def test_barbican_adapters(self, config):
        reply = {
            'keystone-api-version': '2',
            # for the charms.openstack code, which breaks if we don't have:
            'os-public-hostname': 'host',
            'os-internal-hostname': 'internal',
            'os-admin-hostname': 'admin',
        }

        def cf(key=None):
            if key is not None:
                return reply[key]
            return reply

        config.side_effect = cf
        amqp_relation = mock.MagicMock()
        amqp_relation.relation_name = 'amqp'
        shared_db_relation = mock.MagicMock()
        shared_db_relation.relation_name = 'shared_db'
        other_relation = mock.MagicMock()
        other_relation.relation_name = 'other'
        other_relation.thingy = 'help'
        # verify that the class is created with a BarbicanConfigurationAdapter
        b = barbican.BarbicanAdapters([amqp_relation,
                                       shared_db_relation,
                                       other_relation])
        # ensure that the relevant things got put on.
        self.assertTrue(
            isinstance(
                b.other,
                barbican.charms_openstack.adapters.OpenStackRelationAdapter))
        self.assertTrue(isinstance(b.options,
                                   barbican.BarbicanConfigurationAdapter))


class TestBarbicanCharm(Helper):

    def test_action_generate_mkek(self):
        hsm = mock.MagicMock()
        hsm.plugin_data = {
            'library_path': 'path1',
            'login': '1234',
            'slot_id': 'slot1'
        }
        self.patch(barbican.hookenv, 'config')
        config = {
            'mkek-key-length': 5,
            'label-mkek': 'the-label'
        }

        def cf(key=None):
            if key is not None:
                return config[key]
            return config

        self.config.side_effect = cf
        self.patch(barbican.subprocess, 'check_call')
        self.patch(barbican.hookenv, 'log')
        # try generating a an mkek with no failure
        c = barbican.BarbicanCharm()
        c.action_generate_mkek(hsm)
        cmd = [
            'barbican-manage', 'hsm', 'gen_mkek',
            '--library-path', 'path1',
            '--passphrase', '1234',
            '--slot-id', 'slot1',
            '--length', '5',
            '--label', 'the-label',
        ]
        self.check_call.assert_called_once_with(cmd)
        self.log.assert_called_once_with(
            "barbican-mangage hsm gen_mkek succeeded")
        # and check that a problem is logged if it goes wrong

        def side_effect():
            raise barbican.subprocess.CalledProcessError

        self.check_call.side_effect = side_effect
        self.log.reset_mock()
        with self.assertRaises(Exception):
            c.action_generate_mkek(hsm)
            self.log.assert_called_once_with(
                "barbican-manage hsm gen_mkek failed.")

    def test_action_generate_hmac(self):
        hsm = mock.MagicMock()
        hsm.plugin_data = {
            'library_path': 'path1',
            'login': '1234',
            'slot_id': 'slot1'
        }
        self.patch(barbican.hookenv, 'config')
        config = {
            'hmac-key-length': 5,
            'label-hmac': 'the-label'
        }

        def cf(key=None):
            if key is not None:
                return config[key]
            return config

        self.config.side_effect = cf
        self.patch(barbican.subprocess, 'check_call')
        self.patch(barbican.hookenv, 'log')
        # try generating a an hmac with no failure
        c = barbican.BarbicanCharm()
        c.action_generate_hmac(hsm)
        cmd = [
            'barbican-manage', 'hsm', 'gen_hmac',
            '--library-path', 'path1',
            '--passphrase', '1234',
            '--slot-id', 'slot1',
            '--length', '5',
            '--label', 'the-label',
        ]
        self.check_call.assert_called_once_with(cmd)
        self.log.assert_called_once_with(
            "barbican-mangage hsm gen_hmac succeeded")
        # and check that a problem is logged if it goes wrong

        def side_effect():
            raise barbican.subprocess.CalledProcessError

        self.check_call.side_effect = side_effect
        self.log.reset_mock()
        with self.assertRaises(Exception):
            c.action_generate_hmac(hsm)
            self.log.assert_called_once_with(
                "barbican-manage hsm gen_hmac failed.")
