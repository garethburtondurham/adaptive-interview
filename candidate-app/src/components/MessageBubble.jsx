function MessageBubble({ message, isInterviewer }) {
  return (
    <div
      className={`flex ${isInterviewer ? 'justify-start' : 'justify-end'} animate-slide-up`}
    >
      <div
        className={`max-w-[80%] md:max-w-[70%] ${
          isInterviewer
            ? 'bg-white border border-gray-100 text-gray-800'
            : 'bg-gray-900 text-white'
        } rounded-2xl px-5 py-4 shadow-sm`}
      >
        {/* Role indicator for interviewer */}
        {isInterviewer && (
          <div className="text-xs font-medium text-gray-400 mb-1.5">
            Interviewer
          </div>
        )}

        {/* Message content with preserved line breaks */}
        <div className="text-[15px] leading-relaxed whitespace-pre-wrap">
          {message}
        </div>
      </div>
    </div>
  )
}

export default MessageBubble
