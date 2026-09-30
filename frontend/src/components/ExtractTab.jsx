import React, { useState, useEffect, useRef } from 'react';
import useRequest from './useRequest';
import {describeError,isCancelled} from '../workspaceClient';
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

export default function ExtractTab() {
  const request=useRequest(),copyTimer=useRef(null);
  const [mode, setMode] = useState('text');
  const [textInput, setTextInput] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [extractedData, setExtractedData] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(()=>()=>{if(previewUrl)URL.revokeObjectURL(previewUrl);},[previewUrl]);
  useEffect(()=>()=>clearTimeout(copyTimer.current),[]);
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        setErrorMsg('File exceeds 2 MiB upload limit.');
        return;
      }
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setExtractedData(null);
      setErrorMsg('');
    }
  };

  const handleExtractText = async () => {
    if (!textInput.trim() || isProcessing) return;
    const signal=request.begin();if(!signal)return;
    setIsProcessing(true);
    setErrorMsg('');
    setExtractedData(null);

    try {
      const data = await request.call(signal,s=>extractText(textInput,s));
      if (data.status === 'success' && data.extracted) {
        setExtractedData(data.extracted);
      } else {
        setErrorMsg(data.error || 'Extraction failed to conform to schema.');
      }
    } catch (err) {
      if(isCancelled(err))return;
      setErrorMsg(describeError(err));
    } finally {
      if(request.finish(signal))setIsProcessing(false);
    }
  };

  const handleExtractImage = async () => {
    if (!selectedFile || isProcessing) return;
    const signal=request.begin();if(!signal)return;
    setIsProcessing(true);
    setErrorMsg('');
    setExtractedData(null);

    try {
      const data = await request.call(signal,s=>extractImage(selectedFile,s));
      if (data.status === 'success' && data.extracted) {
        setExtractedData(data.extracted);
      } else {
        setErrorMsg(data.error || 'Multimodal extraction failed.');
      }
    } catch (err) {
      if(isCancelled(err))return;
      setErrorMsg(describeError(err));
    } finally {
      request.finish(signal);if(request.active())setIsProcessing(false);
    }
  };

  const copyToClipboard = async () => {
    if (!extractedData) return;
    try {await navigator.clipboard.writeText(JSON.stringify(extractedData,null,2));if(!request.active())return;setCopied(true);clearTimeout(copyTimer.current);copyTimer.current=setTimeout(()=>setCopied(false),2000);}
    catch {if(request.active())setErrorMsg('Clipboard unavailable. Select and copy the JSON below manually.');}
  };

  return (
    <fieldset className="glass-card request-fields" disabled={isProcessing} aria-busy={isProcessing}>
      <div className="card-header">
        <h2 className="card-title">📷 Multimodal Structured Extraction</h2>
        <p className="card-subtitle">
          Extract strictly validated Pydantic JSON from unstructured text or uploaded documents with 1-attempt schema feedback correction.
        </p>
      </div>

      <div className="mode-toggle">
        <button
          className={`toggle-btn ${mode === 'text' ? 'active' : ''}`}
          onClick={() => { setMode('text'); setErrorMsg(''); }}
        >
          📝 Text Mode
        </button>
        <button
          className={`toggle-btn ${mode === 'image' ? 'active' : ''}`}
          onClick={() => { setMode('image'); setErrorMsg(''); }}
        >
          🖼️ Image / Scan Mode
        </button>
      </div>

      <div className="extract-grid">
        {/* Left Column: Input Form */}
        <div>
          {mode === 'text' ? (
            <div>
              <div className="sample-chips">
                <span className="sample-label">Try sample:</span>
                <button
                  type="button"
                  className="chip-btn"
                  onClick={() => setTextInput(SAMPLE_TEXTS.invoice)}
                >
                  Invoice Text
                </button>
                <button
                  type="button"
                  className="chip-btn"
                  onClick={() => setTextInput(SAMPLE_TEXTS.medical)}
                >
                  Clinical Report
                </button>
              </div>

              <textarea
                maxLength={16000}
                rows={11}
                className="chat-input"
                style={{ width: '100%', resize: 'vertical' }}
                placeholder="Paste unorganized text, resume, invoice details, or patient notes here..."
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
              />

              <div style={{ marginTop: '1rem' }}>
                <button
                  className="primary-btn"
                  onClick={handleExtractText}
                  disabled={isProcessing || !textInput.trim()}
                >
                  {isProcessing ? '⚡ Extracting with Pydantic...' : 'Run Extraction ➜'}
                </button>
              </div>
            </div>
          ) : (
            <div>
              <label className="dropzone" style={{ display: 'block' }}>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/jpg,image/webp"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
                <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📤</div>
                <div style={{ fontWeight: 600 }}>Click to browse document images (maximum 2 MiB)</div>
                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.35rem' }}>
                  Supports PNG, JPG, WEBP (Invoices, Receipts, Prescription Strips, ID Cards)
                </div>
              </label>

              {previewUrl && (
                <div className="image-preview-box">
                  <img
                    src={previewUrl}
                    alt="Uploaded preview"
                    className="preview-img"
                  />
                  <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                    <button
                      className="primary-btn"
                      onClick={handleExtractImage}
                      disabled={isProcessing}
                    >
                      {isProcessing ? '⚡ Processing Vision & Schema...' : 'Extract Data from Image ➜'}
                    </button>
                    <button
                      className="secondary-btn"
                      onClick={() => { setSelectedFile(null); setPreviewUrl(''); }}
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
        <div>
          <div className="flex-between" style={{ marginBottom: '0.75rem' }}>
            <h4 style={{ color: '#cbd5e1' }}>Validated Pydantic JSON:</h4>
            {extractedData && (
              <button className="secondary-btn btn-sm" onClick={copyToClipboard}>
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
              <div className="schema-badge">
                <span className="dot online"></span>
                Schema Conforming (Pydantic v2)
              </div>
              <pre className="json-display">
                {JSON.stringify(extractedData, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="empty-state-box">
              {isProcessing ? (
                <div>
                  <div className="spinner-dots" style={{ marginBottom: '0.5rem' }}></div>
                  <p>Running LLM structured extraction & Pydantic validation...</p>
                </div>
              ) : (
                <p>Awaiting input. Extracted structured JSON will be displayed here.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </fieldset>
  );
}
