import pygame
import sys
import random
import inspect
import operator as op
import PIL.Image
import PIL.ImageEnhance
import PIL.ImageDraw
import PIL.ImageFilter
from datetime import date
#
from pyengine.pgwidgets import *
from pyengine.imports import *
from pyengine.basics import *
from pyengine.pilbasics import *
#
from .imgtools import *

#
# print(sustainability(400, 1.58, 342.3, 12))
# print(sustainability(15, 0.80, 46.08, 2))
# print(sustainability(15, 0.80, 100.21, 7))
# print(sustainability(30, 0.82, 114.23, 16/2))
# print(sustainability(32.6, 3.50, 72.11, 8/2))
# print(sustainability(61.5, 0.95, 142.28, 20/2))
# print(sustainability(7.6, 0.90, 128.26, 9))


# N O N - G R A P H I C A L  C L A S S E S  P R E - I N I T I A L I Z E D ------------------------------ #
class BlockNotFoundError(Exception):
    pass


class System:
    version = "Alpha"
    if version not in ("Alpha", "Beta"):
        maj, min, pat = version.split(".")


# W I N D O W ------------------------------------------------------------------------------------------ #
class CRenderer(Renderer):  # DEPRECATED DO NOT USE PLZ
    def blit(self, texture, pos, *args, **kwargs):
        try:
            # texture is an SDL2 texture
            w, h = texture.width, texture.height
        except AttributeError:
            # texture is an SDL2 image
            w, h = texture.texture.width, texture.texture.height
        try:
            # position is a tuple
            super().blit(texture, pygame.Rect(pos, (w, h)), *args, **kwargs)
        except TypeError:
            # position is a rect
            super().blit(texture, pos, *args, **kwargs)


# V I S U A L  &  B G  I M A G E S --------------------------------------------------------------------- #
# hotbar blits
yo = 10
xo = 85
inventory_img = timgload3("assets", "Images", "Background", "inventory.png", tex=True)
inventory_width, inventory_height = inventory_img.width, inventory_img.height
inventory_rect = inventory_img.get_rect(midtop=(win.width / 2 + xo, yo))
extended_inventory_img = timgload3("assets", "Images", "Background", "extended_inventory.png", tex=True)
extended_inventory_width, extended_inventory_height = extended_inventory_img.width, extended_inventory_img.height
extended_inventory_rect = extended_inventory_img.get_rect(midtop=(0, 138))
tool_holders_img = timgload3("assets", "Images", "Background", "tool_holders.png", tex=True)
tool_holders_width, tool_holders_height = tool_holders_img.width, tool_holders_img.height
tool_holders_rect = tool_holders_img.get_rect(midtop=(win.width / 2 - xo, yo))
pouch_img = timgload3("assets", "Images", "Background", "pouch.png")
pouch_icon = timgload3("assets", "Images", "Background", "pouch_icon.png")
pouch_width = pouch_img.width
square_border_img = timgload3("assets", "Images", "Visuals", "square_border.png")
square_border_rect = square_border_img.get_rect()
player_border = timgload3("assets", "Images", "Visuals", "player_border.png")
player_border_rect = pygame.Rect(10, 10, player_border.width, player_border.height)
dart_img = timgload3("assets", "Images", "Visuals", "dart.png")
orbs = {
    "blue": timgload3("assets", "Images", "Visuals", "base_orb.png"),
    "green": timgload3("assets", "Images", "Visuals", "base_orb.png"),
    "purple": timgload3("assets", "Images", "Visuals", "base_orb.png"),
}
orbs["blue"].color = POWDER_BLUE
orbs["green"].color = MOSS_GREEN
orbs["purple"].color = PURPLE

