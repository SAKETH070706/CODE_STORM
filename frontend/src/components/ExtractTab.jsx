import React, { useState, useRef } from 'react';
import { extractText, extractImage } from '../api/extraction';

const SAMPLE_TEXTS = {
  invoice: `ACME Logistics Inc.
INVOICE #INV-2026-8941
Date: September 30, 2026
Client: Apex Technology Solutions
Items:
1. High-Density Vector Compute Server - Qty: 2 @ $3,200.00 = $6,400.00
2. Enterprise Fiber Routing Switch - Qty: 1 @ $1,850.00 = $1,850.00
3. 24/7 Managed SRE Support - Qty: 1 @ $1,200.00 = $1,200.00
Subtotal: $9,450.00
Taxes (8.5%): $803.25
Total Balance Due: $10,253.25
Payment Due: Net 30 days`,
  medical: `Clinical Consultation Note:
Patient: Sarah Jenkins (DOB: 1988-04-12)
Chief Complaint: Acute respiratory congestion and persistent nocturnal cough for 4 days.
Vitals: BP 118/76, HR 74 bpm, Temp 99.1 F, SpO2 98% on room air.
Assessment: Acute mild viral bronchitis with seasonal rhinitis. No signs of bacterial pneumonia.
Plan: Hydration, OTC Guaifenesin 400mg q4h PRN, follow up in 7 days if symptoms worsen.`
};

