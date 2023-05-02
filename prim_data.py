import pygame
import itertools
from pyengine.basics import *
from pyengine.pgbasics import *
from settings import *

# imporant primitive objects and constants
black_filter = pygame.Surface((30, 30)); black_filter.set_alpha(200)
avatar_map = dict.fromkeys(((2, 3), (2, 4), (7, 3), (7, 4)), WHITE) | dict.fromkeys(((3, 3), (3, 4), (6, 3), (6, 4)), BLACK)

# color prims
BLUE = POWDER_BLUE
orb_colors = {"red": RED, "green": GREEN, "blue": BLUE, "yellow": YELLOW, "orange": ORANGE, "purple": PURPLE, "pink": PINK, "white": WHITE, "black": BLACK}
orb_names = {"purple": "majestic",
             "white": "imperial",
             "yellow": "regal",
             "black": "aristocratic",
             "blue": "domineering",
             "red": "tyrannical",
             "green": "noble"}
orb_names_r = {v: k for k, v in orb_names.items()}

# rotation prims
rotations2 = {0: 90, 90: 0}
rotations4 = {90: 0, 0: 270, 270: 180, 180: 90}
rotations4_stairs_tup = (0, "270_0_hor", "180_0_hor_ver", "90_0_ver")
unplaceable_blocks = []

# additional constants
vel_mult = 1


# C L A S S E S ---------------------------------------------------------------------------------------- #
class CThread(DThread):
    pass


max_light = 15
class Block:
    def __init__(self, name, pos, ore_chance=-1, light=max_light):
        # default
        self.name = name
        self.pos = pos
        self._rect = pygame.Rect((pos[0] * BS, pos[1] * BS), (BS, BS))
        self.ore_chance = ore_chance
        self.angle = 0
        self.sin = rand(0, 500)
        self.waters = []
        self.collided = False
        self.broken = 0
        self.righted = False
        self.light = max_light
        # special
        self.craftings = {}
        self.reductant = [None, None]  # [name, amount]
        self.oxidant = [None, None]  #         ^
        self.cooked = [None, None]  #          ^
        self.furnace_log = []
        self.oxidation_index = 0
        self.smithings = {}
        self.smither = None
        self.anvil_log = []
        self.crafting_log = []
        # self.gun_parts = {k: None for k in self.gun_parts}
        self.gun_log = []
        self.last_flow = ticks()
        # tool-crafter stuff
        self.sword = None


class VoidBlock:
    def __init__(self, name="", ore_chance=0):
        self.name = name
        self.ore_chance = ore_chance
        self.light = 15


void_block = VoidBlock()


class Vel:
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return str(self.val)


class Scrollable:
    @property
    def rect(self):
        return pygame.Rect(self._rect.x - g.scroll[0], self._rect.y - g.scroll[1], *self._rect.size)

    @property
    def rrect(self):
        return pygame.Rect([r * 3 for r in self.rect])


