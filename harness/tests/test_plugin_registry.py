import copy
import json

import pytest

from src.config.schema import HarnessConfig
from src.harness.factory import build_agent
from src.llm.client import LLMResponse
from src.policy.plugin import NoOpPolicyPlugin
from src.policy.registry import PolicyPluginRegistry, PluginBindingError
from src.runtime.session import RunSession, runtime_fingerprint
from src.runtime.window import WindowPolicy, WindowPolicyHooks
from src.tracing.store import StoreError
from tests.fixtures.h4_worker import make_loop, expected


class External:
    name = 'external'
    schema_version = '0.1'
    def __init__(self, config):
        self.config = config
        self.calls = 0  # Test observation only, not used to compute decisions.
    async def decide(self, data):
        self.calls += 1
        return dict(schema_version='0.1', candidates=[], events=[], action_proposals=[{'tool':'read'}],
                    state={'calls': data['state'].get('calls', 0)+1})


def registry(config=None, source=None, factory=External):
    source = source if source is not None else ['a'*64]
    r = PolicyPluginRegistry()
    r.register('external', name='external', wire_version='0.1', implementation_sha256=source[0],
               public_config=config or {'tree':['a.py'], 'task':'public', 'snapshot':[]},
               factory=factory, verify_source=lambda:source[0])
    return r


def test_registry_rejects_unregistered_selector_and_arbitrary_imports(tmp_path):
    config = HarnessConfig.model_validate({'llm':{'base_url':'https://example.invalid'},
             'runtime':{'context':{'strategy':'none','plugin':'external'}}}).model_dump()
    with pytest.raises(ValueError, match='registration'):
        build_agent(config, tmp_path)
    with pytest.raises(PluginBindingError, match='not registered'):
        build_agent(config, tmp_path, plugin_registry=PolicyPluginRegistry())
    agent = build_agent(config, tmp_path, plugin_registry=registry())
    assert agent.hooks.plugin.name == 'external'
    with pytest.raises(ValueError):
        HarnessConfig.model_validate({'llm':{'base_url':'x'},'runtime':{'context':{'plugin':'evil.module:call'}}})


@pytest.mark.parametrize('config', [{'tree':['b.py']}, {'task':'other'}, {'snapshot':['new']}, {'enabled':False}])
def test_public_configuration_is_frozen_and_fingerprinted(config):
    original = {'tree':['a.py']}
    r = registry(original)
    original['tree'].append('mutated.py')
    p = r.create('external')
    assert p._implementation.config == {'tree':['a.py']}
    assert p.fingerprint() != registry(config).create('external').fingerprint()
    assert p is not r.create('external')
    assert p.fingerprint() == r.create('external').fingerprint()


async def test_source_drift_is_not_degraded_to_noop():
    source = ['a'*64]
    r = registry(source=source)
    p = r.create('external')
    source[0] = 'b'*64
    with pytest.raises(PluginBindingError):
        p.fingerprint()
    with pytest.raises(PluginBindingError):
        r.create('external')
    with pytest.raises(PluginBindingError):
        await p.decide({})


def test_duplicate_private_config_and_sync_implementation_rejected():
    r = registry()
    with pytest.raises(PluginBindingError, match='duplicate'):
        r.register('external', name='external', wire_version='0.1', implementation_sha256='a'*64,
                   public_config={}, factory=External, verify_source=lambda:'a'*64)
    with pytest.raises(ValueError):
        registry({'hidden_tests': 'no'})
    class Sync(External):
        def decide(self, data): return {}
    with pytest.raises(PluginBindingError, match='async'):
        registry(factory=Sync).create('external')


async def test_unregistered_external_still_rejected_by_persistent_session(tmp_path):
    workspace=tmp_path/'workspace'; workspace.mkdir()
    loop=make_loop(workspace, resumed=True)
    loop.hooks=WindowPolicyHooks(WindowPolicy(), External({}))
    with RunSession.create(tmp_path/'run',task_id='test',expected=expected(workspace)) as session:
        with pytest.raises(StoreError, match='host-registered'):
            await session.run(loop,'public')
        assert loop.llm._call_count == 0


class StopBeforeModel(BaseException):
    pass


async def test_registered_restore_reuses_view_and_rejects_configuration_drift(tmp_path):
    workspace=tmp_path/'workspace'; workspace.mkdir()
    directory=tmp_path/'run'
    r=registry()
    loop=make_loop(workspace, resumed=True)
    loop.hooks=WindowPolicyHooks(WindowPolicy(), r.create('external'))
    with RunSession.create(directory,task_id='test',expected=expected(workspace)) as session:
        append=session.append
        def interrupt(kind,payload,**meta):
            result=append(kind,payload,**meta)
            if kind=='context.prepared': raise StopBeforeModel()
            return result
        session.append=interrupt
        with pytest.raises(StopBeforeModel):
            await session.run(loop,'public')
        assert loop.llm._call_count == 0
    prepared=RunSession.replay(directory).context['view']
    with RunSession.resume(directory,expected=expected(workspace)) as session:
        changed=make_loop(workspace,resumed=True)
        changed.hooks=WindowPolicyHooks(WindowPolicy(), registry({'tree':['changed.py']}).create('external'))
        with pytest.raises(StoreError, match='configuration changed'):
            await session.run(changed,'public')
        assert changed.llm._call_count == 0
    with RunSession.resume(directory,expected=expected(workspace)) as session:
        restored=make_loop(workspace,resumed=True)
        restored.hooks=WindowPolicyHooks(WindowPolicy(), r.create('external'))
        result=await session.run(restored,'public')
        assert result.success
        assert restored.llm.calls[0]['messages'] == prepared
        assert restored.hooks.plugin._implementation.calls == 0
        plugin=result.context_events[0]['plugin']
        assert plugin['action_proposals'][0]['reason']=='dispatcher_not_enabled'
        assert session.state.plugin_state['h4']['plugin_state']=={'calls':1}
    assert RunSession.replay(directory).terminal['success']
