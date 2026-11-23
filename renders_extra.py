"""
Imagens e quadros de video do abrigo do gerador, a partir de casa_gerador.blend.

  blender --background casa_gerador.blend --python renders_extra.py -- \
      [--imagens] [--video aberto|fechado] [--quadros 192]

Nao altera o .blend: so muda a cena em memoria para renderizar.
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
ALVO = Vector((1.0, 0.8, 1.06))
ABERTA = 105.0                      # graus, portas bem abertas

piv_e = bpy.data.objects["Porta_Pivo_Esquerdo"]
piv_d = bpy.data.objects["Porta_Pivo_Direito"]
porta = list(piv_e.children_recursive) + list(piv_d.children_recursive)
tampa = [o for o in bpy.data.objects if o.name.startswith(
    ("Capuz_Tampa", "La_Capuz_Teto", "Tela_Capuz_Teto"))]

# Luz de preenchimento para as vistas de tras e de lado
for nome, pos, energia in (("Sol_Fundo", (4, -5, 6), 1.0),
                           ("Sol_Lado", (7, 3, 5), 0.6)):
    luz = bpy.data.objects.new(nome, bpy.data.lights.new(nome, 'SUN'))
    luz.data.energy = energia
    luz.location = pos
    luz.rotation_euler = (ALVO - luz.location).to_track_quat(
        '-Z', 'Y').to_euler()
    scene.collection.objects.link(luz)


def portas(estado):
    """'abertas', 'fechadas' ou 'sem' (ocultas)."""
    ang = ABERTA if estado == "abertas" else 0.0
    piv_e.rotation_euler = (0, 0, math.radians(ang))
    piv_d.rotation_euler = (0, 0, math.radians(-ang))
    for o in porta:
        o.hide_render = estado == "sem"


def camera(pos, alvo=ALVO, lente=40, up='Y'):
    cam.location = pos
    cam.data.lens = lente
    cam.rotation_euler = (Vector(alvo) - cam.location).to_track_quat(
        '-Z', up).to_euler()


def render(caminho):
    scene.render.filepath = caminho
    bpy.ops.render.render(write_still=True)


if "--imagens" in args:
    pasta = os.path.join(BASE, "renders", "vistas")
    os.makedirs(pasta, exist_ok=True)
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1200
    FRENTE = (1.0, 8.6, 1.25)
    LAT_FRIO = (7.2, 4.6, 2.3)      # lado da entrada de ar frio (esq. de quem olha)
    LAT_QUENTE = (-5.2, 4.6, 2.3)   # lado do escapamento e da saida quente
    vistas = [
        ("01_frente_portas_fechadas", "fechadas", FRENTE, 50),
        ("02_frente_sem_portas", "sem", FRENTE, 50),
        ("03_lateral_entrada_ar_frio_com_portas", "fechadas", LAT_FRIO, 50),
        ("04_lateral_entrada_ar_frio_sem_portas", "sem", LAT_FRIO, 50),
        ("05_lateral_saida_ar_quente_com_portas", "fechadas", LAT_QUENTE, 50),
        ("06_lateral_saida_ar_quente_sem_portas", "sem", LAT_QUENTE, 50),
    ]
    for nome, estado, pos, lente in vistas:
        portas(estado)
        camera(pos, lente=lente)
        render(os.path.join(pasta, nome + ".png"))

    # Vistas de topo, portas abertas (com a tampa e sem a tampa do capuz)
    portas("abertas")
    camera((1.0, 1.25, 9.5), alvo=(1.0, 1.25, 0.0), lente=50)
    cam.rotation_euler = (0, 0, math.pi)     # frente (portas) para baixo
    render(os.path.join(pasta, "07_topo_portas_abertas.png"))
    for o in tampa:
        o.hide_render = True
    render(os.path.join(pasta, "08_topo_portas_abertas_sem_tampa.png"))
    for o in tampa:
        o.hide_render = False

modo = arg("--video")
if modo:
    n = int(arg("--quadros", "192"))
    pasta = os.path.join(BASE, "renders", "video_" + modo)
    os.makedirs(pasta, exist_ok=True)
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    portas("abertas" if modo == "aberto" else "fechadas")
    raio, altura = 6.6, 2.7
    for i in range(n):
        a = math.radians(90.0) + 2 * math.pi * i / n   # comeca de frente
        camera((ALVO.x + raio * math.cos(a), ALVO.y + raio * math.sin(a),
                altura), lente=35)
        render(os.path.join(pasta, f"q_{i:04d}.png"))

print("renders_extra concluido")
