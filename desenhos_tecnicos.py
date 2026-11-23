"""
Desenhos tecnicos cotados da cabine acustica, a partir das medidas exportadas
do modelo do Blender (Especificações/dados_construcao.json).

  blender --background --factory-startup --python casa_gerador.py -- \
      --save casa_gerador.blend --dados Especificações/dados_construcao.json
  python3 desenhos_tecnicos.py

Gera em Especificações/desenhos/: uma folha SVG (A4 paisagem) por desenho,
`desenhos.html` com todas as folhas e, se o Google Chrome estiver instalado,
`desenhos_tecnicos.pdf`. Gera tambem Especificações/lista_de_pecas.md.
"""
import collections
import json
import os
import shutil
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
ESP = os.path.join(BASE, "Especificações")
OUT = os.path.join(ESP, "desenhos")
D = json.load(open(os.path.join(ESP, "dados_construcao.json"),
                   encoding="utf-8"))
C = D["const"]
LARG, ALT = 297.0, 210.0            # folha A4 paisagem, em mm

# vista -> (vetor "direita", vetor "cima") de quem olha a partir desse lado
VISTAS = {'+y': ((-1, 0, 0), (0, 0, 1)), '-y': ((1, 0, 0), (0, 0, 1)),
          '+x': ((0, 1, 0), (0, 0, 1)), '-x': ((0, -1, 0), (0, 0, 1)),
          '+z': ((-1, 0, 0), (0, -1, 0)), '-z': ((1, 0, 0), (0, -1, 0))}
NOME_VISTA = {
    '+y': "vista pela frente (lado das portas)", '-y': "vista por trás",
    '+x': "vista pelo lado da entrada de ar frio",
    '-x': "vista pelo lado do escapamento",
    '+z': "vista por cima (frente da cabine para baixo)",
    '-z': "vista por baixo (frente da cabine para baixo)"}
COR_PARAF = {"4,0 x 30": "#7b3fa0", "4,5 x 40": "#c62828",
             "4,5 x 50": "#1565c0", "5,0 x 70": "#ef6c00",
             "5,0 x 80": "#2e7d32", "5,0 x 50 com arruela EPDM": "#00838f"}

# objeto do modelo -> nome da peca nos desenhos (na ordem das folhas)
NOMES = [
    ("Base", "Base (piso)"),
    ("Teto_Camara", "Teto da câmara (piso do capuz)"),
    ("Capuz_Tampa", "Tampa do capuz"),
    ("Parede_Traseira_Inferior", "Traseira inferior"),
    ("Parede_Traseira_Superior", "Traseira superior"),
    ("Parede_X2_Entrada", "Lateral da entrada de ar frio"),
    ("Parede_X0_Escapamento", "Lateral do escapamento"),
    ("Divisoria_Labirinto_Entrada", "Divisória do labirinto de entrada"),
    ("Capuz_Frente", "Capuz: frente"),
    ("Capuz_X0_Saida", "Capuz: lateral da saída de ar quente"),
    ("Capuz_X2_Fechada", "Capuz: lateral fechada"),
    ("Capuz_Chicana_1_Defletor_Superior", "Chicana 1 (presa à tampa)"),
    ("Capuz_Chicana_2_Defletor_Inferior", "Chicana 2 (presa ao piso do capuz)"),
    ("Porta_Folha_Direita_Ativa",
     "Folha de porta ativa (lado da entrada de ar)"),
    ("Porta_Folha_Esquerda_Passiva",
     "Folha de porta passiva (lado do escapamento)"),
    ("Guarnicao_Direita", "Guarnição do lado da entrada de ar"),
    ("Guarnicao_Esquerda", "Guarnição do lado do escapamento"),
    ("Batente_Inferior", "Batente inferior (removível)"),
    ("Batente_Superior", "Batente superior"),
    ("Batente_Direito", "Batente lateral do lado da entrada de ar"),
    ("Batente_Esquerdo", "Batente lateral do lado do escapamento"),
    ("Mata_Junta_Central", "Mata-junta central"),
    ("Regua_Emenda_Traseira", "Régua de emenda da traseira"),
    ("Porta_Quadro_Esquerda_Vertical_A", "Quadro da lã das portas: vertical"),
    ("Porta_Quadro_Esquerda_Vertical_B", "Quadro da lã das portas: vertical"),
    ("Porta_Quadro_Direita_Vertical_A", "Quadro da lã das portas: vertical"),
    ("Porta_Quadro_Direita_Vertical_B", "Quadro da lã das portas: vertical"),
    ("Porta_Quadro_Esquerda_Horizontal_A",
     "Quadro da lã das portas: horizontal"),
    ("Porta_Quadro_Esquerda_Horizontal_B",
     "Quadro da lã das portas: horizontal"),
    ("Porta_Quadro_Direita_Horizontal_A",
     "Quadro da lã das portas: horizontal"),
    ("Porta_Quadro_Direita_Horizontal_B",
     "Quadro da lã das portas: horizontal"),
]
PECA = {p["obj"]: p for p in D["pecas"]}


def fmt(v):
    """Milimetros sem casas decimais desnecessarias."""
    v = round(v, 1)
    return f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}".replace(
        ".", ",")


def eixo(v):
    return 'xyz'.index(v[1])


def sinal(v):
    return 1 if v[0] == '+' else -1


def proj(v, p):
    r, u = VISTAS[v]
    return (sum(a * b for a, b in zip(r, p)), sum(a * b for a, b in zip(u, p)))


def ret(v, bb):
    """bbox do mundo -> (u0, u1, v0, v1) na vista."""
    a = proj(v, (bb[0], bb[2], bb[4]))
    b = proj(v, (bb[1], bb[3], bb[5]))
    return (min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]),
            max(a[1], b[1]))


def comprimento(tipo):
    return float(tipo.split("x")[1].split()[0].replace(",", "."))


