function CompletionScreen({ onStartNew }) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        {/* Success Icon */}
        <div className="mb-8 animate-fade-in">
          <div className="w-20 h-20 mx-auto bg-green-50 rounded-full flex items-center justify-center">
            <svg
              className="w-10 h-10 text-green-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        </div>

        {/* Message */}
        <div className="animate-slide-up">
          <h1 className="text-3xl font-semibold text-gray-900 mb-4">
            Interview Complete
          </h1>
          <p className="text-gray-500 mb-8 leading-relaxed">
            Thank you for completing the case interview. Your responses have been
            recorded. We appreciate the time and effort you put into this
            exercise.
          </p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8 animate-slide-up">
          <h2 className="text-sm font-medium text-gray-700 mb-3">What happens next?</h2>
          <p className="text-sm text-gray-500">
            Your interviewer will review your responses and provide feedback.
            You should expect to hear back within the next few days.
          </p>
        </div>

        {/* Action */}
        <button
          onClick={onStartNew}
          className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
        >
          Start another interview
        </button>
      </div>
    </div>
  )
}

export default CompletionScreen
