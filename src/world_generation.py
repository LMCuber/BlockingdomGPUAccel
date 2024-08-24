import io
import random
import requests
import PIL.Image
#
from pyengine.basics import *
from pyengine.pgbasics import *
from pyengine.pilbasics import pil_to_pg
#
from .prim_data import *
from .entities import *
from . import entities as ent


# avatar_url = r"https://avatars.dicebear.com/api/pixel-art-neutral/:seed.svg?mood[]=:mood"
avatar_url = r"https://api.dicebear.com/7.x/pixel-art/svg?seed="
quote_url = "https://inspirobot.me/api?generate=true"


def get_chest_insides(block_names):
    chest_inventory = []
    chest_amounts = []
    for _ in range(nordis(5, 2, g.wg)):
        chest_inventory.append(g.wg.choice(block_names))
        chest_amounts.append(nordis(2, 1, g.wg) + 1)
    return [list(x) for x in zip(chest_inventory, chest_amounts)]


def get_quote():
    img_url = requests.get(quote_url).text
    img_io = requests.get(img_url).content
    pil_img = PIL.Image.open(io.BytesIO(img_io))
    pil_img = pil_img.resize([s // 2 for s in pil_img.size])
    quote = image_to_string(pil_img)
    quote = "".join([char for char in quote])
    return quote


def destroy_group(grp):
    for spr in grp:
        spr.kill()


def is_transparent(image):
    if image.get_at((0, 0))[3] == 0:
        return True
    else:
        return False


def rand_block(*args):
    blocklist = []
    chancelist = []
    for arg in args:
        if type(arg) == str:
            blocklist.append(arg)
        elif type(arg) == int or type(arg) == float:
            chancelist.append(arg)
    arr = []
    item = -1
    for i in range(len(chancelist)):
        item += 1
        for i in range(chancelist[item]):
            arr.append(blocklist[item])
    chance = arr[g.wg.randint(0, 99)]
    return chance


class Biome:
    def __init__(self):
        self.heights = {"forest": 4, "desert": 4, "beach": 2, "mountain": 9, "industry": 2, "wasteland": 2}
        self.blocks = {"forest":   ("soil_f", "dirt_f"),         "desert":    ("sand", "sand"),
                       "beach":    ("sand", "sand"),             "mountain":  ("snow-stone", "stone"),
                       "swamp":    ("soil_sw", "dirt_f"),         "prairie":   ("hay", "dirt_f"),
                       "jungle":   ("soil_f", "dirt_f"),          "savanna":   ("soil_sv", "dirt_f"),
                       "industry": ("soil_p", "dirt_f"),          "wasteland": ("dirt_f", "dirt_f"),
                       "volcano":  ("blackstone", "blackstone"), "arctic":    ("snow", "snow")}
        self.tree_heights = {"swamp": 4, "jungle": 8, "savanna": 10, "beach": 6}
        self.tree_chances = {"forest": 8, "beach": 16, "swamp": 7, "jungle": 6, "savanna": 20}
        self.wood_types = {"savanna": "wood_sv"}
        self.fill_chances = {"forest": ("water", 3), "beach": ("water", 3), "swamp": ("water", 5), "jungle": ("water", 4),
                             "savanna": ("water", 100), "volcsano": ("lava", 3)}
        self.flatnesses = {"forest": 7, "industry": 10, "beach": 10}
        self.biomes = list(self.blocks.keys())

    def get_transition(self, biome):
        o1 = nordis(2, 2)
        o2 = nordis(2, 2)
        return {
            "beach": {
                (0, CH / 4 + o1): "sand",
                (CH / 4 + o1, CH / 2 + o2): "sandstone",
                (CH / 2 + o2, CH): "stone",
            },
            "forest": {
                (0, CH / 4 + o1): "dirt_f",
                (CH / 4 + o1, CH / 2 + o2): "stone",
                (CH / 2 + o2, CH): "stone",
            }
        }[biome]


bio = Biome()


def fromdict(dict_, el, exc, sf=None):
    try:
        try:
            return dict_[el] + sf
        except TypeError:
            return dict_[el]
    except KeyError:
        return exc


def get_leaf_type(blockname):
    try:
        type_ = blockname.split("_")[0]
        a.blocks["leaf_" + type_]
        return "leaf_" + type_
    except Exception:
        return "leaf_f_bg"


# chunk-based v2
# real (finfallataloaeer332l version, I assert) (are you having a stroke lil retigga wtf is this)
def world_modifications(chunk_data, metadata, biome, chunk_pos, r):
    # funcs
    def _rand(x, y):
        return r.randint(x, y)

    def _chance(x):
        return r.random() < x

    def get(block_x, block_y):
        try:
            return chunk_data[(block_x, block_y)].name
        except KeyError:
            return None
            rel_x, rel_y = block_x % CW, block_y % CH

    def set(name, block_x, block_y):
        rel_x, rel_y = block_x - chunk_x, block_y - chunk_y
        if 0 <= rel_x <= CW - 1 and 0 <= rel_y <= CH - 1:
            ap = (block_x, block_y)
            chunk_data[ap] = Block(name, ap)
        else:
            xo, yo = block_x - x, block_y - y
            new_chunk, new_pos = correct_tile(chunk_index, (x, y), xo, yo)
            if new_chunk in late_chunk_data:
                late_chunk_data[new_chunk][new_pos] = name
            else:
                late_chunk_data[new_chunk] = {new_pos: name}

    def struct(struct_name, block_x, block_y):
        for (xo, yo), block_name in structures[struct_name].items():
            set(block_name, block_x + xo, block_y + yo)

    def entity(traits=None, rel=None, **kwargs):
        species = traits[0]
        e = getattr(ent, species.title().replace("_", ""))(species, traits, metadata["index"], rel if rel is not None else rel_xy, **kwargs)
        entities.append(e)

    # misc. init
    entities = []
    chunk_x, chunk_y = chunk_pos
    chunk_index = metadata["index"]
    chunk_xi, chunk_yi = chunk_index
    late_chunk_data = {}
    # biome init
    prim, sec = bio.blocks[biome]
    # loop
    for pos, block in chunk_data.copy().items():
        rel_x, rel_y = pos[0] % CW, pos[1] % CH
        rel_xy = (rel_x, rel_y)
        name = block.name
        x, y = pos

        # water level
        if chunk_y == 0:
            if name in empty_blocks:
                # forest water
                if rel_y >= 8:
                    # set("water", x, y)
                    # swamp lotus
                    if biome == "swamp":
                        if get(x, y - 1) in empty_blocks:
                            if _chance(1 / 20):
                                set("lotus", x, y - 1)

        if name == prim:
            # forest
            if biome == "forest":
                # chicken
                if _chance(1 / 10):
                    entity(["chicken", "mob", "moving", "demon"])

                # top is free
                if get(x, y - 1) in empty_blocks:
                    # tree
                    if _chance(1 / 10):
                        tree_height = _rand(4, 9)
                        for tree_yo in range(tree_height):
                            wood_x, wood_y = x, y - tree_yo - 1
                            wood_suffix = ""
                            leaf_name = "leaf_f_bg"
                            leaf_chance = 1 / 2.4
                            if tree_yo > 0:
                                if _chance(leaf_chance):
                                    wood_suffix += "L"
                                    set(leaf_name, wood_x - 1, wood_y)
                                if _chance(leaf_chance):
                                    wood_suffix += "R"
                                    set(leaf_name, wood_x + 1, wood_y)
                                if tree_yo == tree_height - 1:
                                    wood_suffix += "T"
                                    set(leaf_name, wood_x, wood_y - 1)
                            wood_suffix = "N" if not wood_suffix else wood_suffix
                            wood_name = f"wood_f_vr{wood_suffix}_bg"
                            set(wood_name, wood_x, wood_y)

            # desert
            if biome == "desert":
                if get(x, y - 1) in empty_blocks:
                    # pyramid
                    if _chance(1 / 50):
                        struct("pyramid", x, y - 1)

                    # cactuses (yes I know the plural is also cacti dumbass)
                    elif _chance(1 / 7):
                        cactus_height = _rand(2, 6)
                        for cactus_yo in range(cactus_height):
                            set("cactus_bg", x, y - cactus_yo - 1)

                    elif _chance(1 / 20):
                        water_depth = _rand(1, 5)
                        struct("desert-well", x, y)

            # beachs
            elif biome == "beach":
                if get(x, y - 1) in empty_blocks:
                    # tree
                    if _chance(1 / 14):
                        num = 0
                        h = 8
                        for yo in range(nordis(h, 2)):
                            num += 1
                            suffix = ""
                            c = h * 1.4
                            if _chance(yo / c):
                                set("coconut_bg", x - 1, y - 1 - yo)
                                suffix += "L"
                            if _chance(yo / c):
                                set("coconut_bg", x + 1, y - 1 - yo)
                                suffix += "R"
                            suffix = suffix if suffix else "N"
                            set(f"wood_p_vr{suffix}_bg", x, y - 1 - yo)
                        if num:
                            entity(["leaf_p"], (rel_x, rel_y - yo - 2), anchor="center")
                    # rock
                    if _chance(1 / 15):
                        set(f"rock{'_hor' if chance(1 / 2) else ''}_bg", x, y - 1)

    return entities, late_chunk_data


pyramid = dict.fromkeys([(-2, 0), (-1, -1), (0, -2), (1, -1), (2, 0), (1, 0), (0, 0), (-1, 0)], "sand") \
        | dict.fromkeys([(-1, 0), (0, -1), (1, 0)], "sand_bg") \
        | {(0, 0): "chest"}

with open(path("assets", "structures.json"), "r") as f:
    try:
        structures = json.load(f)
    except json.decoder.JSONDecodeError:
        structures = {}
    else:
        structures = {k: {tuple(int(x) for x in pos.split(",")): block for pos, block in v.items()} for k, v in structures.items()}
