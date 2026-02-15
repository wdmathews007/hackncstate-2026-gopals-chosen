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
    : verdict === 'fake'
      ? 'verdict-badge verdict-fake'
      : 'verdict-badge verdict-unknown'

  const verdictText = verdict === 'real'
    ? 'REAL'
    : verdict === 'fake'
      ? 'FAKE / EDITED'
      : 'INCONCLUSIVE'

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
            <p><strong>Metadata signal:</strong> {metadata?.likely_edited || 'Unknown'}</p>
            <p><strong>Software tag:</strong> {metadata?.software || 'n/a'}</p>
          </div>

          {verdict === 'fake' && (
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
