#!/bin/bash

set -ex

# Create demo/testing users, tenants and flavor
openstack project create demo
openstack user create --project demo --password pass --email demo@dev.null demo
openstack role add --user demo --project demo Member
openstack project create alt_demo
openstack user create --project alt_demo --password secret --email demo@dev.null alt_demo
openstack role add --user alt_demo --project alt_demo Member