class Entity(SmartVector):  # removed Scrollable inheritance
    imgs = {
        "portal": timgload3("Images", "Spritesheets", "portal.png", frames=7),
        "camel": img_mult(timgload3("Images", "Mobs", "camel.png"), randf(0.8, 1.2)),
        "fluff_camel": timgload3("Images", "Mobs", "fluff_camel.png", frames=4),
        "penguin": timgload3("Images", "Mobs", "penguin.png", frames=4),
        "penguin_sliding": timgload3("Images", "Mobs", "penguin.png", frames=4, rotation=-90),
        "snowman": timgload3("Images", "Mobs", "snowman.png", frames=4),
        "hallowskull": timgload3("Images", "Mobs", "hallowskull.png", frames=4),
        "keno": timgload3("Images", "Mobs", "bushes.png", frames=3, end_frame=1),
        "bok-bok": timgload3("Images", "Mobs", "bok-bok.png", frames=4),
        "chicken": timgload3("Images", "Mobs", "chicken.png", frames=2),
    }
    imgs["idle_hallowskull"] = imgs["hallowskull"][0:4]
    attrs = {"penguin":      {"hp": 100},
             "fluff-camel":  {"hp": 110},
             "camel":        {"hp":  80},
             "chicken":      {"hp":  40, "xvel": 0.3, "gravity": 0.1, "chance": 100, "drops": {"chicken": 1}},
             "keno":         {"hp": 250},
             "bok-bok":      {"hp":  60, "xvel": 2.2},
             "hallowskull":  {"hp": 250, "xvel": 0},
    }
    def __init__(self, img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, **kwargs):
        # init
        self.anim = 0
        self.init_images(img_data, "images")
        self.og_chunk_index = chunk_index
        self.chunk_index = list(chunk_index)
        self.x = chunk_index[0] * CW * BS + rel_pos[0] * BS
        self.y = chunk_index[1] * CH * BS + rel_pos[1] * BS
        self.pos = self.x, self.y
        self._rect = self.image.get_rect()
        self.rect = self._rect.copy()
        self.smart_vector = smart_vector
        self.traits = traits
        self.species = self.traits[0]
        self.attrs = Entity.attrs[self.species]
        self.block_data = []
        if smart_vector:
            if anchor == "bottomleft":
                self.left, self.bottom = self.pos
        else:
            self.og_rect = self.image.get_rect()
            setattr(self.og_rect, anchor, self.pos)
        self.og_pos = self._rect.topleft
        self.dx = 0
        self.xvel = 0
        self.yvel = 0
        self.gravity = self.attrs.get("gravity", 0.2)
        self.paused = False
        for k, v in (Entity.attrs.get(self.species, {}) | kwargs).items():
            setattr(self, k, v)

        # species
        if self.species == "penguin":
            self.penguin_spinning = False
            self.penguin_sliding = False

        # extra traits
        if "mob" in self.traits:
            self.max_hp = self.hp = self.attrs["hp"]
        if "demon" in self.traits:
            self.bar_rgb = lerp(RED, PURPLE, 50) + lerp(PURPLE, RED, 51)
        else:
            self.bar_rgb = bar_rgb

        # lasts
        self.taking_damage = False
        self.last_took_damage = ticks()
        self.glitching = False
        self.last_glitched = ticks()
        self.last_pause = ticks()

        # other attrs
        self.ray_cooldown = False
        self.dying = False
        self.initted_images = False

    @property
    def sign(self):
        return sign(self.xvel)

    def update(self, dt):  # entity update
        # self.x += 1
        self._rect.topleft = (int(self.x), int(self.y))
        self.rect.topleft = (self._rect.x - g.scroll[0], self._rect.y - g.scroll[1])
        # bok-bok
        # if self.species == "bok-bok":
        #     # direction change
        #     if (g.player._rect.centerx > self._rect.centerx and self.xvel < 0) \
        #             or (self._rect.centerx > g.player._rect.centerx and self.xvel > 0):
        #         delay(self.set_xvel, 0.6, -self.xvel)
        #     self.jump_over_obstacles()
        #
        #     # colliding with the player
        #     if self._rect.colliderect(g.player._rect):
        #         # g.player.flinch(0.1 * self.sign, -2)
        #         pass

        # if self.species == "chicken":
        #     self.jump_over_obstacles()
        #     if self.paused:
        #         if chance(1 / 10_000):
        #             self.paused = False
        #             if chance(1 / 2):
        #                 self.xvel *= -1
        #     else:
        #         if chance(1 / 40_000):
        #             self.paused = True

        # rest
        # if not self.dying:
        #     getattr(self, f"{self.species}_animate", self.animate)(dt)
        #     getattr(self, f"{self.species}_function", lambda_none)(dt)
        #     self.regenerate()

        self.draw()

    def jump_over_obstacles(self, yvel=-2):
        s = 1 if self.xvel >= 0 else -1
        ahead = pygame.Rect(self._rect.x + 10 * s, self._rect.y, *self.rect.size)
        if self.get_cols(ahead):
            self.yvel = yvel

    def set_xvel(self, value):
        self.xvel = value

    def get_cols(self, call=None):
        return [rect for rect in self.get_rects() if (call if call is not None else self._rect).colliderect(rect)]

    def get_rects(self):
        return [data[1] for data in self.block_data if is_hard(data[0].name)]

    def flinch(self, height):
        def inner():
            self.yvel = height
            fv = 0.6
            og_xvel = self.xvel
            self.xvel = fv if g.player.direc == "right" else -fv
            sleep(0.4)
            self.xvel = og_xvel
        DThread(target=inner).start()

    def glitch(self):
        mask = pygame.mask.from_surface(self.image)
        self.mask_surf_red = SmartSurface.from_surface(mask.to_surface(setcolor=(255, 40, 40, 127)))
        self.mask_surf_red.set_colorkey(BLACK)
        self.mask_surf_green = SmartSurface.from_surface(mask.to_surface(setcolor=(0, 255, 0, 127)))
        self.mask_surf_green.set_colorkey(BLACK)
        self.mask_surf_blue = SmartSurface.from_surface(mask.to_surface(setcolor=(0, 0, 255, 127)))
        self.mask_surf_blue.set_colorkey(BLACK)
        self.last_glitched = ticks()
        self.glitching = True

    def stop_taking_damage(self):
        if self.taking_damage:
            self.xvel = self.attrs["xvel"]
            self.taking_damage = False

    @property
    def xbound(self):
        return 1 if self.xvel >= 0 else -1

    @property
    def ybound(self):
        return 1 if self.yvel >= 0 else -1

    @property
    def width(self):
        return self.image.width

    @property
    def height(self):
        return self.image.height

    @property
    def mask(self):
        return pygame.mask.from_surface(self.image)

    @property
    def x_taken(self):
        return self._rect.x - self.og_pos[0]

    @property
    def y_taken(self):
        return self._rect.y - self.og_pos[1]

    def get_rect(self):
        return self._rect

    def init_images(self, img_data, type_):
        if type_ == "images":
            self.images = Entity.imgs[img_data]
            self.image = self.images[0]

    def movex(self, amount):
        if not self.dying:
            self.x += amount
            self.dx += amount
            if self.dx >= 30:
                self.dx = 0
                self.index += 1

    def draw(self):  # entity draw
        # if self.taking_damage:
        #     #image.fill((255, 0, 0, 125), special_flags=BLEND_RGB_ADD)
        #     image = red_filter(image)
        # if self.glitching:
        #     o = R * 1
        #     win.renderer.blit(self.mask_surf_red, (self.rect.x - o, self.rect.y))
        #     win.renderer.blit(self.mask_surf_green, (self.rect.x, self.rect.y + o))
        #     win.renderer.blit(self.mask_surf_blue, (self.rect.x + o, self.rect.y))
        win.renderer.blit(self.image, self.rect)

    def animate(self, dt):
        self.anim += g.p.anim_fps * dt
        try:
            self.images[int(self.anim)]
        except IndexError:
            self.anim = 0
        finally:
            self.image = (self.images if self.xvel >= 0 else self.h_images)[int(self.anim)]

    def penguin_animate(self, dt):
        self.anim += g.p.anim_fps * dt if self.penguin_spinning else 0
        try:
            self.images[int(self.anim)]
        except IndexError:
            self.anim = 0
            self.penguin_spinning = False
        finally:
            if self.penguin_sliding:
                self.image = (self.sliding_images if self.xvel >= 0 else self.h_sliding_images)[int(self.anim)]
            else:
                self.image = (self.images if self.xvel >= 0 else self.h_images)[int(self.anim)]
        if not self.penguin_spinning and not self.penguin_sliding and chance(1 / 500):
            self.penguin_spinning = True
        elif not self.penguin_sliding and not self.penguin_spinning and chance(1 / 1000):
            self.penguin_sliding = True
            self.xvel = 0.4
        elif self.penguin_sliding and chance(1 / 500):
            self.penguin_sliding = False
            self.xvel = 0.2

    def regenerate(self):
        if self.taking_damage and ticks() - self.last_took_damage >= 300:
            self.taking_damage = False
        if self.glitching and ticks() - self.last_glitched >= 300:
            self.glitching = False

    def take_damage(self, amount):
        self.taking_damage = True
        self.last_took_damage = ticks()
        self.hp -= amount


class Simp(pygame.sprite.Sprite):
    def __init__(self, img, center):
        pygame.sprite.Sprite.__init__(self)
        self.image = Image(img)
        self.rect = self.image.get_rect()
        self.rect.center = center


# F U N C T I O N S ------------------------------------------------------------------------------------ #
def fill(color, rect, fill=True):
    win.renderer.draw_color = color
    if fill:
        win.renderer.fill_rect(rect)
    else:
        win.renderer.draw_rect(rect)


