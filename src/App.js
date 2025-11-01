import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploadedPhoto, setUploadedPhoto] = useState(null);
  const [uploadedFilename, setUploadedFilename] = useState('');
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

  // Laad de bestaande foto bij opstarten
  useEffect(() => {
    loadExistingPhoto();
  }, []);

  // Stel de achtergrond in (altijd senf_original.png uit public folder)
  useEffect(() => {
    document.body.style.backgroundImage = `url('/senf_original.png')`;
  }, []);

  const loadExistingPhoto = async () => {
    try {
      const response = await fetch('/api/photo');
      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        setUploadedPhoto(url);
      }
    } catch (error) {
      console.log('Geen bestaande foto gevonden');
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);

      // Maak preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setMessage('Selecteer eerst een foto');
      return;
    }

    setUploading(true);
    setMessage('');

    const formData = new FormData();
    formData.append('file', selectedFile);

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
        setSelectedFile(null);
        setPreview(null);

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
        <h1>Foto Upload</h1>

        <div className="upload-section">
          <input
            type="file"
            id="file-input"
            accept="image/*"
            capture="environment"
            onChange={handleFileSelect}
            className="file-input"
          />
          <label htmlFor="file-input" className="file-label">
            📷 Kies een foto
          </label>

          {preview && (
            <div className="preview-section">
              <h3>Preview:</h3>
              <img src={preview} alt="Preview" className="preview-image" />
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="upload-button"
              >
                {uploading ? 'Uploaden...' : 'Upload Foto'}
              </button>
            </div>
          )}

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
