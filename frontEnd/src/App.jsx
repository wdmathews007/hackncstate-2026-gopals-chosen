import { useState } from 'react'
import './styles/app.css'
import Header from './components/Header'
import UploadForm from './components/UploadForm'
import ResultsPanel from './components/ResultsPanel'
function App() {
  const [image, setImage] = useState(null)
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  function handleFileSelect(selectedFile) {
    console.log('App: Received file ->', selectedFile?.name)
    setImage(URL.createObjectURL(selectedFile))
    setFile(selectedFile)
    setResult(null)
    setError(null)
  }
  async function handleCheck() {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const formData = new FormData()
      formData.append("file", file)
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      })
      if (!response.ok) {
        setError("Upload failed. Is the backend running?")
        return
      }
      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  return (
    <div className="container">
      <Header />
      <UploadForm
        image={image}
        loading={loading}
        onFileSelect={handleFileSelect}
        onCheck={handleCheck}
      />
      <ResultsPanel result={result} error={error} />
    </div>
  )
}
export default App