export default function ExtractTab({ onNotify }) {
  const [mode, setMode] = useState('text');
  const [textInput, setTextInput] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [extractedData, setExtractedData] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [copied, setCopied] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        const msg = 'File exceeds 10MB upload limit. Please select a smaller document image.';
        setErrorMsg(msg);
        if (onNotify) onNotify(msg, 'error');
        return;
      }
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setExtractedData(null);
      setErrorMsg('');
      if (onNotify) onNotify(`Selected image: ${file.name}`, 'info');
    }
  };

  const handleExtractText = async () => {
    if (!textInput.trim() || isProcessing) return;
    setIsProcessing(true);
    setErrorMsg('');
    setExtractedData(null);

    try {
      const data = await extractText(textInput);
      if (data.status === 'success' && data.extracted) {
        setExtractedData(data.extracted);
        if (onNotify) onNotify('Structured data extracted and verified against Pydantic schema!', 'success');
      } else {
        const rawErr = data.error || 'Extraction failed to conform to schema.';
        const friendlyErr = rawErr === 'SERVICE_UNAVAILABLE'
          ? 'LLM service is currently unavailable. Please ensure Groq or Gemini API keys are configured in backend environment.'
          : rawErr;
        setErrorMsg(friendlyErr);
        if (onNotify) onNotify(friendlyErr, 'error');
      }
    } catch (err) {
      const msg = err.message === 'SERVICE_UNAVAILABLE'
        ? 'LLM service is currently unavailable. Please ensure Groq or Gemini API keys are configured in backend environment.'
        : (err.message || 'Extraction failed.');
      setErrorMsg(msg);
      if (onNotify) onNotify(msg, 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleExtractImage = async () => {
    if (!selectedFile || isProcessing) return;
    setIsProcessing(true);
    setErrorMsg('');
    setExtractedData(null);

    try {
      const data = await extractImage(selectedFile);
      if (data.status === 'success' && data.extracted) {
        setExtractedData(data.extracted);
        if (onNotify) onNotify('Multimodal vision extraction succeeded!', 'success');
      } else {
        const rawErr = data.error || 'Multimodal extraction failed.';
        const friendlyErr = rawErr === 'SERVICE_UNAVAILABLE'
          ? 'Vision LLM service is currently unavailable. Please ensure Gemini API key is configured for multimodal extraction.'
          : rawErr;
        setErrorMsg(friendlyErr);
        if (onNotify) onNotify(friendlyErr, 'error');
      }
    } catch (err) {
      const msg = err.message === 'SERVICE_UNAVAILABLE'
        ? 'Vision LLM service is currently unavailable. Please ensure Gemini API key is configured for multimodal extraction.'
        : (err.message || 'Image extraction failed.');
      setErrorMsg(msg);
      if (onNotify) onNotify(msg, 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  const copyToClipboard = () => {
    if (!extractedData) return;
    navigator.clipboard.writeText(JSON.stringify(extractedData, null, 2));
    setCopied(true);
    if (onNotify) onNotify('Extracted JSON copied to clipboard!', 'success');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClearImage = () => {
    setSelectedFile(null);
    setPreviewUrl('');
    setExtractedData(null);
    setErrorMsg('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getFieldCount = (data) => {
    if (!data || typeof data !== 'object') return 0;
    return Object.keys(data).length;
  };

  return (
    <div className="glass-card">
      <div className="card-header">
        <div className="badge-pill online" style={{ marginBottom: '0.4rem' }}>
          Pydantic v2 Schema Enforcement Active
        </div>
        <h2 className="card-title">📷 Multimodal Structured Extraction Engine</h2>
        <p className="card-subtitle">
          Transform unstructured text and raw document scans into strictly typed, schema-validated JSON with 1-attempt error-correction feedback.
        </p>
      </div>

      {/* Visual Pipeline Progression Strip */}
      <div className="pipeline-strip" role="region" aria-label="Extraction processing steps">
        <div className="pipeline-step">
          <span className="step-num">1</span>
          <span className="step-text">Input Payload</span>
        </div>
        <div className="pipeline-arrow">&rarr;</div>
        <div className="pipeline-step">
          <span className="step-num">2</span>
          <span className="step-text">Vision / LLM Parsing</span>
        </div>
        <div className="pipeline-arrow">&rarr;</div>
        <div className="pipeline-step">
          <span className="step-num">3</span>
          <span className="step-text">Pydantic Schema Check</span>
        </div>
        <div className="pipeline-arrow">&rarr;</div>
        <div className="pipeline-step">
          <span className="step-num">4</span>
          <span className="step-text">Conforming JSON</span>
        </div>
      </div>

      <div className="mode-toggle" role="group" aria-label="Extraction Mode">
        <button
          type="button"
          className={`toggle-btn ${mode === 'text' ? 'active' : ''}`}
          onClick={() => { setMode('text'); setErrorMsg(''); }}
        >
          📝 Text Mode
        </button>
        <button
          type="button"
          className={`toggle-btn ${mode === 'image' ? 'active' : ''}`}
          onClick={() => { setMode('image'); setErrorMsg(''); }}
        >
          🖼️ Image / Scan Mode
        </button>
      </div>

      <div className="extract-grid">
        {/* Left Column: Input Form */}
        <div className="extract-left-col">
          {mode === 'text' ? (
            <div>
              <div className="sample-chips" role="group" aria-label="Sample input prompts">
                <span className="sample-label">Try sample:</span>
                <button
                  type="button"
                  className="chip-btn"
                  onClick={() => setTextInput(SAMPLE_TEXTS.invoice)}
                >
                  📄 Commercial Invoice
                </button>
                <button
                  type="button"
                  className="chip-btn"
                  onClick={() => setTextInput(SAMPLE_TEXTS.medical)}
                >
                  🩺 Clinical Consultation
                </button>
              </div>

              <textarea
                rows={11}
                className="chat-input extract-textarea"
                placeholder="Paste unorganized text, resume, invoice details, or patient notes here..."
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                aria-label="Raw text to extract data from"
              />

              <div style={{ marginTop: '1rem' }}>
                <button
                  type="button"
                  className="primary-btn"
                  onClick={handleExtractText}
                  disabled={isProcessing || !textInput.trim()}
                >
                  {isProcessing ? '⚡ Enforcing Pydantic Schema...' : 'Run Extraction ➜'}
                </button>
              </div>
            </div>
          ) : (
            <div>
              <div
                className="dropzone"
                tabIndex="0"
                role="button"
                aria-label="Click or press enter to upload document image"
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/jpg,image/webp"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
                <div className="dropzone-icon" aria-hidden="true">📤</div>
                <div className="dropzone-heading">Click to browse or drop document image</div>
                <div className="dropzone-sub">
                  Supports PNG, JPG, WEBP (Invoices, Receipts, Prescription Strips, ID Cards)
                </div>
              </div>

              {previewUrl && (
                <div className="image-preview-box">
                  <img
                    src={previewUrl}
                    alt={`Preview of document upload ${selectedFile?.name || ''}`}
                    className="preview-img"
                    loading="lazy"
                  />
                  <div className="preview-actions">
                    <button
                      type="button"
                      className="primary-btn"
                      onClick={handleExtractImage}
                      disabled={isProcessing}
                    >
                      {isProcessing ? '⚡ Processing Vision & Schema...' : 'Extract Data from Image ➜'}
                    </button>
                    <button
                      type="button"
                      className="secondary-btn"
                      onClick={handleClearImage}
                      disabled={isProcessing}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Structured JSON Output */}
        <div className="extract-right-col">
          <div className="flex-between" style={{ marginBottom: '0.75rem' }}>
            <h4 style={{ color: '#cbd5e1' }}>Validated Pydantic JSON:</h4>
            {extractedData && (
              <button
                type="button"
                className="secondary-btn btn-sm"
                onClick={copyToClipboard}
                aria-label="Copy extracted JSON"
              >
                {copied ? '✓ Copied' : '📋 Copy JSON'}
              </button>
            )}
          </div>

          {errorMsg && (
            <div className="error-banner" role="alert" style={{ marginBottom: '1rem' }}>
              ⚠️ {errorMsg}
            </div>
          )}

          {extractedData ? (
            <div className="json-container">
              <div className="schema-badge-strip">
                <div className="schema-badge">
                  <span className="dot online" aria-hidden="true"></span>
                  Pydantic v2 Validated
                </div>
                <div className="schema-metric-pill">
                  {getFieldCount(extractedData)} Fields Extracted
                </div>
                <div className="schema-metric-pill">
                  Type Safety: 100%
                </div>
              </div>
              <pre className="json-display" tabIndex="0" aria-label="Extracted JSON data">
                {JSON.stringify(extractedData, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="empty-state-box">
              {isProcessing ? (
                <div>
                  <div className="spinner-dots" aria-hidden="true" style={{ marginBottom: '0.75rem' }}></div>
                  <p>Running LLM multimodal vision extraction & Pydantic validation...</p>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem', opacity: 0.6 }}>📐</div>
                  <p style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.25rem' }}>
                    Awaiting Input Document
                  </p>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    Paste unstructured text or upload an invoice/receipt scan on the left to generate verified JSON.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
