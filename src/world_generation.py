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

    def get_layers(self, biome):
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


# list-based
def dworld_modifications(data, metadata, screen, layer, biome, blockindex, blockname, abs_screen, block_names, Window):
    #g.wg.seed(111)
    horindex, verindex = blockindex % HL, blockindex // HL
    block_pos = (horindex * 30, verindex * 30)
    block_x, block_y = block_pos
    entities = []
    sec, prim = bio.blocks[biome]
    if bpure(blockname) == "soil":
        if 2 <= horindex <= HL - 3:
            if biome in bio.tree_chances:
                tree_chance = chance(1 / bio.tree_chances[biome])
            else:
                tree_chance = 0
            if tree_chance:
                tree_index = blockindex - HL
                tree_height = bio.tree_heights.get(biome, nordis(6, 2, g.wg))
                wood_type = fromdict(bio.wood_types, biome, exc="wood_bg", sf="_bg")
                leaf_type = get_leaf_type(blockname)
                if biome != "savanna":
                    for i in range(tree_height):
                        data[screen][tree_index] = wood_type
                        tree_index -= HL
                    if biome == "forest" or biome == "swamp":
                        data[screen][tree_index - 2]      = leaf_type
                        data[screen][tree_index - 1]      = leaf_type
                        data[screen][tree_index]          = leaf_type
                        data[screen][tree_index + 1]      = leaf_type
                        data[screen][tree_index + 2]      = leaf_type
                        data[screen][tree_index - HL + 1] = leaf_type
                        data[screen][tree_index - HL]     = leaf_type
                        data[screen][tree_index - HL - 1] = leaf_type
                        data[screen][tree_index - HL * 2] = leaf_type
                    elif biome == "jungle":
                        data[screen][tree_index + HL - 2]     = leaf_type
                        data[screen][tree_index + HL + 2]     = leaf_type
                        data[screen][tree_index - 2]          = leaf_type
                        data[screen][tree_index - 1]          = leaf_type
                        data[screen][tree_index]              = leaf_type
                        data[screen][tree_index + 1]          = leaf_type
                        data[screen][tree_index + 2]          = leaf_type
                        data[screen][tree_index - HL - 1]     = leaf_type
                        data[screen][tree_index - HL]         = leaf_type
                        data[screen][tree_index - HL + 1]     = leaf_type
                        data[screen][tree_index - HL + 2]     = leaf_type
                        data[screen][tree_index - HL * 2 - 2] = leaf_type
                        data[screen][tree_index - HL * 2 - 1] = leaf_type
                        data[screen][tree_index - HL * 2]     = leaf_type
                        data[screen][tree_index - HL * 2 + 1] = leaf_type
                        data[screen][tree_index - HL * 3 - 1] = leaf_type
                        data[screen][tree_index - HL * 3]     = leaf_type
                        data[screen][tree_index - HL * 4 - 1] = leaf_type
                else:
                    for i in range(tree_height):
                        data[screen][tree_index]     = wood_type
                        data[screen][tree_index + 1] = wood_type
                        tree_index -= HL
                    data[screen][tree_index + HL - 1] = leaf_type
                    data[screen][tree_index]          = leaf_type
                    data[screen][tree_index + 1]      = leaf_type
                    data[screen][tree_index + HL + 2] = leaf_type

                # vines
                if biome in ("swamp", "jungle"):
                    vine_height = nordis(tree_height // 2, 2, g.wg)
                    vine_index = g.wg.choice((tree_index + HL - 2,
                                                tree_index + HL - 1,
                                                tree_index + HL + 1,
                                                tree_index + HL + 2))
                    for i in range(vine_height):
                        data[screen][vine_index] = "vine"
                        vine_index += HL

            # bamboo
            if biome == "jungle":
                if chance(1 / 7):
                    bamboo_height = nordis(8, 2, g.wg)
                    bamboo_index = blockindex - HL
                    for i in range(bamboo_height):
                        data[screen][bamboo_index] = "bamboo_bg"
                        bamboo_index -= HL

        if biome == "jungle":
            if 0 <= horindex <= HL - 3:
                # portal
                if chance(1 / 20):
                    e = Entity("portal", block_pos, abs_screen, 1, traits=["portal"])
                    entities.append(e)

        if biome == "forest":
            # watermelons
            if chance(1 / 40):
                data[screen][blockindex - HL] = "watermelon_bg"

        if biome == "industry":
            # barrels
            if chance(1 / 40):
                barrel_indexes = [blockindex - HL, blockindex - HL * 2]
                barrel_type = "red_barrel_bg" if chance(1 / 5) else "blue_barrel_bg"
                for bi in barrel_indexes:
                    data[screen][bi] = barrel_type
            # npc
            if chance(1 / 50):
                e = Entity(get_avatar(), (horindex * 30, verindex * 30), abs_screen, 1, name="Joe", script=None, traits=["npc"])
                entities.append(e)

    if biome == "desert":
        if data[screen][blockindex] == prim:
            if data[screen][blockindex - HL] == "air":
                # camels
                if chance(1 / 50):
                    name = g.wg.choice(("camel", "fluff_camel"))
                    camel = Entity(name, block_pos, abs_screen, 1, "bottomleft", traits=["camel", "mob", "passive", "moving"], smart_vector=True, index=blockindex)
                    entities.append(camel)

                # cacti
                if chance(1 / 20):
                    cactus_height = nordis(4, 2, g.wg)
                    cactus_index = blockindex - HL
                    for i in range(cactus_height):
                        data[screen][cactus_index] = "cactus_bg"
                        cactus_index -= HL

                # temples
                if chance(1 / 10):
                    upp_blocks = [data[screen][blockindex - HL], data[screen][blockindex - HL - 1],
                            data[screen][blockindex - HL - 2], data[screen][blockindex - HL + 1],
                            data[screen][blockindex - HL + 2]]
                    nei_blocks = [data[screen][blockindex - 2], data[screen][blockindex - 1],
                            data[screen][blockindex + 1], data[screen][blockindex + 2]]
                    if nei_blocks.count("sand") == len(nei_blocks):
                        data[screen][blockindex - HL]  = "chest_bg"
                        data[screen][blockindex - 28]  = "sand_bg"
                        data[screen][blockindex - 29]  = "sand"
                        data[screen][blockindex - 26]  = "sand_bg"
                        data[screen][blockindex - 25]  = "sand"
                        data[screen][blockindex - 54]  = "sand_bg"
                        data[screen][blockindex - 55]  = "sand"
                        data[screen][blockindex - 53]  = "sand"
                        data[screen][blockindex - 81]  = "sand"
                        metadata[screen][layer * L + blockindex - HL]["chest"] = get_chest_insides(block_names)

    elif biome == "beach":
        if data[screen][blockindex] == prim and data[screen][blockindex - HL] == "air":
            if not is_in("wood", (data[screen][blockindex - HL - 1], data[screen][blockindex - HL + 1])):
                if 4 <= horindex <= HL - 2:
                    if biome in bio.tree_chances:
                        tree_chance = chance(1 / bio.tree_chances[biome])
                    else:
                        tree_chance = 0
                    if tree_chance:
                        tree_height = bio.tree_heights["beach"]
                        pairs = []
                        pairs.append(g.wg.randint(1, tree_height - 1))
                        pairs.append(tree_height - pairs[-1])

                        tree_index = blockindex - HL
                        for i in range(pairs[0]):
                            data[screen][tree_index] = "wood_bg"
                            tree_index -= HL
                        tree_index -= 1
                        for i in range(pairs[1]):
                            data[screen][tree_index] = "wood_bg"
                            tree_index -= HL

                        leaves = [tree_index + HL - 2, tree_index - 1, tree_index + 2,
                                  tree_index, tree_index - HL - 3, tree_index - HL - 1,
                                  tree_index - HL, tree_index - HL + 1, tree_index - HL * 2 - 2,
                                  tree_index - HL * 2, tree_index - HL * 3 + 1]
                        for leaf in leaves:
                            data[screen][leaf] = "leaf_f_bg"
                        for leaf in leaves:
                            if chance(1 / 12):
                                data[screen][leaf] = "coconut"

            # rocks
            if biome == "beach":
                if 1 <= horindex <= HL - 1:
                    if chance(1 / 25):
                        data[screen][blockindex - HL] = "rock_bg"

    elif biome == "volcano":
        # volcanoes
        if chance(1 / 25):
            if data[screen][blockindex] == "air" and data[screen][blockindex + HL] == prim:
                pass

    elif biome == "arctic":
        if data[screen][blockindex] == prim:
            if data[screen][blockindex - HL] == "air":
                if chance(1 / 50):
                    penguin = Entity("penguin", block_pos, abs_screen, 1, "bottomleft", traits=["penguin", "mob", "passive", "moving"], smart_vector=True, index=blockindex)
                    entities.append(penguin)

    if blockname == bio.blocks[biome][0]:
        if data[screen][blockindex - HL] == "air":
            if 2 <= horindex <= HL - 1:
                try:
                    stmt = data[screen][blockindex - 1] == "air" or data[screen][blockindex + 1] == "air"
                except IndexError:
                    stmt = False
                finally:
                    if stmt:
                        if biome in bio.fill_chances:
                            fill_chance = chance(1 / bio.fill_chances[biome][1])
                            fill_type = bio.fill_chances[biome][0]
                        else:
                            fill_chance = 0
                        if fill_chance:
                            # check whether water can flow horizontally
                            check_xindex = blockindex
                            faulty = True
                            for i in range(HL - horindex - 1):
                                check_xindex += 1
                                if data[screen][check_xindex] != "air":
                                    faulty = False
                                    break
                            if not faulty:
                                water_xindex = blockindex + 1
                                while data[screen][water_xindex] == "air":
                                    data[screen][water_xindex] = fill_type
                                    water_yindex = water_xindex + HL
                                    while data[screen][water_yindex] == "air":
                                        data[screen][water_yindex] = fill_type
                                        water_yindex += HL
                                    water_xindex += 1
    for md in metadata[screen]:
        if "chest" in md:
            while len(md["chest"]) < 25:
                md["chest"].append((None, None))
    return entities


# image-based
def dworld_modifications(data, width, height):
    def set(name, xpos, ypos):
        with suppress(IndexError):
            data[xpos][ypos] = Block(name)

    def get(xpos, ypos):
        try:
            return data[xpos][ypos].name
        except IndexError:
            return None

    for x in range(width):
        for y in range(height):
            block = data[x][y]
            name = block.name
            if name == "sand":
                if get(x, y - 1) == "air":
                    if chance(1 / 10):
                        for (xo, yo), setto in structures["pyramid"].items():
                            set(setto, x + xo, y + yo)


# chunk-based
def dworld_modifications(chunk: (int, int), metadata: DictWithoutException, biome: str, chunk_pos: (int, int), r) -> list:
    def set(pos, name):
        chunk[pos] = Block(name)
        metadata[pos] = {"light": 1}

    # init
    prim, sec = bio.blocks[biome]
    entities = []
    rel_x = rel_y = xo = yo = 0
    rel_xy = (rel_x, rel_y)
    abs_x, abs_y = chunk_pos[0] * BS, chunk_pos[1] * BS
    min_x = min_y = float("inf")
    # chunk chances
    keno_avail = True
    # dynamic chances
    for pos, block in chunk.copy().items():
        # init
        x, y = pos
        name = block.name
        x, y = pos
        if x < min_x:
            min_x = x
        if y < min_y:
            min_y = y
        rel_x, rel_y = x % CW, y % CH
        rel_xy = (rel_x, rel_y)
        rel_x_blocks = rel_x * BS
        rel_y_blocks = rel_y * BS
        rel_pos = (rel_x_blocks, rel_y_blocks)
        abs_pos = abs_x_blocks, abs_y_blocks = chunk_pos[0] * BS + rel_x_blocks, chunk_pos[1] * BS + rel_y_blocks

        if biome == "forest":
            if name == prim:
                # serial
                if chance(1 / 3):  # grass
                    # chunk[(pos[0], pos[1] - 1)] = f"grass{rand(1, 2)}_bg"
                    grass_x, grass_y = pos[0], pos[1] - 1
                    set((grass_x, grass_y), "grass_f")
                elif chance(1 / 25):  # watermelon
                    set((pos[0], pos[1] - 1), "watermelon_bg")
                # parallel
                if chance(1 / 10):  # tree
                    if 0 < rel_x < CW:
                        tree_height = nordis(10, 4)
                        wood_x = pos[0]
                        for tree_yo in range(tree_height):
                            wood_y = pos[1] - (tree_yo + 1)
                            wood_pos = (wood_x, wood_y)
                            left_leaf_pos = (wood_x - 1, wood_y)
                            right_leaf_pos = (wood_x + 1, wood_y)
                            leaf_chance = 1 / (tree_height - tree_yo)
                            suffix = ""
                            if chance(leaf_chance):
                                set(left_leaf_pos, "leaf_f_bg")
                                suffix += "L"
                            if chance(leaf_chance):
                                set(right_leaf_pos, "leaf_f_bg")
                                suffix += "R"
                            suffix = suffix if suffix else "N"
                            set(wood_pos, f"wood_f_vr{suffix}_bg")
                            if tree_yo == tree_height - 1:
                                set((wood_x, wood_y - 1), "leaf_f_bg")
                                set(wood_pos, "wood_f_vrLRT_bg")

                if chance(1 / Chicken.chance):
                    e = Entity("chicken", ["chicken", "mob", "moving"], metadata["index"], rel_xy)
                    # metadata["entities"].append(e)
                    entities.append(e)

        elif biome == "savanna":
            if name == "prim":
                pass

        elif biome == "swamp":
            if name == prim:
                if chance(1 / 20):  # daivinus
                    set((pos[0], pos[1] - 1), "daivinus_bg")

            elif name == "water":
                if chance(1 / 2):
                    set((pos[0], pos[1] - 1), "lotus")

        elif biome == "arctic":
            if name == prim and chunk[(x, y - 1)] == "air":
                if chance(1 / 20):  # penguin
                    e = Entity("penguin", ["penguin", "moving", "mob", "passive"], abs_pos, chunk_pos, rel_pos)
                    metadata["entities"].append(e)

    max_x, max_y = min_x + CW, min_y + CH
    for pos, name in chunk.copy().items():
        x, y = pos
        if min_x <= x < max_x and min_y <= y < max_y:
            continue
        # del chunk[pos]
        # del metadata[pos]

    return entities


# chunk-based v2
# real (finfal version, at least for now)
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
            if name == "air":
                # forest water
                if rel_y >= 8:
                    # set("water", x, y)
                    # swamp lotus
                    if biome == "swamp":
                        if get(x, y - 1) == "air":
                            if _chance(1 / 20):
                                set("lotus", x, y - 1)

        if name == prim:
            # forest
            if biome == "forest":
                # chicken
                if _chance(1 / 16):
                    entity(["chicken", "mob", "moving"])

                # top is free
                if get(x, y - 1) == "air":
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

                    elif _chance(1 / 10):
                        tree_height = _rand(3, 6)
                        for yo in range(tree_height):
                            set("wood_f_vrN_bg", x, y - yo - 1)
                        struct("treetop", x, y - yo - 1)

            # desert
            if biome == "desert":
                if get(x, y - 1) == "air":
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
                if get(x, y - 1) == "air":
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
