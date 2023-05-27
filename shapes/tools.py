from settings import *



# constants
grays = [(x, x, x, 255) for x in range(1, 256)]
browns = [(int(x * 0.6), int(x * 0.4), int(x * 0.2), 255) for x in range(1, 256)]


# functions
def get_crystal(type_, color=None):
    with open(path("shapes", f"{type_}.json"), "r") as f:
        crystal_data = json.load(f)
    bcc = Crystal(
        win.renderer,
        crystal_data["vertices"],
        crystal_data["point_colors"] if color is None else [color] * len(crystal_data["vertices"]),
        crystal_data["connections"],
        [],
        (300, 300), 25, 4, 0, 0, 0, 0.015, 0.015, 0.015
    )
    return bcc


def get_sword(base_color):
    w, l, h = 0.12, 0.8, 0.03
    tl = 0.3
    gw, gl, gh = 0.24, 0.1, 0.1
    gxo = l
    uw, ul, uh = 0.05, 0.4, 0.05
    uxo = gxo
    body_color = (235, 235, 235, 255)
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
            [body_color, 0 + 8, 1 + 8, 2 + 8],
            [body_color, 3 + 8, 4 + 8, 5 + 8],
            [body_color, 3 + 8, 0 + 8, 2 + 8, 5 + 8],
            [body_color, 0 + 8, 3 + 8, 4 + 8, 1 + 8],
            [body_color, 5 + 8, 4 + 8, 1 + 8, 2 + 8],

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
        (300, 300), 140, 2, 0, 0, 0, 0, 0.015, 0,
        fill_as_connections=True
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
    hw, hh = 0.35, 0.4
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
            # (2x)
            # head-back
            [w, -l, -h],
            [w + hw, -l + hh * 0.25, -h],
            [w, -l + hh * 0.5, -h],
            # head-front
            # down
            [-w, -l + hh * 0.4, -h],
            [-w - hw * 0.4, -l + hh * 0.4, -h],
            [-w - hw * 0.8, -l + hh, -h],
            [-w - hw, -l + hh * 0.4, -h],
            # up
            [-w - hw * 0.8, -l - hh * 0.2, -h],
            [-w - hw * 0.6, -l, -h],
            [-w, -l, -h],
        ], [
            # point colors
        ], [
            # connections
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
            [body_color, 11, 12, 13, 14, 15, 16, 17],
            [body_color, 18, 19, 20],
            [body_color, 21, 22, 23, 24, 25, 26, 27],

            # connecting the head

        ],
        (300, 300), 140, 2, 0, 0, 0, 0, 0.015, 0,
        fill_as_connections=True
    )
    return axe


def get_pickaxe(base_color):
    w, l, h = 0.05, 0.8, 0.05
    hw, hh = 0.35, 0.4
    body_color = (235, 235, 235, 0)
    pickaxe = Crystal(
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
        ], [
            # point colors
        ], [
            # connections
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

            # connecting the head

        ],
        (300, 300), 140, 2, 0, 0, 0, 0, 0.015, 0,
        fill_as_connections=True
    )
    return pickaxe


def get_kunai(base_color):
    w, l, h = 0.1, 0.55, 0.05
    mw, ml, mh = .3 * w, .32 * l, .3 * h
    gl = 0.75 * l
    body_color = (235, 235, 235, 255)
    kunai = Crystal(
        win.renderer, [
            # base
            [-w, 0, 0],
            [0, 0, h],
            [w, 0, 0],
            [0, 0, -h],
            # tip
            [0, -l, 0],
            # middle
            [-mw, ml, 0],
            [0, ml, mh],
            [mw, ml, 0],
            [0, ml, -mh],
            # bottom
            [-mw, ml + gl, 0],
            [0, ml + gl, mh],
            [mw, ml + gl, 0],
            [0, ml + gl, -mh],
        ], [
            # point colors
        ], [
            # connections
        ], [
            # body and tip
            [grays[50], 0, 4, 1],
            [grays[40], 1, 4, 2],
            [grays[70], 2, 4, 3],
            [grays[60], 3, 4, 0],
            # middle
            [grays[70], 5, 0, 1, 6],
            [grays[60], 6, 1, 2, 7],
            [grays[50], 7, 2, 3, 8],
            [grays[40], 8, 3, 0, 5],
            # grip
            [browns[50], 9, 5, 6, 10],
            [browns[40], 10, 6, 7, 11],
            [browns[70], 11, 7, 8, 12],
            [browns[60], 12, 8, 5, 9],
        ],
        (300, 300), 140, 2, 0, 0, 0, 0, 0.015, 0,
        fill_as_connections=False
    )
    return kunai


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
