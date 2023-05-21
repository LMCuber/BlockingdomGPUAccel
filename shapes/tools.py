from settings import *


def get_crystal(type_, color=None):
    with open(path("Images", "Vertices", f"{type_}.json"), "r") as f:
        crystal_data = json.load(f)
    bcc = Crystal(
        win.renderer,
        crystal_data["vertices"],
        crystal_data["point_colors"] if color is None else [color] * len(crystal_data["vertices"]),
        crystal_data["connections"],
        [],
        (300, 300), 25, 4, 0, 0, 0, 0.0005, 0.0005, 0.0005
    )
    return bcc


def get_sword(base_color):
    w, l, h = 0.12, 0.8, 0.03
    tl = 0.3
    gw, gl, gh = 0.24, 0.1, 0.1
    gxo = l
    uw, ul, uh = 0.05, 0.4, 0.05
    uxo = gxo
    sword_atoms = []
    body_color = (235, 235, 235, 0)
    sword = Crystal(
        win.renderer, [
            # base
            [-w, -l - tl, h],
            [w, -l, h],
            [w, l, h],
            [-w, l, h],
            [-w, -l - tl, -h],
            [w, -l, -h],
            [w, l, -h],
            [-w, l, -h],

            # tip
            [-w, -l - tl, h],
            [w, -l, h],
            [-w, -l, h],
            [-w, -l - tl, -h],
            [w, -l, -h],
            [-w, -l, -h],

            # guard
            [-gw, gxo, gh],
            [gw, gxo, gh],
            [gw, gxo + gl, gh],
            [-gw, gxo + gl, gh],
            [-gw, gxo, -gh],
            [gw, gxo, -gh],
            [gw, gxo + gl, -gh],
            [-gw, gxo + gl, -gh],

            # grip
            [-uw, uxo, uh],
            [uw, uxo, uh],
            [uw, uxo + ul, uh],
            [-uw, uxo + ul, uh],
            [-uw, uxo, -uh],
            [uw, uxo, -uh],
            [uw, uxo + ul, -uh],
            [-uw, uxo + ul, -uh],

            # the polygons
            # PASS
        ], [
            # point colors
        ], [
            # lines
        ], [
            # fills
            # base
            [body_color, 0, 1, 2, 3],
            [body_color, 4, 5, 1, 0],
            [body_color, 4, 5, 6, 7],
            [body_color, 7, 6, 2, 3],
            [body_color, 4, 0, 3, 7],
            [body_color, 1, 5, 6, 2],

            # tip
            # [body_color, 0 + 8, 1 + 8, 2 + 8],
            # [body_color, 3 + 8, 4 + 8, 5 + 8],
            # [body_color, 3 + 8, 0 + 8, 2 + 8, 5 + 8],
            # [body_color, 0 + 8, 3 + 8, 4 + 8, 1 + 8],
            # [body_color, 5 + 8, 4 + 8, 1 + 8, 2 + 8],

            # guard
            [body_color, 0 + 14, 1 + 14, 2 + 14, 3 + 14],
            [body_color, 4 + 14, 5 + 14, 1 + 14, 0 + 14],
            [body_color, 4 + 14, 5 + 14, 6 + 14, 7 + 14],
            [body_color, 7 + 14, 6 + 14, 2 + 14, 3 + 14],
            [body_color, 4 + 14, 0 + 14, 3 + 14, 7 + 14],
            [body_color, 1 + 14, 5 + 14, 6 + 14, 2 + 14],

            # grip
            [body_color, 0 + 22, 1 + 22, 2 + 22, 3 + 22],
            [body_color, 4 + 22, 5 + 22, 1 + 22, 0 + 22],
            [body_color, 4 + 22, 5 + 22, 6 + 22, 7 + 22],
            [body_color, 7 + 22, 6 + 22, 2 + 22, 3 + 22],
            [body_color, 4 + 22, 0 + 22, 3 + 22, 7 + 22],
            [body_color, 1 + 22, 5 + 22, 6 + 22, 2 + 22],
        ],
        (300, 300), 140, 2, 0, 0, 0, 0, 0.0005, 0
    )
    """
    sxo, syo = -w, -l
    sw, sl, sh = w / 2, w / 2, h
    sword_atom_shapes = [
        [[0, 0, 1], [1, 0, 1], [0, 1, 1]],
        [[1, 0, 1], [2, 0, 1], [2, 1, 1]],
        [[1, 0, 1], [1, 2, 1], [0, 1, 1]],
        [[0, 1, 1], [2, 1, 1], [1, 2, 1]],
        [[0, 1, 1], [1, 2, 1], [0, 2, 1]],
        [[2, 1, 1], [2, 2, 1], [1, 2, 1]]
    ]
    """
    return sword


def get_axe(base_color):
    w, l, h = 0.05, 0.8, 0.05
    hw, hh = 0.4, 0.25
    body_color = (235, 235, 235, 0)
    axe = Crystal(
        win.renderer, [
            # base
            [-w, -l, h],
            [w, -l, h],
            [w, l, h],
            [-w, l, h],
            [-w, -l, -h],
            [w, -l, -h],
            [w, l, -h],
            [-w, l, -h],

            # head-back
            [w, -l, h],
            [w + hw, -l + hh * 0.25, h],
            [w, -l + hh * 0.5, h],
            # head-front
            # down
            [-w, -l + hh * 0.4, h],
            [-w - hw * 0.4, -l + hh * 0.4, h],
            [-w - hw * 0.8, -l + hh, h],
            [-w - hw, -l + hh * 0.4, h],
            # up
            [-w - hw * 0.8, -l - hh * 0.2, h],
            [-w - hw * 0.6, -l, h],
            [-w, -l, h],
        ], [
            # point colors
        ], [
            # lines
        ], [
            # fills
            # base
            [body_color, 0, 1, 2, 3],
            [body_color, 4, 5, 1, 0],
            [body_color, 4, 5, 6, 7],
            [body_color, 7, 6, 2, 3],
            [body_color, 4, 0, 3, 7],
            [body_color, 1, 5, 6, 2],

            # head
            [body_color, 8, 9, 10],
            [body_color, 11, 12, 13, 14],
            [body_color, 14, 15, 16, 17],
        ],
        (300, 300), 140, 2, 0, 0, 0, 0, 0.0005, 0
    )
    return axe


#
def get_tool_crafter():
    tool_crafter_img = timgload3("Images", "Midblits", "tool-crafter.png")
    w, h = 550, 350
    tool_crafter_img = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(tool_crafter_img, (*NAVY_BLUE[:3], 220), (0, 0, w, h))
    pygame.draw.rect(tool_crafter_img, NAVY_BLUE, (0, 0, tool_crafter_sword_width, h))
    pygame.draw.rect(tool_crafter_img, BLACK, (0, 0, w, h), 3)
    pygame.draw.rect(tool_crafter_img, BLACK, (0, 0, tool_crafter_sword_width, h), 3)
    # write(tool_crafter_img, "topleft", "wt% Fe", orbit_fonts[16], BLACK, 136, 8)
    # write(tool_crafter_img, "topleft", "wt% C", orbit_fonts[16], BLACK, 220, 8)
    pygame.image.save(tool_crafter_img, path("Images", "Surfaces", "tool-crafter.png"))
# get_tool_crafter()
