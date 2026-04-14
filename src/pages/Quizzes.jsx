import React, { useState, useEffect } from 'react';
import { BookOpen, Check, X, Award, ChevronRight, Brain, Zap, Target, RotateCcw } from 'lucide-react';

const QUIZ_TOPICS = [
  { name: 'Cardiology', icon: '🫀', color: '#ef4444', questions: 10 },
  { name: 'Neurology', icon: '🧠', color: '#8b5cf6', questions: 12 },
  { name: 'Pharmacology', icon: '💊', color: '#06b6d4', questions: 15 },
  { name: 'Anatomy', icon: '🦴', color: '#10b981', questions: 8 },
  { name: 'Pathology', icon: '🔬', color: '#f59e0b', questions: 11 },
  { name: 'Pediatrics', icon: '👶', color: '#ec4899', questions: 14 },
];

const QUIZ_QUESTIONS = [
  {
    id: 1,
    question: "A 60-year-old male presents with crushing substernal chest pain radiating to the left arm. ECG shows ST elevation in leads II, III, and aVF. Which coronary artery is most likely occluded?",
    options: ["Left Anterior Descending (LAD)", "Right Coronary Artery (RCA)", "Left Circumflex (LCx)", "Posterior Descending Artery (PDA)"],
    correctAnswer: 1,
    explanation: "Leads II, III, and aVF correspond to the inferior wall of the heart, which is supplied by the Right Coronary Artery (RCA) in 85% of people. This is a classic inferior STEMI pattern.",
    source: "Harrison's Principles of Internal Medicine, Ch. 272"
  },
  {
    id: 2,
    question: "Which of the following is the first-line treatment for an acute gout flare in a patient also diagnosed with peptic ulcer disease?",
    options: ["Indomethacin", "Colchicine", "Allopurinol", "Prednisone"],
    correctAnswer: 1,
    explanation: "NSAIDs like Indomethacin are contraindicated in active Peptic Ulcer Disease. Colchicine is a safer alternative for acute gout. Allopurinol is for long-term prophylaxis only.",
    source: "Nelson's Textbook of Pediatrics, 22nd Ed."
  }
];

