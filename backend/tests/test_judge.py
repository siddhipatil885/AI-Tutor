from app.services.judge import judge_python_submission


def test_judge_accepts_working_python_solution():
    code = '''
def two_sum(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        need = target - value
        if need in seen:
            return [seen[need], index]
        seen[value] = index
    return []
'''

    result = judge_python_submission(
        code=code,
        problem_id='P001',
        function_name='two_sum',
        tests=[
            {"input": [[2, 7, 11, 15], 9], "expected": [0, 1]},
            {"input": [[3, 2, 4], 6], "expected": [1, 2]},
        ],
    )

    assert result['passed'] is True
    assert result['failed_tests'] == []


def test_judge_rejects_wrong_python_solution():
    code = '''
def two_sum(nums, target):
    return [0, 0]
'''

    result = judge_python_submission(
        code=code,
        problem_id='P001',
        function_name='two_sum',
        tests=[
            {"input": [[2, 7, 11, 15], 9], "expected": [0, 1]},
        ],
    )

    assert result['passed'] is False
    assert result['failed_tests'][0]['index'] == 0