def pos_to_tile(pos):
    x, y = pos
    # x and y must be unscaled & unscrolled; returns chunk and abs_pos ([chunk][pos] notation for accessation :D :P :/ :] Ü)
    target_x = floor(x / (BS * CW) + g.scroll[0] / (BS * CW))
    target_y = floor(y / (BS * CH) + g.scroll[1] / (BS * CH))
    target_chunk = (target_x, target_y)
    abs_x = floor(x / BS + g.scroll[0] / BS)
    abs_y = floor(y / BS + g.scroll[1] / BS)
    abs_pos = (abs_x, abs_y)
    return target_chunk, abs_pos


def correct_tile(target_chunk, abs_pos, xo, yo):
    rel_x, rel_y = abs_pos[0] % CW, abs_pos[1] % CH
    default = True
    pos_xo = xo
    pos_yo = yo
    chunk_xo = chunk_yo = 0
    # correct (verb) bordering chunks
    if rel_x + xo < 0:
        chunk_xo -= 1
    elif rel_x + xo > CW - 1:
        chunk_xo += 1
    if rel_y + yo < 0:
        chunk_yo -= 1
    elif rel_y + yo > CH - 1:
        chunk_yo += 1
    abs_pos = (abs_pos[0] + pos_xo, abs_pos[1] + pos_yo)
    target_chunk = (target_chunk[0] + chunk_xo, target_chunk[1] + chunk_yo)
    return target_chunk, abs_pos


def group(spr, grp):
    try:
        grp.add(spr)
    except AttributeError:
        grp.append(spr)
    if grp in (all_particles,):
        all_foreground_sprites.add(spr)


def bshow(str_):
    ret = str_
    if ret is None:
        return ""
    # ret = ret.replace("gold_", "golden_").replace("wood_", "wooden_")  # lexicon
    if "_en" in str_:  # enchanted block
        ret = ret.removesuffix("_en")
    if "_deg" in str_:  # rotated by n degrees
        spl = str_.split("_")
        deg = int(spl[-1].removeprefix("deg"))
        ret = f"{deg}{DEG} {bshow(spl[0])}"
    if "_st" in str_:  # stage of block
        spl = str_.split("_st")
        stage = spl[-1].removeprefix("st")
        ret = f"{spl[0]} [stage {stage}]"
    if "_f" in str_:  # forest
        ret = f"forest {ret.replace('_f', '')}"
    if "_sv" in str_:  # savanna
        ret = f"savanna {ret.replace('_sv', '')}"
    if "_sw" in str_:  # swamp
        ret = f"swamp {ret.replace('_sw', '')}"
    if "_a" in str_:  # acacia
        ret = f"acacia {ret.replace('_a', '')}"
    if "_ck" in str_:  # cooked
        ret = f"cooked {ret.replace('_ck', '')}"
    if "_vr" in str_:  # variation of block:
        ret = ret.split("_vr")[0]
    ret = ret.replace("_", " ").replace("-", " ")
    return ret


def tshow(str_):
    # init
    ret = str_
    if ret is None:
        return ""
    # tools
    for tool in tinfo:
        ret = ret.replace(f"_{tool}", f" {tool}")
    # other
    if "_en" in ret:
        pass
    return ret


def is_hard(blockname):
    return blockname not in walk_through_blocks and not is_bg(blockname)


def is_drawable(obj):
    try:
        return g.w.dimension == getattr(obj, "dimension", "data")
    except AttributeError:
        return not hasattr(obj, "visible_when") or obj.visible_when is None or (callable(obj.visible_when) and obj.visible_when())


def is_bg(name):
    return "_bg" in name


def color_base(block_type, colors, unplaceable=False, sep="-"):
    base_block = a.blocks[f"base-{block_type}"]
    w, h = base_block.get_size()
    for name, color in colors.items():
        colored_block = pygame.Surface((30, 30), pygame.SRCALPHA)
        for y in range(h):
            for x in range(w):
                c = base_block.get_at((x, y))
                if c != (0, 0, 0, 0):
                    rgb = c[:3]
                    if rgb != BLACK:
                        colored_block.set_at((x, y), rgb_mult(color, rgb[0] / 255))
                    else:
                        colored_block.set_at((x, y), BLACK)
        block_name = f"{name}{sep}{block_type}"
        a.blocks[block_name] = colored_block
        if unplaceable:
            unplaceable_blocks.append(block_name)


def rotate_base(block_type, rotations, prefix="base-", func=None, colorkey=None, ramp=False):
    if func is None:
        func = lambda x: block_type
    block_type = func(block_type)
    base_block = a.blocks[f"{prefix}{block_type}"]
    w, h = base_block.get_size()
    for r in rotations:
        name = f"{block_type}_deg{r}"
        if isinstance(r, str):
            name_angle = int(r.split("_")[0])
            name = f"{block_type}_deg{name_angle}"
            rotate_angle = int(r.split("_")[1].removesuffix("_ver").removesuffix("_hor"))
            a.blocks[name] = flip(rotate(base_block, rotate_angle), "_hor" in r, "_ver" in r)
        else:
            a.blocks[name] = rotate(base_block, r)
        if colorkey is not None:
            a.blocks[name].set_colorkey(colorkey)
        if ramp and r in (0, 90):
                ramp_blocks.append(name)
    rinfo[block_type] = rotations
    a.aliases["blocks"][block_type] = f"{block_type}_deg0"


def get_avatar():
    """
    svg_path = path("tempfiles", "avatar.svg")
    png_path = path("tempfiles", "avatar.jpg")
    with open(svg_path, "wb") as f:
        f.write(requests.get(avatar_url.replace(":mood", mood).replace(":seed", str(random.random()))).content)
    svg = svg2rlg(svg_path)
    renderPM.drawToFile(svg, png_path, fmt="JPG")
    pg_img = timgload3(png_path)
    pg_img = pgscale(pg_img, (30, 30))
    os.remove(svg_path)
    os.remove(png_path)
    """
    """
    png_path = path("tempfiles", "avatar.png")
    with open(png_path, "wb") as f:
        f.write(requests.get(avatar_url.replace(":seed", str(random.random()))).content)
    pil_img = PIL.Image.open(png_path).resize((10, 10), resample=PIL.Image.BILINEAR).resize((30, 30), PIL.Image.NEAREST)
    pg_img = pil_to_pg(pil_img)
    os.remove(png_path)
    """
    img = pygame.Surface((10, 10))
    skin_color = rgb_mult(SKIN_COLOR, randf(0.4, 8))
    hair_color = rand_rgb()
    hair_chance = 1
    img.fill(skin_color)
    for y in range(img.get_height()):
        for x in range(img.get_width()):
            if (x, y) in avatar_map:
                img.set_at((x, y), avatar_map[(x, y)])
            else:
                truthy = False
                try:
                    if chance(1 / hair_chance) and img.get_at((x, y - 1)) == hair_color:
                        truthy = True
                except IndexError:
                    truthy = True
                if truthy:
                    img.set_at((x, y), hair_color)
        hair_chance += 0.1
    img = pgscale(img, (30, 30))
    return img


