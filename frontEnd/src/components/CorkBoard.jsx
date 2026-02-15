import { useRef, useState, useCallback, useEffect, useMemo } from 'react'
import PinnedPhoto from './PinnedPhoto'

/**
 * CorkBoard – the investigation board view.
 *
 * Props:
 *   spreadData    – { source, nodes, edges, summary } (the contract from mockSpread.js)
 *   uploadedImage – data URL or blob URL of the user's uploaded image
 *   onBack        – callback to return to upload view
 */

// ── Layout ──────────────────────────────────────────────────────────────────
// Source node at center.  Other nodes arranged in concentric rings based on
// graph distance from source.  The uploaded image gets its own position
// separate from the source.

const BOARD_W = 2000
const BOARD_H = 1600
const CENTER_X = BOARD_W / 2
const CENTER_Y = BOARD_H / 2
const RING_SPACING = 260
const NODE_W = 160
const NODE_H = 200

function buildLayout(spreadData) {
  if (!spreadData) return { positions: {}, allNodes: [], allNodeMap: {}, visibleEdges: [] }

  const { source, nodes, edges } = spreadData
  const nodeById = Object.fromEntries(nodes.map((node) => [node.id, node]))

  // Build adjacency list (directed, from source outward)
  const children = {}
  for (const e of edges) {
    if (!e?.from || !e?.to) continue
    if (!children[e.from]) children[e.from] = []
    children[e.from].push(e.to)
  }

  // BFS from source to keep only nodes reachable from source
  const depth = { [source.id]: 0 }
  const reachableIds = new Set([source.id])
  const queue = [source.id]
  while (queue.length > 0) {
    const cur = queue.shift()
    for (const child of children[cur] || []) {
      if (!nodeById[child]) continue
      if (depth[child] === undefined) {
        reachableIds.add(child)
        depth[child] = depth[cur] + 1
        queue.push(child)
      }
    }
  }

  const visibleNodes = nodes.filter((n) => reachableIds.has(n.id))
  const visibleEdges = edges.filter((e) => reachableIds.has(e.from) && reachableIds.has(e.to))

  // Group nodes by depth ring
  const rings = {}
  const allNodeMap = { [source.id]: source }
  for (const n of visibleNodes) {
    allNodeMap[n.id] = n
    const d = depth[n.id]
    if (!rings[d]) rings[d] = []
    rings[d].push(n.id)
  }

  // Position: source at center, each ring gets evenly spaced angles
  const positions = {}

  // Source at center
  positions[source.id] = {
    x: CENTER_X - NODE_W / 2,
    y: CENTER_Y - NODE_H / 2,
    cx: CENTER_X,
    cy: CENTER_Y,
  }

  // Uploaded image placed above-left of source
  positions["__uploaded__"] = {
    x: CENTER_X - NODE_W / 2 - 300,
    y: CENTER_Y - NODE_H / 2 - 280,
    cx: CENTER_X - 300,
    cy: CENTER_Y - 280,
  }

  const ringKeys = Object.keys(rings).map(Number).sort((a, b) => a - b)
  for (const ringDepth of ringKeys) {
    const ids = rings[ringDepth]
    const radius = (ringDepth + 1) * RING_SPACING
    const angleStep = (2 * Math.PI) / ids.length
    // Offset so nodes don't line up on the same radial for each ring
    const angleOffset = ringDepth * 0.4

    for (let i = 0; i < ids.length; i++) {
      const angle = angleOffset + i * angleStep - Math.PI / 2
      const cx = CENTER_X + radius * Math.cos(angle)
      const cy = CENTER_Y + radius * Math.sin(angle)
      positions[ids[i]] = {
        x: cx - NODE_W / 2,
        y: cy - NODE_H / 2,
        cx,
        cy,
      }
    }
  }

  // Build full node list (source + reachable nodes)
  const allNodes = [source, ...visibleNodes]

  return { positions, allNodes, allNodeMap, visibleEdges }
}

// ── Yarn path (slightly wavy bezier) ────────────────────────────────────────

function yarnPath(x1, y1, x2, y2, idx) {
  // Add a slight curve offset so lines aren't perfectly straight
  const mx = (x1 + x2) / 2
  const my = (y1 + y2) / 2
  const dx = x2 - x1
  const dy = y2 - y1
  const len = Math.sqrt(dx * dx + dy * dy)
  // Perpendicular offset, alternating direction, scaled to line length
  const offsetMag = Math.min(len * 0.1, 40) * (idx % 2 === 0 ? 1 : -1)
  const nx = -dy / (len || 1)
  const ny = dx / (len || 1)
  const cpx = mx + nx * offsetMag
  const cpy = my + ny * offsetMag
  return `M ${x1} ${y1} Q ${cpx} ${cpy} ${x2} ${y2}`
}

// ── Pan / Zoom ──────────────────────────────────────────────────────────────

function usePanZoom() {
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 0.55 })
  const isPanning = useRef(false)
  const lastPos = useRef({ x: 0, y: 0 })

  const onMouseDown = useCallback((e) => {
    // Only pan on middle-click or left-click on the board background
    if (e.target.closest('.pinned-photo, .back-button, .node-drawer')) return
    isPanning.current = true
    lastPos.current = { x: e.clientX, y: e.clientY }
  }, [])

  const onMouseMove = useCallback((e) => {
    if (!isPanning.current) return
    const dx = e.clientX - lastPos.current.x
    const dy = e.clientY - lastPos.current.y
    lastPos.current = { x: e.clientX, y: e.clientY }
    setTransform(t => ({ ...t, x: t.x + dx, y: t.y + dy }))
  }, [])

  const onMouseUp = useCallback(() => {
    isPanning.current = false
  }, [])

  const onWheel = useCallback((e) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.92 : 1.08
    setTransform(t => ({
      ...t,
      scale: Math.min(2, Math.max(0.2, t.scale * delta)),
    }))
  }, [])

  return { transform, onMouseDown, onMouseMove, onMouseUp, onWheel }
}

