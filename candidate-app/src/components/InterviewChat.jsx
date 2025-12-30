import { useState, useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import TypingIndicator from './TypingIndicator'

function InterviewChat({ sessionId, caseTitle, openingMessage, onComplete }) {
  // Parse the opening message to separate question from guidelines
  const parseOpening = (message) => {
    if (message.includes('Take a moment')) {
      const parts = message.split('Take a moment')
      return {
        question: parts[0].trim(),
        guidelines: 'Take a moment' + (parts[1] || ''),
      }
    }
    return { question: message, guidelines: '' }
  }

  const { question: caseQuestion, guidelines } = parseOpening(openingMessage)

  const [messages, setMessages] = useState([])  // Start empty, opening shown separately
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setError(null)

    // Add user message immediately
    setMessages((prev) => [...prev, { role: 'candidate', content: userMessage }])
    setIsLoading(true)

    try {
      const response = await fetch(`/api/interviews/${sessionId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
      })

      if (!response.ok) throw new Error('Failed to get response')

      const data = await response.json()

      // Add interviewer response
      setMessages((prev) => [
        ...prev,
        { role: 'interviewer', content: data.interviewer_message },
      ])

      // Check if interview is complete
      if (data.is_complete) {
        setTimeout(() => onComplete(), 1500)
      }
    } catch (err) {
      setError('Unable to send message. Please try again.')
      // Remove the failed user message
      setMessages((prev) => prev.slice(0, -1))
      setInput(userMessage)
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="flex-shrink-0 bg-white border-b border-gray-100 px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-lg font-semibold text-gray-900">{caseTitle}</h1>
          <p className="text-sm text-gray-500">Case Interview</p>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Case Question - Prominent Display */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden animate-fade-in">
            <div className="bg-gray-900 px-5 py-3">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Case Question
              </span>
            </div>
            <div className="px-5 py-5">
              <p className="text-gray-800 text-[15px] leading-relaxed whitespace-pre-wrap">
                {caseQuestion}
              </p>
            </div>
          </div>

          {/* Guidelines - Secondary/FYI Display */}
          {guidelines && (
            <div className="flex items-start gap-3 px-4 py-3 bg-gray-100 rounded-xl animate-fade-in">
              <div className="flex-shrink-0 w-5 h-5 rounded-full bg-gray-300 flex items-center justify-center mt-0.5">
                <svg className="w-3 h-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500 leading-relaxed">
                {guidelines}
              </p>
            </div>
          )}

          {/* Divider before conversation */}
          {messages.length > 0 && (
            <div className="flex items-center gap-3 py-2">
              <div className="flex-1 h-px bg-gray-200" />
              <span className="text-xs text-gray-400 font-medium">Conversation</span>
              <div className="flex-1 h-px bg-gray-200" />
            </div>
          )}

          {/* Conversation Messages */}
          {messages.map((msg, idx) => (
            <MessageBubble
              key={idx}
              message={msg.content}
              isInterviewer={msg.role === 'interviewer'}
            />
          ))}

          {isLoading && <TypingIndicator />}

          {error && (
            <div className="text-center py-2">
              <p className="text-sm text-red-500">{error}</p>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input */}
      <footer className="flex-shrink-0 bg-white border-t border-gray-100 px-4 py-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="flex gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your response..."
              disabled={isLoading}
              rows={1}
              className="flex-1 px-4 py-3 rounded-xl border border-gray-200 bg-gray-50
                       text-gray-900 placeholder-gray-400 resize-none
                       focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent
                       disabled:opacity-50 transition-all"
              style={{
                minHeight: '48px',
                maxHeight: '150px',
              }}
              onInput={(e) => {
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'
              }}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-6 py-3 rounded-xl bg-gray-900 text-white font-medium
                       hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-900
                       focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              )}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </form>
      </footer>
    </div>
  )
}

export default InterviewChat
