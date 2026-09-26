# PLAYER: terminal-native art direction and visual system

**Scope.** This is the art-direction and presentation contract for all 20 themed built-ins and three starter layouts. Each design gets a distinct *page grammar*: masthead, layout silhouette, control rail, frame, typography, palette, visualizer composition, companion scene, and motion. The ten renderer families within each themed preset should remain visually distinct; the same family may recur in another preset. User-saved layouts remain editable and unconstrained. References inform material, era, composition, and instrumentation; do not ship reference screenshots, logos, art, typefaces, branded labels, or copied interface text. Avoid a universal neon-card treatment.

## Theme directions

### Y2K Aesthetic
- **Page:** Compact utility-window silhouette with a raised/double-rule frame, one broad viewport, and an oversized segmented `99 → 00` date readout. Use graphite with Indigo/Ruby/Sage/Snow accent tabs; compact late-90s UI labels. [R1–R3]
- **Graph / companion / controls:** Render time as a segmented odometer beside one signal plot; give the companion a tiny utility-widget frame; make transport and selection controls read as square inset keys. [R1, R3]

### Cyberpunk 2077
- **Page:** Asymmetric district-sign composition: narrow vertical zone labels and a dense street/status rail beside a dominant view. Use ink-black negative space, tungsten amber, hazard red, and cold cyan; condensed, high-impact headings. [R4]
- **Graph / companion / controls:** Make the graph feel like traffic or a city signal trace; use a short intercepted-radio ticker as companion; label hard-edged controls `SCAN / HOLD / TUNE`. Keep all signage and UI original. [R4]

### Matrix Terminal
- **Page:** Reserve one vertical column-rain field against a black terminal; keep the main panel and side telemetry sparse, with a bright green lead and dimmer trailing values. Use strict monospaced hierarchy. [R5]
- **Graph / companion / controls:** Let sampled values descend as original ASCII/numeric tokens; show an operator log as the companion and a terse prompt row for controls. Avoid the film's exact glyph set or type treatment. [R5]

### Lo-Fi Chill
- **Page:** Horizontal cassette-deck face: broad tape window above twin level readouts, with generous breathing room. Use washed cream, tobacco, olive, and muted rust; small printed labels around a relaxed title. [R6]
- **Graph / companion / controls:** Use a slightly irregular waveform and twin VU strips; companion is a low-key `ON AIR`/track note; transport feels like square `PLAY / REC / REW` buttons. [R6]

### Tokyo Night
- **Page:** Calm transit-map structure, not a collage of neon signs. Start from the theme's deep indigo (`#1a1b26`) with electric blue (`#7aa2f7`), cyan (`#7dcfff`), and lavender (`#bb9af7`); use thin routes and tidy mono labels. [R7]
- **Graph / companion / controls:** Draw a connected flow with stop markers rather than a wall of spectrum bars; use a quiet route/track ticker as companion and a compact, even-weight key strip. [R7]

### Retrowave Sunset
- **Page:** Make the full-width horizon and converging road/grid the frame—avoid surrounding it with repeated cards. Layer sunset bands of coral, orange, and magenta over deep indigo; use oversized segmented numerals. [R8, R9]
- **Graph / companion / controls:** Turn peaks into road markers receding to one vanishing point; companion reads like an instrument-cluster trip meter; controls are three squared arcade-style transport keys. [R8, R9]

### Industrial Decay
- **Page:** Build a wide exposed-beam/truss silhouette with uneven open bays, not a row of equal compartments. Use soot gray, oxidized orange, and faded caution yellow; stencil-like mono headings. [R10]
- **Graph / companion / controls:** Use a heavy load/pressure trace across a riveted grid, `o` bolt marks, and a sparse `///` caution strip; companion is a maintenance log and controls are breaker-like toggles. [R10]

### Deep Ocean
- **Page:** Let black-navy negative space dominate; frame a narrow vertical depth shaft with only a few separators. Use muted blue/cyan and one rare bioluminescent green accent. [R11]
- **Graph / companion / controls:** Render sonar returns as spaced pips and echo arcs rather than star-like noise; place `ROV / DEPTH` telemetry in the companion; make `PING / GAIN / DEPTH` readable controls. [R11]

### Solar Flare
- **Page:** Use one central flare/loop silhouette in an otherwise dark field, with a legible wavelength key (`131 / 171 / 304 Å`) in gold, teal, and red rather than a full-screen fire texture. [R12]
- **Graph / companion / controls:** Plot the flare rise as the dominant trace, with dimmer wavelength traces; companion is an event/active-region callout; controls select channel and time window. [R12]

### Acid Techno
- **Page:** Make a 16-step sequencer the page composition, with numbered steps and accent/slide lanes; use sour lime/yellow against black with a small violet counter-accent. [R13]
- **Graph / companion / controls:** Use a sharp cutoff/resonance sweep as the graph; companion carries pattern and tempo; controls are compact labeled knob-glyphs for `CUTOFF / RES / DECAY`. [R13]