# backgrounds
player_hit_chart = timgload3("assets", "Images", "Background", "player_hit_chart.png")
lock = timgload3("assets", "Images", "Player_Skins", "lock.png")
frame_img = scale3x(timgload3("assets", "Images", "Background", "frame.png"))
armor_indicator = timgload3("assets", "Images", "Background", "armor_indicator.png")
bag_img = timgload3("assets", "Images", "Background", "bag.png")
logo_img = timgload3("assets", "Images", "Background", "logo.png", scale=3, img=False)

# surfaces
bag_rect = bag_img.get_rect(topleft=(24, 157))
# bag_mask = pygame.mask.from_surface(bag_img)
clouds = {i + 1: timgload3("assets", "Images", "Background", f"cloud{i + 1}.png") for i in range(1)}
cursor_img = pygame.Surface((10, 10), pygame.SRCALPHA)
cursor_img.fill(WHITE, (4, 0, 2, 10))
cursor_img.fill(WHITE, (0, 4, 10, 2))
black_square = pygame.Surface((BS, BS), pygame.SRCALPHA)

# visuals
arrow_sprs = timgload3("assets", "Images", "Spritesheets", "arrow.png", frames=11)
shower_sprs = timgload3("assets", "Images", "Spritesheets", "shower.png", frames=9)
shower_sprs = timgload3("assets", "Images", "Spritesheets", "fuel.png", frames=9)
chest_template = timgload3("assets", "Images", "Visuals", "chest_template.png")
leaf_img = timgload3("assets", "Images", "Visuals", "leaf.png")
breaking_sprs = timgload3("assets", "Images", "Visuals", "breaking.png", frames=4)
right_bar_surf = pygame.Surface((50, 200)); right_bar_surf.fill(LIGHT_GRAY)
death_screen = pygame.Surface(win.size); death_screen.fill(RED); death_screen.set_alpha(150)
cartridge_img = pygame.Surface((10, 3))
cartridge_img.fill((255, 184, 28))
sky_bg = pygame.transform.rotozoom(pygame.transform.scale(lerp_img(SKY_BLUE, WHITE, win.height, win.height), win.size), 90, 1)
fog_light = imgload3("assets", "Images", "Visuals", "fog.png")
fog_w, fog_h = fog_light.get_size()
test_sprs = timgload3("assets", "Images", "Spritesheets", "test.png", frames=7)
gas_sprs = timgload3("assets", "Images", "Spritesheets", "gases.png", frames=5)
#pygame.display.set_icon(timgload3("assets", "Images", "Visuals", f"{Platform.os.lower()}_icon.png"))
keybind_icons = {"rmouse": imgload3("assets", "Images", "Visuals", "mouse.png")}
keybind_icons["lmouse"] = flip(keybind_icons["rmouse"], True, False)

