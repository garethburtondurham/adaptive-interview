function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="bg-white border border-gray-100 rounded-2xl px-5 py-4 shadow-sm">
        <div className="text-xs font-medium text-gray-400 mb-2">
          Interviewer
        </div>
        <div className="flex items-center gap-1.5">
          <div
            className="w-2 h-2 bg-gray-400 rounded-full animate-pulse-dot"
            style={{ animationDelay: '0ms' }}
          />
          <div
            className="w-2 h-2 bg-gray-400 rounded-full animate-pulse-dot"
            style={{ animationDelay: '200ms' }}
          />
          <div
            className="w-2 h-2 bg-gray-400 rounded-full animate-pulse-dot"
            style={{ animationDelay: '400ms' }}
          />
        </div>
      </div>
    </div>
  )
}

export default TypingIndicator
