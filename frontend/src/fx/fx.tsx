import { useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import './fx.css'

/**
 * Small "award-site" effects, no libraries:
 *  - Cursor:    a dot + a trailing ring; over anything with data-cursor="LABEL" the ring
 *               grows into a bubble showing LABEL. Off on touch screens / reduced motion.
 *  - Preloader: counts 0 → 100, then the curtain slides up.
 *  - SplitText: each character rises in, one after another.
 *  - Marquee:   an endless ticker.
 */

import { reducedMotion } from './motion'
const finePointer = () => window.matchMedia('(pointer: fine)').matches

export function Cursor() {
  const dotRef = useRef<HTMLDivElement>(null)
  const ringRef = useRef<HTMLDivElement>(null)
  const [label, setLabel] = useState<string | null>(null)
  const [enabled] = useState(() => finePointer() && !reducedMotion())

  useEffect(() => {
    if (!enabled) return
    document.documentElement.classList.add('has-cursor')
    const mouse = { x: innerWidth / 2, y: innerHeight / 2 }
    const ring = { ...mouse }
    let raf = 0

    const move = (e: PointerEvent) => {
      mouse.x = e.clientX
      mouse.y = e.clientY
      const target = (e.target as Element | null)?.closest('[data-cursor]')
      setLabel(target ? target.getAttribute('data-cursor') : null)
    }
    const tick = () => {
      ring.x += (mouse.x - ring.x) * 0.16 // the ring trails behind the dot
      ring.y += (mouse.y - ring.y) * 0.16
      if (dotRef.current) dotRef.current.style.transform = `translate3d(${mouse.x}px,${mouse.y}px,0)`
      if (ringRef.current) ringRef.current.style.transform = `translate3d(${ring.x}px,${ring.y}px,0)`
      raf = requestAnimationFrame(tick)
    }
    window.addEventListener('pointermove', move)
    raf = requestAnimationFrame(tick)
    return () => {
      window.removeEventListener('pointermove', move)
      cancelAnimationFrame(raf)
      document.documentElement.classList.remove('has-cursor')
    }
  }, [enabled])

  if (!enabled) return null
  // Rendered into <body> on purpose: if a parent has a transform/animation, position: fixed
  // would be relative to that parent instead of the screen, and the cursor drifts away.
  return createPortal(
    <>
      <div ref={ringRef} className={`cursor-ring ${label ? 'cursor-ring--label' : ''}`} aria-hidden="true">
        <span>{label}</span>
      </div>
      <div ref={dotRef} className="cursor-dot" aria-hidden="true" />
    </>,
    document.body,
  )
}

export function Preloader({ onDone }: { onDone: () => void }) {
  const [count, setCount] = useState(0)
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    const start = performance.now()
    const DURATION = 1500
    let raf = 0
    const tick = (now: number) => {
      const t = Math.min((now - start) / DURATION, 1)
      setCount(Math.round(100 * (1 - Math.pow(1 - t, 3)))) // ease-out: fast, then settles
      if (t < 1) raf = requestAnimationFrame(tick)
      else {
        setLeaving(true)
        window.setTimeout(onDone, 750)
      }
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [onDone])

  return (
    <div className={`preloader ${leaving ? 'preloader--leave' : ''}`} role="status" aria-label="Loading">
      <p className="preloader__hand">brewing your decaf…</p>
      <p className="preloader__count">{String(count).padStart(3, '0')}</p>
      <div className="preloader__bar">
        <div style={{ transform: `scaleX(${count / 100})` }} />
      </div>
    </div>
  )
}

/** Splits text into characters that rise in with a stagger. `delay` in ms. */
export function SplitText({ text, delay = 0 }: { text: string; delay?: number }) {
  let i = 0
  return (
    <span className="split" aria-label={text}>
      {text.split(' ').map((word, w) => (
        <span key={w} className="split__word" aria-hidden="true">
          {[...word].map((ch) => (
            <span key={i} className="split__char" style={{ animationDelay: `${delay + i++ * 28}ms` }}>
              {ch}
            </span>
          ))}
          {' '}
        </span>
      ))}
    </span>
  )
}

export function Marquee({ children, reverse = false }: { children: ReactNode; reverse?: boolean }) {
  return (
    <div className={`marquee ${reverse ? 'marquee--reverse' : ''}`} aria-hidden="true">
      <div className="marquee__track">
        <span>{children}</span>
        <span>{children}</span>
      </div>
    </div>
  )
}
