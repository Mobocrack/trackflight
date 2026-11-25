"""Dessine l'icône de l'application (carré arrondi bleu, avion en papier blanc) en .png, .ico et .icns."""
import os
import sys

from PIL import Image, ImageDraw

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "..", "icones")


def dessiner(taille=1024):
    s = taille
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    marge = int(s * .09)  # marge des icônes macOS
    haut, bas = (10, 132, 255), (0, 96, 223)
    for y in range(marge, s - marge):  # dégradé vertical discret
        k = (y - marge) / (s - 2 * marge)
        c = tuple(int(haut[i] + (bas[i] - haut[i]) * k) for i in range(3))
        d.line([(marge, y), (s - marge, y)], fill=c + (255,))
    masque = Image.new("L", (s, s), 0)
    ImageDraw.Draw(masque).rounded_rectangle([marge, marge, s - marge, s - marge], radius=int(s * .2), fill=255)
    fond = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    fond.paste(im, (0, 0), masque)
    d = ImageDraw.Draw(fond)
    u = s / 64  # avion en papier, dessiné sur une grille de 64
    aile = [(15 * u, 33 * u), (49 * u, 19 * u), (27 * u, 37 * u)]
    corps = [(27 * u, 37 * u), (49 * u, 19 * u), (40 * u, 46 * u)]
    pli = [(27 * u, 37 * u), (30 * u, 46 * u), (33 * u, 40.5 * u)]
    d.polygon(aile, fill=(255, 255, 255, 255))
    d.polygon(corps, fill=(232, 240, 255, 255))
    d.polygon(pli, fill=(200, 218, 250, 255))
    return fond


def main():
    os.makedirs(SORTIE, exist_ok=True)
    im = dessiner()
    im.save(os.path.join(SORTIE, "icone.png"))
    im.save(os.path.join(SORTIE, "icone.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    if "--icns" in sys.argv or sys.platform == "darwin":
        im.save(os.path.join(SORTIE, "icone.icns"))
    print("icônes écrites dans", os.path.abspath(SORTIE))


if __name__ == "__main__":
    main()
