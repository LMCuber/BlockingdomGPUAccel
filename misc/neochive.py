# # MOUSE ICON
from pyengine.pgbasics import *
w, h = 10 * 3, 15 * 3
br = int(30 / 1.5)
img = pygame.Surface((w, h), pygame.SRCALPHA)
pygame.draw.rect(img, WHITE, (0, 0, w, h), 0, 0, 7, 7, br, br)
pygame.draw.rect(img, BLACK, (0, 0, w, h), 1, 0, 7, 7, br, br)
pygame.draw.line(img, BLACK, (0, int(h * 0.4) - 1), (w, int(h * 0.4) - 1))
pygame.draw.rect(img, ORANGE, (w / 2, 0, w / 2, int(h * 0.4)), 0, 0, 0, 6)
pygame.draw.rect(img, BLACK, (w / 2, 0, w / 2, int(h * 0.4)), 1, 0, 0, 5)
pygame.draw.rect(img, WHITE, (w / 2 - 3, 6, 6, 15), 0, 5)
pygame.draw.rect(img, BLACK, (w / 2 - 3, 6, 6, 15), 1, 5)
# pg_to_pil(img).show()
pygame.image.save(img, "assets/Images/Visuals/mouse.png")