// ── Component ───────────────────────────────────────────────────────────────

function CorkBoard({ spreadData, uploadedImage, onBack }) {
  const boardRef = useRef(null)
  const { transform, onMouseDown, onMouseMove, onMouseUp, onWheel } = usePanZoom()
  const [selectedNodeId, setSelectedNodeId] = useState(null)

  const { positions, allNodes, allNodeMap, visibleEdges } = useMemo(
    () => buildLayout(spreadData),
    [spreadData]
  )

  // Attach wheel listener with passive: false so we can preventDefault
  useEffect(() => {
    const el = boardRef.current
    if (!el) return
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [onWheel])

  if (!spreadData) return null

  const { source } = spreadData
  const uploadedNode = {
    id: '__uploaded__',
    label: 'Your Upload',
    platform: 'upload',
    date: 'now',
    url: null,
  }

  const selectedNode = selectedNodeId === '__uploaded__'
    ? uploadedNode
    : allNodeMap?.[selectedNodeId] || null

  function handleSelectNode(node) {
    setSelectedNodeId(node.id)
  }

  // Build yarn edges: source → nodes, plus uploaded → source
  const allEdges = [
    { from: "__uploaded__", to: source.id },
    ...visibleEdges,
  ]

  // Animation timing: yarn appears first, then nodes fade in by depth
  const BASE_DELAY = 400 // ms before first element appears
  const YARN_DURATION = 600 // ms per yarn line animation
  const NODE_STAGGER = 300 // ms between each node appearing

  // Compute node animation delays based on BFS order
  const nodeDelays = {}
  // Uploaded image appears first
  nodeDelays["__uploaded__"] = BASE_DELAY
  // Source appears next
  nodeDelays[source.id] = BASE_DELAY + NODE_STAGGER
  // Other nodes by their order in the data
  allNodes.slice(1).forEach((n, i) => {
    nodeDelays[n.id] = BASE_DELAY + NODE_STAGGER * (i + 2)
  })

  const transformStyle = {
    transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
    transformOrigin: '0 0',
  }

  return (
    <div
      className="corkboard-viewport"
      ref={boardRef}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    >
      <button className="back-button" onClick={onBack}>
        New Investigation
      </button>

      <div className="corkboard-surface" style={transformStyle}>
        {/* SVG layer for yarn */}
        <svg
          className="yarn-layer"
          width={BOARD_W}
          height={BOARD_H}
          viewBox={`0 0 ${BOARD_W} ${BOARD_H}`}
        >
          {allEdges.map((edge, i) => {
            const from = positions[edge.from]
            const to = positions[edge.to]
            if (!from || !to) return null

            const totalLen = Math.sqrt(
              (to.cx - from.cx) ** 2 + (to.cy - from.cy) ** 2
            )

            return (
              <path
                key={`${edge.from}-${edge.to}`}
                className="yarn-line"
                d={yarnPath(from.cx, from.cy, to.cx, to.cy, i)}
                style={{
                  strokeDasharray: totalLen,
                  strokeDashoffset: totalLen,
                  animationDelay: `${BASE_DELAY + i * 200}ms`,
                  animationDuration: `${YARN_DURATION}ms`,
                }}
              />
            )
          })}
        </svg>

        {/* Uploaded image node */}
        {positions["__uploaded__"] && (
          <PinnedPhoto
            node={uploadedNode}
            isUploaded
            uploadedImage={uploadedImage}
            isActive={selectedNodeId === '__uploaded__'}
            onSelect={handleSelectNode}
            style={{
              position: 'absolute',
              left: positions["__uploaded__"].x,
              top: positions["__uploaded__"].y,
            }}
            animDelay={nodeDelays["__uploaded__"]}
          />
        )}

        {/* Source + spread nodes */}
        {allNodes.map((node) => {
          const pos = positions[node.id]
          if (!pos) return null
          return (
            <PinnedPhoto
              key={node.id}
              node={node}
              isSource={node.id === source.id}
              isActive={selectedNodeId === node.id}
              onSelect={handleSelectNode}
              style={{
                position: 'absolute',
                left: pos.x,
                top: pos.y,
              }}
              animDelay={nodeDelays[node.id]}
            />
          )
        })}

        {selectedNode && (
          <aside className="node-drawer" aria-live="polite">
            <div className="node-drawer-header">
              <h2 className="node-drawer-title">Node Details</h2>
              <button
                className="node-drawer-close"
                onClick={() => setSelectedNodeId(null)}
                aria-label="Close node details"
              >
                X
              </button>
            </div>

            <p><strong>Label:</strong> {selectedNode.label}</p>
            <p><strong>Platform:</strong> {selectedNode.platform}</p>
            <p><strong>Date:</strong> {selectedNode.date}</p>

            {selectedNode.url ? (
              <a
                className="node-drawer-link"
                href={selectedNode.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open Source
              </a>
            ) : (
              <p className="node-drawer-muted">No public URL</p>
            )}
          </aside>
        )}
      </div>
    </div>
  )
}

export default CorkBoard
