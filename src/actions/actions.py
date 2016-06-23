#!/usr/bin/env python3
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

import os
import sys

# Load modules from $CHARM_DIR/lib
sys.path.append('lib')

from charms.layer import basic
basic.bootstrap_charm_deps()
basic.init_config_states()

import charms.reactive as reactive

import charmhelpers.core.hookenv as hookenv

import charm.openstack.barbican as barbican


def generate_mkek_action(*args):
    """Generate an MKEK in the backend HSM"""
    # try and get the reactive relation instance for hsm:
    # We only do this because there's no @action(<name>) yet that we could
    # access from the reactive file.
    hsm = reactive.RelationBase.from_state('hsm.available')
    if hsm is None:
        hookenv.action_fail(
            "Can't generate an MKEK in associated HSM because HSM is not "
            "available.")
        return
    barbican.generate_mkek(hsm)


def generate_hmac_action(*args):
    """Generate an HMAC in the backend HSM"""
    # try and get the reactive relation instance for hsm:
    # We only do this because there's no @action(<name>) yet that we could
    # access from the reactive file.
    hsm = reactive.RelationBase.from_state('hsm.available')
    if hsm is None:
        hookenv.action_fail(
            "Can't generate an HMAC in associated HSM because HSM is not "
            "available.")
    barbican.generate_hmac(hsm)


# Actions to function mapping, to allow for illegal python action names that
# can map to a python function.
ACTIONS = {
    "generate-mkek": generate_mkek_action,
    "generate-hmac": generate_hmac_action,
}


def main(args):
    action_name = os.path.basename(args[0])
    try:
        action = ACTIONS[action_name]
    except KeyError:
        return "Action %s undefined" % action_name
    else:
        try:
            action(args)
        except Exception as e:
            hookenv.action_fail(str(e))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
