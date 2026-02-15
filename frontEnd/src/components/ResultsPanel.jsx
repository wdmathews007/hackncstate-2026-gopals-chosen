function ResultsPanel({ result, error }) {
  if (!result && !error) return null
  return (
    <div>
      {error && <p className="error-message">{error}</p>}
      {result && (
        <pre className="result-output">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  )
}
export default ResultsPanel
