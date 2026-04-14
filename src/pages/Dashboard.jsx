import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, BookOpen, Brain, ArrowRight, ExternalLink,
  Loader2, RefreshCw, ChevronRight, Stethoscope,
  FlaskConical, Newspaper, AlertCircle, BookMarked
} from 'lucide-react';

const TOPICS = [
  { id: 'general',    label: 'All Fields' },
  { id: 'pediatrics', label: 'Pediatrics' },
  { id: 'cardiology', label: 'Cardiology' },
  { id: 'neurology',  label: 'Neurology' },
  { id: 'infectious', label: 'Infectious Disease' },
  { id: 'emergency',  label: 'Emergency Med' },
];

// ── Control Centre Config ─────────────────────────────────────────────────
const CONTROL_CARDS = [
  {
    id: 'ddx',
    icon: Stethoscope,
    label: 'DDx Scan',
    sub: 'Differential diagnosis engine',
    stat: '12',
    statLabel: 'scans today',
    route: '/ddx',
    glowClass: 'glow-blue',
    accentColor: '#60a5fa',
  },
  {
    id: 'textbook',
    icon: BookMarked,
    label: 'Textbook Citations',
    sub: 'Gold Standard corpus search',
    stat: '85',
    statLabel: 'citations read',
    route: '/chat',
    glowClass: 'glow-purple',
    accentColor: '#a78bfa',
  },
  {
    id: 'quizzes',
    icon: FlaskConical,
    label: 'Pending Quizzes',
    sub: 'NEET-PG adaptive MCQs',
    stat: '4',
    statLabel: 'quizzes due',
    route: '/quizzes',
    glowClass: 'glow-green',
    accentColor: '#22c55e',
  },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [topic, setTopic]       = useState('general');
  const [page, setPage]         = useState(1);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [hasMore, setHasMore]   = useState(true);
  const [totalFound, setTotalFound] = useState(0);
  const [expanded, setExpanded] = useState({});  // { pmid: bool }

  const fetchFeed = useCallback(async (currentPage, currentTopic, append = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `http://localhost:8000/api/research/feed?page=${currentPage}&topic=${currentTopic}`
      );
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setArticles(prev => append ? [...prev, ...data.articles] : data.articles);
      setHasMore(data.has_more);
      setTotalFound(data.total_found);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    setPage(1);
    setArticles([]);
    fetchFeed(1, topic, false);
  }, [topic, fetchFeed]);

  const handleNext = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchFeed(nextPage, topic, true);
  };

  const toggleExpand = (pmid) => {
    setExpanded(prev => ({ ...prev, [pmid]: !prev[pmid] }));
  };

  return (
    <div className="dashboard-container">

      {/* ── Control Centre ──────────────────────────────────────────────── */}
      <section className="fade-in-up" style={{ animationDelay: '0ms' }}>
        <div className="section-label">
          <span className="live-dot pulse-animation" />
          Control Centre
        </div>
        <div className="control-grid">
          {CONTROL_CARDS.map((card, i) => (
            <button
              key={card.id}
              className="control-card hover-lift fade-in-up"
              style={{ animationDelay: `${i * 80}ms` }}
              onClick={() => navigate(card.route)}
            >
              <div className="control-card-top">
                <div className={`icon-wrapper ${card.glowClass}`}>
                  <card.icon size={22} />
                </div>
                <div className="control-stat-block">
                  <span className="control-stat-value" style={{ color: card.accentColor }}>{card.stat}</span>
                  <span className="control-stat-label">{card.statLabel}</span>
                </div>
              </div>
              <div className="control-card-body">
                <span className="control-label">{card.label}</span>
                <span className="control-sub">{card.sub}</span>
              </div>
              <div className="control-card-arrow">
                <ArrowRight size={16} />
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* ── Research Feed ───────────────────────────────────────────────── */}
      <section className="fade-in-up" style={{ animationDelay: '200ms' }}>

        {/* Feed header */}
        <div className="feed-header">
          <div>
            <div className="section-label">
              <Newspaper size={14} />
              Live Research Feed
            </div>
            <h2 className="feed-title gold-heading">Latest Medical Evidence</h2>
            {totalFound > 0 && (
              <p className="feed-meta">{totalFound.toLocaleString()} articles indexed · Sorted by publication date</p>
            )}
          </div>
          <button
            className="btn-outline-glow"
            onClick={() => { setPage(1); setArticles([]); fetchFeed(1, topic, false); }}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'icon-spin-fast' : ''} />
            Refresh
          </button>
        </div>

        {/* Topic Pills */}
        <div className="topic-pills-row">
          {TOPICS.map(t => (
            <button
              key={t.id}
              className={`topic-pill-btn ${topic === t.id ? 'active' : ''}`}
              onClick={() => setTopic(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Error state */}
        {error && (
          <div className="feed-error">
            <AlertCircle size={18} />
            <span>Could not load research feed. Is the backend running?</span>
            <button className="btn-outline-glow" onClick={() => fetchFeed(page, topic, false)}>Retry</button>
          </div>
        )}

        {/* Article cards */}
        <div className="research-feed-list">
          {articles.map((art, i) => (
            <article
              key={art.pmid}
              className="research-card glass-card fade-in-up"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              {/* Card header */}
              <div className="research-card-header">
                <div className="research-card-meta">
                  <span className="research-journal">{art.journal}</span>
                  <span className="research-dot">·</span>
                  <span className="research-year">{art.year}</span>
                  <span className="research-dot">·</span>
                  <span className="research-authors">{art.authors}</span>
                </div>
                <span className="pmid-badge">PMID {art.pmid}</span>
              </div>

              {/* Title */}
              <h3 className="research-title">{art.title}</h3>

              {/* AI Summary */}
              <div className="research-summary-block">
                <div className="ai-summary-label">
                  <Brain size={12} />
                  AI Clinical Summary
                </div>
                <p className="research-summary">{art.summary}</p>
              </div>

              {/* Expanded abstract */}
              {expanded[art.pmid] && (
                <div className="research-abstract fade-in-up">
                  <p>{art.abstract}</p>
                </div>
              )}

              {/* Footer actions */}
              <div className="research-card-footer">
                <button
                  className="toggle-abstract-btn"
                  onClick={() => toggleExpand(art.pmid)}
                >
                  {expanded[art.pmid] ? 'Hide abstract ↑' : 'Show full abstract ↓'}
                </button>
                <a
                  href={art.pubmed_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="read-more-btn"
                >
                  Read full paper
                  <ExternalLink size={13} />
                </a>
              </div>
            </article>
          ))}

          {/* Loading skeleton */}
          {loading && (
            <div className="feed-loading">
              {[0,1,2,4,5].map(i => (
                <div key={i} className="research-skeleton glass-card">
                  <div className="skeleton-line short" />
                  <div className="skeleton-line long" />
                  <div className="skeleton-line medium" />
                  <div className="skeleton-line medium" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Next / Load more */}
        {!loading && articles.length > 0 && (
          <div className="feed-pagination">
            {hasMore ? (
              <button className="btn-animated-pulse" onClick={handleNext}>
                Next 5 Articles
                <ChevronRight size={16} />
              </button>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                You've reached the end of this topic's results.
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
