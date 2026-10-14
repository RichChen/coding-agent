"""Trusted image pytest entrypoint, sent by the host via python -I -B -c.

No host imports of candidate code. This is not a security boundary against a
candidate deliberately modifying the Python interpreter executing its tests.
"""
import json
import os
from pathlib import Path
import sys


def main():
    payload = json.load(sys.stdin)
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    os.environ.pop('PYTEST_ADDOPTS', None)
    import pytest  # Import image pytest before putting candidate on sys.path.
    for relative in reversed(payload['python_paths']):
        sys.path.insert(0, str(Path('/workspace') / relative))
    receipt = dict(schema='repo.pytest.receipt.v1', collected=[], reports=[], collection_errors=[],
                   pytest_version=pytest.__version__, python=sys.version, complete=False)

    class Observer:
        def pytest_collection_finish(self, session):
            receipt['collected'] = [item.nodeid for item in session.items]

        def pytest_collectreport(self, report):
            if report.failed:
                receipt['collection_errors'].append(dict(nodeid=report.nodeid, detail=str(report.longrepr)[:4000]))

        def pytest_runtest_logreport(self, report):
            receipt['reports'].append(dict(nodeid=report.nodeid, when=report.when, outcome=report.outcome,
                wasxfail=str(report.wasxfail) if hasattr(report, 'wasxfail') else None,
                detail=str(report.longrepr)[:1000] if report.failed or report.skipped else None))

    Path('/tmp/grader-empty.ini').write_text('[pytest]\n')
    args = ['-c', '/tmp/grader-empty.ini', '--rootdir=/workspace', '-p', 'no:cacheprovider',
            '--basetemp=/tmp/grader-pytest', '-q', '--tb=short']
    if payload['collect_only']:
        args.append('--collect-only')
    args.extend(['--', *payload['test_paths']])
    try:
        code = int(pytest.main(args, plugins=[Observer()]))
        receipt.update(exit_code=code, complete=True)
        receipt['workspace_imports'] = {name: str(module.__file__) for name,module in list(sys.modules.items())
            if getattr(module,'__file__',None) and str(module.__file__).startswith('/workspace/') and '.' not in name}
    except BaseException as exc:
        receipt.update(exit_code=3, runner_error=type(exc).__name__)
        code = 3
    Path('/tmp/grader-receipt.json').write_text(json.dumps(receipt, ensure_ascii=True), encoding='utf-8')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
