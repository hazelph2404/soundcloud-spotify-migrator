// What hangs on the hallway walls: postcards, polaroids, records. Edit freely.
// Caption style: 'place - year', like a note written under a polaroid.
// To use your own photos: drop files into frontend/public/hallway/ and set `src: '/hallway/your-file.jpg'`.
// Without `src`, a frame paints its own artwork from `hue`.

export type Memory = {
  kind: 'album' | 'photo'
  caption: string
  hue: number // 0–360, base color for the painted artwork
  tilt: number // degrees, so the wall looks hung by hand
  lift: number // px up/down from the wall's centre line
  src?: string
}

export const MEMORIES: Memory[] = [
  { kind: 'photo', caption: 'new york - 2016', hue: 24, tilt: -3, lift: -40 },
  { kind: 'album', caption: 'lowkey finds, vol. 1', hue: 330, tilt: 2, lift: 30 },
  { kind: 'photo', caption: '3am bus home', hue: 210, tilt: 4, lift: -10 },
  { kind: 'album', caption: 'the bootleg era', hue: 12, tilt: -2, lift: 50 },
  { kind: 'photo', caption: 'headphones on, rain outside', hue: 190, tilt: -4, lift: -50 },
  { kind: 'album', caption: 'remixes nobody else knew', hue: 280, tilt: 3, lift: 20 },
  { kind: 'photo', caption: 'home, 2016', hue: 38, tilt: 2, lift: -30 },
  { kind: 'album', caption: "may '20", hue: 150, tilt: -3, lift: 40 },
  { kind: 'photo', caption: 'the one that got taken down', hue: 0, tilt: 5, lift: -20 },
  { kind: 'album', caption: "march '20", hue: 50, tilt: -1, lift: 10 },
  { kind: 'photo', caption: 'on repeat all year', hue: 320, tilt: -5, lift: -45 },
  { kind: 'album', caption: 'lowkey finds, vol. 2', hue: 18, tilt: 3, lift: 35 },
]