def get_robot():
    half = pygame.Surface((5, 10))
    color = [rand(0, 255) for _ in range(3)]
    for y in range(half.get_height()):
        for x in range(half.get_width()):
            if chance(1 / 2.7):
                half.set_at((x, y), color)
    ret = pygame.Surface((half.get_width() * 2, half.get_height()))
    ret.blit(half, (0, 0))
    ret.blit(pygame.transform.flip(half, True, False), (ret.get_width() / 2, 0))
    ret = pygame.transform.scale(ret, (30, 30))
    return ret


def get_name():
    ret = ""
    for _ in range(rand(4, 8)):
        if not ret:
            pass


def cfilter(image, alpha, size, color=BLACK, colorkey=BLACK):
    surf = pygame.Surface((size[0], size[1]))
    surf.fill(color)
    surf.set_alpha(alpha)
    final_surf = image.copy()
    final_surf.blit(surf, (0, 0))
    final_surf.set_colorkey(colorkey)
    return final_surf


def tpure(tool):
    if tool[-1].isdigit():
        ret = tool.split("_en")[0]
    ret = tool.removesuffix("_en")
    for orb_name in orb_names.values():
        ret = ret.removeprefix(f"{orb_name}_")
    return ret


def gtool(tool):
    return tpure(tool).split("_")[-1]


def tore(tool):
    return tpure(tool).split("_")[1 if tool.endswith("_en") else 0]


def gorb(tool):
    if "_en" not in tool:
        return tool
    return orb_names_r[tool.split("_")[0]]


def s(num):
    return num * (30 / 3)


# I M A G E S ------------------------------------------------------------------------------------------ #
# specific colors
STONE_GRAY = (65, 65, 65)
WOOD_BROWN = (87, 44, 0)
DARK_WOOD_BROWN = (80, 40, 0)


class _Assets:
    def __init__(self):
        self.surf_assets = {"blocks": {}, "tools": {}, "icons": {}, "sprss": {}}
        self.aliases = {"blocks": {"door": "closed-door"}, "tools": {}, "icons": {}}
        self.sizes = {}

    @property
    def blocks(self):
        return self.surf_assets["blocks"]

    @blocks.setter
    def blocks(self, value):
        self.surf_assets["blocks"] = value

    @property
    def tools(self):
        return self.surf_assets["tools"]

    @tools.setter
    def tools(self, value):
        self.surf_assets["tools"] = value

    @property
    def icons(self):
        return self.surf_assets["icons"]

    @icons.setter
    def icons(self, value):
        self.surf_assets["icons"] = value

    @property
    def sprss(self):
        return self.surf_assets["sprss"]

    @sprss.setter
    def icon(self, value):
        self.sprss["sprss"] = value

    @property
    def all_assets(self):
        return list((self.blocks | self.tools | self.icons).keys())

    @property
    def all_asset_images(self):
        return self.blocks | self.tools | self.icons


a = _Assets()