### Vaporwave Mall
- **Page:** Use a dated mall-directory plan: floor bands, central court, store-code rail, and a kiosk-like title. Fade pink, cyan, lavender, and warm tile tones; leave generous blank atrium space. [R14, R15]
- **Graph / companion / controls:** Treat the graph as a slow ambient/muzak strip; companion is a PA announcement or wayfinding tile; make controls resemble `INFO / FIND / PLAY` kiosk keys. [R14, R15]

### Dungeon Synth
- **Page:** Center a single illuminated initial or map cartouche inside a parchment/folio frame; use deep plum/charcoal, parchment, ochre, and restrained rust-red. Keep ornamental corners sparse. [R16, R17]
- **Graph / companion / controls:** Shape the graph as a winding corridor/level contour rather than generic equalizer bars; companion is a map legend or field chronicle; controls read like small engraved plaques. [R16, R17]

### Chiptune Gameboy
- **Page:** Frame one dot-matrix viewport around the original Game Boy's `160×144` / four-level display logic; map it to four muted green-gray ANSI shades, with compact all-caps labels. [R18]
- **Graph / companion / controls:** Build bars from `░▒▓█` or an original 8×8 sprite motif; use a sprite/battery badge as companion and `↑ ↓ ← →` plus `[A] [B]` controls. Do not use Nintendo sprites or logos. [R18]

### Nordic Aurora
- **Page:** Use a wide polar horizon with sparse latitude arcs and airy spacing; midnight blue carries teal/aurora green, with only a trace of violet. [R19]
- **Graph / companion / controls:** Render spectrum as vertical curtain ribbons; pair it with an observed/forecast band and a companion latitude/time stamp; controls scrub direction and time range. [R19]

### Bioshock Steampunk
- **Page:** Borrow the underwater Art Deco silhouette: stepped crown, symmetry, and narrow vertical rails in brass-gold over deep teal/black. Use formal tall headings, not gear wallpaper. [R20]
- **Graph / companion / controls:** Shape the graph as a pressure needle and water ripple; make the companion a maintenance/telegraph slate; use round knob glyphs and explicit lever labels. [R20]

### Quantum Void
- **Page:** Start with near-empty space, a few bracketed register labels such as `|ψ⟩`, and one violet/cyan accent; avoid a card grid. [R21]
- **Graph / companion / controls:** Show measured outcomes as labeled probability bars; companion is a run/outcome ledger; use explicit `PREPARE / MEASURE / RESET` controls. [R21]

### Hyprland Rice
- **Page:** Use a tiling composition (one master pane plus a stack), thin active edge, deliberate gaps, and a small workspace strip. Borrow a muted pastel palette from Catppuccin; suggest focus with border contrast, not simulated blur. [R22, R23]
- **Graph / companion / controls:** Treat visualizers as resizable panes, not decorative cards; companion becomes the workspace/status bar; controls are concise key-hint labels. [R22, R23]

### DOS Mpxplay
- **Page:** Use a tight commander-style playlist/file view with fixed rows, a strong selection bar, abbreviations, and a bottom command rail. Keep a limited DOS-like blue/cyan/gray/amber palette and no gradients. [R24]
- **Graph / companion / controls:** Use block spectrum and stereo level columns; companion carries file metadata and elapsed time; put function-key actions in the footer. [R24]

### Analog Mastering
- **Page:** Build a matte instrument face with large dual scales and a narrow numeric ledger. Use neutral charcoal, warm ivory/olive, and sparing green/amber/red threshold accents; make labels precise and aligned. [R6, R25]
- **Graph / companion / controls:** Show calibrated loudness/true-peak history with L/R meters (phase/correlation can be a separate scope); companion is a calibration sheet; controls expose monitor A/B, bypass, and mute. [R6, R25]

### Stellar Galaxy
- **Page:** Use a dark sky-chart field with sparse RA/Dec ticks and star points at varied density; choose navy/ultramarine/violet with rare gold labels and light framing. [R26]
- **Graph / companion / controls:** Make the graph a constellation link or spectral trace, not an aurora curtain; companion is an object card (`RA / DEC / MAG`); controls change chart, zoom, or time. [R26]

## Starter layouts

### Solo Stanford 3D Waterfall
- **Page:** Give one wide viewport most of the screen, with a perspective/staggered-row waterfall and clear `TIME / FREQ / DEPTH` axes; keep the header and side rail quiet. [R27]
- **Graph / companion / controls:** Waterfall is the hero; waveform, FFT, or Lissajous are optional views rather than simultaneous mini-cards. Companion carries feature stats; controls expose freeze, rotate, and scale. [R27]

### Dual Cyber Deck
- **Page:** Make two complementary screens explicit: a large main scope plus a narrower telemetry/companion pane, distinct frame weights, and one shared bottom rail. Do not copy the referenced physical build. [R28]
- **Graph / companion / controls:** Pair views such as waveform and spectrum; put telemetry/companion in the second pane; provide shared transport plus independent pane focus. [R28]

### Quad Studio Master Deck
- **Page:** Arrange four aligned console panes around one master-bus header and shared time ruler; use compact engineering labels, consistent gutters, and one focused-pane accent. [R25, R29]
- **Graph / companion / controls:** Give quadrants complementary scopes—waveform, spectrum, loudness, phase/correlation—with common units and thresholds; keep mastering notes beside the bus and A/B/monitor controls shared. [R25, R29]

