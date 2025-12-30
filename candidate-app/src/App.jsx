import { useState } from 'react'
import CaseSelection from './components/CaseSelection'
import InterviewChat from './components/InterviewChat'
import CompletionScreen from './components/CompletionScreen'

const VIEWS = {
  SELECTION: 'selection',
  INTERVIEW: 'interview',
  COMPLETE: 'complete',
}

function App() {
  const [currentView, setCurrentView] = useState(VIEWS.SELECTION)
  const [sessionData, setSessionData] = useState(null)

  const handleStartInterview = (data) => {
    setSessionData(data)
    setCurrentView(VIEWS.INTERVIEW)
  }

  const handleInterviewComplete = () => {
    setCurrentView(VIEWS.COMPLETE)
  }

  const handleStartNew = () => {
    setSessionData(null)
    setCurrentView(VIEWS.SELECTION)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {currentView === VIEWS.SELECTION && (
        <CaseSelection onStart={handleStartInterview} />
      )}
      {currentView === VIEWS.INTERVIEW && sessionData && (
        <InterviewChat
          sessionId={sessionData.sessionId}
          caseTitle={sessionData.caseTitle}
          openingMessage={sessionData.openingMessage}
          onComplete={handleInterviewComplete}
        />
      )}
      {currentView === VIEWS.COMPLETE && (
        <CompletionScreen onStartNew={handleStartNew} />
      )}
    </div>
  )
}

export default App
