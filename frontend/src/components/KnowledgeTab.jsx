import React, { useState, useEffect, useCallback } from 'react';
import { getRagStats, reindexKnowledge, listDocuments, uploadDocument, deleteDocument } from '../api/knowledge';

export default function KnowledgeTab({ onNotify }) {
  const [stats, setStats] = useState({
    total_chunks: 0,
    dimension: 1024,
    index_name: 'code-storm',
    namespace: 'default',
    connected_to_pinecone: false,
    total_documents: 0,
    is_mock: false
  });
  const [documents, setDocuments] = useState([]);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [statusNote, setStatusNote] = useState('');
  const [uploadFile, setUploadFile] = useState(null);

  const fetchKnowledgeData = useCallback(async () => {
    try {
      const [statsData, docsData] = await Promise.all([
        getRagStats().catch(() => null),
        listDocuments().catch(() => null)
      ]);

      if (statsData) {
        setStats(statsData);
      }
      if (docsData && docsData.documents) {
        setDocuments(docsData.documents);
      }
    } catch (err) {
      console.warn('Could not fetch knowledge data:', err);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      try {
        const [statsData, docsData] = await Promise.all([
          getRagStats().catch(() => null),
          listDocuments().catch(() => null)
        ]);
        if (!ignore) {
          if (statsData) setStats(statsData);
          if (docsData && docsData.documents) setDocuments(docsData.documents);
        }
      } catch (err) {
        if (!ignore) console.warn('Knowledge init fetch failed:', err);
      }
    };
    load();
    return () => { ignore = true; };
  }, []);

  const handleReindex = async () => {
    setIsIngesting(true);
    setStatusNote('');
    try {
      const data = await reindexKnowledge();
      const msg = `Successfully indexed ${data.documents_processed} document(s) into ${data.chunks_ingested} Pinecone vector chunks!`;
      setStatusNote(`✅ ${msg}`);
      if (onNotify) onNotify(msg, 'success');
      await fetchKnowledgeData();
    } catch (err) {
      const msg = `Re-indexing failed: ${err.message}`;
      setStatusNote(`❌ ${msg}`);
      if (onNotify) onNotify(msg, 'error');
    } finally {
      setIsIngesting(false);
    }
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!uploadFile || isUploading) return;

    setIsUploading(true);
    setStatusNote('');
    try {
      const res = await uploadDocument(uploadFile);
      const msg = `Document "${res.name}" indexed into ${res.chunk_count} vector chunks!`;
      setStatusNote(`✅ ${msg}`);
      if (onNotify) onNotify(msg, 'success');
      setUploadFile(null);
      e.target.reset();
      await fetchKnowledgeData();
    } catch (err) {
      const msg = `Upload failed: ${err.message}`;
      setStatusNote(`❌ ${msg}`);
      if (onNotify) onNotify(msg, 'error');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId, docName) => {
    if (!window.confirm(`Are you sure you want to delete "${docName}"? This will delete both the database record and all vectors from Pinecone.`)) {
      return;
    }
    try {
      await deleteDocument(docId);
      const msg = `Deleted "${docName}" and purged its Pinecone vectors.`;
      setStatusNote(`🗑️ ${msg}`);
      if (onNotify) onNotify(msg, 'info');
      await fetchKnowledgeData();
    } catch (err) {
      const msg = `Delete failed: ${err.message}`;
      setStatusNote(`❌ ${msg}`);
      if (onNotify) onNotify(msg, 'error');
    }
  };

  return (
    <div className="glass-card">
      <div className="card-header flex-between">
        <div>
          <h2 className="card-title">📚 Vector Knowledge Base & Document Store</h2>
          <p className="card-subtitle">
            Aiven PostgreSQL for document metadata + Pinecone vector index for semantic retrieval with deterministic SHA-256 deduplication.
          </p>
        </div>
        <button
          type="button"
          className="secondary-btn btn-sm"
          onClick={fetchKnowledgeData}
          title="Refresh metrics and document list"
          aria-label="Refresh knowledge base"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Stats Banner */}
      <div className="stats-banner" role="region" aria-label="Knowledge metrics">
        <div className="stat-box">
          <div className="stat-num">{stats.total_chunks}</div>
          <div className="stat-label">Vector Chunks in Pinecone</div>
        </div>
        <div className="stat-box">
          <div className="stat-num" style={{ color: '#8b5cf6' }}>{stats.total_documents}</div>
          <div className="stat-label">Documents in PostgreSQL</div>
        </div>
        <div className="stat-box">
          <div className="stat-num" style={{ color: '#06b6d4' }}>{stats.dimension}</div>
          <div className="stat-label">Embedding Dimension</div>
        </div>
        <div className="stat-box">
          <div className="stat-num" style={{ color: stats.connected_to_pinecone ? '#10b981' : '#f59e0b' }}>
            {stats.connected_to_pinecone ? 'Active' : (stats.is_mock ? 'Fallback' : 'Connecting')}
          </div>
          <div className="stat-label">Pinecone Index Status</div>
        </div>
      </div>

      {/* Status Note Banner */}
      {statusNote && (
        <div
          className={`status-banner-box ${statusNote.startsWith('❌') ? 'error-banner' : 'success-banner'}`}
          role="status"
        >
          {statusNote}
        </div>
      )}

      {/* Actions Grid: Re-index + Upload */}
      <div className="knowledge-actions-grid">
        {/* Re-Index Folder Panel */}
        <div className="action-panel">
          <h3 className="panel-title">📁 Sync Knowledge Folder</h3>
          <p className="panel-desc">
            Scans <code>backend/data/knowledge/</code> and idempotently ingests all <code>.md</code> and <code>.txt</code> guidelines.
          </p>
          <div style={{ marginTop: '1.25rem' }}>
            <button
              type="button"
              className="primary-btn"
              onClick={handleReindex}
              disabled={isIngesting}
            >
              {isIngesting ? '⏳ Chunking & Embedding...' : '🔄 Re-Index Knowledge Base Now'}
            </button>
          </div>
        </div>

        {/* Upload Custom Document Panel */}
        <div className="action-panel">
          <h3 className="panel-title">📤 Upload New Document</h3>
          <p className="panel-desc">
            Directly upload guidelines, medical handbooks, or contracts to parse, chunk, embed, and index into Pinecone.
          </p>
          <form
            onSubmit={handleUploadSubmit}
            className="upload-doc-form"
            aria-label="Upload document to knowledge base"
          >
            <input
              type="file"
              accept=".txt,.md,.json,.csv"
              className="chat-input upload-file-input"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              disabled={isUploading}
              aria-label="Select file to upload"
            />
            <button
              type="submit"
              className="primary-btn"
              disabled={isUploading || !uploadFile}
            >
              {isUploading ? 'Uploading...' : 'Upload & Index'}
            </button>
          </form>
        </div>
      </div>

      {/* Indexed Documents Table */}
      <div className="documents-section" role="region" aria-label="Synchronized documents table">
        <h3 className="section-title">📄 Synchronized Knowledge Documents ({documents.length})</h3>
        {documents.length > 0 ? (
          <div className="table-responsive">
            <table className="docs-table">
              <thead>
                <tr>
                  <th scope="col">Document Name</th>
                  <th scope="col">Status</th>
                  <th scope="col">Chunks</th>
                  <th scope="col">Size</th>
                  <th scope="col">SHA-256 Hash</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <strong className="doc-name">{doc.name}</strong>
                    </td>
                    <td>
                      <span className="badge-pill online">{doc.status}</span>
                    </td>
                    <td>{doc.chunk_count} vectors</td>
                    <td>{(doc.file_size / 1024).toFixed(1)} KB</td>
                    <td>
                      <code className="doc-hash">
                        {doc.content_hash.slice(0, 10)}...
                      </code>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="danger-btn btn-xs"
                        onClick={() => handleDelete(doc.id, doc.name)}
                        title="Delete from PostgreSQL and Pinecone"
                        aria-label={`Delete document ${doc.name}`}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state-box" style={{ padding: '2.5rem' }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem', opacity: 0.5 }}>📚</div>
            <p>No documents currently indexed. Click "Re-Index Knowledge Base Now" or upload a file above.</p>
          </div>
        )}
      </div>
    </div>
  );
}
