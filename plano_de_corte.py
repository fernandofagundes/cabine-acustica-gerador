"""
Plano de corte do compensado naval 18 mm (chapas de 2200 x 1600 mm) da cabine
acustica do gerador. Confere se as pecas cabem e nao se sobrepoem e desenha
um SVG por conjunto.

  python3 plano_de_corte.py
"""
import os

CHAPA = (2200, 1600)
SERRA = 4            # folga de corte entre pecas (mm)

# (nome, largura_x, altura_y, x, y, observacao) - posicao na chapa, em mm
CHAPAS = [
    ("Chapa 1", [
        ("Base (piso)", 2000, 1600, 0, 0, ""),
        ("Chicana 1 do capuz", 182, 1464, 2004, 0, ""),
    ]),
    ("Chapa 2", [
        ("Teto da câmara", 2000, 1582, 0, 0, "2 furos Ø300"),
        ("Batente lateral", 80, 1546, 2004, 0, ""),
        ("Batente lateral", 80, 1546, 2088, 0, ""),
    ]),
    ("Chapa 3", [
        ("Tampa do capuz (chapa inteira)", 2200, 1600, 0, 0,
         "beiral de 100 mm sobre as venezianas"),
    ]),
    ("Chapa 4", [
        ("Traseira inferior", 2000, 1560, 0, 0, ""),
        ("Quadro da lã vertical", 50, 1542, 2004, 0, ""),
        ("Quadro da lã vertical", 50, 1542, 2058, 0, ""),
        ("Quadro da lã vertical", 50, 1542, 2112, 0, ""),
    ]),
    ("Chapa 5", [
        ("Lateral da entrada de ar frio", 1666, 1564, 0, 0,
         "recorte 1100 x 400"),
        ("Capuz: lateral da saída quente", 320, 1564, 1670, 0,
         "recorte 1300 x 220"),
        ("Chicana 2 do capuz", 198, 1464, 1994, 0, ""),
    ]),
    ("Chapa 6", [
        ("Lateral do escapamento", 1666, 1564, 0, 0, "furo Ø150"),
        ("Capuz: lateral fechada", 320, 1564, 1670, 0, ""),
        ("Quadro da lã vertical", 50, 1542, 1994, 0, ""),
        ("Quadro da lã horizontal", 50, 828, 2048, 0, ""),
        ("Quadro da lã horizontal", 50, 828, 2102, 0, ""),
    ]),
    ("Chapa 7", [
        ("Divisória do labirinto de entrada", 1514, 1402, 0, 0, ""),
        ("Mata-junta", 60, 1542, 1888, 0, ""),
        ("Régua de emenda da traseira", 1884, 100, 0, 1406, ""),
        ("Quadro da lã horizontal", 828, 50, 0, 1510, ""),
        ("Quadro da lã horizontal", 828, 50, 832, 1510, ""),
    ]),
    ("Chapa 8", [
        ("Folha de porta passiva", 1658, 936, 0, 0, ""),
        ("Traseira superior", 2000, 444, 0, 940, ""),
        ("Batente inferior", 1964, 60, 0, 1388, ""),
        ("Batente superior", 1964, 60, 0, 1452, ""),
    ]),
    ("Chapa 9", [
        ("Folha de porta ativa", 1658, 936, 0, 0, ""),
        ("Capuz: frente", 2000, 320, 0, 940, ""),
        ("Guarnição lateral", 1666, 60, 0, 1264, ""),
        ("Guarnição lateral", 1666, 60, 0, 1328, ""),
    ]),
]


def conferir():
    erros = []
    for chapa, pecas in CHAPAS:
        for i, (n, w, h, x, y, _) in enumerate(pecas):
            if x < 0 or y < 0 or x + w > CHAPA[0] or y + h > CHAPA[1]:
                erros.append(f"{chapa}: '{n}' sai da chapa")
            for n2, w2, h2, x2, y2, _ in pecas[i + 1:]:
                livre = (x + w + SERRA <= x2 or x2 + w2 + SERRA <= x or
                         y + h + SERRA <= y2 or y2 + h2 + SERRA <= y)
                if not livre:
                    erros.append(f"{chapa}: '{n}' encosta/sobrepoe '{n2}'")
    return erros


