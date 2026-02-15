function ResultsPanel({
  result,
  error,
  verdict,
  spreadLoading,
  onInvestigate,
  spreadError,
}) {
  if (!result && !error) return null

  const metadata = result?.analysis?.metadata || {}
  const badgeClass = verdict === 'real'
    ? 'verdict-badge verdict-real'
    : verdict === 'ai'
      ? 'verdict-badge verdict-ai'
      : verdict === 'edited'
        ? 'verdict-badge verdict-edited'
        : 'verdict-badge verdict-unknown'

  const verdictText = verdict === 'real'
    ? 'REAL'
    : verdict === 'ai'
      ? 'AI-GENERATED'
      : verdict === 'edited'
        ? 'EDITED / MANIPULATED'
        : 'INCONCLUSIVE'

  const classifierSubtype = result?.analysis?.classifier_subtype || 'unknown'
  const canInvestigate = verdict === 'ai' || verdict === 'edited'
  const metadataSignals = Array.isArray(metadata?.metadata_signals)
    ? metadata.metadata_signals
    : []

  return (
    <section className="results-panel">
      {error && <p className="error-message">{error}</p>}

      {result && (
        <>
          <div className="verdict-row">
            <span className={badgeClass}>{verdictText}</span>
            <span className="confidence-text">
              Confidence: {Math.round((result?.analysis?.confidence || 0) * 100)}%
            </span>
          </div>

          <div className="result-grid">
            <p><strong>File:</strong> {result.filename}</p>
            <p><strong>Classifier:</strong> {result?.analysis?.label || 'unknown'}</p>
            <p><strong>Subtype:</strong> {classifierSubtype}</p>
            <p><strong>Metadata signal:</strong> {metadata?.likely_edited || 'Unknown'}</p>
            <p><strong>Metadata confidence:</strong> {metadata?.metadata_confidence || 'low'}</p>
            <p><strong>Metadata reason:</strong> {metadata?.metadata_reason || 'No strong metadata signal found.'}</p>
            <p><strong>Metadata tags:</strong> {metadataSignals.length ? metadataSignals.join(', ') : 'none'}</p>
            <p><strong>Software tag:</strong> {metadata?.software || 'n/a'}</p>
          </div>

          {canInvestigate && (
            <button
              className="investigate-button"
              onClick={onInvestigate}
              disabled={spreadLoading}
            >
              {spreadLoading ? 'Building spread graph...' : 'Investigate Spread'}
            </button>
          )}

          {spreadError && <p className="error-message">{spreadError}</p>}
        </>
      )}
    </section>
  )
}

export default ResultsPanel
