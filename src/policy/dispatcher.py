"""Host-owned, read-only H5 action dispatcher.

The plugin supplies declarative ``read``/``search`` proposals. This module
validates them and executes a fixed Python RPC inside the already-running
Docker workspace. It never accepts shell text, writes, or plugin callables.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import PurePosixPath

from src.execution.base import ExecutionRequest, OutputQuotas, RunOutputMeter


RPC = r'''import json,pathlib,sys
req=json.load(sys.stdin); root=pathlib.Path('/workspace')
def safe(raw):
    if not isinstance(raw,str) or not raw or '\\' in raw: raise ValueError('path denied')
    rel=pathlib.PurePosixPath(raw)
    if rel.is_absolute() or '..' in rel.parts or any(p.startswith('.') for p in rel.parts): raise ValueError('path denied')
    p=(root/rel).resolve()
    if not p.is_relative_to(root): raise ValueError('path denied')
    return p
def read_file(raw):
    p=safe(raw)
    if (not p.is_file() or p.stat().st_size > req['max_bytes']
            or p.stat().st_size > req['max_output']):
        raise ValueError('file unavailable or too large')
    return {'path':raw,'content':p.read_text(encoding='utf-8'),'kind':'file'}
def search(query):
    if not isinstance(query,str) or not query.strip() or len(query.encode()) > 512: raise ValueError('invalid search query')
    needle=query.casefold(); hits=[]; total=0
    for p in sorted(root.rglob('*')):
        if not p.is_file() or any(part.startswith('.') for part in p.relative_to(root).parts): continue
        if len(hits) >= req['max_hits'] or total >= req['max_output']: break
        try: text=p.read_text(encoding='utf-8')
        except (UnicodeDecodeError,OSError): continue
        lines=[]
        for no,line in enumerate(text.splitlines(),1):
            if needle in line.casefold(): lines.append({'line':no,'text':line[:req['max_line_chars']]})
        if lines:
            item={'path':p.relative_to(root).as_posix(),'matches':lines}
            blob=json.dumps(item,ensure_ascii=False,separators=(',',':'))
            if total+len(blob.encode()) > req['max_output']: break
            hits.append(item); total += len(blob.encode())
    return {'query':query,'matches':hits,'kind':'search'}
try:
    if req['tool']=='read': result=read_file(req['path'])
    elif req['tool']=='search': result=search(req['query'])
    else: raise ValueError('dispatcher tool denied')
    print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
except Exception as exc:
    print(json.dumps({'error':str(exc)[:160]},ensure_ascii=True,separators=(',',':')))
    raise
'''


class DispatcherError(ValueError):
    pass


class ReadSearchDispatcher:
    name = "host-read-search-v1"

    def __init__(self, backend, *, max_calls=8, max_file_bytes=1_048_576,
                 max_output_bytes=16_000, max_hits=20, max_line_chars=400):
        if backend is None or getattr(backend, "profile", None) != "docker_linux":
            raise DispatcherError("read/search dispatcher requires docker_linux backend")
        if max_calls < 0 or max_file_bytes <= 0 or max_output_bytes <= 0:
            raise DispatcherError("invalid dispatcher limits")
        self.backend = backend
        self.max_calls = max_calls
        self.max_file_bytes = max_file_bytes
        self.max_output_bytes = max_output_bytes
        self.max_hits = max_hits
        self.max_line_chars = max_line_chars

    def fingerprint(self):
        return dict(name=self.name, tools=["read", "search"], max_calls=self.max_calls,
                    max_file_bytes=self.max_file_bytes, max_output_bytes=self.max_output_bytes,
                    max_hits=self.max_hits, max_line_chars=self.max_line_chars,
                    backend=self.backend.capabilities)

    @staticmethod
    def _validate(proposal):
        if not isinstance(proposal, dict): raise DispatcherError("proposal must be an object")
        tool=proposal.get("tool")
        if tool not in ("read", "search"): raise DispatcherError("proposal tool is not enabled")
        proposal_id=proposal.get("proposal_id")
        if not isinstance(proposal_id,str) or not proposal_id: raise DispatcherError("proposal id required")
        if tool == "read":
            path=proposal.get("path")
            rel=PurePosixPath(path) if isinstance(path,str) else None
            if rel is None or rel.is_absolute() or ".." in rel.parts or "\\" in path or any(p.startswith('.') for p in rel.parts):
                raise DispatcherError("read path denied")
            return dict(proposal_id=proposal_id, tool=tool, path=path)
        query=proposal.get("query")
        if not isinstance(query,str) or not query.strip() or len(query.encode()) > 512:
            raise DispatcherError("search query denied")
        return dict(proposal_id=proposal_id, tool=tool, query=query)

    async def dispatch(self, proposal, *, deadline_mono, cancel_event, run_meter, artifact_dir=None):
        item=self._validate(proposal)
        operation_id="h5-dispatch-"+uuid.uuid4().hex
        attempt_id=uuid.uuid4().hex
        request=dict(tool=item["tool"],max_bytes=self.max_file_bytes,max_hits=self.max_hits,
                     max_output=self.max_output_bytes,max_line_chars=self.max_line_chars,**
                     {k:item[k] for k in ("path","query") if k in item})
        execution=await self.backend.execute(ExecutionRequest(
            argv=["/usr/local/bin/python","-I","-S","-c",RPC], stdin_bytes=json.dumps(request).encode(),
            env={}, operation_id=operation_id, attempt_id=attempt_id, deadline_mono=deadline_mono,
            cancel_event=cancel_event, run_meter=run_meter or RunOutputMeter(),
            quotas=OutputQuotas(memory_per_stream_bytes=65536, artifact_per_tool_bytes=0,
                                run_total_bytes=(run_meter or RunOutputMeter()).limit_bytes), artifact_dir=artifact_dir))
        parsed=None
        if execution.status.value == "succeeded":
            try: parsed=json.loads(execution.stdout.text_preview)
            except (ValueError, TypeError): parsed=None
        output=parsed if isinstance(parsed,dict) else {"error": execution.error_message or "dispatcher execution failed"}
        content=json.dumps(output,ensure_ascii=False,sort_keys=True,separators=(",",":"))
        return dict(operation_id=operation_id,attempt_id=attempt_id,proposal_id=item["proposal_id"],
                    tool=item["tool"],request=item,status=execution.status.value,success=execution.status.value=="succeeded",
                    output=content,output_sha256=hashlib.sha256(content.encode()).hexdigest(),
                    observation_sha256=hashlib.sha256(content.encode()).hexdigest(),
                    bytes_seen=execution.bytes_seen,truncated=execution.truncated,
                    cleanup_state=execution.cleanup_state.value,cleanup_ok=execution.cleanup_state.value=="cleaned",
                    duration_ms=execution.duration_ms,
                    raw_meta=(f"status={execution.status.value};error_kind={execution.error_kind};"
                              f"exit_code={execution.exit_code}"))
