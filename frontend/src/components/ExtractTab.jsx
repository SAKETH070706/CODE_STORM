import React, { useState } from 'react';
import { api } from '../services/api';

export default function ExtractTab() {

    const [mode, setMode] = useState('text');

    const [textInput, setTextInput] =
        useState('');

    const [selectedFile, setSelectedFile] =
        useState(null);

    const [previewUrl, setPreviewUrl] =
        useState('');

    const [extractedData, setExtractedData] =
        useState(null);

    const [errorMsg, setErrorMsg] =
        useState('');

    const [isProcessing, setIsProcessing] =
        useState(false);


    /* ========================================================
       FILE SELECTION
    ======================================================== */

    const handleFileChange = (e) => {

        const file = e.target.files?.[0];

        if (!file) {
            return;
        }

        setSelectedFile(file);

        setPreviewUrl(
            URL.createObjectURL(file)
        );

        setExtractedData(null);
        setErrorMsg('');
    };


    /* ========================================================
       TEXT EXTRACTION
    ======================================================== */

    const handleExtractText = async () => {

        if (
            !textInput.trim() ||
            isProcessing
        ) {
            return;
        }

        setIsProcessing(true);
        setErrorMsg('');
        setExtractedData(null);

        try {

            const data =
                await api.extractText(
                    textInput
                );

            if (
                data.status === 'success'
            ) {

                setExtractedData(
                    data.extracted
                );

            } else {

                setErrorMsg(
                    data.error ||
                    'Extraction failed to conform to schema.'
                );
            }

        } catch (err) {

            setErrorMsg(
                err.message ||
                'Connection to API failed.'
            );

        } finally {

            setIsProcessing(false);
        }
    };


    /* ========================================================
       IMAGE EXTRACTION
    ======================================================== */

    const handleExtractImage = async () => {

        if (
            !selectedFile ||
            isProcessing
        ) {
            return;
        }

        setIsProcessing(true);
        setErrorMsg('');
        setExtractedData(null);

        try {

            const data =
                await api.extractImage(
                    selectedFile
                );

            if (
                data.status === 'success'
            ) {

                setExtractedData(
                    data.extracted
                );

            } else {

                setErrorMsg(
                    data.error ||
                    'Multimodal extraction failed.'
                );
            }

        } catch (err) {

            setErrorMsg(
                err.message ||
                'Connection to API failed.'
            );

        } finally {

            setIsProcessing(false);
        }
    };


    /* ========================================================
       CLEAR IMAGE
    ======================================================== */

    const handleClearFile = () => {

        if (previewUrl) {
            URL.revokeObjectURL(
                previewUrl
            );
        }

        setSelectedFile(null);
        setPreviewUrl('');
        setExtractedData(null);
        setErrorMsg('');
    };


    /* ========================================================
       RENDER
    ======================================================== */

    return (

        <div className="glass-card">

            {/* =================================================
                HEADER
            ================================================= */}

            <div className="card-header">

                <h2 className="card-title">
                    📷 Multimodal Structured Extraction
                </h2>

                <p className="card-subtitle">
                    Extract strictly validated Pydantic
                    JSON from unstructured text or
                    uploaded images with error feedback.
                </p>

            </div>


            {/* =================================================
                MODE TOGGLE
            ================================================= */}

            <div className="mode-toggle">

                <button
                    className={
                        `toggle-btn ${
                            mode === 'text'
                                ? 'active'
                                : ''
                        }`
                    }
                    onClick={() => {

                        setMode('text');
                        setErrorMsg('');
                        setExtractedData(null);

                    }}
                >
                    📝 Text Input
                </button>


                <button
                    className={
                        `toggle-btn ${
                            mode === 'image'
                                ? 'active'
                                : ''
                        }`
                    }
                    onClick={() => {

                        setMode('image');
                        setErrorMsg('');
                        setExtractedData(null);

                    }}
                >
                    🖼️ Image / Document Upload
                </button>

            </div>


            {/* =================================================
                CONTENT GRID
            ================================================= */}

            <div className="extract-grid">

                {/* =================================================
                    LEFT SIDE
                ================================================= */}

                <div>

                    {/* =================================================
                        TEXT MODE
                    ================================================= */}

                    {mode === 'text' && (

                        <div>

                            <textarea
                                rows={10}
                                className="chat-input"
                                style={{
                                    width: '100%',
                                    resize: 'vertical'
                                }}
                                placeholder={
                                    'Paste unorganized text, resume, ' +
                                    'invoice details, or patient notes here...'
                                }
                                value={textInput}
                                onChange={(e) =>
                                    setTextInput(
                                        e.target.value
                                    )
                                }
                            />


                            <div
                                style={{
                                    marginTop: '1rem'
                                }}
                            >

                                <button
                                    className="primary-btn"
                                    onClick={
                                        handleExtractText
                                    }
                                    disabled={
                                        isProcessing ||
                                        !textInput.trim()
                                    }
                                >

                                    {isProcessing
                                        ? '⚡ Extracting with Schema...'
                                        : 'Run Extraction ➜'}

                                </button>

                            </div>

                        </div>

                    )}


                    {/* =================================================
                        IMAGE MODE
                    ================================================= */}

                    {mode === 'image' && (

                        <div>

                            <label
                                className="dropzone"
                                style={{
                                    display: 'block'
                                }}
                            >

                                <input
                                    type="file"
                                    accept={
                                        'image/png,' +
                                        'image/jpeg,' +
                                        'image/jpg'
                                    }
                                    style={{
                                        display: 'none'
                                    }}
                                    onChange={
                                        handleFileChange
                                    }
                                />


                                <div
                                    style={{
                                        fontSize: '2rem',
                                        marginBottom:
                                            '0.5rem'
                                    }}
                                >
                                    📤
                                </div>


                                <div
                                    style={{
                                        fontWeight: 600
                                    }}
                                >
                                    Click to browse or
                                    drop document image
                                </div>


                                <div
                                    style={{
                                        fontSize: '0.8rem',
                                        color: '#94a3b8',
                                        marginTop:
                                            '0.35rem'
                                    }}
                                >
                                    Supports PNG, JPG
                                    (Invoices, IDs,
                                    Prescription Strips,
                                    Forms)
                                </div>

                            </label>


                            {/* IMAGE PREVIEW */}

                            {previewUrl && (

                                <div
                                    style={{
                                        marginTop: '1rem',
                                        textAlign: 'center'
                                    }}
                                >

                                    <img
                                        src={previewUrl}
                                        alt="Preview"
                                        style={{
                                            maxHeight: '180px',
                                            maxWidth: '100%',
                                            borderRadius: '8px',
                                            border:
                                                '1px solid rgba(255,255,255,0.1)'
                                        }}
                                    />


                                    <div
                                        style={{
                                            marginTop:
                                                '0.75rem',
                                            display: 'flex',
                                            justifyContent:
                                                'center',
                                            gap: '0.75rem',
                                            flexWrap:
                                                'wrap'
                                        }}
                                    >

                                        <button
                                            className="primary-btn"
                                            onClick={
                                                handleExtractImage
                                            }
                                            disabled={
                                                isProcessing
                                            }
                                        >

                                            {isProcessing
                                                ? '⚡ Auditing Vision...'
                                                : 'Extract Data from Image ➜'}

                                        </button>


                                        <button
                                            className="toggle-btn"
                                            onClick={
                                                handleClearFile
                                            }
                                            disabled={
                                                isProcessing
                                            }
                                        >
                                            Clear
                                        </button>

                                    </div>

                                </div>

                            )}

                        </div>

                    )}

                </div>


                {/* =================================================
                    RIGHT SIDE
                ================================================= */}

                <div>

                    <h4
                        style={{
                            marginBottom:
                                '0.75rem',
                            color: '#cbd5e1'
                        }}
                    >
                        Validated Pydantic Output:
                    </h4>


                    {/* ERROR */}

                    {errorMsg && (

                        <div
                            style={{
                                padding: '1rem',
                                background:
                                    'rgba(239, 68, 68, 0.15)',
                                border:
                                    '1px solid #ef4444',
                                borderRadius: '8px',
                                color: '#fee2e2',
                                fontSize: '0.9rem',
                                marginBottom:
                                    '1rem'
                            }}
                        >
                            ⚠️ {errorMsg}
                        </div>

                    )}


                    {/* SUCCESS RESULT */}

                    {extractedData ? (

                        <pre className="json-display">
                            {JSON.stringify(
                                extractedData,
                                null,
                                2
                            )}
                        </pre>

                    ) : (

                        <div
                            style={{
                                padding: '2rem',
                                textAlign: 'center',
                                border:
                                    '1px dashed rgba(255,255,255,0.1)',
                                borderRadius: '12px',
                                color: '#64748b'
                            }}
                        >
                            Awaiting extraction.
                            <br />
                            Output will appear here
                            as formatted JSON.
                        </div>

                    )}

                </div>

            </div>

        </div>
    );
}