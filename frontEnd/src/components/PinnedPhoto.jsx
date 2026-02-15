import { useEffect, useState } from 'react'

const PLATFORM_ICONS = {
  reddit: "R",
  twitter: "X",
  facebook: "f",
  instagram: "IG",
  tiktok: "TT",
  news: "N",
  "4chan": "4",
  imgur: "im",
  upload: "UP",
}

function PinnedPhoto({
  node,
  isSource,
  isUploaded,
  uploadedImage,
  style,
  animDelay,
  onSelect,
  isActive,
  isDimmed,
}) {
  const [visible, setVisible] = useState(false)
  const [thumbnailFailed, setThumbnailFailed] = useState(false)
  const [faviconFailed, setFaviconFailed] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), animDelay || 0)
    return () => clearTimeout(timer)
  }, [animDelay])

  useEffect(() => {
    setThumbnailFailed(false)
    setFaviconFailed(false)
  }, [node?.url])

  const icon = PLATFORM_ICONS[node.platform] || "?"

  let nodeHost = null
  let thumbnailUrl = null
  let faviconUrl = null
  if (node?.url) {
    try {
      const parsed = new URL(node.url)
      nodeHost = parsed.hostname.replace(/^www\./, '')
      thumbnailUrl = `https://s.wordpress.com/mshots/v1/${encodeURIComponent(node.url)}?w=600`
      faviconUrl = `https://www.google.com/s2/favicons?domain=${encodeURIComponent(nodeHost)}&sz=128`
    } catch {
      nodeHost = null
      thumbnailUrl = null
      faviconUrl = null
    }
  }

  const classes = [
    "pinned-photo",
    isSource ? "pinned-source" : "",
    isUploaded ? "pinned-uploaded" : "",
    onSelect ? "pinned-selectable" : "",
    isActive ? "pinned-active" : "",
    isDimmed ? "pinned-dim" : "",
    visible ? "pinned-visible" : "",
  ].filter(Boolean).join(" ")

  const interactiveProps = onSelect
    ? {
      role: 'button',
      tabIndex: 0,
      onClick: () => onSelect(node),
      onKeyDown: (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onSelect(node)
        }
      },
      'aria-label': `View details for ${node.label}`,
    }
    : {}

  return (
    <div className={classes} style={style} {...interactiveProps}>
      <div className="pin" />
      <div className="polaroid">
        {isUploaded && uploadedImage ? (
          <img className="polaroid-image" src={uploadedImage} alt="Uploaded" />
        ) : thumbnailUrl && !thumbnailFailed ? (
          <div className="polaroid-placeholder node-preview node-preview-screenshot">
            <img
              className="node-thumbnail"
              src={thumbnailUrl}
              alt=""
              aria-hidden="true"
              loading="lazy"
              referrerPolicy="no-referrer"
              onError={() => setThumbnailFailed(true)}
            />
            <span className="node-preview-domain">{nodeHost}</span>
          </div>
        ) : faviconUrl && !faviconFailed ? (
          <div className="polaroid-placeholder node-preview node-preview-favicon">
            <img
              className="node-favicon"
              src={faviconUrl}
              alt=""
              aria-hidden="true"
              onError={() => setFaviconFailed(true)}
            />
            <span className="node-preview-domain">{nodeHost}</span>
          </div>
        ) : (
          <div className="polaroid-placeholder">
            <span className="platform-icon">{icon}</span>
          </div>
        )}
        <div className="polaroid-label">
          <span className="polaroid-name">{node.label}</span>
          <span className="polaroid-date">{node.date || 'Unknown time'}</span>
        </div>
      </div>
      {isSource && <div className="source-stamp">SOURCE</div>}
    </div>
  )
}

export default PinnedPhoto
