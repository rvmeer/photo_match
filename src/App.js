import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

function App() {
  const [uploadedPhoto, setUploadedPhoto] = useState(null);
  const [uploadedFilename, setUploadedFilename] = useState('');
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

  const loadExistingPhoto = useCallback(async () => {
    try {
      // Voeg timestamp toe om browser cache te omzeilen
      const timestamp = new Date().getTime();
      const response = await fetch(`/api/photo?t=${timestamp}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        setUploadedPhoto(url);
      }
    } catch (error) {
      console.log('Geen bestaande foto gevonden');
    }
  }, []);

  // Laad de bestaande foto bij opstarten
  useEffect(() => {
    loadExistingPhoto();
  }, [loadExistingPhoto]);

  // Stel de achtergrond in (altijd senf_original.png uit public folder)
  useEffect(() => {
    document.body.style.backgroundImage = `url('/senf_original.png')`;
  }, []);

  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) {
      return;
    }

    setUploading(true);
    setMessage('Foto uploaden en vergelijken...');

    // Upload direct
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();

        // Toon het resultaat van de vergelijking
        setMessage(data.result);
        setUploadedFilename(data.filename);

        // Herlaad de geüploade foto
        setTimeout(loadExistingPhoto, 500);
      } else {
        const error = await response.json();
        setMessage(`Fout: ${error.detail}`);
      }
    } catch (error) {
      setMessage(`Upload fout: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="App">
      <div className="container">
        <div className="header-with-admin">
          <h1>Foto Upload</h1>
          <a href="/admin" className="admin-link">⚙️ Admin</a>
        </div>

        <div className="upload-section">
          <input
            type="file"
            id="file-input"
            accept="image/*"
            capture="environment"
            onChange={handleFileSelect}
            className="file-input"
            disabled={uploading}
          />
          <label htmlFor="file-input" className={`file-label ${uploading ? 'disabled' : ''}`}>
            📷 {uploading ? 'Bezig met uploaden...' : 'Kies een foto'}
          </label>

          {message && (
            <div className={`message ${message.includes('Gefeliciteerd') ? 'success' : message.includes('Helaas') ? 'error' : 'info'}`}>
              {message}
            </div>
          )}
        </div>

        {uploadedPhoto && (
          <div className="uploaded-section">
            <h3>Geüploade Foto {uploadedFilename && `(${uploadedFilename})`}:</h3>
            <img src={uploadedPhoto} alt="Uploaded" className="uploaded-image" />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
