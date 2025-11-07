import React, { useState, useEffect } from 'react';
import './Admin.css';

function Admin() {
  const [threshold, setThreshold] = useState(90);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [currentThreshold, setCurrentThreshold] = useState(null);

  useEffect(() => {
    loadCurrentThreshold();
  }, []);

  const loadCurrentThreshold = async () => {
    try {
      const response = await fetch('/api/admin/threshold');
      if (response.ok) {
        const data = await response.json();
        const percentValue = Math.round(data.threshold * 100);
        setThreshold(percentValue);
        setCurrentThreshold(percentValue);
      }
    } catch (error) {
      console.error('Failed to load threshold:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    // Convert percentage to decimal (0.0 - 1.0)
    const thresholdValue = threshold / 100;

    try {
      const response = await fetch('/api/admin/threshold', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ threshold: thresholdValue }),
      });

      if (response.ok) {
        await response.json();
        setMessage(`Threshold succesvol aangepast naar ${threshold}%`);
        setCurrentThreshold(threshold);
      } else {
        const error = await response.json();
        setMessage(`Fout: ${error.detail}`);
      }
    } catch (error) {
      setMessage(`Fout bij opslaan: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSliderChange = (e) => {
    setThreshold(parseInt(e.target.value));
  };

  return (
    <div className="Admin">
      <div className="admin-container">
        <h1>Admin Panel</h1>

        <div className="admin-card">
          <h2>Match Threshold Instelling</h2>

          {currentThreshold !== null && (
            <div className="current-threshold">
              Huidige threshold: <strong>{currentThreshold}%</strong>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="threshold-control">
              <label htmlFor="threshold-slider">
                Threshold voor puzzle match:
              </label>

              <div className="slider-container">
                <input
                  id="threshold-slider"
                  type="range"
                  min="50"
                  max="100"
                  value={threshold}
                  onChange={handleSliderChange}
                  className="threshold-slider"
                />
                <div className="threshold-value">{threshold}%</div>
              </div>

              <div className="threshold-info">
                <p><strong>Aanbevolen waarden:</strong></p>
                <ul>
                  <li><strong>90-100%:</strong> Zeer strikt - alleen bijna perfecte matches</li>
                  <li><strong>80-90%:</strong> Strikt - goede foto kwaliteit vereist</li>
                  <li><strong>70-80%:</strong> Gemiddeld - accepteert meer variatie</li>
                  <li><strong>50-70%:</strong> Soepel - accepteert lagere foto kwaliteit</li>
                </ul>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || threshold === currentThreshold}
              className="save-button"
            >
              {loading ? 'Opslaan...' : 'Threshold Opslaan'}
            </button>
          </form>

          {message && (
            <div className={`admin-message ${message.includes('succesvol') ? 'success' : 'error'}`}>
              {message}
            </div>
          )}
        </div>

        <div className="admin-actions">
          <a href="/" className="back-button">← Terug naar Upload</a>
        </div>
      </div>
    </div>
  );
}

export default Admin;
