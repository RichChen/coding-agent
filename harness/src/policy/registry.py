"""Explicit host-owned registration, NOT a sandbox for untrusted Python.

YAML selects a registered ID; it cannot import modules or supply executable paths.
Registered factories receive only frozen public JSON. Mutable run state must be
externalized through the H4 state DTO; factories create a fresh instance per run.
"""
import hashlib
import inspect
import json
import re
import weakref

from src.policy.plugin import json_data, version


class PluginBindingError(ValueError):
    pass


_ISSUED = weakref.WeakSet()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class RegisteredPolicyPlugin:
    def __init__(self, implementation, identity, verifier):
        self._implementation = implementation
        self._identity = json_data(identity)
        self._verifier = verifier
        self.name = implementation.name
        self.schema_version = implementation.schema_version

    def fingerprint(self):
        self.verify()
        return json_data(self._identity)

    def verify(self):
        if self not in _ISSUED:
            raise PluginBindingError('plugin was not issued by a host registry')
        if (self._implementation.name != self._identity['name'] or
                self._implementation.schema_version != self._identity['wire_version'] or
                self.name != self._identity['name'] or self.schema_version != self._identity['wire_version']):
            raise PluginBindingError('plugin identity changed')
        try:
            actual = self._verifier()
        except Exception:
            raise PluginBindingError('plugin source verification failed') from None
        if actual != self._identity['implementation_sha256']:
            raise PluginBindingError('plugin source changed after registration')

    async def decide(self, data):
        self.verify()
        return await self._implementation.decide(json_data(data))


class PolicyPluginRegistry:
    def __init__(self):
        self._entries = {}

    def register(self, registration_id, *, name, wire_version, implementation_sha256,
                 public_config, factory, verify_source):
        if (not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', registration_id) or
                registration_id in ('noop', 'fixture') or registration_id in self._entries):
            raise PluginBindingError('invalid or duplicate plugin registration ID')
        version(wire_version)
        if not isinstance(name, str) or not name or not re.fullmatch(r'[0-9a-f]{64}', implementation_sha256):
            raise PluginBindingError('plugin name and source digest required')
        config = json_data(public_config)
        if not isinstance(config, dict):
            raise PluginBindingError('public configuration must be an object')
        if verify_source() != implementation_sha256:
            raise PluginBindingError('plugin source differs from approved digest')
        identity = dict(registration_id=registration_id, name=name, wire_version=wire_version,
                        implementation_sha256=implementation_sha256, config_sha256=digest(config),
                        state_contract='external-json-v1', capabilities=['context_candidates'],
                        action_dispatch='disabled')
        self._entries[registration_id] = (identity, json.dumps(config), factory, verify_source)

    def create(self, registration_id):
        if registration_id not in self._entries:
            raise PluginBindingError('plugin is not registered by host')
        identity, config, factory, verifier = self._entries[registration_id]
        if verifier() != identity['implementation_sha256']:
            raise PluginBindingError('plugin source changed before construction')
        implementation = factory(json.loads(config))
        if (getattr(implementation, 'name', None) != identity['name'] or
                getattr(implementation, 'schema_version', None) != identity['wire_version'] or
                not inspect.iscoroutinefunction(getattr(implementation, 'decide', None))):
            raise PluginBindingError('registered implementation does not match async contract')
        wrapped = RegisteredPolicyPlugin(implementation, identity, verifier)
        _ISSUED.add(wrapped)
        wrapped.verify()
        return wrapped
