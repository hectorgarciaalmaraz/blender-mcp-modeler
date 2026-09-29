"""Build a real-scale tapered glass bottle with engraved agave-leaf grooves.

Runs inside Blender (``bpy`` and ``bmesh`` are Blender's bundled modules). Meant to be
sent by Claude Code through the Blender MCP server, but it also runs from Blender's
Scripting workspace or headless with ``blender --background --python``.

Steps:
    1. Build a 2D (radius, height) profile in centimeters.
    2. Revolve it into a closed mesh with ``bmesh`` (360 segments).
    3. Displace eight S-shaped grooves into the lower third of the body.
    4. Recalculate normals, shade smooth and assign a glass material (IOR 1.52).
    5. Add a cylinder cork with a wood-colored material.
    6. Print the measured height and maximum diameter next to the reference values.

The script is idempotent: it removes the ``BottleBody`` and ``Cork`` objects it created
on a previous run before rebuilding them. It does not touch any other scene object.
Scene units: 1 Blender unit = 1 m; dimensions below are in cm and scaled by ``S``.
"""

import math

import bmesh
import bpy

S = 0.01  # cm → metros

# ================================================================
# LIMPIAR ESCENA
# ================================================================
for obj in list(bpy.context.scene.objects):
    if obj.name in ("BottleBody", "Cork"):
        bpy.data.objects.remove(obj, do_unlink=True)
for b in list(bpy.data.meshes):
    if b.users == 0:
        bpy.data.meshes.remove(b)

# ================================================================
# PERFIL — basado en la especificación de CLAUDE.md:
#   plano técnico  → dimensiones exactas
#   forma          → cónica, hombro suave
#   relieve        → surcos en tercio inferior
#
# Secciones (r en cm, z en cm desde base):
#   PIE        Z=0.0→0.5   r=3.0          (base plana, 6cm Ø)
#   PIE→CUERPO Z=0.5→2.5   r=3.0→4.5     (transición curva suave)
#   CUERPO     Z=2.5→21.2  r=4.5→2.5     (cono lineal)
#   HOMBRO     Z=21.2→22.7 r=2.5→1.25    (curva cóncava suave)
#   CUELLO     Z=22.7→27.7 r=1.25         (cilindro, 5cm)
#   COLLARÍN   Z=27.7→28.0 r=1.25→1.0    (asiento corcho)
# ================================================================

TAU = 2.0 * math.pi

profile = []

# PIE PLANO
profile.append((3.0, 0.0))
profile.append((3.0, 0.5))

# TRANSICIÓN PIE → CUERPO (curva suave coseno: 0.5 → 2.5cm)
N_foot = 6
for i in range(1, N_foot + 1):
    t = i / N_foot
    ez = (1.0 - math.cos(t * math.pi)) / 2.0  # ease 0→1
    z = 0.5 + 2.0 * t  # Z = 0.5 → 2.5
    r = 3.0 + (4.5 - 3.0) * ez
    profile.append((round(r, 4), round(z, 4)))


# CUERPO PRINCIPAL — taper lineal r=4.5→2.5 (Z=2.5→21.2)
# Zona relieve Z=2.5-11cm: punto cada 0.5cm para suavidad
def r_body(z):
    return 4.5 + (2.5 - 4.5) / (21.2 - 2.5) * (z - 2.5)


z = 3.0
while z <= 11.0 + 0.01:
    profile.append((round(r_body(z), 4), round(z, 4)))
    z = round(z + 0.5, 4)

# Zona superior Z=12-21.2: puntos cada 1.5cm
for z in [12.5, 14.0, 15.5, 17.0, 18.5, 20.0, 21.2]:
    profile.append((round(r_body(z), 4), z))

# HOMBRO — curva cóncava suave de r=2.5 → r=1.25 en 1.5cm
# ease = sin(t*π/2)^1.5 → concave (más rápido al inicio)
N_sh = 6
for i in range(1, N_sh + 1):
    t = i / N_sh
    ez = math.sin(t * math.pi / 2.0) ** 1.5
    z = 21.2 + 1.5 * t
    r = 2.5 + (1.25 - 2.5) * ez
    profile.append((round(r, 4), round(z, 4)))