## Terminal translation guardrail

Treat each design as a layout and information-hierarchy cue, not a screenshot to reproduce. Textual supports widget borders and per-edge border styling plus CSS-defined layouts; translate frames into box-drawing/ASCII glyphs, map palettes to terminal color roles, and retain an ASCII fallback for glyph-width differences. Use contrast and sparse character density for glow/material instead of relying on raster textures, blur, or custom fonts. [R30]

## 2026 Visual Research Update

Use current aesthetic revivals as precise ingredients, not as a single trend applied everywhere. The current design response to generic, frictionless interfaces is to restore intentional texture, recognizable material, and human character. On a terminal, those qualities must come from composition, glyph density, color, and meaningful motion rather than raster effects.

- **Y2K and Frutiger Aero are adjacent, not interchangeable.** Y2K is chrome, optical media, and an uncertain digital future. The Frutiger Aero revival adds a more optimistic nature/technology blend: aquatic blues and greens, bubbles, soft glass-like highlights, and open space. Use the latter as a secondary layer for Y2K, without turning it into a generic glossy dashboard. [R31]
- **Neo Deco updates the Bioshock direction.** Keep the Art Deco symmetry and underwater geometry, but use a few precise fan, stepped, or sunburst motifs with deep jewel tones and restrained brass. Prefer selective geometry and negative space to wallpapering every panel with gears. [R32]
- **Cyberpunk needs compositional rules, not just neon.** Use near-black negative space, clipped or bracketed framing, a strict type hierarchy, one dominant alert hue, and cyan or amber only for distinct information roles. Reserve glitch for semantically unstable moments; do not animate every element. [R33, R34]
- **Rave, Outrun, and Mallsoft need separate emotional tempos.** Acid/rave is compressed, percussive, high-contrast, and flyer-dense; Outrun is forward-driving and optimistic; Mallsoft is spacious, slow, and liminal. Shared pink/purple colors do not make them the same design. [R35, R36, R37, R38]
- **Calm does not mean generic or motionless.** Lo-Fi and Nordic can be richly authored while keeping one clear focal point, broad breathing space, and slow motion. Motion should confirm audio or state, not compete with listening. [R31, R32]
- **Aesthetic fidelity includes source culture.** Dungeon Synth draws on low-fi cover art, solitary landscapes, manuscript/cartouche forms, and restrained mystery. Hyprland Rice draws on tiling, focus edges, gaps, workspace strips, and compact status bars. Reproduce the information grammar, not a screenshot or an unrelated cyberpunk overlay. [R39, R40]

## Preset Scene and Companion Direction

The companion is a designed part of the preset's information hierarchy, not a decorative portrait pasted beside it. Give each built-in a companion frame, scene vocabulary, and restrained audio response that share the page palette and material language. The companion may occupy a sidebar, instrument inset, directory tile, status rail, or a small footer slot; its location is specified per design. Keep dialogue short and contextual, preserve legibility, and provide a reduced-motion mode.

