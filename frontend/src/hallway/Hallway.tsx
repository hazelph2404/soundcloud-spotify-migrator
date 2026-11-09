import { useEffect, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from 'react'
import { MEMORIES, type Memory } from './memories'
import { Marquee, SplitText } from '../fx/fx'
import './hallway.css'

/**
 * The walk-in: scrolling down moves you sideways along a hallway of old albums and
 * photos, ending at a door. Opening the door calls `onEnter` (the app lives behind it).
 *
 * How the scroll works: the section is as tall as the hallway is wide, and its inner
 * "viewport" is sticky. Each frame we read how far the page has scrolled into the
 * section and slide the layers left by that much (eased, so it glides).
 */

const EASE = 0.13 // 0–1: lower = smoother/slower catch-up
const SPEED = { far: 0.45, wall: 1, near: 1.6 } // parallax: near things move faster

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export default function Hallway({ onEnter, introDelay = 0 }: { onEnter: () => void; introDelay?: number }) {
  const sectionRef = useRef<HTMLElement>(null)
  const wallRef = useRef<HTMLDivElement>(null)
  const farRef = useRef<HTMLDivElement>(null)
  const nearRef = useRef<HTMLDivElement>(null)
  const floorRef = useRef<HTMLDivElement>(null)
  const lightRef = useRef<HTMLDivElement>(null)
  const barRef = useRef<HTMLDivElement>(null)
  const [travel, setTravel] = useState(0) // px the wall slides from start to door
  const [atDoor, setAtDoor] = useState(false)
  const [opening, setOpening] = useState(false)
  const [wiping, setWiping] = useState(false)
  const [reduced] = useState(prefersReducedMotion)

  // Measure the hallway so the section is exactly long enough to walk it.
  useEffect(() => {
    if (reduced) return
    const measure = () => {
      const wall = wallRef.current
      if (wall) setTravel(Math.max(0, wall.scrollWidth - window.innerWidth))
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [reduced])

  // The walk: one requestAnimationFrame loop, writing transforms directly (no re-renders).
  useEffect(() => {
    if (reduced || travel === 0) return
    let current = 0
    let raf = 0
    const tick = () => {
      const section = sectionRef.current
      if (section) {
        const scrolled = -section.getBoundingClientRect().top
        const target = Math.min(Math.max(scrolled, 0), travel)
        const velocity = target - current
        current += velocity * EASE
        // lean the frames while you scroll fast (award-site "velocity skew")
        const skew = Math.max(-8, Math.min(8, velocity * -0.02))
        const progress = current / travel

        if (wallRef.current) {
          wallRef.current.style.transform = `translate3d(${-current * SPEED.wall}px,0,0)`
          wallRef.current.style.setProperty('--skew', `${skew}deg`)
        }
        if (farRef.current) farRef.current.style.transform = `translate3d(${-current * SPEED.far}px,0,0)`
        if (nearRef.current) nearRef.current.style.transform = `translate3d(${-current * SPEED.near}px,0,0)`
        if (floorRef.current) floorRef.current.style.backgroundPositionX = `${-current}px`
        if (lightRef.current) lightRef.current.style.opacity = String(0.35 + 0.65 * progress)
        if (barRef.current) barRef.current.style.transform = `scaleX(${progress})`
        setAtDoor(progress > 0.96)
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [reduced, travel])

  // Easier walking: sideways trackpad swipes, arrow keys, and the walk button all move you along.
  useEffect(() => {
    if (reduced) return
    const onWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) window.scrollBy({ top: e.deltaX })
    }
    const onKey = (e: KeyboardEvent) => {
      const step = window.innerWidth * 0.7
      if (e.key === 'ArrowRight') window.scrollBy({ top: step, behavior: 'smooth' })
      if (e.key === 'ArrowLeft') window.scrollBy({ top: -step, behavior: 'smooth' })
    }
    window.addEventListener('wheel', onWheel, { passive: true })
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('wheel', onWheel)
      window.removeEventListener('keydown', onKey)
    }
  }, [reduced])

  const walk = () => {
    if (atDoor) return
    window.scrollBy({ top: window.innerWidth * 0.7, behavior: 'smooth' })
  }

  const openDoor = () => {
    if (opening) return
    setOpening(true)
    if (reduced) return onEnter()
    window.setTimeout(() => setWiping(true), 950) // door swings, then a circle wipes to the room
    window.setTimeout(onEnter, 1700)
  }

  const door = (
    <div className={`door ${atDoor || reduced ? 'door--near' : ''} ${opening ? 'door--open' : ''}`}>
      <p className="door__sign">your 2016 lives in here</p>
      <div className="door__frame">
        <div className="door__room" aria-hidden="true" />
        <button className="door__panel" onClick={openDoor} aria-label="Open the door" data-cursor="open">
          <span className="door__knob" />
          <span className="door__label">open</span>
        </button>
      </div>
      <div className="door__glow" aria-hidden="true" />
    </div>
  )

  // Reduced motion: no scroll-jacking or parallax, just the door.
  if (reduced) {
    return (
      <section className="hallway hallway--static">
        <div className="hallway__viewport">
          <div className="hallway__light" style={{ opacity: 1 }} />
          <div className="hallway__static-door">{door}</div>
        </div>
      </section>
    )
  }

  return (
    <section ref={sectionRef} className="hallway" style={{ height: `calc(${travel}px + 100vh)` }}>
      <div className="hallway__viewport">
        <div ref={lightRef} className="hallway__light" />

        {/* far layer: the back of the hallway, moves slowly */}
        <div ref={farRef} className="hallway__layer hallway__far" aria-hidden="true">
          {Array.from({ length: 10 }, (_, i) => (
            <span key={i} className={`far-shape far-shape--${i % 3}`} />
          ))}
        </div>

        {/* the wall: memories, then the door */}
        <div ref={wallRef} className="hallway__layer hallway__wall">
          <div className="hallway__intro">
            <p className="hallway__kicker">hello kitty decaf</p>
            <h1>
              <SplitText text="your 2016 soundcloud likes deserve a home." delay={introDelay} />
            </h1>
            <p className="hallway__hint">scroll, swipe, or press → to walk in</p>
          </div>
          {MEMORIES.map((m, i) => (
            <Frame key={i} memory={m} pattern={i % 4} />
          ))}
          {door}
        </div>

        {/* near layer: things close to you, moves fast */}
        <div ref={nearRef} className="hallway__layer hallway__near" aria-hidden="true">
          {Array.from({ length: 9 }, (_, i) => (
            <span key={i} className={`near-sticker near-sticker--${i % 3}`}>
              {['★', '✿', '♪'][i % 3]}
            </span>
          ))}
        </div>

        <div ref={floorRef} className="hallway__floor" aria-hidden="true" />
        <div className="hallway__dots" aria-hidden="true" />

        <div className="hallway__ticker">
          <Marquee>lowkey finds ★ bootlegs ★ remixes nobody knew ★ summer 2016 ★ 3am bus home ★ on repeat ★</Marquee>
        </div>
        <div className="hallway__ticker hallway__ticker--floor">
          <Marquee reverse>save the songs before they disappear ✿ soundcloud → spotify ✿ hello kitty decaf ✿</Marquee>
        </div>
        {wiping && <div className="wipe" aria-hidden="true" />}

        {!atDoor && (
          <button className="hallway__walk" onClick={walk} aria-label="Walk forward" data-cursor="walk">
            →
          </button>
        )}

        <button className="hallway__skip" onClick={onEnter} data-cursor="skip">
          skip the hallway →
        </button>
        <div className="hallway__progress" aria-hidden="true">
          <div ref={barRef} className="hallway__progress-bar" />
        </div>
      </div>
    </section>
  )
}

function Frame({ memory, pattern }: { memory: Memory; pattern: number }) {
  const { kind, caption, hue, tilt, lift, src } = memory
  const style = { '--hue': hue, '--tilt': `${tilt}deg`, '--lift': `${lift}px` } as CSSProperties

  // 3D tilt toward the pointer while hovering
  const onMove = (e: ReactPointerEvent<HTMLElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const x = (e.clientX - r.left) / r.width - 0.5
    const y = (e.clientY - r.top) / r.height - 0.5
    e.currentTarget.style.setProperty('--ry', `${x * 18}deg`)
    e.currentTarget.style.setProperty('--rx', `${-y * 18}deg`)
  }
  const onLeave = (e: ReactPointerEvent<HTMLElement>) => {
    e.currentTarget.style.setProperty('--ry', '0deg')
    e.currentTarget.style.setProperty('--rx', '0deg')
  }
  const hover = { onPointerMove: onMove, onPointerLeave: onLeave, 'data-cursor': '2016' }

  if (kind === 'album') {
    return (
      <figure className={`frame album album--p${pattern}`} style={style} {...hover}>
        <div className="album__vinyl" aria-hidden="true" />
        <div className="album__cover">{src && <img src={src} alt="" loading="lazy" />}</div>
        <figcaption className="sticker">{caption}</figcaption>
      </figure>
    )
  }
  return (
    <figure className="frame photo" style={style} {...hover}>
      <span className="tape" aria-hidden="true" />
      <div className="photo__image">
        {src ? <img src={src} alt="" loading="lazy" /> : <span className="photo__sun" aria-hidden="true" />}
      </div>
      <figcaption>{caption}</figcaption>
    </figure>
  )
}
