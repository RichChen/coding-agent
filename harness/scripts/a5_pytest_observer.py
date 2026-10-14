"""Container-only observer for pytest's own full suite; candidate imported first."""
import json
import os
from pathlib import Path
import sys


def main():
    payload = json.load(sys.stdin)
    path = Path('/tmp/a5-receipt.json')
    receipt = dict(schema='repo.pytest.receipt.v1', collected=[], reports=[], collection_errors=[],
                   complete=False, python=sys.version, exit_code=3)
    path.write_text(json.dumps(receipt))
    # The fresh container contains only this task's public base/private grader
    # overlay; neither the agent repository nor host data is mounted.
    sys.path.insert(0, '/workspace/src')
    plugin_autoload = payload.get('pinned_plugin_autoload', False)
    if plugin_autoload:
        os.environ.pop('PYTEST_DISABLE_PLUGIN_AUTOLOAD', None)
    else:
        os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    receipt['pinned_plugin_autoload'] = plugin_autoload
    os.environ['PYTHONPATH'] = '/workspace/src'
    os.environ.pop('PYTEST_ADDOPTS', None)
    try:
        import pytest
        import _pytest
        receipt['pytest_version'] = pytest.__version__
        receipt['pytest_import'] = pytest.__file__
        receipt['_pytest_import'] = _pytest.__file__
        if not all(str(p).startswith('/workspace/src/') for p in (pytest.__file__, _pytest.__file__)):
            raise RuntimeError('pytest must be imported from this candidate workspace')

        class Observer:
            def pytest_sessionstart(self, session):
                distributions = [(dist.project_name, dist.version) for _, dist in session.config.pluginmanager.list_plugin_distinfo()]
                receipt['plugin_distributions'] = distributions
                if plugin_autoload and any(name.lower() != 'hypothesis' for name, _ in distributions):
                    raise RuntimeError('unexpected plugin distribution in fixed image')

            def pytest_collection_finish(self, session):
                receipt['collected'] = [item.nodeid for item in session.items]

            def pytest_collectreport(self, report):
                if report.failed:
                    receipt['collection_errors'].append(dict(nodeid=report.nodeid, detail=str(report.longrepr)))

            def pytest_runtest_logreport(self, report):
                receipt['reports'].append(dict(nodeid=report.nodeid, when=report.when, outcome=report.outcome,
                    wasxfail=str(report.wasxfail) if hasattr(report, 'wasxfail') else None,
                    detail=str(report.longrepr) if report.failed or report.skipped else None))

        # Preserve the repository's test-discovery configuration and full testing
        # tree. Explicit plugin loading is fixed; third-party autoload is disabled.
        args = ['-q', '--tb=short', '-o', 'cache_dir=/tmp/a5-cache', '--basetemp=/tmp/a5-pytest']
        if not plugin_autoload:
            args.extend(['-p', 'hypothesis.extra.pytestplugin'])
        if payload['collect_only']:
            args.append('--collect-only')
        args.extend(['--', 'testing'])
        code = int(pytest.main(args, plugins=[Observer()]))
        receipt.update(complete=True, exit_code=code, argv=args)
    except BaseException as exc:
        receipt.update(runner_error=type(exc).__name__ + ': ' + str(exc), exit_code=3)
        code = 3
    path.write_text(json.dumps(receipt, ensure_ascii=True), encoding='utf-8')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
