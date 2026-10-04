import contextlib
import io
import traceback
from typing import Any


def _safe_exec_namespace(code: str, function_name: str) -> dict[str, Any]:
    namespace: dict[str, Any] = {}
    exec(code, namespace, namespace)
    if function_name not in namespace:
        raise NameError(f"Function '{function_name}' is not defined.")
    return namespace


def judge_python_submission(code: str, problem_id: str, function_name: str, tests: list[dict[str, Any]]) -> dict[str, Any]:
    """Run a Python solution against a list of test cases and report pass/fail."""
    try:
        namespace = _safe_exec_namespace(code, function_name)
    except Exception as exc:
        return {
            'passed': False,
            'problem_id': problem_id,
            'function_name': function_name,
            'failed_tests': [{
                'index': 0,
                'input': None,
                'expected': None,
                'actual': None,
                'error': f'{type(exc).__name__}: {exc}',
            }],
            'compiler_error': True,
            'runtime_error': False,
        }

    failed_tests: list[dict[str, Any]] = []
    for index, test in enumerate(tests):
        try:
            output = namespace[function_name](*test['input'])
            if output != test['expected']:
                failed_tests.append({
                    'index': index,
                    'input': test['input'],
                    'expected': test['expected'],
                    'actual': output,
                    'error': 'Output mismatch',
                })
        except Exception as exc:
            failed_tests.append({
                'index': index,
                'input': test['input'],
                'expected': test['expected'],
                'actual': None,
                'error': f'{type(exc).__name__}: {exc}',
            })

    return {
        'passed': len(failed_tests) == 0,
        'problem_id': problem_id,
        'function_name': function_name,
        'failed_tests': failed_tests,
        'compiler_error': False,
        'runtime_error': any(item['error'] for item in failed_tests if 'Error' in item['error'] or 'Exception' in item['error']),
    }
