#!/usr/bin/env python3
"""Prepare a complete pinned Flask tree and a private evaluator calibration package."""
import argparse
import asyncio
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from src.eval.grader import save_json, encode_snapshot, tree_hash
from src.execution.docker import validate_files, TRANSFER_LIMIT, MAX_FILES
from src.tracing.artifacts import atomic_replace

ROOT=Path(__file__).resolve().parents[1]
REV='4c288bc97ea371817199908d0d9b12de9dae327e'
BASE_IMAGE='python@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9'
FIXTURE=ROOT/'tests/fixtures/repos/swebench_pallets__flask-4992'
URL=f'https://codeload.github.com/pallets/flask/tar.gz/{REV}'


def extract(data):
    files={}
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
        members=archive.getmembers()
        roots={m.name.split('/')[0] for m in members}
        if len(roots)!=1: raise ValueError('archive has multiple roots')
        for member in members:
            if member.isdir(): continue
            if not member.isfile(): raise ValueError('nonregular archive member: '+member.name)
            relative=member.name.partition('/')[2]
            if relative in files or member.size>TRANSFER_LIMIT: raise ValueError('duplicate/oversized archive member')
            files[relative]=archive.extractfile(member).read(TRANSFER_LIMIT+1)
            validate_files(files)
    return files


def inventory():
    result=[]
    for folder in sorted((ROOT/'tests/fixtures/repos').glob('swebench*')):
        files={}
        for path in folder.rglob('*'):
            rel=path.relative_to(folder)
            if any(x in ('.oracle','.git','__pycache__') for x in rel.parts): continue
            if path.is_file(): files[rel.as_posix()]=path.stat().st_size
        size=sum(files.values()); setup=(folder/'SETUP.md').read_text(encoding='utf-8')
        match=re.search(r'swebench_python: `([^`]+)`',setup)
        result.append(dict(task_id=folder.name,files=len(files),bytes=size,python=match.group(1) if match else None,
            within_transfer_quota=size<=TRANSFER_LIMIT and len(files)<=MAX_FILES,
            complete_upstream_tree=False,environment_verified=False,
            decision='needs_full_source_and_pinned_environment' if size<=TRANSFER_LIMIT and len(files)<=MAX_FILES else 'blocked_transfer_quota'))
    return result


async def prepare(output, archive_path=None, werkzeug_version='2.3.7'):
    output.mkdir(parents=True,exist_ok=False)
    save_json(output/'fixture-inventory.json',inventory())
    if archive_path:
        archive=archive_path.read_bytes()
    else:
        async with httpx.AsyncClient(follow_redirects=True,timeout=90,trust_env=False) as client:
            response=await client.get(URL); response.raise_for_status(); archive=response.content
    atomic_replace(output/'flask-base.tar.gz',archive)
    base=extract(archive)
    if not any(n.startswith('docs/') for n in base) or not any(n.startswith('examples/') for n in base):
        raise ValueError('full upstream tree missing documentation/examples')
    for path in (FIXTURE/'src').rglob('*.py'):
        name=path.relative_to(FIXTURE).as_posix()
        if path.read_bytes()!=base.get(name): raise ValueError('local public source drift: '+name)
    overlay={}
    for path in (FIXTURE/'tests').rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            name=path.relative_to(FIXTURE).as_posix(); data=path.read_bytes()
            if data!=base.get(name): overlay[name]=data
    if set(overlay)!={'tests/test_config.py','tests/static/config.toml'}:
        raise ValueError('unexpected test patch changes: '+repr(sorted(overlay)))
    gold=dict(base)
    for path in (FIXTURE/'.oracle').rglob('*'):
        if path.is_file(): gold[path.relative_to(FIXTURE/'.oracle').as_posix()]=path.read_bytes()
    changed=[n for n in gold if base.get(n)!=gold[n]]
    if changed!=['src/flask/config.py']: raise ValueError('unexpected private calibration paths')
    save_json(output/'public/base.json',encode_snapshot(base))
    save_json(output/'private/known-good.json',encode_snapshot(gold))
    save_json(output/'private/overlay.json',encode_snapshot(overlay))
    source=dict(url=URL,revision=REV,archive_sha256=hashlib.sha256(archive).hexdigest(),base_hash=tree_hash(base),
        files=len(base),bytes=sum(map(len,base.values())),complete_upstream_tree=True,excluded_upstream_paths=[],
        original_file_hashes={n:hashlib.sha256(b).hexdigest() for n,b in sorted(base.items())},
        overlay_hash=tree_hash(overlay),known_good_hash=tree_hash(gold),model_calls=0)
    save_json(output/'source.json',source)
    task=next(t for t in json.loads((ROOT/'datasets/swebench_lite_tasks.json').read_text(encoding='utf-8'))['tasks'] if t['id']=='swebench_pallets__flask-4992')
    save_json(output/'public/task.json',dict(task_id='pallets__flask-4992',repo_id='pallets/flask',base_revision=REV,
        workspace_profile='docker_linux',description=task['description'].replace(' Do not use .oracle files and do not modify tests.',' Do not modify tests or project configuration.'),
        public_context=dict(scope='complete upstream repository',editable_paths=['src/flask/config.py']),budget={}))
    build=output/'build'
    for name,data in base.items(): atomic_replace(build/'base'/name,data)
    requirements='''pytest==7.2.1
attrs==22.2.0
iniconfig==2.0.0
packaging==23.0
pluggy==1.0.0
exceptiongroup==1.1.0
setuptools==70.0.0
wheel==0.38.4
click==8.1.3
itsdangerous==2.1.2
Jinja2==3.1.2
MarkupSafe==2.1.1
Werkzeug==2.3.7
asgiref==3.6.0
blinker==1.5
python-dotenv==0.21.1
tomli==2.0.1
'''
    if werkzeug_version not in ('2.3.7','2.2.2'): raise ValueError('unreviewed environment version')
    requirements=requirements.replace('Werkzeug==2.3.7',f'Werkzeug=={werkzeug_version}')
    atomic_replace(build/'requirements.lock',requirements.encode())
    dockerfile=f'''FROM {BASE_IMAGE}
COPY requirements.lock /opt/grader-requirements.lock
RUN python -m pip install --no-cache-dir -r /opt/grader-requirements.lock
COPY base /workspace
RUN python -m pip install --no-deps --no-build-isolation -e /workspace
RUN python -m pip freeze --all > /opt/grader-environment.txt
ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
WORKDIR /workspace
'''
    atomic_replace(build/'Dockerfile',dockerfile.encode())
    save_json(output/'preparation.json',dict(status='source_ready',model_calls=0,base_image=BASE_IMAGE,
        dockerfile_sha256=hashlib.sha256(dockerfile.encode()).hexdigest(),requirements_sha256=hashlib.sha256(requirements.encode()).hexdigest()))
    print(json.dumps(dict(status='source_ready',files=len(base),bytes=sum(map(len,base.values())),base_hash=tree_hash(base))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--archive',type=Path); parser.add_argument('--werkzeug-version',default='2.3.7')
    args=parser.parse_args()
    asyncio.run(prepare(args.output_dir.resolve(),args.archive,args.werkzeug_version))