# ----------------------------------------------------------------------------
# Folha SVG
# ----------------------------------------------------------------------------
class Folha:
    def __init__(self, codigo, titulo, sub=""):
        self.codigo, self.titulo, self.sub = codigo, titulo, sub
        self.e = []
        self.defs = []

    def add(self, s):
        self.e.append(s)

    def line(self, x1, y1, x2, y2, cor="#222", w=0.25, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" '
                 f'y2="{y2:.2f}" stroke="{cor}" stroke-width="{w}"{d}/>')

    def rect(self, x, y, w, h, fill="none", cor="#222", sw=0.3, dash=None,
             op=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{op}"' if op is not None else ""
        self.add(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(w, 0.01):.2f}" '
                 f'height="{max(h, 0.01):.2f}" fill="{fill}" stroke="{cor}" '
                 f'stroke-width="{sw}"{d}{o}/>')

    def circ(self, x, y, r, fill="none", cor="#222", sw=0.3, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" '
                 f'fill="{fill}" stroke="{cor}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, t, size=2.6, anchor="start", cor="#222", rot=None,
             bold=False):
        r = f' transform="rotate({rot} {x:.2f} {y:.2f})"' if rot else ""
        b = ' font-weight="bold"' if bold else ""
        t = t.replace("&", "&amp;").replace("<", "&lt;")
        self.add(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" '
                 f'text-anchor="{anchor}" fill="{cor}"{r}{b}>{t}</text>')

    def svg(self, n, total):
        o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{LARG}mm" '
             f'height="{ALT}mm" viewBox="0 0 {LARG} {ALT}" '
             f'font-family="DejaVu Sans, Arial, sans-serif">',
             '<defs>',
             '<pattern id="la" width="2.4" height="2.4" '
             'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             '<rect width="2.4" height="2.4" fill="#fbf6c8"/>'
             '<line x1="0" y1="0" x2="0" y2="2.4" stroke="#b9a94a" '
             'stroke-width="0.25"/></pattern>',
             *self.defs, '</defs>',
             f'<rect width="{LARG}" height="{ALT}" fill="#ffffff"/>',
             f'<rect x="6" y="6" width="{LARG - 12}" height="{ALT - 12}" '
             f'fill="none" stroke="#222" stroke-width="0.5"/>',
             f'<line x1="6" y1="{ALT - 16}" x2="{LARG - 6}" y2="{ALT - 16}" '
             f'stroke="#222" stroke-width="0.5"/>']
        o += self.e
        self.e = []
        self.text(9, ALT - 9.5, f"{self.codigo} — {self.titulo}", 3.6,
                  bold=True)
        self.text(LARG - 9, ALT - 11.5,
                  "Cabine acústica ventilada para gerador", 2.4, "end")
        self.text(LARG - 9, ALT - 8.2,
                  f"Medidas em mm · não medir no desenho, usar as cotas · "
                  f"folha {n}/{total}", 2.2, "end", "#444")
        if self.sub:
            self.text(9, ALT - 13.5 + 7.2 - 0.6, "", 2)
            self.text(LARG / 2 + 8, ALT - 9.5, self.sub, 2.4, "middle",
                      "#444")
        o += self.e
        o.append('</svg>')
        return "\n".join(o)


def cota_h(f, x1, x2, y, txt, yref=None, cor="#1a3c8a"):
    if yref is not None:
        for x in (x1, x2):
            f.line(x, yref, x, y + (1.2 if y > yref else -1.2), cor, 0.13)
    f.line(x1, y, x2, y, cor, 0.18)
    for x in (x1, x2):
        f.line(x - 0.8, y + 0.8, x + 0.8, y - 0.8, cor, 0.3)
    f.text((x1 + x2) / 2, y - 0.9, txt, 2.5, "middle", cor)


def cota_v(f, y1, y2, x, txt, xref=None, cor="#1a3c8a"):
    if xref is not None:
        for y in (y1, y2):
            f.line(xref, y, x + (1.2 if x > xref else -1.2), y, cor, 0.13)
    f.line(x, y1, x, y2, cor, 0.18)
    for y in (y1, y2):
        f.line(x - 0.8, y + 0.8, x + 0.8, y - 0.8, cor, 0.3)
    f.text(x - 0.9, (y1 + y2) / 2, txt, 2.5, "middle", cor, rot=-90)


def ordenadas_h(f, itens, y, lado=1, size=2.1, yref=None):
    """Cotas acumuladas ao longo de X do papel. itens = [(x, rotulo, cor)].
    lado = +1 escreve abaixo de y, -1 acima."""
    faixas = [-1e9, -1e9, -1e9]
    vistos = set()
    for x, rot, cor in sorted(itens):
        if (round(x, 1), rot) in vistos:
            continue
        vistos.add((round(x, 1), rot))
        k = next((i for i in range(3) if x - faixas[i] >= size * 1.25), 2)
        faixas[k] = x
        ya = y + lado * (2.0 + k * (size * 3.4))
        if yref is not None:
            f.line(x, yref, x, y, cor, 0.1, "0.6 0.6")
        f.line(x, y, x, ya - lado * 0.4, cor, 0.15)
        f.text(x + size * 0.36, ya, rot, size,
               "end" if lado > 0 else "start", cor, rot=-90)


def ordenadas_v(f, itens, x, lado=-1, size=2.1, xref=None):
    """Cotas acumuladas ao longo de Y do papel. itens = [(y, rotulo, cor)].
    lado = -1 escreve a esquerda de x, +1 a direita."""
    faixas = [1e9, 1e9, 1e9]
    vistos = set()
    for y, rot, cor in sorted(itens, reverse=True):
        if (round(y, 1), rot) in vistos:
            continue
        vistos.add((round(y, 1), rot))
        k = next((i for i in range(3) if faixas[i] - y >= size * 1.25), 2)
        faixas[k] = y
        xa = x + lado * (2.0 + k * (size * 3.4))
        if xref is not None:
            f.line(xref, y, x, y, cor, 0.1, "0.6 0.6")
        f.line(x, y, xa - lado * 0.4, y, cor, 0.15)
        f.text(xa, y + size * 0.36, rot, size,
               "end" if lado < 0 else "start", cor)


def marca_furo(f, x, y, tipo, estilo, r=0.75):
    cor = COR_PARAF.get(tipo, "#000")
    if estilo == "frente":
        f.circ(x, y, r, cor, cor, 0.1)
    elif estilo == "tras":
        f.circ(x, y, r, "#fff", cor, 0.3)
    else:                                   # furo de parafuso que vem de outra peca
        f.rect(x - r, y - r, 2 * r, 2 * r, "#fff", cor, 0.3)


# ----------------------------------------------------------------------------
# Folhas das pecas de compensado
# ----------------------------------------------------------------------------
def furos_da_peca(p):
    v = p["vista"]
    a, s = eixo(v), sinal(v)
    u0, _, v0, _ = ret(v, p["bbox"])
    out = []
    for q in D["parafusos"]:
        if q["obj"] == p["obj"]:
            est = "frente" if q["n"][a] * s > 0 else "tras"
        elif p["obj"] in q["passa"]:
            est = "passa"
        else:
            continue
        u, vv = proj(v, q["p"])
        out.append((round(u - u0, 1), round(vv - v0, 1), q["tipo"], est))
    return sorted(out)


def recortes_da_peca(p):
    v = p["vista"]
    u0, _, v0, _ = ret(v, p["bbox"])
    out = []
    for r in p["recortes"]:
        if r["forma"] == "ret":
            a, b, c, d = ret(v, r["dados"])
            out.append(("ret", round(a - u0, 1), round(b - u0, 1),
                        round(c - v0, 1), round(d - v0, 1), r["nota"]))
        else:
            u, vv = proj(v, r["dados"][:3])
            out.append(("circ", round(u - u0, 1), round(vv - v0, 1),
                        r["dados"][3], 0, r["nota"]))
    return out