# images
rinfo = {}
def load_blocks():
    # general
    _bsprs = imgload3("Images", "Spritesheets", "blocks.png")
    block_list = [
        ["air",         "bucket",           "apple",     "bamboo",        "cactus",        "watermelon",       "rock",       "chicken",     "leaf_f",                   ],
        ["chest",       "snow",             "coconut",   "coconut-piece", "command-block", "wood",             "bed",        "bed-right",   "wood_f_vrLRT"              ],
        ["base-pipe",   "",                 "dynamite",  "fire",          "magic-brick",   "watermelon-piece", "grass1",     "bush",        "wood_f_vrRT"               ],
        ["hay",         "base-curved-pipe", "glass",     "grave",         "sand",          "workbench",        "grass2",     "depr_leaf_f", "wood_f_vrLT"               ],
        ["snow-stone",  "soil",             "stone",     "vine",          "wooden-planks", "wooden-planks_a",  "stick",      "stone",       "wood_f_vrT",               ],
        ["anvil",       "furnace",          "soil_p",    "blue_barrel",   "red_barrel",    "gun-crafter",      "base-ore",   "bread",       "wood_f_vrLR", "wood_sv_vrN"],
        ["blackstone",  "closed-core",      "base-core", "lava",          "base-orb",      "magic-table",      "base-armor", "altar",       "wood_f_vrR",               ],
        ["closed-door", "wheat_st1",        "wheat_st2", "wheat_st3",     "wheat_st4",     "stone-bricks",     "",           "arrow",       "wood_f_vrL",  "soil_t"     ],
        ["open-door",   "",                 "daivinus",  "dirt_f_depr",   "grass3",        "",                 "bricks",     "solar-panel", "wood_f_vrN",  "dirt_t"     ],
        ["cable_vrF",   "cable_vrH",        "",          "",              "",              "",                 "",           "",            "grass_f",      ""          ],
        ["",            "",                 "",          "",              "",              "",                 "",           "",            "soil_f",      ""           ],
        ["",            "",                 "",          "",              "",              "",                 "",           "",            "dirt_f",      ""           ],
    ]
    for y, layer in enumerate(block_list):
        for x, block in enumerate(layer):
            a.blocks[block] = _bsprs.subsurface(x * 10 * R, y * 10 * R, 10 * R, 10 * R)
    placeholder_blocks = {"broken-penguin-beak", "jump-pad", "fall-pad", "tool-crafter"}
    for block in placeholder_blocks:
        surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        surf.fill(LIGHT_GRAY)
        # write(surf, "center", block, orbit_fonts[10], BLACK, *[s / 2 for s in surf.get_size()])
        a.blocks[block] = surf
    # special one-line blocks
    # a.blocks["soil_f"] = a.blocks["soil"].copy()
    a.blocks["soil_sw"] = cfilter(a.blocks["soil"].copy(), 150, (30, 4))
    a.blocks["soil_sv"] = cfilter(a.blocks["soil"].copy(), 150, (30, 4), (68, 95, 35))
    a.blocks["wood_sv"] = img_mult(a.blocks["wood"].copy(), 1.2)
    a.blocks["leaf_sw"] = cfilter(a.blocks["leaf_f"].copy(), 150, (30, 30))
    a.blocks["leaf_sk"] = cfilter(a.blocks["leaf_f"].copy(), 150, (30, 30), PINK)
    a.blocks["water"] = pygame.Surface((10, 10), pygame.SRCALPHA); a.blocks["water"].fill((17, 130, 177)); a.blocks["water"].set_alpha(180)
    # spike plant
    a.blocks["spike-plant"] = pygame.Surface((30, 30), pygame.SRCALPHA)
    for i in range(3):
        _x = nordis(15, 3)
        _y = 30
        while _y != 0:
            _x += choice((-3, 0, 3))
            if _x < 0:
                _x = 0
            elif _x > 9:
                _x = 9
            _y -= 1
            pygame.draw.rect(a.blocks["spike-plant"], rgb_mult(GREEN, randf(0.6, 1.4)), (_x, _y, 3, 3))
    pygame.draw.rect(a.blocks["spike-plant"], rgb_mult(YELLOW, randf(0.6, 1.4)), (_x, _y, 3, 3))
    # portal generator
    a.blocks["portal-generator"] = pygame.Surface((30, 30), pygame.SRCALPHA)
    for y in range(10):
        for x in range(10):
            surf = a.blocks["portal-generator"]
            color = [rand(0, 255) for _ in range(3)]
            rect = (x * 3, y * 3, 3, 3)
            pygame.draw.rect(surf, color, rect)
    # gray
    a.blocks["wall"] = pygame.Surface((30, 30))
    a.blocks["wall"].fill((100, 100, 100))
    # bedrock
    b = pygame.Surface((10, 10))
    for y in range(10):
        for x in range(10):
            b.set_at((x, y), rgb_mult(BLACK, 5))
    b = pygame.transform.scale(b, [s * 3 for s in b.get_size()])
    # ramp
    a.blocks["base-ramp"] = pygame.Surface((BS, BS), pygame.SRCALPHA)
    pygame.gfxdraw.aapolygon(a.blocks["base-ramp"], [(0, 0), (0, BS - 1), (BS, BS - 1)], GRAY)
    # stone
    a.blocks["stone"] = grayscale(a.blocks["dirt_f_depr"])
    # jetpack
    pass
    # grass3
    g = a.blocks["grass3"].copy()
    a.blocks["grass3"] = pygame.Surface((g.get_width(), g.get_height() * 2), pygame.SRCALPHA)
    a.blocks["grass3"].blit(g, (0, 0))
    # slime
    a.blocks["slime"] = pygame.Surface((BS, BS))
    a.blocks["slime"].fill(SLIME_GREEN)
    # ------------------------------------------------------
    # ores
    for name, color in [(oi, oinfo[oi]["color"]) for oi in oinfo]:
        a.blocks[name] = swap_palette(a.blocks["base-ore"], BLACK, color)
        a.blocks[f"{name}-ingot"] = pygame.Surface((30, 30), pygame.SRCALPHA)
        ingot_keys = ("blocks", f"{name}-ingot")
        ingot_img = ndget(a.surf_assets, ingot_keys)
        pygame.draw.polygon(ingot_img, color, ((0, 11), (22, 3), (30, 11), (8, 19)))
        pygame.draw.polygon(ingot_img, rgb_mult(color, 0.9), ((0, 11), (8, 19), (8, 27), (0, 19)))
        pygame.draw.polygon(ingot_img, rgb_mult(color, 0.8), ((8, 19), (30, 11), (30, 19), (8, 27)))
        # a.surf_assets[ingot_keys[0]][ingot_keys[1]] = pil_to_pg(pil_pixelate(pg_to_pil(ndget(a.surf_assets, ingot_keys)), (10, 10)))
        unplaceable_blocks.append(ingot_keys[-1])
    a.blocks["bedrock"] = b
    for name, img in a.blocks.copy().items():
        if name.endswith("-planks"):
            # stairs
            stairs = img.copy()
            stairs.fill(BLACK, (0, 0, *[s / 2 for s in img.get_size()]))
            stairs.set_colorkey(BLACK)
            stairs_name = f"{name.removesuffix('-planks')}-stairs"
            a.blocks[stairs_name] = stairs
            rotate_base(name, rotations4_stairs_tup, prefix="", func=lambda x: x.removesuffix("-planks") + "-stairs", colorkey=BLACK, ramp=True)
            slabs = img.subsurface(0, 0, img.get_width(), img.get_height() / 2)
            slabs_name = f"{name.removesuffix('-planks')}-slabs"
            a.blocks[slabs_name] = pygame.Surface((BS, BS), pygame.SRCALPHA)
            a.blocks[slabs_name].blit(slabs, (0, BS / 2))
    # deleting unneceserry blocks that have been modified anyway
    del a.blocks["soil"]


def load_tools():
    # additional tools
    a.sprss["bow"] = imgload3("Images", "Spritesheets", "bow.png", frames=4)
    a.sprss["bat"] = imgload3("Images", "Spritesheets", "bat.png", frames=6)

    # lists
    _tsprs = imgload3("Images", "Spritesheets", "tools.png")
    tool_list = [
        ["pickaxe", "axe",    "sickle",  "monocular"],
        ["shovel",  "rake",   "scissors"],
        ["kunai",   "hammer", "sword",   "grappling-hook"]
    ]
    tools = {}
    whole_tools = {"stick"}
    plus = []
    for name, sprs in a.sprss.items():
        ap = [{"name": f"{name}{i}", "img": x} for i, x in enumerate(sprs)]
        plus.append(ap)
        plus[-1].append({"name": name, "img": [bdict["img"] for bdict in plus[-1] if bdict["name"] == f"{name}0"][0]})
        for data in ap:
            a.sizes[data["name"]] = data["img"].get_size()
    # actually generating
    for y, layer in enumerate(tool_list + plus):
        for x, tool in enumerate(layer):
            if isinstance(tool, str):
                tool_img = _tsprs.subsurface(x * 10 * R, y * 10 * R, 10 * R, 10 * R)
                tool_name = tool
            elif isinstance(tool, dict):
                tool_img = tool["img"]
                tool_name = tool["name"]
            if bpure(tool_name) not in non_ored_tools:
                for name, color in tool_rarity_colors.items():
                    fin_name = f"{name}_{tool_name}"
                    if name != "coal":
                        a.tools[fin_name] = swap_palette(tool_img, STONE_GRAY if tool_name not in whole_tools else WOOD_BROWN, color)

                    #a.tools[fin_name] = borderize(tool_img, color)
            else:
                a.tools[bpure(tool_name)] = tool_img

    a.og_tools = {k: v.copy() for k, v in a.tools.items()}


