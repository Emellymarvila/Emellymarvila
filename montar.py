# -*- coding: utf-8 -*-
"""
Monta as imagens do README do perfil do GitHub (imagem única, fatiada para os cliques).

Como usar:
  1) Ícones de stacks: PNG/WEBP em  icones/  (html5, css3, javascript, c, figma, canva, excel)
  2) Fotos dos projetos: em  projetos/  com os nomes
        organizador-de-referencias.(png|jpg|webp)   tradutor-de-livros.(png|jpg|webp)
  3) Rode:  python montar.py      (precisa de:  pip install pillow numpy scipy)
  4) Envie para o GitHub: README.md + a pasta imagens/

Arquivos em fontes/:  fundo-limpo.png (sem nada nos espaços)  e  referencia.png (com os quadrados vermelhos).
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

AQUI = Path(__file__).parent
FONTES, ICONES, PROJ, SAIDA = (AQUI / p for p in ("fontes", "icones", "projetos", "imagens"))
SAIDA.mkdir(exist_ok=True)

ORDEM_ICONES = ["html5", "css3", "javascript", "c", "figma", "canva", "excel"]   # esquerda->direita, cima->baixo
NOMES_CARDS = ["organizador-de-referencias", "tradutor-de-livros"]                # esquerda->direita
ICON = 76                                                                        # tamanho do ícone no quadrado

# cortes (pixels da arte 2048x1520)
Y_CONTATOS = (592, 692)                  # faixa onde ficam LinkedIn e e-mail
X_CONTATOS = (1190, 1482, 1740)          # início do LinkedIn | início do e-mail | fim do e-mail
Y_PROJETOS = 878                         # a partir daqui ficam os cards (dois links)


def abrir_icone(nome):
    for ext in ("png", "webp", "PNG", "WEBP"):
        f = ICONES / f"{nome}.{ext}"
        if f.exists():
            return Image.open(f).convert("RGBA")
    svg = ICONES / f"{nome}.svg"
    if svg.exists():
        try:
            import cairosvg, io
            return Image.open(io.BytesIO(cairosvg.svg2png(url=str(svg), output_width=256))).convert("RGBA")
        except ImportError:
            print(f"! {svg.name}: para usar SVG rode  pip install cairosvg  (ou exporte como PNG)")
    print(f"! ícone '{nome}' não encontrado em icones/")
    return None


def cobrir(img, w, h):
    r = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def foto_projeto(nome, w, h):
    for ext in ("png", "jpg", "jpeg", "webp"):
        f = PROJ / f"{nome}.{ext}"
        if f.exists():
            return cobrir(Image.open(f).convert("RGB"), w, h)
    ph = Image.new("RGB", (w, h), (233, 235, 245))
    d = ImageDraw.Draw(ph)
    try:
        fonte = ImageFont.truetype("DejaVuSans.ttf", 34)
    except OSError:
        fonte = ImageFont.load_default()
    txt = "foto do projeto aqui"
    d.text(((w - d.textlength(txt, font=fonte)) / 2, h / 2 - 20), txt, fill=(120, 126, 160), font=fonte)
    print(f"! sem foto para '{nome}' (espaço reservado) -> projetos/{nome}.png")
    return ph


# --- 1) base = referência, com os quadrados vermelhos trocados pelo fundo limpo
ref = Image.open(FONTES / "referencia.png").convert("RGB")
limpo = Image.open(FONTES / "fundo-limpo.png").convert("RGB")
a = np.array(ref).astype(int)
vermelho = (a[:, :, 0] > 245) & (a[:, :, 1] < 10) & (a[:, :, 2] < 10)
lab, n = ndi.label(vermelho)
caixas = []
for s in ndi.find_objects(lab):
    caixas.append((s[1].start, s[0].start, s[1].stop, s[0].stop))
vermelho_png = Image.fromarray((ndi.binary_dilation(vermelho, iterations=1) * 255).astype("uint8"))
base = Image.composite(limpo, ref, vermelho_png).convert("RGBA")

slots = sorted([c for c in caixas if (c[2] - c[0]) < 300], key=lambda c: (round(c[1] / 100), c[0]))
cards = sorted([c for c in caixas if (c[2] - c[0]) >= 300], key=lambda c: c[0])

# --- 2) ícones nos quadrados
for nome, (x0, y0, x1, y1) in zip(ORDEM_ICONES, slots):
    ic = abrir_icone(nome)
    if ic is None:
        continue
    ic.thumbnail((ICON, ICON), Image.LANCZOS)
    base.alpha_composite(ic, (x0 + (x1 - x0 - ic.width) // 2, y0 + (y1 - y0 - ic.height) // 2))

# --- 3) fotos dos projetos
base = base.convert("RGB")
for nome, (x0, y0, x1, y1) in zip(NOMES_CARDS, cards):
    base.paste(foto_projeto(nome, x1 - x0, y1 - y0), (x0, y0))

# --- 4) fatias
W, H = base.size
yc0, yc1 = Y_CONTATOS
xl, xe, xf = X_CONTATOS
fatias = {
    "topo": (0, 0, W, yc0),
    "contatos-esquerda": (0, yc0, xl, yc1),
    "contato-linkedin": (xl, yc0, xe, yc1),
    "contato-email": (xe, yc0, xf, yc1),
    "contatos-direita": (xf, yc0, W, yc1),
    "meio": (0, yc1, W, Y_PROJETOS),
    "projeto-esquerda": (0, Y_PROJETOS, W // 2, H),
    "projeto-direita": (W // 2, Y_PROJETOS, W, H),
}
for nome, box in fatias.items():
    base.crop(box).save(SAIDA / f"{nome}.png", optimize=True)
    print("ok", nome, box, f"-> width=\"{(box[2]-box[0])/W*100:.2f}%\"")