def medidas(p):
    bb = p["bbox"]
    d = [bb[1] - bb[0], bb[3] - bb[2], bb[5] - bb[4]]
    u0, u1, v0, v1 = ret(p["vista"], bb)
    return u1 - u0, v1 - v0, d[eixo(p["vista"])]


def grupos_de_pecas():
    """Agrupa pecas identicas (mesmas medidas, furos e recortes)."""
    grupos = collections.OrderedDict()
    for obj, nome in NOMES:
        p = PECA[obj]
        w, h, e = medidas(p)
        chave = (nome, round(w, 1), round(h, 1), round(e, 1),
                 tuple(furos_da_peca(p)), tuple(recortes_da_peca(p)))
        grupos.setdefault(chave, []).append(p)
    out = []
    for i, (chave, ps) in enumerate(grupos.items(), 1):
        out.append({"cod": f"P{i:02d}", "nome": chave[0], "w": chave[1],
                    "h": chave[2], "e": chave[3], "furos": list(chave[4]),
                    "recortes": list(chave[5]), "pecas": ps})
    return out


def folha_peca(g):
    p = g["pecas"][0]
    w, h = g["w"], g["h"]
    f = Folha(g["cod"], g["nome"],
              f'{len(g["pecas"])} peça(s) · compensado naval '
              f'{fmt(g["e"])} mm · {fmt(w)} × {fmt(h)}')
    ax0, ax1, ay0, ay1 = 34.0, 268.0, 22.0, 140.0
    esc = min((ax1 - ax0) / w, (ay1 - ay0) / h, 0.5)
    ox = ax0 + ((ax1 - ax0) - w * esc) / 2
    oy = ay1 - ((ay1 - ay0) - h * esc) / 2          # y do papel para v = 0

    def X(u):
        return ox + u * esc

    def Y(vv):
        return oy - vv * esc

    f.rect(X(0), Y(h), w * esc, h * esc, "#f6e7c6", "#3b2a10", 0.45)
    azul = "#1a3c8a"
    oh, ov = [], []
    for r in g["recortes"]:
        if r[0] == "ret":
            _, a, b, c, d, nota = r
            f.rect(X(a), Y(d), (b - a) * esc, (d - c) * esc, "#ffffff",
                   "#3b2a10", 0.45)
            f.line(X(a), Y(c), X(b), Y(d), "#999", 0.12)
            f.line(X(a), Y(d), X(b), Y(c), "#999", 0.12)
            f.text(X((a + b) / 2), Y((c + d) / 2) - 1.5,
                   f"{nota}: {fmt(b - a)} × {fmt(d - c)}", 2.4, "middle",
                   azul, bold=True)
            oh += [(X(a), fmt(a), azul), (X(b), fmt(b), azul)]
            ov += [(Y(c), fmt(c), azul), (Y(d), fmt(d), azul)]
            for xx in (a, b):
                f.line(X(xx), Y(c), X(xx), Y(0), azul, 0.1, "0.6 0.6")
            for yy in (c, d):
                f.line(X(0), Y(yy), X(a), Y(yy), azul, 0.1, "0.6 0.6")
        else:
            _, u, vv, raio, _, nota = r
            f.circ(X(u), Y(vv), raio * esc, "#ffffff", "#3b2a10", 0.45)
            f.line(X(u) - 2, Y(vv), X(u) + 2, Y(vv), azul, 0.15)
            f.line(X(u), Y(vv) - 2, X(u), Y(vv) + 2, azul, 0.15)
            if raio > 20:
                f.text(X(u), Y(vv) - 3, nota, 2.3, "middle", azul, bold=True)
                f.line(X(u), Y(vv), X(u), Y(0), azul, 0.1, "0.6 0.6")
                f.line(X(0), Y(vv), X(u), Y(vv), azul, 0.1, "0.6 0.6")
            else:
                f.text(X(u) + 2, Y(vv) - 1.5, nota, 2.0, "start", azul)
            oh.append((X(u), fmt(u), azul))
            ov.append((Y(vv), fmt(vv), azul))

    # Furos: em linha (mesma altura) ou em coluna (mesma distancia da borda)
    nv = collections.Counter(q[1] for q in g["furos"])
    nu = collections.Counter(q[0] for q in g["furos"])
    for u, vv, tipo, est in g["furos"]:
        cor = COR_PARAF.get(tipo, "#000")
        marca_furo(f, X(u), Y(vv), tipo, est)
        if nv[vv] >= nu[u] and nv[vv] >= 2:
            ov.append((Y(vv), fmt(vv), cor))
            alto = vv > h / 2
            f.text(X(u) + 0.6, Y(vv) + (2.0 if alto else -1.6), fmt(u), 1.7,
                   "end" if alto else "start", cor, rot=-90)
        elif nu[u] >= 2:
            oh.append((X(u), fmt(u), cor))
            dir_ = u > w / 2
            f.text(X(u) + (-1.5 if dir_ else 1.5), Y(vv) + 0.6, fmt(vv), 1.7,
                   "end" if dir_ else "start", cor)
        else:
            f.text(X(u) + 1.5, Y(vv) - 1.2, f"({fmt(u)}; {fmt(vv)})", 1.7,
                   "start", cor)
    ordenadas_h(f, oh + [(X(0), "0", "#555")], Y(0) + 1.0)
    ordenadas_v(f, ov + [(Y(0), "0", "#555")], X(0) - 1.0)
    cota_h(f, X(0), X(w), Y(h) - 7, fmt(w), Y(h))
    cota_v(f, Y(0), Y(h), X(w) + 8, fmt(h), X(w))

    # Notas e legenda
    y = 168.0
    f.text(9, y, f"Desenho: {NOME_VISTA[p['vista']]}. Origem das cotas no "
           f"canto inferior esquerdo do desenho.", 2.4)
    nomes_obj = ", ".join(q["obj"] for q in g["pecas"])
    f.text(9, y + 4, f"No modelo 3D: {nomes_obj}", 2.0, cor="#666")
    cont = collections.Counter((q[2], q[3]) for q in g["furos"])
    x = 9.0
    yl = y + 9.5
    for (tipo, est), n in sorted(cont.items()):
        marca_furo(f, x + 1, yl - 0.9, tipo, est, 0.9)
        txt = {"frente": "cabeça nesta face",
               "tras": "cabeça na face oposta",
               "passa": "vem do sarrafo e atravessa esta peça"}[est]
        s = f"{n} × parafuso {tipo} ({txt})"
        f.text(x + 3.5, yl, s, 2.3)
        x += 3.5 + len(s) * 1.32 + 6
        if x > 215:
            x, yl = 9.0, yl + 4
    if g["furos"]:
        f.text(9, yl + 4.5, "Número ao lado de cada furo: posição ao longo "
               "da linha. Número na margem: posição da linha. Furo passante "
               "Ø5 escareado na chapa; pré-furo Ø3 no sarrafo.", 2.2,
               cor="#444")
    return f