def load_guns():
    for gun_part in g.tup_gun_parts:
        for gun_filename in os.listdir(path("Images", "Guns", gun_part)):
            gun_name = splitext(gun_filename)[0]
            a.blocks[f"{gun_name}_{gun_part}"] = imgload3("Images", "Guns", gun_part, gun_filename)
            gun_blocks.append(f"{gun_name}_{gun_part}")
    a.og_blocks = {k: v.copy() for k, v in a.blocks.items()}


def load_icons():
    _isprs = imgload3("Images", "Spritesheets", "icons.png")
    icon_list = [
        ["lives", "shield", "hunger", "thirst", "energy", "o2", "xp"]
    ]
    for y, layer in enumerate(icon_list):
        for x, tool in enumerate(layer):
            a.icons[tool] = _isprs.subsurface(x * 0.5 * 10 * R, y * 0.5 * 10 * R, 0.5 * 10 * R, 0.5 * 10 * R)
    a.icons["armor"] = a.blocks["base-armor"].subsurface((0, 10 * R * 0.5, 10 * R, 0.5 * 10 * R))
    a.og_icons = {k: v.copy() for k, v in a.icons.items()}


def load_sizes():
    for atype, dict_ in a.surf_assets.items():
        if isinstance(dict_, dict):
            for name, img in dict_.items():
                if isinstance(img, pygame.Surface):
                    a.sizes[name] = img.get_size()


# B L O C K  D A T A ----------------------------------------------------------------------------------- #
# ore info
oinfo = {
    # name        | crystal |       | mohs |    | fracture toughness  |  price in $ / kg |  | ppm in crust |      | mined at depth in km|      | color in rgb|
    # metals
    "diamond":    {"crystal": "FCC", "mohs": 10, "toughness":   3.4, "price": 20_000_000,    "ppm": None,          "depth": (140_000, 200_000), "color": POWDER_BLUE},
    "molybdenum": {"crystal": "BCC", "mohs":  6, "toughness":  30,   "price":        110,    "ppm":      1.2,      "depth": 1 ,                 "color": SILVER},
    "aluminium":  {"crystal": "FCC", "mohs":  3, "toughenss":  33,   "price":         18,    "ppm":    82_300,     "depth": 0,                  "color": SILVER},
    "titanium":   {"crystal": "HCP", "mohs":  6, "toughness":  57.5, "price":         61,    "ppm":  5_650,        "depth": 0,                  "color": SILVER},
    "gold":       {"crystal": "FCC", "mohs":  3, "toughness":  65,   "price":     55_500,    "ppm":      0.004,    "depth": 0,                  "color": GOLD},
    "copper":     {"crystal": "FCC", "mohs":  3, "toughness":  70,   "price":         27,    "ppm":     60,        "depth": 1,                  "color": (184, 115, 51)},
    "palladium":  {"crystal": "FCC", "mohs":  5, "toughness":  90,   "price":     65_829,    "ppm":      0.015,    "depth": 0,                  "color": (190, 173, 210)},
    "vanadium":   {"crystal": "BCC", "mohs":  7, "toughness": 110,   "price":      2_000,    "ppm":    100,        "depth": 0,                  "color": SILVER},
    "nickel":     {"crystal": "FCC", "mohs":  4, "toughness": 125,   "price":         77,    "ppm":     85,        "depth": 0,                  "color": (189, 186, 174)},
    "uranium":    {"crystal": "FCC", "mohs":  6, "toughness": 130,   "price":         11.75, "ppm":      2.5,      "depth": 0,                  "color": MOSS_GREEN},
    "iron":       {"crystal": "BCC", "mohs":  4, "toughness": 135,   "price":         53,    "ppm": 50_000,        "depth": [9.14, 1.219],      "color": LIGHT_GRAY},
    "tungsten":   {"crystal": "BCC", "mohs":  9, "toughness": 135,   "price":        110,    "ppm":      1.2,      "depth": 0.260,              "color": (226, 229, 222)},
    "manganese":  {"crystal": "BCC", "mohs":  6, "toughness": 135,   "price":         17,    "ppm":      1066,     "depth": 1,                  "color": LIGHT_GRAY},
    "chromium":   {"crystal": "BCC", "mohs":  8, "toughness": 135,   "price":        100,    "ppm":    110,        "depth": 0,                  "color": SILVER},
    # gemstones
    "coal":       {"mohs": 3, "price": 0.39,   "ppm": 000,    "depth": [0, 300],                      "color": BLACK},
    "orthoclase": {"mohs": 6, "price": 93,     "ppm": None,   "depth": None,                          "color": (255, 197, 148)},
    "topaz":      {"mohs": 8, "price": 000,    "ppm": None,   "depth": 0,                             "color": (30, 144, 255)},
    "talc":       {"mohs": 1, "price": 4.2,    "ppm": 000,    "depth": 0,                             "color": MINT},
    "quartz":     {"mohs": 7, "price": 000,    "ppm": None,   "depth": None,                          "color": LIGHT_PINK},
    "tin":        {"mohs": 1, "price": 25.75,  "ppm": 000,    "depth": 0,                             "color": SILVER},
    "corundum":   {"mohs": 9, "price": 000,    "ppm": 000,    "depth": [3.85, 10],                    "color": (168, 50, 107)},
    "granite":    {"mohs": 6, "price": None,   "ppm": 800000, "depth": [1.5, 50],                     "color": (244, 174, 114)}
}
c = 2
for ore in oinfo:
    # generation chance
    oinfo[ore]["chance"] = c
    c /= 1.4
    oinfo

# tree info
trinfo = {       # force in N (Janka scale)
    "live oak": {"Janka": 11_900}
}

