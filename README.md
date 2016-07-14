# Barbican Source Charm

THIS CHARM IS FOR EXPERIMENTAL USE AT PRESENT.

This repository is for the reactive, layered,
[Barbican](https://wiki.openstack.org/wiki/Barbican) _source_ charm. From the
[wiki](https://wiki.openstack.org/wiki/Barbican) 'Barbican is a REST API
designed for the secure storage, provisioning and management of secrets such as
passwords, encryption keys and X.509 Certificates. It is aimed at being useful
for all environments, including large ephemeral Clouds.'

Barbican can be used without an HSM for test purposes.

# Plugins

The Barbican charm currently supports the following plugins:

 - charm-barbican-softhsm

However, due to an odd quirk of interelating software issues, barbican +
SoftHSM2 + OpenSSL < 1.0.2h is not functionaly due to a missing feature in
OpenSSL (EVP_aes_128_wrap_pad specifically).

Thus the plugin interface is _currently_ provided to show how to interface an
HSM to the barbican charm.

# Creating the primary MKEK and primary HMAC

Barbican (can use|uses) a Master Key Encryption Key (MKEK) scheme to wrap other
keys so that in the course of issuing new encryption keys, it does not exhaust
the storage capacity of an HSM.

See [KMIP MKEK Model
Plugin](https://specs.openstack.org/openstack/barbican-specs/specs/kilo/barbican-mkek-model.html)
for more details.

Barbican itself can generate the MKEK and HMAC keys and store them in the
associated HSM through the use of two actions 'generate-mkek' and
'generate-hmac'.

The names of the keys are stored in the configuration for the service as
'mkek-label' and 'hmac-label'.  These default to 'primarymkek' and
'primaryhmac' respectively.

Note that these keys are not recoverable _from_ the HSM.  If the HSM has
already been configured with these keys then these actions would overwrite the
existing key. So only use them for the initial implementation or to change the
MKEK and HMAC keys in the HSM.

## Use of actions

For juju 1.x:
```bash
juju action do generate-mkek
```

For juju 2.x:

```bash
juju run-action generate-mkek
```

Note that, depending on the HSM, it may only be possible to do this ONCE as the
HSM may reject setting up the keys more than once.

# Developer Notes

The Barbican charm has to be able to set `[crypto]` and `[xxx_plugin]` sections
in the `barbican-api.conf` file. This data comes via the `barbican-hsm`
interface from a charm (probably a subordinate) that provides the interface.

On the `barbican-hsm` interface the data is provided in the `plugin_data()`
method of the interface (or if it is adapted) in the `plugin_data` property.

The theory of operation for the crypto plugin is that a local library that
supports the PKCS#11 interface that Barbican can talk to locally.

Note(AJK): it is not clear yet how a clustered Barbican can be created with
a single HSM backend.  It's likely to be a separate piece of hardward with
a local library that talks to it.

In order for Barbican to be configured for the example softhsm2 library, the
configuration file needs to include the entries:

```ini
[crypto]
enabled_crypto_plugins = p11_crypto

[p11_crypto_plugin]
library_path = '/usr/lib/libCryptoki2_64.so'
login = 'catt'
mkek_label = 'primarymkek'
mkek_length = 32
hmac_label = 'primaryhmac' slot_id = <slot_id>
```

Note that the /var/lib/softhsm/tokens directory HAS to exist as otherwise the
softhsm2-util command won't work.
