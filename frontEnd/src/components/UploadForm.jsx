function UploadForm({ image, loading, onFileSelect, onCheck }) {
  function handleInput(event) {
    const selectedFile = event.target.files[0]
    console.log('UploadForm: File selected ->', selectedFile?.name)
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
        disabled={loading}
      >
        {loading ? <span className="loading-text">Analyzing...</span> : "Check image"}
      </button>
    </>
  )
}
export default UploadForm