# alloy info
alinfo = {
    "Austenitic Stainless Steel": {
        "atoms": {
            "Fe": 70,
            "Cr": 18,
            "Ni":  8,
        },
        "tensile": 515,
    },
    "High-Speed Steel": {
        "atoms": {
            "Fe": 84,
            "W":   6,
            "Mo":  5,
        },
        "tensile": 1200,
    },
    "PH Stainless Steel": {
        "atoms": {
            "Fe": 73,
            "Cr": 17,
            "Ni":  4,
        },
        "tensile": 1000
    },
    "Tool Steel": {
        "atoms": {
            "Fe": 91,
            "Cr":  5,
            "C":   1
        },
        "tensile": 1860
    },
    "Duplex Stainless Steel": {
        "atoms": {
            "Fe": 67,
            "Cr": 22,
            "Ni":  5,
        },
        "tensile": 620
    },
    "Chromoly Steel": {
        "atoms": {
            "Fe": 97,
            "Cr":  0.8,
            "Mo":  0.2,
        },
        "tensile": 700
    },
    "High-Carbon Steel": {
        "atoms": {
            "Fe": 98,
            "C":   1,
            "Mn":  0.5
        },
        "tensile": 685
    },
    "Martensitic Steel": {
        "atoms": {
            "Fe": 78,
            "Cr": 17,
            "C":  1.1,
        },
        "tensile": 760
    },
    "Mild Steel": {
        "atoms": {
            "Fe": 98,
            "Mn":  1,
            "C":   0.25,
        },
        "tensile": (400 + 550) / 2
    },
}
for name, data in alinfo.items():
    perc = data["atoms"]
    alinfo[name]["atoms"]["Fe"] += 100 - sum(perc.values())

ore_blocks = set(oinfo.keys())

tool_rarity_colors = {k: v["color"] for k, v in oinfo.items()}

wheats = [f"wheat_st{i}" for i in range(1, 5)]
block_breaking_times = {"stone": 1000, "sand": 200, "hay": 150, "soil": 200, "dirt": 200, "watermelon": 500}
block_breaking_amounts = {"stone": 0.01, "sand": 0.01, "hay": 0.07, "soil": 0.05, "dirt": 0.05, "watermelon": 0.01}

# tool info
tinfo = {
    "axe":
        {"blocks": {"wood": 0.03, "bamboo": 0.024, "coconut": 0.035, "cactus": 0.04, "barrel": 0.01, "workbench": 0.02, "wooden-planks": 0.035}},

    "pickaxe":
        {"blocks": {"snow-stone": 0.036, "stone": 0.02, "blackstone": 0.015, "grave": 0.015, "rock": 0.015}},

    "shovel":
        {"blocks": {"soil": 0.16, "dirt": 0.06, "sand": 0.2}},

    "sickle":
        {"blocks": {"hay": 0.10}},

    "scissors":
        {"blocks": {"leaf": 0.04, "vine": 0.02}},

    "sword":
        {"blocks": {}},

    "grappling-hook":
        {"blocks": {}},

    "hammer":
        {"blocks": {}},

    "bow":
        {"blocks": {}},

    "bat":
        {"blocks": {}},
}
tinfo["sickle"]["blocks"] |= {wheat: 0.12 for wheat in wheats}

sinfo = {
    "iron": {
        "damage": 10,
        "knockback": 10,
        "cooldown": 1000
    }
}

health_tools = [tool for tool in tinfo if tool not in {}]
unrotatable_tools = {"sword", "bow", "grappling-hook", "bat"}
unflipping_tools = {"grappling-hook"}
non_ored_tools = {"bat", "monocular"}
fin_mult = 1 / 0.015873
for mult, ore in enumerate(oinfo, 50):
    tinfo["pickaxe"]["blocks"][ore] = (11 - oinfo[ore]["mohs"]) * 0.003 * (1 - (1 / mult * fin_mult - 1) * 2.3)
tool_blocks = set(itertools.chain.from_iterable([list(tinfo[tool]["blocks"].keys()) for tool in tinfo]))

# furnace
fuinfo = {
    "sand": "glass"
}
for ore in oinfo:
    fuinfo[ore] = f"{ore}-ingot"
fueinfo = {  # combustion energy in MJ | subtraction in amount p/f
    "coal": {"mj": 33, "sub": 0.007},
}

# B L O C K  C L A S S I F I C A T I O N S ------------------------------------------------------------- #
cables = {name for name in a.blocks.keys() if bpure(name) == "cable"}
walk_through_blocks = {"air", "fire", "lava", "water", "spike-plant", "grass1", "grass2", "grass_f",
                       "workbench", "anvil", "furnace", "gun-crafter", "altar", "magic-table", "vine",
                       "open-door", "arrow", "grass3", "chest", "bed", "bed-right", "solar-panel",
                       *wheats, *cables}
feature_blocks = {"solar-panel"}
unbreakable_blocks = {"air", "fire", "water"}
item_blocks = {"dynamite"}
unbreakable_blocks = {"air", "water"}
functionable_blocks = {"dynamite", "command-block"}
climbable_blocks = ["vine"]
dif_drop_blocks = {"coconut": {"coconut-piece": 2},
                   "watermelon": {"watermelon-piece": 2},
                   "bed-right": {"bed": 1}}
fall_damage_blocks = {"hay": 10}
gun_blocks = []
furnaceable_blocks = {"chicken"} | set(x for x in fuinfo if x not in fueinfo)
block_breaking_effects = {
    "glass": {"damage": (0, 4)}
}
ramp_blocks = []
empty_blocks = {None, "air"}

# food info
finfo = {
    # energy is in kcal
    # thirst is in ml water (or grams for that matter)
    # vitamins is in μg
    # iron and potassium is in mg
    # * x is relative to 100g of that particular food (e.g. 1 apple is 200g on average)
    "apple": {
        "amounts": {
            "thirst": 85.6 * 2,
            "energy": 52 * 2,
            "vitamin A": 3 * 2,
            "vitamin B": 0.041 * 2,
            "vitamin C": 4.6 * 2,
            "Fe": 0.12 * 2,
            "K": 107
        },
        "speed": 2
    },

    "coconut-piece": {
        "amounts": {
            "thirst": 95 * 6.8,
            "energy": 19 * 6.8,
            "vitamin A": 0,
            "vitamin B": 0.032,
            "vitamin C": 2.4
        },
        "speed": 1.25
    },

    "watermelon-piece":
        {"amounts": {"thirst": 8255, "energy": 1361}, "speed": 2.5},
    "chicken":
        {"amounts": {                "energy": 1784}, "speed": 1.25},
    "chicken_ck":
        {"amounts": {                "energy": 2358}, "speed": 1.5},
    "bread":
        {"amounts": {"thirst": -3,   "energy": 1060}, "speed": 4}
}
for food in finfo:
    finfo[food]["amounts"]["energy"] /= 100
meat_blocks = {"chicken"}
for food in furnaceable_blocks:
    if food in finfo:
        name = food + "_ck"
        finfo[food + "_ck"] = {"amounts": {k: v * 2 for k, v in finfo[food]["amounts"].items()}, "speed": finfo[food]["speed"]}

