"""Host integration for the reviewed RepoSkill H4 adapter (empty memory only).

No plugin auto-discovery, YAML import strings, private spec, client or executor.
The caller must supply an explicit trusted source root and its approved digest.
"""
import hashlib
import importlib
import importlib.util
from pathlib import Path
import sys

from src.policy.plugin import json_data
from src.policy.registry import PolicyPluginRegistry, PluginBindingError, digest


def source_files(root):
    root = Path(root).resolve(strict=True)
    package = root / 'reposkill_agent'
    if not (package / 'integrations' / 'harness_h4.py').is_file():
        raise PluginBindingError('RepoSkill H4 source missing')
    files = {}
    for path in sorted(package.rglob('*.py')):
        if path.is_symlink() or any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
                                    for p in (path, *path.parents) if p.is_relative_to(root)):
            raise PluginBindingError('plugin source links are not supported')
        if path.stat().st_size > 1024*1024 or len(files) >= 512:
            raise PluginBindingError('plugin source quota exceeded')
        files[path.relative_to(root).as_posix()] = path.read_bytes()
    if sum(map(len, files.values())) > 8*1024*1024:
        raise PluginBindingError('plugin source quota exceeded')
    return files


def source_digest(root):
    return digest({p: hashlib.sha256(b).hexdigest() for p, b in source_files(root).items()})


def load_adapter(root, approved_sha256):
    root = Path(root).resolve(strict=True)
    if source_digest(root) != approved_sha256:
        raise PluginBindingError('RepoSkill source differs from approved digest')
    package_root = root / 'reposkill_agent'
    # Avoid collisions with another installed checkout; never mutate sys.path.
    for name, module in tuple(sys.modules.items()):
        if name == 'reposkill_agent' or name.startswith('reposkill_agent.'):
            origin = getattr(module, '__file__', None)
            if not origin or not Path(origin).resolve().is_relative_to(package_root):
                raise PluginBindingError('another RepoSkill source is already imported')
    if 'reposkill_agent' not in sys.modules:
        spec = importlib.util.spec_from_file_location('reposkill_agent', package_root / '__init__.py',
                                                      submodule_search_locations=[str(package_root)])
        package = importlib.util.module_from_spec(spec)
        sys.modules['reposkill_agent'] = package
        try:
            spec.loader.exec_module(package)
        except BaseException:
            del sys.modules['reposkill_agent']
            raise
    adapter = importlib.import_module('reposkill_agent.integrations.harness_h4')
    if adapter.ADAPTER_VERSION != 'reposkill-h4-1':
        raise PluginBindingError('unreviewed RepoSkill adapter version')
    if source_digest(root) != approved_sha256:
        raise PluginBindingError('RepoSkill source changed during import')
    return adapter


def register_reposkill(registry: PolicyPluginRegistry, *, source_root, approved_sha256,
                      public_task, public_tree, enabled):
    adapter = load_adapter(source_root, approved_sha256)
    config = json_data(dict(adapter_version=adapter.ADAPTER_VERSION, public_task=public_task,
                           public_tree=sorted(public_tree), enabled=enabled, memory_snapshot=[]))
    if type(enabled) is not bool:
        raise PluginBindingError('enabled must be boolean')

    def factory(data):
        task, _ = adapter.decode_public_task(data['public_task'])
        return adapter.RepoSkillH4Plugin(task, tuple(data['public_tree']), enabled=data['enabled'])

    registry.register('reposkill', name='reposkill-public', wire_version='0.1',
                      implementation_sha256=approved_sha256, public_config=config, factory=factory,
                      verify_source=lambda: source_digest(source_root))
    return adapter


def register_public_memory(registry: PolicyPluginRegistry, *, source_root, approved_sha256,
                           public_task, variant, snapshot_path, target_root,
                           enabled=True, max_bytes=4096):
    """Bind the agent's public trajectory policy to one host-owned run."""
    adapter = load_adapter(source_root, approved_sha256)
    from reposkill_agent.memory.public_runtime_view import load_public_episodes, A5PublicMemoryPlugin
    episodes = load_public_episodes(Path(snapshot_path))
    task, _ = adapter.decode_public_task(public_task)
    config = json_data(dict(adapter_version=adapter.ADAPTER_VERSION, variant=variant,
                            snapshot_hash=episodes[0].snapshot_hash if episodes else None,
                            enabled=enabled, record_count=len(episodes)))
    if type(enabled) is not bool:
        raise PluginBindingError('enabled must be boolean')

    def factory(data):
        return A5PublicMemoryPlugin(variant=data['variant'], episodes=episodes,
                                    repo=task.repo_ref.repo_id, issue=task.issue_text,
                                    target_root=Path(target_root), max_bytes=max_bytes)

    registry.register('reposkill', name='reposkill-public', wire_version='0.1',
                      implementation_sha256=approved_sha256, public_config=config, factory=factory,
                      verify_source=lambda: source_digest(source_root))
    return adapter
