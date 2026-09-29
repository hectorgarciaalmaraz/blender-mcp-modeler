# Parametric Glass Bottle — Blender MCP Project

## Goal
Build a photorealistic 3D model of a tapered glass spirits bottle in Blender. Claude Code runs every
modeling step through the Blender MCP server; the geometry lives in `scripts/build_bottle.py` so it can be
re-run from scratch at any time.

## Blender connection
- Blender must be open with the MCP add-on server running on port **9876**.
- Use the Blender MCP tools to execute Python directly inside Blender.
- Before each session, confirm Blender shows "Running on port 9876".
- `scripts/build_bottle.py` is idempotent: it deletes `BottleBody` and `Cork` before rebuilding them.

## Bottle specification

### Shape
- Conical/triangular silhouette: wide at the base, narrowing toward the neck.
- Flat, thick base (solid-glass foot).
- Smooth transition from the wide body to the narrow neck.

### Dimensions (real-world scale, 1 unit = 1 m in Blender)
| Part | Measurement |
|---|---|
| Base | 6 cm wide |
| Lower body (widest point) | 9 cm wide |
| Body height | 21.2 cm |
| Upper body (narrowest point) | 5 cm wide |
| Neck width | 2.5 cm |
| Neck height | 5 cm |
| Cork seat collar | 0.3 cm |
| Cork width | 4 cm |
| Cork height | 1.5 cm |

### Surface detail
- Lower third of the body (Z = 2.5–11 cm): sunken S-shaped grooves running diagonally from lower-left to
  upper-right, evoking agave leaves carved into the glass.
- Current setting: 8 grooves around the full 360°, 5 mm deep (started at 4–5 cuts; 8 read better in render).
- Grooves are displaced inward (engraved), never raised.

### Glass material
- Clear glass with a slight blue-green tint, high transparency.
- IOR 1.52, roughness 0, with reflections and refractions (render in Cycles).
- Pending: a small amount of clear liquid at the base.

### Cork
- Wooden cork, cylindrical, warm oak color.
- Sits on the neck collar.
- Pending: rounded top (currently a flat cylinder).

## Labels (future phase, not started)
Front label, neck band, back label and a decorative side label. Artwork is supplied per project; no brand
artwork lives in this repository.

## Lighting and render
- Three-point studio lighting.
- Neutral light-gray background.
- Front camera centered on the bottle.
- Render with **Cycles** for photorealistic glass.
