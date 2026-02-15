function UploadForm({ image, loading, onFileSelect, onCheck, canCheck }) {
  function handleInput(event) {
    const selectedFile = event.target.files[0]
    if (selectedFile) {
      onFileSelect(selectedFile)
    }
  }
  return (
    <>
      {image && (
        <img className="preview-image" width="200" src={image} alt="Preview" />
      )}
      <input
        className="file-input"
        type="file"
        accept="image/*"
        onChange={handleInput}
      />
      <button
        className="check-button"
        onClick={onCheck}
        disabled={loading || !canCheck}
      >
        {loading ? <span className="loading-text">Analyzing...</span> : "Check image"}
      </button>
    </>
  )
}
export default UploadForm