# ----------------------------------------------------------------------------
# Vistas e cortes do conjunto
# ----------------------------------------------------------------------------
EST_CORTE = {"compensado": ("#e3c48a", "#3b2a10", 0.35),
             "sarrafo": ("#c68a4e", "#3b2a10", 0.3),
             "longarina": ("#c68a4e", "#3b2a10", 0.3),
             "calco": ("#d9a968", "#3b2a10", 0.3),
             "borracha": ("#333333", "#000", 0.2),
             "revest": ("url(#la)", "#b9a94a", 0.12)}
EST_FUNDO = {"compensado": ("#fbf4e3", "#555", 0.2),
             "sarrafo": ("#f1dfc6", "#555", 0.2),
             "longarina": ("#f1dfc6", "#555", 0.2),
             "calco": ("#f1dfc6", "#555", 0.2),
             "borracha": ("#777", "#333", 0.2),
             "revest": ("#f7f5e6", "#cfc9a0", 0.12)}


def itens_do_modelo(revest=True):
    it = [{"nome": p["obj"], "tipo": p["tipo"], "bbox": p["bbox"],
           "recortes": p["recortes"]} for p in D["pecas"]]
    if revest:
        it += [{"nome": r["nome"], "tipo": "revest", "bbox": r["bbox"],
                "recortes": []} for r in D["revestimentos"]]
    return it


def desenha(f, vista, plano, ox, oy, esc, janela=None, revest=True,
            parafusos=None, gerador=True, sem=()):
    """Desenha o modelo visto de `vista`. `plano` = coordenada do plano de
    corte (None = vista externa). (ox, oy) = canto inferior esquerdo no papel.
    Retorna as funcoes X(u), Y(v) e os limites (u0, u1, v0, v1)."""
    a, s = eixo(vista), sinal(vista)
    itens = [i for i in itens_do_modelo(revest and plano is not None)
             if not i["nome"].startswith(tuple(sem))] if sem else \
        itens_do_modelo(revest and plano is not None)
    fundo, corte = [], []
    for it in itens:
        lo, hi = it["bbox"][2 * a], it["bbox"][2 * a + 1]
        if plano is None:
            fundo.append((hi if s > 0 else -lo, it))
        elif lo < plano < hi:
            corte.append(it)
        elif (s > 0 and hi <= plano) or (s < 0 and lo >= plano):
            fundo.append((hi if s > 0 else -lo, it))
    todos = [ret(vista, i["bbox"]) for _, i in fundo] + \
            [ret(vista, i["bbox"]) for i in corte]
    if janela:
        u0, u1, v0, v1 = janela
    else:
        u0 = min(r[0] for r in todos)
        u1 = max(r[1] for r in todos)
        v0 = min(r[2] for r in todos)
        v1 = max(r[3] for r in todos)

    def X(u):
        return ox + (u - u0) * esc

    def Y(v):
        return oy - (v - v0) * esc

    cid = f"c{len(f.defs)}"
    f.defs.append(f'<clipPath id="{cid}"><rect x="{X(u0):.2f}" '
                  f'y="{Y(v1):.2f}" width="{(u1 - u0) * esc:.2f}" '
                  f'height="{(v1 - v0) * esc:.2f}"/></clipPath>')
    f.add(f'<g clip-path="url(#{cid})">')

    def caixa(it, est, tabela):
        fill, cor, sw = tabela[it["tipo"]]
        a0, a1, b0, b1 = ret(vista, it["bbox"])
        f.rect(X(a0), Y(b1), (a1 - a0) * esc, (b1 - b0) * esc, fill, cor, sw)
        bb = it["bbox"]
        dims = [bb[1] - bb[0], bb[3] - bb[2], bb[5] - bb[4]]
        if (est == "corte" and it["tipo"] in ("sarrafo", "longarina")
                and dims[a] == max(dims)):
            f.line(X(a0), Y(b0), X(a1), Y(b1), cor, 0.15)
            f.line(X(a0), Y(b1), X(a1), Y(b0), cor, 0.15)
        if est == "fundo":
            for r in it["recortes"]:
                if r["forma"] == "ret":
                    bb = r["dados"]
                    if bb[2 * a + 1] - bb[2 * a] > 30:
                        continue
                    c0, c1, d0, d1 = ret(vista, bb)
                    f.rect(X(c0), Y(d1), (c1 - c0) * esc, (d1 - d0) * esc,
                           "#e9eef2", "#555", 0.2)
                    k = max(2, int((d1 - d0) / 45))
                    for j in range(1, k):
                        yy = Y(d0 + (d1 - d0) * j / k)
                        f.line(X(c0), yy, X(c1), yy, "#777", 0.12)
                elif dims[a] <= 30:
                    u, vv = proj(vista, r["dados"][:3])
                    f.circ(X(u), Y(vv), r["dados"][3] * esc, "#e9eef2",
                           "#555", 0.2)

    for _, it in sorted(fundo, key=lambda t: t[0]):
        caixa(it, "fundo", EST_FUNDO)
    for it in sorted(corte, key=lambda i: i["tipo"] != "revest"):
        caixa(it, "corte", EST_CORTE)
    if gerador and plano is not None:
        g0, g1, h0, h1 = ret(vista, D["gerador"])
        f.rect(X(g0), Y(h1), (g1 - g0) * esc, (h1 - h0) * esc, "#fdeaea",
               "#b71c1c", 0.3, "2 1", 0.6)
        f.text(X((g0 + g1) / 2), Y((h0 + h1) / 2), "gerador", 2.4, "middle",
               "#b71c1c")
    if parafusos == "cabecas":              # cabecas voltadas para quem olha
        cab = [q for q in D["parafusos"] if q["n"][a] * s > 0]
        face = max(q["p"][a] * s for q in cab)      # so a face de fora
        for q in cab:
            if q["p"][a] * s > face - 1:
                u, vv = proj(vista, q["p"])
                f.circ(X(u), Y(vv), 0.45, COR_PARAF[q["tipo"]], "none", 0)
    elif parafusos is not None:             # parafusos proximos do plano
        vistos = set()
        for q in D["parafusos"]:
            if q["n"][a] != 0 or abs(q["p"][a] - plano) > parafusos:
                continue
            u, vv = proj(vista, q["p"])
            comp = comprimento(q["tipo"])
            ponta = [q["p"][k] - q["n"][k] * comp for k in range(3)]
            u2, v2 = proj(vista, ponta)
            chave = (round(u), round(vv), q["tipo"])
            if chave in vistos:
                continue
            vistos.add(chave)
            cor = COR_PARAF[q["tipo"]]
            f.line(X(u), Y(vv), X(u2), Y(v2), cor, max(0.35, 4.5 * esc))
            f.circ(X(u), Y(vv), max(0.6, 4.5 * esc), cor, cor, 0.1)
    f.add('</g>')
    return X, Y, (u0, u1, v0, v1)


