from ..settings import *


# constants
grays = [(x, x, x, 255) for x in range(1, 256)]
browns = [(int(x * 0.6), int(x * 0.4), int(x * 0.2), 255) for x in range(1, 256)]


def get_brown(mu, sigma):
    return browns[int(random.gauss(mu, sigma))]


def get_gray(mu, sigma):
    return grays[int(random.gauss(mu, sigma))]


# functions
def get_crystal(type_, color=None):
    with open(path("src", "shapes", f"{type_}.json"), "r") as f:
        crystal_data = json.load(f)
    bcc = Crystal(
        win.renderer,
        crystal_data["vertices"],
        crystal_data["point_colors"] if color is None else [color] * len(crystal_data["vertices"]),
        crystal_data["connections"],
        [],
        (300, 300), 18, 3, 0, 0, 0, 0.015, 0.015, 0.015
    )
    return bcc


def get_sword(base_color):
    mult = 140
    w, l, h = 0.12, 0.8, 0.03
    tl = 0.3
    gw, gl, gh = 0.24, 0.1, 0.1
    gxo = l
    uw, ul, uh = 0.05, 0.4, 0.05
    uxo = gxo
    base_color = (235, 235, 235, 255)
    outline_color = (20, 20, 20, 255)
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
            [[base_color, outline_color], 0, 1, 2, 3],
            [[base_color, outline_color], 4, 5, 1, 0],
            [[base_color, outline_color], 4, 5, 6, 7],
            [[base_color, outline_color], 7, 6, 2, 3],
            [[base_color, outline_color], 4, 0, 3, 7],
            [[base_color, outline_color], 1, 5, 6, 2],

            # tip
            [[base_color, outline_color], 0 + 8, 1 + 8, 2 + 8],
            [[base_color, outline_color], 3 + 8, 4 + 8, 5 + 8],
            [[base_color, outline_color], 3 + 8, 0 + 8, 2 + 8, 5 + 8],
            [[base_color, outline_color], 0 + 8, 3 + 8, 4 + 8, 1 + 8],
            [[base_color, outline_color], 5 + 8, 4 + 8, 1 + 8, 2 + 8],

            # guard
            [[browns[90], outline_color], 0 + 14, 1 + 14, 2 + 14, 3 + 14],
            [[browns[80], outline_color], 4 + 14, 5 + 14, 1 + 14, 0 + 14],
            [[browns[70], outline_color], 4 + 14, 5 + 14, 6 + 14, 7 + 14],
            [[browns[110], outline_color], 7 + 14, 6 + 14, 2 + 14, 3 + 14],
            [[browns[120], outline_color], 4 + 14, 0 + 14, 3 + 14, 7 + 14],
            [[browns[100], outline_color], 1 + 14, 5 + 14, 6 + 14, 2 + 14],

            # grip
            [[browns[150], outline_color], 0 + 22, 1 + 22, 2 + 22, 3 + 22],
            [[browns[140], outline_color], 4 + 22, 5 + 22, 1 + 22, 0 + 22],
            [[browns[160], outline_color], 4 + 22, 5 + 22, 6 + 22, 7 + 22],
            [[browns[170], outline_color], 7 + 22, 6 + 22, 2 + 22, 3 + 22],
            [[browns[130], outline_color], 4 + 22, 0 + 22, 3 + 22, 7 + 22],
            [[browns[120], outline_color], 1 + 22, 5 + 22, 6 + 22, 2 + 22],
        ],
        (300, 300), mult, 2, 0, 0, 0, 0, 0.015,0,
        fill_as_connections=False,
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
    mult = 140
    w, l, h = 0.05, 0.8, 0.05
    hw, hh = 0.35, 0.4
    base_color = (235, 235, 235, 255)
    blade_color = (50, 50, 50, 255)
    outline_color = (255, 255, 255, 255)
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
            [-w, l, -h],  # 7

            # head-back
            [w, -l, h],  # 8
            [w + hw, -l + hh * 0.25, h],  # 9
            [w, -l + hh * 0.5, h],  # 10
            # head-front
            # down
            [-w, -l + hh * 0.4, h],  # 11
            [-w - hw * 0.4, -l + hh * 0.4, h],  # 12
            [-w - hw * 0.8, -l + hh, 0],  # 13
            [-w - hw, -l + hh * 0.4, 0],  # 14
            # up (both z-layers | middle)
            [-w - hw * 0.8, -l - hh * 0.2, 0],  # 15
            [-w - hw * 0.6, -l, h],  # 16
            [-w, -l, h],  # 17
            # (2x, z-variance)
            # head-back
            [w, -l, -h],  # 18
            [w + hw, -l + hh * 0.25, -h],  # 19
            [w, -l + hh * 0.5, -h],  # 20
            # head-front
            # down
            [-w, -l + hh * 0.4, -h],  # 21
            [-w - hw * 0.4, -l + hh * 0.4, -h],  # 22
            # up
            [-w - hw * 0.6, -l, -h],  # 23
            [-w, -l, -h],  # 24
        ], [
            # point colors
        ], [
            # connections
        ], [
            # fills
            # base
            [[get_brown(160, 20), outline_color], 0, 1, 2, 3],
            [[get_brown(160, 20), outline_color], 4, 5, 1, 0],
            [[get_brown(160, 20), outline_color], 4, 5, 6, 7],
            [[get_brown(160, 20), outline_color], 7, 6, 2, 3],
            [[get_brown(160, 20), outline_color], 4, 0, 3, 7],
            [[get_brown(160, 20), outline_color], 1, 5, 6, 2],

            # back
            [[blade_color, outline_color], 8, 9, 10],
            [[blade_color, outline_color], 18, 19, 20],
            [[blade_color, outline_color], 18, 19, 9, 8],
            [[blade_color, outline_color], 10, 9, 19, 20],

            # head
            # stems
            [[blade_color, outline_color], 23, 24, 17, 16],
            [[blade_color, outline_color], 15, 16, 23],
            [[blade_color, outline_color], 22, 21, 11, 12],
            [[blade_color, outline_color], 13, 12, 22],
            # faces
            # section vermillion
            [[blade_color, outline_color], 16, 17, 11, 12],
            [[blade_color, outline_color], 23, 24, 21, 22],
            # section cyan
            [[blade_color, outline_color], 14, 15, 16, 12],
            [[blade_color, outline_color], 14, 15, 23, 22],
            # section olive
            [[blade_color, outline_color], 14, 13, 12],
            [[blade_color, outline_color], 14, 13, 22],

        ],
        (300, 300), mult, 2, 0, 0, 0, 0, 0.015,0,
        fill_as_connections=False,
    )
    return axe