| Design ID | Built-in | Scene and visual signature | Companion integration and response |
| --- | --- | --- | --- |
| `preset_y2k_aesthetic` | Y2K Aesthetic | Chrome utility window with a Frutiger-Aero accent: aqua glass cues, optical-disc shimmer, bubbles, and an oversized segmented readout. | Aimi sits in a compact desktop-widget frame; slow bubble drift and one CD-spectrum sweep; playful expression on a clear transient. |
| `preset_cyberpunk_2077` | Cyberpunk 2077 | Asymmetric district map, near-black field, clipped brackets, sparse rain-reflection marks, and role-based amber/cyan/red. | V-Kira appears as an intercepted-radio portrait in the side rail; rain is slow, while a transient may briefly charge an original energy-line prop. |
| `preset_matrix_terminal` | Matrix Terminal | One phosphor-green code-rain field, dark trailing values, strict mono labels, and a restrained CRT scan. | Trinity-X is an operator/status tile with a short log line; code flow is continuous but sparse, with a brief bright lead on strong transients. |
| `preset_lofi_chill` | Lo-Fi Chill | Cassette-deck silhouette, warm paper/wood tones, broad waveform window, and soft grain implied by glyph density. | Maya occupies an `ON AIR` listening nook with mug-steam and window-rain motifs; breathing/sway only, no strobe or rapid color cycling. |
| `preset_tokyo_night` | Tokyo Night | Indigo transit map, thin connected routes, station dots, and reflected-rain accents; keep the hierarchy calm. | Ren is a platform-status portrait with a route ticker; a single train-light pass can follow a track change, otherwise the scene stays quiet. |
| `preset_retrowave_sunset` | Retrowave Sunset | Full-width road perspective, segmented low sun, palm silhouettes, VHS-like line interruptions, and coral-to-magenta horizon bands. | Chloe appears in an instrument-cluster inset; beat-synced road markers and a gentle bob, with chromatic split reserved for transitions. |
| `preset_industrial_decay` | Industrial Decay | Open truss bays, uneven structural spans, soot and oxidized metal roles, bolt marks, and a sparse caution stripe. | Rust-01 occupies a maintenance log; a small gauge tremor or spark marks a strong transient, while idle remains still and legible. |
| `preset_deep_ocean` | Deep Ocean | Narrow bathymetry shaft, sonar returns, broad navy negative space, and rare bioluminescent marks. | Marina is an ROV telemetry tile with depth and ping status; bubbles rise slowly, and bioluminescent trails appear only on detected events. |
| `preset_solar_flare` | Solar Flare | Dark observatory field, one dominant coronal-loop trace, and explicitly keyed wavelength channels. | Solara is an active-region observer; an arc and warm edge-light intensify on transients, not as a permanent fire texture. |
| `preset_acid_techno` | Acid Techno | 16-step sequencer is the page; numbered steps, accent/slide lanes, acid lime, and a small violet counter-accent. | Acid-DJ sits beside pattern/tempo readouts; the active step follows the audio pulse, with a short controlled flash on a strong transient. |
| `preset_vaporwave_mall` | Vaporwave Mall | Floor-directory plan, central atrium, store-code rail, generous empty space, pastel tile cues, and a deliberately slow muzak strip. | Crystal is a kiosk/PA tile; fountain ripples and a distant announcement bubble create gentle, slightly uncanny motion without horror imagery. |
| `preset_dungeon_synth` | Dungeon Synth | Parchment cartouche, one illuminated initial, sparse engraved corners, muted sepia/plum, and cassette-grain character. | Morwen appears in a field chronicle; one torch ember or rune glint responds to a transient, with long quiet intervals. |
| `preset_chiptune_gameboy` | Chiptune Gameboy | Single dot-matrix viewport, four-level green-gray logic, chunky 8-bit sprite motifs, and hard pixel alignment. | Dot-Chan is a cartridge/battery badge; use discrete pixel-frame poses and `[A]`/`[B]` emotes, never smooth neon gradients. |
| `preset_nordic_aurora` | Nordic Aurora | Wide polar horizon, sparse latitude arcs, airy spacing, and narrow curtain ribbons against midnight blue. | Freya is an observation/time stamp; slow aurora drift and a breath-vapor accent; no abrupt flashes. |
| `preset_bioshock_steampunk` | Bioshock Steampunk | Neo-Deco crown and rails, mirrored geometry, deep teal, jewel-tone highlights, and matte brass used sparingly. | Ada is a telegraph/pressure slate; a pressure needle and water ripple share the page's geometry, with deliberate, mechanical motion. |
| `preset_quantum_void` | Quantum Void | Near-empty field, a few ket-register labels, probability outcomes, and a measured decoherence trace. | Nova is an outcome ledger; particle paths resolve into stable states on measurement, avoiding random glitch or noisy starfields. |
| `preset_hyprland_rice` | Hyprland Rice | Master/stack tile composition, deliberate gaps, thin active edge, workspace strip, and Catppuccin-derived roles. | Dotfile is the compact workspace/status companion; focus follows the selected pane, with a tiny status pulse instead of simulated blur. |
| `preset_dos_mpxplay` | DOS Mpxplay | Commander-style fixed rows, selection bar, limited ANSI palette, block spectrum, and bottom function-key rail. | Commander Ken is file metadata/status, not a large portrait; use a blinking cursor and row selection, no gradients or faux scanline noise. |
| `preset_analog_mastering` | Analog Mastering | Matte instrument face, aligned dual scales, loudness/true-peak ledger, and threshold colors with calibrated units. | Elena is a calibration sheet; VU ballistics and alignment markers follow measured level smoothly, without decorative bounce. |
| `preset_stellar_galaxy` | Stellar Galaxy | Sparse RA/Dec chart, varied star density, constellation links, and rare gold object labels. | Astra is an object card with coordinates/magnitude; slow orbital drift and sparse twinkle, not an aurora curtain. |
| `builtin_solo_stanford` | Solo Stanford 3D Waterfall | One broad waterfall viewport with `TIME / FREQ / DEPTH` axes and a quiet lab rail. | CCRMA companion is a small research reticle/feature-stat panel; freeze/rotate state is explicit and the hero scope owns the motion. |
| `builtin_dual_cyber` | Dual Cyber Deck | Large primary scope, narrower telemetry/companion pane, distinct frame weights, and one shared bottom rail. | Companion links the two panes with a short signal/status line; pane focus is visible and does not change transport behavior. |
| `builtin_quad_matrix` | Quad Studio Master Deck | Four aligned console panes, common time ruler, master-bus header, and one focused-pane accent. | Companion is a four-bus monitor badge beside engineering notes; readings remain calibrated and stable across quadrants. |

## Dynamic Design Contract

Each built-in design is authored data, not a hand-tuned screen. The engine reads the design record and applies rail placement, button vocabulary, panel geometry, frame glyphs, and motion at runtime. This section is the field-level schema; `player_designs.py` is the source of record and `player_layout.py` (Phase 4) is the consumer.

### Design Field Schema

