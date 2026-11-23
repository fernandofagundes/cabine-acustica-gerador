"""
Cabine acustica ventilada para gerador Toyama TG8000CXER (7,2 kVA, 420 cc).

Unidades: metros. Origem no canto inferior traseiro esquerdo, no nivel do piso.
X = comprimento  (0..2.000)  X = 0: escapamento, exaustores e saida quente
                             X = 2: labirinto de entrada de ar frio
                             (de frente para as portas, X = 2 fica a ESQUERDA
                             e X = 0 a DIREITA de quem olha)
Y = profundidade (0..1.600)  0 = traseira, 1.600 = frente (portas duplas)
Z = altura       (0..2.120)

Revestimento acustico: 50 mm no total (48 mm de la de rocha + 2 mm de tela).
Vao interno livre em Y: 1.464 (0.068..1.532). Piso sem revestimento.

Uso dentro do Blender: abrir no editor de texto e executar (apaga a cena atual).
Uso headless:
  blender --background --factory-startup --python casa_gerador.py -- \
      --save casa_gerador.blend --render renders \
      --dados Especificações/dados_construcao.json [--engine CYCLES]
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

T = 0.018          # compensado naval
CH = 0.002         # tela perfurada
REV = 0.050        # revestimento total (la + tela)
LA = REV - CH
ABERTURA_FOLHA_ESQ = 15.0     # graus (0 = fechada)
ABERTURA_FOLHA_DIR = -35.0

# Envelope externo
LX, LY = 2.000, 1.600
Z_PE = 0.080                           # pes de borracha
Z_BASE0, Z_BASE1 = Z_PE, Z_PE + T      # 0.080 / 0.098
Z_TETO0, Z_TETO1 = 1.764, 1.782        # teto da camara principal
Z_TAMPA0, Z_TAMPA1 = 2.102, 2.120      # tampa do capuz
Y_FR = LY - T                          # 1.582 plano interno da frente

# Faces livres (apos revestimento)
ZP = Z_BASE1                           # piso sem revestimento
ZT = Z_TETO0 - REV                     # 1.714
YT = T + REV                           # 0.068
YF = Y_FR - REV                        # 1.532 face do revestimento das portas
YL = Y_FR - 0.030                      # 1.552 limite junto ao batente
XE, XD = T + REV, LX - T - REV         # 0.068 / 1.932
ZCT = Z_TAMPA0 - REV                   # 2.052 face livre do teto do capuz

# Labirinto de entrada de ar frio (X alto: esquerda de quem olha de frente)
ENTRADA = (0.250, 1.350, 0.150, 0.550)  # veneziana (y0, y1, z0, z1)
X_DIV, Z_DIV = 1.618, 1.500             # divisoria: compensado em X_DIV..+T
DV0, DV1 = X_DIV - REV, X_DIV + T + REV  # 1.568 / 1.686 faces do sanduiche

# Exaustores e labirinto em "S" do capuz
FAN_XY = [(0.850, 0.500), (0.850, 1.100)]
X_CH1, Z_CH1 = 0.532, 1.920            # chicana 1 desce do teto ate Z_CH1
X_CH2, Z_CH2 = 0.262, 1.980            # chicana 2 sobe do piso ate Z_CH2
SAIDA = (0.150, 1.450, 1.830, 2.050)   # veneziana de saida (y0, y1, z0, z1)

# Gerador: envelope 0.82 x 0.68 x 0.65
GX, GY, GZ = 0.318, 0.220, Z_BASE1 + 0.020
EY, EZ = GY + 0.34, 0.450              # eixo do escapamento na parede X = 0

# ----------------------------------------------------------------------------
# Cena limpa
# ----------------------------------------------------------------------------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
              bpy.data.lights, bpy.data.cameras):
    for d in list(block):
        if d.users == 0:
            block.remove(d)

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0


def colecao(nome):
    c = bpy.data.collections.new(nome)
    scene.collection.children.link(c)
    return c


C_CENA = colecao("00_Cena")
C_MAD = colecao("01_Estrutura_Madeira")
C_TAMPA = colecao("01B_Tampas_Corte")
C_ISO = colecao("02_Isolamento_Acustico")
C_VENT = colecao("03_Ventilacao_Escapamento")
C_GER = colecao("04_Gerador_Base_Iluminacao")
C_FIX = colecao("05_Fixacao_Parafusos")


# ----------------------------------------------------------------------------
# Materiais
# ----------------------------------------------------------------------------
def hexcor(h):
    """#RRGGBB (sRGB) -> RGB linear."""
    h = h.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def material(nome, cor, rough=0.5, metal=0.0, emissao=0.0):
    m = bpy.data.materials.new(nome)
    if m.node_tree is None:
        m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rgba = (cor[0], cor[1], cor[2], 1.0)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emissao > 0:
        em = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if em is not None:
            em.default_value = rgba
        st = bsdf.inputs.get("Emission Strength")
        if st is not None:
            st.default_value = emissao
    m.diffuse_color = rgba
    return m


M_MAD = material("Compensado_Naval", (0.62, 0.45, 0.24), 0.55)
M_LA = material("La_De_Rocha", (0.55, 0.52, 0.18), 0.95)
M_TELA = material("Tela_Perfurada", (0.70, 0.71, 0.72), 0.35, 0.85)
M_EPDM = material("Borracha_EPDM", (0.015, 0.015, 0.015), 0.85)
M_ACO = material("Aco_Escapamento", (0.55, 0.55, 0.56), 0.30, 0.90)
M_CERAM = material("Fibra_Ceramica", (0.90, 0.88, 0.82), 0.95)
M_LED = material("LED_12V", (1.0, 0.97, 0.90), 0.3, 0.0, 3.0)
M_VENT = material("Exaustor_Carcaca", (0.08, 0.08, 0.09), 0.5, 0.5)
M_PISO = material("Piso_Cena", (0.55, 0.55, 0.55), 0.9)
# Gerador
M_QUADRO = material("Quadro_Preto_Fosco", hexcor("#111111"), 0.45, 0.6)
M_TOYAMA = material("Vermelho_Toyama", hexcor("#C8102E"), 0.25, 0.3)
M_ALUM = material("Aluminio_Fundido", hexcor("#9EA2A5"), 0.35, 0.85)
M_ESCOV = material("Aluminio_Escovado", (0.75, 0.76, 0.77), 0.25, 0.95)
M_CROMO = material("Cromado", (0.85, 0.85, 0.86), 0.12, 1.0)
M_PLAST = material("Plastico_Preto", (0.02, 0.02, 0.02), 0.55)
M_CINZA = material("Painel_Cinza_Escuro", (0.10, 0.10, 0.11), 0.5)
M_ETIQ = material("Painel_Etiqueta", (0.85, 0.85, 0.82), 0.6)
M_DISPLAY = material("Painel_Display", (0.15, 0.55, 0.35), 0.3, 0.0, 0.8)
M_TOM_AZUL = material("Tomada_Industrial_Azul", hexcor("#0055CC"), 0.4)
M_BORNE_V = material("Borne_Vermelho", (0.8, 0.02, 0.02), 0.4)


# ----------------------------------------------------------------------------
# Primitivas
# ----------------------------------------------------------------------------
def _obj(nome, bm, mat, col, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nome, me)
    ob.location = loc
    if mat is not None:
        me.materials.append(mat)
    (col.objects if col is not None else scene.collection.objects).link(ob)
    return ob