# CUELLO (cilindro recto, 5cm altura)
profile.append((1.25, 27.7))

# COLLARÍN / ASIENTO CORCHO
profile.append((1.1, 27.85))
profile.append((1.0, 28.0))

# ================================================================
# MALLA POR REVOLUCIÓN (N=360, 1° por segmento)
# ================================================================
N = 360
bm = bmesh.new()
v_bot = bm.verts.new((0.0, 0.0, 0.0))
v_top = bm.verts.new((0.0, 0.0, profile[-1][1] * S))

rings = []
for seg in range(N):
    angle = (seg / N) * TAU
    ca, sa = math.cos(angle), math.sin(angle)
    ring = [bm.verts.new((r * S * ca, r * S * sa, z * S)) for r, z in profile]
    rings.append(ring)

for i in range(N):
    ni = (i + 1) % N
    bm.faces.new([v_bot, rings[i][0], rings[ni][0]])

P = len(profile)
for p in range(P - 1):
    for i in range(N):
        ni = (i + 1) % N
        bm.faces.new([rings[i][p], rings[ni][p], rings[ni][p + 1], rings[i][p + 1]])

for i in range(N):
    ni = (i + 1) % N
    bm.faces.new([v_top, rings[ni][-1], rings[i][-1]])

mesh = bpy.data.meshes.new("Bottle")
bm.to_mesh(mesh)
bm.free()
mesh.update()

bottle = bpy.data.objects.new("BottleBody", mesh)
bpy.context.scene.collection.objects.link(bottle)
print("Perfil: " + str(len(profile)) + " pts | " + str(len(mesh.vertices)) + " verts")

# ================================================================
# RELIEVE DE AGAVE
# Ref: relieve — líneas en S diagonales (abajo-izq → arriba-der)
#      alrededor de TODA la botella 360°, tercio inferior del cuerpo
#
#   N_LEAVES = 8   → 45° spacing, sin solapamiento
#   TWIST    = 28° → inclinación diagonal
#   WAVE     = 14° → S-curve orgánica pronunciada
#   TWIST+WAVE = 42° < 45° spacing → OK sin solapamiento
#   HA       = 5°  → surcos moderados
#   MAX_D    = 5mm → profundidad visible en render
#   Z_MIN    = 2.5cm, Z_MAX = 11cm (tercio inferior)
# ================================================================
N_LEAVES = 8
Z_MIN = 0.025  # 2.5cm desde base
Z_MAX = 0.110  # 11.0cm
MAX_D = 0.005  # 5mm profundidad
TWIST = math.radians(28)
WAVE = math.radians(14)
HA = math.radians(5)

base_angles = [k * TAU / N_LEAVES for k in range(N_LEAVES)]


def h_fac(t: float) -> float:
    """Depth factor along a groove, tapering over the first and last 10%.

    Línea continua con taper 10% en puntas para evitar corte brusco.

    Args:
        t: Normalized height inside the groove band, from 0.0 (bottom) to 1.0 (top).

    Returns:
        Multiplier for the groove depth: 1.0 in the middle, falling to 0.0 at both
        ends with a square-root curve.
    """
    edge = 0.10
    if t < edge:
        return (t / edge) ** 0.5
    elif t > 1.0 - edge:
        return ((1.0 - t) / edge) ** 0.5
    return 1.0


def a_fac(d: float, ha: float) -> float:
    """Cross-section factor of a groove at a given angular offset.

    Sección transversal coseno^2: perfil suave y redondeado.

    Args:
        d: Angular distance in radians from the groove centerline (sign ignored).
        ha: Half-width of the groove in radians.

    Returns:
        Cosine-squared falloff: 1.0 on the centerline, 0.0 at ``|d| >= ha``.
    """
    a = abs(d)
    if a >= ha:
        return 0.0
    return ((1.0 + math.cos((a / ha) * math.pi)) * 0.5) ** 2.0