export default function Quizzes() {
  const [activeTopic, setActiveTopic] = useState(null);
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [score, setScore] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [quizComplete, setQuizComplete] = useState(false);
  const [animateOptions, setAnimateOptions] = useState(false);

  useEffect(() => {
    if (activeTopic) {
      setAnimateOptions(false);
      const t = setTimeout(() => setAnimateOptions(true), 100);
      return () => clearTimeout(t);
    }
  }, [currentQuestionIdx, activeTopic]);

  const handleStartQuiz = (topic) => {
    setActiveTopic(topic);
    setCurrentQuestionIdx(0);
    setScore(0);
    setQuizComplete(false);
    setSelectedOption(null);
    setShowExplanation(false);
  };

  const handleOptionSelect = (idx) => {
    if (selectedOption !== null) return;
    setSelectedOption(idx);
    setShowExplanation(true);
    if (idx === QUIZ_QUESTIONS[currentQuestionIdx].correctAnswer) {
      setScore(prev => prev + 1);
    }
  };

  const nextQuestion = () => {
    if (currentQuestionIdx < QUIZ_QUESTIONS.length - 1) {
      setCurrentQuestionIdx(prev => prev + 1);
      setSelectedOption(null);
      setShowExplanation(false);
    } else {
      setQuizComplete(true);
    }
  };

  // Topic Selection Screen
  if (!activeTopic) {
    return (
      <div className="quiz-container">
        <div className="quiz-header fade-in-up">
          <Brain size={36} className="glow-purple" style={{ marginBottom: '12px' }} />
          <h1 className="quiz-main-title gold-heading">Personalized Medical Quizzes</h1>
          <p className="quiz-main-sub">AI-curated MCQs targeting NEET-PG & INI-CET exam patterns from your textbook corpus.</p>
        </div>

        <div className="quiz-topics-grid">
          {QUIZ_TOPICS.map((topic, i) => (
            <div
              key={topic.name}
              className="quiz-topic-card glass-card hover-lift fade-in-up"
              style={{ animationDelay: `${i * 80}ms`, '--topic-color': topic.color }}
              onClick={() => handleStartQuiz(topic.name)}
            >
              <div className="topic-icon-ring" style={{ background: `${topic.color}20`, boxShadow: `0 0 20px ${topic.color}30` }}>
                <span className="topic-emoji">{topic.icon}</span>
              </div>
              <h3 className="topic-name">{topic.name}</h3>
              <p className="topic-count">{topic.questions} High-Yield Questions</p>
              <div className="topic-cta" style={{ color: topic.color }}>
                Start Quiz <ChevronRight size={16} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Quiz Complete Screen
  if (quizComplete) {
    const pct = Math.round((score / QUIZ_QUESTIONS.length) * 100);
    const grade = pct >= 80 ? { label: 'Excellent!', color: '#4ade80', icon: '🏆' }
      : pct >= 60 ? { label: 'Good Work!', color: '#facc15', icon: '⭐' }
      : { label: 'Keep Practicing', color: '#f87171', icon: '📚' };

    return (
      <div className="quiz-complete-screen fade-in-up">
        <div className="quiz-complete-card glass-card">
          <div className="complete-icon-ring" style={{ boxShadow: `0 0 40px ${grade.color}50` }}>
            <span style={{ fontSize: '3rem' }}>{grade.icon}</span>
          </div>
          <h3 className="complete-title gold-heading">{grade.label}</h3>
          <p className="complete-score" style={{ color: grade.color }}>{score} / {QUIZ_QUESTIONS.length} Correct</p>

          <div className="score-progress-bar">
            <div className="score-progress-fill"
              style={{ width: `${pct}%`, background: grade.color, boxShadow: `0 0 15px ${grade.color}` }}>
            </div>
          </div>
          <p className="score-pct">{pct}% Score</p>

          <div className="complete-actions">
            <button onClick={() => setActiveTopic(null)} className="quiz-btn-outline">
              <RotateCcw size={16} /> Change Topic
            </button>
            <button onClick={() => handleStartQuiz(activeTopic)} className="quiz-btn-primary">
              <Zap size={16} /> Retake Quiz
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Active Question Screen
  const currentQ = QUIZ_QUESTIONS[currentQuestionIdx];
  const progress = ((currentQuestionIdx) / QUIZ_QUESTIONS.length) * 100;

  return (
    <div className="quiz-active-screen">
      {/* Progress Header */}
      <div className="quiz-progress-header fade-in-up">
        <button onClick={() => setActiveTopic(null)} className="quiz-back-btn">← Back</button>
        <div className="quiz-progress-track">
          <div className="quiz-progress-fill glow-blue-bg" style={{ width: `${progress}%`, transition: 'width 0.5s ease' }} />
        </div>
        <span className="quiz-progress-label">{currentQuestionIdx + 1}/{QUIZ_QUESTIONS.length}</span>
      </div>

      {/* Question Card */}
      <div className="quiz-question-card glass-card fade-in-up" style={{ animationDelay: '50ms' }}>
        <div className="question-meta">
          <span className="topic-pill" style={{ background: 'rgba(96,165,250,0.15)', color: '#60a5fa' }}>
            <Target size={13} /> {activeTopic}
          </span>
          <span className="question-score-badge">Score: {score}</span>
        </div>
        <h2 className="question-text">{currentQ.question}</h2>

        {/* Answer Options */}
        <div className="options-list">
          {currentQ.options.map((opt, idx) => {
            const isSelected = selectedOption === idx;
            const isCorrect = idx === currentQ.correctAnswer;
            const isAnswered = selectedOption !== null;

            let cls = 'option-btn';
            if (isAnswered && isCorrect) cls += ' correct';
            else if (isAnswered && isSelected && !isCorrect) cls += ' incorrect';
            else if (isAnswered) cls += ' dimmed';

            return (
              <button
                key={idx}
                className={`${cls} ${animateOptions ? 'stagger-slide-in' : ''}`}
                style={{ animationDelay: `${idx * 80}ms` }}
                onClick={() => handleOptionSelect(idx)}
                disabled={isAnswered}
              >
                <span className="option-letter">{String.fromCharCode(65 + idx)}</span>
                <span className="option-text">{opt}</span>
                <span className="option-icon">
                  {isAnswered && isCorrect && <Check size={20} className="icon-correct" />}
                  {isAnswered && isSelected && !isCorrect && <X size={20} className="icon-incorrect" />}
                </span>
              </button>
            );
          })}
        </div>

        {/* Explanation */}
        {showExplanation && (
          <div className="explanation-block fade-in-up">
            <div className="explanation-header">
              <BookOpen size={16} className="glow-blue" />
              <span>Clinical Explanation</span>
            </div>
            <p className="explanation-text">{currentQ.explanation}</p>
            <p className="explanation-source">📚 Source: {currentQ.source}</p>
            <button onClick={nextQuestion} className="quiz-btn-primary" style={{ marginTop: '20px', width: '100%' }}>
              {currentQuestionIdx === QUIZ_QUESTIONS.length - 1 ? '🏁 Finish Quiz' : 'Next Question →'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
