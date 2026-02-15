import { useState } from 'react'

const styles = {
  container: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: '#000000',
    color: '#c0c0c0',
    fontFamily: "'Courier New', Courier, monospace",
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundImage: 'radial-gradient(circle at center, #95561c 0%, #635145 100%)',
    overflow: 'hidden',
  },
  heading: {
    fontSize: '2.5rem',
    textTransform: 'uppercase',
    letterSpacing: '0.15em',
    marginBottom: '1.5rem',
    textShadow: '0px 0px 8px rgba(255, 255, 255, 0.2)',
    borderBottom: '1px solid #333',
    paddingBottom: '10px',
    textAlign: 'center',
  },
  fileInput: {
    marginBottom: '15px',
    padding: '10px',
    backgroundColor: '#111',
    color: '#aaa',
    border: '1px solid #333',
  },
  image: {
    marginTop: '15px',
    marginBottom: '20px',
    border: '1px solid #222',
    boxShadow: '0 20px 50px rgba(0,0,0,0.9)',
    filter: 'grayscale(100%) contrast(120%) brightness(90%)',
    maxHeight: '40vh',
    maxWidth: '90%',
    objectFit: 'contain',
  },
  button: {
    padding: '10px 25px',
    fontSize: '1rem',
    backgroundColor: '#1a1a1a',
    color: '#ddd',
    border: '1px solid #444',
    cursor: 'pointer',
    textTransform: 'uppercase',
    letterSpacing: '2px',
    transition: 'background-color 0.3s',
  }
}

function App() {
  const [image, setImage] = useState(null)
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

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
    <div style={styles.container}>
      <h1 style={styles.heading}>Smoke and Mirrors</h1>
      
      <img style={styles.image} id="output" width="200" src={image} />
      <input style={styles.fileInput} type="file" accept="image/*" id="file_input" onInput={(event) => 
        { const selectedFile = event.target.files[0]
          setImage(URL.createObjectURL(selectedFile))
          setFile(selectedFile)
          setResult(null)
          setError(null)
        }} />

      <button style={styles.button} onClick = {handleCheck}> {loading ? "Analyzing..." : "Check image"} </button>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {result && <pre style={{ color: '#aaa' }}>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}

export default App