modified = 0
for vert in mesh.vertices:
    x, y, z = vert.co
    if z < Z_MIN - 0.002 or z > Z_MAX + 0.002:
        continue
    r = math.sqrt(x * x + y * y)
    if r < 0.002:
        continue
    theta = math.atan2(y, x)
    zn = max(0.0, min(1.0, (z - Z_MIN) / (Z_MAX - Z_MIN)))

    # S-CURVE completa: sin(zn*2π) hace un ciclo completo S
    tz = TWIST * zn + WAVE * math.sin(zn * TAU)
    depth = MAX_D * h_fac(zn)

    mx = 0.0
    for la in base_angles:
        d = theta - (la + tz)
        d = (d + math.pi) % TAU - math.pi
        inf = a_fac(d, HA)
        if inf > mx:
            mx = inf

    if mx > 0.0001:
        disp = depth * mx
        ir = 1.0 / r
        vert.co.x -= x * ir * disp
        vert.co.y -= y * ir * disp
        modified += 1

mesh.update()
print("Surcos desplazados: " + str(modified) + " verts")

# ================================================================
# NORMALES + SHADING SUAVE
# ================================================================
bpy.context.view_layer.objects.active = bottle
bottle.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.shade_smooth()

# ================================================================
# MATERIAL VIDRIO — IOR 1.52, tinte azul-verde
# ================================================================
mat = bpy.data.materials.get("GlassBottle")
if not mat:
    mat = bpy.data.materials.new("GlassBottle")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
glass = nt.nodes.new("ShaderNodeBsdfGlass")
glass.inputs["Color"].default_value = (0.87, 0.96, 0.93, 1.0)
glass.inputs["IOR"].default_value = 1.52
glass.inputs["Roughness"].default_value = 0.0
out.location = (300, 0)
glass.location = (0, 0)
nt.links.new(glass.outputs["BSDF"], out.inputs["Surface"])
mat.use_screen_refraction = True
bottle.data.materials.clear()
bottle.data.materials.append(mat)

# ================================================================
# CORCHO — r=2.0cm, h=1.5cm, sobre la apertura
# ================================================================
bpy.ops.mesh.primitive_cylinder_add(
    radius=2.0 * S, depth=1.5 * S, vertices=64, location=(0, 0, (28.0 + 0.75) * S)
)
cork = bpy.context.active_object
cork.name = "Cork"
for obj in bpy.context.scene.objects:
    obj.select_set(False)

cork_mat = bpy.data.materials.get("CorkWood")
if not cork_mat:
    cork_mat = bpy.data.materials.new("CorkWood")
cork_mat.use_nodes = True
nk = cork_mat.node_tree
nk.nodes.clear()
out_k = nk.nodes.new("ShaderNodeOutputMaterial")
diff_k = nk.nodes.new("ShaderNodeBsdfPrincipled")
diff_k.inputs["Base Color"].default_value = (0.52, 0.34, 0.14, 1.0)
diff_k.inputs["Roughness"].default_value = 0.65
out_k.location = (300, 0)
diff_k.location = (0, 0)
nk.links.new(diff_k.outputs["BSDF"], out_k.inputs["Surface"])
cork.data.materials.clear()
cork.data.materials.append(cork_mat)

# ================================================================
# VERIFICACIÓN
# ================================================================
bb = bottle.bound_box
h_cm = (max(v[2] for v in bb) - min(v[2] for v in bb)) * 100
d_cm = max(abs(v[0]) for v in bb) * 200
print("=== VERIFICACIÓN ===")
print("  Altura vidrio: " + str(round(h_cm, 1)) + "cm  (ref: 28cm)")
print("  Diámetro max:  " + str(round(d_cm, 1)) + "cm  (ref: 9cm)")
print(
    "  Surcos: "
    + str(N_LEAVES)
    + " | TWIST="
    + str(round(math.degrees(TWIST)))
    + "° WAVE="
    + str(round(math.degrees(WAVE)))
    + "° HA="
    + str(round(math.degrees(HA)))
    + "°"
)
print(
    "  Zona relieve: Z="
    + str(round(Z_MIN * 100, 1))
    + "-"
    + str(round(Z_MAX * 100, 1))
    + "cm"
)
