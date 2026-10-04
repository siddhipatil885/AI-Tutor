import test from 'node:test'
import assert from 'node:assert/strict'
import { evaluateReview, evaluateTask, initialWorkspaceState, isTaskUnlocked, languageForPath, listModifiedFiles, project, reviewPullRequest, starterForPath, supportedEditorLanguages } from '../src/domain/workspace.ts'
import { maybeUnlockAchievements, reward, rewardForTask, totalXp } from '../src/services/progression.ts'
import { journeyTourSteps, studentFlowModes } from '../src/flow.ts'
import { journeyTourStorageKey } from '../src/services/auth.ts'
const stored = new Map()
globalThis.localStorage = { getItem:key=>stored.get(key)??null, setItem:(key,value)=>stored.set(key,value) }
const { loadWorkspace, saveWorkspace, limitedTerminal } = await import('../src/services/workspace.ts')

test('project starts with a reproducible bug and gates follow-up work', () => {
  const state = initialWorkspaceState()
  assert.equal(project.tasks.length, 3)
  assert.equal(isTaskUnlocked(project.tasks[1], state), false)
  assert.equal(evaluateTask(project.tasks[0], state.files).every(check => check.passed), false)
})

test('bug fix acceptance checks require inclusive output and an empty-range guard', () => {
  const state = initialWorkspaceState()
  state.files['src/sequence.py'] = 'def values_between(start, stop):\n    if start >= stop:\n        return []\n    return list(range(start, stop + 1))\n'
  assert.deepEqual(evaluateTask(project.tasks[0], state.files).map(check => check.passed), [true, true])
})

test('regression-test ticket recognizes the expected focused assertion', () => {
  const state = initialWorkspaceState()
  state.files['tests/test_sequence.py'] += '\n    def test_includes_final_value(self):\n        self.assertEqual(values_between(1, 3), [1, 2, 3])\n'
  assert.equal(evaluateTask(project.tasks[1], state.files)[0].passed, true)
})

test('feature acceptance checks recognize a reusable formatting helper', () => {
  const state = initialWorkspaceState()
  state.files['src/sequence.py'] += '\ndef format_sequence(start, stop):\n    return " ".join(str(value) for value in values_between(start, stop))\n'
  assert.deepEqual(evaluateTask(project.tasks[2], state.files).map(check => check.passed), [true, true])
})

test('review completion requires comments on both known issues', () => {
  assert.equal(evaluateReview([{ issueId:'exclusive-stop', line:27, text:'range excludes the stop value; include the final requested value.' }]), false)
  assert.equal(evaluateReview([
    { issueId:'empty-interval', line:25, text:'Handle equal start and stop values as an empty interval.' },
    { issueId:'exclusive-stop', line:27, text:'range excludes the stop value; include the final requested value.' },
  ]), true)
})

test('rewards deduplicate and achievements follow engineering milestones', () => {
  let state = initialWorkspaceState()
  state = reward(state, 'test-once', 10, 'Example')
  state = reward(state, 'test-once', 10, 'Example')
  assert.equal(totalXp(state), 10)
  state = { ...state, completedTaskIds:['RL-1042'], signals:[{ taskId:'RL-1042', kind:'run', passed:false, at:'2026-01-01T00:00:00Z' }] }
  state = rewardForTask(state, project.tasks[0])
  state = maybeUnlockAchievements(state)
  assert.equal(state.achievements.includes('first-bug-fix'), true)
})

test('repository changes are listed against the saved commit snapshot', () => {
  const state = initialWorkspaceState()
  state.files['README.md'] += '\nA new note.\n'
  assert.deepEqual(listModifiedFiles(state), ['README.md'])
})

test('file drafts survive save and reload', () => {
  const state = initialWorkspaceState()
  state.files['src/sequence.py'] = 'learner draft'
  saveWorkspace(state)
  assert.equal(loadWorkspace().files['src/sequence.py'], 'learner draft')
})

test('terminal stays allowlisted and does not execute arbitrary Python', () => {
  const state = initialWorkspaceState()
  assert.match(limitedTerminal('python main.py', state, project.tasks[0]), /Arbitrary Python execution is disabled/)
  assert.match(limitedTerminal('ls && cat README.md', state, project.tasks[0]), /Command not available/)
  assert.match(limitedTerminal('cat README.md', state, project.tasks[0]), /Loopback Tasks API/)
})

test('new file templates and Monaco modes cover the four target languages', () => {
  assert.deepEqual(supportedEditorLanguages, ['python','c','cpp','html'])
  for (const [path,language] of [['examples/demo.py','python'],['examples/demo.c','c'],['examples/demo.cpp','cpp'],['public/demo.html','html']]) {
    assert.equal(languageForPath(path), language)
    assert.ok(starterForPath(path).length > 0)
  }
})

test('student flow exposes a clear landing-page mode chooser', () => {
  assert.deepEqual(studentFlowModes.map(mode => mode.id), ['learning','project','review','progress'])
  assert.ok(studentFlowModes.every(mode => mode.label && mode.description && mode.stage && mode.bridge))
  assert.equal(journeyTourSteps.length, 4)
  assert.ok(journeyTourSteps.every(step => step.title && step.description && step.details.length >= 2))
  assert.notEqual(journeyTourStorageKey('student/one'), journeyTourStorageKey('student/two'))
  assert.match(journeyTourStorageKey('student/one'), /student%2Fone$/)
  assert.match(reviewPullRequest.description, /loop-boundary/)
})
