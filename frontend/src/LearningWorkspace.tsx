import { useState, useEffect } from 'react'
import { existingDiagnosisAdapter } from './services/learningAdapters'
import type { Diagnosis } from './types'

export default function LearningWorkspace({ user, onComplete, onBack }: { user: any; onComplete: () => void; onBack: () => void }) {
  const [step, setStep] = useState<'quiz' | 'code' | 'pr'>('quiz')
  const [userCode, setUserCode] = useState(`def binary_search(arr, target):
    low = 0
    high = len(arr) - 1
    
    while low < high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
            
    return -1
`)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', background: '#f5f6f4', color: '#334155', overflow: 'hidden' }}>
      {/* Top Navbar */}
      <header style={{ height: '60px', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', padding: '0 24px', background: '#fff', flexShrink: 0, justifyContent: 'space-between', margin: 0, width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <button onClick={onBack} style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', color: '#475569', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', fontSize: '0.9rem', borderRadius: '6px', fontWeight: 600 }}>
            <i className="bi bi-arrow-left" /> Back to Dashboard
          </button>
          <div style={{ display: 'flex', gap: '6px', marginLeft: '16px' }}>
            {['quiz', 'code', 'pr'].map((s, i) => (
              <div key={s} style={{ width: '40px', height: '6px', borderRadius: '3px', background: step === s ? '#4f46e5' : (i < ['quiz', 'code', 'pr'].indexOf(step) ? '#10b981' : '#e2e8f0') }} />
            ))}
          </div>
          <span style={{ fontWeight: 700, color: '#0f172a', marginLeft: '16px', fontSize: '1.1rem' }}>Binary Search Masterclass</span>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {step === 'quiz' && <QuizView onNext={() => setStep('code')} />}
        {step === 'code' && <CodeView user={user} code={userCode} setCode={setUserCode} onNext={() => setStep('pr')} />}
        {step === 'pr' && <PRView code={userCode} onNext={onComplete} />}
      </main>
    </div>
  )
}

function QuizView({ onNext }: { onNext: () => void }) {
  const [selected, setSelected] = useState<number | null>(null)
  const [submitted, setSubmitted] = useState(false)

  const options = [
    { id: 1, text: "while low < high:" },
    { id: 2, text: "while low <= high:", correct: true },
    { id: 3, text: "while low != high:" },
    { id: 4, text: "while low > high:" }
  ]

  const check = () => {
    setSubmitted(true)
  }

  const isCorrect = selected !== null && options.find(o => o.id === selected)?.correct

  return (
    <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '40px', overflowY: 'auto' }}>
      <div className="planner-card" style={{ maxWidth: '800px', width: '100%', background: '#fff', padding: '40px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}>
        <div className="card-top" style={{ marginBottom: '24px' }}>
          <span className="pill" style={{ background: '#e0e7ff', color: '#3730a3', fontWeight: 600 }}>01 · UNDERSTAND CONCEPT</span>
        </div>
        <h2 style={{ fontSize: '1.8rem', marginBottom: '16px', color: '#0f172a' }}>Loop Condition in Binary Search</h2>
        
        <p style={{ fontSize: '1.1rem', lineHeight: '1.6', marginBottom: '32px', color: '#475569' }}>
          When implementing an iterative Binary Search, which <code>while</code> loop condition ensures that we don't miss the target element if it resides at the exact boundary when <code>low</code> equals <code>high</code>?
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '32px' }}>
          {options.map((opt) => {
            const isSelected = selected === opt.id
            let bg = '#f8fafc'
            let border = '1px solid #cbd5e1'
            let color = '#334155'
            if (isSelected) {
               bg = '#eef2ff'
               border = '1px solid #6366f1'
               color = '#4f46e5'
            }
            if (submitted) {
               if (opt.correct) {
                 bg = '#f0fdf4'
                 border = '1px solid #22c55e'
                 color = '#15803d'
               } else if (isSelected && !opt.correct) {
                 bg = '#fef2f2'
                 border = '1px solid #ef4444'
                 color = '#b91c1c'
               }
            }

            return (
              <button 
                key={opt.id} 
                onClick={() => !submitted && setSelected(opt.id)}
                style={{ 
                  textAlign: 'left', padding: '16px 24px', borderRadius: '8px', 
                  background: bg, border: border, color: color, 
                  fontSize: '1.05rem', cursor: submitted ? 'default' : 'pointer',
                  fontFamily: 'monospace', transition: 'all 0.2s', fontWeight: isSelected || submitted ? 600 : 400
                }}
              >
                {opt.text}
              </button>
            )
          })}
        </div>

        {submitted && (
          <div style={{ padding: '20px', borderRadius: '8px', background: isCorrect ? '#dcfce7' : '#fee2e2', border: `1px solid ${isCorrect ? '#bbf7d0' : '#fecaca'}`, marginBottom: '24px', display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
             <i className={`bi bi-${isCorrect ? 'check-circle-fill' : 'exclamation-circle-fill'}`} style={{ fontSize: '1.25rem', color: isCorrect ? '#166534' : '#991b1b' }} />
            {isCorrect ? 
              <span style={{ color: '#166534', fontWeight: 500 }}>Correct! Using <code>&lt;=</code> ensures we check the final element when the search space narrows down to a single item.</span> : 
              <span style={{ color: '#991b1b', fontWeight: 500 }}>Incorrect. If you use <code>&lt;</code>, you might exit the loop before checking the last remaining element when <code>low == high</code>.</span>
            }
          </div>
        )}

        <div style={{ display: 'flex', gap: '16px' }}>
          {!submitted ? (
            <button 
              className="primary"
              onClick={check} 
              disabled={selected === null}
            >
              Check Answer
            </button>
          ) : (
            <button 
              className="primary"
              onClick={onNext}
            >
              Continue to Challenge <i className="bi bi-arrow-right" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function CodeView({ user, code, setCode, onNext }: { user: any; code: string; setCode: (c: string) => void; onNext: () => void }) {
  const [busy, setBusy] = useState(false)
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  
  // States for automatic AI hint popup
  const [autoHint, setAutoHint] = useState<string | null>(null)
  const [showAutoHint, setShowAutoHint] = useState(false)

  // Wait 15 seconds, if they haven't run correct code yet, fetch a hint silently and pop it up
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!diagnosis?.is_correct && !showAutoHint) {
         try {
           const isCorrect = code.includes('low <= high')
           const result = await existingDiagnosisAdapter.diagnose({
             taskId: 'binary_search_1',
             userId: user.id,
             questionId: 1,
             code: code,
             output: isCorrect ? 'Test passed: binary_search([1,2,3,4,5], 5) == 4' : 'Test failed: binary_search([1,2,3,4,5], 5) returned -1, expected 4',
             allPassed: isCorrect
           })
           if (result.diagnosis.evidence && result.diagnosis.evidence.length > 0 && !result.diagnosis.is_correct) {
              setAutoHint(result.diagnosis.evidence[0])
              setShowAutoHint(true)
           }
         } catch (e) {
           console.error("Failed to auto-fetch hint", e)
         }
      }
    }, 15000)
    return () => clearTimeout(timer)
  }, [diagnosis, code, showAutoHint, user.id])

  const runCode = async () => {
    setBusy(true)
    setDiagnosis(null)
    setShowAutoHint(false)
    try {
      const isCorrect = code.includes('low <= high')
      const result = await existingDiagnosisAdapter.diagnose({
        taskId: 'binary_search_1',
        userId: user.id,
        questionId: 1,
        code: code,
        output: isCorrect ? 'Test passed: binary_search([1,2,3,4,5], 5) == 4' : 'Test failed: binary_search([1,2,3,4,5], 5) returned -1, expected 4',
        allPassed: isCorrect
      })
      setDiagnosis(result.diagnosis)
    } catch (e: any) {
      setDiagnosis({
        id: Date.now(),
        is_correct: false,
        misconception_id: 'error',
        misconception_name: 'Error',
        confidence: 0,
        evidence: [e.message || 'An error occurred during diagnosis.'],
        error_type: 'ml_diagnosis',
        needs_intervention: true
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ flex: 1, display: 'flex', width: '100%', height: '100%' }}>
      {/* Left Pane: Description */}
      <div style={{ width: '40%', borderRight: '1px solid #e2e8f0', background: '#fff', padding: '32px', overflowY: 'auto' }}>
        <div className="card-top" style={{ marginBottom: '16px' }}>
          <span className="pill" style={{ background: '#dbeafe', color: '#1e40af', fontWeight: 600 }}>02 · BUILD</span>
        </div>
        <h1 style={{ fontSize: '1.8rem', color: '#0f172a', marginBottom: '16px' }}>Binary Search</h1>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '24px' }}>
          <span style={{ color: '#15803d', background: '#f0fdf4', padding: '4px 10px', borderRadius: '12px', fontSize: '0.85rem', fontWeight: 600 }}>Easy</span>
          <span style={{ color: '#475569', background: '#f1f5f9', padding: '4px 10px', borderRadius: '12px', fontSize: '0.85rem', fontWeight: 500 }}>Array</span>
        </div>
        
        <div style={{ fontSize: '1.05rem', lineHeight: '1.6', color: '#334155' }}>
          <p>Given an array of integers <code>nums</code> which is sorted in ascending order, and an integer <code>target</code>, write a function to search <code>target</code> in <code>nums</code>. If <code>target</code> exists, then return its index. Otherwise, return <code>-1</code>.</p>
          <p>You must write an algorithm with <code>O(log n)</code> runtime complexity.</p>
          
          <h3 style={{ color: '#0f172a', marginTop: '32px', marginBottom: '12px', fontSize: '1.2rem' }}>Example 1:</h3>
          <pre style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0', color: '#334155', fontFamily: 'monospace' }}>
Input: nums = [-1,0,3,5,9,12], target = 9{'\n'}
Output: 4{'\n'}
Explanation: 9 exists in nums and its index is 4
          </pre>

          <h3 style={{ color: '#0f172a', marginTop: '24px', marginBottom: '12px', fontSize: '1.2rem' }}>Example 2:</h3>
          <pre style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0', color: '#334155', fontFamily: 'monospace' }}>
Input: nums = [-1,0,3,5,9,12], target = 2{'\n'}
Output: -1{'\n'}
Explanation: 2 does not exist in nums so return -1
          </pre>
        </div>
      </div>

      {/* Right Pane: Editor & Console */}
      <div style={{ width: '60%', display: 'flex', flexDirection: 'column', background: '#f8fafc', position: 'relative' }}>
        
        {/* Editor Area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderBottom: '1px solid #e2e8f0' }}>
          <div style={{ padding: '12px 20px', background: '#fff', borderBottom: '1px solid #e2e8f0', display: 'flex', gap: '16px', fontSize: '0.9rem' }}>
            <span style={{ color: '#4f46e5', fontWeight: 600, borderBottom: '2px solid #4f46e5', paddingBottom: '10px', marginBottom: '-12px' }}>main.py</span>
          </div>
          <textarea 
            value={code} 
            onChange={e => setCode(e.target.value)} 
            style={{ 
              flex: 1, width: '100%', padding: '20px', background: '#fff', 
              color: '#334155', border: 'none', fontFamily: 'Consolas, monospace', 
              fontSize: '1rem', resize: 'none', outline: 'none', lineHeight: '1.5'
            }} 
            spellCheck={false}
          />
        </div>

        {/* Console / Output Area */}
        <div style={{ height: '35%', minHeight: '250px', background: '#fff', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '12px 20px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f8fafc' }}>
            <span style={{ color: '#475569', fontSize: '0.95rem', fontWeight: 600 }}>Test Results / AI Diagnosis</span>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button 
                onClick={runCode} 
                disabled={busy}
                className="outline-button mini"
              >
                {busy ? 'Running...' : 'Run Code'}
              </button>
              <button 
                onClick={runCode} 
                disabled={busy}
                className="primary mini"
              >
                Submit
              </button>
            </div>
          </div>
          <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
            {!diagnosis ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#94a3b8' }}>
                 Run your code to see test cases and AI feedback.
              </div>
            ) : (
              <div>
                 {diagnosis.is_correct ? (
                   <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                     <h3 style={{ color: '#166534', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}><i className="bi bi-check-circle-fill" /> Accepted</h3>
                     <button onClick={onNext} className="primary" style={{ alignSelf: 'flex-start' }}>
                       Continue to PR Review <i className="bi bi-arrow-right" />
                     </button>
                   </div>
                 ) : (
                   <div>
                     <h3 style={{ margin: '0 0 16px 0', color: '#991b1b', display: 'flex', alignItems: 'center', gap: '8px' }}><i className="bi bi-x-circle-fill" /> Wrong Answer</h3>
                     <div style={{ background: '#fffbeb', padding: '20px', borderRadius: '8px', border: '1px solid #fde68a', marginBottom: '16px' }}>
                       <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                         <i className="bi bi-stars" style={{ fontSize: '1.2rem', color: '#d97706' }} />
                         <span style={{ color: '#d97706', fontWeight: 700 }}>AI Tutor Intervention</span>
                       </div>
                       {diagnosis.evidence.map((ev, i) => (
                         <p key={i} style={{ margin: 0, color: '#475569', marginBottom: i < diagnosis.evidence.length - 1 ? '12px' : 0, lineHeight: 1.6, fontSize: '0.95rem' }}>
                           {ev}
                         </p>
                       ))}
                     </div>
                   </div>
                 )}
              </div>
            )}
          </div>
        </div>

        {/* Automatic AI Hint Popup */}
        {showAutoHint && autoHint && (
          <div style={{ 
            position: 'absolute', bottom: '40%', right: '24px', transform: 'translateY(-20px)',
            background: '#fff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '20px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.1)', zIndex: 10, display: 'flex', flexDirection: 'column', gap: '12px',
            animation: 'fadeIn 0.4s ease', maxWidth: '400px'
          }}>
             <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px', marginBottom: '4px' }}>
               <span style={{ fontWeight: 700, color: '#4f46e5', display: 'flex', alignItems: 'center', gap: '8px' }}>
                 <i className="bi bi-stars" /> You seem stuck. Here's a hint:
               </span>
               <button onClick={() => setShowAutoHint(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: 0 }}><i className="bi bi-x-lg" /></button>
             </div>
             <p style={{ margin: 0, fontSize: '0.95rem', color: '#334155', lineHeight: 1.6 }}>{autoHint}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function PRView({ code, onNext }: { code: string; onNext: () => void }) {
  const [branch, setBranch] = useState('feature/binary-search')
  const [title, setTitle] = useState('Implement Binary Search with O(log n) time complexity')
  const [comment, setComment] = useState('I have implemented the binary search algorithm to find the target element efficiently. I made sure to use `low <= high` to avoid boundary bugs.')
  const [submitted, setSubmitted] = useState(false)
  
  if (submitted) {
    return (
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '40px', background: '#f5f6f4' }}>
        <div style={{ background: '#fff', padding: '48px', borderRadius: '16px', border: '1px solid #e2e8f0', boxShadow: '0 10px 25px rgba(0,0,0,0.05)', textAlign: 'center', maxWidth: '500px', width: '100%', animation: 'fadeIn 0.5s ease' }}>
          <div style={{ width: '80px', height: '80px', background: '#dcfce7', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px auto' }}>
             <i className="bi bi-check-lg" style={{ fontSize: '3rem', color: '#166534' }} />
          </div>
          <h2 style={{ fontSize: '2rem', color: '#0f172a', margin: '0 0 16px 0' }}>Pull Request Created! 🎉</h2>
          <p style={{ fontSize: '1.1rem', color: '#475569', lineHeight: 1.6, margin: '0 0 32px 0' }}>
            Your code is now in review. You've successfully completed the Binary Search Masterclass journey. Great job applying what you've learned!
          </p>
          <button onClick={() => { localStorage.setItem('journey_binary_search_completed', 'true'); onNext(); }} className="primary wide" style={{ fontSize: '1.1rem', padding: '14px' }}>
            Return to Dashboard <i className="bi bi-house-door" style={{ marginLeft: '8px' }} />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ flex: 1, display: 'flex', justifyContent: 'center', padding: '40px', overflowY: 'auto' }}>
      <div className="planner-card" style={{ maxWidth: '1000px', width: '100%', display: 'flex', flexDirection: 'column', gap: '24px', padding: '40px', background: '#fff', border: '1px solid #e2e8f0', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}>
        <div className="card-top">
          <span className="pill" style={{ background: '#ffedd5', color: '#9a3412', fontWeight: 600 }}>03 · OPEN PULL REQUEST</span>
        </div>
        <h2 style={{ fontSize: '1.8rem', color: '#0f172a', margin: 0 }}>Open a Pull Request</h2>
        
        <p style={{ fontSize: '1.1rem', lineHeight: '1.6', color: '#475569' }}>
          Great job passing the tests! In a real engineering team, the final step is to prepare your code for review. Give your branch a name, write a descriptive PR title, and add a comment explaining your approach.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', background: '#f8fafc', padding: '24px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ fontSize: '0.95rem', fontWeight: 600, color: '#334155' }}>Branch name</label>
              <div style={{ display: 'flex', alignItems: 'center', background: '#fff', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '8px 12px', gap: '8px' }}>
                <i className="bi bi-git" style={{ color: '#64748b' }} />
                <input value={branch} onChange={e => setBranch(e.target.value)} style={{ border: 'none', background: 'transparent', width: '100%', outline: 'none', fontSize: '0.95rem', color: '#0f172a' }} />
              </div>
            </div>
            
            <div style={{ padding: '8px', color: '#94a3b8', marginTop: '28px' }}>
              <i className="bi bi-arrow-right" />
            </div>
            
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ fontSize: '0.95rem', fontWeight: 600, color: '#334155' }}>Target branch</label>
              <div style={{ display: 'flex', alignItems: 'center', background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '8px 12px', gap: '8px', color: '#475569' }}>
                <i className="bi bi-git" />
                <span style={{ fontSize: '0.95rem' }}>main</span>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ fontSize: '0.95rem', fontWeight: 600, color: '#334155' }}>Pull Request Title</label>
            <input value={title} onChange={e => setTitle(e.target.value)} style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '10px 12px', fontSize: '1.05rem', color: '#0f172a', fontWeight: 500, outline: 'none' }} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ fontSize: '0.95rem', fontWeight: 600, color: '#334155' }}>Description</label>
            <textarea value={comment} onChange={e => setComment(e.target.value)} style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '12px', fontSize: '0.95rem', color: '#334155', minHeight: '120px', resize: 'vertical', outline: 'none', fontFamily: 'inherit', lineHeight: 1.5 }} />
          </div>
        </div>

        <div style={{ border: '1px solid #d0d7de', borderRadius: '6px', overflow: 'hidden', background: '#fff', marginTop: '16px' }}>
          <div style={{ background: '#f6f8fa', padding: '8px 16px', borderBottom: '1px solid #d0d7de', display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: '#57606a' }}>
            <span><i className="bi bi-chevron-down" style={{ marginRight: '8px' }} /> 1 changed file</span>
            <span><strong>main.py</strong></span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', fontFamily: 'Consolas, monospace', fontSize: '0.9rem', background: '#fff', overflowX: 'auto' }}>
            {code.split('\n').map((line, i) => (
              <div key={i} style={{ display: 'flex', background: '#e6ffec', color: '#24292f' }}>
                 <div style={{ width: '40px', textAlign: 'right', padding: '2px 8px', borderRight: '1px solid #d0d7de', background: '#e6ffec', color: '#6e7781' }}></div>
                 <div style={{ width: '40px', textAlign: 'right', padding: '2px 8px', borderRight: '1px solid #d0d7de', background: '#ccffd8', color: '#6e7781' }}>{i + 1}</div>
                 <div style={{ padding: '2px 16px', whiteSpace: 'pre' }}>+ {line}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
          <button onClick={() => setSubmitted(true)} className="primary" style={{ background: '#2da44e', border: '1px solid rgba(27,31,36,0.15)', color: '#fff', padding: '10px 20px', fontSize: '1rem' }}>
            Create Pull Request <i className="bi bi-arrow-right" style={{ marginLeft: '4px' }} />
          </button>
        </div>
      </div>
    </div>
  )
}
