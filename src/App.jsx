import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import AIChat from './pages/AIChat';
import Quizzes from './pages/Quizzes';
import DailyBriefing from './pages/DailyBriefing';
import DDxAssistant from './pages/DDxAssistant';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="chat" element={<AIChat />} />
          <Route path="ddx" element={<DDxAssistant />} />
          <Route path="quizzes" element={<Quizzes />} />
          <Route path="briefing" element={<DailyBriefing />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
