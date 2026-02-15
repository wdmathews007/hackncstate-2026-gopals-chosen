function BreadIcon() {
  return (
    <svg className="bread-icon-svg" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <path
        className="bread-crust"
        d="M9 5c-3.9 0-7 3.1-7 7v11c0 2.8 2.2 5 5 5h18c2.8 0 5-2.2 5-5V12c0-3.9-3.1-7-7-7-1.8 0-3.4.7-4.7 1.8L16 9 13.7 6.8A7 7 0 0 0 9 5z"
      />
      <path
        className="bread-crumb"
        d="M7 13h18v10a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V13z"
      />
      <circle className="bread-dot" cx="12" cy="18" r="1.3" />
      <circle className="bread-dot" cx="17" cy="16.8" r="1.15" />
      <circle className="bread-dot" cx="20.5" cy="20.2" r="1" />
    </svg>
  )
}

function UploadForm({ image, loading, onFileSelect, onCheck, canCheck, fileName }) {
  const hasFile = Boolean(fileName)

  function handleInput(event) {
    const selectedFile = event.target.files[0]
    if (selectedFile) {
      onFileSelect(selectedFile)
    }
  }
  return (
    <section className="upload-zone">
      {image && (
        <img className="preview-image" width="200" src={image} alt="Preview" />
      )}

      <label className={`file-picker ${hasFile ? 'file-picker-selected' : ''}`} htmlFor="image-upload-input">
        <span className="bread-icon"><BreadIcon /></span>
        <span className="file-picker-copy">
          <span className="file-picker-title">{fileName || 'Click to upload image evidence'}</span>
          <span className="file-picker-subtitle">{fileName ? 'Tap to replace file' : 'Step 1 of 2 - JPG, PNG, WEBP, GIF'}</span>
        </span>
        <span className="file-picker-cta">{fileName ? 'Replace' : 'Browse'}</span>
      </label>

      <input
        id="image-upload-input"
        className="file-input-hidden"
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
    </section>
  )
}
export default UploadForm
