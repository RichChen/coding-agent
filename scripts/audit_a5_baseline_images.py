"""Verify complete patched trees and installed environments inside pinned images."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preflight_a5_repo_baseline import load, save, sha, prepare_repo_runtime
from src.execution.docker import DockerExecutionBackend

CHECK = r'''
import hashlib,json,os,pathlib,stat,sys,tarfile,platform
root=pathlib.Path('/workspace'); expected={}; mismatches=[]
with tarfile.open('/opt/'+sys.argv[1]+'.tar.gz') as archive:
    for member in archive:
        name=member.name; p=root/name; expected[name]=None
        if not p.exists() and not p.is_symlink():
            mismatches.append([name,'missing']); continue
        actual=p.lstat()
        if stat.S_IMODE(actual.st_mode) != member.mode:
            mismatches.append([name,'mode',member.mode,stat.S_IMODE(actual.st_mode)])
        if member.isdir():
            if not p.is_dir() or p.is_symlink(): mismatches.append([name,'directory_type'])
        elif member.issym():
            if not p.is_symlink() or os.readlink(p)!=member.linkname: mismatches.append([name,'symlink'])
        elif member.isfile():
            wanted=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
            actual_hash=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() and not p.is_symlink() else None
            if actual_hash!=wanted: mismatches.append([name,'file_content',wanted,actual_hash])
        else: mismatches.append([name,'unsupported_member'])
generated={}
for parent,dirs,files in os.walk(root,followlinks=False):
    for name in dirs+files:
        p=pathlib.Path(parent)/name; rel=p.relative_to(root).as_posix()
        if rel not in expected:
            generated[rel]=dict(kind='symlink' if p.is_symlink() else 'dir' if p.is_dir() else 'file',size=p.lstat().st_size)
print(json.dumps(dict(expected_members=len(expected),mismatches=mismatches,generated=generated,
    environment=pathlib.Path('/opt/grader-environment.txt').read_text(),python=platform.python_version(),
    generated_native_links=json.loads(pathlib.Path('/tmp/a5-native-links.json').read_text()),
    mountinfo=pathlib.Path('/proc/self/mountinfo').read_text())))
'''


async def audit(row, kind, output):
    image = row['baseline_image_digest' if kind == 'baseline' else 'known_good_image_digest']
    backend = DockerExecutionBackend(image=image, context='desktop-linux', memory_bytes=2*1024**3,
        workspace_bytes=512*1024**2, tmpfs_bytes=512*1024**2, network='none')
    result = dict(task_id=row['task_id'], kind=kind, image=image, status='invalid', model_calls=0, paid=False)
    try:
        await backend.start({})
        await prepare_repo_runtime(backend)
        raw = await backend._ok('exec', backend.name, '/usr/local/bin/python', '-I', '-S', '-c', CHECK, kind,
                                limit=8*1024**2, timeout=120)
        result.update(json.loads(raw))
        result['status'] = 'verified' if not result['mismatches'] else 'invalid'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        await backend.close()
        result['cleanup_verified'] = backend.cleanup_ok
        if not backend.cleanup_ok: result['status']='invalid'
    save(output / row['task_id'] / (kind+'.json'), result)
    print(json.dumps({k:result.get(k) for k in ('task_id','kind','status','error')}), flush=True)
    return result


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--only-task',action='append',default=[])
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=False)
    rows={}
    for root in args.input:
        for path in sorted((root/'tasks').glob('*/receipt.json')):
            row=load(path)
            if args.only_task and row['task_id'] not in args.only_task: continue
            if row.get('baseline_image_digest') and row.get('known_good_image_digest'):
                rows[row['task_id']]=row
    results=[]
    for row in rows.values():
        for kind in ('baseline','known-good'):
            results.append(await audit(row,kind,args.output))
    save(args.output/'audit.json',dict(rows=results,verified=sum(r['status']=='verified' for r in results),
                                     assigned=len(results),model_calls=0,paid=False))


if __name__=='__main__': asyncio.run(main())