def get_shovel(base_color):
    mult = 140
    w, l, h = 0.05, 0.8, 0.03
    bw, bl, bh = 0.15, 0.35, 0.03
    tl = 0.1
    base_color = (235, 235, 235, 255)
    outline_color = (255, 255, 255, 255)
    shovel = Crystal(
        win.renderer, [
            # base
            [-w, -l, h],
            [w, -l, h],
            [w, l, h],
            [-w, l, h],
            [-w, -l, -h],
            [w, -l, -h],
            [w, l, -h],
            [-w, l, -h],  # 7

            # blade
            [-bw, l, -bh],
            [bw, l, -bh],
            [bw, l + bl, -bh],
            [-bw, l + bl, -bh],  # 11

            # tip
            [0, l + bl + tl, -bh],
        ], [
            # point colors
        ], [
            # connections
        ], [
            # fills
            # base
            [[browns[100], outline_color], 0, 1, 2, 3],
            [[browns[90], outline_color], 4, 5, 1, 0],
            [[browns[70], outline_color], 4, 5, 6, 7],
            [[browns[80], outline_color], 7, 6, 2, 3],
            [[browns[110], outline_color], 4, 0, 3, 7],
            [[browns[120], outline_color], 1, 5, 6, 2],

            # blade
            [[grays[180], outline_color], 8, 9, 10, 11],

            # tip
            [[grays[170], outline_color], 10, 11, 12],
        ],
        (300, 300), mult, 2, 0, 0, 0, 0, 0.015,0,
        fill_as_connections=False,
    )
    return shovel


def get_pickaxe(base_color):
    mult = 140
    w, l, h = 0.05, 0.8, 0.05
    hw, hh = 0.35, 0.4
    base_color = (235, 235, 235, 255)
    outline_color = (255, 255, 255, 255)
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
            [[base_color, outline_color], 0, 1, 2, 3],
            [[base_color, outline_color], 4, 5, 1, 0],
            [[base_color, outline_color], 4, 5, 6, 7],
            [[base_color, outline_color], 7, 6, 2, 3],
            [[base_color, outline_color], 4, 0, 3, 7],
            [[base_color, outline_color], 1, 5, 6, 2],

            # head
            [[base_color, outline_color], 8, 9, 10],

            # connecting the head

        ],
        (300, 300), mult, 2, 0, 0, 0, 0, 0.015,0,
        fill_as_connections=False,
    )
    return pickaxe


def get_kunai(base_color):
    mult = 230
    w, l, h = 0.1, 0.55, 0.05
    mw, ml, mh = .3 * w, .32 * l, .3 * h
    gl = 0.75 * l
    base_color = (235, 235, 235, 255)
    outline_color = (255, 255, 255, 255)
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
            [[grays[50], outline_color], 0, 4, 1],
            [[grays[40], outline_color], 1, 4, 2],
            [[grays[70], outline_color], 2, 4, 3],
            [[grays[60], outline_color], 3, 4, 0],
            # middle
            [[grays[70], outline_color], 5, 0, 1, 6],
            [[grays[60], outline_color], 6, 1, 2, 7],
            [[grays[50], outline_color], 7, 2, 3, 8],
            [[grays[40], outline_color], 8, 3, 0, 5],
            # grip
            [[browns[50], outline_color], 9, 5, 6, 10],
            [[browns[40], outline_color], 10, 6, 7, 11],
            [[browns[70], outline_color], 11, 7, 8, 12],
            [[browns[60], outline_color], 12, 8, 5, 9],
        ],
        (300, 300), mult, 2, 0, 0, 0, 0, 0.015, 0,
        fill_as_connections=False,
    )
    return kunai


