# Overview

This charm provides the Barbican secret service for an OpenStack Cloud.

# Usage

Barbican relies on services from the mysql/percona, rabbitmq-server and keystone charms:

    juju deploy barbican
    juju deploy keystone
    juju deploy mysql
    juju deploy rabbitmq-server
    juju add-relation barbican rabbitmq-server
    juju add-relation barbican mysql
    juju add-relation barbican keystone

Optionally, but advisedly, Barbican should be deployed with an HSM subordinate charm.

# Bugs

Please report bugs on [Launchpad](https://bugs.launchpad.net/charm-barbican/+filebug).

For general questions please refer to the OpenStack [Charm Guide](https://github.com/openstack/charm-guide).
