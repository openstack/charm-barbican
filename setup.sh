#!/bin/bash
export http_proxy=http://squid.internal:3128                                                              
export https_proxy=http://squid.internal:3128
export JUJU_REPOSITORY="$(pwd)/build"
#export INTERFACE_PATH=interfaces
export LAYER_PATH=layers
rm -rf $JUJU_REPOSITORY
mkdir -p $JUJU_REPOSITORY
#if [[ ! -d $INTERFACE_PATH ]]; then
#    mkdir $INTERFACE_PATH
#    ( cd $INTERFACE_PATH;
#      git clone https://git.launchpad.net/~gnuoy/charms/+source/interface-rabbitmq rabbitmq;
#      git clone git+ssh://git.launchpad.net/~openstack-charmers-layers/charms/+source/interface-keystone keystone;
#      git clone https://git.launchpad.net/~openstack-charmers-layers/charms/+source/interface-mysql-shared mysql-shared; )
#fi
if [[ ! -d $LAYER_PATH ]]; then
    mkdir $LAYER_PATH
    ( cd $LAYER_PATH;
      git clone git+ssh://git.launchpad.net/~openstack-charmers-layers/charms/+source/reactive-openstack-layer openstack; )
fi
make clean
make generate
./kill_charms.sh barbican
juju-deployer -c barbican.yaml
echo $JUJU_REPOSITORY
