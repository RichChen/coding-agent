"""Local v0.1 policy boundary. Trusted code receives data, never executors/clients.

This is an in-process extension contract, not isolation for malicious Python.
Action proposals remain declarative; the host may execute only through an
explicitly configured controlled dispatcher.
"""
from __future__ import annotations
import copy
import json
import math
import re
from typing import Protocol


MAX_POLICY_BYTES = 65536


def json_data(value):
    from src.eval.contracts import _walk_forbidden
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    if len(encoded.encode()) > MAX_POLICY_BYTES:
        raise ValueError('policy data quota exceeded')
    cloned = json.loads(encoded)
    _walk_forbidden(cloned)
    return cloned


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'0\.\d+', value):
        raise ValueError('unsupported policy schema major/version')
    return value


class PolicyPlugin(Protocol):
    name: str
    schema_version: str
    async def decide(self, policy_input: dict) -> dict: ...


class NoOpPolicyPlugin:
    name = 'noop'
    schema_version = '0.1'
    async def decide(self, policy_input):
        return dict(schema_version=self.schema_version, candidates=[], state={}, events=[], action_proposals=[])


class FixturePolicyPlugin:
    name = 'fixture'
    schema_version = '0.1'
    def __init__(self, candidates=()):
        self.candidates = json_data(list(candidates))
    async def decide(self, policy_input):
        count = policy_input['state'].get('calls', 0)
        return dict(schema_version=self.schema_version, candidates=copy.deepcopy(self.candidates),
                    state={'calls': count+1}, events=[], action_proposals=[])


def validate_decision(raw):
    raw = json_data(raw)
    if not isinstance(raw, dict): raise ValueError('decision must be a JSON object')
    version(raw.get('schema_version'))
    for key, typ in [('candidates', list), ('state', dict), ('events', list), ('action_proposals', list)]:
        if not isinstance(raw.get(key, typ()), typ): raise ValueError(f'invalid {key}')
        raw.setdefault(key, typ())
    seen = set()
    for candidate in raw['candidates']:
        if not isinstance(candidate, dict): raise ValueError('candidate must be object')
        for key in ('id', 'text', 'source', 'reason'):
            if not isinstance(candidate.get(key), str) or not candidate[key]:
                raise ValueError(f'candidate requires {key}')
        if candidate['id'] in seen: raise ValueError('duplicate candidate id')
        seen.add(candidate['id'])
        if type(candidate.get('valid', True)) is not bool: raise ValueError('invalid validity flag')
        priority = candidate.get('priority', 0)
        if type(priority) not in (float, int) or not math.isfinite(priority): raise ValueError('invalid priority')
    return raw
