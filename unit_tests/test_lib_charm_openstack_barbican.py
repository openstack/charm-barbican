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

import mock
import charms_openstack.test_utils as test_utils

import charm.openstack.barbican as barbican


class Helper(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_release(barbican.BarbicanCharm.release)


class TestCustomProperties(Helper):

    def test_validate_keystone_api_version(self):
        config = mock.MagicMock()
        for v in ['2', '3', 'none']:
            config.keystone_api_version = v
            barbican.validate_keystone_api_version(config)
        # ensure that it fails
        with self.assertRaises(ValueError):
            config.keystone_api_version = 'fail-me'
            barbican.validate_keystone_api_version(config)

    def test_barbican_api_keystone_pipeline(self):
        config = mock.MagicMock()
        config.keystone_api_version = '2'
        self.assertEqual(
            barbican.barbican_api_keystone_pipeline(config),
            'cors http_proxy_to_wsgi keystone_authtoken context apiapp')
        config.keystone_api_version = ''
        self.assertEqual(
            barbican.barbican_api_keystone_pipeline(config),
            'cors http_proxy_to_wsgi keystone_v3_authtoken context apiapp')

    def test_barbican_api_pipeline(self):
        config = mock.MagicMock()
        config.keystone_api_version = '2'
        self.assertEqual(
            barbican.barbican_api_pipeline(config),
            'cors http_proxy_to_wsgi keystone_authtoken context apiapp')
        config.keystone_api_version = '3'
        self.assertEqual(
            barbican.barbican_api_pipeline(config),
            'cors http_proxy_to_wsgi keystone_v3_authtoken context apiapp')
        config.keystone_api_version = 'none'
        self.assertEqual(
            barbican.barbican_api_pipeline(config),
            'cors http_proxy_to_wsgi unauthenticated-context apiapp')

    def test_barbican_api_keystone_audit_pipeline(self):
        config = mock.MagicMock()
        config.keystone_api_version = '2'
        self.assertEqual(
            barbican.barbican_api_keystone_audit_pipeline(config),
            'http_proxy_to_wsgi keystone_authtoken context audit apiapp')
        config.keystone_api_version = ''
        self.assertEqual(
            barbican.barbican_api_keystone_audit_pipeline(config),
            'http_proxy_to_wsgi keystone_v3_authtoken context audit apiapp')


class TestHSMProperties(Helper):

    def setUp(self):
        super().setUp()
        self.data_none = {}
        self.data_set = {
            'library_path': 'a-path',
            'login': 'a-login',
            'slot_id': 'a-slot_id',
        }

    def test_library_path(self):
        hsm = mock.MagicMock()
        hsm.relation.plugin_data = self.data_none
        self.assertEqual(barbican.library_path(hsm), '')
        hsm.relation.plugin_data = self.data_set
        self.assertEqual(barbican.library_path(hsm), 'a-path')

    def test_login(self):
        hsm = mock.MagicMock()
        hsm.relation.plugin_data = self.data_none
        self.assertEqual(barbican.login(hsm), '')
        hsm.relation.plugin_data = self.data_set
        self.assertEqual(barbican.login(hsm), 'a-login')

    def test_slot_id(self):
        hsm = mock.MagicMock()
        hsm.relation.plugin_data = self.data_none
        self.assertEqual(barbican.slot_id(hsm), '')
        hsm.relation.plugin_data = self.data_set
        self.assertEqual(barbican.slot_id(hsm), 'a-slot_id')


class TestBarbicanCharm(Helper):

    def test_action_generate_mkek(self):
        hsm = mock.MagicMock()
        hsm.plugin_data = {
            'library_path': 'path1',
            'login': '1234',
            'slot_id': 'slot1'
        }
        self.patch_object(barbican.hookenv, 'config')
        config = {
            'mkek-key-length': 5,
            'label-mkek': 'the-label'
        }

        def cf(key=None):
            if key is not None:
                return config[key]
            return config

        self.config.side_effect = cf
        self.patch_object(barbican.subprocess, 'check_call')
        self.patch_object(barbican.hookenv, 'log')
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
        self.patch_object(barbican.hookenv, 'config')
        config = {
            'hmac-key-length': 5,
            'label-hmac': 'the-label'
        }

        def cf(key=None):
            if key is not None:
                return config[key]
            return config

        self.config.side_effect = cf
        self.patch_object(barbican.subprocess, 'check_call')
        self.patch_object(barbican.hookenv, 'log')
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
