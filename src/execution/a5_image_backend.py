"""Complete immutable image base with bounded typed candidate deltas."""
import asyncio
import json

from src.eval.a5_image_tree import canonical, tree_hash, validate_delta, LIMIT
from src.execution.docker import DockerExecutionBackend


class A5ImageBackend(DockerExecutionBackend):
    def __init__(self, *, manifest, editable_paths, **kwargs):
        super().__init__(**kwargs)
        if tree_hash(manifest['entries']) != manifest['source_tree_hash']:
            raise ValueError('image base manifest hash mismatch')
        self.manifest = manifest
        self.editable_paths = tuple(editable_paths)
        self.candidate_delta = None
        self.base_verified = False

    @property
    def capabilities(self):
        return {**super().capabilities, 'transport': 'image_backed_base_plus_delta',
                'source_tree_hash': self.manifest['source_tree_hash'],
                'delta_schema': 'a5.typed-tree.delta.v1'}

    async def tree_command(self, action, payload=None):
        return json.loads(await self._ok('exec', *(['-i'] if payload is not None else []),
            self.name, '/usr/local/bin/python', '-I', '-S', '/opt/a5-tree.py', action,
            data=canonical(payload) if payload is not None else None,
            limit=LIMIT, timeout=60))

    async def start(self, files=None):
        if files:
            raise ValueError('image backend seeds from bound image only')
        try:
            await super().start({})
            actual = await self.tree_command('seed')
            if actual != self.manifest['source_tree_hash']:
                raise ValueError('live image base mismatch')
            self.base_verified = True
        except BaseException:
            await self.close()
            raise

    async def export_delta(self):
        # Imports may drop __pycache__; strip bytecode before allowlist export.
        await self._ok('exec', self.name, '/usr/local/bin/python', '-I', '-S', '-c',
            "import pathlib,shutil\n"
            "root=pathlib.Path('/workspace')\n"
            "[shutil.rmtree(p, ignore_errors=True) for p in root.rglob('__pycache__')]\n"
            "[p.unlink() for p in root.rglob('*.py[co]') if p.is_file()]\n")
        # Container file tools rewrite via mkstemp/os.replace and can change mode;
        # restore declared file modes so typed-tree export accepts content edits.
        await self._ok('exec', self.name, '/usr/local/bin/python', '-I', '-S', '-c',
            "import json,pathlib\n"
            "m=json.loads(pathlib.Path('/opt/a5-tree.json').read_text())\n"
            "root=pathlib.Path('/workspace')\n"
            "for name, meta in m['entries'].items():\n"
            "    p=root/name\n"
            "    if meta.get('kind')=='file' and p.is_file() and not p.is_symlink():\n"
            "        p.chmod(meta['mode'])\n")
        delta = await self.tree_command('export', {'allowed_paths': list(self.editable_paths)})
        validate_delta(self.manifest, delta, self.editable_paths)
        self.candidate_delta = delta
        return delta

    async def apply_candidate(self, delta):
        validate_delta(self.manifest, delta, self.editable_paths)
        actual = await self.tree_command('apply', {'allowed_paths': list(self.editable_paths), 'delta': delta})
        if actual != delta['candidate_tree_hash']:
            raise ValueError('reconstructed candidate mismatch')
        return actual

    async def close(self, *, snapshot=False):
        if snapshot and self.active:
            try:
                await self.export_delta()
                # AgentLoop expects a snapshot marker; the real candidate is candidate_delta.
                self.snapshot = {}
            except (Exception, asyncio.CancelledError) as exc:
                self.snapshot_error = type(exc).__name__ + ': ' + str(exc)
        return await super().close(snapshot=False)
