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
}) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), animDelay || 0)
    return () => clearTimeout(timer)
  }, [animDelay])

  const icon = PLATFORM_ICONS[node.platform] || "?"

  const classes = [
    "pinned-photo",
    isSource ? "pinned-source" : "",
    isUploaded ? "pinned-uploaded" : "",
    onSelect ? "pinned-selectable" : "",
    isActive ? "pinned-active" : "",
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
        ) : (
          <div className="polaroid-placeholder">
            <span className="platform-icon">{icon}</span>
          </div>
        )}
        <div className="polaroid-label">
          <span className="polaroid-name">{node.label}</span>
          <span className="polaroid-date">{node.date}</span>
        </div>
      </div>
      {isSource && <div className="source-stamp">SOURCE</div>}
    </div>
  )
}

export default PinnedPhoto