Fields on `PlayerPageDesign` as implemented in `src/harvester/ui/player_designs.py`:

| Field | Type | Allowed values / format | Consumed by |
| --- | --- | --- | --- |
| `layout_id` | `str` | One of the 23 ids in the design table above | `PLAYER_PAGE_DESIGNS`, `PlayerStudioWidget.apply_layout` |
| `eyebrow` | `str` | short uppercase kicker | compact masthead treatment |
| `page_title` | `str` | unique per design | `#plr-page-title` |
| `subtitle` | `str` | unique per design | `#plr-theme-subtitle` |
| `motif` | `str` | original glyph/word strip | motif slot (masthead, companion frame, or footer) |
| `dashboard_layout` | `str` | `balanced_rows`, `hero_left`, `hero_top`, `five_by_two`, `three_columns`, `split_columns`, `solo`, `dual`, `quad` | `VisualDashboardWidget.layout_style` |
| `control_style` | `str` | `capsule`, `cutout`, `terminal`, `soft`, `flat`, `heavy`, `lcd`, `instrument` | button family selection |
| `title_style` | `str` | Textual text-style subset: `bold`, `italic`, `underline`, or combinations | title label styling |
| `companion_heading` | `str` | unique per design | `#plr-anime-companion` header |
| `top_controls` | `tuple[str, ...]` (6 values) | label templates supporting `{gap}` and `{queue}` | order: home, presets, load, save, gap, popout |

Dimensions the runtime engine supports (resolved by `player_layout.py`, authored per built-in in `player_designs.py`); each dimension must exist and must not collapse into one generic theme switch:

| Dimension | Type | Allowed values / format | Purpose |
| --- | --- | --- | --- |
| `rail` | `str` | `masthead`, `rail_left`, `rail_right`, `footer`, `split_hud`, `corner_hud` | docking of the page control bar |
| `rail_axis` | `str` | `horizontal`, `vertical`, `grid` | button strip layout |
| `button_family` | `str` | `keys`, `plaques`, `pills`, `toggles`, `kiosk`, `knobs`, `lcd`, `brackets` | variant, border, and weight of controls |
| `button_frame` | `str` | template with `{label}`; e.g. `[F{n}:{label}]`, `【{label}】`, `> {label}` | transport label rendering |
| `panel_slots` | `dict[str, str]` | `dashboard` (dashboard layout id); `companion` ∈ `rail_left`/`rail_right`/`footer`/`inset`/`hidden`; `dock` ∈ `footer`/`header`; `motif` ∈ `masthead`/`companion`/`footer`/`hidden` | panel geometry |
| `frame_glyphs` | `str` | `box`, `double`, `heavy`, `ascii`, `tall`, `round`, `dashed`, `solid` plus one preset glyph set | per-edge borders and `border_title` treatment |
| `border_roles` | `dict[str, str]` | edge or panel name → theme role (`primary`, `secondary`, `accent`, `surface`, `foreground`) | border color mapping |
| `motion` | `tuple[...]` | `(kind, trigger, intensity, reduced)`; kind ∈ `odometer`, `marquee`, `blink`, `scanline`, `drift`, `pulse`, `step-blink`, `needle`; trigger ∈ `idle`, `playing`, `transient`, `track_change`, `selection`; intensity 0–2; reduced ∈ `hold`/`slow`/`hide` | `_tick_60fps` motion pass |

Authoring rules:

- **Page chrome:** eyebrow/title/subtitle/motif; control-rail placement and axis; control order; label vocabulary; button frame/family.
- **Panel geometry:** one supported dashboard composition; companion slot and size; player-dock slot and height; focused-panel behavior; breakpoint/compact fallback.
- **Visual language:** theme color roles (`background`, `surface`, `primary`, `secondary`, `accent`, `foreground`); border family and per-edge treatment; glyph/material vocabulary; visualizer family emphasis; density and renderer profile.
- **Companion direction:** original character identity; scene recipe; prop/emote vocabulary; permitted mood set; audio response profile; dialogue tone; companion frame and slot.
- **Motion:** one primary motion signature per page and at most one secondary accent. Define the audio/state event that triggers it, its intensity cap, and its reduced-motion behavior. Idle ambience must not masquerade as live audio.
- **Fallbacks:** fit at compact terminal sizes; retain clear controls; use ASCII-safe borders/glyphs where width or font coverage is uncertain; hide secondary decoration before clipping required information.

Legacy compatibility: user-saved layouts carry `ui_structure_style` and `button_style_mode`. `LEGACY_DASHBOARD_LAYOUTS` and `LEGACY_CONTROL_STYLES` in `player_designs.py` map those onto the vocabulary above. Built-in layouts resolve to their curated design; custom layouts fall back to the canonical design and remain editable.

### Terminal Rendering Fidelity

Default ladder: **sextant → quadrant → half-block → braille**, with octants only behind an explicit capability opt-in and ASCII as the universal fallback. Kitty/Sixel pixel protocols remain an optional future mode, not a requirement for the standard PLAYER experience. [R41–R45]