def legenda_parafusos(f, x, y):
    f.text(x, y, "Parafusos:", 2.3, bold=True)
    for i, (tipo, cor) in enumerate(COR_PARAF.items()):
        f.circ(x + 1, y + 3.4 + i * 3.4, 0.8, cor, cor, 0.1)
        f.text(x + 3.5, y + 4.2 + i * 3.4, tipo, 2.2)


def rotulo(f, x, y, tx, ty, txt, anchor="start"):
    f.line(x, y, tx, ty, "#333", 0.15)
    f.circ(x, y, 0.35, "#333", "#333", 0.1)
    f.text(tx + (0.8 if anchor == "start" else -0.8), ty + 0.8, txt, 2.2,
           anchor, "#111")


def folhas_conjunto():
    out = []
    az = "#1a3c8a"
    LX, LY, ZT = C["LX"], C["LY"], C["Z_TAMPA1"]

    # --- G01: quatro vistas externas com a posicao dos parafusos ------------
    f = Folha("G01", "Vistas externas e posição dos parafusos",
              "portas fechadas")
    esc = 1 / 33.0
    x = 18.0
    for vista, nome in (('+y', "Frente (portas)"),
                        ('+x', "Lado da entrada de ar frio"),
                        ('-y', "Traseira"), ('-x', "Lado do escapamento")):
        X, Y, (u0, u1, v0, v1) = desenha(f, vista, None, x, 118, esc,
                                         parafusos="cabecas")
        f.text((X(u0) + X(u1)) / 2, 128, nome, 2.8, "middle", bold=True)
        cota_h(f, X(u0), X(u1), Y(v1) - 6, fmt(u1 - u0), Y(v1))
        if vista == '+y':
            cota_v(f, Y(v0), Y(v1), X(u0) - 6, fmt(v1 - v0), X(u0))
            for z in D["dobradicas_z"]:
                for xp in (C["PX0"], C["PX1"]):
                    u, vv = proj(vista, (xp, 0, z))
                    f.rect(X(u) - 1.4, Y(vv) - 1.7, 2.8, 3.4, "#9aa0a6",
                           "#333", 0.15)
        x = X(u1) + 9
    legenda_parafusos(f, 20, 138)
    f.text(70, 141, "Cada ponto colorido é um parafuso com a cabeça na face "
           "mostrada. As posições exatas estão nas folhas das peças (P01 em "
           "diante).", 2.4)
    f.text(70, 146, "Convenção: de frente para as portas, a entrada de ar "
           "frio fica à esquerda e o escapamento e a saída de ar quente à "
           "direita.", 2.4)
    f.text(70, 151, "Tampa do capuz com beiral de 100 mm de cada lado "
           f"(largura total {fmt(LX + 2 * C['BEIRAL'])}). Altura total "
           f"{fmt(ZT)}, sendo {fmt(C['Z_PE'])} das longarinas e calços.",
           2.4)
    f.text(70, 156, "Cotas das dobradiças (centro, a partir do chão): "
           + ", ".join(fmt(z) for z in D["dobradicas_z"]) + ".", 2.4)
    out.append(f)

    # --- G02: vista superior e apoios ----------------------------------------
    f = Folha("G02", "Vista superior e apoios (vista por baixo)",
              "frente da cabine para baixo nos dois desenhos")
    esc = 1 / 19.0
    X, Y, (u0, u1, v0, v1) = desenha(f, '+z', None, 22, 118, esc,
                                     parafusos="cabecas")
    f.text((X(u0) + X(u1)) / 2, 130, "Vista superior (tampa do capuz)", 2.8,
           "middle", bold=True)
    cota_h(f, X(u0), X(u1), Y(v1) - 6, fmt(u1 - u0), Y(v1))
    cota_v(f, Y(v0), Y(v1), X(u0) - 6, fmt(v1 - v0), X(u0))
    X, Y, (u0, u1, v0, v1) = desenha(
        f, '-z', None, 160, 118, esc,
        sem=("Capuz_", "Sarrafo_", "Porta_", "Guarnicao", "Batente", "Calco_G",
             "Mata", "Regua", "Parede", "Teto", "Divisoria"))
    f.text((X(u0) + X(u1)) / 2, 130, "Vista por baixo: base, 3 longarinas "
           "45 × 70 e 9 calços de borracha", 2.8, "middle", bold=True)
    oh, ov = [], []
    for p in D["pecas"]:
        if p["tipo"] == "longarina":
            _, _, b0, b1 = ret('-z', p["bbox"])
            ov += [(Y(b0), fmt(-b0), az), (Y(b1), fmt(-b1), az)]
        if p["tipo"] == "borracha":
            a0, a1, _, _ = ret('-z', p["bbox"])
            oh += [(X(a0), fmt(a0), az), (X(a1), fmt(a1), az)]
    ordenadas_v(f, ov + [(Y(v1), "0", "#555"), (Y(v0), fmt(LY), "#555")],
                X(u1) + 1, lado=1)
    ordenadas_h(f, oh + [(X(u0), "0", "#555"), (X(u1), fmt(LX), "#555")],
                Y(v1) - 1, lado=-1)
    f.text(160, 137, "Cotas na margem direita: distância a partir da face de "
           "trás (Y). Em cima: a partir do lado do escapamento (X).", 2.3)
    f.text(160, 142, "Calços de borracha 120 × 60 × 10 colados sob as "
           "longarinas. Apoiar sobre contrapiso nivelado.", 2.3)
    f.text(160, 147, "As longarinas da frente e de trás ficam sob os "
           "sarrafos inferiores e recebem os parafusos 5,0 × 80.", 2.3)
    legenda_parafusos(f, 22, 138)
    out.append(f)

    def ords(f, X, Y, lim, vista, xs, zs, lado_h=1, eix_h=0, eix_v=2):
        u0, u1, v0, v1 = lim
        r, up = VISTAS[vista]
        sh, sv = r[eix_h], up[eix_v]
        oh = [(X(sh * x), fmt(x), az) for x in xs]
        ov = [(Y(sv * z), fmt(z), az) for z in zs]
        ordenadas_h(f, oh, Y(v0) + 1.0 if lado_h > 0 else Y(v1) - 1.0,
                    lado_h)
        ordenadas_v(f, ov, X(u0) - 1.0)

    zs = [0, 10, C["Z_PE"], C["Z_BASE1"], C["Z_DIV"], C["Z_EM"],
          C["Z_TETO0"] - C["REV"], C["Z_TETO0"], C["Z_TETO1"], C["Z_CH1"],
          C["Z_CH2"], C["Z_TAMPA0"], C["Z_TAMPA1"]]

    # --- G03: corte A-A (paralelo as portas) --------------------------------
    f = Folha("G03", "Corte A-A — paralelo às portas, no meio da cabine",
              "plano a 800 da traseira, visto da frente")
    esc = 1 / 16.5
    X, Y, lim = desenha(f, '+y', 800, 40, 172, esc)
    xs = [0, C["T"], C["T"] + C["REV"], C["X_CH2"], C["X_CH1"],
          C["X_DIV"] - C["REV"], C["X_DIV"], C["X_DIV"] + C["T"],
          C["X_DIV"] + C["T"] + C["REV"], LX - C["T"] - C["REV"],
          LX - C["T"], LX]
    ords(f, X, Y, lim, '+y', xs, zs)
    for fx, fy in D["exaustores"]:
        f.rect(X(-fx - 160), Y(C["Z_TETO1"] + 80), 320 * esc, 80 * esc,
               "#444", "#000", 0.2)
    tx = 190
    f.text(tx, 26, "Leitura do corte", 3.0, bold=True)
    notas = [
        "Marrom claro: compensado naval 18 mm cortado pelo plano.",
        "Marrom com X: sarrafo 40 × 40 ou longarina 45 × 70.",
        "Amarelo hachurado: lã de rocha 50 mm + tela.",
        "Tracejado vermelho: envelope do gerador (820 × 680 × 650).",
        "",
        "Cotas acumuladas. Horizontais: a partir da face externa",
        "do lado do escapamento (direita do desenho).",
        "Verticais: a partir do chão.",
        "",
        f"Divisória: topo a {fmt(C['Z_DIV'])}; passagem de ar de",
        f"{fmt(C['Z_TETO0'] - C['REV'] - C['Z_DIV'])} até o revestimento do teto.",
        f"Duto de entrada: {fmt((LX - C['T'] - C['REV']) - (C['X_DIV'] + C['T'] + C['REV']))} livres entre revestimentos.",
        f"Chicana 1: desce da tampa até {fmt(C['Z_CH1'])}.",
        f"Chicana 2: sobe do piso do capuz até {fmt(C['Z_CH2'])}.",
        f"Emenda da traseira a {fmt(C['Z_EM'])} do chão.",
        "Exaustores Ø300 sobre o teto, centro a 850 do lado",
        "do escapamento.",
    ]
    for i, t in enumerate(notas):
        f.text(tx, 32 + i * 4.3, t, 2.4)
    out.append(f)

    # --- G04: corte B-B (perpendicular as portas) ---------------------------
    f = Folha("G04", "Corte B-B — perpendicular às portas",
              "plano a 900 do lado do escapamento, visto do lado da "
              "entrada de ar")
    esc = 1 / 17.5
    X, Y, lim = desenha(f, '+x', 900, 40, 164, esc, parafusos=130)
    ys = [0, C["T"], C["YT"], 777.5, 822.5, C["YF"], C["YL"],
          C["YL"] + C["T"], C["Y_FR"], LY]
    ords(f, X, Y, lim, '+x', ys, zs, eix_h=1)
    f.text(tx, 26, "Leitura do corte", 3.0, bold=True)
    notas = [
        "Traseira à esquerda do desenho, portas à direita.",
        "",
        "Traseira em duas peças, com régua de emenda de",
        f"compensado 18 × 100 por dentro, centrada a {fmt(C['Z_EM'])}.",
        "A traseira superior sobe até a tampa e faz a parede",
        "de trás do capuz.",
        "",
        "Apoio: 3 longarinas 45 × 70 no sentido da largura,",
        "sobre calços de borracha de 10 mm.",
        "",
        "Frente, de dentro para fora: sarrafo 40 × 40,",
        "batente 18, vedação EPDM 12 e folha de porta 18.",
        f"Vão livre de passagem: {fmt(C['BZ1'] - C['BZ0'])} de altura",
        f"(batentes de {fmt(C['BZ0'] - C['Z_BASE1'])} em cima e embaixo).",
        "",
        "Parafusos desenhados em cor (ver legenda).",
    ]
    for i, t in enumerate(notas):
        f.text(tx, 32 + i * 4.3, t, 2.4)
    legenda_parafusos(f, tx, 106)
    out.append(f)

    # --- G05: plantas em corte ----------------------------------------------
    f = Folha("G05", "Plantas em corte — câmara e capuz",
              "frente da cabine (portas) para baixo")
    esc = 1 / 18.0
    X, Y, lim = desenha(f, '+z', 1000, 26, 132, esc)
    f.text(26 + LX * esc / 2, 16, "Corte C-C: câmara, a 1.000 do chão", 2.8,
           "middle", bold=True)
    xs = [0, C["T"], C["T"] + C["SR"], C["PX0"], C["XFE"], C["XFD"],
          C["X_DIV"], C["X_DIV"] + C["T"], C["PX1"], LX - C["T"], LX]
    ys = [0, C["T"], C["YT"], C["YF"], C["YL"], C["YL"] + C["T"], C["Y_FR"],
          LY]
    r, up = VISTAS['+z']
    ordenadas_h(f, [(X(-x), fmt(x), az) for x in xs], Y(lim[2]) + 1.0)
    ordenadas_v(f, [(Y(-y), fmt(y), az) for y in ys], X(lim[0]) - 1.0)
    x2 = 160
    X, Y, lim = desenha(f, '+z', 1950, x2, 132, esc, gerador=False)
    f.text(x2 + LX * esc / 2, 16, "Corte D-D: capuz, a 1.950 do chão", 2.8,
           "middle", bold=True)
    for fx, fy in D["exaustores"]:
        f.circ(X(-fx), Y(-fy), 150 * esc, "none", "#000", 0.35)
        f.rect(X(-fx - 160), Y(-fy + 160), 320 * esc, 320 * esc, "none",
               "#000", 0.2)
        f.line(X(-fx) - 2, Y(-fy), X(-fx) + 2, Y(-fy), az, 0.15)
        f.line(X(-fx), Y(-fy) - 2, X(-fx), Y(-fy) + 2, az, 0.15)
    xs = [0, C["T"], C["X_CH2"], C["X_CH2"] + C["T"], C["X_CH1"],
          C["X_CH1"] + C["T"], D["exaustores"][0][0], LX - C["T"], LX]
    ys = [0, C["T"], C["YT"], D["exaustores"][0][1], D["exaustores"][1][1],
          C["YF"], C["Y_FR"], LY]
    ordenadas_h(f, [(X(-x), fmt(x), az) for x in xs], Y(lim[2]) + 1.0)
    ordenadas_v(f, [(Y(-y), fmt(y), az) for y in ys], X(lim[0]) - 1.0)
    f.text(26, 160, "Cotas acumuladas: X a partir da face externa do lado "
           "do escapamento (direita do desenho); Y a partir da face de "
           "trás (topo do desenho).", 2.3)
    f.text(26, 165, f"Folhas de porta de {fmt(C['XFE'] - C['PX0'])} com "
           f"{fmt(C['XFD'] - C['XFE'])} de folga no centro, coberta pela "
           "mata-junta. No capuz: 2 exaustores Ø300 e 2 chicanas com "
           "revestimento nas duas faces.", 2.3)
    f.text(26, 170, "Saída de ar quente pela veneziana da lateral direita "
           "do capuz, do mesmo lado do escapamento.", 2.3)
    out.append(f)

    # --- G06: detalhes de fixacao -------------------------------------------
    f = Folha("G06", "Detalhes de fixação (escala 1:2,5)",
              "cores dos parafusos conforme a legenda da folha G04")
    esc = 0.4

    def coluna(X, Y, lim, itens, larg=None):
        """Rotulos em coluna a direita da janela: itens = [(u, v, texto)]."""
        u0, u1, v0, v1 = lim
        itens = sorted(itens, key=lambda t: -t[1])
        passo = (Y(v0) - Y(v1) - 4) / max(1, len(itens) - 1)
        for i, (u, v, txt) in enumerate(itens):
            rotulo(f, X(u), Y(v), X(u1) + 3, Y(v1) + 2 + i * passo, txt)

    f.text(12, 16, "Detalhe 1 — canto inferior traseiro", 2.7, bold=True)
    f.text(12, 20, "corte B-B", 2.2, cor="#555")
    jan = (-12, 120, 0, 150)
    X, Y, lim = desenha(f, '+x', 900, 12, 84, esc, janela=jan, parafusos=130,
                        gerador=False)
    coluna(X, Y, lim, [
        (9, 142, "traseira inferior 18"), (30, 126, "sarrafo 40 × 40"),
        (0, 118, "4,5 × 40 a cada 200"), (95, 89, "base 18"),
        (38, 70, "5,0 × 80 a cada 250"), (50, 40, "longarina 45 × 70"),
        (60, 5, "calço de borracha 10")])

    f.text(104, 16, "Detalhe 2 — soleira das portas", 2.7, bold=True)
    f.text(104, 20, "corte B-B", 2.2, cor="#555")
    jan = (1480, 1612, 0, 170)
    X, Y, lim = desenha(f, '+x', 900, 104, 92, esc, janela=jan,
                        parafusos=130, gerador=False)
    coluna(X, Y, lim, [
        (1591, 165, "folha de porta 18"), (1576, 152, "vão do EPDM 12"),
        (1561, 140, "batente inferior 18 × 60"),
        (1570, 118, "4,5 × 40, sem cola"), (1520, 126, "sarrafo 40 × 40"),
        (1595, 89, "base 18"), (1532, 60, "5,0 × 80 a cada 250"),
        (1545, 35, "longarina 45 × 70")])

    f.text(196, 16, "Detalhe 3 — emenda da traseira e teto", 2.7, bold=True)
    f.text(196, 20, "corte B-B", 2.2, cor="#555")
    jan = (-12, 150, 1590, 1850)
    X, Y, lim = desenha(f, '+x', 900, 196, 128, esc, janela=jan,
                        parafusos=130, gerador=False)
    coluna(X, Y, lim, [
        (38, 1822, "5,0 × 80"), (50, 1800, "sarrafo do capuz"),
        (120, 1773, "teto 18"), (50, 1744, "sarrafo da câmara"),
        (0, 1744, "4,5 × 40"), (9, 1700, "traseira superior"),
        (27, 1670, "régua 18 × 100"), (0, 1633, "4,0 × 30"),
        (9, 1610, "traseira inferior")])

    f.text(12, 104, "Detalhe 4 — canto da frente, lado do escapamento", 2.7,
           bold=True)
    f.text(12, 108, "planta, corte C-C", 2.2, cor="#555")
    jan = (-140, 12, -1612, -1490)
    X, Y, lim = desenha(f, '+z', 1000, 12, 160, esc, janela=jan,
                        parafusos=130, gerador=False)
    coluna(X, Y, lim, [
        (-9, -1500, "lateral 18"), (-0, -1532, "4,5 × 40"),
        (-45, -1525, "montante 40 × 40"), (-85, -1561, "batente 18 × 80"),
        (-38, -1576, "calço 12 × 40"), (-25, -1591, "guarnição 18 × 60"),
        (-46, -1600, "5,0 × 70"), (-110, -1591, "folha de porta 18")])
    f.text(112, 134, "Regras gerais de fixação", 3.0, bold=True)
    notas = [
        "1. Toda junta estrutural leva cola PU e parafuso inox; exceções: tampa do capuz e batente",
        "    inferior, que são removíveis e vão só parafusados.",
        "2. Parafusos a cada 200 mm no máximo, o primeiro a 50 mm da ponta do sarrafo.",
        "3. Na chapa: furo passante Ø5 escareado. No sarrafo: pré-furo Ø3 com 2/3 do comprimento.",
        "4. Linha de furos a 38 mm da borda externa da chapa (eixo do sarrafo de 40 encostado na",
        "    parede de 18). Onde duas linhas se cruzam no mesmo sarrafo, desencontrar 20 mm.",
        "5. Sarrafos 40 × 40 de madeira seca tratada. Se a medida real for outra, manter a face que",
        "    encosta na chapa e ajustar o revestimento.",
        "6. Dobradiças: parafusos 5,0 × 70 atravessando guarnição, calço e batente até o montante.",
        "7. Selar com PU40 todas as juntas por dentro antes de aplicar a lã de rocha.",
    ]
    for i, t in enumerate(notas):
        f.text(112, 139.5 + i * 4.1, t, 2.3)
    out.append(f)
    return out


