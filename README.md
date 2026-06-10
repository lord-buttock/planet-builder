# Planet Builder

A web app for Year 6 students at Ngarri Primary School (Victoria, Australia) to design their own habitable alien planet. Students fill in a 10-section form describing their planet's appearance, terrain, atmosphere, life forms, and civilisation. The app generates AI image and video prompts they can use in Firefly or Canva AI, and shows a live interactive 3D model of their planet.

**Live site:** https://planet-builder.onrender.com
**GitHub:** https://github.com/lord-buttock/planet-builder

---

## What students do

1. Fill in the form across 10 sections (name, type, colours, terrain, atmosphere, life, civilisation, etc.)
2. Click **Generate My Planet** — the 3D model renders immediately in the browser
3. Copy the AI **image prompt** → paste into Adobe Firefly or Canva AI to generate a detailed image
4. Copy the AI **video prompt** → paste into an AI video tool to animate their planet
5. Compare the AI-generated image with the 3D model

---

## Features

### 3D Planet Renderer (Babylon.js)

Every form choice drives a visible change in the 3D model:

**Surface & texture**
- 9 surface coverage types (deep oceans, lava flows, thick ice sheets, dense forests, alien vegetation, crystal formations, toxic pools, vast deserts, bare rock) — each tints/modifies the terrain texture at the correct elevation band
- Life type tint — planets with living organisms get a soft organic green cast across mid-elevations
- Terrain features painted at seeded positions: active volcanoes (glowing hotspots), impact craters (dark depressions with bright rims), deep canyons, glaciers, winding rivers, mountain ranges with bright snow peaks
- Permanent storm system — oval swirling region with darker rim and glowing centre (Jupiter's Great Red Spot style)
- Each planet name produces a unique terrain — the noise seed is derived from the planet name, so the same planet always looks the same

**Atmosphere & effects**
- Aurora — coloured bands (green/blue/purple) concentrated at the poles, slow independent rotation, picked up by GlowLayer
- Volcanic smoke — dark grey cloud layer, only appears if volcanoes or volcanic planet type is selected
- Thick fog — milky haze hugging the surface
- Coloured atmospheric haze — increases atmosphere rim glow intensity
- Cloud layer — thick storm, standard, or thin clouds

**Lighting & glow**
- Sun intensity wired from the lighting form field (brightly lit / half lit / dimly lit / glowing from within)
- Emissive glow wired from the glow field (cracked glowing surface / edge glow / full atmosphere glow)
- GlowLayer picks up all emissive surfaces — lava, volcanoes, aurora, city lights, special features

**City lights**
- Appears only for intelligent life + modern, advanced, or unknown civilisation level
- Pinpoint dots placed only on land masses (matching the planet's terrain noise), not over oceans
- Density and size scale with civilisation level (unknown → sparse dots, modern → clusters, advanced → dense clusters + megacity blobs)
- Additive transparent sphere — visible only on the dark side, subtle on the lit side

**Moons**
- One large moon, two smaller moons, several moons + ringed neighbour, or a distant neighbouring planet
- Each moon has a rocky greyscale texture, unique orbital inclination, and animated orbital motion
- Outer moons orbit slower (realistic feel)

**Planetary rings**
- Flat disc (cylinder with height 0.015) with a radial gradient ring texture, not a tube
- Colour-matched to the planet atmosphere, tilted 0.38 radians

**Space background**
- Deep black with stars (default)
- Vivid colourful nebula — full-screen background layer with rich purples, oranges, blues, and magentas (no geometry artifacts)
- Near a bright galaxy — warm white/yellow stars, more particles
- Dusty and dim — amber-tinged, fewer particles
- Dense star cluster — blue-white, many bright particles

### AI Prompt Generation

- **Space view image prompt** — full-planet orbital view, emphasises the complete sphere in frame with rich surface detail
- **Surface view image prompt** — ground-level cinematic scene facing the student's chosen feature, describes terrain, sky, creatures, and civilisation
- **Space view video prompt** — planet rotates slowly left-to-right
- **Surface view video prompt** — slow smooth pan across the landscape
- Prompts adapt to every form choice including life type, civilisation level, special features, and art style

### Planet Info Panel

- Planet name, type badge, life badge, civilisation badge
- 6 stat cards: Diameter, Gravity, Temperature, Day Length, Year Length, Moons
- Stats are seeded from the planet name — same planet always gets the same stats
- Key Features list
- "Life on [Planet]" section for planets with living organisms

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + Flask 3.0 |
| 3D rendering | Babylon.js 7 (CDN) |
| Texture generation (client) | HTML5 Canvas 2D + value noise FBM |
| Texture generation (server) | NumPy + SciPy + Pillow (higher quality fallback) |
| Hosting | Render.com free tier (gunicorn, 1 worker) |
| Fonts | Orbitron (headings) + Nunito (body) via Google Fonts |

---

## File structure

```
planet-builder/
├── app.py                 # Flask routes — serves index.html and /api/planet
├── planet_gen.py          # Server-side texture generator (numpy/scipy/Pillow)
├── requirements.txt       # Python dependencies
├── render.yaml            # Render.com deployment config
├── Procfile               # gunicorn start command
├── .python-version        # Pins Python 3.11.9
├── static/
│   └── textures/          # Server-generated textures (not committed)
└── templates/
    └── index.html         # Entire frontend — HTML + CSS + JavaScript (~1400 lines)
```

The entire frontend lives in a single `templates/index.html` file. There are no build steps, no bundler, no npm.

---

## Running locally

```bash
cd planet-builder
pip3 install -r requirements.txt
python3 app.py
```

Open http://localhost:5000

---

## Deployment

Hosted on Render.com free tier. Auto-deploys on every push to `main`.

```bash
git push origin main
# Render picks it up automatically — deploys in ~2 minutes
```

Note: the free tier sleeps after 15 minutes of inactivity. The first request after a sleep takes 30–60 seconds to wake up.

---

## Educational context

- **School:** Ngarri Primary School, Victoria, Australia
- **Teacher:** Phill Cantone, Digitech Learning Specialist
- **Year level:** Year 6 (age 11–12)
- **Curriculum:** Science — conditions for life, habitable planets
- **Framework:** CE⁵ (Curiosity, Creativity, Empowerment, Connection, Equity)
