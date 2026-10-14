"""Finalize the 20-source memory gate after image calibration and failures."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs/a5/pilot20-harness-manifest.json"

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(p, v):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--pool',type=Path,required=True); ap.add_argument('--calibration',type=Path,required=True); ap.add_argument('--calibration-retry',type=Path,required=True); ap.add_argument('--history',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    pool=load(a.pool/'receipts.json')['rows']; cal=load(a.calibration/'receipts.json')['rows']; retry=load(a.calibration_retry/'receipts.json')['rows']; hist=load(a.history/'receipts.json')['rows']
    cal_by={r['task_id']:r for r in cal}; cal_by.update({r['task_id']:r for r in retry})
    history_by={r['task_id']:r for r in hist}
    rows=[]
    for r in pool:
        tid=r['task_id']; c=cal_by.get(tid)
        if tid in history_by:
            h=history_by[tid]
            rows.append({'task_id':tid,'role':'historical_pool','source_preflight':{'status':'complete','receipt_ref':h.get('source_attempt_ref')},'transport':{'status':'transport_ready'},'environment_baseline':{'status':'invalid_env','attempt_receipt_ref':str(a.history/'tasks'/tid/'receipt.json'),'disposition':'retry_blocked_by_host_acl_or_docker_buildx_lock'},'grader':{'status':'blocked','calibration':'not_run_due_to_missing_image'},'eligible':False,'blockers':['historical_own_environment_baseline_not_verified','image_build_or_windows_symlink_acl_blocked','independent_full_repo_grader_not_run'],'model_calls':0,'paid':False})
            continue
        if c:
            row={**r, 'grader': {**r.get('grader',{}), 'status': 'ready' if c['status']=='ready' else 'blocked', 'calibration': c}, 'eligible': c['status']=='ready' and r['environment_baseline']['status']=='baseline_ready', 'blockers': list(r.get('blockers',[]))}
            if c['status']!='ready' and 'image_backed_full_repo_grader_calibration_failed' not in row['blockers']: row['blockers'].append('image_backed_full_repo_grader_calibration_failed')
            rows.append(row)
        else: rows.append(r)
    out=a.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    save(out/'manifest.json',{'schema':'a5.memory-gates-finalization.v1','assigned':20,'pool_audit':str(a.pool.resolve()),'calibration':str(a.calibration.resolve()),'history_retry':str(a.history.resolve()),'model_calls':0,'paid':False})
    save(out/'receipts.json',{'schema':'a5.memory-gates-final-receipts.v1','rows':rows,'full_denominator':20,'model_calls':0,'paid':False})
    ready=sum(bool(r.get('eligible')) for r in rows)
    readiness={'schema':'a5.memory-gates-final-readiness.v1','status':'blocked','assigned':20,'full_denominator':20,'source_complete':20,'environment_baseline_ready':sum(r.get('environment_baseline',{}).get('status')=='baseline_ready' for r in rows),'grader_ready':sum(r.get('grader',{}).get('status')=='ready' for r in rows),'eligible':ready,'blocking_tasks':[r['task_id'] for r in rows if not r.get('eligible')],'model_calls':0,'paid':False,'paid_build_started':False,'paid_pilot_started':False,'memory_build_eligible':False,'next_gate':'resolve historical host ACL/buildx failures and five remaining16 invalid_env rows; rerun full grader calibration','created_at':datetime.now(timezone.utc).isoformat()}
    save(out/'readiness.json',readiness)
    save(out/'anomaly-dispositions.json',{'schema':'a5.memory-source-anomaly-dispositions.v1','model_calls':0,'paid':False,'rows':[
        {'task_id':'django__django-11001','disposition':'blocked_baseline_contract_mismatch','evidence':'A5-harness-preflight-57-remaining16-baseline/tasks/django__django-11001/receipt.json'},
        {'task_id':'django__django-11019','disposition':'blocked_baseline_contract_mismatch','evidence':'A5-harness-preflight-57-remaining16-baseline/tasks/django__django-11019/receipt.json'},
        {'task_id':'sympy__sympy-12236','disposition':'blocked_known_good_failure','evidence':'A5-harness-preflight-57-remaining16-baseline/tasks/sympy__sympy-12236/receipt.json'},
        {'task_id':'pytest-dev__pytest-5413','disposition':'blocked_collection_invalid_and_known_good_failure','evidence':'A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5413/receipt.json'},
        {'task_id':'pytest-dev__pytest-5495','disposition':'blocked_collection_invalid_and_known_good_failure','evidence':'A5-harness-preflight-57-remaining16-baseline/tasks/pytest-dev__pytest-5495/receipt.json'}]})
    save(out/'failure-retry-ledger.json',{'schema':'a5.failure-retry-ledger.v1','entries':[{'task_id':r['task_id'],'status':r.get('environment_baseline',{}).get('status'),'blockers':r.get('blockers',[])} for r in rows],'model_calls':0,'paid':False})
    save(out/'artifact-manifest.json',{p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps(readiness,ensure_ascii=False,indent=2)); raise SystemExit(2)
if __name__=='__main__': main()