# ----------------------------------------------------------------------------
# Tabelas
# ----------------------------------------------------------------------------
def folha_tabelas(grupos):
    f = Folha("G07", "Lista de peças, sarrafos e parafusos")
    y = 16.0
    f.text(10, y, "Compensado naval 18 mm", 3.0, bold=True)
    col = [10, 22, 104, 116]
    for i, t in enumerate(("Folha", "Peça", "Qtd", "Medida")):
        f.text(col[i], y + 5, t, 2.3, bold=True)
    for k, g in enumerate(grupos):
        yy = y + 9 + k * 3.7
        f.text(col[0], yy, g["cod"], 2.2)
        f.text(col[1], yy, g["nome"], 2.2)
        f.text(col[2], yy, str(len(g["pecas"])), 2.2)
        f.text(col[3], yy, f'{fmt(g["w"])} × {fmt(g["h"])}', 2.2)
    x = 152.0
    f.text(x, y, "Madeira maciça e apoios", 3.0, bold=True)
    linhas = tabela_macicos()
    for i, t in enumerate(("Seção", "Comprimento", "Qtd", "Onde")):
        f.text(x + (0, 26, 48, 58)[i], y + 5, t, 2.3, bold=True)
    for k, (sec, comp, n, onde) in enumerate(linhas):
        yy = y + 9 + k * 3.7
        f.text(x, yy, sec, 2.2)
        f.text(x + 26, yy, fmt(comp), 2.2)
        f.text(x + 48, yy, str(n), 2.2)
        f.text(x + 58, yy, onde[:52], 2.0)
    y2 = y + 14 + len(linhas) * 3.7
    f.text(x, y2, "Parafusos inox (cabeça chata, rosca soberba)", 3.0,
           bold=True)
    cont = collections.Counter(q["tipo"] for q in D["parafusos"])
    for k, (tipo, n) in enumerate(sorted(cont.items())):
        yy = y2 + 5 + k * 3.7
        f.circ(x + 1, yy - 0.8, 0.8, COR_PARAF[tipo], COR_PARAF[tipo], 0.1)
        f.text(x + 4, yy, tipo, 2.2)
        f.text(x + 58, yy, f"{n} no modelo", 2.2)
    return f


