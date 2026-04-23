import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, BookOpen, Brain, ArrowRight, ExternalLink,
  Loader2, RefreshCw, ChevronRight, Stethoscope,
  FlaskConical, Newspaper, AlertCircle, BookMarked, ScanSearch, X, FileText
} from 'lucide-react';

const TOPICS = [
  { id: 'general',    label: 'All Fields' },
  { id: 'pediatrics', label: 'Pediatrics' },
  { id: 'cardiology', label: 'Cardiology' },
  { id: 'neurology',  label: 'Neurology' },
];

const GUIDE_SOURCES = [
  { id: 'all', label: 'All Sources' },
  { id: 'WHO SEARO', label: 'WHO SEARO' },
  { id: 'DOHFW', label: 'DOHFW' }
];

export default function Dashboard() {
  const navigate = useNavigate();
  
  // High-Level Tab State
  const [activeMainTab, setActiveMainTab] = useState('academic'); // 'academic' | 'guidelines'

  // Feed state
  const [topic, setTopic]       = useState('general');
  const [page, setPage]         = useState(1);
  const [articles, setArticles] = useState([]);
  const [loadingFeeds, setLoadingFeeds] = useState(false);
  const [hasMore, setHasMore]   = useState(true);
  
  // Guidelines state
  const [guideSource, setGuideSource] = useState('all');
  const [guidePage, setGuidePage] = useState(1);
  const [guidelines, setGuidelines] = useState([]);
  const [loadingGuide, setLoadingGuide] = useState(false);
  
  const [error, setError]       = useState(null);
  const [expanded, setExpanded] = useState({});

  // PDF Analysis Modal State
  const [activePdfUrl, setActivePdfUrl] = useState(null);
  const [pdfAnalysis, setPdfAnalysis] = useState("");
  const [analyzingPdf, setAnalyzingPdf] = useState(false);
  const [pdfError, setPdfError] = useState("");

  const fetchScholarly = useCallback(async (currentPage, currentTopic, append = false) => {
    setLoadingFeeds(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/research/scholarly?page=${currentPage}&topic=${currentTopic}`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setArticles(prev => append ? [...prev, ...data.articles] : data.articles);
      setHasMore(data.has_more);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingFeeds(false);
    }
  }, []);

  const fetchGuidelines = useCallback(async (currentPage, append = false) => {
    setLoadingGuide(true);
    try {
      const res = await fetch(`http://localhost:8000/api/research/guidelines?page=${currentPage}`);
      if (res.ok) {
        const data = await res.json();
        setGuidelines(prev => append ? [...prev, ...data.guidelines] : data.guidelines);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingGuide(false);
    }
  }, []);

  const triggerPdfAnalysis = async (url) => {
    setActivePdfUrl(url);
    setPdfAnalysis("");
    setPdfError("");
    setAnalyzingPdf(true);
    try {
      const res = await fetch("http://localhost:8000/api/research/analyze_pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, source_type: "document" })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to analyze document.");
      }
      const data = await res.json();
      setPdfAnalysis(data.analysis_markdown);
    } catch (err) {
      setPdfError(err.message);
    } finally {
      setAnalyzingPdf(false);
    }
  };

  useEffect(() => {
    setPage(1);
    fetchScholarly(1, topic, false);
  }, [topic, fetchScholarly]);
  
  useEffect(() => {
    setGuidePage(1);
    fetchGuidelines(1, false);
  }, [fetchGuidelines]);

  const handleNextScholarly = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchScholarly(nextPage, topic, true);
  };

  const handleNextGuidelines = () => {
    const nextPage = guidePage + 1;
    setGuidePage(nextPage);
    fetchGuidelines(nextPage, true);
  };

  const toggleExpand = (id) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredGuidelines = guideSource === 'all' ? guidelines : guidelines.filter(g => g.source === guideSource);

  return (
    <div className="dashboard-container" style={{ position: 'relative' }}>
      
      {/* ── PDF Analysis Modal Overlay ──────────────── */}
      {activePdfUrl && (
        <div className="pdf-modal-overlay fade-in-up">
          <div className="pdf-modal-container glass-card">
            <button className="pdf-close-btn" onClick={() => setActivePdfUrl(null)}>
              <X size={20} />
            </button>
            <div className="pdf-modal-split">
              <div className="pdf-analysis-pane">
                <h3 className="gold-heading-sm" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
                  <Brain size={18} /> Deep Clinical Analysis
                </h3>
                
                {analyzingPdf && (
                  <div className="pdf-loading">
                    <RefreshCw className="icon-spin-fast" size={24} style={{ color: 'var(--color-primary)', marginBottom: '1rem' }} />
                    <p>Downloading and analyzing document...</p>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>This may take 10-15 seconds.</p>
                  </div>
                )}

                {pdfError && (
                  <div className="pdf-error">
                    <AlertCircle size={16} />
                    <span>{pdfError}</span>
                  </div>
                )}

                {!analyzingPdf && pdfAnalysis && (
                  <div className="pdf-markdown-body fade-in-up">
                     {pdfAnalysis.split('\n').map((line, idx) => {
                       if (line.startsWith('### ')) return <h4 key={idx}>{line.replace('### ', '')}</h4>;
                       if (line.startsWith('- ')) return <li key={idx}>{line.substring(2)}</li>;
                       if (line.trim() === '') return <br key={idx} />;
                       return <p key={idx}>{line}</p>;
                     })}
                  </div>
                )}
              </div>
              <div className="pdf-viewer-pane">
                 <iframe 
                   src={`http://localhost:8000/api/research/proxy_pdf?url=${encodeURIComponent(activePdfUrl)}`} 
                   title="PDF Viewer" 
                   className="pdf-iframe"
                 />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Top Level Dashboard Tabs ──────────────── */}
      <div className="dashboard-tabs">
        <button 
          className={`tab-btn ${activeMainTab === 'academic' ? 'active' : ''}`}
          onClick={() => setActiveMainTab('academic')}
        >
          <BookOpen size={16} className="tab-icon" /> Academic Articles
        </button>
        <button 
          className={`tab-btn ${activeMainTab === 'guidelines' ? 'active' : ''}`}
          onClick={() => setActiveMainTab('guidelines')}
        >
          <FileText size={16} className="tab-icon" /> Medical Guidelines
        </button>
      </div>

      <div style={{ display: 'block', marginTop: '1.5rem' }}>
        
        {/* ── Tab: Academic Articles ──────────────── */}
        {activeMainTab === 'academic' && (
          <section className="fade-in-up">
            <div className="feed-header">
              <div>
                <div className="section-label">
                  <Newspaper size={14} /> Clinical Evidence Feed
                </div>
                <h2 className="feed-title gold-heading">Peer-Reviewed Papers</h2>
              </div>
              <button
                className="btn-outline-glow"
                onClick={() => { setPage(1); fetchScholarly(1, topic, false); }}
                disabled={loadingFeeds}
              >
                <RefreshCw size={14} className={loadingFeeds ? 'icon-spin-fast' : ''} />
              </button>
            </div>

            <div className="topic-pills-row" style={{ marginBottom: '1.5rem' }}>
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

            {error && (
              <div className="feed-error">
                <AlertCircle size={18} />
                <span>Could not load research feed. Backend running?</span>
              </div>
            )}

            <div className="research-feed-list">
              {articles.map((art, i) => (
                <article key={art.pmid} className="research-card glass-card fade-in-up" style={{ animationDelay: `${i * 60}ms` }}>
                  <div className="research-card-header">
                    <div className="research-card-meta">
                      <span className="research-journal">{art.journal}</span>
                      <span className="research-dot">·</span>
                      <span className="research-year">{art.year}</span>
                    </div>
                    <span className="pmid-badge">PMID {art.pmid}</span>
                  </div>
                  <h3 className="research-title">{art.title}</h3>
                  
                  <div className="research-summary-block">
                    <div className="ai-summary-label">
                      <Brain size={12} /> AI Clinical Summary
                    </div>
                    <p className="research-summary">{art.summary}</p>
                  </div>
                  
                  {expanded[art.pmid] && (
                    <div className="research-abstract fade-in-up">
                      <p>{art.abstract}</p>
                    </div>
                  )}
                  
                  <div className="research-card-footer">
                    <button className="toggle-abstract-btn" onClick={() => toggleExpand(art.pmid)}>
                      {expanded[art.pmid] ? 'Hide abstract ↑' : 'Show full abstract ↓'}
                    </button>
                    <div className="action-row" style={{ display: 'flex', gap: '0.75rem' }}>
                       {art.pdf_url && (
                          <button className="btn-solid-glow" style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.4rem'}} onClick={() => triggerPdfAnalysis(art.pdf_url)}>
                            <ScanSearch size={14} /> Analyze PDF
                          </button>
                       )}
                      <a href={art.pubmed_url} target="_blank" rel="noopener noreferrer" className="read-more-btn">
                        Read full paper <ExternalLink size={13} />
                      </a>
                    </div>
                  </div>
                </article>
              ))}

              {loadingFeeds && (
                <div className="feed-loading">
                  <div className="research-skeleton glass-card">
                     <div className="skeleton-line short" />
                     <div className="skeleton-line long" />
                  </div>
                </div>
              )}

              {!loadingFeeds && hasMore && articles.length > 0 && (
                <button className="btn-animated-pulse" onClick={handleNextScholarly} style={{ marginTop: '1rem', width: '100%' }}>
                  Load Next 5 Articles <ChevronRight size={16} />
                </button>
              )}
            </div>
          </section>
        )}

        {/* ── Tab: Medical Guidelines ──────────────── */}
        {activeMainTab === 'guidelines' && (
          <section className="fade-in-up">
             <div className="feed-header" style={{ marginBottom: '1.5rem' }}>
              <div>
                <div className="section-label" style={{ color: 'var(--color-primary)' }}>
                  <AlertCircle size={14} /> Live Alerts
                </div>
                <h2 className="feed-title gold-heading">Authority Guidelines</h2>
              </div>
              <button
                className="btn-outline-glow"
                onClick={() => { setGuidePage(1); fetchGuidelines(1, false); }}
                disabled={loadingGuide}
              >
                <RefreshCw size={14} className={loadingGuide ? 'icon-spin-fast' : ''} />
              </button>
            </div>

            <div className="topic-pills-row" style={{ marginBottom: '1.5rem' }}>
              {GUIDE_SOURCES.map(t => (
                <button
                  key={t.id}
                  className={`topic-pill-btn ${guideSource === t.id ? 'active' : ''}`}
                  onClick={() => setGuideSource(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="guidelines-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {loadingGuide && guidePage === 1 && <p>Loading guidelines...</p>}
              {!loadingGuide && filteredGuidelines.length === 0 && <p className="text-muted">No recent guidelines found for this source.</p>}
              
              {filteredGuidelines.map((item, i) => {
                 const uniqueId = `guide-${i}-${item.published}`;
                 return (
                 <article key={uniqueId} className="research-card glass-card hover-lift fade-in-up" style={{ animationDelay: `${i * 40}ms`, padding: '1.5rem' }}>
                    <div className="research-card-header" style={{ marginBottom: '0.75rem' }}>
                      <div className="research-card-meta">
                        <span className="research-journal" style={{ color: 'var(--color-primary)', fontWeight: '600', fontSize: '0.85rem'}}>{item.source}</span>
                      </div>
                      <span className="pmid-badge" style={{ fontSize: '0.7rem' }}>
                        {new Date(item.published).toLocaleDateString() === 'Invalid Date' ? item.published : new Date(item.published).toLocaleDateString()}
                      </span>
                    </div>
                    
                    <h4 style={{ color: '#fff', fontSize: '1.1rem', marginBottom: '1rem', lineHeight: '1.4' }}>
                      {item.title}
                    </h4>

                    <div className="research-summary-block" style={{ padding: '1rem', marginBottom: '1rem' }}>
                      <div className="ai-summary-label" style={{ fontSize: '0.75rem' }}>
                        <Brain size={12} /> AI Clinical Summary
                      </div>
                      <p className="research-summary" style={{ fontSize: '0.9rem' }}>{item.summary}</p>
                    </div>
                    
                    {expanded[uniqueId] && (
                      <div className="research-abstract fade-in-up" style={{ padding: '1rem' }}>
                        <p style={{ fontSize: '0.9rem', marginBottom: '10px' }}>
                          <span style={{ color: 'var(--gold-mid)' }}>Details:</span> Please review the embedded document below for exact clinical intervention rules.
                        </p>
                        
                        {/* THE INLINE PDF RENDERER */}
                        {item.pdf_url ? (
                            <iframe 
                              src={`http://localhost:8000/api/research/proxy_pdf?url=${encodeURIComponent(item.pdf_url)}`} 
                              className="inline-pdf-iframe" 
                              title="Guideline Document"
                            />
                        ) : (
                            <div className="feed-error" style={{ padding: '10px', fontSize: '0.8rem' }}>
                               No direct PDF integration available for this source. Please click "Read official".
                            </div>
                        )}
                      </div>
                    )}
                    
                    <div className="research-card-footer" style={{ borderTop: '1px solid var(--black-border)', paddingTop: '1rem', marginTop: '1rem' }}>
                      <button className="toggle-abstract-btn" onClick={() => toggleExpand(uniqueId)} style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                        {expanded[uniqueId] ? 'Hide document ↑' : 'Show full document ↓'}
                      </button>

                      <div className="action-row" style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                         {item.pdf_url && (
                            <button className="btn-solid-glow" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.3rem'}} onClick={() => triggerPdfAnalysis(item.pdf_url)}>
                              <ScanSearch size={14} /> AI Analyze
                            </button>
                         )}
                        <a href={item.link} target="_blank" rel="noopener noreferrer" className="read-more-btn" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>
                          Read official 
                          <ExternalLink size={12} />
                        </a>
                      </div>
                    </div>
                 </article>
              )})}
              
              {loadingGuide && guidePage > 1 && (
                 <div className="research-skeleton glass-card">
                     <div className="skeleton-line short" />
                     <div className="skeleton-line long" />
                 </div>
              )}
              
              {!loadingGuide && filteredGuidelines.length > 0 && (
                <button className="btn-animated-pulse" onClick={handleNextGuidelines} style={{ marginTop: '1rem', width: '100%', fontSize: '0.9rem', padding: '0.8rem' }}>
                  Load Next 5 Guidelines <ChevronRight size={14} />
                </button>
              )}
            </div>
          </section>
        )}

      </div>
    </div>
  );
}
