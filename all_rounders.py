from settings import *


def get_bcc():
    with open(path("Images", "Vertices", "test.json"), "r") as f:
        crystal_data = json.load(f)
    bcc = Crystal(
        win.renderer,
        crystal_data["vertices"],
        crystal_data["point_colors"],
        crystal_data["connections"],
        [],
        (300, 300), 25, 5, 0, 0, 0, 0.001, 0.001, 0.001
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
    sword = Crystal(
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
            [base_color, 0, 1, 2, 3],
            [base_color, 4, 5, 1, 0],
            [base_color, 4, 5, 6, 7],
            [base_color, 7, 6, 2, 3],
            [base_color, 4, 0, 3, 7],
            [base_color, 1, 5, 6, 2],

            [(200, 200, 200, 255), 0 + 8, 1 + 8, 2 + 8],
            [(200, 200, 200, 255), 3 + 8, 4 + 8, 5 + 8],
            [(200, 200, 200, 255), 3 + 8, 0 + 8, 2 + 8, 5 + 8],
            [(200, 200, 200, 255), 0 + 8, 3 + 8, 4 + 8, 1 + 8],
            [(200, 200, 200, 255), 5 + 8, 4 + 8, 1 + 8, 2 + 8],

            [DARK_BROWN, 0 + 14, 1 + 14, 2 + 14, 3 + 14],
            [DARK_BROWN, 4 + 14, 5 + 14, 1 + 14, 0 + 14],
            [DARK_BROWN, 4 + 14, 5 + 14, 6 + 14, 7 + 14],
            [DARK_BROWN, 7 + 14, 6 + 14, 2 + 14, 3 + 14],
            [DARK_BROWN, 4 + 14, 0 + 14, 3 + 14, 7 + 14],
            [DARK_BROWN, 1 + 14, 5 + 14, 6 + 14, 2 + 14],

            [BROWN, 0 + 22, 1 + 22, 2 + 22, 3 + 22],
            [BROWN, 4 + 22, 5 + 22, 1 + 22, 0 + 22],
            [BROWN, 4 + 22, 5 + 22, 6 + 22, 7 + 22],
            [BROWN, 7 + 22, 6 + 22, 2 + 22, 3 + 22],
            [BROWN, 4 + 22, 0 + 22, 3 + 22, 7 + 22],
            [BROWN, 1 + 22, 5 + 22, 6 + 22, 2 + 22],
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