SECAO = {"sarrafo": "40 × 40", "longarina": "45 × 70", "calco": "12 × 40",
         "borracha": "120 × 60 × 10"}
ONDE = [("Capuz_Vertical", "cantos do capuz"),
        ("Capuz_Chicana", "fixação das chicanas"),
        ("Capuz_Inferior", "capuz, junto ao piso do capuz"),
        ("Capuz_Superior", "capuz, junto à tampa"),
        ("Vertical_Traseiro", "cantos de trás da câmara"),
        ("Montante_Frontal", "montantes da frente (dobradiças)"),
        ("Divisoria_Vertical", "divisória, na traseira"),
        ("Divisoria_Base", "divisória, no piso"),
        ("Divisoria_Travessa", "travessa no topo da divisória"),
        ("Inferior", "câmara, junto ao piso"),
        ("Superior", "câmara, junto ao teto"),
        ("Longarina", "apoio sob a base"),
        ("Calco_Guarnicao", "entre guarnição e batente"),
        ("Calco_Borracha", "sob as longarinas")]


def tabela_macicos():
    g = collections.OrderedDict()
    for p in D["pecas"]:
        if p["tipo"] == "compensado":
            continue
        bb = p["bbox"]
        comp = max(bb[1] - bb[0], bb[3] - bb[2], bb[5] - bb[4])
        onde = next(t for k, t in ONDE if k in p["obj"])
        chave = (SECAO[p["tipo"]], round(comp, 1), onde)
        g[chave] = g.get(chave, 0) + 1
    return sorted(((s, c, n, o) for (s, c, o), n in g.items()),
                  key=lambda t: (t[0], -t[1]))


