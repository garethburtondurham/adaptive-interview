import { useState, useEffect } from 'react'

function CaseSelection({ onStart }) {
  const [cases, setCases] = useState([])
  const [selectedCase, setSelectedCase] = useState('')
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchCases()
  }, [])

  const fetchCases = async () => {
    try {
      const response = await fetch('/api/cases')
      if (!response.ok) throw new Error('Failed to fetch cases')
      const data = await response.json()
      setCases(data)
      if (data.length > 0) {
        setSelectedCase(data[0].id)
      }
    } catch (err) {
      setError('Unable to load cases. Please ensure the API server is running.')
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async () => {
    if (!selectedCase) return

    setStarting(true)
    setError(null)

    try {
      const response = await fetch('/api/interviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: selectedCase }),
      })

      if (!response.ok) throw new Error('Failed to start interview')

      const data = await response.json()
      onStart({
        sessionId: data.session_id,
        caseTitle: data.case_title,
        openingMessage: data.opening_message,
      })
    } catch (err) {
      setError('Unable to start interview. Please try again.')
      setStarting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-semibold text-gray-900 mb-3">
            Case Interview
          </h1>
          <p className="text-gray-500">
            Select a case to begin your interview session
          </p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="w-8 h-8 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
            </div>
          ) : error ? (
            <div className="text-center py-6">
              <p className="text-red-500 mb-4">{error}</p>
              <button
                onClick={fetchCases}
                className="text-gray-600 hover:text-gray-900 underline"
              >
                Try again
              </button>
            </div>
          ) : (
            <>
              {/* Case Selection */}
              <div className="mb-6">
                <label
                  htmlFor="case-select"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Select Case
                </label>
                <select
                  id="case-select"
                  value={selectedCase}
                  onChange={(e) => setSelectedCase(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50
                           text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900
                           focus:border-transparent transition-all"
                >
                  {cases.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Instructions */}
              <div className="mb-8 p-4 bg-gray-50 rounded-xl">
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  Before you begin
                </h3>
                <ul className="text-sm text-gray-500 space-y-1">
                  <li>Take your time to structure your thoughts</li>
                  <li>Feel free to ask clarifying questions</li>
                  <li>Think out loud as you work through the problem</li>
                </ul>
              </div>

              {/* Start Button */}
              <button
                onClick={handleStart}
                disabled={starting || !selectedCase}
                className="w-full py-3 px-6 rounded-xl bg-gray-900 text-white font-medium
                         hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-900
                         focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all"
              >
                {starting ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Starting...
                  </span>
                ) : (
                  'Begin Interview'
                )}
              </button>
            </>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-gray-400 mt-6">
          Powered by AI
        </p>
      </div>
    </div>
  )
}

export default CaseSelection
