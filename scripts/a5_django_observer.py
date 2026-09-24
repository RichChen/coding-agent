"""Trusted no-network observer around each checkout's own Django test runner."""
import json
import os
import runpy
import sys
import traceback
import unittest
import hashlib
from pathlib import Path

sys.path[:0] = ['/workspace', '/workspace/tests']
os.chdir('/workspace')
payload = json.load(sys.stdin)
receipt = dict(schema='a5.repo.django.receipt.v2', collected=[], reports=[],
               collection_errors=[], complete=False, exit_code=3, python=sys.version)
receipt['observer_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


class Result(unittest.TextTestResult):
    def in_test_body(self, err):
        trace = err[2]
        while trace:
            if trace.tb_frame.f_code.co_name == '_callTestMethod':
                return True
            trace = trace.tb_next
        return False

    def record(self, test, outcome, err=None):
        receipt['reports'].append(dict(nodeid=test.id(), when='call', outcome=outcome,
            detail=''.join(traceback.format_exception(*err)) if err else None))

    def addSuccess(self, test):
        self.record(test, 'passed'); super().addSuccess(test)

    def addFailure(self, test, err):
        self.record(test, 'failed' if self.in_test_body(err) else 'error', err); super().addFailure(test, err)

    def addError(self, test, err):
        self.record(test, 'failed' if self.in_test_body(err) else 'error', err); super().addError(test, err)

    def addSkip(self, test, reason):
        self.record(test, 'skipped'); super().addSkip(test, reason)

    def addSubTest(self, test, subtest, err):
        if err:
            self.record(test, 'failed' if issubclass(err[0], test.failureException) else 'error', err)
        super().addSubTest(test, subtest, err)


class Runner(unittest.TextTestRunner):
    def __init__(self, *args, **kwargs):
        kwargs['resultclass'] = Result
        super().__init__(*args, **kwargs)


try:
    import django
    from django.test.runner import DiscoverRunner
    receipt.update(django_version=django.get_version(), django_import=django.__file__)
    original_build = DiscoverRunner.build_suite

    def build(self, *args, **kwargs):
        suite = original_build(self, *args, **kwargs)
        tests = list(flatten(suite))
        receipt['collected'] = [t.id() for t in tests]
        receipt['collection_errors'] = [dict(nodeid=t.id(), detail=str(t._exception))
            for t in tests if isinstance(t, unittest.loader._FailedTest)]
        return suite

    DiscoverRunner.build_suite = build
    DiscoverRunner.test_runner = Runner
    if payload.get('collect_only'):
        def collect(self, test_labels, **kwargs):
            self.setup_test_environment()
            try:
                self.build_suite(test_labels)
                return len(receipt['collection_errors'])
            finally:
                self.teardown_test_environment()
        DiscoverRunner.run_tests = collect
    sys.argv = ['tests/runtests.py', '--settings=test_sqlite', '--parallel=1', '--verbosity=1'] + payload['labels']
    receipt['argv'] = sys.argv
    try:
        runpy.run_path('tests/runtests.py', run_name='__main__')
        code = 0
    except SystemExit as exc:
        code = exc.code or 0
    receipt.update(complete=True, exit_code=code)
except BaseException:
    receipt['runner_error'] = traceback.format_exc()
finally:
    with open('/tmp/a5-pytest-receipt.json', 'w') as stream:
        json.dump(receipt, stream)
sys.exit(receipt['exit_code'])