def area_usada(pecas):
    return sum(w * h for _, w, h, _, _, _ in pecas) / 1e6


def svg():
    esc = 0.25
    mx, my, gap = 30, 50, 70
    cols = 3
    cw, chh = CHAPA[0] * esc, CHAPA[1] * esc
    linhas = (len(CHAPAS) + cols - 1) // cols
    W = mx * 2 + cols * cw + (cols - 1) * gap
    H = my + linhas * (chh + gap)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" '
         f'height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" '
         f'font-family="sans-serif">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>',
         f'<text x="{mx}" y="26" font-size="18" font-weight="bold" '
         f'fill="#222">Plano de corte — compensado naval 18 mm, chapas '
         f'2200 × 1600 mm (medidas em mm)</text>']
    for k, (chapa, pecas) in enumerate(CHAPAS):
        ox = mx + (k % cols) * (cw + gap)
        oy = my + (k // cols) * (chh + gap) + 20
        uso = 100 * area_usada(pecas) / (CHAPA[0] * CHAPA[1] / 1e6)
        o.append(f'<text x="{ox:.0f}" y="{oy - 6:.0f}" font-size="14" '
                 f'font-weight="bold" fill="#222">{chapa} — '
                 f'aproveitamento {uso:.0f}%</text>')
        o.append(f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{cw:.1f}" '
                 f'height="{chh:.1f}" fill="#eeeeee" stroke="#555" '
                 f'stroke-width="1.5"/>')
        for n, w, h, x, y, obs in pecas:
            px, py, pw, ph = ox + x * esc, oy + y * esc, w * esc, h * esc
            o.append(f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" '
                     f'height="{ph:.1f}" fill="#e3c58f" stroke="#6b4a1e" '
                     f'stroke-width="1"/>')
            cx, cy = px + pw / 2, py + ph / 2
            estreita = pw < 100
            baixa = ph < 26
            if estreita:
                o.append(f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="9" '
                         f'fill="#222" text-anchor="middle" '
                         f'transform="rotate(-90 {cx:.1f} {cy:.1f})" '
                         f'dominant-baseline="middle">{n} {w}×{h}</text>')
            elif baixa:
                o.append(f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="9" '
                         f'fill="#222" text-anchor="middle" '
                         f'dominant-baseline="middle">{n} {w}×{h}</text>')
            else:
                o.append(f'<text x="{cx:.1f}" y="{cy - 8:.1f}" '
                         f'font-size="11" fill="#222" text-anchor="middle">'
                         f'{n}</text>')
                o.append(f'<text x="{cx:.1f}" y="{cy + 7:.1f}" '
                         f'font-size="11" font-weight="bold" fill="#222" '
                         f'text-anchor="middle">{w} × {h}</text>')
                if obs:
                    o.append(f'<text x="{cx:.1f}" y="{cy + 21:.1f}" '
                             f'font-size="9" fill="#555" '
                             f'text-anchor="middle">{obs}</text>')
    o.append('</svg>')
    return "\n".join(o)


if __name__ == "__main__":
    erros = conferir()
    for e in erros:
        print("ERRO:", e)
    total = 0.0
    for chapa, pecas in CHAPAS:
        a = area_usada(pecas)
        total += a
        print(f"{chapa}: {len(pecas)} pecas, {a:.2f} m2 "
              f"({100 * a / 3.52:.0f}%)")
    print(f"Total de pecas: {total:.2f} m2 em {len(CHAPAS)} chapas "
          f"({len(CHAPAS) * 3.52:.2f} m2)")
    pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "Especificações")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "plano_de_corte.svg")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(svg())
    print("Desenho:", caminho, "| erros:", len(erros))
