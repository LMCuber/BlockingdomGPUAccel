from pyengine.pgbasics import *
from pyengine.pilbasics import *

from PIL import Image, ImageDraw
im = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
draw = ImageDraw.Draw(im, "RGBA")
draw.rounded_rectangle((20, 20, 180, 80), 30, outline="#000")
im.save("normal.png")

factor = 5
w, h = 160, 100
im = Image.new("RGBA", (factor*w, factor*h), (0, 0, 0, 0))
draw = ImageDraw.Draw(im, "RGBA")
draw.rounded_rectangle((0, 0, factor*w, factor*h), factor*40, fill=LIGHT_GRAY)
draw.rounded_rectangle((0, 0, factor*w, factor*h), factor*40, outline=DARK_GRAY, width=14)
im = im.resize((200, 100), Image.Resampling.LANCZOS)
# im.show()
rounded = pil_to_pg(im)


def get_fonts(*p, sys=False, **kwargs):
    if not sys:
        return [pygame.font.Font(path("assets", "Fonts", *p), i) for i in range(1, 101)]
    else:
        return [pygame.font.SysFont(p[0], i, **kwargs) for i in range(1, 101)]


rounded = pygame.transform.rotozoom(rounded, 90, 1)
# pg_to_pil(rounded).show()
orbit_fonts = (get_fonts("Orbitron", "Orbitron-VariableFont_wght.ttf"))
w, h = rounded.get_size()
pw, ph = 30, 15
fracdes_img = pygame.Surface((w + pw * 2, h), pygame.SRCALPHA)
# pygame.draw.rect(fracdes_img, LIGHT_GRAY, (pw, 0, w, h), border_radius=50)
# pygame.draw.rect(fracdes_img, DARK_GRAY, (pw, 0, w, h), 3, 50)
fracdes_img.blit(rounded, (pw, 0))
pygame.draw.rect(fracdes_img, LIGHT_GRAY, (0, h / 2 - 4, pw + 8, ph))
# pygame.draw.rect(fracdes_img, (255, 0, 0), (0, 0, *fracdes_img.get_size()), 1)
gases = ("He", "Ne", "Ar", "Kr", "Xe")
colors = [(170, 170, 170), pygame.Color("green3"), pygame.Color("gray29"), pygame.Color("indianred3"), pygame.Color("yellow2")]
num = 5
for i in range(num):
    yo = h / (num + 1)
    y = int(yo + i * yo)
    pygame.draw.rect(fracdes_img, LIGHT_GRAY, (w + pw - 10, y - ph / 2, pw + 10, ph))
    # pygame.gfxdraw.filled_circle(fracdes_img, int(w + pw - 10), int(y - ph / 2), 3, colors[i])
    write(fracdes_img, "midright", gases[i], orbit_fonts[11], (0, 0, 0), w + pw * 2 - 7, y)
    if i != num - 1:
        num_lines = 10
        space = 4
        line_length = w - 10 - (num_lines - 1) * space
        line_per = line_length / num_lines
        x = pw + 8
        for lo in range(num_lines):
            # pygame.gfxdraw.hline(fracdes_img, int(x), int(x + line_per), y - ph // 2 - 3, (0, 0, 0))
            pygame.gfxdraw.hline(fracdes_img, int(x), int(x + line_per), y + ph, (0, 0, 0))
            x += line_per + space

pg_to_pil(fracdes_img).show()
pygame.image.save(fracdes_img, path("assets", "Images", "Surfaces", "frac-dest.png"))
