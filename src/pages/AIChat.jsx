import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Library, ExternalLink, X, ChevronDown, Loader2, Search } from 'lucide-react';

const MAX_FREE_QUERIES = 20;

const INITIAL_MESSAGES = [
  {
    id: 1,
    sender: 'ai',
    text: "Hello Dr. Swetha. I'm your Medico AI clinical companion, powered by your offline Gold Standard textbook library and live PubMed synthesis.\n\nAsk me anything — differential diagnoses, treatment protocols, drug interactions, or clinical guidelines.",
    sources: [],
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  }
];

const SUGGESTED_QUERIES = [
  "What are the red flags in pediatric fever management?",
  "Differentiate Kawasaki disease from Viral Exanthem",
  "First-line drugs for pediatric hypertensive emergency",
  "Nelson's criteria for Acute Rheumatic Fever diagnosis",
];

export default function AIChat() {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [queryCount, setQueryCount] = useState(0);
  const [activeCitation, setActiveCitation] = useState(null);
  const [sourcePanelOpen, setSourcePanelOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const parseTextWithCitations = (text) => {
    if (!text) return null;
    const citationRegex = /\[(?:Source\s*)?(\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(text)) !== null) {
      if (match.index > lastIndex) parts.push(text.substring(lastIndex, match.index));
      const num = parseInt(match[1], 10);
      parts.push(
        <button
          key={`${match.index}-${num}`}
          className={`chat-citation-badge ${activeCitation === num ? 'active' : ''}`}
          onClick={() => { setActiveCitation(num); setSourcePanelOpen(true); }}
          onMouseEnter={() => setActiveCitation(num)}
        >
          {num}
        </button>
      );
      lastIndex = citationRegex.lastIndex;
    }
    if (lastIndex < text.length) parts.push(text.substring(lastIndex));
    return <>{parts}</>;
  };

  const handleSend = async (query = inputValue) => {
    if (!query.trim() || queryCount >= MAX_FREE_QUERIES) return;
    const queryText = query;
    setMessages(prev => [...prev, {
      id: Date.now(), sender: 'user', text: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
    setInputValue('');
    setIsTyping(true);
    setActiveCitation(null);
    setQueryCount(prev => prev + 1);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: "demo-session-123", query: queryText })
      });
      const data = await response.json();
      setMessages(prev => [...prev, {
        id: Date.now() + 1, sender: 'ai',
        text: data.answer, sources: data.sources || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
      if (data.sources?.length > 0) setSourcePanelOpen(true);
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1, sender: 'ai',
        text: "Backend unreachable. Please ensure the FastAPI server is running on port 8000.",
        sources: [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSubmit = (e) => { e.preventDefault(); handleSend(); };

  const latestAiSources = [...messages].reverse().find(m => m.sender === 'ai')?.sources || [];
  const isFirstMessage = messages.length === 1;

  return (
    <div className="perplexity-layout">
      {/* LEFT: Main Chat Column */}
      <div className={`perplexity-chat-col ${sourcePanelOpen ? 'panel-open' : ''}`}>

        {/* Messages Stream */}
        <div className="perplexity-messages-stream">
          {isFirstMessage && (
            <div className="perplexity-welcome fade-in-up">
              <div className="perplexity-welcome-icon pulse-glow">
                <Sparkles size={32} />
              </div>
              <h1 className="perplexity-welcome-title gold-heading">What can I help you find?</h1>
              <p className="perplexity-welcome-sub">Synthesizing knowledge from Nelson's, Piyush Gupta & live PubMed.</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={msg.id} className={`perplexity-msg fade-in-up ${msg.sender}`} style={{ animationDelay: `${i * 30}ms` }}>
              {msg.sender === 'ai' ? (
                <div className="ai-msg-block">
                  {msg.sources?.length > 0 && (
                    <div className="sources-bubbles">
                      {msg.sources.slice(0, 4).map((src, idx) => (
                        <button key={idx}
                          className={`source-bubble ${activeCitation === idx + 1 ? 'active' : ''}`}
                          onClick={() => { setActiveCitation(idx + 1); setSourcePanelOpen(true); }}>
                          <span className="bubble-num">{idx + 1}</span>
                          <span className="bubble-label">{src.title?.substring(0, 28)}...</span>
                        </button>
                      ))}
                      {msg.sources.length > 4 && (
                        <button className="source-bubble more-bubble" onClick={() => setSourcePanelOpen(true)}>
                          +{msg.sources.length - 4} more
                        </button>
                      )}
                    </div>
                  )}
                  <div className="ai-answer-text">
                    {parseTextWithCitations(msg.text)}
                  </div>
                  <div className="ai-msg-footer">
                    <span className="ai-badge"><Sparkles size={11} /> Medico AI</span>
                    <span className="ai-timestamp">{msg.timestamp}</span>
                    {msg.sources?.length > 0 && (
                      <button className="sources-toggle-btn" onClick={() => setSourcePanelOpen(!sourcePanelOpen)}>
                        <Library size={13} />
                        {msg.sources.length} Sources
                        <ChevronDown size={13} className={sourcePanelOpen ? 'rotate-180' : ''} />
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="user-msg-pill">{msg.text}</div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="perplexity-msg ai fade-in-up">
              <div className="ai-msg-block">
                <div className="typing-indicator">
                  <Search size={14} className="icon-spin-slow" />
                  <span>Searching textbooks & PubMed</span>
                  <div className="typing-dots">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Queries — shown only at start */}
        {isFirstMessage && (
          <div className="suggestions-row fade-in-up" style={{ animationDelay: '200ms' }}>
            {SUGGESTED_QUERIES.map((q, i) => (
              <button key={i} className="suggestion-chip" onClick={() => handleSend(q)}>
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Floating Input Bar */}
        <div className="perplexity-input-shell">
          {queryCount >= MAX_FREE_QUERIES ? (
            <div className="limit-banner">
              <span>🔒 Free tier limit reached.</span>
              <button className="upgrade-cta">Upgrade to Pro →</button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="perplexity-input-form">
              <Search size={18} className="input-search-icon" />
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                placeholder="Ask a clinical question..."
                className="perplexity-input"
                autoFocus
              />
              <button type="submit"
                disabled={!inputValue.trim() || isTyping}
                className={`perplexity-send-btn ${inputValue.trim() && !isTyping ? 'active' : ''}`}>
                {isTyping ? <Loader2 size={20} className="icon-spin-fast" /> : <Send size={20} />}
              </button>
            </form>
          )}
          <p className="input-disclaimer">AI synthesizes from your Gold Standard textbook library. Always verify clinical decisions.</p>
        </div>
      </div>

      {/* RIGHT: Sliding Sources Panel */}
      <div className={`sources-slide-panel ${sourcePanelOpen ? 'open' : ''}`}>
        <div className="sources-panel-header">
          <div className="sources-panel-title">
            <Library size={18} />
            <span>References</span>
            <span className="source-count-badge">{latestAiSources.length}</span>
          </div>
          <button onClick={() => setSourcePanelOpen(false)} className="close-panel-btn">
            <X size={18} />
          </button>
        </div>
        <div className="sources-panel-list">
          {latestAiSources.map((src, idx) => {
            const isPubMed = src.type === 'pubmed';
            const isActive = activeCitation === idx + 1;
            return (
              <div key={idx}
                className={`source-detail-card ${isActive ? 'active' : ''}`}
                onMouseEnter={() => setActiveCitation(idx + 1)}
                onMouseLeave={() => setActiveCitation(null)}
                onClick={() => src.url && window.open(src.url, '_blank')}>
                <div className="source-detail-top">
                  <span className={`source-type-pill ${isPubMed ? 'pubmed' : 'corpus'}`}>
                    {isPubMed ? 'PubMed' : 'Textbook'}
                  </span>
                  <span className={`source-num-badge ${isActive ? 'active' : ''}`}>[{idx + 1}]</span>
                </div>
                <h4 className="source-detail-title">{src.title}</h4>
                <p className="source-detail-snippet">"{src.snippet}"</p>
                {src.url && (
                  <div className="source-detail-link">
                    <ExternalLink size={12} /> View Full Source
                  </div>
                )}
              </div>
            );
          })}
          {latestAiSources.length === 0 && (
            <div className="panel-empty">
              <Library size={32} style={{ opacity: 0.2 }} />
              <p>Sources will appear here after your first query.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