def markdown(grupos):
    o = ["# Lista de peças, sarrafos e parafusos",
         "",
         "Arquivo gerado por `desenhos_tecnicos.py` a partir do modelo 3D. "
         "Não editar à mão. Medidas em milímetros.",
         "",
         "## Compensado naval 18 mm",
         "",
         "| Folha | Peça | Qtd | Medida | Furos | Recortes |",
         "|---|---|---|---|---|---|"]
    for g in grupos:
        rec = "; ".join(f"{r[5]}" for r in g["recortes"]) or "—"
        o.append(f'| {g["cod"]} | {g["nome"]} | {len(g["pecas"])} | '
                 f'{fmt(g["w"])} × {fmt(g["h"])} | {len(g["furos"])} | '
                 f'{rec} |')
    o += ["", "## Madeira maciça, calços e apoios", "",
          "| Seção | Comprimento | Qtd | Onde |", "|---|---|---|---|"]
    total = collections.Counter()
    for sec, comp, n, onde in tabela_macicos():
        o.append(f"| {sec} | {fmt(comp)} | {n} | {onde} |")
        total[sec] += comp * n
    o += ["", "Comprimento total por seção (sem perdas):", ""]
    for sec, t in total.items():
        if sec != SECAO["borracha"]:
            o.append(f"- {sec}: {t / 1000:.1f} m".replace(".", ","))
    o += ["", "## Parafusos por junta", "",
          "| Junta | Parafuso | Qtd |", "|---|---|---|"]
    cont = collections.Counter((q["junta"], q["tipo"]) for q in D["parafusos"])
    for (junta, tipo), n in sorted(cont.items()):
        o.append(f"| {junta} | {tipo} | {n} |")
    o += ["", "Total por tipo:", ""]
    for tipo, n in sorted(collections.Counter(
            q["tipo"] for q in D["parafusos"]).items()):
        o.append(f"- {tipo}: {n}")
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for a in os.listdir(OUT):
        if a.endswith((".svg", ".html", ".pdf")):
            os.remove(os.path.join(OUT, a))
    grupos = grupos_de_pecas()
    folhas = folhas_conjunto() + [folha_tabelas(grupos)] + \
        [folha_peca(g) for g in grupos if g["furos"] or g["recortes"]]
    html = ['<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            '<title>Desenhos técnicos da cabine acústica</title><style>'
            '@page{size:A4 landscape;margin:0}body{margin:0}'
            'svg{display:block;width:297mm;height:210mm;'
            'page-break-after:always}</style></head><body>']
    for i, f in enumerate(folhas, 1):
        s = f.svg(i, len(folhas))
        nome = f"{f.codigo}_" + "".join(
            c if c.isalnum() else "_" for c in f.titulo.lower())[:48]
        with open(os.path.join(OUT, nome.rstrip("_") + ".svg"), "w",
                  encoding="utf-8") as fh:
            fh.write(s)
        html.append(s)
    html.append("</body></html>")
    pagina = os.path.join(OUT, "desenhos.html")
    with open(pagina, "w", encoding="utf-8") as fh:
        fh.write("\n".join(html))
    with open(os.path.join(ESP, "lista_de_pecas.md"), "w",
              encoding="utf-8") as fh:
        fh.write(markdown(grupos))
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if chrome:
        pdf = os.path.join(OUT, "desenhos_tecnicos.pdf")
        subprocess.run([chrome, "--headless", "--disable-gpu",
                        "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                        "file://" + pagina], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("PDF:", pdf, os.path.exists(pdf))
    print(len(folhas), "folhas em", OUT)
