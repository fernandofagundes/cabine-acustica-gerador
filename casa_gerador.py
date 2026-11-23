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
      --save casa_gerador.blend --render renders [--engine CYCLES]
"""
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
C_FLUXO = colecao("05_Fluxos_Ar_Cutaway")


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
M_AZUL = material("Fluxo_Frio_Azul", (0.05, 0.30, 1.0), 0.4, 0.0, 1.5)
M_VERM = material("Fluxo_Quente_Vermelho", (1.0, 0.06, 0.03), 0.4, 0.0, 1.5)
M_LARANJA = material("Fluxo_Escape_Laranja", (0.75, 0.22, 0.0), 0.4, 0.0, 1.2)
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
# 01 - Estrutura de madeira
# ----------------------------------------------------------------------------
n = 0
for px in (0.0, LX / 2 - 0.06, LX - 0.12):
    for py in (0.0, LY - 0.12):
        n += 1
        caixa(f"Pe_Borracha_{n}", px, px + 0.12, py, py + 0.12, 0, Z_PE,
              M_EPDM, C_MAD)

caixa("Base", 0, LX, 0, LY, Z_BASE0, Z_BASE1, M_MAD, C_MAD)
caixa("Parede_Traseira", 0, LX, 0, T, Z_BASE1, Z_TETO0, M_MAD, C_MAD)

p_x0 = caixa("Parede_X0_Escapamento", 0, T, T, Y_FR, Z_BASE1, Z_TETO0, M_MAD,
             C_MAD)
recortar(p_x0, cilindro("c", (T / 2, EY, EZ), 0.075, 0.2, 'X', None, None))

p_x2 = caixa("Parede_X2_Entrada", LX - T, LX, T, Y_FR, Z_BASE1, Z_TETO0,
             M_MAD, C_MAD)
recortar(p_x2, caixa("c", LX - 0.1, LX + 0.1, *ENTRADA, None, None))

# Divisoria do labirinto de entrada (para em YF: as portas vedam contra ela)
caixa("Divisoria_Labirinto_Entrada", X_DIV, X_DIV + T, T, YF, Z_BASE1, Z_DIV,
      M_MAD, C_MAD)

teto = caixa("Teto_Camara", 0, LX, 0, LY, Z_TETO0, Z_TETO1, M_MAD, C_MAD)
for fx, fy in FAN_XY:
    recortar(teto, cilindro("c", (fx, fy, Z_TETO0), 0.15, 0.2, 'Z', None,
                            None))

# --- Portas duplas acusticas -------------------------------------------------
# Folhas no plano Y_FR..LY; batente por dentro, onde elas encostam
LF, PH = 0.936, 1.640                               # folha: largura x altura
PX0, PX1 = 0.060, LX - 0.060
PZ0 = (Z_BASE1 + Z_TETO0 - PH) / 2
PZ1 = PZ0 + PH
BX0, BX1, BZ0, BZ1 = PX0 + 0.038, PX1 - 0.038, PZ0 + 0.038, PZ1 - 0.038
YB0, YB1 = YL, YL + T                               # batente (18 mm)
E = 0.012                                           # EPDM 12 x 12

# Guarnicao fixa em volta das folhas (fecha o plano frontal)
caixa("Guarnicao_Esquerda", 0, PX0, Y_FR, LY, Z_BASE1, Z_TETO0, M_MAD, C_MAD)
caixa("Guarnicao_Direita", PX1, LX, Y_FR, LY, Z_BASE1, Z_TETO0, M_MAD, C_MAD)
caixa("Guarnicao_Inferior", PX0, PX1, Y_FR, LY, Z_BASE1, PZ0, M_MAD, C_MAD)
caixa("Guarnicao_Superior", PX0, PX1, Y_FR, LY, PZ1, Z_TETO0, M_MAD, C_MAD)

# Batente perimetral
caixa("Batente_Inferior", T, LX - T, YB0, YB1, Z_BASE1, BZ0, M_MAD, C_MAD)
caixa("Batente_Superior", T, LX - T, YB0, YB1, BZ1, Z_TETO0, M_MAD, C_MAD)
caixa("Batente_Esquerdo", T, BX0, YB0, YB1, BZ0, BZ1, M_MAD, C_MAD)
caixa("Batente_Direito", BX1, LX - T, YB0, YB1, BZ0, BZ1, M_MAD, C_MAD)
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
folha_esq = [caixa("Porta_Folha_Esquerda_Passiva", PX0, XFE, Y_FR, LY, PZ0,
                   PZ1, M_MAD, C_MAD)]
folha_dir = [caixa("Porta_Folha_Direita_Ativa", XFD, PX1, Y_FR, LY, PZ0, PZ1,
                   M_MAD, C_MAD)]

# Mata-junta central na folha esquerda (avanca 30 mm sobre a juncao)
YM0, YM1 = Y_FR - 0.021, Y_FR - 0.003
folha_esq += [
    caixa("Mata_Junta_Central", XFE - 0.030, XFE + 0.030, YM0, YM1,
          BZ0 + 0.002, BZ1 - 0.002, M_MAD, C_MAD),
    caixa("Mata_Junta_EPDM", XFD, XFE + 0.030, YM1, Y_FR, BZ0 + 0.002,
          BZ1 - 0.002, M_EPDM, C_MAD),
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
for i, z in enumerate((PZ0 + 0.15, (PZ0 + PZ1) / 2, PZ1 - 0.15), 1):
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
# X = 2 (lado da entrada de ar frio) e fechada.
caixa("Capuz_Traseira", 0, LX, 0, T, Z_TETO1, Z_TAMPA0, M_MAD, C_MAD)
caixa("Capuz_Frente", 0, LX, Y_FR, LY, Z_TETO1, Z_TAMPA0, M_MAD, C_MAD)
caixa("Capuz_X2_Fechada", LX - T, LX, T, Y_FR, Z_TETO1, Z_TAMPA0, M_MAD,
      C_MAD)
c_sai = caixa("Capuz_X0_Saida", 0, T, T, Y_FR, Z_TETO1, Z_TAMPA0, M_MAD,
              C_MAD)
recortar(c_sai, caixa("c", -0.1, 0.1, *SAIDA, None, None))
caixa("Capuz_Chicana_1_Defletor_Superior", X_CH1, X_CH1 + T, YT, YF, Z_CH1,
      Z_TAMPA0, M_MAD, C_MAD)
caixa("Capuz_Chicana_2_Defletor_Inferior", X_CH2, X_CH2 + T, YT, YF, Z_TETO1,
      Z_CH2, M_MAD, C_MAD)
caixa("Capuz_Tampa", 0, LX, 0, LY, Z_TAMPA0, Z_TAMPA1, M_MAD, C_TAMPA)

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

# Sanduiche acustico recuado em cada folha (encaixa dentro do batente)
folha_esq += revestimento("Porta_Folha_Esquerda", BX0 + 0.004, XFE - 0.030,
                          YF, Y_FR, BZ0 + 0.002, BZ1 - 0.002, 'y', -1)
folha_dir += revestimento("Porta_Folha_Direita", XFE + 0.038, BX1 - 0.004,
                          YF, Y_FR, BZ0 + 0.002, BZ1 - 0.002, 'y', -1)

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
# 05 - Fluxos de ar
# ----------------------------------------------------------------------------
def seta(nome, pontos, mat, raio=0.012):
    ob = tubo(nome, pontos, raio, mat, C_FLUXO, suave=True)
    a, b = Vector(pontos[-2]), Vector(pontos[-1])
    d = (b - a).normalized()
    comp = raio * 6
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=raio * 2.6,
                          radius2=0.0, depth=comp)
    ponta = _obj(nome + "_Ponta", bm, mat, C_FLUXO)
    ponta.matrix_world = (Matrix.Translation(b + d * comp / 2)
                          @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4())
    return ob


XDUTO = (DV1 + XD) / 2                   # eixo do duto de subida
ZPAS = (Z_DIV + ZT) / 2                  # eixo da passagem sobre a divisoria
XV, ZV = GX + GL + 0.01, GZ + AZ         # ventoinha do motor
for i, (y, yv) in enumerate(((0.55, GY + AY - 0.06), (1.05, GY + AY + 0.06)),
                            1):
    seta(f"Fluxo_Ar_Frio_{i}", [
        (LX + 0.42, y, 0.35), (LX + 0.05, y, 0.35), (LX - 0.12, y, 0.35),
        (XDUTO, y, 0.46), (XDUTO, y, 1.45), (XDUTO - 0.01, y, ZPAS - 0.02),
        (X_DIV, y, ZPAS), (DV0 - 0.08, y, ZPAS - 0.02), (1.40, y, 1.40),
        (1.40, y, 0.75), (1.36, yv, ZV + 0.06), (XV, yv, ZV)], M_AZUL)

ZV1 = (Z_TETO1 + Z_CH1) / 2              # vao sob a chicana 1
ZV2 = (Z_CH2 + Z_TAMPA0) / 2             # vao sobre a chicana 2
XMEIO = (C2B + C1A) / 2                  # espaco intermediario
for i, (fx, fy) in enumerate(FAN_XY, 1):
    ys = GY + 0.34 + (0.12 if fy > 0.8 else -0.12)
    seta(f"Fluxo_Ar_Quente_{i}", [
        (fx - 0.25, ys, 0.82), (fx, fy, 1.10), (fx, fy, 1.55),
        (fx, fy, 1.92), (fx - 0.08, fy, 1.96), (C1B + 0.07, fy, 1.95),
        (C1B + 0.01, fy, ZV1), (C1A - 0.01, fy, ZV1), (XMEIO, fy, 1.90),
        (XMEIO, fy, 2.00), (C2B + 0.01, fy, ZV2), (C2A - 0.01, fy, ZV2),
        (C2A - 0.09, fy, 2.02), (C2A - 0.11, fy, 1.95), (0.0, fy, 1.91),
        (-0.22, fy, 1.74)], M_VERM)

seta("Fluxo_Gases_Escape", [(-0.27, EY, EZ), (-0.38, EY, EZ),
                            (-0.52, EY, EZ)], M_LARANJA, raio=0.014)

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