def caixa(nome, x0, x1, y0, y1, z0, z1, mat, col):
    """Caixa definida pelos limites em coordenadas do mundo."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=bm.verts)
    return _obj(nome, bm, mat, col,
                ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def cilindro(nome, centro, raio, comprimento, eixo, mat, col, seg=48):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=raio,
                          radius2=raio, depth=comprimento)
    if eixo == 'X':
        bmesh.ops.rotate(bm, verts=bm.verts,
                         matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
    elif eixo == 'Y':
        bmesh.ops.rotate(bm, verts=bm.verts,
                         matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
    ob = _obj(nome, bm, mat, col, centro)
    for p in ob.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    return ob


def recortar(ob, cortador):
    """Subtrai `cortador` de `ob` (booleana aplicada) e remove o cortador."""
    mod = ob.modifiers.new("corte", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cortador
    try:
        mod.solver = 'EXACT'
    except TypeError:
        pass
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    nova = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    velha = ob.data
    ob.data = nova
    nova.name = velha.name
    bpy.data.meshes.remove(velha)
    me = cortador.data
    bpy.data.objects.remove(cortador, do_unlink=True)
    bpy.data.meshes.remove(me)
    return ob


def revestimento(nome, x0, x1, y0, y1, z0, z1, eixo, lado):
    """La de rocha + tela perfurada (2 mm) dentro da caixa dada.
    `lado` = +1 se o ar fica no sentido positivo do eixo, -1 no negativo."""
    lim = {'x': [x0, x1], 'y': [y0, y1], 'z': [z0, z1]}
    la = {k: list(v) for k, v in lim.items()}
    ch = {k: list(v) for k, v in lim.items()}
    a0, a1 = lim[eixo]
    if lado > 0:
        la[eixo] = [a0, a1 - CH]
        ch[eixo] = [a1 - CH, a1]
    else:
        la[eixo] = [a0 + CH, a1]
        ch[eixo] = [a0, a0 + CH]
    o1 = caixa("La_" + nome, *la['x'], *la['y'], *la['z'], M_LA, C_ISO)
    o2 = caixa("Tela_" + nome, *ch['x'], *ch['y'], *ch['z'], M_TELA, C_ISO)
    REVEST.append({"nome": nome, "eixo": eixo,
                   "bbox": [mm(v) for v in (x0, x1, y0, y1, z0, z1)]})
    return [o1, o2]


def recortar_todos(objs, fabrica_cortador):
    for o in objs:
        recortar(o, fabrica_cortador())


def tubo(nome, pontos, raio, mat, col, ciclico=False, suave=False):
    """Tubo ao longo de uma lista de pontos (curva com bevel)."""
    cu = bpy.data.curves.new(nome, 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('NURBS' if suave else 'POLY')
    sp.points.add(len(pontos) - 1)
    for p, co in zip(sp.points, pontos):
        p.co = (co[0], co[1], co[2], 1.0)
    if suave:
        sp.order_u = 3
        sp.use_endpoint_u = True
        cu.resolution_u = 16
    sp.use_cyclic_u = ciclico
    cu.bevel_depth = raio
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    cu.materials.append(mat)
    ob = bpy.data.objects.new(nome, cu)
    col.objects.link(ob)
    return ob


# ----------------------------------------------------------------------------
# Registro de pecas, revestimentos e parafusos (usado pelos desenhos tecnicos)
# ----------------------------------------------------------------------------
PECAS, PARAFUSOS, REVEST = [], [], []
SR = 0.040                              # sarrafo de madeira macica 40 x 40
Z_EM = 1.658                            # emenda horizontal da parede traseira
BEIRAL = 0.100                          # beiral da tampa sobre as venezianas
M_SAR = material("Sarrafo_Madeira_Macica", (0.42, 0.25, 0.10), 0.65)
M_PARAF = material("Parafuso_Inox", (0.85, 0.85, 0.87), 0.25, 1.0)
P30, P40, P50 = "4,0 x 30", "4,5 x 40", "4,5 x 50"
P70, P80, PTAMPA = "5,0 x 70", "5,0 x 80", "5,0 x 50 com arruela EPDM"


def mm(v):
    return round(v * 1000.0, 1)


def peca(nome, x0, x1, y0, y1, z0, z1, vista, tipo="compensado", col=None):
    """Cria a caixa e registra a peca. `vista` = lado de onde o desenho da
    peca e visto (+x, -x, +y, -y, +z, -z)."""
    mat = {"compensado": M_MAD, "borracha": M_EPDM}.get(tipo, M_SAR)
    ob = caixa(nome, x0, x1, y0, y1, z0, z1, mat, col or C_MAD)
    PECAS.append({"obj": nome, "tipo": tipo, "vista": vista, "recortes": [],
                  "bbox": [mm(v) for v in (x0, x1, y0, y1, z0, z1)]})
    return ob


def recorte(nome, forma, dados, nota):
    """Registra um recorte: forma 'ret' (bbox) ou 'circ' (centro + raio)."""
    p = next(p for p in PECAS if p["obj"] == nome)
    p["recortes"].append({"forma": forma, "dados": [mm(v) for v in dados],
                          "nota": nota})


def parafuso(tipo, obj, p, n, junta, passa=(), grupo=""):
    PARAFUSOS.append({"tipo": tipo, "obj": obj, "junta": junta,
                      "p": [round(c * 1000.0) for c in p], "n": list(n),
                      "passa": list(passa), "grupo": grupo})


def fila(tipo, obj, p0, p1, n, junta, passo=0.20, margem=0.05, passa=(),
         grupo=""):
    """Linha de parafusos entre p0 e p1 (pontos na face onde fica a cabeca),
    com `margem` nas pontas e espacamento maximo `passo`."""
    a, b = Vector(p0), Vector(p1)
    comp = (b - a).length
    util = comp - 2 * margem
    if util <= 0:
        pts = [(a + b) / 2]
    else:
        k = max(1, math.ceil(util / passo - 1e-6))
        pts = [a + (b - a) * ((margem + util * i / k) / comp)
               for i in range(k + 1)]
    for p in pts:
        parafuso(tipo, obj, p, n, junta, passa, grupo)


def cabecas_dos_parafusos():
    """Uma malha por grupo com a cabeca (9 mm) de todos os parafusos."""
    grupos = {}
    for s in PARAFUSOS:
        grupos.setdefault(s["grupo"], []).append(s)
    objs = {}
    for g, lista in grupos.items():
        bm = bmesh.new()
        for s in lista:
            nv = Vector(s["n"])
            pos = Vector(s["p"]) / 1000.0 + nv * 0.001
            bmesh.ops.create_cone(
                bm, cap_ends=True, segments=10, radius1=0.0045,
                radius2=0.0045, depth=0.002,
                matrix=(Matrix.Translation(pos)
                        @ nv.to_track_quat('Z', 'Y').to_matrix().to_4x4()))
        objs[g] = _obj("Parafusos" + ("_" + g if g else ""), bm, M_PARAF,
                       C_FIX)
    return objs


# ----------------------------------------------------------------------------
# 01 - Estrutura de madeira
# ----------------------------------------------------------------------------
# Apoio: 3 longarinas de madeira tratada 45 x 70 sobre calcos de borracha de
# 10 mm. As longarinas da frente e de tras ficam sob os sarrafos inferiores.
LONG_Y = [(0.015, 0.060), (LY / 2 - 0.0225, LY / 2 + 0.0225), (1.510, 1.555)]
n = 0
for i, (y0, y1) in enumerate(LONG_Y, 1):
    peca(f"Longarina_{i}", 0, LX, y0, y1, 0.010, Z_PE, '-z', "longarina")
    for px in (0.02, LX / 2 - 0.06, LX - 0.14):
        n += 1
        peca(f"Calco_Borracha_{n}", px, px + 0.12, (y0 + y1) / 2 - 0.03,
             (y0 + y1) / 2 + 0.03, 0, 0.010, '-z', "borracha")

peca("Base", 0, LX, 0, LY, Z_BASE0, Z_BASE1, '+z')
for yd in (0.40, 1.20):
    recorte("Base", "circ", (1.81, yd, Z_BASE1, 0.005), "dreno Ø10")

# Parede traseira em duas pecas (a chapa tem 1.600): a superior cobre o topo
# da camara e faz a parede de tras do capuz.
peca("Parede_Traseira_Inferior", 0, LX, 0, T, Z_BASE1, Z_EM, '-y')
peca("Parede_Traseira_Superior", 0, LX, 0, T, Z_EM, Z_TAMPA0, '-y')

p_x0 = peca("Parede_X0_Escapamento", 0, T, T, Y_FR, Z_BASE1, Z_TETO0, '-x')
recortar(p_x0, cilindro("c", (T / 2, EY, EZ), 0.075, 0.2, 'X', None, None))
recorte("Parede_X0_Escapamento", "circ", (0, EY, EZ, 0.075),
        "furo Ø150 da flange térmica")

p_x2 = peca("Parede_X2_Entrada", LX - T, LX, T, Y_FR, Z_BASE1, Z_TETO0, '+x')
recortar(p_x2, caixa("c", LX - 0.1, LX + 0.1, *ENTRADA, None, None))
recorte("Parede_X2_Entrada", "ret",
        (LX - T, LX, ENTRADA[0], ENTRADA[1], ENTRADA[2], ENTRADA[3]),
        "abertura da veneziana de entrada")

# Divisoria do labirinto de entrada (para em YF: as portas vedam contra ela)
peca("Divisoria_Labirinto_Entrada", X_DIV, X_DIV + T, T, YF, Z_BASE1, Z_DIV,
     '-x')

# Teto da camara: encosta por dentro na traseira superior
teto = peca("Teto_Camara", 0, LX, T, LY, Z_TETO0, Z_TETO1, '+z')
for fx, fy in FAN_XY:
    recortar(teto, cilindro("c", (fx, fy, Z_TETO0), 0.15, 0.2, 'Z', None,
                            None))
    recorte("Teto_Camara", "circ", (fx, fy, Z_TETO1, 0.15),
            "furo Ø300 do exaustor")

# --- Sarrafos 40 x 40 (ficam dentro da espessura do revestimento) -----------
XS0, XS1 = T + SR, LX - T - SR          # 0.058 / 1.942
YS0, YS1 = T + SR, YL - SR              # 0.058 / 1.512
XCA, XCB = T + SR / 2, LX - T - SR / 2  # eixos dos sarrafos junto as laterais
YCA, YCB = T + SR / 2, YL - SR / 2      # eixos junto a traseira / a frente
XDC0, XDC1 = X_DIV + T, X_DIV + T + SR  # sarrafos da divisoria (lado do duto)
YH1 = Y_FR - SR                         # 1.542 sarrafo frontal do capuz


def sar(nome, x0, x1, y0, y1, z0, z1):
    return peca("Sarrafo_" + nome, x0, x1, y0, y1, z0, z1, '+y', "sarrafo")


for nome, x0 in (("X0", T), ("X2", XS1)):
    sar(f"Vertical_Traseiro_{nome}", x0, x0 + SR, T, YS0, ZP, Z_TETO0)
    sar(f"Montante_Frontal_{nome}", x0, x0 + SR, YS1, YL, ZP, Z_TETO0)
    sar(f"Inferior_Lateral_{nome}", x0, x0 + SR, YS0, YS1, ZP, ZP + SR)
    sar(f"Superior_Lateral_{nome}", x0, x0 + SR, YS0, YS1, Z_TETO0 - SR,
        Z_TETO0)
for nome, y0 in (("Traseiro", T), ("Frontal", YS1)):
    sar(f"Inferior_{nome}_A", XS0, X_DIV, y0, y0 + SR, ZP, ZP + SR)
    sar(f"Inferior_{nome}_B", XDC1 if nome == "Traseiro" else XDC0, XS1, y0,
        y0 + SR, ZP, ZP + SR)
    sar(f"Superior_{nome}", XS0, XS1, y0, y0 + SR, Z_TETO0 - SR, Z_TETO0)
sar("Divisoria_Vertical", XDC0, XDC1, T, YS0, ZP, Z_DIV)
sar("Divisoria_Base", XDC0, XDC1, YS0, YS1, ZP, ZP + SR)
sar("Divisoria_Travessa", XDC0, LX - T, YS1 - SR, YS1, Z_DIV - SR, Z_DIV)

# Regua de emenda da traseira (compensado 18 x 100, por dentro)
peca("Regua_Emenda_Traseira", XS0, XS1, T, 2 * T, Z_EM - 0.05, Z_EM + 0.05,
     '+y')

# --- Portas duplas acusticas -------------------------------------------------
# Folhas no plano Y_FR..LY; batente por dentro, onde elas encostam
LF, PH = 0.936, 1.658                               # folha: largura x altura
PX0, PX1 = 0.060, LX - 0.060
PZ0 = (Z_BASE1 + Z_TETO0 - PH) / 2                  # 4 mm de folga
PZ1 = PZ0 + PH
BX0, BX1 = PX0 + 0.038, PX1 - 0.038
BZ0, BZ1 = Z_BASE1 + 0.060, Z_TETO0 - 0.060         # batentes de 60 mm
YB0, YB1 = YL, YL + T                               # batente (18 mm)
E = 0.012                                           # EPDM 12 x 12

# Guarnicao fixa ao lado das folhas, com calco de 12 mm ate o batente
peca("Guarnicao_Esquerda", 0, PX0, Y_FR, LY, Z_BASE1, Z_TETO0, '+y')
peca("Guarnicao_Direita", PX1, LX, Y_FR, LY, Z_BASE1, Z_TETO0, '+y')
peca("Calco_Guarnicao_Esquerda", T, XS0, YB1, Y_FR, Z_BASE1, Z_TETO0, '+y',
     "calco")
peca("Calco_Guarnicao_Direita", XS1, LX - T, YB1, Y_FR, Z_BASE1, Z_TETO0,
     '+y', "calco")

# Batente perimetral
peca("Batente_Inferior", T, LX - T, YB0, YB1, Z_BASE1, BZ0, '+y')
peca("Batente_Superior", T, LX - T, YB0, YB1, BZ1, Z_TETO0, '+y')
peca("Batente_Esquerdo", T, BX0, YB0, YB1, BZ0, BZ1, '+y')
peca("Batente_Direito", BX1, LX - T, YB0, YB1, BZ0, BZ1, '+y')
caixa("EPDM_Esquerdo", BX0 - E - 0.004, BX0 - 0.004, YB1, Y_FR, BZ0 - E,
      BZ1 + E, M_EPDM, C_MAD)
caixa("EPDM_Direito", BX1 + 0.004, BX1 + E + 0.004, YB1, Y_FR, BZ0 - E,
      BZ1 + E, M_EPDM, C_MAD)
caixa("EPDM_Inferior", BX0 - 0.004, BX1 + 0.004, YB1, Y_FR, BZ0 - E - 0.004,
      BZ0 - 0.004, M_EPDM, C_MAD)
caixa("EPDM_Superior", BX0 - 0.004, BX1 + 0.004, YB1, Y_FR, BZ1 + 0.004,
      BZ1 + E + 0.004, M_EPDM, C_MAD)

# Pingadeira em "L" acima do vao
caixa("Pingadeira_Aba", PX0 - 0.02, PX1 + 0.02, LY, LY + 0.030, PZ1 + 0.004,
      PZ1 + 0.007, M_ESCOV, C_MAD)
caixa("Pingadeira_Costas", PX0 - 0.02, PX1 + 0.02, LY, LY + 0.003,
      PZ1 + 0.007, PZ1 + 0.029, M_ESCOV, C_MAD)

XFE, XFD = PX0 + LF, PX1 - LF           # bordas centrais das folhas
folha_esq = [peca("Porta_Folha_Esquerda_Passiva", PX0, XFE, Y_FR, LY, PZ0,
                  PZ1, '+y')]
folha_dir = [peca("Porta_Folha_Direita_Ativa", XFD, PX1, Y_FR, LY, PZ0, PZ1,
                  '+y')]

# Quadro de compensado 18 x 50 em volta da la de cada folha
QZ0, QZ1 = BZ0 + 0.002, BZ1 - 0.002
QUADROS = (("Esquerda", BX0 + 0.004, XFE - 0.030, folha_esq),
           ("Direita", XFE + 0.038, BX1 - 0.004, folha_dir))
for nome, qx0, qx1, partes in QUADROS:
    partes += [
        peca(f"Porta_Quadro_{nome}_Vertical_A", qx0, qx0 + T, YF, Y_FR, QZ0,
             QZ1, '+x'),
        peca(f"Porta_Quadro_{nome}_Vertical_B", qx1 - T, qx1, YF, Y_FR, QZ0,
             QZ1, '+x'),
        peca(f"Porta_Quadro_{nome}_Horizontal_A", qx0 + T, qx1 - T, YF, Y_FR,
             QZ0, QZ0 + T, '+z'),
        peca(f"Porta_Quadro_{nome}_Horizontal_B", qx0 + T, qx1 - T, YF, Y_FR,
             QZ1 - T, QZ1, '+z'),
    ]

# Mata-junta central na folha esquerda (avanca 30 mm sobre a juncao)
YM0, YM1 = Y_FR - 0.021, Y_FR - 0.003
folha_esq += [
    peca("Mata_Junta_Central", XFE - 0.030, XFE + 0.030, YM0, YM1, QZ0, QZ1,
         '+y'),
    caixa("Mata_Junta_EPDM", XFD, XFE + 0.030, YM1, Y_FR, QZ0, QZ1, M_EPDM,
          C_MAD),
]
# Trincos ferrolho verticais (topo e base, lado interno da folha esquerda)
for nome, z0, z1, zh0, zh1 in (
        ("Topo", BZ1 - 0.13, BZ1 - 0.03, BZ1 - 0.11, BZ1 + 0.05),
        ("Base", BZ0 + 0.03, BZ0 + 0.13, BZ0 - 0.05, BZ0 + 0.11)):
    folha_esq.append(caixa(f"Trinco_Ferrolho_{nome}", XFE - 0.024,
                           XFE + 0.016, YM0 - 0.010, YM0, z0, z1, M_ACO,
                           C_MAD))
    folha_esq.append(cilindro(f"Trinco_Ferrolho_{nome}_Haste",
                              (XFE - 0.004, YM0 - 0.006, (zh0 + zh1) / 2),
                              0.005, zh1 - zh0, 'Z', M_ACO, C_MAD, 12))

# Ferragens externas
DOBRADICAS_Z = (PZ0 + 0.15, (PZ0 + PZ1) / 2, PZ1 - 0.15)
for i, z in enumerate(DOBRADICAS_Z, 1):
    for lado, xp, sx, partes in (("Esq", PX0, 1, folha_esq),
                                 ("Dir", PX1, -1, folha_dir)):
        cilindro(f"Dobradica_{lado}_{i}_Pino", (xp, LY + 0.006, z), 0.007,
                 0.102, 'Z', M_ACO, C_MAD, 16)
        caixa(f"Dobradica_{lado}_{i}_Aba_Fixa", min(xp, xp - sx * 0.045),
              max(xp, xp - sx * 0.045), LY, LY + 0.003, z - 0.051, z + 0.051,
              M_ACO, C_MAD)
        partes.append(caixa(f"Dobradica_{lado}_{i}_Aba_Folha",
                            min(xp, xp + sx * 0.045), max(xp, xp + sx * 0.045),
                            LY, LY + 0.003, z - 0.051, z + 0.051, M_ACO,
                            C_MAD))
    folha_dir.append(caixa(f"Fecho_Rapido_{i}", XFD + 0.004, XFD + 0.050, LY,
                           LY + 0.014, z - 0.035, z + 0.035, M_ACO, C_MAD))
    folha_esq.append(caixa(f"Fecho_Rapido_{i}_Gancho", XFE - 0.035,
                           XFE - 0.004, LY, LY + 0.010, z - 0.015, z + 0.015,
                           M_ACO, C_MAD))
for nome, xh, partes in (("Esquerdo", XFE - 0.09, folha_esq),
                         ("Direito", XFD + 0.09, folha_dir)):
    partes.append(tubo(f"Puxador_{nome}", [
        (xh, LY, 1.08), (xh, LY + 0.045, 1.08), (xh, LY + 0.045, 1.24),
        (xh, LY, 1.24)], 0.008, M_ACO, C_MAD))

# Capuz superior de exaustao (Z_TETO1..Z_TAMPA0 + tampa removivel).
# Saida de ar quente na parede X = 0, mesmo lado do escapamento; a parede
# X = 2 (lado da entrada de ar frio) e fechada. A parede de tras do capuz e a
# propria traseira superior.
peca("Capuz_Frente", 0, LX, Y_FR, LY, Z_TETO1, Z_TAMPA0, '+y')
peca("Capuz_X2_Fechada", LX - T, LX, T, Y_FR, Z_TETO1, Z_TAMPA0, '+x')
c_sai = peca("Capuz_X0_Saida", 0, T, T, Y_FR, Z_TETO1, Z_TAMPA0, '-x')
recortar(c_sai, caixa("c", -0.1, 0.1, *SAIDA, None, None))
recorte("Capuz_X0_Saida", "ret",
        (0, T, SAIDA[0], SAIDA[1], SAIDA[2], SAIDA[3]),
        "abertura da veneziana de saída")
peca("Capuz_Chicana_1_Defletor_Superior", X_CH1, X_CH1 + T, YT, YF, Z_CH1,
     Z_TAMPA0, '+x')
peca("Capuz_Chicana_2_Defletor_Inferior", X_CH2, X_CH2 + T, YT, YF, Z_TETO1,
     Z_CH2, '-x')
# Tampa: chapa inteira de 2.200, com beiral de 100 mm sobre cada veneziana
peca("Capuz_Tampa", -BEIRAL, LX + BEIRAL, 0, LY, Z_TAMPA0, Z_TAMPA1, '+z',
     col=C_TAMPA)

for nome, z0 in (("Inferior", Z_TETO1), ("Superior", Z_TAMPA0 - SR)):
    sar(f"Capuz_{nome}_Traseiro", XS0, XS1, T, YS0, z0, z0 + SR)
    sar(f"Capuz_{nome}_Frontal", XS0, XS1, YH1, Y_FR, z0, z0 + SR)
    sar(f"Capuz_{nome}_X0", T, XS0, YS0, YH1, z0, z0 + SR)
    sar(f"Capuz_{nome}_X2", XS1, LX - T, YS0, YH1, z0, z0 + SR)
for nx, x0 in (("X0", T), ("X2", XS1)):
    for ny, y0 in (("Traseiro", T), ("Frontal", YH1)):
        sar(f"Capuz_Vertical_{ny}_{nx}", x0, x0 + SR, y0, y0 + SR, Z_TETO1,
            Z_TAMPA0)
# A chicana 2 fica presa ao piso do capuz; a chicana 1 sai junto com a tampa
sar("Capuz_Chicana_2", X_CH2 + T, X_CH2 + T + SR, YT, YF, Z_TETO1,
    Z_TETO1 + SR)
sar("Capuz_Chicana_1", X_CH1 - SR, X_CH1, YT, YF, Z_TAMPA0 - SR, Z_TAMPA0)

# --- Parafusos ---------------------------------------------------------------
ZI, ZS = ZP + SR / 2, Z_TETO0 - SR / 2          # sarrafos inferior / superior
ZHI, ZHS = Z_TETO1 + SR / 2, Z_TAMPA0 - SR / 2  # idem, no capuz
N_TRAS, N_FR, N_X0, N_X2 = (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0)
N_CIMA, N_BAIXO = (0, 0, 1), (0, 0, -1)

o = "Parede_Traseira_Inferior"
fila(P40, o, (XS0, 0, ZI), (X_DIV, 0, ZI), N_TRAS,
     "Traseira inferior no sarrafo inferior")
fila(P40, o, (XDC1, 0, ZI), (XS1, 0, ZI), N_TRAS,
     "Traseira inferior no sarrafo inferior")
for x in (XCA, XCB):
    fila(P40, o, (x, 0, ZP), (x, 0, Z_EM), N_TRAS,
         "Traseira nos sarrafos verticais")
fila(P40, o, ((XDC0 + XDC1) / 2, 0, ZP + SR), ((XDC0 + XDC1) / 2, 0, Z_DIV),
     N_TRAS, "Traseira no sarrafo vertical da divisória")
fila(P30, o, (XS0, 0, Z_EM - 0.025), (XS1, 0, Z_EM - 0.025), N_TRAS,
     "Traseira na régua de emenda")

o = "Parede_Traseira_Superior"
fila(P30, o, (XS0, 0, Z_EM + 0.025), (XS1, 0, Z_EM + 0.025), N_TRAS,
     "Traseira na régua de emenda")
fila(P40, o, (XS0, 0, ZS), (XS1, 0, ZS), N_TRAS,
     "Traseira superior no sarrafo superior da câmara")
for z in (ZHI, ZHS):
    fila(P40, o, (XS0, 0, z), (XS1, 0, z), N_TRAS,
         "Paredes do capuz nos sarrafos do capuz")
for x in (XCA, XCB):
    fila(P40, o, (x, 0, Z_EM), (x, 0, Z_TETO0), N_TRAS,
         "Traseira nos sarrafos verticais", margem=0.035)
    fila(P40, o, (x, 0, Z_TETO1), (x, 0, Z_TAMPA0), N_TRAS,
         "Paredes do capuz nos sarrafos do capuz", margem=0.08)

for o, x, nx in (("Parede_X0_Escapamento", 0.0, N_X0),
                 ("Parede_X2_Entrada", LX, N_X2)):
    for z in (ZI, ZS):
        fila(P40, o, (x, YS0, z), (x, YS1, z), nx,
             "Laterais nos sarrafos inferior e superior")
    for y in (YCA, YCB):
        fila(P40, o, (x, y, ZP), (x, y, Z_TETO0), nx,
             "Laterais nos sarrafos verticais e montantes", margem=0.07)

for o, x, nx in (("Capuz_X0_Saida", 0.0, N_X0),
                 ("Capuz_X2_Fechada", LX, N_X2)):
    for z in (ZHI, ZHS):
        fila(P40, o, (x, YS0, z), (x, YH1, z), nx,
             "Paredes do capuz nos sarrafos do capuz")
    for y in (YCA, Y_FR - SR / 2):
        fila(P40, o, (x, y, Z_TETO1), (x, y, Z_TAMPA0), nx,
             "Paredes do capuz nos sarrafos do capuz", margem=0.08)
o = "Capuz_Frente"
for z in (ZHI, ZHS):
    fila(P40, o, (XS0, LY, z), (XS1, LY, z), N_FR,
         "Paredes do capuz nos sarrafos do capuz")
for x in (XCA, XCB):
    fila(P40, o, (x, LY, Z_TETO1), (x, LY, Z_TAMPA0), N_FR,
         "Paredes do capuz nos sarrafos do capuz", margem=0.08)

o = "Divisoria_Labirinto_Entrada"
fila(P40, o, (X_DIV, YS0, ZI), (X_DIV, YS1, ZI), N_X0,
     "Divisória nos sarrafos da divisória")
fila(P40, o, (X_DIV, YCA, ZP + SR), (X_DIV, YCA, Z_DIV), N_X0,
     "Divisória nos sarrafos da divisória", margem=0.07)
ZTRAV = Z_DIV - SR / 2
parafuso(P80, o, (X_DIV, YS1 - SR / 2, ZTRAV), N_X0,
         "Travessa da divisória (topo da travessa)")
parafuso(P80, "Parede_X2_Entrada", (LX, YS1 - SR / 2, ZTRAV), N_X2,
         "Travessa da divisória (topo da travessa)")

# Base: sarrafos laterais e da divisoria presos por baixo; a base desce nas
# longarinas. Os sarrafos da frente e de tras levam parafuso longo que
# atravessa a base e ancora na longarina.
for x in (XCA, XCB, (XDC0 + XDC1) / 2):
    for ya, yb in ((YS0, LONG_Y[1][0] - 0.02), (LONG_Y[1][1] + 0.02, YS1)):
        fila(P50, "Base", (x, ya, Z_BASE0), (x, yb, Z_BASE0), N_BAIXO,
             "Base nos sarrafos inferiores (por baixo)")
fila(P50, "Base", (0, LY / 2, Z_BASE1), (LX, LY / 2, Z_BASE1), N_CIMA,
     "Base na longarina central (por cima)", passo=0.25)
for nome, y in (("Traseiro", YCA), ("Frontal", YCB)):
    for suf, xa, xb in (("A", XS0, X_DIV),
                        ("B", XDC1 if nome == "Traseiro" else XDC0, XS1)):
        fila(P80, f"Sarrafo_Inferior_{nome}_{suf}", (xa, y, ZP + SR),
             (xb, y, ZP + SR), N_CIMA,
             "Sarrafo inferior + base na longarina", passo=0.25,
             passa=("Base",))

o = "Teto_Camara"
fila(P50, o, (XS0, YCB, Z_TETO1), (XS1, YCB, Z_TETO1), N_CIMA,
     "Teto no sarrafo superior frontal (por cima)")
fila(P50, o, (XS0, Y_FR - SR / 2, Z_TETO0), (XS1, Y_FR - SR / 2, Z_TETO0),
     N_BAIXO, "Teto no sarrafo frontal do capuz (por baixo)")
fila(P50, o, (X_CH2 + T + SR / 2, YT, Z_TETO0),
     (X_CH2 + T + SR / 2, YF, Z_TETO0), N_BAIXO,
     "Teto no sarrafo da chicana 2 (por baixo)")
fila(P80, "Sarrafo_Capuz_Inferior_Traseiro", (XS0, YCA, Z_TETO1 + SR),
     (XS1, YCA, Z_TETO1 + SR), N_CIMA,
     "Sarrafo do capuz + teto no sarrafo superior da câmara", passo=0.25,
     passa=("Teto_Camara",))
for nome, x in (("X0", XCA), ("X2", XCB)):
    fila(P80, f"Sarrafo_Capuz_Inferior_{nome}", (x, YS0, Z_TETO1 + SR),
         (x, YS1, Z_TETO1 + SR), N_CIMA,
         "Sarrafo do capuz + teto no sarrafo superior da câmara", passo=0.25,
         passa=("Teto_Camara",))

fila(P40, "Capuz_Chicana_2_Defletor_Inferior", (X_CH2, YT, ZHI),
     (X_CH2, YF, ZHI), N_X0, "Chicanas nos sarrafos das chicanas")
fila(P40, "Capuz_Chicana_1_Defletor_Superior", (X_CH1 + T, YT, ZHS),
     (X_CH1 + T, YF, ZHS), N_X2, "Chicanas nos sarrafos das chicanas")

o = "Capuz_Tampa"
fila(P50, o, (X_CH1 - SR / 2, YT, Z_TAMPA1), (X_CH1 - SR / 2, YF, Z_TAMPA1),
     N_CIMA, "Tampa no sarrafo da chicana 1")
for y in (YCA, Y_FR - SR / 2):
    fila(PTAMPA, o, (XS0, y, Z_TAMPA1), (XS1, y, Z_TAMPA1), N_CIMA,
         "Tampa nos sarrafos superiores do capuz (removível, sem cola)",
         passo=0.30)
for x in (XCA, XCB):
    fila(PTAMPA, o, (x, YS0, Z_TAMPA1), (x, YH1, Z_TAMPA1), N_CIMA,
         "Tampa nos sarrafos superiores do capuz (removível, sem cola)",
         passo=0.30)

fila(P40, "Batente_Inferior", (XS0, YB1, ZI), (X_DIV, YB1, ZI), N_FR,
     "Batente inferior no sarrafo frontal (removível, sem cola)")
fila(P40, "Batente_Inferior", (XDC0, YB1, ZI), (XS1, YB1, ZI), N_FR,
     "Batente inferior no sarrafo frontal (removível, sem cola)")
fila(P40, "Batente_Superior", (XS0, YB1, ZS), (XS1, YB1, ZS), N_FR,
     "Batente superior e laterais nos sarrafos e montantes")
for nome, x in (("Esquerdo", T + 0.012), ("Direito", LX - T - 0.012)):
    fila(P40, f"Batente_{nome}", (x, YB1, BZ0), (x, YB1, BZ1), N_FR,
         "Batente superior e laterais nos sarrafos e montantes")
for nome, x in (("Esquerda", T + 0.028), ("Direita", LX - T - 0.028)):
    fila(P70, f"Guarnicao_{nome}", (x, LY, Z_BASE1), (x, LY, Z_TETO0), N_FR,
         "Guarnição + calço + batente no montante frontal", passo=0.25,
         margem=0.08)
for (nome, qx0, qx1, _), leaf, g in zip(
        QUADROS, ("Porta_Folha_Esquerda_Passiva", "Porta_Folha_Direita_Ativa"),
        ("Porta_Esq", "Porta_Dir")):
    for x in (qx0 + T / 2, qx1 - T / 2):
        fila(P40, leaf, (x, LY, QZ0), (x, LY, QZ1), N_FR,
             "Folha de porta no quadro da lã", passo=0.25, grupo=g)
    for z in (QZ0 + T / 2, QZ1 - T / 2):
        fila(P40, leaf, (qx0 + T, LY, z), (qx1 - T, LY, z), N_FR,
             "Folha de porta no quadro da lã", passo=0.25, margem=0.10,
             grupo=g)

cab = cabecas_dos_parafusos()
folha_esq.append(cab["Porta_Esq"])
folha_dir.append(cab["Porta_Dir"])

# ----------------------------------------------------------------------------
# 02 - Isolamento acustico (la de rocha + tela perfurada, 50 mm no total)
# ----------------------------------------------------------------------------
r = revestimento("Teto_Camara", T, LX - T, T, YL, ZT, Z_TETO0, 'z', -1)
for fx, fy in FAN_XY:
    recortar_todos(r, lambda: cilindro("c", (fx, fy, ZT), 0.15, 0.2, 'Z',
                                       None, None))

r = revestimento("Parede_X0", T, XE, T, YL, ZP, ZT, 'x', +1)
recortar_todos(r, lambda: cilindro("c", (0.04, EY, EZ), 0.085, 0.2, 'X',
                                   None, None))
r = revestimento("Parede_X2", XD, LX - T, T, YL, ZP, ZT, 'x', -1)
recortar_todos(r, lambda: caixa("c", LX - 0.2, LX + 0.1, *ENTRADA, None,
                                None))

revestimento("Traseira_Camara", XE, DV0, T, YT, ZP, ZT, 'y', +1)
revestimento("Traseira_Passagem", DV0, DV1, T, YT, Z_DIV, ZT, 'y', +1)
revestimento("Traseira_Duto_Entrada", DV1, XD, T, YT, ZP, ZT, 'y', +1)

revestimento("Divisoria_Face_Camara", DV0, X_DIV, YT, YF, ZP, Z_DIV, 'x', -1)
revestimento("Divisoria_Face_Duto", X_DIV + T, DV1, YT, YF, ZP, Z_DIV,
             'x', +1)

# Sanduiche acustico recuado em cada folha (encaixa dentro do batente),
# contido pelo quadro de compensado
for nome, qx0, qx1, partes in QUADROS:
    partes += revestimento(f"Porta_Folha_{nome}", qx0 + T, qx1 - T, YF, Y_FR,
                           QZ0 + T, QZ1 - T, 'y', -1)

# Capuz: teto, parede fechada (X = 2), frente/tras e as duas faces de cada
# chicana. O piso do capuz fica sem revestimento e o teto nao e revestido
# sobre a chicana 2, para manter o vao de 0.122 acima dela.
C1A, C1B = X_CH1 - REV, X_CH1 + T + REV
C2A, C2B = X_CH2 - REV, X_CH2 + T + REV
revestimento("Capuz_Teto_A", X_CH1 + T, LX - T, T, Y_FR, ZCT, Z_TAMPA0,
             'z', -1)
revestimento("Capuz_Teto_B", C2B, X_CH1, T, Y_FR, ZCT, Z_TAMPA0, 'z', -1)
revestimento("Capuz_Teto_C", T, C2A, T, Y_FR, ZCT, Z_TAMPA0, 'z', -1)
revestimento("Capuz_Traseira", T, XD, T, YT, Z_TETO1, ZCT, 'y', +1)
revestimento("Capuz_Frente", T, XD, YF, Y_FR, Z_TETO1, ZCT, 'y', -1)
revestimento("Capuz_X2_Fechada", XD, LX - T, T, Y_FR, Z_TETO1, ZCT, 'x', -1)
revestimento("Capuz_Chicana_1_Face_A", C1A, X_CH1, YT, YF, Z_CH1, ZCT,
             'x', -1)
revestimento("Capuz_Chicana_1_Face_B", X_CH1 + T, C1B, YT, YF, Z_CH1, ZCT,
             'x', +1)
revestimento("Capuz_Chicana_2_Face_A", C2A, X_CH2, YT, YF, Z_TETO1, Z_CH2,
             'x', -1)
revestimento("Capuz_Chicana_2_Face_B", X_CH2 + T, C2B, YT, YF, Z_TETO1,
             Z_CH2, 'x', +1)

# Aplica a abertura das folhas (pivo na aresta externa de cada dobradica)
porta_partes = folha_esq + folha_dir
for nome, xp, graus, partes in (
        ("Porta_Pivo_Esquerdo", PX0, ABERTURA_FOLHA_ESQ, folha_esq),
        ("Porta_Pivo_Direito", PX1, ABERTURA_FOLHA_DIR, folha_dir)):
    pivo = bpy.data.objects.new(nome, None)
    pivo.empty_display_size = 0.1
    pivo.location = (xp, LY, 0.0)
    C_MAD.objects.link(pivo)
    inv = Matrix.Translation(pivo.location).inverted()
    for o in partes:
        o.parent = pivo
        o.matrix_parent_inverse = inv
    pivo.rotation_euler = (0, 0, math.radians(graus))


# ----------------------------------------------------------------------------
# 03 - Ventilacao e escapamento
# ----------------------------------------------------------------------------
def veneziana(nome, x_c, y0, y1, z0, z1, lado_externo, n_aletas,
              graus=35.0):
    """Aletas inclinadas para baixo no sentido externo (-1 = -X, +1 = +X)."""
    ang = math.radians(graus) * lado_externo
    passo = (z1 - z0) / n_aletas
    for i in range(n_aletas):
        zc = z0 + passo * (i + 0.5)
        a = caixa(f"{nome}_Aleta_{i + 1}", -0.03, 0.03, y0, y1, -0.001,
                  0.001, M_ACO, C_VENT)
        a.location = (x_c, (y0 + y1) / 2, zc)
        a.rotation_euler = (0, ang, 0)
    xe = x_c + lado_externo * 0.011
    m = 0.02
    caixa(f"{nome}_Moldura_Sup", xe - 0.002, xe + 0.002, y0 - m, y1 + m, z1,
          z1 + m, M_ACO, C_VENT)
    caixa(f"{nome}_Moldura_Inf", xe - 0.002, xe + 0.002, y0 - m, y1 + m,
          z0 - m, z0, M_ACO, C_VENT)
    caixa(f"{nome}_Moldura_A", xe - 0.002, xe + 0.002, y0 - m, y0, z0, z1,
          M_ACO, C_VENT)
    caixa(f"{nome}_Moldura_B", xe - 0.002, xe + 0.002, y1, y1 + m, z0, z1,
          M_ACO, C_VENT)


veneziana("Veneziana_Entrada", LX - T / 2, *ENTRADA, +1, 9)
veneziana("Veneziana_Saida", T / 2, *SAIDA, -1, 5, 45.0)

ZF = Z_TETO1 + 0.04
for n, (fx, fy) in enumerate(FAN_XY, 1):
    carc = caixa(f"Exaustor_{n}_Carcaca", fx - 0.16, fx + 0.16, fy - 0.16,
                 fy + 0.16, Z_TETO1, Z_TETO1 + 0.08, M_VENT, C_VENT)
    recortar(carc, cilindro("c", (fx, fy, ZF), 0.145, 0.2, 'Z', None, None))
    cilindro(f"Exaustor_{n}_Cubo", (fx, fy, ZF), 0.045, 0.05, 'Z', M_VENT,
             C_VENT, 32)
    for k in range(5):
        pa = caixa(f"Exaustor_{n}_Pa_{k + 1}", -0.05, 0.05, -0.032, 0.032,
                   -0.0015, 0.0015, M_ACO, C_VENT)
        pa.matrix_world = (Matrix.Translation((fx, fy, ZF))
                           @ Matrix.Rotation(math.radians(72 * k), 4, 'Z')
                           @ Matrix.Translation((0.09, 0, 0))
                           @ Matrix.Rotation(math.radians(30), 4, 'X'))

# Flange termica dupla + miolo de fibra ceramica (parede X = 0)
for nome, xc in (("Flange_Interna", T + 0.0015), ("Flange_Externa", -0.0015)):
    f = cilindro(nome, (xc, EY, EZ), 0.080, 0.003, 'X', M_ACO, C_VENT)
    recortar(f, cilindro("c", (xc, EY, EZ), 0.025, 0.05, 'X', None, None))
miolo = cilindro("Flange_Miolo_Fibra_Ceramica", (T / 2, EY, EZ), 0.075, T,
                 'X', M_CERAM, C_VENT)
recortar(miolo, cilindro("c", (T / 2, EY, EZ), 0.0235, 0.05, 'X', None, None))


def tubo_corrugado(nome, x0, x1, y, z, raio, mat, col, passo=0.006, seg=24):
    bm = bmesh.new()
    n = int(round((x1 - x0) / passo))
    aneis = []
    for i in range(n + 1):
        rr = raio + (0.0028 if i % 2 else 0.0)
        x = x0 + (x1 - x0) * i / n
        aneis.append([bm.verts.new((x, y + rr * math.cos(2 * math.pi * s / seg),
                                    z + rr * math.sin(2 * math.pi * s / seg)))
                      for s in range(seg)])
    for a, b in zip(aneis, aneis[1:]):
        for s in range(seg):
            t = (s + 1) % seg
            bm.faces.new((a[s], b[s], b[t], a[t]))
    bm.faces.new(aneis[0])
    bm.faces.new(reversed(aneis[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = _obj(nome, bm, mat, col)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


tubo_corrugado("Tubo_Escapamento_Corrugado", -0.250, GX, EY, EZ, 0.0225,
               M_ACO, C_VENT)

# ----------------------------------------------------------------------------
# 04 - Gerador Toyama TG8000CXER, tapete e iluminacao
#      Envelope 0.82 x 0.68 x 0.65 em X 0.318..1.138, Y 0.220..0.900.
#      Painel voltado para as portas. Como no equipamento real visto pelo
#      painel: a ESQUERDA (X alto, lado da entrada de ar frio) ficam as rodas,
#      o motor, a ventoinha e a partida retratil; a DIREITA (X baixo, lado
#      quente) ficam o alternador, o silencioso e o pe de apoio.
#      Coordenadas locais: x medido a partir da extremidade do motor.
# ----------------------------------------------------------------------------
caixa("Tapete_Antivibracao", 0.18, 1.28, 0.09, 1.34, Z_BASE1, GZ, M_EPDM,
      C_GER)
GL = 0.82


def gc(nome, x0, x1, y0, y1, z0, z1, mat):
    return caixa("Gerador_" + nome, GX + GL - x1, GX + GL - x0, GY + y0,
                 GY + y1, GZ + z0, GZ + z1, mat, C_GER)


def gcil(nome, c, raio, comp, eixo, mat, seg=32):
    return cilindro("Gerador_" + nome, (GX + GL - c[0], GY + c[1], GZ + c[2]),
                    raio, comp, eixo, mat, C_GER, seg)


def gp(pts):
    return [(GX + GL - x, GY + y, GZ + z) for x, y, z in pts]


# 1. Quadro tubular: prisma 0.82 x 0.54 x 0.62 com cantos arredondados
RQ = 0.016
QX0, QX1 = RQ, GL - RQ
QY0, QY1 = 0.07 + RQ, 0.61 - RQ
QZ0, QZ1 = 0.05 + RQ, 0.62 - RQ


def ret_arredondado(y, rc=0.07, n=6):
    pts = []
    cantos = [(QX1 - rc, QZ0 + rc, -90), (QX1 - rc, QZ1 - rc, 0),
              (QX0 + rc, QZ1 - rc, 90), (QX0 + rc, QZ0 + rc, 180)]
    for cx, cz, a0 in cantos:
        for i in range(n + 1):
            a = math.radians(a0 + 90.0 * i / n)
            pts.append((cx + rc * math.cos(a), y, cz + rc * math.sin(a)))
    return pts


for i, y in enumerate((QY0, QY1), 1):
    tubo(f"Gerador_Quadro_Lateral_{i}", gp(ret_arredondado(y)), RQ, M_QUADRO,
         C_GER, ciclico=True)
for i, (x, z) in enumerate([(0.10, QZ0), (0.72, QZ0), (0.10, QZ1),
                            (0.72, QZ1), (QX0, 0.33), (QX1, 0.33),
                            (0.27, QZ0), (0.52, QZ0)], 1):
    tubo(f"Gerador_Quadro_Travessa_{i}", gp([(x, QY0, z), (x, QY1, z)]), RQ,
         M_QUADRO, C_GER)
for i, (x, y) in enumerate([(0.27, 0.24), (0.27, 0.48), (0.52, 0.24),
                            (0.52, 0.48)], 1):
    gcil(f"Coxim_{i}", (x, y, 0.097), 0.025, 0.03, 'Z', M_EPDM, 20)
gc("Bandeja_Motor", 0.10, 0.62, 0.20, 0.52, 0.112, 0.130, M_QUADRO)

# 2. Tanque 25 L (0.64 x 0.46 x 0.16) vermelho Toyama
tanque = gc("Tanque", 0.09, 0.73, 0.11, 0.57, 0.47, 0.63, M_TOYAMA)
bv = tanque.modifiers.new("Bevel", 'BEVEL')
bv.width = 0.035
bv.segments = 5
for p in tanque.data.polygons:
    p.use_smooth = True
gcil("Tampa_Combustivel", (0.55, 0.34, 0.640), 0.035, 0.02, 'Z', M_PLAST)
gc("Visor_Nivel", 0.28, 0.36, 0.31, 0.37, 0.630, 0.634, M_ETIQ)
gc("Tanque_Faixa_Logo", 0.26, 0.56, 0.566, 0.572, 0.52, 0.57, M_PLAST)

# 3. Motor 420 cc, ventoinha e partida retratil (lado da entrada de ar frio)
AY, AZ = 0.36, 0.25                      # eixo do virabrequim/alternador
gc("Motor_Bloco", 0.10, 0.30, 0.22, 0.50, 0.130, 0.340, M_ALUM)
base_cil = (Matrix.Translation((GX + GL - 0.20, GY + 0.33, GZ + 0.33))
            @ Matrix.Rotation(math.radians(25), 4, 'X'))


def motor_peca(nome, sx, sy, z0, z1, mat):
    o = caixa("Gerador_" + nome, -sx / 2, sx / 2, -sy / 2, sy / 2,
              -(z1 - z0) / 2, (z1 - z0) / 2, mat, C_GER)
    o.matrix_world = base_cil @ Matrix.Translation((0, 0, (z0 + z1) / 2))
    return o


motor_peca("Motor_Cilindro", 0.13, 0.11, 0.0, 0.075, M_ALUM)
for i in range(5):
    motor_peca(f"Motor_Aleta_{i + 1}", 0.17, 0.15, 0.008 + i * 0.015,
               0.012 + i * 0.015, M_ALUM)
motor_peca("Motor_Cabecote", 0.15, 0.13, 0.075, 0.105, M_ALUM)
motor_peca("Motor_Tampa_Valvulas", 0.12, 0.10, 0.105, 0.130, M_CROMO)
gcil("Carenagem_Ventoinha", (0.065, AY, AZ), 0.14, 0.07, 'X', M_TOYAMA, 48)
gcil("Grade_Entrada_Ar", (0.027, AY, AZ), 0.10, 0.008, 'X', M_PLAST, 40)
gcil("Partida_Retratil_Tambor", (0.014, AY, AZ), 0.06, 0.026, 'X', M_PLAST)
gcil("Partida_Retratil_Manopla", (0.012, AY + 0.10, AZ + 0.10), 0.011, 0.07,
     'Y', M_PLAST, 16)
gc("Filtro_Ar", 0.11, 0.29, 0.11, 0.20, 0.30, 0.42, M_PLAST)
gc("Carburador", 0.16, 0.24, 0.19, 0.23, 0.31, 0.37, M_ALUM)

# 4. Alternador e bateria 12 V
gcil("Alternador", (0.45, AY, AZ), 0.13, 0.30, 'X', M_ESCOV, 48)
gcil("Alternador_Tampa_Ventilada", (0.6125, AY, AZ), 0.125, 0.025, 'X',
     M_PLAST, 48)
for i in range(6):
    a = math.radians(60 * i)
    gc(f"Alternador_Fenda_{i + 1}",
       0.6245, 0.6265,
       AY + 0.07 * math.cos(a) - 0.02, AY + 0.07 * math.cos(a) + 0.02,
       AZ + 0.07 * math.sin(a) - 0.006, AZ + 0.07 * math.sin(a) + 0.006,
       M_CINZA)
gc("Bandeja_Bateria", 0.33, 0.53, 0.095, 0.235, 0.070, 0.085, M_QUADRO)
gc("Bateria_12V", 0.34, 0.52, 0.10, 0.23, 0.085, 0.255, M_PLAST)
gcil("Bateria_Borne_Positivo", (0.37, 0.165, 0.263), 0.009, 0.016, 'Z',
     M_BORNE_V, 16)
gcil("Bateria_Borne_Negativo", (0.49, 0.165, 0.263), 0.009, 0.016, 'Z',
     M_PLAST, 16)

# 5. Silencioso com grade termica na extremidade quente (depois do
#    alternador), bocal alinhado com a flange termica da parede X = 0
SY, SZ = EY - GY, EZ - GZ
gc("Silencioso", 0.64, 0.80, SY - 0.13, SY + 0.13, SZ - 0.09, SZ + 0.09,
   M_ACO)
gc("Silencioso_Grade_Termica", 0.63, 0.81, SY - 0.14, SY + 0.14, SZ - 0.10,
   SZ + 0.10, M_QUADRO)
gcil("Silencioso_Bocal", (0.815, SY, SZ), 0.021, 0.03, 'X', M_ACO, 24)
gc("Silencioso_Coletor", 0.24, 0.63, SY - 0.02, SY + 0.02, 0.40, 0.43, M_ACO)

# 6. Painel de controle (voltado para as portas, +Y)
YPN = 0.626
gc("Painel", 0.17, 0.65, 0.61, YPN, 0.25, 0.47, M_QUADRO)
gcil("Painel_Chave_Ignicao", (0.215, YPN + 0.005, 0.40), 0.014, 0.012, 'Y',
     M_CROMO, 20)
gc("Painel_Display", 0.26, 0.33, YPN, YPN + 0.004, 0.375, 0.42, M_DISPLAY)
gc("Painel_Disjuntor", 0.355, 0.385, YPN, YPN + 0.012, 0.37, 0.42, M_PLAST)
for i, x in enumerate((0.435, 0.495), 1):
    gcil(f"Painel_Tomada_2PT_{i}", (x, YPN + 0.004, 0.395), 0.024, 0.01, 'Y',
         M_CINZA, 24)
gcil("Painel_Tomada_Industrial_32A", (0.585, YPN + 0.025, 0.385), 0.034,
     0.05, 'Y', M_TOM_AZUL, 32)
for i, (x0, x1, z0, z1) in enumerate([(0.19, 0.24, 0.28, 0.34),
                                      (0.26, 0.385, 0.28, 0.34),
                                      (0.41, 0.52, 0.28, 0.33),
                                      (0.19, 0.24, 0.43, 0.455)], 1):
    gc(f"Painel_Etiqueta_{i}", x0, x1, YPN, YPN + 0.001, z0, z1, M_ETIQ)

# 7. Rodas (lado do motor) e pes de apoio (lado do alternador/silencioso)
XR = 0.13
for i, y in enumerate((0.03, 0.65), 1):
    gcil(f"Roda_{i}", (XR, y, 0.125), 0.125, 0.06, 'Y', M_PLAST, 48)
    yc = y + (0.031 if y > 0.3 else -0.031)
    gcil(f"Roda_{i}_Calota", (XR, yc, 0.125), 0.045, 0.006, 'Y', M_TOYAMA,
         32)
gcil("Eixo_Rodas", (XR, 0.34, 0.125), 0.011, 0.60, 'Y', M_ACO, 16)
for i, y in enumerate((QY0, QY1), 1):
    gc(f"Pe_Apoio_{i}", 0.69, 0.74, y - 0.018, y + 0.018, 0.015, 0.055,
       M_QUADRO)
    gc(f"Pe_Apoio_{i}_Sapata", 0.68, 0.75, y - 0.025, y + 0.025, 0.0, 0.015,
       M_EPDM)

# Fita de LED 12 V IP65 (1.00 x 0.02 x 0.01) no teto, sobre o corredor frontal
YLED = 1.38
caixa("LED_12V", 0.30, 1.30, YLED - 0.01, YLED + 0.01, ZT - 0.01, ZT, M_LED,
      C_GER)
xb, xr = GX + GL - 0.37, 1.20
tubo("Cabo_LED_Bateria", [
    (xb, GY + 0.165, GZ + 0.27), (xb, GY + 0.165, GZ + 0.30),
    (xb, YT + 0.006, GZ + 0.30), (xr, YT + 0.006, GZ + 0.30),
    (xr, YT + 0.006, ZT - 0.015), (xr, YLED, ZT - 0.015)], 0.0025, M_PLAST,
    C_GER)
luz_led = bpy.data.objects.new("LED_12V_Luz", bpy.data.lights.new(
    "LED_12V_Luz", 'AREA'))
luz_led.data.shape = 'RECTANGLE'
luz_led.data.size = 1.0
luz_led.data.size_y = 0.02
luz_led.data.energy = 12
luz_led.location = (0.80, YLED, ZT - 0.012)
C_GER.objects.link(luz_led)


# ----------------------------------------------------------------------------
# 00 - Cena: piso, camera e luzes
# ----------------------------------------------------------------------------
caixa("Piso", -5, 7, -5, 7, -0.01, 0.0, M_PISO, C_CENA)


def apontar(ob, alvo):
    d = Vector(alvo) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


CAM_POS, CAM_ALVO = (-2.9, 6.2, 3.2), (1.0, 0.8, 1.02)
cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
cam.data.lens = 40
cam.location = CAM_POS
apontar(cam, CAM_ALVO)
C_CENA.objects.link(cam)
scene.camera = cam

sol = bpy.data.objects.new("Sol", bpy.data.lights.new("Sol", 'SUN'))
sol.data.energy = 1.6
sol.location = (-2, 5, 6)
apontar(sol, (1.0, 0.8, 0.8))
C_CENA.objects.link(sol)

area = bpy.data.objects.new("Luz_Area", bpy.data.lights.new("Luz_Area",
                                                           'AREA'))
area.data.energy = 300
area.data.size = 3.5
area.location = (0.6, 5.0, 2.6)
apontar(area, (1.0, 0.8, 0.9))
C_CENA.objects.link(area)

mundo = scene.world or bpy.data.worlds.new("Mundo")
scene.world = mundo
try:
    if mundo.node_tree is None:
        mundo.use_nodes = True
    bg = next(n for n in mundo.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (0.75, 0.78, 0.82, 1.0)
    bg.inputs[1].default_value = 0.35
except Exception:
    pass

scene.render.resolution_x = 1600
scene.render.resolution_y = 1100

# ----------------------------------------------------------------------------
# Execucao headless: salvar e renderizar
# ----------------------------------------------------------------------------
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(nome, padrao=None):
    return args[args.index(nome) + 1] if nome in args else padrao


motor = arg("--engine")
if motor:
    try:
        scene.render.engine = motor
    except TypeError as e:
        print("Motor invalido:", e)
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = 48
        scene.cycles.use_denoising = True

# Dados de construcao: ficam guardados na cena e podem ser exportados em JSON
DADOS = {
    "pecas": PECAS, "parafusos": PARAFUSOS, "revestimentos": REVEST,
    "gerador": [mm(v) for v in (GX, GX + GL, GY, GY + 0.68, GZ, GZ + 0.65)],
    "tapete": [180.0, 1280.0, 90.0, 1340.0, mm(Z_BASE1), mm(GZ)],
    "exaustores": [[mm(fx), mm(fy)] for fx, fy in FAN_XY],
    "escapamento": [mm(EY), mm(EZ)],
    "dobradicas_z": [mm(z) for z in DOBRADICAS_Z],
    "const": {k: mm(v) for k, v in (
        ("T", T), ("REV", REV), ("SR", SR), ("LX", LX), ("LY", LY),
        ("Z_PE", Z_PE), ("Z_BASE1", Z_BASE1), ("Z_EM", Z_EM),
        ("Z_TETO0", Z_TETO0), ("Z_TETO1", Z_TETO1), ("Z_TAMPA0", Z_TAMPA0),
        ("Z_TAMPA1", Z_TAMPA1), ("X_DIV", X_DIV), ("Z_DIV", Z_DIV),
        ("X_CH1", X_CH1), ("Z_CH1", Z_CH1), ("X_CH2", X_CH2),
        ("Z_CH2", Z_CH2), ("Y_FR", Y_FR), ("YL", YL), ("YF", YF),
        ("YT", YT), ("BZ0", BZ0), ("BZ1", BZ1), ("PX0", PX0), ("PX1", PX1),
        ("PZ0", PZ0), ("PZ1", PZ1), ("XFE", XFE), ("XFD", XFD),
        ("BEIRAL", BEIRAL))},
}
scene["cabine_dados"] = json.dumps(DADOS)
dados_json = arg("--dados")
if dados_json:
    with open(os.path.abspath(dados_json), "w", encoding="utf-8") as f:
        json.dump(DADOS, f, ensure_ascii=False, indent=1)

salvar = arg("--save")
if salvar:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(salvar))

pasta = arg("--render")
if pasta:
    pasta = os.path.abspath(pasta)
    os.makedirs(pasta, exist_ok=True)

    def render(nome, pos, alvo, lente=40):
        cam.location = pos
        cam.data.lens = lente
        apontar(cam, alvo)
        scene.render.filepath = os.path.join(pasta, nome)
        bpy.ops.render.render(write_still=True)

    # As portas ficam ocultas em todas as imagens para mostrar o interior
    for o in porta_partes:
        o.hide_render = True
    render("01_vista_geral.png", CAM_POS, CAM_ALVO)

    # Corte: esconde tambem a frente e a tampa para ver o caminho do ar
    ocultos = [o for o in bpy.data.objects if o.name.startswith((
        "Guarnicao_", "Batente_", "EPDM_", "Pingadeira", "Dobradica",
        "Capuz_Frente", "Capuz_Tampa", "La_Capuz_Teto", "Tela_Capuz_Teto",
        "La_Capuz_Frente", "Tela_Capuz_Frente"))]
    for o in ocultos:
        o.hide_render = True
    render("02_corte_frontal.png", (0.7, 6.3, 3.1), (1.0, 0.8, 1.06), 50)
    render("03_corte_lado_entrada.png", (5.6, 4.9, 3.2), (1.05, 0.8, 1.08),
           50)
    render("04_gerador_detalhe.png", (1.75, 3.5, 1.3),
           (GX + GL / 2, GY + 0.34, 0.45), 55)
    render("05_capuz_labirinto.png", (0.6, 4.1, 2.8), (0.6, 0.8, 1.93), 50)
    render("06_corte_lado_saida.png", (-3.6, 4.9, 3.2), (0.95, 0.8, 1.08),
           50)
    for o in ocultos + porta_partes:
        o.hide_render = False
    cam.location = CAM_POS
    cam.data.lens = 40
    apontar(cam, CAM_ALVO)

print("Modelo criado:", len(bpy.data.objects), "objetos")