# surfaces
workbench_img = timgload3("assets", "Images", "Midblits", "workbench.png")
_wbi = get_icon("arrow")
workbench_icon = pygame.transform.scale(_wbi, [s // 2 for s in _wbi.get_size()])
furnace_img = timgload3("assets", "Images", "Midblits", "furnace.png")
furnace_img = timgload3("assets", "Images", "Midblits", "furnace.png")
anvil_img = timgload3("assets", "Images", "Midblits", "anvil.png")
gun_crafter_img = timgload3("assets", "Images", "Midblits", "gun_crafter.png")
magic_table_img = timgload3("assets", "Images", "Midblits", "magic-table.png")

midblits = {}
for surface in os.listdir(path("assets", "Images", "Midblits")):
    name, ext = os.path.splitext(surface)
    tex = timgload3("assets", "Images", "Midblits", surface)
    midblits[name] = tex


# tool crafter
"""
w, h = 550, 380
tool_crafter_img = pygame.Surface((w, h), pygame.SRCALPHA)
pygame.draw.rect(tool_crafter_img, LAPIS_BLUE, (0, 0, w, h))
pygame.draw.rect(tool_crafter_img, BLACK, (0, 0, w, h), 3)
pygame.draw.rect(tool_crafter_img, LAPIS_BLUE, (0, 0, 124, h))
pygame.draw.rect(tool_crafter_img, BLACK, (0, 0, 124, h), 3)
pygame.image.save(tool_crafter_img, path("assets", "Images", "Midblits", "tool-crafter.png"))
pg_to_pil(tool_crafter_img).show()
tool_crafter_img = Texture.from_surface(win.renderer, tool_crafter_img)
tool_crafter_rect = tool_crafter_img.get_rect()
"""
tool_crafter_img = timgload("assets", "Images", "Midblits", "tool-crafter.png")
tool_crafter_rect = tool_crafter_img.get_rect()
tool_crafter_sword_width = 124
tool_crafter_metals_width = tool_crafter_rect.width - tool_crafter_sword_width

# crafting and midblit constants
workbench_rect = workbench_img.get_rect(center=win.center)
furnace_rect = furnace_img.get_rect(center=workbench_rect.center)
workbench_center = workbench_rect.center
workbench_x, workbench_y = workbench_center
chest_rect = chest_template.get_rect(center=win.center)
chest_rects = []
chest_indexes = {}
chest_rect_start = [p + 3 for p in chest_rect.topleft]
chest_sx, chest_sy = chest_rect_start
_sx, _sy = chest_sx, chest_sy
i = 0
for y in range(5):
    for x in range(5):
        _x = x * 33 + _sx
        _y = y * 51 + _sy
        chest_rects.append(pygame.Rect(_x, _y, 30, 30))
        chest_indexes[_x, _y] = i
        i += 1
w, h = (gun_crafter_img.width, gun_crafter_img.height)
rx, ry = 205, 195
workbench_abs_pos = (rx, ry + 30)
workbench_eff_size = (400, 180)
gun_crafter_part_poss = {"stock": (rx + w // 2 - 32, ry + h // 2 - 9),
                         "body": (rx + w // 2, ry + h // 2 - 15),
                         "scope": (rx + w // 2 + 1, ry + h // 2 - 24),
                         "barrel": (rx + w // 2 + 33, ry + h // 2 - 14),
                         "silencer": (rx + w // 2 + 50, ry + h // 2 - 14),
                         "grip": (rx + w // 2 - 6, ry + h // 2),
                         "magazine": (rx + w // 2 + 19, ry + h // 2 + 3)}
gun_crafter_part_poss = {k: (v[0] - rx, v[1] - ry) for k, v in gun_crafter_part_poss.items()}
# midblits

# F O N T S -------------------------------------------------------------------------------------------- #
# a maximum of two (normal + italic) of them is used; the other ones are experimental
def get_fonts(*p, sys=False, **kwargs):
    if not sys:
        return [pygame.font.Font(path("assets", "Fonts", *p), i) for i in range(1, 101)]
    else:
        return [pygame.font.SysFont(p[0], i, **kwargs) for i in range(1, 101)]


class DumbList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getitem__(self, item):
        return super().__getitem__(item // 3)


exo2_fonts = get_fonts("Exo2", "Exo2-Light.ttf")
iexo2_fonts = get_fonts("Exo2", "Exo2-LightItalic.ttf")
elec_fonts = get_fonts("Electrolize", "Electrolize-Regular.ttf")
awave_fonts = get_fonts("Audiowide", "Audiowide-Regular.ttf")
neuro_fonts = get_fonts("NeuropolX", "neuropol x rg.ttf")
orbit_fonts = get_fonts("Orbitron", "Orbitron-VariableFont_wght.ttf")

#dejavu_fonts = get_fonts("DejaVu", "ttf", "DejaVuSans-ExtraLight.ttf")
#cyber_fonts = get_fonts("Cyberbit", "Cyberbit.ttf")
# stixgen_fonts = get_fonts("Stixgeneral", sys=True, italic=True)
# arial_fonts = get_fonts("arial", sys=True)
# cambria_fonts = get_fonts("cambria", sys=True)
# helvue_fonts = get_fonts("helveticaneue", sys=True)
#pixel_font = Font("Fonts", "Pixel", "pixel.png")
all_fonts = {x: pygame.font.SysFont(x, 30) for x in pygame.font.get_fonts()}

# G R O U P S ------------------------------------------------------------------------------------------ #
all_blocks =                    SmartList()
all_drops =                     SmartGroup()
all_particles =                 SmartGroup()
all_other_particles =           SmartList()
all_background_sprites =        SmartList()
all_projectiles =               SmartGroup()
all_foreground_sprites =        SmartGroup()
all_home_sprites =              SmartGroup()
all_home_world_world_buttons =  SmartGroup()
all_home_world_static_buttons = SmartGroup()
all_home_settings_buttons =     SmartGroup()
all_messageboxes =              SmartGroup()
all_mobs =                      SmartGroup()
all_rests =                     SmartGroup()
all_gases =                     []

# C O N S T A N T S ------------------------------------------------------------------------------------ #
vowels = {"a", "e", "i", "o", "u"}
consonants = {"b", "c", "d", "f", "g", "h", "j", "k", "l", "m", "n", "p", "q", "r", "s", "t", "v", "w", "x", "y", "z"}
skin_to_rgb = {
               "g": (0, 150, 0), "u": (42, 157, 244), "y": (255, 255, 0),
               "r": (255, 0, 0), "b": BLACK, "w": (255, 255, 255), "p": PINK
              }
builtin_skins = {}
DPX = 810 // 2
DPY = 600 // 2
DPP = (DPX, DPY)

bar_outline_width = 80
bar_outline_height = 9
bar_width = bar_outline_width - 4

def_regen_time = millis(5)


class Game:
    def __init__(self):
        """ The game class has all types of global attributes related to the game, as well as the player and the 'w' object that represents a world & its data """
        # initialization
        self.clock = pygame.time.Clock()
        self.def_fps_cap = 120
        self.fps_cap = 120
        self.dt = None
        self.events_locked = False
        self.debug = True
        # constants
        self.fppp = 3
        self.skin_scale_mult = 5
        self.skin_fppp = 15
        self.player_model_pos = (338, 233)
        self.tool_range = 30
        self.player_commands = {"tool", "tp", "give"}
        # in-game attributes
        self.stage = "home"
        self.home_stage = None
        self.menu = False
        self.skin_menu = False
        self.first_affection = None
        self.opened_file = False
        self.last_break = ticks()
        self.last_music = None
        self.last_ambient = None
        self.first_music = False
        self.pending_entries = []
        self.show_info = False
        self.show_info_index = 0
        self.mouse_init = (0, 0)
        self.mouse_quit = (0, 0)
        self.mouse_rel_log = []
        self.mouse_log = []
        self.mouse_delta = (0, 0)
        self.selected_widget = None
        self.disabled_widgets = False
        # surfaces
        self.night_sky = pygame.Surface(win.size)
        self.menu_surf = pygame.Surface(win.size); self.menu_surf.set_alpha(100)
        self.skin_menu_surf = pygame.Surface((win.width / 11 * 9, win.height / 11 * 9)); self.skin_menu_surf.fill(LIGHT_GRAY)
        self.skin_menu_rect = self.skin_menu_surf.get_rect(center=[s / 2 for s in win.size])
        # midblits :[ RIP
        self.midblit = None
        # tool crafter
        self.tool_crafter_selector = "sword"
        self.tool_crafter_selector_rect = None
        self.mb = None
        self.sword = None
        # skin menu
        self.skin_anim_speed = 0.06
        self.skins = {  # "pos" is topleft (of the player model; not the screen) just like normal pixel systems
            "head": [
                {"name": None},
                {"name": "hat", "frames": 4, "offset": (-2, -1)},
                {"name": "headband", "frames": 8, "offset": (-3, -1)},
                {"name": "grass_hat", "frames": 6, "offset": (-2, -4)},
                {"name": "helicopter", "frames": 7, "offset": (0, -5)},
                {"name": "crown", "frames": 6, "offset": (-1, -3)}
            ],
            "face": [
                {"name": None},
                {"name": "glasses", "frames": 5, "frame_pause": 4, "offset": (0, 2)}
            ],
            "shoulder": [
                {"name": None}
            ],
            "body": [
                {"name": None},
                {"name": "detective", "frames": 6, "offset": (0, 5)}
            ]
        }
        self.skin_bts = list(self.skins.keys())
        self.skin_indexes = dict.fromkeys(self.skin_bts, 0)
        self.skin_anims = dict.fromkeys(self.skin_bts, 0)
        for bt in self.skins:
            for index, data in enumerate(self.skins[bt]):
                if data["name"] is not None:
                    self.skins[bt][index]["sprs"] = [pygame.transform.scale_by(img, self.skin_scale_mult) for img in imgload3("assets", "Images", "Player_Skins", data["name"] + ".png", frames=data["frames"], frame_pause=data.get("frame_pause", 0))]
                    del self.skins[bt][index]["name"]
                else:
                    self.skins[bt][index]["sprs"] = []
        # sword model

        """
        vertices = []
        lines = []
        with open("test.obj", "r") as f:
            for line in f.readlines():
                line = line.removesuffix("\n")
                if not line:
                    continue
                if line.startswith("#"):
                    continue
                spl = line.split(" ")
                if spl[0] == "v":
                    vertex = [float(x) for x in spl[1:]]
                    vertex[0] += 1
                    vertices.append(vertex)
                elif spl[0] == "f":
                    spl = spl[1:]
                    line = [int(x.split("/")[0]) - 1 for x in spl][:2]
                    line.insert(0, GREEN)
                    lines.append(line)
        """
        # spritesheets
        self.portal_sprs = timgload3("assets", "Images", "Spritesheets", "portal.png", frames=7)
        # rendering
        self.fake_scroll = [0, 0]
        self.scroll = [0, 0]
        self.extra_scroll = [0, 0]
        self.dialogue = False
        self.scroll_orders = []
        self.saving_structure = False
        self.structure = {}
        # screenshake
        self.last_screen_shake = ticks()
        self.screen_shake_duration = 0
        self.screen_shake_magnitude = 0
        # ...
        self.clicked_when = None
        self.typing = False
        self.worldbutton_pos_ydt = wb_icon_size[1] + 5
        self.max_worldbutton_pos = [45, 180 + 6 * self.worldbutton_pos_ydt]
        # static attributes
        self.color_codes = {"b": BLACK, "w": WHITE, "g": GREEN, "u": WATER_BLUE, "y": YELLOW}
        self.ttypes = [("Data Files", "*.dat")]
        self.itypes = [("PNG Image Files", "*.png"), ("JPG Image Files", "*.jpg")]
        self.bar_rgb = bar_rgb
        w, h = len(self.bar_rgb), 10
        self.bar_rgb_img = pygame.Surface((w, h))
        for x, rgb in enumerate(self.bar_rgb):
            self.bar_rgb_img.fill(rgb, (x, 0, 1, h))
        self.flame_rgb = lerp(RED, WATER_BLUE, 50) + lerp(WATER_BLUE, RED, 50)
        self.common_languages = {"EN", "FR", "SP"}
        self.nouns = txt2list(path("assets", "List_Files", "nouns.txt")) + [verb for verb in txt2list(path("assets", "List_Files", "verbs.txt")) if verb.endswith("ing")]
        self.verbs = [verb for verb in txt2list(path("assets", "List_Files", "verbs.txt")) if verb.endswith("e")]
        self.adjectives = txt2list(path("assets", "List_Files", "adjectives.txt"))
        self.adverbs = txt2list(path("assets", "List_Files", "adverbs.txt"))
        self.profanities = txt2list(path("assets", "List_Files", "profanities.txt"))
        self.rhyme_url = r"https://api.datamuse.com/words?rel_rhy="
        self.funny_words_url = r"http://names.drycodes.com/10?nameOptions=funnyWords"
        self.name_url = r"https://api.namefake.com"
        self.random_word_url = r"http://api.wordnik.com/v4/words.json/randomWords?hasDictionaryDef=true&minCorpusCount=0&minLength=5&maxLength=15&limit=1&api_key=a2a73e7b926c924fad7001ca3111acd55af2ffabf50eb4ae5"
        self.achievements = {}
        # dynamic surfaces
        try:
            self.home_bg_img = iimgload3("assets", "Images", "Background", "home_bg.png")
            self.home_bg_img.set_alpha(100)
        except Exception:
            self.home_bg_img = timgload3("assets", "Images", "Background", "def_home_bg.png")
        self.home_bg_size = (self.home_bg_img.width, self.home_bg_img.height)
        self.loading_world = False
        self.loading_world_perc = 0
        self.loading_world_text = None
        # dynamic other
        self.cannot_place_block = False
        self.process_messageboxworld = True
        # rendering
        self.screen_shake = 0
        self.render_offset = (0, 0)
        self.render_scale = 3
        self.terrain_mode = "chunk"
        self.last_fps = ticks()

    @staticmethod
    def stop():
        pygame.quit()
        sys.exit()

    @staticmethod
    def bglize(img):
        return pygame.transform.scale2x(img)

    @property
    def player(self):
        return self.w.player

    @property
    def mouse(self):
        return pygame.mouse.get_pos()

    @property
    def scaled_mouse(self):
        return [s / S for s in self.mouse]

    @property
    def mouses(self):
        return pygame.mouse.get_pressed()

    @property
    def keys(self):
        return pygame.key.get_pressed()

    @property
    def mod(self):
        return pygame.key.get_mods()

    @property
    def str_mod(self):
        return "_bg" if self.mod == 1 else ""

    @property
    def chest_index(self):
        return chest_indexes[tuple(p + 3 for p in self.chest_pos)]

    @property
    def cur_chest_item(self):
        return self.chest[self.chest_index]

    @cur_chest_item.setter
    def cur_chest_item(self, value):
        self.chest[self.chest_index] = value

    def skin_data(self, bt):
        return self.skins[bt][self.skin_indexes[bt]]

    def set_loading_world(self, tof):
        self.loading_world = self.events_locked = tof
        self.loading_world_perc = 0


g = Game()


# F U N C T I O N S ----------------------------------------------------------------------------------- #
def group(spr, grp):
    try:
        grp.add(spr)
    except Exception:
        grp.append(spr)
    if grp in (all_particles,):
        all_foreground_sprites.append(spr)


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


# L A M B D A S ---------------------------------------------------------------------------------------- #
pass

# img = imgload("assets", "Images", "Mobs", "hallowskull", "hallowskull.png", frames=4)[0]
# palette = imgload("assets", "Images", "Palettes", "sunset.png")
# pg_to_pil(img).show()
# colors = [palette.get_at((x, 0)) for x in range(palette.get_width())]
# # colors = [(0, 0, 128, 255), (194, 178, 128, 255), (0, 0, 0, 255), (137, 207, 240, 255)]
# for y in range(img.get_height()):
#     for x in range(img.get_width()):
#         rgba = tuple(img.get_at((x, y)))
#         rgb = rgba[:3]
#         if rgb in [(1, 0, 0), (0, 1, 0), (0, 0, 1)] and rgba[-1] == 0:
#             img.set_at((x, y), (0, 0, 0, 0))
#             continue
#         if rgba == (0, 0, 0, 0):
#             continue
#         min_ = (float("inf"), None)
#         for color in colors:
#             color = color[:3]
#             diff = color_diff_euclid(rgb, color)
#             if diff < min_[0]:
#                 min_ = (diff, color)
#         img.set_at((x, y), min_[1])
# pg_to_pil(img).show()
# raise
