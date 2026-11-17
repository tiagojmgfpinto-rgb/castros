"""Junta as capturas de tests/antes_depois.mjs numa imagem por página/secção: em cima o computador (antes | depois),
em baixo o telemóvel (antes | depois). Uso: python3 tests/compor_antes_depois.py <pasta antes> <pasta depois> <saída>"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

A, D, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
F = '/usr/share/fonts/truetype/dejavu/'
f_tit = ImageFont.truetype(F + 'DejaVuSerif-Bold.ttf', 40)
f_lab = ImageFont.truetype(F + 'DejaVuSans.ttf', 26)
f_nada = ImageFont.truetype(F + 'DejaVuSans.ttf', 30)
PAPEL, TINTA, GULES = (236, 228, 210), (40, 32, 24), (150, 40, 28)

SECCOES = [
    ('01-mapa', 'Mapa (página inicial)'),
    ('02-indice', 'Índice'),
    ('03-distritos', 'Distritos'),
    ('04-novidades', 'Novidades'),
    ('05-fontes', 'Fontes e método'),
    ('06-caderno', 'Caderno (só no site antigo)'),
    ('07-ficha-com-maqueta', 'Ficha lateral com maqueta 3D (Citânia de Briteiros)'),
    ('08-ficha-sem-maqueta', 'Ficha lateral de um castro sem maqueta (Castro do Pópulo)'),
    ('09-catalogo', 'Catálogo de todos os castros'),
    ('10-pagina-com-maqueta', 'Página permanente com maqueta (Citânia de Briteiros)'),
    ('11-pagina-sem-maqueta', 'Página permanente sem maqueta (Castro do Pópulo)'),
    ('12-proximas-adicoes', 'Próximas adições (só no site novo)'),
    ('13-creditos', 'Créditos e licenças'),
]
NOTA_FALTA = {
    'antes': 'Não existia no site antigo',
    'depois': 'Não existe no site dos Castelos',
}


def abrir(pasta, nome, vp):
    p = os.path.join(pasta, f'{nome}-{vp}.png')
    return Image.open(p).convert('RGB') if os.path.exists(p) else None


def caixa(img, w, h, lado):
    """Imagem reduzida para caber em w×h, ou um cartão a dizer que a secção não existe."""
    c = Image.new('RGB', (w, h), PAPEL)
    if img is None:
        d = ImageDraw.Draw(c)
        t = NOTA_FALTA[lado]
        tw = d.textlength(t, font=f_nada)
        d.text(((w - tw) / 2, h / 2 - 18), t, fill=(120, 105, 85), font=f_nada)
        return c
    k = min(w / img.width, h / img.height)
    im = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
    c.paste(im, ((w - im.width) // 2, 0))
    return c


for nome, titulo in SECCOES:
    a_d, d_d = abrir(A, nome, 'desk'), abrir(D, nome, 'desk')
    a_p, d_p = abrir(A, nome, 'phone'), abrir(D, nome, 'phone')
    W, M = 1440, 30
    # altura da fila do computador: a da captura mais alta, reduzida a W
    hd = max([round(i.height * W / i.width) for i in (a_d, d_d) if i] or [900])
    hd = min(hd, 2200)
    PW = 520
    hp = max([round(i.height * PW / i.width) for i in (a_p, d_p) if i] or [1100])
    hp = min(hp, 2400)
    larg = 2 * W + 3 * M
    alt = 90 + 50 + hd + 70 + 50 + hp + M
    tela = Image.new('RGB', (larg, alt), (250, 246, 236))
    d = ImageDraw.Draw(tela)
    d.text((M, 22), titulo, fill=TINTA, font=f_tit)
    y = 90
    for lado, x in (('ANTES · site antigo', M), ('DEPOIS · base dos Castelos', 2 * M + W)):
        d.text((x, y), f'{lado} · computador', fill=GULES, font=f_lab)
    y += 50
    tela.paste(caixa(a_d, W, hd, 'antes'), (M, y))
    tela.paste(caixa(d_d, W, hd, 'depois'), (2 * M + W, y))
    y += hd + 70
    for lado, x in (('ANTES · site antigo', M), ('DEPOIS · base dos Castelos', 2 * M + W)):
        d.text((x, y - 50), f'{lado} · telemóvel', fill=GULES, font=f_lab)
    tela.paste(caixa(a_p, PW, hp, 'antes'), (M + (W - PW) // 2, y))
    tela.paste(caixa(d_p, PW, hp, 'depois'), (2 * M + W + (W - PW) // 2, y))
    # reduzir para um tamanho que se lê no telemóvel sem pesar demasiado
    k = 2200 / tela.width
    tela = tela.resize((2200, round(tela.height * k)), Image.LANCZOS)
    tela.save(os.path.join(OUT, f'{nome}.jpg'), quality=82, optimize=True, progressive=True)
    print(nome, tela.size)