def get_bow(base_color):
    mult = 230
    # base
    bw, bl, bh = 0.02, 0.4, 0.02
    bo = -0.2
    # string
    sw, sl, sh = 0.007, 0.7, 0.007
    so = 0.2
    base_color = (235, 235, 235, 255)
    outline_color = (255, 255, 255, 255)
    bow = Crystal(
        win.renderer, [
            # base
            [bo + -bw, -bl, bh],
            [bo + bw, -bl, bh],
            [bo + bw, bl, bh],
            [bo + -bw, bl, bh],
            [bo + -bw, -bl, -bh],
            [bo + bw, -bl, -bh],
            [bo + bw, bl, -bh],
            [bo + -bw, bl, -bh],

            # string
            [so + -sw, -sl, sh],
            [so + sw, -sl, sh],
            [so + sw, sl, sh],
            [so + -sw, sl, sh],
            [so + -sw, -sl, -sh],
            [so + sw, -sl, -sh],
            [so + sw, sl, -sh],
            [so + -sw, sl, -sh],
        ], [
            # point colors
        ], [
            # connections
        ], [
            # body
            [[get_brown(120, 20), outline_color], 0, 1, 2, 3],
            [[get_brown(120, 20), outline_color], 4, 5, 1, 0],
            [[get_brown(120, 20), outline_color], 4, 5, 6, 7],
            [[get_brown(120, 20), outline_color], 7, 6, 2, 3],
            [[get_brown(120, 20), outline_color], 4, 0, 3, 7],
            [[get_brown(120, 20), outline_color], 1, 5, 6, 2],
            # string
            [[get_brown(160, 20), outline_color], 0 + 8, 1 + 8, 2 + 8, 3 + 8],
            [[get_brown(160, 20), outline_color], 4 + 8, 5 + 8, 1 + 8, 0 + 8],
            [[get_brown(160, 20), outline_color], 4 + 8, 5 + 8, 6 + 8, 7 + 8],
            [[get_brown(160, 20), outline_color], 7 + 8, 6 + 8, 2 + 8, 3 + 8],
            [[get_brown(160, 20), outline_color], 4 + 8, 0 + 8, 3 + 8, 7 + 8],
            [[get_brown(160, 20), outline_color], 1 + 8, 5 + 8, 6 + 8, 2 + 8],
            # connect-top
            [[get_brown(160, 20), outline_color], 1 + 8, 5 + 8, 6 + 8, 2 + 8],
        ],
        (300, 300), mult, 2, 0, 0, 0, 0, 0.015, 0,
        fill_as_connections=False,
    )
    return bow


def get_hammer(base_color):
    mult = 140
    w, l, h = 0.05, 0.8, 0.05
    hw, hl, hh = 0.3, 0.15, 0.15
    base_color = (235, 235, 235, 255)
    blade_color = (50, 50, 50, 255)
    outline_color = (255, 255, 255, 255)
    hammer = Crystal(
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

            # head
            [-hw, -hl - l, hh],
            [hw, -hl - l, hh],
            [hw, hl - l, hh],
            [-hw, hl - l, hh],
            [-hw, -hl - l, -hh],
            [hw, -hl - l, -hh],
            [hw, hl - l, -hh],
            [-hw, hl - l, -hh],
        ], [
            # point colors
        ], [
            # connections
        ], [
            # fills
            # base
            [[get_brown(160, 20), outline_color], 0, 1, 2, 3],
            [[get_brown(160, 20), outline_color], 4, 5, 1, 0],
            [[get_brown(160, 20), outline_color], 4, 5, 6, 7],
            [[get_brown(160, 20), outline_color], 7, 6, 2, 3],
            [[get_brown(160, 20), outline_color], 4, 0, 3, 7],
            [[get_brown(160, 20), outline_color], 1, 5, 6, 2],

            [[get_gray(180, 20), outline_color], 0 + 8, 1 + 8, 2 + 8, 3 + 8],
            [[get_gray(180, 20), outline_color], 4 + 8, 5 + 8, 1 + 8, 0 + 8],
            [[get_gray(180, 20), outline_color], 4 + 8, 5 + 8, 6 + 8, 7 + 8],
            [[get_gray(180, 20), outline_color], 7 + 8, 6 + 8, 2 + 8, 3 + 8],
            [[get_gray(180, 20), outline_color], 4 + 8, 0 + 8, 3 + 8, 7 + 8],
            [[get_gray(180, 20), outline_color], 1 + 8, 5 + 8, 6 + 8, 2 + 8],
        ],
        (300, 300), mult, 2, 0, 0, 0, 0, 0.015,0,
        fill_as_connections=False,
    )
    return hammer


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