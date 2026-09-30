import { useState } from 'react'

import { api } from '../services/api'

export default function MultimodalTab() {

  const [mode, setMode] =
    useState('text')

  const [text, setText] =
    useState('')

  const [file, setFile] =
    useState(null)

  const [output, setOutput] =
    useState(null)

  const [error, setError] =
    useState('')

  const [busy, setBusy] =
    useState(false)

  const runExtraction = async () => {

    setBusy(true)
    setError('')

    try {

      const data =
        mode === 'text'
          ? await api.extractText(text)
          : await api.extractImage(file)

      setOutput(
        data.extracted || data
      )

    } catch (err) {

      setError(
        err.message
      )

    } finally {

      setBusy(false)

    }
  }

  return (

    <div className="stack">

      <section className="card">

        <div className="page-title">

          <div>

            <div className="eyebrow">
              MULTIMODAL INPUT
            </div>

            <h1>
              Text & Image Extraction
            </h1>

            <p>
              Existing structured extraction
              capability retained for the
              later multimodal integration.
            </p>

          </div>

        </div>

        <div className="toggle">

          <button
            className={
              mode === 'text'
                ? 'active'
                : ''
            }
            onClick={() =>
              setMode('text')
            }
          >
            📝 Text
          </button>

          <button
            className={
              mode === 'image'
                ? 'active'
                : ''
            }
            onClick={() =>
              setMode('image')
            }
          >
            🖼 Image
          </button>

        </div>

        {mode === 'text' ? (

          <textarea
            className="biginput"
            rows="10"
            value={text}
            onChange={e =>
              setText(e.target.value)
            }
            placeholder="Paste unstructured text…"
          />

        ) : (

          <input
            type="file"
            accept="image/png,image/jpeg,image/jpg"
            onChange={e =>
              setFile(
                e.target.files?.[0] ||
                null
              )
            }
          />

        )}

        <button
          className="primary"
          onClick={runExtraction}
          disabled={
            busy ||
            (
              !text.trim() &&
              !file
            )
          }
        >
          {busy
            ? 'Processing…'
            : 'Run Extraction →'}
        </button>

        {error &&
          <div className="notice">
            {error}
          </div>
        }

        {output &&
          <pre className="output">
            {JSON.stringify(
              output,
              null,
              2
            )}
          </pre>
        }

      </section>

    </div>
  )
}