| Mode | Cell geometry | Colors per cell | Default role | Selection signal | Fallback |
| --- | --- | --- | --- | --- | --- |
| `octant` | 2×4 | foreground + background | opt-in only | explicit `ui.visual_fidelity = octant` when the font supports Unicode 16 | sextant |
| `sextant` | 2×3 | foreground + background | default for filled/portrait regions | `auto` with Unicode 13 glyph coverage | quadrant |
| `quadrant` | 2×2 | foreground + background | broad compatibility | `auto` fallback | half-block |
| `halfblock` | 1×2 | foreground + background | universal truecolor | `auto` fallback | braille |
| `braille` | 2×4 | single | line art, sparse plots, legacy terminals | `auto` fallback or explicit | ascii |
| `ascii` | 1×2 | none | final fallback (no Unicode blocks, pipes) | capability failure or explicit | — |
| `kitty` / `sixel` | pixel | truecolor | deferred | explicit opt-in only | sextant |

Rules:

- `ui.visual_fidelity` accepts `auto` or one of the mode names above; `auto` never selects octant without an explicit opt-in, and never relies on glyph availability as the only signal of terminal capability.
- Separate shape from color: select a glyph by the local coverage pattern, then map foreground/background to the preset's theme roles.
- Use ordered or error-diffusion dithering only where it supports the source material. Keep DOS and Game Boy palettes deliberately limited; preserve analog/natural gradients for mastering, ocean, solar, and stellar scenes.
- Cache fitted artwork and unchanged cells. Prefer event-driven redraws and a shared frame clock over independent 60 FPS timers for the dashboard and companion.
- The character art is the focal content. Dense backgrounds, particles, scanlines, and color cycling must yield to face/pose recognition and companion text.

### Companion Character Direction

The current companion library has 31 Braille artworks. Treat that as a starting roster, not a reason to repeat portraits under new names. New characters should be original, have a distinct silhouette/personality and an art source with a clear license; do not add copied anime characters, franchise names, sprites, or recognizable costume designs. Character identity stays stable across presets; only scene lighting, small original props, palette, and stateful expression adapt.

- **Audio-driven states:** map existing `AudioFeatureContext` measures (bass/sub-bass, RMS, spectral centroid, transient, playback state) to authored states such as `idle`, `focus`, `chill`, `groove`, `hype`, and `sleepy`. A BPM estimate may be added from stable onset intervals, but never infer a beat from every spectral transient.
- **Transitions:** use hysteresis and cooldowns so the companion does not flicker between moods. Track changes, pause/resume, and selected visualizer are explicit context events; they may trigger one short greeting or emote.
- **Motion and expression:** breathing, sway, bob, blink, small prop response, and occasional expression changes are preferable to full-frame flashing. Provide a manual mood pin and reduced-motion option.
- **Speech and status:** keep speech bubbles brief, optional, theme-voiced, and non-blocking. Keep track facts accurate; flavor text must not invent playback/analysis data.
- **Integration:** share palette tokens with the page and visualizers; place the companion according to each page grammar; allow selecting another character without breaking the preset's page identity.

### Acceptance Checklist

Every built-in passes these checks before being considered art-directed:

1. Its composition, control rail, panel geometry, frame vocabulary, and motion signature are recognizable without reading the title.
2. It has one primary visual focus and does not reuse a universal card grid or neon treatment.
3. Buttons have a clear role, fit at compact widths, and keep their functional action when labels/styles change.
4. Companion pose, frame, scene, and color belong to the preset; motion is tied to audio/state and has an accessible quiet mode.
5. Audio-driven visuals use measured features; idle motion is visibly distinct from live response.
6. Required labels and controls survive ASCII/limited-glyph fallback and narrow terminal layouts.
7. References are translated into original composition; no shipped UI, logos, fonts, copied artwork, or protected character designs.
8. Doc/code parity: the row's `layout_id` exists in `PLAYER_PAGE_DESIGNS` and `BUILTIN_LAYOUTS`; every field consumed by the engine is declared in the schema above; the ten renderer families stay unique within each preset.
9. Renderer fidelity: the design declares its renderer profile, and required information survives the full fallback ladder down to `ascii`.

## Source register

