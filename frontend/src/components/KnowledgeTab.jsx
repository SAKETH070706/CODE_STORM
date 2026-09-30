import React, { useState, useEffect, useCallback } from 'react';
import useRequest from './useRequest';
import {describeError,isCancelled} from '../workspaceClient';
import { getRagStats, reindexKnowledge, listDocuments, uploadDocument, deleteDocument } from '../api/knowledge';

export default function KnowledgeTab() {
  const request=useRequest();
  const [stats,setStats]=useState({}),[documents,setDocuments]=useState([]);
  const [operation,setOperation]=useState(''),[statusNote,setStatusNote]=useState(''),[error,setError]=useState('');
  const [uploadFile,setUploadFile]=useState(null),[loaded,setLoaded]=useState(false);
  const isIngesting=operation==='reindex',isUploading=operation==='upload';
  const load=useCallback(async(signal)=>{
    const results=await Promise.allSettled([request.call(signal,s=>getRagStats(s)),request.call(signal,s=>listDocuments(s))]);
    if(!request.active()||signal.aborted)return;
    const failures=[];
    if(results[0].status==='fulfilled')setStats(results[0].value);else failures.push('Metrics: '+describeError(results[0].reason));
    if(results[1].status==='fulfilled'&&Array.isArray(results[1].value?.documents)){setDocuments(results[1].value.documents);setLoaded(true);}
    else failures.push('Documents: '+(results[1].status==='rejected'?describeError(results[1].reason):'Invalid server response.'));
    setError(failures.join(' '));
  },[request]);
  const run=useCallback(async(name,fn)=>{
    const signal=request.begin();if(!signal)return;
    setOperation(name);setError('');if(name!=='refresh')setStatusNote('');
    try{if(fn)await fn(signal);await load(signal);}
    catch(e){if(!isCancelled(e)&&request.active())setError(describeError(e));}
    finally{if(request.finish(signal))setOperation('');}
  },[request,load]);
  const fetchKnowledgeData=useCallback(()=>run('refresh'),[run]);
  // Initial server synchronization uses the same guarded lifecycle as manual refresh.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(()=>{fetchKnowledgeData();},[fetchKnowledgeData]);
  const handleReindex=()=>run('reindex',async signal=>{
    const data=await request.call(signal,s=>reindexKnowledge(s));
    setStatusNote('Re-index completed: '+data.documents_processed+' document(s), '+data.chunks_ingested+' chunks.');
  });
  const handleUploadSubmit=e=>{
    e.preventDefault();if(!uploadFile)return;
    const form=e.currentTarget;
    return run('upload',async signal=>{
      const result=await request.call(signal,s=>uploadDocument(uploadFile,s));
      setStatusNote('Document "'+result.name+'" indexed successfully.');setUploadFile(null);form.reset();
    });
  };
  const handleDelete=(id,name)=>{
    if(operation||!confirm('Delete "'+name+'" and its indexed vectors?'))return;
    return run('delete',async signal=>{await request.call(signal,s=>deleteDocument(id,s));setStatusNote('Deleted "'+name+'".');});
  };

  return (
    <fieldset className="glass-card request-fields" disabled={!!operation} aria-busy={!!operation}>
      <div className="card-header flex-between">
        <div>
          <h2 className="card-title">📚 Vector Knowledge Base & Document Store</h2>
          <p className="card-subtitle">
            Aiven PostgreSQL for document metadata + Pinecone vector index for semantic retrieval with deterministic SHA-256 deduplication.
          </p>
        </div>
        <button
          className="secondary-btn btn-sm"
          onClick={fetchKnowledgeData}
          title="Refresh metrics and document list"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Stats Banner */}
      <div className="stats-banner">
        <div className="stat-box">
          <div className="stat-num">{stats.total_chunks??'Unavailable'}</div>
          <div className="stat-label">Vector Chunks in Pinecone</div>
        </div>
        <div className="stat-box">
          <div className="stat-num" style={{ color: '#8b5cf6' }}>{stats.total_documents??'Unavailable'}</div>
          <div className="stat-label">Documents in PostgreSQL</div>
        </div>
        <div className="stat-box">
          <div className="stat-num" style={{ color: '#06b6d4' }}>{stats.dimension??'Unavailable'}</div>
          <div className="stat-label">Embedding Dimension</div>
        </div>
        <div className="stat-box">
          <div className="stat-num" style={{ color: stats.connected_to_pinecone ? '#10b981' : '#f59e0b' }}>
            {stats.connected_to_pinecone ? 'Active' : (stats.is_mock ? 'Fallback' : 'Unavailable')}
          </div>
          <div className="stat-label">Pinecone Index Status</div>
        </div>
      </div>

      {operation&&<p role="status">{operation==='refresh'?'Refreshing data...':'Processing request...'}</p>}
      {error&&<p className="error-banner" role="alert">{error}</p>}
      {/* Status Note Banner */}
      {statusNote && (
        <div className={`status-banner-box ${statusNote.startsWith('❌') ? 'error-banner' : 'success-banner'}`}>
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
          <form onSubmit={handleUploadSubmit} style={{ marginTop: '1rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <input
              type="file"
              accept=".txt,.md,.json,.csv"
              className="chat-input"
              style={{ padding: '0.6rem 1rem', fontSize: '0.85rem' }}
              onChange={(e) => setUploadFile(e.target.files[0])}
              disabled={isUploading}
            />
            <button
              type="submit"
              className="primary-btn"
              style={{ whiteSpace: 'nowrap' }}
              disabled={isUploading || !uploadFile}
            >
              {isUploading ? 'Uploading...' : 'Upload & Index'}
            </button>
          </form>
        </div>
      </div>

      {/* Indexed Documents Table */}
      <div className="documents-section">
        <h3 className="section-title">📄 Synchronized Knowledge Documents ({documents.length})</h3>
        {documents.length > 0 ? (
          <div className="table-responsive">
            <table className="docs-table">
              <thead>
                <tr>
                  <th>Document Name</th>
                  <th>Status</th>
                  <th>Chunks</th>
                  <th>Size</th>
                  <th>Hash</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <strong>{doc.name}</strong>
                    </td>
                    <td>
                      <span className="badge-pill online">{doc.status}</span>
                    </td>
                    <td>{doc.chunk_count} vectors</td>
                    <td>{(doc.file_size / 1024).toFixed(1)} KB</td>
                    <td>
                      <code style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        {doc.content_hash?.slice(0, 10)||'Unavailable'}...
                      </code>
                    </td>
                    <td>
                      <button
                        className="danger-btn btn-xs"
                        onClick={() => handleDelete(doc.id, doc.name)}
                        title="Delete from PostgreSQL and Pinecone"
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
          <div className="empty-state-box" style={{ padding: '2rem' }}>
            {loaded?'No documents currently indexed. Re-index or upload a file above.':'Document list is not available yet. Use Refresh to try again.'}
          </div>
        )}
      </div>
    </fieldset>
  );
}