# crafting info
cinfo = {
    # blocks
    "wooden-planks":    {"recipe": {"wood": 1}, "amount": 3, "energy": 5},
    "sand-brick":       {"recipe": {"sand": 1}, "amount": 3, "energy": 7},
    "anvil":            {"recipe": {"stone": 1}, "energy": 10},
    "portal-generator": {"recipe": {"water": 1}, "energy": 20},
    "furnace":          {"recipe": {"stone": 9}, "energy": 12},
    # food
    "bread":            {"recipe": {"wheat_st4": 3}, "energy": 2},
    "wheat_st4":        {"recipe": {"hay": 1}, "amount": 2, "energy": 1, "reverse": True}
}
for k, v in cinfo.copy().items():
    if v.get("reverse", False):
        key = next(iter(v["recipe"]))
        cinfo[key] = {"recipe": {k: v["amount"]}, "amount": v["recipe"][key], "energy": v["energy"]}

# gun info
ginfo = \
{
    "scope":
        {
            "prototype":
                {
                    "color": GREEN + (150,),
                    "radar": True
                },
        },

    "magazine":
        {
            "prototype":
                {
                    "size": 75,
                }
        }
}


ainfo = {}
block_info = {
}

tool_info = {
    "majestic"
}

unplaceable_blocks.extend([*gun_blocks, "bucket", "broken-penguin-beak", "jetpack"])

# loading assets
load_blocks()
load_tools()
load_guns()
load_icons()

chest_blocks = [block for block in a.blocks if block is not None and block not in ("air",)]
soils = {block for block in a.blocks if bpure(block) == "soil"}
dirts = {block for block in a.blocks if bpure(block) == "dirt"}
tinfo["shovel"]["blocks"] |= {soil: 0.1 for soil in soils} | {dirt: 0.1 for dirt in dirts}

# - initializations after asset loading -
# tool crafts
for tool in a.tools:
    if "_" in tool:
        o, n = tool.split("_")
        if n == "axe":
            o += ("-ingot" if o != "wood" else "")
            ainfo[tool] = {"recipe": {o: 2, "stick": 1}, "energy": 8}

# armo(u)r
armor_types = ("helmet", "chestplate", "leggings")
for ore in oinfo:
    for at in armor_types:
        name = f"{ore}_{at}"
        ams = {"helmet": 4, "chestplate": 6, "leggings": 5}
        ens = {"helmet": 8, "chestplate": 10, "leggings": 9}
        ainfo[name] = {"recipe": {f"{ore}-ingot": ams[at]}, "energy": ens[at]}

# adding specific blocks to tinfo
for block in a.blocks:
    if block.startswith("wooden-"):
        if block.endswith("-stairs"):
            mult = 0.75
        elif block.endswith("-slab"):
            mult = 0.5
        tinfo["axe"]["blocks"][block] = mult * tinfo["axe"]["blocks"]["wood"]

# transparent blocks
transparent_blocks = []
for name, img in a.blocks.items():
    with suppress(BreakAllLoops):
        for y in range(img.get_height()):
            for x in range(img.get_width()):
                if img.get_at((x, y)) == (0, 0, 0, 0):
                    transparent_blocks.append(name)
                    raise BreakAllLoops

# block mods
color_base("orb", orb_colors, unplaceable=True)
rotate_base("pipe", rotations2)
rotate_base("curved-pipe", rotations4)
rotate_base("ramp", rotations4, ramp=True)
rotate_base("cable_vrF", rotations2, prefix="")
rotate_base("cable_vrH", rotations4, prefix="")

# visual orbs
visual_orbs_sprs = timgload3("Images", "Spritesheets", "visual_orbs.png")
visual_orbs = {}

# miscellaneous

# L A S T  S E C O N D  I N I T I A L I Z A T I O N S
oinfo["stone"] = {"mohs": 3}
swinging_tools = {"axe", "pickaxe", "shovel", "sickle"}
rotating_tools = swinging_tools

# O T H E R  I M A G E S
# mini orb blocks
for block in a.blocks.copy():
    if block.endswith("-orb"):
        # b = pil_to_pg(pil_pixelate(pg_to_pil(pygame.transform.scale(a.blocks[block], (12, 12))), (4, 4)))
        b = pygame.Surface((4, 4), pygame.SRCALPHA)
        # black
        coords = [(1, 0), (2, 0), (0, 1), (3, 1), (0, 2), (3, 2), (1, 3), (2, 3)]
        for c in coords:
            b.set_at(c, BLACK)
        # inner
        coords = [(1, 1), (2, 1), (1, 2), (2, 2)]
        for c in coords:
            b.set_at(c, a.blocks[block].get_at((9, 6)))
        # shine
        coord = (1, 1)
        b.set_at(coord, a.blocks[block].get_at((3, 4)))
        # final
        b = pygame.transform.scale(b, (12, 12))
        a.blocks[f"mini-{block}"] = b

# armor
base_armor = imgload("Images", "Visuals", "base_armor.png")
bases = {
    "helmet": base_armor.subsurface(1, 0, 9, 3),
    "chestplate": base_armor.subsurface(0, 3, 11, 4),
    "leggings": base_armor.subsurface(1, 7, 9, 2)
}

a.blocks |= {f"{k}_ck": pil_to_pg(pil_contrast(pg_to_pil(v))) for k, v in a.blocks.items() if k in furnaceable_blocks}

# a.blocks |= {f"base-{k}": v for k, v in bases.items()}
# for base_name, base_img in bases.items():
#     for tool_name, data in oinfo.items():
#         color = data["color"]
#         name = f"{tool_name}_{base_name}"
#         bg_img = pygame.Surface(base_armor.get_size(), pygame.SRCALPHA)
#         blit_img = swap_palette(base_img, WHITE, color)
#         bg_img.blit(blit_img, (bg_img.get_width() / 2 - blit_img.get_width() / 2, bg_img.get_height() / 2 - blit_img.get_height() / 2))
#         # bg_img = pygame.transform.scale(bg_img, (30, 30))
#         # a.blocks[name] = bg_img
#         a.blocks[name] = blit_img
#         unplaceable_blocks.append(name)
# ore_colors = {ore: data["color"] for ore, data in oinfo.items()}

# generating textures from surfaces
a.tex_assets = {k: {name: CImage(Texture.from_surface(win.renderer, img)) for name, img in v.items()} if k != "sprss" else {sprs: [CImage(Texture.from_surface(win.renderer, frame)) for frame in images] for sprs, images in v.items()} for k, v in a.surf_assets.items()}

# wichtig: load all blocks and modifications before loading sizes
load_sizes()