### Computing, games, and place
- **[R1]** [NIST — Year 2000 date problem](https://www.nist.gov/news-events/news/1998/08/nist-tool-will-help-small-manufacturers-exterminate-millennium-bug) — Primary government explanation of failures caused by the `00` year designation.
- **[R2]** [Apple — New iMac colors (2000)](https://www.apple.com/newsroom/2000/07/19Apple-Introduces-New-iMacs-in-Stunning-New-Colors/) — First-party period color names: Indigo, Ruby, Sage, Snow, and Graphite.
- **[R3]** [GUIdebook — Windows 2000 Pro screenshots](https://guidebookgallery.org/screenshots/win2000pro) — Archival captures of desktop, Notepad, HyperTerminal, and Command Prompt; a period-interface reference, not a vendor source.
- **[R4]** [CD PROJEKT RED — Cyberpunk 2077 Photo Mode Challenge](https://www.cyberpunk.net/en/photo-mode-challenge) — Official Night City scene/Photo Mode reference; use its density and lighting as inspiration, not its interface.
- **[R5]** [CNET — interview with Simon Whiteley, Matrix code creator](https://www.cnet.com/culture/entertainment/lego-ninjago-movie-simon-whiteley-matrix-code-creator/) — Creator testimony about the green cascading code and its Japanese-inspired symbols.
- **[R7]** [Tokyo Night theme source](https://github.com/tokyo-night/tokyo-night-vscode-theme) — First-party palette values and a theme described around downtown Tokyo at night.
- **[R9]** [SEGA AGES — Out Run](https://segaages.sega.com/project/out-run/index.htm) — Official retro road-racing page with screenshots; use the horizon/perspective as a structural cue only.
- **[R14]** [猫 シ Corp. — Palm Mall](https://catsystemcorp.bandcamp.com/album/palm-mall) — Artist Bandcamp release describing the mall/ Muzak concept and floor/wayfinding track language.
- **[R15]** [Mall of America — Spring 2017 map + directory](https://www.mallofamerica.com/upload/MOA_Directory_Spring2017.pdf) — First-party floor plan, store codes, and directory hierarchy.
- **[R17]** [Budrum — The Legend of Valtoria, Orko Productions](https://orkoproductions.bandcamp.com/album/the-legend-of-valtoria) — Label/artist page identifies the project as Dungeon Synth and describes its dark-fantasy atmosphere.
- **[R18]** [Nintendo — Game Boy hardware history/specifications](https://www.nintendo.com/en-gb/Hardware/Nintendo-History/Game-Boy/Game-Boy-627031.html) — First-party specs list a 160×144 dot-matrix LCD, four shades of gray, and four-channel sound.
- **[R20]** [2K — BioShock official site](https://2k.com/games/bioshock/bioshock-1/) — Publisher describes Rapture as an underwater Art Deco city and calls out its water effects.

### Instruments, audio standards, and terminal UI
- **[R6]** [Yamaha TC-66 cassette deck owner's manual](https://data.yamaha.com/files/download/other_assets/1/313831/TC-66.pdf) — First-party deck manual with vertical hardware layout and large VU meters, including a −20 to +5 dB range.
- **[R13]** [Roland TB-03 owner's manual](https://static.roland.com/assets/media/pdf/TB-03_eng03_W.pdf) — First-party Bass Line manual covering pattern steps, cutoff, resonance, decay, accent, and slide.
- **[R24]** [Mpxplay developer homepage](https://mpxplay.sourceforge.net/) — Project source describes Mpxplay as a commander-style DOS/Win32 console audio player.
- **[R25]** [EBU R 128-2023](https://tech.ebu.ch/docs/r/r128.pdf) — Broadcast loudness normalization recommendation; references loudness and true-peak measurement.
- **[R27]** [Stanford CCRMA — sndpeek](https://ccrma.stanford.edu/~ge/software/sndpeek) — Real-time visualizer documentation lists waveform, FFT, 3D waterfall, Lissajous, freeze, rotate, and scale views.
- **[R28]** [Raspberry Pi Official Magazine — Dual-screen cyberdeck](https://magazine.raspberrypi.com/articles/dual-screen-cyberdeck) — First-party magazine coverage of a physical dual-display cyberdeck.
- **[R29]** [Yamaha DM7 series reference manual](https://usa.yamaha.com/files/download/other_assets/2/2148452/DM7_RM_En_D1.pdf) — Console manual documents overview, selected-channel, EQ, and dynamics screens.
- **[R30]** [Textual — borders](https://textual.textualize.io/styles/border) and [layouts](https://textual.textualize.io/guide/layout/) — Official documentation for widget border styles/per-edge borders and CSS-defined layout.

### Science and museum references
- **[R8]** [NASA Earth Observatory — ISS sunset](https://science.nasa.gov/earth/earth-observatory/sunset-from-the-international-space-station-44267/) — NASA describes the orbital horizon and its layered sunset colors.
- **[R10]** [National Park Service — Retaining Industrial Character](https://nps.gov/orgs/1739/upload/its-55-retaining-industrial-character.pdf) — Preservation guidance describes large open industrial spaces, exposed structure, and rusted material.
- **[R11]** [NOAA Ocean Exploration — Bioluminescent organisms](https://oceanexplorer.noaa.gov/multimedia/explorations-19biolum-logs-jun12-media-bioluminescent-organisms/) — Official low-light ROV imagery and description of bioluminescence.
- **[R12]** [NASA SVS — October 2024 solar flare](https://svs.gsfc.nasa.gov/14709) — SDO flare image combines 131, 171, and 304 Å extreme-ultraviolet channels and shows a flare loop.
- **[R16]** [The Met — illuminated manuscript leaf](https://www.metmuseum.org/art/collection/search/32833) — Museum catalog for a medieval leaf with an illuminated initial; object record and public-domain image context.
- **[R19]** [NOAA SWPC — 30-minute aurora forecast](https://www.swpc.noaa.gov/products/aurora-30-minute-forecast) — Official location/intensity forecast using the OVATION model.
- **[R21]** [IBM Quantum Learning — measurement formulations](https://quantum.cloud.ibm.com/learning/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements) — Official lesson explains measurement outcomes and their probabilities.
- **[R26]** [NASA — Hubble image gallery](https://science.nasa.gov/mission/hubble/multimedia/hubble-images/) — Official gallery includes nebulae, star clusters, and deep-field galaxy imagery.

### Desktop-theme references
- **[R22]** [Hyprland configuration guide](https://wiki.hypr.land/Configuring/) — Official wiki frames configuration as desktop “ricing” and links its layout/configuration options.
- **[R23]** [Catppuccin palette project](https://github.com/catppuccin/catppuccin) — Theme maintainers describe a pastel palette system with multiple flavors.

### Contemporary visual direction and character interaction
- **[R31]** [Dazed — What is Frutiger Aero?](https://www.dazeddigital.com/life-culture/article/58103/1/what-is-frutiger-aero-aesthetic-tiktok-msn-messenger-windows-vista-noughties) — Interviews with Consumer Aesthetics Research Institute contributors; distinguishes the glossy, nature-linked Aero language from Y2K nostalgia.
- **[R32]** [Architectural Digest — “Neo Deco” is the designer-approved trend of 2026](https://www.architecturaldigest.com/story/neo-deco-decor) — Contemporary interpretation of Art Deco geometry, material restraint, jewel tones, and brass.
- **[R33]** [Curio — Cyberpunk 2077 screen UI style guide](https://designbycurio.com/learn/cyberpunk-2077-screen) — Secondary analysis of black-field hierarchy, L-brackets, scanlines, and semantic use of glitch; inspiration only, not an implementation reference.
- **[R34]** [Nocturne — open-source Cyberpunk-inspired design system](https://mederic.me/blog/nocturne-design-system) — Design tokens and accessibility treatment for a distinct cyberpunk language.
- **[R35]** [Studio 2AM — Late-90s techno aesthetics](https://studio2am.co/blogs/news/why-designers-are-obsessed-with-late-90s-techno-aesthetics-right-now) — Contemporary account of rave-flyer density, chrome, photocopy texture, and subgenre-specific visual grammar.
- **[R36]** [Synthwave TV — What is Mallsoft?](https://synthwavetv.com/what-is-mallsoft/) — Secondary overview of mallsoft's slowed muzak, long reverb, and empty-retail-space atmosphere.
- **[R37]** [Sixth Tone — The Dream of the '90s is Alive on the Chinese Internet](https://www.sixthtone.com/news/1018582) — Reporting on Chinese dreamcore, memory, emptiness, and dated digital/urban environments.
- **[R38]** [AIGA Eye on Design — What rave culture is teaching modern graphic designers](https://eyeondesign.aiga.org/what-rave-culture-is-teaching-modern-graphic-designers/) — Design-history perspective on rave's bold type, fluorescent color, collage, and movement.
- **[R39]** [Dungeon Synth Aesthetic — grandmas and dinosaurs](https://admindagency.com/dungeon-synth-aesthetic/) — Genre-specific analysis of cassette-era cover art, medieval imagery, monochrome/sepia, and DIY presentation.
- **[R40]** [Hyprland “HyprPunk” rice reference](https://www.reddit.com/r/unixporn/comments/1u86zj7/oc_hyprland_hyprpunk_neon_rain_mauve_borders/) — Community example of workspace/status composition and Catppuccin/Mauve theming; treat as a dated user setup, not a canonical design.

### Terminal graphics and reactive companions
- **[R41]** [Kitty Terminal Graphics Protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/) — Primary protocol specification for pixel graphics, placement, blending, and animation.
- **[R42]** [Chafa](https://github.com/hpjansson/chafa) — Open-source terminal graphics converter with ANSI/Unicode and image-protocol output paths.
- **[R43]** [Notcurses terminal support matrix](https://github.com/dankamongmen/notcurses/blob/master/TERMINALS.md) — Practical terminal capability notes for color and graphics features; glyph/font support remains a separate concern.
- **[R44]** [Dapple renderer guide](https://queelius.github.io/dapple/guide/renderers/) — Secondary, current comparison of braille, quadrant, sextant, pixel-protocol, dithering, and fallback trade-offs; reference only, not a required dependency.
- **[R45]** [textual-image](https://github.com/lnqs/textual-image) — Optional Textual image-widget reference for Kitty/Sixel and Unicode fallbacks; its documented Textual performance/flicker caveats support deferring it from the default path.
- **[R46]** [Moeko-chan](https://github.com/Eskalade/moeko-chan) — Recent open-source music companion example: BPM-aware mood states, sleep-on-silence, and spring-like motion; borrow interaction patterns only.
- **[R47]** [NekoAI](https://github.com/nucket/NekoAI) — Recent open-source desktop-pet example for moods, speech bubbles, and a multi-character roster; borrow interaction patterns only.
- **[R48]** [WIRED — The stories behind Japanese text-board ASCII art](https://www.wired.com/2008/06/mf-hiroyuki-ss/) — Reporting on collaborative Japanese AA characters and expressive variants; supports treating character identity and expression as authored systems.
