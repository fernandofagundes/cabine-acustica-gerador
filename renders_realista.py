"""
Render realista (Cycles) do abrigo do gerador: ceu fisico, piso de concreto,
madeira com veio e verniz, la e tela com relevo. Nao altera o .blend.

  blender --background casa_gerador.blend --python renders_realista.py -- \
      --portas abertas|fechadas [--teste] [--quadros 480] [--de 0 --ate 480]
      [--amostras 64] [--cpu]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(nome, padrao=None):
    return args[args.index(nome) + 1] if nome in args else padrao


BASE = os.path.dirname(os.path.abspath(bpy.data.filepath))
scene = bpy.context.scene
cam = scene.camera
ALVO = Vector((1.0, 0.8, 1.02))
MODO = arg("--portas", "abertas")
ABERTA = 105.0

# ---------------------------------------------------------------- motor
scene.render.engine = 'CYCLES'
scene.cycles.samples = int(arg("--amostras", "64"))
scene.cycles.use_denoising = True
scene.cycles.use_adaptive_sampling = True
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
dispositivo = "CPU"
if "--cpu" not in args:
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for tipo in ("OPTIX", "CUDA", "HIP", "ONEAPI"):
            try:
                prefs.compute_device_type = tipo
            except TypeError:
                continue
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type == tipo]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type == tipo
                scene.cycles.device = 'GPU'
                dispositivo = tipo + ": " + gpus[0].name
                break
    except Exception as e:
        print("GPU indisponivel:", e)
print("Dispositivo de render:", dispositivo)


# ---------------------------------------------------------------- nos
def principled(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def no(mat, tipo, **props):
    n = mat.node_tree.nodes.new(tipo)
    for k, v in props.items():
        setattr(n, k, v)
    return n


def liga(mat, a, b):
    mat.node_tree.links.new(a, b)


def entrada(n, *nomes):
    for nome in nomes:
        if nome in n.inputs:
            return n.inputs[nome]
    return None


def coordenadas(mat, escala):
    tc = no(mat, "ShaderNodeTexCoord")
    mp = no(mat, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = escala
    liga(mat, tc.outputs["Object"], mp.inputs["Vector"])
    return mp.outputs["Vector"]


def relevo(mat, altura, forca, normal=None):
    bp = no(mat, "ShaderNodeBump")
    bp.inputs["Strength"].default_value = forca
    liga(mat, altura, bp.inputs["Height"])
    if normal is not None:
        liga(mat, normal, bp.inputs["Normal"])
    return bp.outputs["Normal"]


def rampa(mat, fator, cores):
    cr = no(mat, "ShaderNodeValToRGB")
    els = cr.color_ramp.elements
    while len(els) < len(cores):
        els.new(0.5)
    for el, (pos, cor) in zip(els, cores):
        el.position = pos
        el.color = (*cor, 1.0)
    liga(mat, fator, cr.inputs["Fac"])
    return cr.outputs["Color"]


# Compensado naval envernizado: veio alongado + quinas levemente arredondadas
m = bpy.data.materials.get("Compensado_Naval")
if m:
    b = principled(m)
    veio = no(m, "ShaderNodeTexNoise")
    veio.inputs["Scale"].default_value = 4.0
    veio.inputs["Detail"].default_value = 8.0
    veio.inputs["Roughness"].default_value = 0.65
    liga(m, coordenadas(m, (26.0, 26.0, 1.3)), veio.inputs["Vector"])
    cor = rampa(m, veio.outputs["Fac"], [
        (0.30, (0.33, 0.19, 0.08)), (0.52, (0.52, 0.33, 0.15)),
        (0.75, (0.66, 0.46, 0.23))])
    liga(m, cor, b.inputs["Base Color"])
    fino = no(m, "ShaderNodeTexNoise")
    fino.inputs["Scale"].default_value = 60.0
    fino.inputs["Detail"].default_value = 4.0
    liga(m, coordenadas(m, (40.0, 40.0, 3.0)), fino.inputs["Vector"])
    bev = no(m, "ShaderNodeBevel")
    bev.inputs["Radius"].default_value = 0.0025
    liga(m, relevo(m, fino.outputs["Fac"], 0.12, bev.outputs["Normal"]),
         b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.42
    c = entrada(b, "Coat Weight", "Clearcoat")
    if c:
        c.default_value = 0.35
    c = entrada(b, "Coat Roughness", "Clearcoat Roughness")
    if c:
        c.default_value = 0.25

# La de rocha: fibrosa, com relevo
m = bpy.data.materials.get("La_De_Rocha")
if m:
    b = principled(m)
    nz = no(m, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 180.0
    nz.inputs["Detail"].default_value = 6.0
    liga(m, coordenadas(m, (1.0, 1.0, 1.0)), nz.inputs["Vector"])
    liga(m, rampa(m, nz.outputs["Fac"], [(0.3, (0.36, 0.33, 0.12)),
                                         (0.7, (0.58, 0.54, 0.22))]),
         b.inputs["Base Color"])
    liga(m, relevo(m, nz.outputs["Fac"], 0.6), b.inputs["Normal"])

# Tela perfurada: chapa galvanizada com furos em relevo
m = bpy.data.materials.get("Tela_Perfurada")
if m:
    b = principled(m)
    vo = no(m, "ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 70.0
    if "Randomness" in vo.inputs:
        vo.inputs["Randomness"].default_value = 0.0   # furos em grade regular
    liga(m, coordenadas(m, (1.0, 1.0, 1.0)), vo.inputs["Vector"])
    furo = rampa(m, vo.outputs["Distance"], [(0.25, (0.0, 0.0, 0.0)),
                                             (0.36, (1.0, 1.0, 1.0))])
    mix = rampa(m, vo.outputs["Distance"], [(0.25, (0.20, 0.20, 0.19)),
                                            (0.36, (0.60, 0.62, 0.64))])
    liga(m, mix, b.inputs["Base Color"])
    liga(m, relevo(m, furo, 0.3), b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.42
    b.inputs["Metallic"].default_value = 0.8

# ---------------------------------------------------------------- cenario
for nome in ("Sol", "Luz_Area", "Piso"):
    o = bpy.data.objects.get(nome)
    if o:
        o.hide_render = True
# Setas de fluxo ficam fora do video realista
for o in bpy.data.objects:
    if o.name.startswith("Fluxo_"):
        o.hide_render = True
        o.hide_viewport = True


def plano(nome, x0, x1, y0, y1, z, mat):
    me = bpy.data.meshes.new(nome)
    me.from_pydata([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [],
                   [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(nome, me)
    me.materials.append(mat)
    scene.collection.objects.link(ob)
    return ob


def novo_material(nome):
    mat = bpy.data.materials.new(nome)
    if mat.node_tree is None:
        mat.use_nodes = True
    return mat


m = novo_material("Concreto_Calcada")
b = principled(m)
nz = no(m, "ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 7.0
nz.inputs["Detail"].default_value = 10.0
nz.inputs["Roughness"].default_value = 0.7
liga(m, coordenadas(m, (1.0, 1.0, 1.0)), nz.inputs["Vector"])
liga(m, rampa(m, nz.outputs["Fac"], [(0.3, (0.36, 0.36, 0.35)),
                                     (0.7, (0.56, 0.55, 0.53))]),
     b.inputs["Base Color"])
gr = no(m, "ShaderNodeTexNoise")
gr.inputs["Scale"].default_value = 260.0
liga(m, coordenadas(m, (1.0, 1.0, 1.0)), gr.inputs["Vector"])
liga(m, relevo(m, gr.outputs["Fac"], 0.35), b.inputs["Normal"])
b.inputs["Roughness"].default_value = 0.85
plano("Calcada", -1.6, 3.6, -1.4, 4.0, 0.0, m)

m = novo_material("Gramado")
b = principled(m)
nz = no(m, "ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 3.0
nz.inputs["Detail"].default_value = 12.0
nz.inputs["Roughness"].default_value = 0.8
liga(m, coordenadas(m, (1.0, 1.0, 1.0)), nz.inputs["Vector"])
liga(m, rampa(m, nz.outputs["Fac"], [(0.3, (0.05, 0.11, 0.03)),
                                     (0.7, (0.16, 0.25, 0.07))]),
     b.inputs["Base Color"])
gr = no(m, "ShaderNodeTexNoise")
gr.inputs["Scale"].default_value = 500.0
liga(m, coordenadas(m, (1.0, 1.0, 1.0)), gr.inputs["Vector"])
liga(m, relevo(m, gr.outputs["Fac"], 1.0), b.inputs["Normal"])
b.inputs["Roughness"].default_value = 0.95
plano("Gramado", -60, 60, -60, 60, -0.03, m)

# Ceu fisico com sol
mundo = scene.world
nt = mundo.node_tree
bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
ceu = nt.nodes.new("ShaderNodeTexSky")
tipos = [i.identifier for i in
         ceu.bl_rna.properties["sky_type"].enum_items]
for t in ("MULTIPLE_SCATTERING", "NISHITA", "SINGLE_SCATTERING"):
    if t in tipos:
        ceu.sky_type = t
        break
for prop, val in (("sun_elevation", math.radians(42.0)),
                  ("sun_rotation", math.radians(40.0)),
                  ("sun_size", math.radians(1.2)),
                  ("sun_intensity", 0.6)):
    try:
        setattr(ceu, prop, val)
    except Exception:
        pass
nt.links.new(ceu.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = float(arg("--ceu", "0.12"))
print("Ceu:", ceu.sky_type, "de", tipos)

# ---------------------------------------------------------------- portas
piv_e = bpy.data.objects["Porta_Pivo_Esquerdo"]
piv_d = bpy.data.objects["Porta_Pivo_Direito"]
ang = ABERTA if MODO == "abertas" else 0.0
piv_e.rotation_euler = (0, 0, math.radians(ang))
piv_d.rotation_euler = (0, 0, math.radians(-ang))


def camera(i, n, raio=6.4, altura=2.3):
    a = math.radians(70.0) + 2 * math.pi * i / n
    cam.location = (ALVO.x + raio * math.cos(a), ALVO.y + raio * math.sin(a),
                    altura)
    cam.data.lens = 35
    cam.rotation_euler = (ALVO - cam.location).to_track_quat(
        '-Z', 'Y').to_euler()


n = int(arg("--quadros", "480"))
if "--teste" in args:
    pasta = os.path.join(BASE, "renders", "realista_teste")
    os.makedirs(pasta, exist_ok=True)
    for i in (0,):
        camera(i, n)
        scene.render.filepath = os.path.join(pasta, f"{MODO}_{i:04d}.png")
        bpy.ops.render.render(write_still=True)
else:
    pasta = os.path.join(BASE, "renders", "realista_" + MODO)
    os.makedirs(pasta, exist_ok=True)
    for i in range(int(arg("--de", "0")), int(arg("--ate", str(n)))):
        caminho = os.path.join(pasta, f"q_{i:04d}.png")
        if os.path.exists(caminho):
            continue
        camera(i, n)
        scene.render.filepath = caminho
        bpy.ops.render.render(write_still=True)

print("renders_realista concluido")
