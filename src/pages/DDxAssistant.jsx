import React, { useState } from 'react';

const DDxAssistant = () => {
  const [formData, setFormData] = useState({
    age: '',
    sex: 'Male',
    primary_symptom: '',
    vitals: '',
    comorbidities: ''
  });
  
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [activeCitation, setActiveCitation] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/api/ddx/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          age: parseInt(formData.age) || 0,
          sex: formData.sex,
          primary_symptom: formData.primary_symptom,
          comorbidities: formData.comorbidities.split(',').map(s => s.trim()),
          vitals: formData.vitals
        })
      });
      
      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCitationClick = (citation) => {
    setActiveCitation(citation);
  };

  return (
    <div className="ddx-container">
      {/* Left Pane: The Workflow */}
      <div className="ddx-left-pane">
        <h1 className="ddx-title">Differential Diagnosis Assistant</h1>
        <p className="ddx-subtitle">Enter clinical parameters to generate an evidence-based probability table.</p>
        
        <form onSubmit={handleSubmit} className="ddx-form glass-card">
          <div className="form-row">
            <div className="form-group">
              <label>Age</label>
              <input type="number" 
                value={formData.age} onChange={e => setFormData({...formData, age: e.target.value})} 
                placeholder="e.g., 4" required 
              />
            </div>
            <div className="form-group">
              <label>Sex</label>
              <select value={formData.sex} onChange={e => setFormData({...formData, sex: e.target.value})}>
                <option>Male</option>
                <option>Female</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Primary Symptom & HPI</label>
            <textarea 
              value={formData.primary_symptom} onChange={e => setFormData({...formData, primary_symptom: e.target.value})} 
              placeholder="e.g., Shortness of breath, wheezing for 2 days" rows="3" required
            />
          </div>
          <div className="form-group">
            <label>Vitals</label>
            <input type="text" 
              value={formData.vitals} onChange={e => setFormData({...formData, vitals: e.target.value})} 
              placeholder="e.g., HR 120, O2 93% on RA" 
            />
          </div>
          <div className="form-group">
            <label>Co-morbidities (comma separated)</label>
            <input type="text" 
              value={formData.comorbidities} onChange={e => setFormData({...formData, comorbidities: e.target.value})} 
              placeholder="e.g., Atopy, prior intubation" 
            />
          </div>
          
          <button type="submit" className="ddx-btn" disabled={loading}>
            {loading ? 'Synthesizing Data...' : 'Generate DDx Table'}
          </button>
        </form>

        {results && (
          <div className="ddx-results glass-card fade-in">
            <h3>Probability Assessment (Confidence: {results.confidence_score * 100}%)</h3>
            <table className="ddx-table">
              <thead>
                <tr>
                  <th>Condition</th>
                  <th>Probability</th>
                  <th>Clinical Logic</th>
                </tr>
              </thead>
              <tbody>
                {results.results.map((item, index) => (
                  <tr key={index}>
                    <td className="font-medium">{item.condition}</td>
                    <td><span className={`badge ${item.probability.toLowerCase().includes('high') ? 'badge-high' : 'badge-med'}`}>{item.probability}</span></td>
                    <td>
                      {item.why}
                      <div className="citation-links">
                        {item.citations.map((cit, cIdx) => (
                          <button key={cIdx} className="cite-btn" onClick={() => handleCitationClick(cit)}>
                            [{index + 1}.{cIdx + 1}]
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Right Pane: Evidence Traceability */}
      <div className="ddx-right-pane">
        <h2 className="evidence-title">Evidence Traceability</h2>
        
        {!activeCitation ? (
          <div className="empty-state glass-card">
            <p>Select a citation from the DDx table to view the source context.</p>
          </div>
        ) : (
          <div className="source-card glass-card fade-in">
            <div className="source-header">
              <h4>{activeCitation.source_id}</h4>
              <span className="source-meta">{activeCitation.structural_context}</span>
            </div>
            
            <div className="source-body">
              <p className="highlighted-text">
                "... <mark>{activeCitation.exact_quote}</mark> ..."
              </p>
            </div>
            <div className="source-footer">
              <p className="feedback-text">Was this citation accurate?</p>
              <div className="vote-actions">
                  <button className="vote-btn">👍 Accurate</button>
                  <button className="vote-btn">👎 Inaccurate</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DDxAssistant;
