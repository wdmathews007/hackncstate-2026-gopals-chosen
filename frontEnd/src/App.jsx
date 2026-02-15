import { useState } from 'react'
import './styles/app.css'
import Header from './components/Header'
import UploadForm from './components/UploadForm'
import ResultsPanel from './components/ResultsPanel'
import CorkBoard from './components/CorkBoard'
import MOCK_SPREAD_MEDIUM from './data/mockSpread'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const FORCE_LOCAL_SPREAD_MOCK = import.meta.env.VITE_FORCE_LOCAL_SPREAD_MOCK === 'true'
const USE_SPREAD_FALLBACK = import.meta.env.VITE_USE_SPREAD_FALLBACK !== 'false'

function deriveVerdict(uploadResult) {
  const classifierLabel = String(uploadResult?.analysis?.label || '').toLowerCase()
  const metadataLabel = String(uploadResult?.analysis?.metadata?.likely_edited || '').toLowerCase()

  if (metadataLabel.includes('real')) return 'real'
  if (metadataLabel.includes('edited') || metadataLabel.includes('fake')) return 'fake'
  if (classifierLabel.includes('real')) return 'real'
  if (classifierLabel.includes('fake') || classifierLabel.includes('ai') || classifierLabel.includes('edit')) {
    return 'fake'
  }

  return 'unknown'
}

function App() {
  const [phase, setPhase] = useState('upload')
  const [image, setImage] = useState(null)
  const [file, setFile] = useState(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [spreadLoading, setSpreadLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [spreadData, setSpreadData] = useState(null)
  const [error, setError] = useState(null)
  const [spreadError, setSpreadError] = useState(null)

  function clearImagePreview() {
    setImage((prevImage) => {
      if (prevImage) URL.revokeObjectURL(prevImage)
      return null
    })
  }

  function resetToUpload() {
    clearImagePreview()
    setPhase('upload')
    setFile(null)
    setResult(null)
    setSpreadData(null)
    setError(null)
    setSpreadError(null)
    setUploadLoading(false)
    setSpreadLoading(false)
  }

  function handleFileSelect(selectedFile) {
    const nextImage = URL.createObjectURL(selectedFile)

    setImage((prevImage) => {
      if (prevImage) URL.revokeObjectURL(prevImage)
      return nextImage
    })

    setFile(selectedFile)
    setPhase('upload')
    setResult(null)
    setSpreadData(null)
    setError(null)
    setSpreadError(null)
  }

  async function handleCheck() {
    if (!file) return

    setUploadLoading(true)
    setError(null)
    setSpreadError(null)
    setResult(null)
    setSpreadData(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const message = await response.text()
        setError(message || 'Upload failed. Is the backend running?')
        return
      }

      const data = await response.json()
      setResult(data)
      setPhase('results')
    } catch (err) {
      setError(err.message || 'Upload request failed')
    } finally {
      setUploadLoading(false)
    }
  }

  async function handleInvestigate() {
    if (!file) return

    setSpreadLoading(true)
    setSpreadError(null)

    if (FORCE_LOCAL_SPREAD_MOCK) {
      setSpreadData(MOCK_SPREAD_MEDIUM)
      setPhase('investigate')
      setSpreadLoading(false)
      return
    }

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(
        `${API_BASE_URL}/spread?use_mock_fallback=${USE_SPREAD_FALLBACK ? 'true' : 'false'}`,
        {
          method: 'POST',
          body: formData,
        }
      )

      if (!response.ok) {
        throw new Error('Spread lookup failed')
      }

      const data = await response.json()
      setSpreadData(data)
      setPhase('investigate')
    } catch (err) {
      setSpreadError('Spread lookup failed. Using local mock graph for now.')
      setSpreadData(MOCK_SPREAD_MEDIUM)
      setPhase('investigate')
    } finally {
      setSpreadLoading(false)
    }
  }

  const verdict = deriveVerdict(result)

  if (phase === 'investigate' && spreadData) {
    return (
      <div className="container corkboard-container">
        <Header />
        <CorkBoard
          spreadData={spreadData}
          uploadedImage={image}
          onBack={resetToUpload}
        />
      </div>
    )
  }

  return (
    <div className="container">
      <Header />
      <div className="app-card">
        <UploadForm
          image={image}
          loading={uploadLoading}
          canCheck={Boolean(file)}
          onFileSelect={handleFileSelect}
          onCheck={handleCheck}
        />

        <ResultsPanel
          result={result}
          error={error}
          verdict={verdict}
          spreadLoading={spreadLoading}
          spreadError={spreadError}
          onInvestigate={handleInvestigate}
        />

        {phase === 'results' && verdict === 'real' && (
          <p className="real-note">No spread investigation needed for likely real images.</p>
        )}

        {phase === 'results' && verdict === 'unknown' && (
          <p className="real-note">Verdict is inconclusive. Re-run after model updates.</p>
        )}
      </div>
    </div>
  )
}

export default App
