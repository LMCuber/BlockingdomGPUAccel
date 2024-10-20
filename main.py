#!/usr/bin/env python3

# I M P O R T S --------------------------------------------------------------------------------------- #
import atexit
import string
import time
import pickle
import json
import threading
import asyncio
from copy import deepcopy
from colorsys import rgb_to_hls, hls_to_rgb
#
import pyengine.pgbasics
from pyengine.pgwidgets import *
#
from src.settings import *
from src.prim_data import *
from src.world_generation import *
from src.shapes.tools import *
from src.shapes import tools
from src.controller import *
from src.entities import *
from src.perlin import *



def lowercase_rename(folder):
    # renames all subforders of folder, not including folder itself
    def rename_all(root, items):
        for name in items:
            try:
                os.rename(os.path.join(root, name), os.path.join(root, name.lower()))
            except OSError:
                pass  # can't rename it, so what

    # starts from the bottom so paths further up remain valid after renaming
    for root, dirs, files in os.walk(folder, topdown=False):
        rename_all(root, dirs)
        rename_all(root, files)


class SmartTextRender:
    def __init__(self, func, font_size, pos, anchor, freq=500):
        self.func = func
        self.font_size = font_size
        self.anchor = anchor
        self.pos = pos
        self.freq = freq
        self.update()
        self.last_update = ticks()

    def update(self):
        self.text = self.func()
        self.tex = T(orbit_fonts[self.font_size].render(self.text, True, BLACK))
        self.rect = self.tex.get_rect()
        setattr(self.rect, self.anchor, self.pos)
        self.last_update = ticks()

    def __call__(self):
        if ticks() - self.last_update >= self.freq:
            self.update()
        return self.tex, self.rect


class SmartSurface(pygame.Surface):
    def __init__(self, *args, **kwargs):
        og_args = list(args)
        args = og_args[:]
        with suppress(ValueError):
            args.remove("notalpha")
        args = tuple(args)
        super().__init__(*args)

    def __repr__(self):
        return f"{type(self).__name__}(size={self.get_size()}, flags={hex(self.get_flags())})"

    def __reduce__(self):
        return (str, (self._tobytes,))

    def __deepcopy__(self, memo):
        return self._tobytes

    @property
    def _tobytes(self, mode="RGBA"):
        return pygame.image.tobytes(self, mode)

    @classmethod
    def from_surface(cls, surface):
        ret = cls(surface.get_size(), pygame.SRCALPHA)
        ret.blit(surface, (0, 0))
        return ret

    @classmethod
    def from_string(cls, string, size, format="RGBA"):
        return cls.from_surface(pygame.image.frombytes(string, size, format))

    def cblit(self, surf, pos, anchor="center"):
        rect = surf.get_rect()
        setattr(rect, anchor, pos if not isinstance(pos, pygame.Rect) else pos.topleft)
        self.blit(surf, rect)

    def to_pil(self):
        return pg_to_pil(self)


# N O R M A L  F U N C T I O N S ---------------------------------------------------------------------- #
def pitch_shift(sound):
    return sound


def player_command(command):
    abs_args = command.split()
    args = SmartList(abs_args[1:])
    try:
        if command.startswith("tp "):
            x, y = args[0], args[1]
            pos = int(x), int(y)
            g.player.rect.center = pos

        elif command.startswith("give "):
            args = SmartList(int(arg) if arg.isdigit() else arg for arg in args)
            if args[0] in g.w.blocks:
                block = args[0]
                amount = args.get(1, 1)
                g.player.new_block(block, amount)
            elif args[0] in g.w.tools:
                tool = args[0]
                g.player.new_tool(tool)
            elif args[0] == "random":
                block = random.choice(list(g.w.blocks.keys()))
                amount = args.get(1, 1)
                g.player.new_block(block, amount)
            else:
                raise Exception

        elif command.startswith("recipe "):
            if args[0] in cinfo:
                MessageboxError(win.renderer, str(cinfo[args[0]]["recipe"]), **pw.widget_kwargs)
            else:
                MessageboxError(win.renderer, "Invalid recipable block name", **pw.widget_kwargs)

        elif command.startswith("empty"):
            try:
                g.player.inventory[args[0]] = None
                g.player.inventory_amounts[args[0]] = None
            except IndexError:
                g.player.inventory[g.player.blocki] = None
                g.player.inventory_amounts[g.player.blocki] = None

        elif command.startswith("toggle "):
            mode = abs_args[1]
            if mode == "debug":
                g.debug = not g.debug

        elif command.startswith("structure"):
            g.saving_structure = not g.saving_structure
            if not g.saving_structure:
                xo, yo = list(g.structure.keys())[0]
                g.structure = {f"{x - xo},{y - yo}": v for (x, y), v in g.structure.items()}
                Entry(win.renderer, "Enter structure name:", save_structure, **pw.entry_kwargs)

        elif command:
            raise

    except Exception:
        MessageboxError(win.renderer, "Invalid or unusable command", **pw.widget_kwargs)
        # raise


def tile_to__rect(abs_pos, scale=False):
    bx, by = abs_pos
    _rect = pygame.Rect(bx * BS, by * BS, BS, BS)
    d = {True: S, False: 1}
    return pygame.Rect([r * d[scale] for r in _rect])


def tile_to_rect(abs_pos, scale=False):
    bx, by = abs_pos
    _rect = pygame.Rect(bx * BS, by * BS, BS, BS)
    rect = pygame.Rect(_rect.x - g.scroll[0], _rect.y - g.scroll[1], BS, BS)
    d = {True: S, False: 1}
    return pygame.Rect([r * d[scale] for r in rect])


def save_structure(name):
    with open(path("assets", "structures.json"), "r") as f:
        try:
            existing = json.load(f)
        except json.decoder.JSONDecodeError:
            existing = {}
    with open(path("assets", "structures.json"), "w") as f:
        existing[name] = g.structure
        json.dump(existing, f, indent=4)
    g.structure = {}


def disable_needed_widgets():
    for widget in iter_widgets():
        if widget.visible_when is None:
            if widget.disable_type != "static":
                if "static" not in widget.special_flags:
                    if not widget.rect.collidepoint(g.mouse):
                        faulty = True
                        for friend in widget.friends:
                            if not friend.disabled:
                                if friend.rect.collidepoint(g.mouse):
                                    faulty = False
                                    break
                        else:
                            faulty = True
                        if faulty:
                            if not widget.disable_type:
                                if widget.as_child:
                                    widget.as_child = False
                                else:
                                    CThread(target=widget.zoom, args=["out destroy"]).start()
                            elif not widget.disabled:
                                g.disabled_widgets = True
                                widget.disable()


def mousebuttondown_event(button):
    if button == 1:
        g.clicked_when = g.stage
        if g.stage == "play":
            """
            p = Projectile(g.player.rect.midtop, g.mouse, g.player._rect.center, speed=15, gravity=0.30, image=dart_img, track_path=False)
            p.image.color = choice((get_red, get_green, get_blue))(140, 20)
            all_projectiles.append(p)
            """

            if g.player.main == "tool":
                g.player.attack()

            if g.midblit == "tool-crafter":
                pass

        disable_needed_widgets()

        if g.stage == "home":
            if g.process_messageboxworld:
                for messagebox in all_messageboxes:
                    for name, rect in messagebox.close_rects.items():
                        if rect.collidepoint(g.mouse):
                            messagebox.close(name)
                            break
                    else:
                        if not messagebox.rect.collidepoint(g.mouse):
                            # CThread(target=messagebox.zoom, args=["out"]).start()
                            all_messageboxes.remove(messagebox)
                            break

            if g.home_stage == "worlds":
                if not all_messageboxes:
                    for button in all_home_world_world_buttons:
                        if button.rect.collidepoint(g.mouse):
                            mb = MessageboxWorld(button.world)
                            group(mb, all_messageboxes)
                            break

        if g.clicked_when == "play":
            if g.midblit is not None:
                mbr = g.midblit_rect()
                if g.midblit == "chest":
                    if not chest_rect.collidepoint(g.mouse):
                        stop_midblit()
                    else:
                        for rect in chest_rects:
                            if rect.collidepoint(g.mouse):
                                g.chest_pos = [p - 3 for p in rect.topleft]
                elif not mbr.collidepoint(g.mouse):
                    if not (g.midblit == "tool-crafter" and pw.tool_crafter_selector_range_rect.collidepoint(g.mouse)):
                        stop_midblit()

    elif button == 3:
        if g.stage == "play":
            if g.player.main == "block":
                if any(g.player.block.endswith(x) for x in {"helmet", "chestplate", "leggings"}):
                    armor = g.player.block.split("_")[-1]
                    g.player.armor[armor] = g.player.block
            elif g.player.main == "tool":
                if g.player.tool == "monocular":
                    xvel, yvel = two_pos_to_vel(g.player.rrect.center, g.mouse, 120)
                    g.extra_scroll = [xvel, yvel]

            # for entity in g.w.entities:
            #     if no_widgets(Entry):
            #         if entity.rect.collidepoint(g.mouse):
            #             if is_drawable(entity):
            #                 if "portal" in entity.traits and is_drawable(entity):
            #                     if not g.w.linked:
            #                         MessageboxOkCancel(win.renderer, "Are you sure you want to link worlds?", g.player.link_worlds, ok="Yes", no_ok="No", **pw.widget_kwargs)
            #                 elif "camel" in entity.traits:
            #                     if g.player.moving_mode[0] != "camel":
            #                         g.player.set_moving_mode("camel", entity)
            #                     else:
            #                         g.player.set_moving_mode(g.player.last_moving_mode[0])

            # right-click on block
            target_chunk, abs_pos = pos_to_tile(g.mouse)
            if abs_pos in g.w.data[target_chunk]:
                g.w.trigger(target_chunk, abs_pos, wait=1)


def mousebuttonup_event(button):
    if button == 1:
        g.disabled_widgets = False
        g.first_affection = None
        visual.mouse_init = None
        # mouse log
        if g.player.main == "tool":
            visual.process_swipe(g.mouse_rel_log)
        # rest
        g.clicked_when = None
        for block in all_blocks:
            block.broken = 0
        fps_resetted = False

        if g.stage == "play":
            # nonmenu
            if not g.menu:
                # misc
                g.player.food_pie = g.player.def_food_pie.copy()
                # tools
                if g.player.main == "tool":
                    # shoot arrow
                    if "bow" in g.player.tools:
                        arrow_index = first(g.player.inventory, lambda x: x is not None and "arrow" in x)
                        if arrow_index is not None:
                            if g.player.inventory_amounts[arrow_index] > 0:
                                arrow_name = g.player.inventory[arrow_index]
                                all_projectiles.add(Projectile(visual.rect.center, g.mouse, g.player._rect.center, 4, 0.1, g.w.blocks[arrow_name], arrow_name, traits=["dui"]))
                                g.player.use_up_inv(arrow_index)
                        visual.bow_index = 0

    elif button == 3:
        if g.stage == "play":
            g.extra_scroll = [0, 0]


def change_keybind(widget, name, value, controller=False):
    keybinds = getattr(g.p, name)
    keybinds[int(controller)] = value
    height = pw.keybind_height
    set_widget_icon(widget, keybinds, height)


def set_widget_icon(widget, texts, height=None):
    widget.icon = texts
    icon = get_keybind_icon(texts, height)
    li = widget
    li.icon_img = T(icon)
    li.icon_rect = li.icon_img.get_rect(midright=(li.rect.right - 5, li.rect.centery))


def get_keybind_icon(texts, height):
    f = orbit_fonts[18]
    icons = []
    gap = 20
    for text in texts:
        if text.startswith("#"):
            img = keybind_icons[text.removeprefix("#")]
            iw, ih = img.get_size()
            w, h = iw + 6, ih + 6
            icon = pygame.Surface((w, h), pygame.SRCALPHA)
            icon.blit(img, (w / 2 - iw / 2, h / 2 - ih / 2))
        else:
            w, h = [s + 6 for s in f.size(text)]
            icon = pygame.Surface((w, h), pygame.SRCALPHA)
            write(icon, "center", text, f, WHITE, w / 2, h / 2)
        pygame.draw.rect(icon, WHITE, (0, 0, w, h), 1, 8)
        icons.append(icon)
    fin_height = height if height is not None else max(icons, key=lambda x: x.get_height()).get_height()
    surf = pygame.Surface([sum(icon.get_width() for icon in icons) + (len(icons) - 1) * gap, fin_height], pygame.SRCALPHA)
    x = 0
    for icon in icons:
        surf.blit(icon, (x, fin_height / 2 - icon.get_height() / 2))
        x += icon.get_width()
        write(surf, "center", "/", f, WHITE, x + gap / 2, fin_height / 2)
        x += gap
    return surf


def rotate_name(name, rotations):
    spl = name.split("_deg")
    deg = int(spl.pop(-1))
    prefix = "".join(spl)
    ret = f"{prefix}_deg{rotations[deg]}"
    return ret


def get_gun_info(name, part):
    ret = ginfo[part][g.mb.gun_attrs[name][part].split("_")[0]]
    return ret


def shake_screen(shake_offset, shake_length):
    g.screen_shake_magnitude = shake_offset
    g.screen_shake_duration = shake_length
    g.last_screen_shake = ticks()


def is_audio(file_name):
    return file_name.endswith(".mp3") or file_name.endswith(".wav") or file_name.endswith(".ogg")


def get_rand_track(p):
    while True:
        track = choice(os.listdir(p))
        if is_audio(track):
            break
    else:
        raise RuntimeError(f"No audio files found in given directory: {p}")
    return path(p, track)


def next_ambient():
    pygame.mixer.music.load(get_rand_track(path("assets", "Audio", "Music", "Ambient")))
    try:
        pygame.mixer.music.play(start=rand(0, audio_length(music_path)))
    except pygame.Error:
        pygame.mixer.music.play()
    g.last_ambient = music_name


def ipure(str_):
    if non_bg(str_) in g.w.blocks:
        return bpure(str_)
    elif tpure(str_) in tinfo:
        return tpure(str_)


def show_added(item, pre="Added", post=""):
    group(SlidePopup(f"{pre} {bshow(item)} {post}"), all_particles)


def is_smither(tool):
    return tool.split("_")[1] == "hammer"


def tool_type(tool):
    return tool.split("_")[0].removesuffix("_en")


def non_bg(name):
    return name.replace("_bg", "")


def non_jt(name):
    return name.replace("_jt", "")


def is_jt(name):
    return "_jt" in name


def non_ck(name):
    return name.replace("_ck", "")


def non_wt(name):
    return non_jt(non_bg(name))


def non_en(name):
    return name.replace("_en", "")


def is_en(name):
    return "_en" in name


def is_ck(name):
    return "_ck" in name


def get_ending(name):
    ending = ""
    if is_bg(name):
        ending += "_bg"
    return ending


def toggle_main():
    if g.player.main == "block":
        g.player.main = "tool"
    elif g.player.main == "tool":
        g.player.main = "block"
    visual.bow_index = 0


def all_main_widgets():
    return all_home_sprites + all_home_world_world_buttons + all_home_world_static_buttons + all_home_settings_buttons


def is_gun(name):
    return name.removeprefix("enchanted_").split("_")[0] not in oinfo if name is not None else False


def is_gun_craftable():
    return all({k: v for k, v in g.mb.gun_parts.items() if k not in g.extra_gun_parts}.values())


def custom_gun(name):
    if name not in g.w.blocks:
        g.w.tools[name] = T(SmartSurface.from_surface(g.mb.gun_img.copy()))
        g.player.empty_tool = name
        g.mb.gun_attrs[name] = g.mb.gun_parts
        g.player.tool_ammo = get_gun_info(name, "magazine")["size"]
        g.midblit = None
    else:
        MessageboxError(win.renderer, "Name collides")


def gwfromperc(amount):
    g.loading_world_perc = amount


def update_block_states():
    for block in all_blocks:
        block.update_state()


def is_clickable(block):
    if g.stage == "freestyle":
        return True
    elif g.stage == "adventure":
        pass


def set_midblit(block):
    def midblit_rect():
        rect = pygame.Rect(block._rect.x - g.scroll[0], block._rect.y - g.scroll[1], img.width, img.height)
        if g.midblit == "tool-crafter":
            rect.x -= rect.width / 2 - BS / 2
            rect.y -= rect.height / 2 - BS / 2
        else:
            rect.x -= rect.width / 2
            rect.y -= rect.height / 2
        rect = img.get_rect(center=win.center)
        return rect

    g.mb = block
    g.midblit = non_bg(block.name)
    nbg = block.name
    if nbg == "tool-crafter":
        img = tool_crafter_img
        g.mb.sword_color = (0, 0, 0, 255)
        g.mb.sword = get_sword(g.mb.sword_color)
        g.mb.compoi = [
            get_compos("maru", unlocked=bool(rand(0, 1))),
            get_compos("kobuse", unlocked=bool(rand(0, 1))),
            get_compos("honsanmai", unlocked=bool(rand(0, 1))),
            get_compos("shihozume", unlocked=bool(rand(0, 1))),
            get_compos("makuri", unlocked=bool(rand(0, 1))),
        ]
        g.mb.last_left = ticks()
        for i in range(len(g.mb.compoi)):
            g.mb.compoi[i].target_oox = (i - (len(g.mb.compoi) - 1) / 2) * 50
        # radar
        g.mb.radar_chart = RadarChart(win.renderer, [["Da", 7], ["Du", 7], ["A", 7], ["Ma", 7], ["Mo", 7], ["B", 7]], 0, 0, 50, (200, 200, 200, 255), orbit_fonts[14])
        pw.tool_crafter_selector.enable()
    else:
        img = midblits[nbg]
    g.midblit_rect = midblit_rect


def stop_midblit(args=""):
    g.disabled_widgets = True
    g.midblit = None
    g.cannot_place_block = True
    args = args.split("/")
    if "workbench" in args or not args:
        g.mb.craftings = {}


def is_eatable(food):
    eat = False
    if food in finfo:
        for attr in finfo[food]["amounts"]:
            if g.player.stats[attr]["amount"] != 100:
                eat = True
                break
        else:
            g.player.food_pie = {}
    else:
        eat = False
    return eat


def apply(elm, seq, default):
    if is_in(elm, seq):
        return seq[ipure(elm)]
    else:
        return default


def rand_ore(default="air"):
    rate = randf(0, 100)
    for ore in reversed(oinfo):
        if ore != "stone":
            if rate < oinfo[ore]["chance"]:
                ret = ore
                break
    else:
        ret = default
    return ret


def get_tinfo(tool, name):
    amount = 0
    try:
        for block in tinfo[gtool(tool)]["blocks"]:
            if block == bpure(name):
                amount = tinfo[gtool(tool)]["blocks"][block] * 1
                raise BreakAllLoops
        raise BreakAllLoops
    except (BreakAllLoops, KeyError):
        return amount


def get_finfo(name):
    eaten = False
    for food in finfo:
        if food == bpure(name):
            eaten = finfo[food]
            return eaten
    return eaten


def chanced(name, delimeter="/"):
    return choice(name.split(delimeter))


def convert_size(size_bytes):
    if size_bytes == 0:
       return "0B"
    else:
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"


def update_button_data(button):
    name = button.data["world"]
    mb = convert_size(os.path.getsize(path(".game_data", "worlds", button.data["world"] + ".dat")))
    date = button.data["date"]
    button.overwrite(f"{name} | {mb} | {date}")


def tool_type(tool):
    return tool.split("_")[0].removeprefix("enchanted_")


def is_bg(name):
    return "_bg" in name


def utilize_blocks():
    def utilize():
        for block in g.player.reverse_blocks:
            block.utilize()
            block.broken = 0

    if pw.generation_mode.option == "Instant":
        utilize()
    elif pw.generation_mode.option == "Generative":
        Thread(target=utilize).start()


def new_world(worldcode=None):
    def init_world_data(wn):
        _glob.world_name = wn
        start_generating()

    def destroy_ewn():
        ewn.destroy()

    class Global:
        def __init__(self):
            self.world_name = None
            self.world_code = worldcode[:] if worldcode is not None else None

    _glob = Global()

    def create():
        wn = _glob.world_name
        g.set_loading_world(True)
        game_mode = "adventure"  # switching game mode
        if wn is not None:
            if wn not in g.p.world_names:
                g.w.screen = 0
                if _glob.world_code is None:
                    try:
                        open(path(".game_data", "tempfiles", wn + ".txt"), "w").close()
                        os.remove(path(".game_data", "tempfiles", wn + ".txt"))
                    except (InvalidFilenameError, FileNotFoundError):
                        MessageboxError(win.renderer, "Invalid world name", **pw.widget_kwargs)
                    else:
                        biome = choice(list(bio.blocks.keys()))
                        if not wn:
                            wn = f"New_World_{g.p.new_world_count}"
                            g.p.new_world_count += 1
                        g.w = World()
                        g.w.name = wn
                        group(WorldButton(g.w.get_partition(), c1dl(g.p.next_worldbutton_pos)), all_home_world_world_buttons)
                        g.p.next_worldbutton_pos[1] += g.worldbutton_pos_ydt
                        g.w.mode = game_mode
                        destroy_widgets()
                        g.menu = False
                        g.w.name = wn
                        g.p.world_names.append(wn)
                        # init world
                        init_world("new")
                else:
                    generate_world(_glob.world_code)
            else:
                MessageboxError(win.renderer, "A world with the same name already exists.", **pw.widget_kwargs)
                g.set_loading_world(False)
        destroy_ewn()

    _cr_world_dt = 100 / len(inspect.getsourcelines(create)[0])
    #create = scatter(create, f"g.loading_world_perc += {_cr_world_dt}", globals(), locals())

    def start_generating():
        t = Thread(target=create)
        t.daemon = True
        t.start()

    if g.p.next_worldbutton_pos[1] < g.max_worldbutton_pos[1]:
        ewn = Entry(win.renderer, "Enter world name:", init_world_data, **pw.entry_kwargs)
    else:
        MessageboxError(win.renderer, "You have too many worlds. Delete a world to create another one.", **pw.widget_kwargs)
        g.set_loading_world(False)


def settings():
    g.menu = True
    for widget in pw.death_screen_widgets:
        widget.disable()
    for widget in pw.iter_menu_widgets:
        widget.enable()
    # pg_to_pil(surf).show()
    # if Platform.os == "windows":
    #     g.home_bg_img = g.bglize(win.renderer.copy())
    # elif Platform.os == "darwin":
    #     g.home_bg_img = pygame.Surface(win.size, pygame.SRCALPHA)
    #     g.home_bg_img.blit(win.renderer.copy(), (0, 0))
    #     g.home_bg_img = pygame.transform.scale2x(g.home_bg_img)


def empty_group(group):
    for spr in group[:]:
        try:
            spr.kill()
        except AttributeError:
            group.remove(spr)


def hovering(button):
    if button.rect.collidepoint(g.mouse):
        return True


def delete_all_worlds():
    if all_home_world_world_buttons:
        def delete():
            for file_ in os.listdir(path(".game_data", "worlds")):
                os.remove(path(".game_data", "worlds", file_))
                open(path(".game_data", "variables.dat"), "w").close()
            empty_group(all_home_world_world_buttons)
            g.p.world_names.clear()
            g.w.name = None
            g.p.next_worldbutton_pos = g.p.starting_worldbutton_pos[:]
            g.p.new_world_count = 1

        MessageboxOkCancel(win.renderer, "Delete all worlds? This cannot be undone.", delete, **pw.widget_kwargs)
    else:
        MessageboxError(win.renderer, "You have no worlds to delete.", **pw.widget_kwargs)


def cr_block(name, screen=-1, index=None):
    g.w.get_data[screen].insert(index if index is not None else len(g.w.get_data[screen]), name)


def init_world(type_):
    # player inventory and stats
    if type_ == "new":
        if g.w.mode == "adventure":
            # g.player.inventory = ["tool-crafter", "prototype_grip", "prototype_magazine", "prototype_stock", "prototype_body"]
            g.player.inventory = ["tool-crafter", "ramp_deg90", "glass", "corn-crop_vr0.0", "cattail"]
            g.player.inventory_amounts = [100, 100, 100, 100, 100]
            g.player.stats = {
                "lives": {"amount": rand(10, 100), "color": RED, "pos": (32, 20), "last_regen": ticks(), "regen_time": def_regen_time, "icon": "lives", "width": 0},
                "hunger": {"amount": rand(10, 100), "color": ORANGE, "pos": (32, 40), "icon": "hunger", "width": 0},
                "thirst": {"amount": rand(10, 100), "color": WATER_BLUE, "pos": (32, 60), "icon": "thirst", "width": 0},
                "energy": {"amount": rand(10, 100), "color": YELLOW, "pos": (32, 80), "icon": "energy", "width": 0},
                "oxygen": {"amount": 100, "color": SMOKE_BLUE, "pos": (32, 100), "icon": "o2", "width": 0},
                "xp": {"amount": 100, "color": GREEN, "pos": (32, 120), "icon": "xp", "width": 0},
            }
        elif g.w.mode == "freestyle":
            g.player.inventory = ["anvil", "bush", "dynamite", "command-block", "workbench"]
            g.player.inventory_amounts = [float("inf")] * 5
    elif type_ == "existing":
        g.player.stats["lives"]["regen_time"] = def_regen_time
        g.player.stats["lives"]["last_regen"] = ticks()

    # dynamic surfaces
    g.bars_bg = pygame.Surface((200, len(g.player.stats.keys()) * (16 + 7))); g.bars_bg.fill(GRAY); g.bars_bg.set_alpha(150)
    # music
    pw.next_piece_command()
    # Go!
    g.stage = "play"
    g.set_loading_world(False)


def diffuse_light(og_block, chunk_data):
    stack = []
    visited = []
    count = 0

    def diffuse(block, again=True):
        nonlocal count
        count += 1
        visited.append(block)
        name = block.name
        pos = block.pos
        if name in ("dynamite", "air"):
            block.light = max_light
        offsets = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        # offsets = [
        #     (-1, -1), (0, -1), (1, -1),
        #     (-1,  0), (0,  0), (1,  0),
        #     (-1,  1), (0,  1), (1,  1)
        # ]
        for offset in offsets:
            stack_pos = (pos[0] + offset[0], pos[1] + offset[1])
            if stack_pos in chunk_data:
                stack_block = chunk_data[stack_pos]
                if stack_block not in visited and stack_block not in [s[0] for s in stack]:
                    stack.append([stack_block, block])
        if stack and again:
            new_block, old_block = stack.pop(0)
            # only decrease when it is dimmer
            if new_block.light < old_block.light:
                new_block.light = old_block.light - 2
                new_block.light = max(new_block.light, 0)
            if count >= 100:
                return
            diffuse(new_block)

    diffuse(og_block)


# chunk shit
class ChunkHeights(Enum):
    AIR = -1
    GROUND = 0
    TRANSITION = 1
    MINE = 2
    GROUND_MINE = 3


def generate_chunk(chunk_index, biome="forest", terrain_only=False):
    fast_terrain = None
    x = y = entities = chunk_pos = fast_terrain = chunk_data = 0

    def part1():
        nonlocal fast_terrain, x, y, entities, chunk_pos
        fast_terrain = SmartSurface((CW * BS, CH * BS), pygame.SRCALPHA)
        x, y = chunk_index
        entities = []
        chunk_pos = (x * CW, y * CH)

    def part2():
        g.w.metadata[chunk_index] = DictWithoutException({"index": chunk_index, "pos": chunk_pos, "entities": [], "underground": DictWithoutException()})

    def part3():
        nonlocal chunk_data
        if not terrain_only:
            chunk_data = {}
            for rel_x in range(CW):
                for rel_y in range(CH):
                    width, height = x * CW + rel_x, y * CH + rel_y
                    rel_pos = rel_x, rel_y
                    target_x = x * CW + rel_x
                    target_y = y * CH + rel_y
                    target_pos = (target_x, target_y)
                    blit_x, blit_y = (rel_x * BS, rel_y * BS)
                    name = "air"
                    if y < 0:
                        name = "air"
                    elif y == 0:
                        name = "soil_f"
                    else:
                        name = "stone"
                    if name:
                        chunk_data[target_pos] = Block(name, target_pos, 1)
                        fast_terrain.blit(g.w.bimg(name, tex=False), (blit_x, blit_y))
                        # g.w.modify(name, custom_target=chunk_data, abs_pos=target_pos, custom_terrain=fast_terrain, overwrites_all=True)

    def part4():
        nonlocal chunk_data, fast_terrain
        g.w.data[chunk_index] = chunk_data
        # terrain, _ = generate_lighting(chunk_data, chunk_index, new_lighting=True, blit_image=True)
        # fast_terrain.blit(terrain, (0, 0))
        fast_terrain = T(fast_terrain)
        g.w.terrains[chunk_index] = fast_terrain
        g.w.entities[chunk_index] = entities
        return fast_terrain

    part1()
    part2()
    part3()
    part4()

    return fast_terrain


def generate_chunk(chunk_index, biome="forest", terrain_only=False):
    # fast as fuck boi
    fast_terrain = SmartSurface((CW * BS, CH * BS), pygame.SRCALPHA)
    # init NOW
    x, y = chunk_index
    entities = []
    chunk_pos = (x * CW, y * CH)
    # metadata
    g.w.metadata[chunk_index] = DictWithoutException({"index": chunk_index, "pos": chunk_pos, "entities": [], "underground": DictWithoutException()})
    if chunk_index[0] not in g.w.metadata:
        g.w.metadata[chunk_index[0]] = {"overflowing_mine": chance(1 / 10)}
    overflowing_mine = g.w.metadata[chunk_index[0]]["overflowing_mine"]
    # init varsiables
    biome = biome if biome is not None else choice(list(bio.blocks.keys()))
    if not terrain_only:
        chunk_data = {}
        # per chunk
        if y == 0:
            length = CW
            flatness = bio.flatnesses.get(biome, 0)
            if y in g.w.last_heights:
                height = g.w.last_heights[y]
            else:
                height = bio.heights.get(biome, 4)
            lnoise = g.w.linoise.linear(height, length, flatness, start=height)
            lnoise = [max(1, n) for n in lnoise]
            g.w.last_heights[y] = lnoise[-1]
        prim, sec = bio.blocks[biome]
        tert = "stone"
        # - generation -
        depth = ore_chance = 0
        for rel_x in range(CW):
            noise_input = x * CW + rel_x
            y_offset = int(osimplex.noise2(x=(x * CW + rel_x) * 0.08, y=0) * 8)
            if y == 1:
                layers = bio.get_transition(biome)
            for rel_y in range(CH):
                width, height = x * CW + rel_x, y * CH + rel_y
                rel_pos = rel_x, rel_y
                target_x = x * CW + rel_x
                target_y = y * CH + rel_y
                target_pos = (target_x, target_y)
                name = "air"
                # check which chunk levels we got
                if overflowing_mine:
                    # mine is overflowing, so (ground) mine up to surface level
                    if y < 0:  # air
                        chunk_height = ChunkHeights.AIR
                    elif y == 0:
                        chunk_height = ChunkHeights.GROUND_MINE
                    elif y > 0:
                        chunk_height = ChunkHeights.MINE
                else:
                    if y >= 0:
                        # the height is below air (not super~air or air)
                        chunk_height = {
                            0: ChunkHeights.GROUND,
                            1: ChunkHeights.TRANSITION,
                            2: ChunkHeights.MINE
                        }.get(y, ChunkHeights.MINE)
                    else:
                        chunk_height = ChunkHeights.AIR
                # init vars
                if chunk_height in (ChunkHeights.MINE, ChunkHeights.GROUND_MINE):
                    mine_name = "stone_bg" if osimplex.noise2(x=width * 0.12, y=height * 0.1) < 0 else "stone"
                # rest
                if chunk_height == ChunkHeights.AIR:
                    name = "air"
                elif chunk_height == ChunkHeights.GROUND:
                    if rel_y == 8 + y_offset:
                        name = prim
                    elif rel_y > 8 + y_offset:
                        name = sec
                    else:
                        name = "air"
                elif chunk_height == ChunkHeights.GROUND_MINE:
                    if rel_y >= 8 + y_offset:
                        name = mine_name
                    else:
                        name = "air"
                elif chunk_height == ChunkHeights.TRANSITION:
                    name = "air"
                    for interval, layer_block in layers.items():
                        if interval[0] <= rel_y <= interval[1]:
                            name = layer_block
                elif chunk_height == ChunkHeights.MINE:
                    name = mine_name
                if name:
                    g.w.modify(name, custom_target=chunk_data, abs_pos=target_pos, custom_terrain=fast_terrain, overwrites_all=True)
                # set underground background blocks so it's not just air
                if y >= 0 and name != "air":
                    # set default block when it gets mined
                    if bpure(name) == "soil":
                        u_name = name.replace("soil", "dirt")
                    elif non_bg(name) == "stone":
                        u_name = "stone"
                    else:
                        # stone and stuff
                        u_name = name
                    g.w.metadata[chunk_index]["underground"][target_pos] = f"{u_name}_bg"
        # world mods
        entities, late_chunk_data = world_modifications(chunk_data, g.w.metadata[chunk_index], biome, chunk_pos, g.w.rng)
        # entities, late_chunk_data = [], {}
        # pprint(late_chunk_data)
        g.w.late_chunk_data |= late_chunk_data
    else:
        chunk_data = g.w.data[chunk_index]
    #
    # terrain
    g.w.data[chunk_index] = chunk_data
    terrain, lighting = generate_lighting(chunk_data, chunk_index, new_lighting=True, blit_image=True)
    fast_terrain.blit(terrain, (0, 0))
    fast_terrain = T(fast_terrain)
    g.w.terrains[chunk_index] = fast_terrain
    g.w.entities[chunk_index] = entities
    test("generated")
    return fast_terrain


def generate_lighting(chunk_data, chunk_index, new_lighting=False, blit_image=False):
    chunk_pos = (chunk_index[0] * CW, chunk_index[1] * CH)
    metadata = DictWithoutException({"index": chunk_index, "pos": chunk_pos, "entities": []})
    if blit_image:
        terrain = SmartSurface((CW * BS, CH * BS), pygame.SRCALPHA)
        if chunk_index[1] >= 1:
            pass
            # terrain.blit(pygame.transform.scale(g.w.surf_assets["blocks"]["wallstone"], (CW * BS, CH * BS)), (0, 0))
    if new_lighting:
        lighting = SmartSurface((CW, CH), pygame.SRCALPHA)
    else:
        lighting = g.w.lighting_surfs[chunk_index]
    g.w.lighting_surfs[chunk_index] = lighting
    tex_lighting = T(lighting)
    g.w.lightings[chunk_index] = tex_lighting
    # lighting.fill(BLACK)
    enum = {"left": [], "right": [], "up": [], "down": []}
    for rel_y in range(CH):
        for rel_x in range(CW):
            abs_pos = (chunk_pos[0] + rel_x, chunk_pos[1] + rel_y)
            if abs_pos in chunk_data:
                # blit actual block image onto global chunk surface
                block = chunk_data[abs_pos]
                name = block.name
                blit_x, blit_y = (rel_x * BS, rel_y * BS)
                if blit_image:
                    if name != "air":
                        terrain.blit(g.w.bimg(name, tex=False), (blit_x, blit_y))
    color = (255, 0, 0, 200)
    # lighting = pygame.transform.box_blur(lighting, linfo["torch"]["radius"])
    #
    g.w.metadata[chunk_index] |= metadata
    #
    if blit_image:
        # tex_terrain = T(terrain)
        # g.w.terrains[chunk_index] = terrain
        return terrain, tex_lighting
    return tex_lighting


def update_light():
    global thread_active, light_surf, light_tex, light_rect
    thread_active = True
    light_min_x = DumbNumber()
    light_max_x = DumbNumber()
    light_min_y = DumbNumber()
    light_max_y = DumbNumber()
    #
    for y in range(V_CHUNKS):
        for x in range(H_CHUNKS):
            # init chunk data like pos and other metadata
            target_x = x - 1 + int(round(g.scroll[0] / (CW * BS)))
            target_y = y - 1 + int(round(g.scroll[1] / (CH * BS)))
            target_chunk = (target_x, target_y)
            if target_chunk not in g.w.data or target_chunk != (0, 0):
                continue
            for index, (abs_pos, block) in enumerate(g.w.data[target_chunk].copy().items()):
                block.light = max(block.light, block.light - 16)
    for y in range(V_CHUNKS):
        for x in range(H_CHUNKS):
            # init chunk data like pos and other metadata
            target_x = x - 1 + int(round(g.scroll[0] / (CW * BS)))
            target_y = y - 1 + int(round(g.scroll[1] / (CH * BS)))
            target_chunk = (target_x, target_y)
            if target_chunk not in g.w.data or target_chunk != (0, 0):
                continue
            for index, (abs_pos, block) in enumerate(g.w.data[target_chunk].copy().items()):
                if abs_pos[0] < light_min_x:
                    light_min_x = abs_pos[0]
                if abs_pos[0] > light_max_x:
                    light_max_x = abs_pos[0]
                if abs_pos[1] < light_min_y:
                    light_min_y = abs_pos[1]
                if abs_pos[1] > light_max_y:
                    light_max_y = abs_pos[1]
                block.light = 0
                # if block.name == "air":
                #     fill_light(target_chunk, abs_pos, 255)
    surf_width = light_max_x - light_min_x
    surf_height = light_max_y - light_min_y
    light_surf = pygame.Surface((surf_width * BS, surf_height * BS), pygame.SRCALPHA)
    # ------------
    for y in range(V_CHUNKS):
        for x in range(H_CHUNKS):
            # init chunk data like pos and other metadata
            target_x = x - 1 + int(round(g.scroll[0] / (CW * BS)))
            target_y = y - 1 + int(round(g.scroll[1] / (CH * BS)))
            target_chunk = (target_x, target_y)
            if target_chunk not in g.w.data:
                continue
            if target_chunk == (0, 0):
                for index, (abs_pos, block) in enumerate(g.w.data[target_chunk].copy().items()):
                    rel_x, rel_y = abs_pos[0] % CW, abs_pos[1] % CH
                    # light_surf.set_at((rel_x, rel_y), (0, 0, 0, 255 - block.light))
                    pygame.draw.rect(light_surf, (0, 0, 0, 255 - block.light), (rel_x * BS, rel_y * BS, BS, BS))
                    write(light_surf, "center", block.light, awave_fonts[10], GREEN, rel_x * BS + BS / 2, rel_y * BS + BS / 2)
    light_tex = T(light_surf)
    light_rect = pygame.Rect((0, 0, surf_width * BS, surf_height * BS))
    thread_active = False


def fill_light(target_chunk, abs_pos, light_value):
    light_reduction = 25
    new_light_value = max(0, light_value - light_reduction)
    if target_chunk not in g.w.data:
        return
    if new_light_value > g.w.data[target_chunk][abs_pos].light:
        g.w.data[target_chunk][abs_pos].light = int(new_light_value)
        # rel_x, rel_y = abs_pos[0] % CW, abs_pos[1] % CH
        fill_light(*correct_tile(target_chunk, abs_pos, -1, 0), new_light_value)
        fill_light(*correct_tile(target_chunk, abs_pos, 1, 0), new_light_value)
        fill_light(*correct_tile(target_chunk, abs_pos, 0, -1), new_light_value)
        fill_light(*correct_tile(target_chunk, abs_pos, 0, 1), new_light_value)
    else:
        return


# S T A T I C  O B J E C T  F U N C T I O N S  -------------------------------------------------------  #
def is_drawable(obj):
    try:
        return g.w.screen == obj.screen and g.w.layer == obj.layer and g.w.dimension == getattr(obj, "dimension", "data")
    except AttributeError:
        if not hasattr(obj, "visible_when") or obj.visible_when is None or (callable(obj.visible_when) and obj.visible_when()):
            return True
        else:
            return False


def is_home():
    return g.stage == "home"


def is_home_settings():
    return is_home() and g.home_stage == "settings"


def is_home_worlds():
    return is_home() and g.home_stage == "worlds"


# N O N - G R A P H I C A L  C L A S S E S ------------------------------------------------------------ #
class ExitHandler:
    must_save = False
    @classmethod
    def save(cls, stage):
        # disable unnecessarry widgets
        for widget in pw.death_screen_widgets:
            widget.disable()
        # change bg of the worldbutton
        for wb in all_home_world_world_buttons:
            if wb.world_name == g.w.name:
                wb.bg = T(win.renderer.to_surface())
                wb.bg_rect = wb.bg.get_rect()
        # save world metadata
        g.w.last_epoch = epoch()
        # save world data if it hasn't been saved yet
        if g.w.name is not None:
            with open(path(".game_data", "worlds", f"{g.w.name}.dat"), "wb") as f:
                pickle.dump(g.w, f)
        with open(path(".game_data", "variables.dat"), "wb") as f:
            pickle.dump(g.p, f)
        # generating world icon
        # img = pygame.Surface((),)
        """
        icon = pygame.Surface(wb_icon_size, pygame.SRCALPHA)
        br = 3
        (icon, (95, 95, 95), (0, 0, wb_icon_size[0], wb_icon_size[1] - 30), 0, 0, br, br, -1, -1)
        y = tlo = 9
        o = 4
        yy = 0
        br = 3
        biomes_img = pygame.Surface(wb_icon_size)
        for x, (biome, freq) in enumerate(g.w.biome_freq.items()):
            if x == 3:
                break
            block_img = g.w.blocks[bio.blocks[biome][0]]
            x = x * (BS + 12) + tlo
            icon.blit(block_img, (x, y))
            (icon, YELLOW, (x - o, y - o, BS + o * 2, BS + o * 2), 1, br, br, br, br)
            write(icon, "midtop", f"{freq}%", orbit_fonts[12], BLACK, x + 14, y + 33)
        pygame.gfxdraw.hline(icon, 0, wb_icon_size[0], wb_icon_size[1] - 30, BLACK)
        block_img = g.w.blocks["soil_f"].copy()
        icon.blit(block_img, (tlo, tlo))
        (icon, WHITE, (tlo - o, tlo - o, BS + o * 2, BS + o * 2), 1, 0, br, br, br, br)

        icon.blit(g.player.image, (tlo, tlo))
        """
        # save button data

        # cleanup attributes
        g.w.name = None
        """
        g.mb.craftings = {}
        g.mb.burnings = {}
        g.mb.furnace_log = []
        g.mb.fuels = {}
        g.mb.smithings = {}
        g.mb.smither = None
        g.mb.anvil_log = []
        g.mb.crafting_log = []
        g.mb.gun_parts = {k: None for k in g.mb.gun_parts}
        g.mb.gun_log = []
        """
        # final
        if stage == "quit":
            g.stop()
        elif stage == "home":
            g.w.entities.clear()
            for fgs in all_foreground_sprites:
                if isinstance(fgs, InfoBox):
                    all_foreground_sprites.remove(fgs)
        cls.must_save = False


class WorldPartition:
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)


class World:
    def __init__(self):
        # world-generation / world data related data
        self.player = Player()
        self.data = {}
        self.terrains = {}
        self.lightings = {}
        self.lighting_surfs = {}
        self.magic_data = {}
        self.metadata = {}
        self.block_data = {}
        self.block_rects = {}
        self.to_update = {}
        self.to_break = []
        self.dimension = "data"
        self.entities = {}
        self.late_chunk_data = {}
        self.mode = None
        self.layer = 1
        self.biomes = []
        self.biome = choice(list(bio.blocks.keys()))
        self.name = None
        self.linked = False
        self.boss_scene = False
        self.rng = Random(112)
        self.linoise = Noise()
        # self.noise = PerlinNoise()
        self.last_chunks = []
        # game settings
        self.player_model_color = GRAY
        # day-night cycle
        self.hound_round = False
        self.hound_round_chance = 20
        self.def_dnc_colors = [SKY_BLUE] * 180 + lerp(SKY_BLUE, DARK_BLUE, 180) + lerp(DARK_BLUE, BLACK, 180) + [BLACK] * 180
        self.hr_dnc_colors = [SKY_BLUE for _ in range(360)] + lerp(SKY_BLUE, ORANGE, 180) + lerp(ORANGE, BLACK, 180)
        self.set_dnc_colors()
        self.dnc_direc = op.add
        self.dnc_index = 0
        self.dnc_minutes = 5
        self.dnc_vel = self.dnc_minute_vel / 20
        self.dnc_hours = list(range(12, 24)) + list(range(0, 12))
        self.dnc_darkness = 1
        self.wind = [-0.01, 0.002]
        self.last_heights = {}
        self.chunk_colors = {}
        #  # saved assets
        self.use_default_assets()
        # self.surf_assets = {"blocks": {}, "tools": {}, "icons": {}}
        # self.asset_sizes = a.sizes
        # for atype, dict_ in a.surf_assets.items():
        #     if isinstance(dict_, dict):
        #         for name, img in dict_.items():
        #             if isinstance(img, pygame.Surface):
        #                 self.tex_assets[atype][name] = SmartSurface.from_surface(img)
        #     elif isinstance(dict_, list):
        #         setattr(self, atype, [SmartSurface.from_surface(x) for x in dict_])
        """
        for d in self.surf_assets:
            for k, v in self.tex_assets[d].items():
                pygame.image.save(v, path(".game_data", "texture_packs", ".default", d, k + ".png"))
        """
        self.last_epoch = epoch()
        # other variables
        pass

    def get_partition(self):
        return WorldPartition(name=self.name)

    def __getstate__(self):
        # making sure no Surfaces or Textures get pickled
        del self.tex_assets
        del self.surf_assets
        # self.terrains = {k: pygame.image.tobytes(v.to_surface(), "RGBA") for k, v in self.terrains.items()}
        # self.lightings = {k: pygame.image.tobytes(v.to_surface(), "RGBA") for k, v in self.lightings.items()}
        self.terrains = {}
        self.lightings = {}
        return self.__dict__

    def __setstate__(self, data):
        self.__dict__.update(data)
        self.use_default_assets()

    def use_default_assets(self):
        self.tex_assets = a.tex_assets
        self.surf_assets = a.surf_assets

    @property
    def blocks(self):
        return self.tex_assets["blocks"]

    @property
    def tools(self):
        return self.tex_assets["tools"]

    @property
    def icons(self):
        return self.tex_assets["icons"]

    @property
    def text_color(self):
        return contrast_color(g.w.dnc_color)

    @property
    def dnc_color(self):
        return self.dnc_colors[int(self.dnc_index)]

    @property
    def dnc_length(self):
        for dnct in ("", "def", "hr"):
            with suppress(AttributeError):
                return len(getattr(self, dnct + "_dnc_colors"))

    @property
    def dnc_second_vel(self):
        return self.dnc_length * 2 / g.fps_cap

    @property
    def dnc_minute_vel(self):
        return self.dnc_second_vel / 60

    def set_dnc_colors(self):
        if random.randint(1, self.hound_round_chance) == 1:
            self.dnc_colors = self.hr_dnc_colors.copy()
        else:
            self.dnc_colors = self.def_dnc_colors.copy()

    @property
    def abs_blocki(self):
        return self.layer * L

    @property
    def get_data(self):
        return getattr(self, self.dimension if self.dimension == "data" else self.dimension + "_data")

    @property
    def sky_color(self):
        if self.boss_scene:
            return BLACK
        if self.dimension == "data":
            if self.layer < 2:
                return self.dnc_color
            else:
                return ALMOST_BLACK
        elif self.dimension == "magic":
            return DARK_PURPLE

    @property
    def biome_freq(self):
        check_biomes = set(g.w.biomes)
        write_biomes = []
        for biome in check_biomes:
            bme = biome
            prc = int(g.w.biomes.count(biome) / len(g.w.biomes) * 100)
            write_biomes.append((bme, prc))
        bfreq = {k: v for (k, v) in write_biomes}
        bfreq = dict(sorted(bfreq.items(), key=lambda x: x[1], reverse=True))
        return bfreq

    def bimg(self, name, tex=True):
        if tex:
            img = self.blocks[name]
        else:
            img = self.surf_assets["blocks"][name]
        if name == "water":
            img = pygame.Surface((BS, BS), pygame.SRCALPHA)
            img.fill(list(WATER_BLUE[:2]) + [127])
        return img

    def modify(self, setto, target_chunk=None, abs_pos=None, custom_target=None, custom_terrain=None, update=True, righted=False, overwrites=None, overwrites_empty=True, overwrites_all=False, remove_from_updating=False, update_image=True, **kwargs):
        # setupping texture coordinate variables
        if custom_target is None:
            custom_target = self.data[target_chunk]
            custom_terrain = self.terrains[target_chunk]
        nbg = non_bg(setto)
        block = custom_target.get(abs_pos, void_block)
        current = non_bg(block.name)
        blit_x, blit_y = abs_pos[0] % CW * BS, abs_pos[1] % CH * BS
        # remove from updating if setto doesn't need to be updated anymore
        if remove_from_updating:
            if abs_pos in custom_target:
                self.to_update[target_chunk].remove(custom_target[abs_pos])
        # check what it can overwrite
        if overwrites is None:
            overwrites = empty_blocks
        if overwrites_empty:
            overwrites |= empty_blocks
        # bravo six going dark
        # past leo what the fuck does this comment mean are yue retarded or sum
        if setto in empty_blocks or overwrites_all or current in overwrites:
            u_good = True
            if setto in empty_blocks:
                if abs_pos in custom_target:
                    del custom_target[abs_pos]
                if block.in_updating:
                    block.in_updating = False
                    g.w.to_update[target_chunk].remove(block)
            else:
                if update:
                    if nbg in big_blocks:
                        offset = orientation_blocks[nbg]
                        ori_name = orientation_map[offset]
                        if nbg == "cattail":
                            kw = {}
                        else:
                            kw = {}
                        right_chunk, right_pos = correct_tile(target_chunk, abs_pos, *offset)
                        if g.w.data[right_chunk].get(right_pos, void_block).name not in empty_blocks:
                            left_chunk, left_pos = correct_tile(target_chunk, abs_pos, *[-o for o in offset])
                            if g.w.data[left_chunk].get(left_pos, void_block).name not in empty_blocks:
                                u_good = False
                            else:
                                g.w.modify(f"{setto}-{ori_name}", target_chunk, abs_pos)
                                target_chunk, abs_pos = left_chunk, left_pos
                                blit_x -= 30
                        else:
                            g.w.modify(f"{setto}-{ori_name}", right_chunk, right_pos)
            if u_good:
                # update the dictionary
                if setto not in empty_blocks:
                    custom_target[abs_pos] = Block(setto, abs_pos)
                # update the image
                if update_image:
                    if setto not in invisible_blocks:
                        if isinstance(custom_terrain, SmartSurface):
                            custom_terrain.blit(self.bimg(setto, tex=False), (blit_x, blit_y))
                        else:
                            custom_terrain.update(self.bimg(setto, tex=False), (blit_x, blit_y, BS, BS))
                # set correct sine for cattail
                if nbg in plants:
                    cur = g.w.data[target_chunk][abs_pos]
                    ctt = g.w.data[right_chunk][right_pos]
                    # ctt.sin = cur.sin
                    # ctt.plant_pos = (0, ctt.plant_pos[1] + BS)
                    # ctt.plant_offset = Vector2(0, ctt.plant_offset.y - BS)
        # update the world itself (basically cellular automata eugh eugh eugh I sound so smart rigt now)
        if update:
            # § PLACE §
            # bed (king size)
            # § BREAK §
            if nbg == "air":
                if any(x in current for x in big_blocks):
                    g.w.modify("air", *correct_tile(target_chunk, abs_pos, *orientation_blocks[current]), update=False)
            # cables
            hash_table = {  # TODO: rewrite as wave function collapse later : lol nah
                # up and down
                "cable_vrF_deg0": dict.fromkeys([
                    (0, -1), (0, 1)
                ],
                    dict.fromkeys([
                            "cable_vrF_deg0", "cable_vrF_deg90"
                        ],
                        {"current": "cable_vrF_deg90",
                         "new": "cable_vrF_deg90",
                    }),
                ),
            }
            for current_cable in hash_table:
                if nbg == current_cable:
                    for offset in hash_table[current_cable]:
                        for potential_neighbor in hash_table[current_cable][offset]:
                            new_chunk, new_pos = correct_tile(target_chunk, abs_pos, *offset)
                            if new_pos in g.w.data[new_chunk]:
                                if g.w.data[new_chunk][new_pos].name == potential_neighbor:
                                    current = hash_table[current_cable][offset][potential_neighbor]["current"]
                                    new = hash_table[current_cable][offset][potential_neighbor]["new"]
                                    g.w.modify(current, target_chunk, abs_pos)
                                    g.w.modify(new, new_chunk, new_pos)
            if nbg == "dynamite":
                diffuse_light(custom_target[abs_pos], g.w.data[target_chunk])
        if setto in updating_blocks:
            if target_chunk not in g.w.to_update:
                self.to_update[target_chunk] = []
            custom_target[abs_pos].in_updating = True
            self.to_update[target_chunk].append(custom_target[abs_pos])
        # block updatings
        if setto not in empty_blocks:
            block = custom_target[abs_pos]
            if setto in flinfo:
                block.ypos = 0
                block.yvel = 0
                block.yacc = flinfo[setto]["yacc"]
                block.last_fall = ticks()
        # structure
        if righted:
            g.w.data[target_chunk][abs_pos].righted = True
        if g.saving_structure:
            if nbg in empty_blocks:
                if abs_pos in g.structure:
                    del g.structure[abs_pos]
            else:
                g.structure[abs_pos] = nbg

        # update the lighting if necessary
        if nbg in linfo or current in linfo or nbg == "dynamite":
            # lighting
            self.lightings[target_chunk] = generate_lighting(custom_target, target_chunk, new_lighting=False)
        # kwargs
        for k, v in kwargs.items():
            setattr(custom_target[abs_pos], k, v)

    def trigger(self, target_chunk, abs_pos, wait=0):
        block = g.w.data[target_chunk][abs_pos]
        name = block.name
        nbg = non_bg(name)
        # exploding the dynamite
        if nbg == "dynamite":
            def explode():
                g.w.modify("air", target_chunk, abs_pos)
                r = lambda: rand(7, 7)
                for yo in range(-r(), r()):
                    for xo in range(-r(), r()):
                        if not (xo == yo == 0):
                            new_chunk, new_pos = correct_tile(target_chunk, abs_pos, xo, yo)
                            if new_pos in g.w.data[new_chunk] and non_bg(g.w.data[new_chunk][new_pos].name) == "dynamite":
                                trigger_block(new_chunk, new_pos, wait=0)
                            else:
                                g.w.modify("air", new_chunk, new_pos)
            delay(explode, wait)
        # workbench
        elif nbg in midblits:
            if g.midblit == nbg:
                stop_midblit()
            else:
                set_midblit(block)


class Play:
    def __init__(self):
        self.world_names = []
        self.next_worldbutton_pos = [45, 100]
        self.starting_worldbutton_pos = c1dl(self.next_worldbutton_pos)
        self.new_world_count = 0
        self.loaded_world_count = 0
        self.loading_times = SmartList()
        self.anim_fps = 0.0583
        self.volume = 0.2
        self.gpu_accel = True
        self.keybinds = {
            "Character Attacks": {
                "primary_main": ["#lmouse", "R2"],
                "primary_side": ["E", "R1"],
                "secondary_main": ["#rmouse", "L2"],
                "secondary_side": ["shift", "L1"],
            },
        }
        self.default_keybinds = {keybind_type: {name: [item for item in value] for name, value in data.items()} for keybind_type, data in self.keybinds.items()}
        for keybind_type in self.keybinds:
            for name in self.keybinds[keybind_type]:
                setattr(self, name, self.keybinds[keybind_type][name])
                setattr(self, f"default_{name}", self.default_keybinds[keybind_type][name])


# create game data if it doesn't exist
if not os.path.exists(".game_data"):
    os.makedirs(path(".game_data", "worlds"))
    os.makedirs(path(".game_data", "tempfiles"))
    open(path(".game_data", "variables.dat"), "w").close()

# load variables
if os.path.getsize(path(".game_data", "variables.dat")) > 0:
    with open(path(".game_data", "variables.dat"), "rb") as f:
        g.p = pickle.load(f)
else:
    g.p = Play()

# images
if not g.p.gpu_accel:
    from src.sw_accel import *


class PlayWidgets:
    def __init__(self):
        # menu widgets
        set_default_fonts(orbit_fonts)
        set_default_tooltip_fonts(orbit_fonts)
        #
        _menu_widget_kwargs = {"anchor": "center", "width": 130, "template": "menu widget", "font": orbit_fonts[15], "bg_color": (40, 40, 40, 210), "text_color": WHITE}
        _menu_button_kwargs = _menu_widget_kwargs | {"height": 32}
        _menu_togglebutton_kwargs = _menu_button_kwargs
        _menu_checkbox_kwargs = _menu_widget_kwargs | {"width": 165, "height": 32}
        _menu_slider_kwargs = _menu_widget_kwargs | {"width": 235, "height": 60, "slider_color": WHITE}
        #
        self.widget_kwargs = {"pos": DPP, "font": orbit_fonts[20]}
        self.ok_kwargs = self.widget_kwargs | {"width": 200, "height": 60}
        self.entry_kwargs  = {"pos": (DPX, DPY - 50), "font": orbit_fonts[20], "key_font": orbit_fonts[15]}
        self.menu_widgets = {
            "buttons": SmartList([
                Button(win.renderer,   "Next Piece",    self.next_piece_command,      tooltip="Plays a different random theme piece",             **_menu_button_kwargs),
                Button(win.renderer,   "Config",        self.show_config_command,     tooltip="Configure advanced game parameters",               **_menu_button_kwargs),
                Button(win.renderer,   "Flag",          self.flag_command,            tooltip="Whenever teleported, spawn at current position",   **_menu_button_kwargs),
                Button(win.renderer,   "Textures",      self.texture_pack_command,    tooltip="Initialize a texture pack for this world",         **_menu_button_kwargs),
                Button(win.renderer,   "Keybinds",      self.change_keybinds_command, tooltip="Lets you assign different keys to actions",        **_menu_button_kwargs),
                Button(win.renderer,   "Save and Quit", self.save_and_quit_command,   tooltip="Save and quit world",                              **_menu_button_kwargs),
            ]),
            "togglebuttons": SmartList([
                ToggleButton(win.renderer, ("Instant", "Generative"), tooltip="Toggles the visual generation of chunks", **_menu_togglebutton_kwargs),
            ]),
            "checkboxes": SmartList([
                Checkbox(win.renderer, "Stats",         self.show_stats_command,       checked=True, exit_command=self.checkb_sf_exit_command, tooltip="Shows the player's stats", **_menu_checkbox_kwargs),
                Checkbox(win.renderer, "FPS",                                          tooltip="Shows the amount of frames per second",                          **_menu_checkbox_kwargs),
                Checkbox(win.renderer, "Player Hitboxes",                              tooltip="Shows the player hitboxes",                                      **_menu_checkbox_kwargs, checked=True),
                Checkbox(win.renderer, "Hitboxes",                                     tooltip="Shows hitboxes",                                                 **_menu_checkbox_kwargs),
                Checkbox(win.renderer, "Chunk Borders",                                tooltip="Shows the chunk borders and their in-game ID's",                 **_menu_checkbox_kwargs),
                Checkbox(win.renderer, "Screenshake",                                  tooltip="Screenshake can be disruptive for photosensitive players",       **_menu_checkbox_kwargs, checked=False),
                Checkbox(win.renderer, "Entities",                                     toolptip="Updates the enemies",                                           **_menu_checkbox_kwargs, checked=False)
            ]),
            "sliders": SmartList([
                Slider(win.renderer,   "Resolution",    [", ".join([str(x) for x in r]) for r in resolutions], 0, tooltip="Set the resolution of the game in pixels",                          **_menu_slider_kwargs),
                Slider(win.renderer,   "FPS Cap",       (1, 10, 30, 60, 90, 120, 144, 165, 180, 200, 240, 360), g.def_fps_cap,  tooltip="The framerate cap",                                                 **_menu_slider_kwargs),
                Slider(win.renderer,   "Animation",     range(21),  int(g.p.anim_fps * g.fps_cap),                     tooltip="Animation speed of graphics",                                       **_menu_slider_kwargs),
                Slider(win.renderer,   "Camera Lag",    range(1, 51), 1,                                               tooltip="The lag of the camera that fixated on the player",                  **_menu_slider_kwargs),
                Slider(win.renderer,   "Volume",        range(101), int(g.p.volume * 100),                             tooltip="Master volume",                                                     **_menu_slider_kwargs),
                Slider(win.renderer,   "Entities",      (0, 1, 10, 100), 100,                                          tooltip="Maximum number of entities updateable",                             **_menu_slider_kwargs),
                Slider(win.renderer,   "Lighting",      range(0, 256), 0, on_move_command=self.lighting_command,       tooltip="Experimental lighting",                                             **_menu_slider_kwargs),
            ]),
        }
        _sy = _y = 190
        _x = 200
        for mw_type in self.menu_widgets:
            for mw in self.menu_widgets[mw_type]:
                mw.set_pos((_x, _y), "topleft")
                _y += mw.height + 1
            _x += mw.width + 15
            _y = _sy
        _death_screen_widget_kwargs = {"anchor": "center", "disabled": True, "disable_type": "static", "font": orbit_fonts[15]}
        self.death_screen_widgets = SmartList([
            Label(win.renderer, "Death", (DPX, DPY - 64), **_death_screen_widget_kwargs),
            Button(win.renderer, "Play Again", command=self.quit_death_screen_command, pos=(DPX, DPY), **_death_screen_widget_kwargs)
        ])
        self.death_cause =               self.death_screen_widgets         .find(lambda x: x.text == "Death")
        self.keybinds =                  self.menu_widgets["buttons"]      .find(lambda x: x.text == "Keybinds")
        self.fps_cap =                   self.menu_widgets["sliders"]      .find(lambda x: x.text == "FPS Cap")
        self.show_fps =                  self.menu_widgets["checkboxes"]   .find(lambda x: x.text == "FPS")
        self.show_stats =                self.menu_widgets["checkboxes"]   .find(lambda x: x.text == "Stats")
        self.show_player_hitboxes =      self.menu_widgets["checkboxes"]   .find(lambda x: x.text == "Player Hitboxes")
        self.show_hitboxes =             self.menu_widgets["checkboxes"]   .find(lambda x: x.text == "Hitboxes")
        self.show_chunk_borders =        self.menu_widgets["checkboxes"]   .find(lambda x: x.text == "Chunk Borders")
        self.screenshake =               self.menu_widgets["checkboxes"]   .find(lambda x: x.text == "Screenshake")
        self.entities =                  self.menu_widgets["checkboxes"]   .find(lambda x: x.text == "Entities")
        self.generation_mode =           self.menu_widgets["togglebuttons"].find(lambda x: x.text == "Instant")
        self.anim_fps =                  self.menu_widgets["sliders"]      .find(lambda x: x.text == "Animation")
        self.lag =                       self.menu_widgets["sliders"]      .find(lambda x: x.text == "Camera Lag")
        self.volume =                    self.menu_widgets["sliders"]      .find(lambda x: x.text == "Volume")
        self.max_entities =              self.menu_widgets["sliders"]      .find(lambda x: x.text == "Entities")
        self.texture_pack =              self.menu_widgets["buttons"]      .find(lambda x: x.text == "Textures")
        #
        self.iter_menu_widgets = sum(self.menu_widgets.values(), [])
        befriend_iterable(self.iter_menu_widgets)
        # assignments
        self.show_fps_smart = SmartTextRender(self.get_fps, 12, (5, 5), "topleft")

        # keybind buttons
        self.keybinds_active = False
        self.keybind_buttons = []
        self.keybind_height = 52
        h = self.keybind_height
        self.keybind_button_kwargs = {"width": 400, "height": h, "bg_color": (40, 40, 40, 210), "text_color": WHITE, "text_orien": "left", "friends": [self.keybinds], "disabled": True}
        for kb_type in g.p.keybinds:
            for yo, kb in enumerate(g.p.keybinds[kb_type]):
                b = Button(win.renderer, kb.replace("_", " ").title(), self.set_selected_widget_command, pass_self=True, right_command=self.set_selected_widget_right_command, pass_self_right=True, middle_command=self.set_selected_widget_middle_command, pass_self_middle=True, pos=(win.centerx, yo * h + 200), **self.keybind_button_kwargs)
                b._iden = kb
                set_widget_icon(b, g.p.keybinds[kb_type][kb], h)
                self.keybind_buttons.append(b)
        for i, button in enumerate(self.keybind_buttons):
            try:
                controller.button_protocol[button] = self.keybind_buttons[i + 1]
            except IndexError:
                controller.button_protocol[button] = self.keybind_buttons[0]
        d = Button(win.renderer, "Restore Defaults", self.restore_default_keybinds_confirm, pos=(win.centerx, (yo + 1) * h + 200), **self.keybind_button_kwargs)
        self.keybind_buttons.append(d)
        befriend_iterable(self.keybind_buttons)
        # other widgets
        self.tool_crafter_kwargs = {"text_color": WHITE, "visible_when": lambda: g.midblit == "tool-crafter", "width": tool_crafter_sword_width - 6, "height": 36}
        self.tool_crafter_selector = ComboBox(win.renderer, "sword", ["cube", "sphere", "katana", "icosahedron"] + tool_names, unavailable_tool_names, command=self.tool_crafter_selector_command, font=orbit_fonts[15], bg_color=pygame.Color("aquamarine4"), extension_offset=(-1, 0), **self.tool_crafter_kwargs)
        self.tool_crafter_rotate = ToggleButton(win.renderer, ("rotate", "still"), command=self.tool_crafter_rotate_command, font=orbit_fonts[15], **self.tool_crafter_kwargs)

    def disable_home_widgets(self):
        for wt in self.menu_widgets:
            for widget in self.menu_widgets[wt]:
                widget.disable()

    @property
    def show_any_hitboxes(self):
        return self.show_hitboxes or self.show_player_hitboxes

    # menu widget commands
    @staticmethod
    def show_stats_command():
        pass

    def get_fps(self):
        fps = int(g.clock.get_fps())
        ret = f"FPS: {fps} | Entities: {g.num_entities} | Particles: {len(all_other_particles)}"
        return ret

    def show_fps_command(self):
        yo = 20
        # write(win.renderer, "topright", f"FPS: {self.show_fps_smart()[0]}, 1% low: {g.bottom_1p_avg}", orbit_fonts[20], BLACK, win.width - 10, yo, tex=True, ignore=False)
        win.renderer.blit(*self.show_fps_smart())
        # write(win.renderer, "topright" , int(g.clock.get_fps()), orbit_fonts[20], BLACK, win.width - 10, 40)

    @staticmethod
    def checkb_sf_exit_command():
        g.menu = False

    @staticmethod
    def lighting_command(alpha):
        return
        for chunk_index, lighting in g.w.lightings.items():
            lighting.alpha = alpha

    @staticmethod
    def color_skin(code):
        try:
            color = pygame.Color(code if "#" in code else [int(cc) for cc in code.replace(",", " ").split(" ") if cc])
        except ValueError:
            MessageboxOk(win.renderer, "Invalid color.", **pw.widget_kwargs)
        else:
            g.w.player_model_color = color

    @staticmethod
    def next_piece_command():
        return
        music_path = get_rand_track(path("assets", "Audio", "Music", "Background"))
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.play()
        g.last_music = os.path.splitext(os.path.split(music_path)[1])[0]

    @staticmethod
    def show_config_command():
        g.opened_file = True
        open_text("config.json")

    @staticmethod
    def flag_command():
        g.w.flag_data["pos"] = g.player.rect.center
        group(SlidePopup("Flagged coordinates!"), all_slidepopups)

    @staticmethod
    def texture_pack_command():
        def tpc(e):
            p = path(".game_data", "texture_packs")
            if e in os.listdir(p):
                for d in os.listdir(path(p, e)):
                    if d != ".DS_Store":
                        for item in os.listdir(path(p, e, d)):
                            g.w.tex_assets[d][os.path.splitext(item)[0]] = SmartSurface.from_surface(cimgload3(path(p, e, d, item)))
            else:
                MessageboxOk(win.renderer, "Texture pack does not exist, load it first", **pw.widget_kwargs)
        entry_tp = Entry(win.renderer, "Enter the name of the texture pack ('.default' for default):", tpc, **pw.entry_kwargs, friends=[pw.texture_pack])

    def change_keybinds_command(self):
        self.disable_home_widgets()
        for button in self.keybind_buttons:
            button.enable()
        self.keybinds_active = True

    def disable_keybinds(self):
        for button in self.keybind_buttons:
            button.disable()
        # g.selected_widget = self.keybind_buttons[0]
        self.keybinds_active = False
        g.selected_widget = None

    @staticmethod
    def set_selected_widget_command(widget):
        if g.selected_widget == widget:
            change_keybind(widget, widget._iden, "#lmouse")
        else:
            g.selected_widget = widget

    @staticmethod
    def set_selected_widget_right_command(widget):
        if g.selected_widget == widget:
            change_keybind(widget, widget._iden, "#rmouse")

    @staticmethod
    def set_selected_widget_middle_command(widget):
        if g.selected_widget == widget:
            change_keybind(widget, widget._iden, "#mmouse")

    def restore_default_keybinds_confirm(self):
        MessageboxOkCancel(win.renderer, "Restore default keybinds? This will overwrite your current configuration.", self.restore_default_keybinds_command, **pw.widget_kwargs)

    def restore_default_keybinds_command(self):
        for button in self.keybind_buttons:
            if hasattr(button, "_iden"):
                change_keybind(button, button._iden, getattr(g.p, f"default_{button._iden}")[1])
        self.menu = False
        self.keybinds_active = False

    @staticmethod
    def save_and_quit_command():
        ExitHandler.must_save = True

    # home static widgets
    @staticmethod
    def is_worlds_worlds():
        return g.stage == "home" and g.home_stage == "worlds"

    @staticmethod
    def is_worlds_static():
        return g.stage == "home" and g.home_stage == "settings"

    @staticmethod
    def is_home():
        return g.stage == "home"

    # death screen widget commands
    def quit_death_screen_command(self):
        g.player.dead = False
        for widget in self.death_screen_widgets:
            widget.disable()
        g.w.screen, g.w.layer = g.player.spawn_data

    # outer widget commands
    @staticmethod
    def button_lw_command():
        if not all_messageboxes:
            loading_path = choose_file("Load a .dat file")
            if loading_path != "/":
                with open(loading_path, "rb") as f:
                    worldcode = pickle.load(f)
                new_world(worldcode)

    @staticmethod
    def button_jw_command():
        Entry(win.renderer, "Enter something:", lambda x: print(x), **pw.entry_kwargs)

    @staticmethod
    def button_daw_command():
        if not all_messageboxes:
            delete_all_worlds()

    @staticmethod
    def show_credits_command():
        g.opened_file = True
        open_text("CREDITS.txt")

    @staticmethod
    def intro_command():
        play_intro()

    @staticmethod
    def custom_textures_command():
        # open_text("TEXTURE_TUTORIAL.txt")
        pth = choose_folder("Choose folder where texture pack is located")
        tex = os.path.basename(os.path.normpath(pth))
        if tex == ".default":
            MessageboxOk(win.renderer, "Texture pack cannot have the name '.default'", **pw.widget_kwargs)
            return
        shutil.copytree(pth, path(".game_data", "texture_packs", tex), dirs_exist_ok=True)
        MessageboxOk(win.renderer, "Texture pack loaded succesfully.", **pw.widget_kwargs)

    @staticmethod
    def set_home_stage_worlds_command():
        g.home_stage = "worlds"

    @staticmethod
    def set_home_stage_settings_command():
        g.home_stage = "settings"

    @staticmethod
    def tool_crafter_selector_command(tool):
        func = f"get_{tool}"
        if hasattr(tools, func):
            g.mb.sword = getattr(tools, func)(g.mb.sword_color)
        else:
            MessageboxError(win.renderer, "Selected tool currently has no model view", as_child=True, **pw.widget_kwargs)

    @staticmethod
    def tool_crafter_rotate_command(option):
        g.mb.sword.rotate = option == "rotate"

    @property
    def tool_crafter_selector_range_rect(self):
        mbr = g.midblit_rect()
        return pygame.Rect(mbr.x - pw.tool_crafter_selector.combo_width, mbr.y, pw.tool_crafter_selector.combo_width, pw.tool_crafter_selector.height * pw.tool_crafter_selector.num_combos)


class Lattice:
    def __init__(self, type_, color):
        self.crystal = get_crystal(type_, color)
        self.stoic = 1


# G R A P H I C A L  C L A S S E S S ------------------------------------------------------------------ #
class Animations:
    def __init__(self):
        self.imgs = {}
        self.rects = {}
        self.data = {
            "_default": {
                # default is 0.05 at slider 6 with 120
                "_default_run": {"frames": 8},
                "_default_idle": {"frames": 4, "speed": 0.025},
                "_default_jump": {"frames": 1, "offset": (1, 0)},
                "_default_punch": {"frames": 4, "speed": 0.1, "offset": (9, 2)},
                # staff
                "staff_idle": {"frames": 2, "speed": 0.012},
                "staff_run": {"frames": 4},
                "staff_jump": {"frames": 1},
                # katana
                "katana_run": {"frames": 8},
            },

            "staff": {
                "run": {"frames": 8},
                "jump": {"frames": 8},
            },
        }
        # anim imgs
        base = path("assets", "Images", "Player_Animations")
        for weapon in os.listdir(base):
            if weapon == ".DS_Store" or weapon not in ("_default", "staff"):
                continue
            try:
                self.imgs[weapon] = {}
                self.rects[weapon] = {}
                for anim_file in os.listdir(path(base, weapon)):
                    anim_type, ext = os.path.splitext(anim_file)
                    if weapon != "_default" and anim_type != "run":
                        continue
                    num_frames = self.data[weapon][anim_type]["frames"]
                    surfs = imgload3(base, weapon, anim_file, frames=num_frames)
                    if isinstance(surfs, pygame.Surface):
                        surfs = [surfs]
                    self.imgs[weapon][anim_type] = {}
                    self.imgs[weapon][anim_type]["images"] = [T(img) for img in surfs]
                    self.imgs[weapon][anim_type]["fimages"] = [T(pygame.transform.flip(img, True, False)) for img in surfs]
                    self.rects[weapon][anim_type] = self.imgs[weapon][anim_type]["images"][0].get_rect()
            except KeyError:
                raise


class Player:
    def __init__(self):
        # animation data
        self.anim_type = "idle"
        self.anim_queue = []
        # image initialization
        self.direc = "left"
        self.anim = 0
        self.up = True
        self.tools = [None, None]
        self.tool_healths = [100, 100]
        self.tool_ammos = [None, None]
        self.indexes = {"tool": 0, "block": 0}
        # rest
        self.x = 0
        self.y = 0
        # self._rect = self.image.get_rect(center=win.center)
        self.fre_vel = 3
        self.adv_xvel = 2
        self.water_xvel = 1
        self.xvel = 0
        self.extra_xvel = 0
        self.yvel = 0
        self.xacc = 1  # player xacc
        self.yacc = 0.1
        self.max_xvel = 2
        #
        self.animate()
        self.def_gravity = self.gravity = 0.08
        self.def_jump_yvel = -3.5
        self.jump_yvel = self.def_jump_yvel
        self.water_jump_yvel = self.jump_yvel / 2
        self.fall_effect = 0
        self.jumps_left = 0
        self.dx = 0
        self.dy = 0
        self.to_dashx = [0, 0]
        self.to_dashy = [0, 0]
        self.flinching = False
        self.block_data = []
        self.water_data = []
        self.ramp_data = []
        self.still = True
        self.in_air = True
        self.invisible = False
        self.stats = {}
        self.spin_angle = 0
        self.eating = False

        self.set_moving_mode("adventure")

        self.def_food_pie = {"counter": -90}
        self.food_pie = self.def_food_pie.copy()
        self.achievements = {"steps taken": 0, "steps counting": 0}
        self.dead = False

        self.rand_username()

        self.tool_healths = []
        self.tool_ammos = []
        self.inventory = []
        self.inventory_amounts = []
        self.pouch = 15
        self.broken_blocks = dd(int)
        self.main = "block"
        self.moved_x = 0
        self.circle = T(circle(self.size[0] * 0.08, RED))

    def __getstate__(self):
        del self.image
        return self.__dict__

    def update(self):  # player update
        self.animate()
        self.draw()
        self.move_accordingly()
        self.off_screen()
        self.drops()
        self.achieve()

    def move_accordingly(self):
        if no_widgets(Entry):
            self.adventure_move()

    def draw(self):  # player draw
        win.renderer.blit(self.image, self.rect_draw)
        if pw.show_any_hitboxes:
            draw_rect(win.renderer, (120, 120, 120, 255), self.rect)
            draw_rect(win.renderer, ORANGE, self.rect_draw)
            with suppress(IndexError):
                col = self.get_cols()[0]
                # print(self.y, self._rect, self.rect, pygame.Rect(col.x - g.scroll[0], col.y - g.scroll[1], 30, 30), pygame.mouse.get_pos())
            circle_rect = pygame.Rect(0, 0, self.circle.width, self.circle.height)
            circle_rect.center = self.rect_draw.center
            win.renderer.blit(self.circle, circle_rect)


    @property  # player _rect; player urect
    def _rect(self):
        ret = pygame.Rect(0, 0, *self.size)
        ret.center = (self.x, self.y)
        return ret

    @property
    def rect(self):  # player rect play
        ret = pygame.Rect(self._rect.x - g.scroll[0], self._rect.y - g.scroll[1], *self.size)
        return ret

    @property
    def _rect_draw(self):
        ret = pygame.Rect(0, 0, *self.ci_size)
        xo, yo = anim.data["_default"][self.sanim_type].get("offset", (0, 0))
        xo *= S * self.sign
        yo *= S
        ret.center = (self.x + xo, self.y + yo)
        return ret

    @property
    def rect_draw(self):
        ret = pygame.Rect(self._rect_draw.x - g.scroll[0], self._rect_draw.y - g.scroll[1], *self.ci_size)
        return ret

    @property
    def sign(self):
        return 1 if self.direc == "right" else -1

    @property
    def size(self):
        return (14 * S, 23 * S + 1)

    @property
    def ci_size(self):
        return (self.image.width, self.image.height)

    @property
    def width(self):
        return self.size[0]

    @property
    def height(self):
        return self.size[1]

    @property
    def reverse_blocks(self):
        yield from reversed(all_blocks)

    @property
    def closest_blocks(self):
        yield from sorted(all_blocks, key=lambda block: distance(self.rect, block.rect))

    @property
    def closest_tool_blocks(self):
        yield from sorted(all_blocks, key=lambda block: distance(visual.rect, block.rect))

    @property
    def angle(self):
        return revnum(degrees(two_pos_to_angle(self.rect.center, g.mouse)))

    @property
    def item(self):
        return self.inventory[self.indexes[self.main]]

    @item.setter
    def item(self, value):
        self.inventory[self.indexes[self.main]] = value

    @property
    def itemi(self):
        return self.indexes[self.main]

    @itemi.setter
    def itemi(self, value):
        self.indexes[self.main] = value

    @property
    def block(self):
        return self.inventory[self.blocki] if self.inventory[self.blocki] is not None else ""

    @block.setter
    def block(self, value):
        self.inventory[self.blocki] = value

    @property
    def blocki(self):
        return self.indexes["block"]

    @blocki.setter
    def blocki(self, value):
        self.indexes["block"] = value

    @property
    def empty_blocki(self):
        return first(self.inventory, None, self.blocki)

    @empty_blocki.setter
    def empty_block(self, value):
        if isinstance(value, tuple):
            ebi = self.empty_blocki
            self.inventory[ebi], self.inventory_amounts[ebi] = value
        else:
            self.inventory[self.empty_blocki] = value

    @property
    def tool(self):
        return self.tools[self.indexes["tool"]]

    @tool.setter
    def tool(self, value):
        self.tools[self.indexes["tool"]] = value

    @property
    def stool(self):
        return self.tool if self.tool is not None else "_default"

    @property
    def sanim_type(self):
        return f"{self.stool}_{self.anim_type}"

    @property
    def tool_type(self):
        return gtool(self.tool)

    @property
    def tool_ore(self):
        return tore(self.tool)

    @property
    def tooli(self):
        return self.indexes["tool"]

    @tooli.setter
    def tooli(self, value):
        self.indexes["tool"] = value

    @property
    def empty_tooli(self):
        return first(self.tools, None, self.tooli)

    @empty_tooli.setter
    def empty_tool(self, value):
        self.tools[self.empty_tooli] = value

    @property
    def tool_health(self):
        return self.tool_healths[self.tooli]

    @tool_health.setter
    def tool_health(self, value):
        self.tool_healths[self.tooli] = value

    @property
    def tool_ammo(self):
        return self.tool_ammos[self.tooli]

    @tool_ammo.setter
    def tool_ammo(self, value):
        self.tool_ammos[self.tooli] = value

    @property
    def gun(self):
        return self.tools[self.guni]

    @gun.setter
    def gun(self, value):
        self.tools[self.guni] = value

    @property
    def guni(self):
        return first(self.tools, is_gun, None)

    @property
    def amount(self):
        return self.inventory_amounts[self.indexes[self.main]]

    @amount.setter
    def amount(self, value):
        self.inventory_amounts[self.indexes[self.main]] = value

    def new_block(self, name, amount=1):
        if name in self.inventory:
            self.inventory_amounts[self.inventory.index(name)] += amount
        else:
            self.empty_block = name, amount

    def new_empty_block(self, name, amount=1):
        if None in self.inventory:
            self.new_block(name, amount)

    @property
    def lives(self):
        return self.stats["lives"]["amount"]

    @lives.setter
    def lives(self, value):
        self.stats["lives"]["amount"] = value
        if self.lives > 100:
            self.lives = 100

    @property
    def hunger(self):
        return self.stats["hunger"]["amount"]

    @hunger.setter
    def hunger(self, value):
        self.stats["hunger"]["amount"] = value
        if self.hunger > 100:
            self.hunger = 100

    @property
    def thirst(self):
        return self.stats["thirst"]["amount"]

    @thirst.setter
    def thirst(self, value):
        self.stats["thirst"]["amount"] = value
        if self.thirst > 100:
            self.thirst = 100

    @property
    def energy(self):
        return self.stats["energy"]["amount"]

    @energy.setter
    def energy(self, value):
        self.stats["energy"]["amount"] = value
        if self.energy > 100:
            self.energy = 100

    @property
    def oxygen(self):
        return self.stats["oxygen"]["amount"]

    @oxygen.setter
    def oxygen(self, value):
        self.stats["oxygen"]["amount"] = value
        if self.oxygen > 100:
            self.oxygen = 100

    def attack(self):
        self.new_anim("punch", check=True)

    def dashx(self, amount, speed, wait=0):
        def _dashx():
            time.sleep(wait)
            self.to_dashx = [amount * self.sign, speed * self.sign]
        if wait > 0:
            Thread(target=_dashx).start()

    def dashy(self, amount, speed, wait=0):
        def _dashx():
            time.sleep(wait)
            self.to_dashy = [amount * self.sign, speed * self.sign]
        if wait > 0:
            Thread(target=_dashx).start()

    def flinch(self, xvel, yvel):
        def inner():
            self.flinching = True
            self.extra_xvel += xvel
            self.yvel = yvel
            sleep(0.5)
            self.extra_xvel -= xvel
            self.flinching = False
        CThread(target=inner).start()

    def flip_images(self, images):
        self.right_images = images
        self.left_images = [pygame.transform.flip(img, True, False) for img in images]

    def achieve(self):
        pass

    def set_moving_mode(self, name, *args):
        self.moving_mode = [name, *args]
        if name in ("adventure", "freestyle"):
            self.last_moving_mode = [name, *args]

    def new_tool(self, name):
        self.tool_healths[self.empty_tooli] = 100
        self.empty_tool = name

    def link_worlds(self):
        def m():
            time.sleep(randf(0.5, 1.5))
            if chance(1 / 10):
                text = "The linking has been unsuccesful."
            else:
                text = "The worlds have linked succesfully."
                g.cannot_place_block = True
                g.w.dimension = "magic"
                g.w.linked = True
                utilize_blocks()
                next_ambient()
            MessageboxOk(win.renderer, "The worlds have linked succesfully.", **pw.widget_kwargs)

        Thread(target=m).start()

    def die(self, cause):
        self.dead = True
        pw.death_cause.overwrite(f"{self.username} has died. Cause of death: {cause}")
        for widget in pw.death_screen_widgets:
            widget.enable()

    def use_up_inv(self, index=None, amount=1):
        index = index if index is not None else self.blocki
        self.inventory_amounts[index] -= amount
        if self.inventory_amounts[index] == 0:
            self.inventory[index] = None
            self.inventory_amounts[index] = None

    def take_dmg(self, amount, shake_offset, shake_length, reason=None):
        self.stats["lives"]["amount"] -= amount
        self.stats["lives"]["regen_time"] = def_regen_time
        self.stats["lives"]["last_regen"] = ticks()
        g.s_render_offset = shake_offset
        g.screen_shake = shake_length
        if g.player.stats["lives"]["amount"] <= 0:
            g.player.die(reason)

    def eat(self, food=None):
        # self.eating = True
        # food = self.block if food is not None else self.block
        # self.food_pie["counter"] += get_finfo(self.inventory[self.blocki])["speed"]
        # degrees = self.food_pie["counter"]
        # pie_size = (30, 30)
        # pil_img = PIL.Image.new("RGBA", [s * 4 for s in pie_size])
        # pil_draw = PIL.ImageDraw.Draw(pil_img)
        # pil_draw.pieslice((0, 0, *[ps * 4 - 1 for ps in pie_size]), -90, degrees, fill=g.w.player_model_color[:3])
        # pil_img = pil_img.resize(pie_size, PIL.Image.Resampling.LANCZOS)
        # pg_img = pil_to_pg(pil_img)
        # self.food_pie["image"] = T(pg_img)
        # self.food_pie["rect"] = self.food_pie["image"].get_rect()
        # if self.food_pie["counter"] >= 270:
        #     for attr in finfo[food]["amounts"]:
        #         if self.stats[attr]["amount"] < 100:
        #             self.stats[attr]["amount"] += finfo[food]["amounts"][attr]
        #         if self.stats[attr]["amount"] > 100:
        #             self.stats[attr]["amount"] = 100
        #     self.use_up_inv(self.blocki)
        #     self.food_pie = self.def_food_pie.copy()
        self.eating = True

    def drops(self):
        for drop in all_drops:
            if drop._rect.colliderect(self._rect):
                if None in g.player.inventory or drop.name in g.player.inventory:
                    self.new_block(drop.name, drop.drop_amount)
                    drop.kill()
                    # pitch_shift(pickup_sound).play()
                    if None not in self.inventory:
                        drop._rect.center = [pos + random.randint(-1, 1) for pos in drop.og_pos]

    def rand_username(self):
        # self.username = f"Player{rand(2, 456)}"
        # self.username = json.loads(requests.get(g.funny_words_url).text)[0].split("_")[0]
        # self.username = json.loads(requests.get(g.funny_words_url).text)[0].split("_")[0]
        # self.username = fnames.dwarf()
        # self.username = shake_str(json.loads(requests.get(g.name_url).text)["name"]).title()
        # self.username = json.loads(requests.get(g.name_url).text)["username"].capitalize()
        # self.username = " ".join([json.loads(requests.get(g.random_word_url).text)[0]["word"] for _ in range(2)]).title()
        self.username = rand_alien_name().title()

    def cust_username(self):
        def set_username(ans):
            if ans is not None and ans != "":
                split_username = ans.split(" ")
                username = " ".join([word if not word in g.profanities else len(word) * "*" for word in split_username])

                self.username = username
            else:
                self.rand_username()
        Entry(win.renderer, "Enter your new username:", set_username, **pw.entry_kwargs, default_text=("random", orbit_fonts[20]))

    def get_cols(self, rects_only=True, ramps=False):
        ret = []
        if rects_only:
            for data in ((self.block_data + self.ramp_data) if ramps else self.block_data):
                if pw.show_any_hitboxes:
                    rect = pygame.Rect(data[1].x - g.scroll[0], data[1].y - g.scroll[1], *data[1].size)
                    # draw_rect(win.renderer, ORANGE, rect)
                if self._rect.colliderect(data[1]) and is_hard(data[0].name):
                    ret.append(data[1])
        else:
            for data in ((self.block_data + self.ramp_data) if ramps else self.block_data):
                if pw.show_any_hitboxes:
                    rect = pygame.Rect(data[1].x - g.scroll[0], data[1].y - g.scroll[1], *data[1].size)
                    # draw_rect(win.renderer, GREEN, rect)
                if self._rect.colliderect(data[1]):
                    ret.append(data)
        return ret

    def scroll(self):
        # scrolling
        if g.scroll_orders:
            g.fake_scroll[0] += (g.scroll_orders[0] - g.fake_scroll[0] - win.width // 2) / pw.lag.value
            g.fake_scroll[1] += (g.scroll_orders[1] - g.fake_scroll[1] - win.height // 2) / pw.lag.value
        else:
            g.fake_scroll[0] += (self._rect.x - g.fake_scroll[0] - win.width // 2 + self.width // 2 + g.extra_scroll[0]) / pw.lag.value
            g.fake_scroll[1] += (self._rect.y - g.fake_scroll[1] - win.height // 2 + self.height // 2 + g.extra_scroll[1]) / pw.lag.value
            # getting rid of floating point errors
        g.scroll[0] = round(g.fake_scroll[0])
        g.scroll[1] = round(g.fake_scroll[1])
        # screenshake maybe?
        if pw.screenshake and g.screen_shake_magnitude > 0:
            g.scroll[0] += rand(-g.screen_shake_magnitude, g.screen_shake_magnitude)
            g.scroll[1] += rand(-g.screen_shake_magnitude, g.screen_shake_magnitude)
            if ticks() - g.last_screen_shake >= g.screen_shake_duration:
                g.screen_shake_magnitude = 0

    # player move
    def adventure_move(self):
        # cant walk if some of these are active
        if pw.keybinds_active:
            return
        # scroll
        self.scroll()

        # keyboard input
        keys = pygame.key.get_pressed()
        left = right = up = down = False
        if keys[pygame.K_a]:
            left = True
        if keys[pygame.K_d]:
            right = True
        if keys[pygame.K_w]:
            up = True
        if keys[pygame.K_s]:
            down = True

        # controller movement
        if controller.joystick is not None:
            b = controller.map[controller.name]["buttons"]
            a = controller.map[controller.name]["axes"]
            if controller.joystick is not None:
                j = controller.joystick
                # jump
                if j.get_button(b["cross"]):
                    up = True
                # move
                axis = j.get_axis(a["Jleft"][0])
                if abs(axis) >= 0.1:
                    if axis > 0:
                        right = True
                    else:
                        left = True

        # dashes
        # x
        if abs(self.to_dashx[0]) > 0:
            if sign(self.to_dashx[0] + self.to_dashx[1]) != sign(self.to_dashx[0]):
                self.to_dashx = [0, 0]
            else:
                self.to_dashx[0] += self.to_dashx[1]
            self.x += self.to_dashx[0]
        # y
        if abs(self.to_dashy[0]) > 0:
            if sign(self.to_dashy[0] + self.to_dashy[1]) != sign(self.to_dashy[0]):
                self.to_dashy = [0, 0]
                self.yvel = 0
            else:
                self.to_dashy[0] += self.to_dashy[1]
            self.y += self.to_dashy[0]

        # x-movement
        if left:
            self.direc = "left"
        elif right:
            self.direc = "right"
        # animation setting
        if left or right:
            if self.anim_type == "idle":
                self.set_anim("run")
        else:
            if self.anim_type == "run":
                self.set_anim("idle")
        # x-col (euler's method) (Leo you're a Nerd "eluer's 'todd" suck my balls and shut the fuck up and code the gameplay already)
        if left:
            self.xvel += (-self.max_xvel - self.xvel) * self.xacc
        elif right:
            self.xvel += (self.max_xvel - self.xvel) * self.xacc
        else:
            self.xvel += -self.xvel * self.xacc
        if self.max_xvel == 0 and abs(self.xvel) <= 10 ** -1:
            self.xvel = 0
        self.x += self.xvel
        for col in self.get_cols(rects_only=True):
            if self.xvel > 0:
                self.x = col.left - self.width / 2
            elif self.xvel < 0:
                self.x = col.right + self.width / 2
        # y-col
        self.yvel += self.gravity
        # animation setting
        if self.yvel > 3:
            if self.anim_type in ("idle", "run"):
                self.set_anim("jump")
        self.y += self.yvel
        for col in self.get_cols(rects_only=True):
            if self.yvel > 0:
                self.y = col.top - int(self.height / 2)
                for col in self.get_cols(rects_only=True):
                    draw_rect(win.renderer, GREEN, pygame.Rect(col.x - g.scroll[0], col.y - g.scroll[1], 30, 30))
                self.yvel = 0
                if self.anim_type == "jump":
                    self.set_anim("idle")
            elif self.yvel < 0:
                self.y = col.bottom + int(self.height / 2)
                self.yvel = 0

    def jump(self):
        if self.anim_type != "jump":
            g.player.yvel = g.player.def_jump_yvel
            self.set_anim("jump")

    def camel_move(self, camel):
        self.rect.centerx = camel.centerx - 10
        self.rect.centery = camel.centery - 35
        self.energy += 0.001

    def gain_ground(self):
        pass

    def off_screen(self):
        pass

    def external_gravity(self):
        pass

    # new anim is adding to the queue
    def new_anim(self, anim_type, check=True):
        # dashes
        if anim_type == "dslash":
            self.dashx(8, -0.3)
        elif anim_type == "stab":
            # self.dashx(9, -0.7, 0.1)
            # self.y += 9
            shake_screen(5, 30)
        elif anim_type == "uslash":
            self.dashx(8, -0.3)
            self.dashy(-10, 0.6)
            self.yvel = -3.7
        # rest
        if check and len(self.anim_queue) < 4:
            if self.anim_type in ("idle", "run", "jump"):
                self.set_anim(anim_type)
            else:
                self.anim_queue.append(anim_type)

    # setting anim is instantaneous
    def set_anim(self, anim_type=None):
        self.anim = 0
        self.anim_type = self.anim_queue.pop(0) if anim_type is None else anim_type

    @property
    def anim_direc(self):
        if self.direc == "left":
            return "fimages"
        else:
            return "images"

    # player animate
    def animate(self):
        # debug
        try:
            fdi = anim.imgs["_default"][self.sanim_type][self.anim_direc]
        except KeyError:
            fdi = anim.imgs["_default"]["_default_idle"][self.anim_direc]
        self.anim += anim.data["_default"][self.sanim_type].get("speed", g.p.anim_fps * 2)
        try:
            # try animating the index given the fdi
            fdi[int(self.anim)]
        except IndexError:
            # animation index exceeded the amount of frames
            if self.anim_type in ("jump", "run"):
                self.anim = 0
            else:
                if self.anim_queue:
                    self.set_anim()
                else:
                    self.set_anim("idle")
            fdi = anim.imgs["_default"][self.sanim_type][self.anim_direc]
        finally:
            self.image = fdi[int(self.anim)]


class Visual:
    def __init__(self):
        # misc
        self.following = True
        self.tool_range = 50
        self.moused = True
        # sword
        self.angle = 0
        self.cursor_trail = CursorTrail(win.renderer, 50)
        self.mouse_init = None
        # domineering sword
        self.ns_last = perf_counter()
        self.init_ns()
        self.ns_nodes = []
        # bow
        self.bow_index = 0
        # grappling hook
        self.grapple_line = []
        # pymunk
        self.atoms = []
        self.bonds = []
        w, h = 3, 10
        for y in range(10):
            atom = PhysicsEntity(win.renderer, win.size, win.space, 650, 300 + y * 5, 5, 5, 1, 0, (KINEMATIC if y == 0 else DYNAMIC))
            self.atoms.append(atom)
        self.first_atom = self.atoms[0]
        for i in range(len(self.atoms)):
            with suppress(IndexError):
                bond = PhysicsEntityConnector(win.renderer, win.size, win.space, self.atoms[i], self.atoms[i + 1])
                self.bonds.append(bond)
        # scope
        bw = 5
        self.scope_border_size = (80, 80)
        self.scope_border_img = pygame.Surface(self.scope_border_size, pygame.SRCALPHA)
        pygame.gfxdraw.aacircle(self.scope_border_img, *[s // 2 for s in self.scope_border_size], self.scope_border_size[0] // 2 - 1, BLACK)
        self.scope_inner_size = [s - bw - 5 for s in self.scope_border_size]
        self.scope_inner_img = pygame.Surface(self.scope_inner_size, pygame.SRCALPHA)
        pygame.draw.circle(self.scope_inner_img, DARK_GRAY, [s // 2 for s in self.scope_inner_size], self.scope_inner_size[0] // 2, bw, True, False, False, False)
        self.scope_angle = 0
        self.scope_inner_base = SmartSurface(self.scope_inner_size, pygame.SRCALPHA)
        self.reloading = False
        self.scope_yoffset = 12
        # swinging
        self.avel = 0
        self.max_avel = 6
        self.angle = 0
        self.returning = 0
        self.block_data = []
        self.hit_direc = None
        #
        self.axe_update = self.pickaxe_update
        self.axe_rebound = self.pickaxe_rebound
        self.axe_stop_rebound = self.pickaxe_stop_rebound
        # shoveling
        self.yvel = 0

    def draw(self):  # visual draw
        if self.render:
            # base render
            win.renderer.blit(self.image, self.rect)
            # render mouse
            if self.mouse_init is not None:
                m = self.mouse_init
                s = 8
                o = sin(ticks() * 0.01) * s
                win.renderer.draw_color = DARK_BLUE
                win.renderer.draw_quad((m[0], m[1] + o), (m[0] + s, m[1]), (m[0], m[1] - o), (m[0] - s, m[1]))
                win.renderer.draw_quad((m[0] + o, m[1] - s), (m[0] - o, m[1] - s), (m[0] - o, m[1] + s), (m[0] + o, m[1] + s))
                win.renderer.draw_color = NAVY_BLUE
                win.renderer.draw_line(m, g.mouse)
            if pw.show_hitboxes:
                draw_rect(win.renderer, RED, self.rect)
            # pymunk render
            # self.first_atom.body.velocity = g.mouse_delta
            # for bond in self.bonds:
            #     bond.draw()
                # bond.src.draw()
                # bond.dest.draw()
        for node in self.ns_nodes[:]:
            if ticks() - node[-1] >= 330:
                self.ns_nodes.remove(node)
        if len(self.ns_nodes) >= 2:
            draw_lines(win.renderer, MOSS_GREEN, False, [node[0] for node in self.ns_nodes])

    @property
    def srect(self):
        return [r / 3 for r in self.rect]

    @property
    def facing_right(self):
        return g.mouse[0] > g.player.rect.centerx

    @property
    def facing_up(self):
        return g.mouse[1] > g.player.rect.centery

    @property
    def sign(self):
        return 1 if self.facing_right else -1

    @property
    def mask(self):
        return pygame.mask.from_surface(self.image)

    # update rebound stop rebound
    def pickaxe_update(self):
        if self.returning == 0:
            m = 0.04
            self.avel += m * (self.sign * self.max_avel - self.avel)

    def pickaxe_rebound(self, block=None):
        if self.returning == 0:
            self.returning = self.avel = -sign(self.avel)

    def pickaxe_stop_rebound(self):
        if self.returning != 0:
            self.avel = 7 * self.returning
            self.returning = 0

    def shovel_update(self):
        self.yvel += 0.4
        self.rect.y += self.yvel
        # self.rect.y = g.player.rect.centery - abs(sin(2 * pi * ticks() / 1000)) * 30 + 15

    def shovel_rebound(self, rect=None):
        if rect is not None:
            self.rect.bottom = rect.top
        self.yvel = -5 * sign(self.yvel)

    def update(self):  # visual update
        # self.cursor_trail.update()
        self.render = True
        if g.player.main == "tool":
            # set visual image
            self.image = g.w.surf_assets["tools"][g.player.tool]
            if g.player.tool_type in rotating_tools:
                self.image, self.rect = rot_pivot(self.image, self.angle, g.player.rect.center, Vector2(-13, -13))
            self.image = Image(T(self.image))
            if g.player.tool_type == "shovel":
                self.image.angle = 225
            #
            self.rect.centerx = g.player.rect.centerx - g.player.sign * 16
            self.rect.centery = g.player.rect.centery - 10
            self.image.flip_x = g.player.direc == "left"

            # get collisions
            self.block_data.clear()
            for yo in range(-2, 3):
                for xo in range(-2, 3):
                    target_chunk, abs_pos = pos_to_tile(self.rect.center)
                    target_chunk, abs_pos = correct_tile(target_chunk, abs_pos, xo, yo)
                    # processing the data
                    if target_chunk in g.w.data:
                        if abs_pos in g.w.data[target_chunk]:
                            try:
                                block = g.w.data[target_chunk][abs_pos]
                            except KeyError:
                                continue
                            else:
                                rect = pygame.Rect(block._rect.x - g.scroll[0], block._rect.y - g.scroll[1], BS, BS)
                                self.block_data.append([block, rect])
            if g.mouses[0]:
                # collisiòn
                any_col = False
                # x-axis collision
                m = 0.04
                self.avel += m * (self.sign * self.max_avel - self.avel)

                # if self.rect.centery - g.player.rect.centery >= 3 * BS:
                #     getattr(self, f"{g.player.tool_type}_rebound", lambda_none)()
                for block, rect in self.block_data:
                    if self.rect.colliderect(rect):
                        if block.name not in unbreakable_blocks:
                            if bpure(block.name) in tinfo[g.player.tool_type]["blocks"]:
                                block.broken += tinfo[g.player.tool_type]["blocks"][bpure(block.name)]
                                # getattr(self, f"{g.player.tool_type}_rebound", lambda_none)(rect)
                                if block not in g.w.to_break:
                                    g.w.to_break.append(block)
                                    any_col = True
                                break
                # if not any_col:
                #     getattr(self, f"{g.player.tool_type}_stop_rebound", lambda_none)()
            else:
                # pickaxe deceleration
                if g.player.tool_type in rotating_tools:
                    m = 0.04
                    self.avel += m * -self.avel
            # x-axis collision
            if g.player.tool_type == "shovel":
                self.rect.centerx = g.mouse[0]
            """
                for block, rect in self.block_data:
                    if pw.show_hitboxes:
                        draw_rect(win.renderer, ORANGE, rect)
                    if self.rect.colliderect(rect):
                        if g.mouse_delta[0] >= 0:
                            self.rect.right = rect.left
                        else:
                            self.rect.left = rect.right
            """

            # final angle adjustments
            if g.player.tool_type in rotating_tools:
                self.angle += self.avel

            # # set tool x-pos to player
            # if g.player.tool_type == "shovel":
            #     o = 60
            #     if self.facing_right:
            #         self.rect.centerx = min(g.player.rect.centerx + o, g.mouse[0])
            #     else:
            #         self.rect.centerx = max(g.player.rect.centerx - o, g.mouse[0])

            # render
            self.draw()

        elif g.player.main == "block":
            self.image = g.w.blocks[g.player.block]
            self.rect = self.image.get_rect(bottomright=g.player.rect.center)
            self.rect.centerx = g.player.rect.centerx
            self.rect.centery = g.player.rect.centery - 50
            if g.player.eating:
                self.rect.y += sin(2 * pi * ticks() * 0.005) * 7
            else:
                # self.rect.y += sin(ticks() / 7_000 * 2 * pi) * 12
                pass
            self.draw()

    def init_ns(self):
        self.ns_freq = 35
        self.ns_width = gauss(100, 50)
        self.ns_height = gauss(100, 50)
        self.ns_theta = randf(0, 2 * pi)
        self.ns_xo = 0
        self.ns_yo = 0

    def process_swipe(self, points):
        dx = sum(p[0] for p in points)
        dy = sum(p[1] for p in points)
        if (dx > 0) if g.player.direc == "right" else (dx < 0):
            if dy < 0:
                # g.player.new_anim("uslash")
                pass
            elif dy > 0:
                # g.player.new_anim("stab")
                pass
        g.mouse_rel_log.clear()

    def swing_sword(self):
        g.player.anim = 0
        # g.player.anim_type = choice(("uslash", "dslash"))

    def start_reloading(self):
        self.stop_reloading()
        self.reloading = True

    def stop_reloading(self):
        self.scope_angle = 0
        self.scope_inner_base = SmartSurface(self.scope_inner_size, pygame.SRCALPHA)
        self.reloading = False


class UI:
    def __init__(self):
        self.biggest = 0

    # ui update
    def update(self):
        if not g.dialogue:
            # self.render_player_icon()
            pass

    def render_player_icon(self):
        m = g.mouse
        if hypot(m[0] - player_border_rect.centerx, m[1] - player_border_rect.centery) <= player_border_rect.width / 2:
            for y, (name, stat) in enumerate(g.player.stats.items()):
                width = stat["width"]
                xmax = stat["amount"]
                stat["width"] += (xmax - width) * 0.2
        else:
            for y, (name, stat) in enumerate(g.player.stats.items()):
                width = stat["width"]
                stat["width"] -= width * 0.2
        _o = 10
        yo, height = player_border_rect.height / len(g.player.stats), 10
        height = yo * 0.7
        for y, (name, stat) in enumerate(g.player.stats.items()):
            color = stat["color"]
            width = stat["width"] * 2
            eff_width = width - _o
            if eff_width > 0:
                rect = [player_border_rect.right, player_border_rect.top + 10 + y * yo, width, height]
                #
                quad = [(player_border_rect.centerx, player_border_rect.top + y * yo),  # topleft
                        (player_border_rect.centerx + width, player_border_rect.top + y * yo),  # topright
                        [player_border_rect.centerx + width - _o, player_border_rect.top + y * yo + height],  # bottomright
                        (player_border_rect.centerx, player_border_rect.top + height + y * yo)]  # bottomleft
                fill_quad(win.renderer, color, *quad)
                draw_quad(win.renderer, BLACK, *quad)
        win.renderer.blit(player_border, player_border_rect)
        win.renderer.blit(g.player.player_icon, g.player.player_icon_rect)


class Projectile(Scrollable):
    def __init__(self, pos, mouse, start_pos, speed, gravity=0, image=None, name=None, color=BLACK, size=None, damage=0, traits=None, rotate=True, air_resistance=0, invisible=False, unfeelable=False, track_path=None, tangent=None):
        Scrollable.__init__(self, g)
        if image is None:
            self.image = pygame.Surface(size)
            self.image.fill(color)
            self.image = I(self.image)
        else:
            self.image = Image(image)
        self.name = name
        self.og_img = scale3x(self.image)
        self.rotate = rotate
        self.speed = speed
        self.size = self.image.texture.width, self.image.texture.height
        self.w, self.h = self.size
        self.x, self.y = start_pos
        self.x -= self.size[0] / 2
        self.y -= self.size[1] / 2
        self.sx, self.sy = self.x, self.y
        self.xvel, self.yvel = two_pos_to_vel(pos, mouse, speed)
        self.sxvel, self.syvel = self.xvel, self.yvel
        self.damage = damage
        self.gravity = gravity
        self.invisible = invisible
        self.unfeelable = unfeelable
        self.track_path = track_path
        self.tangent = tangent
        self.traits = traits if traits is not None else []
        self.air_resistance = air_resistance
        self.active = True

    def update(self):  # projectile update
        if self.active:
            self.move()
            self.collide_blocks()
        else:
            self.collide_player()
        self.draw()

    def draw(self):  # projectile draw
        if not self.invisible:
            win.renderer.blit(self.image, self.rect)

    @property
    def dx(self):
        return self.x - self.sx

    def move(self, sign=1):  # projectile move
        # calculus shit
        if self.rotate:
            angle = degrees(atan2(self.yvel, self.xvel))
            self.image.angle = angle
            if self.track_path:
                dx = self.x - self.sx
                pm = pmotion(self.sxvel, self.syvel, dx, self.sx, self.sy, self.gravity)
                for point in pm[0]:
                    _x = point[0] - g.scroll[0] + self.w / 2
                    _y = point[1] - g.scroll[1] + self.h / 2
                    draw_rect(win.renderer, RED, (_x, _y, 3, 3))
        # moving
        if self.xvel != 0:
            self.xvel -= self.air_resistance if self.xvel > 0 else -self.air_resistance
        self.yvel += self.gravity
        self.x += self.xvel * sign
        self.y += self.yvel * sign
        # prevent stepping through bullets
        self.last_x = self.x
        self.last_y = self.y

    @property
    def _rect(self):
        return pygame.Rect((self.x, self.y), self.size)

    def collide_blocks(self):  # projectile collide
        # blocks
        for block, rect in g.player.block_data:
            name = block.name
            if rect.clipline((self.x, self.y), (self.last_x, self.last_y)):
                self.active = False
        else:
            travelled = hypot(self.x - self.sx, self.y - self.sy)
            if travelled >= 500:
                all_projectiles.remove(self)

    def collide_player(self):
        if not self.active:
            if self._rect.colliderect(g.player._rect):
                if self.name is not None:
                    g.player.new_block(self.name)
                    all_projectiles.remove(self)


class Drop(Scrollable):
    def __init__(self, name, rect, extra=None, offset=True):
        Scrollable.__init__(self, g)
        self.name = name
        if extra is None:
            self.drop_amount = 1
        elif isinstance(extra, int):
            self.drop_amount = extra
        self.image = T(scale2x(g.w.surf_assets["blocks"][name]))
        self.width, self.height = self.image.width, self.image.height
        self._rect = self.image.get_rect(topleft=rect.topleft)
        self._rect.x += rect.width / 2 - self.width / 3 / 2
        self._rect.y += rect.height / 2 - self.width / 3 / 2
        if offset:
            self._rect.topleft = [r + rand(0, 0) for r in self._rect.topleft]
        self.og_pos = self._rect.center
        self.sin = rand(0, 500)

    # drop update
    def update(self):
        # doesnt work for scaled blitting past leo what an idiot you are not we cant emulate sine waves dumbass you think this was gud idear
        self._rect.centery = self.og_pos[1] + sin(ticks() * 0.001 * 2 * pi * 0.5 + self.sin) * 5
        win.renderer.blit(self.image, self.rect)
        if pw.show_hitboxes:
            draw_rect(win.renderer, RED, self.rect)

    def kill(self):
        all_drops.remove(self)


class SlidePopup:
    def __init__(self, text):
        self.font = orbit_fonts[12]
        self.image = pygame.Surface(self.font.size(text), pygame.SRCALPHA)
        write(self.image, "center", text, self.font, BLACK, *[s / 2 for s in self.image.get_size()])
        self.rect = self.image.get_rect(center=(win.width - 110, 100))
        self.alpha = 255

    def update(self):
        self.rect.y -= 1
        self.alpha -= 2
        self.image.set_alpha(self.alpha)
        if self.alpha <= 0:
            self.kill()


class BreakingBlockParticle:
    def __init__(self, name, pos):
        try:
            self.image = g.w.blocks[non_bg(name)]
            self.width = self.image.get_width()
            self.height = self.image.get_height()
            self.image = scale(self.image, (self.width // 4, self.height // 4))
        except AttributeError:
            self.image = name.copy()
        self.rect = self.image.get_rect(center=pos)
        self.xvel = rand(-2, 2)
        self.yvel = -3
        self.start_time = ticks()

    def update(self):
        self.yvel += 0.3
        self.rect.x += self.xvel
        self.rect.y += self.yvel
        if ticks() - self.start_time >= 200:
            self.kill()


class MiscParticle:
    def __init__(self, pos, radius, shrinkage, color, rot=0, speed=0, fade=0):
        self.x, self.y = pos
        self.angle = 0
        self.radius = radius
        self.shrinkage = shrinkage
        self.rot = rot
        self.speed = speed
        self.color = color
        self.fade = fade

    def update(self):
        self.xvel, self.yvel = angle_to_vel(self.angle, self.speed)
        self.x += self.xvel
        self.y += self.yvel
        self.radius -= self.shrinkage
        if self.radius <= 0:
            all_other_particles.remove(self)
        pygame.gfxdraw.filled_circle(win.renderer, int(self.x), int(self.y), int(self.radius), (255, 120, 120, 120))


class FollowParticle:
    def __init__(self, img, start_pos, end_pos):
        self.image = img
        self.x, self.y = start_pos
        self.end_x, self.end_y = [int(p) for p in end_pos]
        self.xvel, self.yvel = two_pos_to_vel(start_pos, end_pos)

    def draw(self):
        win.renderer.blit(self.image, (self.x, self.y))

    def update(self):
        self.x += self.xvel
        self.y += self.yvel
        if int(self.x) == self.end_x and int(self.y) == self.end_y:
            all_other_particles.remove(self)
        self.draw()


class FracDistParticle:
    def __init__(self, level):
        self.alpha = 0
        self.x = 40
        self.y = -127
        self.y += 33 + level * 33
        self.image = gas_sprs[level]
        self.rect = self.image.get_rect()
        self.step = 0
        self.xvel = 0
        self.xacc = 0.2
        self.aacc = 10
        self.direc = 1
        self.gas = gas_blocks[level]

    @property
    def mbr(self):
        return g.midblit_rect()

    def draw(self):
        win.renderer.blit(self.image, self.rect)

    def movex(self, amount):
        self.x += amount
        self.step += amount

    def update(self):
        # move
        if self.direc == 1:
            self.xvel += self.xacc
            self.alpha += self.aacc
            self.movex(self.xvel)
            if self.alpha >= 255:
                self.alpha = 255
                self.direc = -1
        elif self.direc == -1:
            self.xacc = -0.005
            self.aacc = -5
            self.xvel += self.xacc
            self.alpha += self.aacc
            self.movex(self.xvel)
            if self.alpha <= 0:
                self.alpha = 0
                all_gases.remove(self)
                g.mb.frac_dist[self.gas] += 1
        self.image.alpha = self.alpha
        # update rect
        self.rect.topleft = (self.mbr.x + self.x, self.mbr.y + self.y)
        # draw (final lel tback)
        self.draw()


class Cloud:
    def __init__(self, index):
        self.index = index
        self.image = clouds[index]
        self.width, self.height = self.image.get_size()
        self.x = -self.width
        self.y = rand(-30, 70)
        self.xvel = randf(0.05, 0.4)

    def draw(self):
        win.renderer.blit(self.image, (self.x, self.y))
        if pw.show_hitboxes:
            (win.renderer, RED, (self.x, self.y, *self.image.get_size()), 1)

    def update(self):
        self.x += self.xvel
        self.draw()


class OrbParticle:
    def __init__(self, og_offset, color, wait=0):
        self.image = iimgload("assets", "Images", "Visuals", "monk_orb.png", after_func=None)
        self.image.color = color
        self.angle = 0
        self.og_offset = pos[:]
        self.rect = pygame.Rect((g.player.rect.x + self.og_offset[0], g.player.rect.y + self.og_offset[1]), (3 * 20, 3 * 20))
        self.dash = False
        self.t = 0
        self.log = lambda x: genlog(x, 0, 1.6, 0.6, 5.6, 0.8, 0.3)
        self.wait = wait
        self.last = None
        self.go = False
        self.follow = True

    def move(self):
        if self.follow:
            # m = 0.5
            # self.rect.x += (self.og_offset[0] - self.rect.x) * m
            # self.rect.y += (self.og_offset[1] - self.rect.y) * m
            pass
        else:
            self.angle += (45 - self.angle) * 0.1
            self.image.angle = self.angle
            if self.angle >= 43:
                self.dash = True
            if self.dash:
                if self.last is None:
                    self.last = ticks()
                if ticks() - self.last < self.wait:
                    return
                self.t += 0.4
                self.rect.x = self.og_pos[0] + self.log(self.t) * 100

    def draw(self):
        win.renderer.blit(self.image, self.rect)

    def update(self):
        self.draw()
        self.move()


class ShatterParticle(Scrollable):
    def __init__(self, entity, area, blood=False):
        super().__init__(g)
        self.blood = blood
        self.entity = entity
        #
        if not self.blood:
            self.area = area
            self.image = entity.image
            self._rect = pygame.Rect((0, 0), self.area[2:])
            self.width, self.height = area[2:]
            self.x, self.y = entity._rect.center
        else:
            self.width, self.height = 2, 2
            surf = pygame.Surface((self.width, self.height))
            surf.fill(RED)
            self.image = T(surf)
            self.area = pygame.Rect(0, 0, self.width, self.height)
            self._rect = self.image.get_rect()
            self.x = rand(entity._rect.left, entity._rect.right)
            self.y = rand(entity._rect.top, entity._rect.bottom)
        #
        self._rect.center = self.x, self.y
        self._rects = entity.final_rects
        self.syvel = self.yvel = randf(-3.5, -4)
        self.yacc = 0.08
        self.energy = self.yvel
        # self.xvel = 0
        self.xvel = randf(-0.5, 0.5)
        self.drops = entity.drops
        self.bounces = 0
        self.last = ticks()

    def update(self):
        self.x += self.xvel
        self.yvel += self.yacc
        self.y += self.yvel
        self._rect.topleft = (int(self.x), int(self.y))
        # for _rect in self._rects:
        #     if self._rect.colliderect(_rect):
        #         self.y = _rect.top - self.height
        #         self.energy *= 0.6
        #         self.yvel = self.energy
        #         self.bounces += 1
        #         if self.bounces == 4:
        #             all_other_particles.remove(self)
        self._rect.topleft = (int(self.x), int(self.y))
        win.renderer.blit(self.image, self.rect, area=self.area)
        if ticks() - self.last >= 1250:
            # drop the loot (only the first time) (and only when is kein blood particle)
            if not self.blood:
                if self.entity not in g.w.entities[self.entity.chunk_index]:
                    return
                g.w.entities[self.entity.chunk_index].remove(self.entity)
                for drop, amount in self.entity.drops.items():
                    all_drops.append(Drop(drop, self.entity._rect, amount))
            all_other_particles.remove(self)


class BloodParticle(ShatterParticle):
    def __init__(self, entity):
        super().__init__(entity, None, blood=True)


class OrbMatrix:
    def __init__(self, pos_function):
        self.orbs = [timgload3("assets", "Images", "Visuals", "monk_orb.png") for _ in range(3)]
        for index, orb in enumerate(self.orbs):
            orb.color = (GREEN, WATER_BLUE, PURPLE)[index]
        self.offsets = [[0, -1], [1, 1], [-1, 1]]
        self.mult = 50
        self.rects = [pygame.Rect(0, 0, self.orbs[0].width, self.orbs[0].height) for _ in range(3)]
        self.pos_function = pos_function
        self.switching = False
        self.aiming_for = [(0, 0) for _ in range(3)]

    def move(self):
        if not self.switching:
            pass
        else:
            speed = 0.02
            for offset, aiming_for in zip(self.offsets, self.aiming_for):
                dx = (aiming_for[0] - offset[0]) * speed
                dy = (aiming_for[1] - offset[1]) * speed
                offset[0] += dx
                offset[1] += dy
        for index in range(len(self.orbs)):
            pos = list(self.pos_function())
            pos[0] += self.offsets[index][0] * self.mult
            pos[1] += self.offsets[index][1] * self.mult
            self.rects[index].center = pos

    def draw(self):
        for index in range(len(self.orbs)):
            orb = self.orbs[index]
            rect = self.rects[index]
            win.renderer.blit(orb, rect)

    def switch(self):
        self.switching = True
        self.current = self.offsets.copy()
        for index, rect in enumerate(self.rects):
            try:
                self.aiming_for[index] = self.current[index + 1].copy()
            except IndexError:
                self.aiming_for[index] = self.current[0].copy()

    def update(self):
        self.move()
        self.draw()


class OrbMatrix:
    def __init__(self, pos_function):
        self.img = timgload3("assets", "Images", "Visuals", "monk_orb.png")
        self.oimg = timgload3("assets", "Images", "Visuals", "monk_orb.png")
        self.oimg.color = RED
        self.pos_function = pos_function
        self.x = self.y = 0
        self.r = 60
        self.num_imgs = 3
        self.speed = 5
        self.switching = False
        self.offset = 0
        self.inc = True
        self.vel = 0.01
        self.cap = 5

    def move(self):
        if self.switching:
            pass

    def draw(self):
        return
        self.x, self.y = self.pos_function()
        angle = 0
        #
        if self.inc:
            if self.offset + self.vel <= self.cap:
                self.offset += self.vel
            else:
                self.inc = False
        if not self.inc:
            if self.offset - self.vel >= 0:
                self.offset -= self.vel
            else:
                self.inc = True
        #
        for i in range(self.num_imgs):
            angle = (i + 1) / self.num_imgs * 2 * pi + self.offset
            x = self.x + self.r * sin(self.speed * ticks() / 10000 * 2 * pi + angle)
            y = self.y - self.r * cos(self.speed * ticks() / 10000 * 2 * pi + angle)
            rect = pygame.Rect(x, y, self.img.width, self.img.height)
            win.renderer.blit(self.img, rect)
            angle = (i + 1) / self.num_imgs * 2 * pi
            x = self.x + self.r * sin(self.speed * ticks() / 10000 * 2 * pi + angle)
            y = self.y - self.r * cos(self.speed * ticks() / 10000 * 2 * pi + angle)
            rect = pygame.Rect(x, y, self.img.width, self.img.height)
            win.renderer.blit(self.oimg, rect)

    def switch(self):
        self.switching = True

    def update(self):
        self.move()
        self.draw()


class Spark:
    def __init__(self, loc, angle, speed, color, scale=1):
        self.loc = loc
        self.angle = angle
        self.speed = speed
        self.scale = scale
        self.color = color
        self.alive = True

    def point_towards(self, angle, rate):
        rotate_direction = ((angle - self.angle + math.pi * 3) % (math.pi * 2)) - math.pi
        try:
            rotate_sign = abs(rotate_direction) / rotate_direction
        except ZeroDivisionError:
            rotate_sing = 1
        if abs(rotate_direction) < rate:
            self.angle = angle
        else:
            self.angle += rate * rotate_sign

    def calculate_movement(self, dt):
        return [math.cos(self.angle) * self.speed * dt, math.sin(self.angle) * self.speed * dt]

    # gravity and friction
    def velocity_adjust(self, friction, force, terminal_velocity, dt):
        movement = self.calculate_movement(dt)
        movement[1] = min(terminal_velocity, movement[1] + force * dt)
        movement[0] *= friction
        self.angle = math.atan2(movement[1], movement[0])
        # if you want to get more realistic, the speed should be adjusted here

    def update(self, dt=1):
        movement = self.calculate_movement(dt)
        self.loc[0] += movement[0]
        self.loc[1] += movement[1]

        # a bunch of options to mess around with relating to angles...
        #self.point_towards(math.pi / 2, 0.02)
        #self.velocity_adjust(0.975, 0.2, 8, dt)
        #self.angle += 0.1

        self.speed -= 0.1

        if self.speed <= 0:
            self.alive = False

        self.draw()

    def draw(self, offset=[0, 0]):
        if self.alive:
            points = [
                [self.loc[0] + math.cos(self.angle) * self.speed * self.scale, self.loc[1] + math.sin(self.angle) * self.speed * self.scale],
                [self.loc[0] + math.cos(self.angle + math.pi / 2) * self.speed * self.scale * 0.3, self.loc[1] + math.sin(self.angle + math.pi / 2) * self.speed * self.scale * 0.3],
                [self.loc[0] - math.cos(self.angle) * self.speed * self.scale * 3.5, self.loc[1] - math.sin(self.angle) * self.speed * self.scale * 3.5],
                [self.loc[0] + math.cos(self.angle - math.pi / 2) * self.speed * self.scale * 0.3, self.loc[1] - math.sin(self.angle + math.pi / 2) * self.speed * self.scale * 0.3],
            ]
            fill_quad(win.renderer, self.color, *points)


class InfoBox:
    def __init__(self, texts, pos=None, index=0):
        # init
        self.padding = 20
        self.index = index
        text = texts[self.index]
        self.og_text = text
        self.texts = texts
        self.text = ""
        self.pos = pos if pos is not None else (win.width / 2, win.height / 2 - 100)
        self.font = orbit_fonts[16]
        # self image
        self.image = pygame.Surface([s + self.padding for s in self.font.size(text)], pygame.SRCALPHA)
        br = 10
        self.rect = self.image.get_rect(topleft=self.pos)
        self.width, self.height = self.rect.size
        # continue image
        self.con_image = pygame.Surface((80, 30), pygame.SRCALPHA)
        br = 10
        self.con_rect = self.con_image.get_rect(topright=(self.rect.right, self.rect.bottom))
        # rest
        self.alpha = 0
        self.bg_alpha = ceil(255 / 4)
        self.last_init = float("inf")
        self.can_skip = False
        self.show()

    def update(self):
        win.renderer.blit(self.image, self.rect)
        text_surf, text_rect = write(win.renderer, "topleft", self.text, self.font, BLACK, *[p + self.padding / 2 for p in self.rect.topleft], blit=False)
        # text_surf.set_alpha(self.alpha * (255 / self.bg_alpha))
        win.renderer.blit(text_surf, text_rect)
        if epoch() - self.last_init >= 1:
            # self.con_image.set_alpha(self.alpha)
            win.renderer.blit(self.con_image, self.con_rect)
            text_surf, text_rect = write(win.renderer, "topleft", "[SPACE]", orbit_fonts[12], BLACK, *[p + self.padding / 2 for p in self.con_rect.topleft], blit=False)
            # text_surf.set_alpha(self.alpha * (255 / self.bg_alpha))
            win.renderer.blit(text_surf, text_rect)

    def process_event(self, event):
        if event.type == KEYDOWN:
            if event.key == K_SPACE:
                if self.can_skip:
                    with suppress(IndexError):
                        group(InfoBox(self.texts, self.pos, self.index + 1), all_foreground_sprites)
                    all_foreground_sprites.remove(self)

    def show(self):
        def _show():
            for _ in range(self.bg_alpha):
                # self.image.set_alpha(self.alpha)
                time.sleep(WOOSH_TIME * 6)
                self.alpha += 1
            self.characterize()
            self.can_skip = True
        CThread(target=_show).start()

    def characterize(self):
        def _characterize():
            for char in self.og_text:
                self.text += char
                time.sleep(WOOSH_TIME * 30)
            self.last_init = epoch()
        CThread(target=_characterize).start()


class WorldButton:
    def __init__(self, world, pos, text_color=BLAC):
        # init
        self.world = world
        self.text_color = text_color
        self.world_name = world.name
        w, h = orbit_fonts[20].size(self.world_name)
        w, h = 120, g.worldbutton_pos_ydt - 5
        w, h = MHL / 2, MVL / 2
        w, h = wb_icon_size
        # image
        #self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        #(self.image, LIGHT_BROWN, (0, 0, *self.image.get_size()), 0, 10, 10, 10, 10)
        #(self.image, DARK_BROWN, (0, 0, *self.image.get_size()), 2, 10, 10, 10, 10)
        #self.image.set_colorkey(BLACK)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        br = 12
        pygame.draw.rect(self.image, (200, 200, 200, 255), (0, 0, w, h), 0, br)
        pygame.draw.rect(self.image, BLACK, (0, 0, w, h), 2, br)
        # self.image.fill((40, 40, 40, 40))
        br = 3
        write(self.image, "bottomleft", self.world_name, orbit_fonts[20], self.text_color, 5, self.image.get_height() - 3)
        # rest
        self.rect = self.image.get_rect(topleft=pos)
        self.image = T(self.image)
        self.o = 0

    def update(self):
        self.draw()
        self.preview()

    def draw(self):
        win.renderer.blit(self.image, self.rect)

    def preview(self):
        if self.rect.collidepoint(g.mouse):
            self.o += 0.25
            xo, yo = g.mouse[0] - self.rect.x, g.mouse[1] - self.rect.y
            topleft = (xo / self.rect.width * (self.bg_rect.width - self.rect.width), yo / self.rect.height * (self.bg_rect.height - self.rect.height))
            area = pygame.Rect(*topleft, topleft[0] + self.rect.width, topleft[1] + self.rect.height)
            self.blit_rect = pygame.Rect(self.rect.topleft, self.rect.size)
            area = pygame.Rect(0 + int(self.o), 0 + int(self.o), self.rect.width + int(self.o), self.rect.height + int(self.o))
            area = pygame.Rect(100, 100, 100 + self.rect.width, 100 + self.rect.height)
            win.renderer.blit(self.bg, self.blit_rect, area=area)

    def init_bg(self, bg, username):
        bgw, bgh = bg.get_size()
        self.image.blit(bg, (0, 0))
        write(self.image, "midtop", username, orbit_fonts[11], BLACK, bgw / 2, 3)
        self.data["bg"] = deepcopy(SmartSurface.from_surface(bg))
        self.data["bg_size"] = bg.get_size()

    def overwrite(self, inputtext, name=False):
        if name:
            g.p.world_names.remove(self.data["world"])
            g.p.world_names.append(inputtext)
            self.data["world"] = inputtext
        w, h = orbit_fonts[20].size(str(inputtext))
        self.image = pygame.Surface((w + 10, h + 10), pygame.SRCALPHA)
        (self.image, LIGHT_BROWN, (0, 0, *self.image.get_size()), 0, 10, 10, 10, 10)
        (self.image, DARK_BROWN, (0, 0, *self.image.get_size()), 2, 10, 10, 10, 10)
        write(self.image, "center", inputtext, orbit_fonts[20], self.text_color, *[s / 2 for s in self.image.get_size()])
        self.rect = self.image.get_rect(topleft=self.rect.topleft)


class WorldIcon:
    def __init__(self, data):
        self.image = pygame.Surface((200, 50))
        self.rect = self.image.get_rect(topleft=data)
        self.image = T(self.image)

    def draw(self):
        win.renderer.blit(self.image, self.rect)

    def update(self):
        self.draw()


class StaticWidget:
    def __init__(self, grp, visible_when):
        group(self, grp)
        self.visible_when = visible_when

    def __after_init__(self, alpha=None):
        self.image = T(self.image)
        if alpha is not None:
            self.image.alpha = alpha

    def draw(self):
        win.renderer.blit(self.image, self.rect)

    def update(self):
        self.draw()
        if hasattr(self, "spec_update"):
            self.spec_update()
        # self.check_selected()
        # self.spec_update()

    def check_selected(self):
        o = 3
        if self.selected:
            draw_rect(win.renderer, ORANGE, self.rect)


class StaticButton(StaticWidget):
    def __init__(self, text, pos, group, bg_color=WHITE, text_color=BLAC, anchor="center", size="icon", shape="rect", command=None, visible_when=None, selected=False):
        StaticWidget.__init__(self, group, visible_when)
        self.selected = selected
        self.text = text
        if size == "world":
            tw, th = 300, 24
        elif size == "main":
            tw, th = 225, 24
        else:
            tw, th = orbit_fonts[20].size(text)
        w, h = tw + 10, th + 10
        self.sw = sw = 20
        self.width, self.height = w, h
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        # (self.image, bg_color, (0, 0, *self.image.get_size()), 0, 10, 10, 10, 10)
        # (self.image, DARK_BROWN, (0, 0, *self.image.get_size()), 2, 10, 10, 10, 10)
        # br = 6
        # if shape == "rect":
        #     self.image.fill(bg_color)
        # elif shape == "crect":
            # pygame.draw.rect(self.image, bg_color, (0, 0, *self.image.get_size()), 0, br, br, br, br)
        # self.text_color = text_color
        if shape == "sharp":
            wx = w / 2 + sw / 2
            wy = h / 2
        else:
            wx, wy = w / 2, h / 2
        self.rect = self.image.get_rect()
        self.command = command
        self.orange = 0
        setattr(self.rect, anchor, pos)
        super().__after_init__()

    def spec_update(self):
        if self.rect.collidepoint(g.mouse):
            self.orange += 0.06 * (self.width - self.orange)
        else:
            self.orange += 0.06 * -self.orange
        # draw
        fill_rect(win.renderer, LIGHT_GRAY, self.rect)
        fill_rect(win.renderer, DARKISH_GREEN, (self.rect.x, self.rect.y, self.orange, self.height))
        draw_quad(win.renderer, BLACK,
            (self.rect.x, self.rect.y),
            (self.rect.x + self.sw, self.rect.y + self.height),
            (self.rect.x + self.width, self.rect.y + self.height),
            (self.rect.x + self.width - self.sw, self.rect.y)
        )
        fill_triangle(win.renderer, LIGHT_GRAY,
            (self.rect.x - 1, self.rect.y),
            (self.rect.x - 1, self.rect.y + self.height),
            (self.rect.x - 1 + self.sw, self.rect.y + self.height)
        )
        fill_triangle(win.renderer, LIGHT_GRAY,
            (self.rect.x + 1 + self.width - self.sw, self.rect.y),
            (self.rect.x + 1 + self.width, self.rect.y),
            (self.rect.x + 1 + self.width, self.rect.y + self.height)
        )
        # write
        write(win.renderer, "center", self.text, orbit_fonts[20], BLACK, *self.rect.center, tex=True)

    def process_event(self, event):
        if is_left_click(event):
            if is_drawable(self):
                if self.rect.collidepoint(g.mouse):
                    self.command()


class StaticToggleButton(StaticWidget):
    def __init__(self, cycles, pos, group, bg_color=WHITE, text_color=BLACK, anchor="center", command=None, visible_when=None, selected=False):
        StaticWidget.__init__(self, group, visible_when)
        self.selected = selected
        self.cycles = cycles
        self.cycle = 0
        w, h = [5 + size + 5 for size in orbit_fonts[20].size(str(self.cycles[self.cycle]))]
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        #self.image.fill(bg_color)
        (self.image, LIGHT_BROWN, (0, 0, *self.image.get_size()), 0, 10, 10, 10, 10)
        (self.image, DARK_BROWN, (0, 0, *self.image.get_size()), 2, 10, 10, 10, 10)
        self.text_color = text_color
        write(self.image, "topleft", self.cycles[self.cycle], orbit_fonts[20], self.text_color, 5, 5)
        self.rect = self.image.get_rect()
        self.command = command
        setattr(self.rect, anchor, pos)
        super().__after_init__()

    def process_event(self, event):
        if is_left_click(event):
            if is_drawable(self):
                if self.rect.collidepoint(g.mouse):
                    self.command()

    def overwrite(self, text):
        w, h = [5 + size + 5 for size in orbit_fonts[20].size(str(self.cycles[self.cycle]))]
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        (self.image, LIGHT_BROWN, (0, 0, *self.image.get_size()), 0, 10, 10, 10, 10)
        (self.image, DARK_BROWN, (0, 0, *self.image.get_size()), 2, 10, 10, 10, 10)
        write(self.image, "topleft", text, orbit_fonts[20], self.text_color, 5, 5)


class StaticOptionMenu(StaticWidget):
    def __init__(self, options, default, pos, group, bg_color=WHITE, text_color=BLACK, anchor="center", visible_when=None):
        StaticWidget.__init__(self, group, visible_when)
        self.options = options
        self.default = default
        w, h = orbit_fonts[20].size(str(default))
        self.image = SmartSurface((w + 40, h + 10), pygame.SRCALPHA)
        w, h = self.image.get_size()
        (self.image, bg_color, (0, 0, *self.image.get_size()), 0, 10, 10, 10, 10)
        (self.image, DARK_BROWN, (0, 0, *self.image.get_size()), 2, 10, 10, 10, 10)
        write(self.image, "midleft", default, orbit_fonts[20], BLACK, 5, h / 2)
        self.image.cblit(rotozoom(triangle(12), 180, 1), (w - 20, h / 2))
        self.og_img = self.image.copy()
        self.rects = []
        self.rect = self.image.get_rect()
        setattr(self.rect, anchor, pos)
        y = self.rect.y
        for option in options:
            self.rects.append(pygame.Rect(self.rect.x, y, w, h))
            y += h
        self.surf = pygame.Surface((w, h * (len(options) + 5)), pygame.SRCALPHA)
        (self.surf, bg_color, (0, 0, *self.surf.get_size()), 0, 10, 10, 10, 10)
        (self.surf, DARK_BROWN, (0, 0, *self.surf.get_size()), 2, 10, 10, 10, 10)
        self.opened = False
        super().__after_init__()

    def process_event(self, event):
        if is_left_click(event):
            if self.rect.collidepoint(g.mouse):
                self.opened = not self.opened

    def update(self):
        if self.opened:
            self.image = self.surf
        else:
            self.image = self.og_img
            if self.rect.collidepoint(g.mouse):
                self.image.set_alpha(150)
            else:
                self.image.set_alpha(255)


class MessageboxWorld:
    def __init__(self, world):
        # initialization
        self.world = world
        self.image = SmartSurface((300, 200))
        bg_color = list(DARKISH_GREEN)[:3] + [130]
        self.image.fill(bg_color)
        self.rect = self.image.get_rect(topleft=(win.width / 2 - 150, win.height / 2 - 100))
        self.text_height = orbit_fonts[20].size("J")[1]
        self.bred_size = (self.rect.width / 2 - 15, self.text_height + 10)
        box = pygame.Surface(self.bred_size)
        self.bred_writing_pos = (box.get_width() / 2, box.get_height() / 2)
        (self.image, DARKISH_GREEN, (0, 0, *self.image.get_size()), 4)
        self.close_rects = {}
        # close boxes
        write(self.image, "midtop", "?", orbit_fonts[30], BLACK, self.rect.width / 2, 5)
        w, h = self.image.get_size()
        self.get_box("Info", (10, h - 90), "bottomleft")
        self.get_box("Download", (10, h - 50), "bottomleft")
        self.get_box("Rename", (w - 10, h - 50), "bottomright")
        self.get_box("Open", (10, h - 10), "bottomleft")
        self.get_box("Delete", (w - 10, h - 10), "bottomright")
        self.image = T(self.image)
        # animation
        # Thread(target=self.zoom, args=["in"]).start()

    def draw(self):
        win.renderer.blit(self.image, self.rect)

    def update(self):
        self.draw()

    @property
    def path(self):
        return path(".game_data", "worlds", self.world.name + ".dat")

    def get_box(self, text, pos, anchor):
        box = pygame.Surface(self.bred_size, pygame.SRCALPHA)
        bred_size = box.get_size()
        self.close_rects[text.lower()] = box.get_rect(**{anchor: [m + p for m, p in zip(self.rect.topleft, pos)]})
        (box, CREAM, (0, 0, *self.bred_size))
        (box, LIGHT_GRAY, (0, 0, *self.bred_size), 4)
        write(box, "center", text, orbit_fonts[20], BLACK, *self.bred_writing_pos)
        self.image.cblit(box, pos, anchor)

    def zoom(self, type_):
        og_img = self.image.copy()
        og_size = og_img.get_size()
        if type_ == "in":
            for i in range(20):
                size = [round((fromperc((i + 1) * 5, s))) for s in og_size]
                self.image = scale(og_img, size)
                self.rect = self.image.get_rect()
                self.rect.center = (win.width / 2, win.height / 2)
                time.sleep(WOOSH_TIME)
        elif type_ == "out":
            for i in reversed(range(20)):
                size = [round(fromperc((i + 1) * 5, s)) for s in og_size]
                self.image = scale(og_img, size)
                self.rect = self.image.get_rect()
                self.rect.center = (win.width / 2, win.height / 2)
                time.sleep(WOOSH_TIME)
            all_messageboxes.remove(self)

    def close(self, option):
        if option == "info":
            MessageboxOk(win.renderer, "\n", **pw.widget_kwargs)

        elif option == "download":
            with open(self.path, "rb") as f:
                world_data = pickle.load(f)
            dir_ = tkinter.filedialog.asksaveasfilename()
            name = dir_.split(".")[0]
            with open(name + ".dat", "wb") as f:
                pickle.dump(world_data, f)

        elif option == "rename":
            def rename(ans_rename):
                if ans_rename is not None:
                    if ans_rename != "":
                        if ans_rename not in g.p.world_names:
                            try:
                                open(path("tempfiles", ans_rename + ".txt"), "w").close()
                                os.remove(path("tempfiles", ans_rename + ".txt"))
                            except Exception:
                                MessageboxError(win.renderer, "World name is invalid.", **pw.widget_kwargs)
                            else:
                                os.rename(path(".game_data", "worlds", self.data["world"] + ".dat"), path(".game_data", "worlds", ans_rename + ".dat"))
                                for button in all_home_world_world_buttons:
                                    if button.data["world"] == self.data["world"]:
                                        button.overwrite(ans_rename, True)
                                        button.data["world_obj"].name = ans_rename
                                        break
                        else:
                            MessageboxError(win.renderer, "A world with the same name already exists.", **pw.widget_kwargs)
                    else:
                        MessageboxError(win.renderer, "World name is invalid.", **pw.widget_kwargs)

            Entry(win.renderer, "Rename world to:", rename, **pw.entry_kwargs)

        elif option == "open":
            with open(self.path, "rb") as f:
                # world assets
                g.w = pickle.load(f)
                # terrain
                init_world("existing")
                # general
                destroy_widgets()
                g.menu = False

        elif option == "delete":
            delete_file(path(".game_data", "worlds", self.data["world"] + ".dat"))
            g.p.world_names.remove(self.data["world"])
            for button in all_home_world_world_buttons:
                if button.rect.y > self.data["pos"][1]:
                    button.rect.y -= g.worldbutton_pos_ydt
                    button.data["pos"][1] -= g.worldbutton_pos_ydt
                elif button.data == self.data:
                    button.kill()
            g.p.next_worldbutton_pos[1] -= g.worldbutton_pos_ydt

        elif g.debug:
            raise ValueError(f"'{option}'")

        all_messageboxes.remove(self)


# I N I T I A L I Z I N G  S P R I T E S -------------------------------------------------------------- #
anim = Animations()
visual = Visual()
ui = UI()
pw = PlayWidgets()
g.w = World()
perlin = Perlin(g.w.rng)

# le button
_a, _b = 23, 25
button_cnw = StaticButton("Create New World",  (_a * 1 + _b, win.height - 200),        all_home_world_static_buttons, LIGHT_BROWN, anchor="topleft", size="world", command=new_world,                          visible_when=pw.is_worlds_worlds)
button_lw =  StaticButton("Load World",        (_a * 2 + _b, win.height - 160),        all_home_world_static_buttons, LIGHT_BROWN, anchor="topleft", size="world", command=pw.button_lw_command,               visible_when=pw.is_worlds_worlds)
button_jw =  StaticButton("Join World",        (_a * 3 + _b, win.height - 120),        all_home_world_static_buttons, LIGHT_BROWN, anchor="topleft", size="world", command=pw.button_jw_command,               visible_when=pw.is_worlds_worlds)
button_daw = StaticButton("Delete All Worlds", (_a * 4 + _b, win.height - 80),         all_home_world_static_buttons, LIGHT_BROWN, anchor="topleft", size="world", command=pw.button_daw_command,              visible_when=pw.is_worlds_worlds)
button_c =   StaticButton("Credits",           (35, 130),                            all_home_settings_buttons,     LIGHT_BROWN, anchor="topleft",               command=pw.show_credits_command,            visible_when=pw.is_worlds_static)
button_i =   StaticButton("Intro",             (35, 170),                            all_home_settings_buttons,     LIGHT_BROWN, anchor="topleft",               command=pw.intro_command,                   visible_when=pw.is_worlds_static)
button_ct =  StaticButton("Custom Textures",   (35, 210),                            all_home_settings_buttons,     LIGHT_BROWN, anchor="topleft",               command=pw.custom_textures_command,         visible_when=pw.is_worlds_static)
button_s =   StaticButton("Settings",          (win.width / 2, win.height / 2),      all_home_sprites,              WHITE, anchor="center", size="main",         command=pw.set_home_stage_settings_command, visible_when=pw.is_home)
button_w =   StaticButton("Worlds",            (win.width / 2, win.height / 2 + 50), all_home_sprites,              WHITE, anchor="center", size="main",         command=pw.set_home_stage_worlds_command,   visible_when=pw.is_home)

# la protocola
controller.button_protocol |= {
    #
    button_s: button_w,
    button_w: button_s,
    #
    button_cnw: button_lw,
    button_lw: button_daw,
    button_daw: button_cnw,
}
controller.next_protocol |= {
    button_w: button_cnw,
}

# L O A D I N G  T H E  G A M E ----------------------------------------------------------------------- #
# load le button
make_sure_dir_exists(path(".game_data", "worlds"))
make_sure_dir_exists(path(".game_data", "tempfiles"))
for y, world_file in enumerate(os.listdir(path(".game_data", "worlds"))):
    world_name, _ = os.path.splitext(world_file)
    part = WorldPartition(name=world_name)
    pos = (45, 100 + y * g.worldbutton_pos_ydt)
    button = WorldButton(part, pos)
    group(button, all_home_world_world_buttons)

# debugging stuff
late_rects = []
late_pixels = []
late_lines = []
late_imgs = []
last_qwe = perf_counter()

#
thread_active = False
light_surf = None
light_tex = None
light_rect = None


# M A I N  L O O P ------------------------------------------------------------------------------------ #
async def main(debug, cprof=False):
    with nullcontext() if debug else redirect_stdout(open(os.devnull, "w")):
        # cursors
        # set_cursor_when(pygame.SYSTEM_CURSOR_CROSSHAIR, lambda: g.stage == "play")
        corner_cursor = get_binary_cursor(
            ["xxx          xxx",
             "x              x",
             "x              x",
             "                ",
             "                ",
             "                ",
             "       xx       ",
             "      x  x      ",
             "      x  x      ",
             "       xx       ",
             "                ",
             "                ",
             "                ",
             "x              x",
             "x              x",
             "xxx          xxx"],
        (8, 8)
        )
        # pygame.mouse.set_cursor(corner_cursor)
        # initializing lasts
        last_rain_partice = ticks()
        last_snow_particle = ticks()
        last_gunfire = ticks()
        last_cloud = ticks()
        last_s = ticks()
        # dynamic stuff
        music_count = None
        # counts
        g.stage = "home"
        # end signals
        pass
        # loop
        running = True
        pritn()
        loading_time = round(perf_counter(), 2)
        g.p.loading_times.append(loading_time)
        pritn(f"Loaded in: {loading_time}s")
        pritn(f"Average loading time: {round(g.p.loading_times.mean, 2)}s")
        pritn()
        # PyMunk
        balls = []
        strings = []
        # game loop
        anim_index = 0
        fpss = []
        last_fps_update = ticks()
        shown_fps = bottom_1p_avg = "0"
        fps_resetted = False
        started = ticks()
        poly = Crystal(win.renderer, "Battleaxe.obj", [], [], [], (940, 300), 140, 1, 0.2, 0.2, 0.3, 0.01, 0.01, 0.01, normalize=True)
        # pygame.mouse.set_visible(False)
        # light.blend_mode = pygame.BLEND_RGBA_MULT
        i = 0
        yyy = 0

        # lighting debug station lapland
        bliss = timgload("bliss.png")
        bliss_rect = bliss.get_rect()
        r = 200
        surf = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
        layers = 25
        glow = 11
        for i in range(layers):
            k = i * glow
            k = clamp(k, 0, 255)
            pygame.draw.circle(
                surf, (k, k, k), surf.get_rect().center, r - i * 3
            )
        big_surf = pygame.Surface((win.width, win.height), pygame.SRCALPHA)
        big_surf.fill(BLACK)
        big_surf.blit(surf, (win.width // 2 - r, win.height // 2 - r))
        tex = T(big_surf)
        tex.blend_mode = pygame.BLEND_RGBA_MULT
        # tex.blend_mode = pygame.BLEND_RGBA_MULT

        # mist station jamayèn
        ...

        # cantaloop
        while running:
            # group(Spark(list(pygame.mouse.get_pos()), rand(0, 360), 2, WHITE, 3), all_other_particles)
            # init dynamic constants
            mouse = pygame.mouse.get_pos()
            mouses = pygame.mouse.get_pressed()
            keys = pygame.key.get_pressed()
            mod = pygame.key.get_mods()

            # prepare renderer for ... rendering
            win.renderer.clear()

            # fps calculating
            fpss.insert(0, g.clock.get_fps())
            if ticks() - last_fps_update >= 1000:
                shown_fps = str(sum(fpss) // len(fpss))
                last_fps_update = ticks()
                fpss.sort()
                bottom_1p = fpss[:int(len(fpss) / 100)]
                if len(bottom_1p) > 0:
                    g.bottom_1p_avg = int(sum(bottom_1p) / len(bottom_1p))
            fpss = fpss[:100]
            shown_fps = str(int(g.clock.get_fps()))

            # fps regulating
            g.dt = g.clock.tick(pw.fps_cap.value) / (1000 / g.def_fps_cap)
            # g.dt = g.clock.tick() / (1000 / g.def_fps_cap)
            if g.stage == "play":
                win.space.step(1 / pw.fps_cap.value)

            # global dynamic variables
            g.p.anim_fps = pw.anim_fps.value / g.fps_cap
            g.process_messageboxworld = True
            if g.mb is not None:
                if g.mb.sword is not None:
                    g.mb.sword.update_lerp = True

            # music
            if g.stage == "play":
                volume = pw.volume.value / 100
            elif g.stage == "home":
                volume = 0
            set_volume(volume)
            g.p.volume = volume
            if not pygame.mixer.music.get_busy():
                pw.next_piece_command()

            # event loop
            create_command_entry = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    # sys.exit()

                # mechanical events
                if not g.events_locked:
                    for fgs in all_foreground_sprites:
                        if hasattr(fgs, "process_event") and callable(fgs.process_event):
                            fgs.process_event(event)

                    if event.type == KEYDOWN:
                        if event.key != K_ESCAPE:
                            if pw.keybinds_active and isinstance(g.selected_widget, Button):
                                b = g.selected_widget
                                key_name = pygame.key.name(event.key).upper()
                                change_keybind(b, b._iden, key_name)

                        # dbging
                        if event.key == K_SPACE and g.debug:
                            # group(Drop("dynamite", pygame.Rect([x / 3 for x in g.mouse] + [10, 10])), all_drops)
                            #group(FollowParticle(g.w.blocks["soil_f"], g.mouse, g.player.rect.center), all_other_particles)
                            # g.w.boss_scene = not g.w.boss_scene
                            # for p in all_other_particles:
                            #     p.switch()
                            if g.midblit == "tool-crafter":
                                g.mb.radar_chart.revaluate(["Da", rand(0, 7)], ["Du", rand(0, 7)], ["A", rand(0, 7)], ["Ma", rand(0, 7)], ["Mo", rand(0, 7)], ["B", rand(0, 7)])

                        if event.key == pygame.K_1:
                            # win.target_zoom = (3, 3)
                            pass

                        if event.key == pygame.K_w:
                            g.player.jump()

                        if event.key == K_q:  # debug so far until it gets a feature on its own
                            ...
                            # setattr(win, f"window{rand(0, 10000000000)}", Window(title=f"Blockingdom", size=(500, 400)))
                            # pprint({k: v.name for k, v in g.w.data[(0, 0)].items()})
                            print(g.w.data[(0, 0)][(0, 0)].name)

                        # actual gameplay events
                        if g.stage == "play":
                            if no_widgets(Entry):
                                if event.key == pygame.K_TAB:
                                    toggle_main()

                                elif event.key == pygame.K_q:
                                    # m = 50
                                    m = 10
                                    g.player.x += sign(g.player.xvel) * m
                                    pass

                                if g.midblit == "workbench":
                                    if event.key == K_SPACE:
                                        if g.player.block :
                                            if g.player.block in g.mb.craftings:
                                                g.mb.craftings[g.player.block] += 1 if g.mod != K_OSC else g.player.amount - g.mb.craftings[g.player.block]
                                                g.mb.crafting_log.append(g.player.block)
                                            else:
                                                g.mb.craftings[g.player.block] = 1 if g.mod != K_OSC else g.player.amount
                                                g.mb.crafting_log.append(g.player.block)
                                            g.player.use_up_inv()
                                            show_added(g.mb.crafting_log[-1])

                                    elif event.key == K_ENTER:
                                        for craftable, amount in g.mb.craftables.items():
                                            if g.player.stats["xp"]["amount"] >= cinfo[craftable].get("xp", 0):
                                                if g.player.stats["energy"]["amount"] - cinfo[craftable].get("energy", 0) >= 0:
                                                    g.player.stats["energy"]["amount"] -= cinfo[craftable].get("energy", 0)
                                                    if craftable in g.w.blocks:
                                                        g.player.new_block(craftable, amount)
                                                    else:
                                                        g.player.new_tool(craftable)
                                                    stop_midblit("workbench")

                                    elif event.key == K_BACKSPACE:
                                        if g.mb.crafting_log:
                                            if None in g.player.inventory:
                                                g.mb.craftings[g.mb.crafting_log[-1]] -= 1
                                                if g.mb.craftings[g.mb.crafting_log[-1]] == 0:
                                                    del g.mb.craftings[g.mb.crafting_log[-1]]
                                                g.player.new_block(g.mb.crafting_log[-1])
                                                del g.mb.crafting_log[-1]

                                elif g.midblit == "furnace":
                                    if event.key == K_SPACE:
                                        if g.player.block:
                                            if g.player.block in fueinfo:
                                                # oxidant (fuel)
                                                if g.player.block == g.mb.oxidant[0]:
                                                    g.mb.oxidant[1] += 1
                                                else:
                                                    g.mb.oxidant = [g.player.block, 1]
                                                g.mb.oxidant_remnant = 0
                                                g.mb.furnace_log.append(["oxidant", g.player.block])
                                            else:
                                                # reductant (burnable / burning / burned / has burned / will burned / ought to be burning)
                                                if g.player.block == g.mb.reductant[0]:
                                                    g.mb.reductant[1] += 1
                                                else:
                                                    g.mb.reductant = [g.player.block, 1]
                                                    g.mb.oxidation_index = 0
                                                g.mb.furnace_log.append(["reductant", g.player.block])
                                            g.player.use_up_inv()

                                    elif event.key == K_BACKSPACE:
                                        type_ = g.mb.furnace_log[-1][0]
                                        if type_ == "oxidant":
                                            g.mb.oxidant[1] -= 1
                                            g.player.new_block(g.mb.oxidant[0])
                                        elif type_ == "reductant":
                                            g.mb.reductant[1] -= 1
                                            g.player.new_block(g.mb.reductant[0])
                                        del g.mb.furnace_log[-1]

                                    elif event.key == K_ENTER:
                                        if all(g.mb.cooked):
                                            g.player.new_block(g.mb.cooked[0])
                                            g.mb.cooked[-1] -= 1

                                elif g.midblit == "anvil":
                                    if event.key == K_SPACE:
                                        if g.player.main == "tool":
                                            if g.player.tool is not None:
                                                if is_smither(g.player.tool):
                                                    g.smither = g.player.tool
                                                    g.anvil_log.append(g.player.tool)
                                        elif g.player.main == "block":
                                            if g.player.block:
                                                if g.player.block not in g.smithings:
                                                    g.smithings[g.player.block] = 1
                                                else:
                                                    g.smithings[g.player.block] += 1
                                                g.player.use_up_inv()
                                                g.anvil_log.append(g.player.block)

                                    elif event.key == K_BACKSPACE:
                                        if g.anvil_log:
                                            if not is_smither(g.anvil_log):
                                                if None in g.player.inventory:
                                                    g.player.new_block(g.anvil_log[-1])
                                                    del g.anvil_log[-1]
                                            else:
                                                if None in g.player.tools:
                                                    g.player.empty_tool = g.anvil_log[-1]
                                                    del g.anvil_log[-1]

                                    elif event.key == K_ENTER:
                                         if g.smithable is not None:
                                            if g.player.stats["xp"]["amount"] >= ainfo[g.smithable].get("xp", 0):
                                                if g.player.stats["energy"]["amount"] - ainfo[g.smithable].get("energy", 0) >= 0:
                                                    g.player.stats["energy"]["amount"] -= ainfo[g.smithable].get("energy", 0)
                                                    if smithable in g.w.blocks:
                                                        g.player.new_block(g.smithable, g.mb.craft_by_what)
                                                    else:
                                                        g.player.new_tool(g.smithable)

                                elif g.midblit == "gun-crafter":
                                    if event.key == K_SPACE:
                                        if g.player.block in gun_blocks:
                                            g.mb.gun_parts[g.player.block.split("_")[1]] = g.player.block
                                            g.mb.gun_log.append(g.player.block.split("_")[1])
                                            g.player.use_up_inv(g.player.blocki, 1)
                                            show_added(g.mb.gun_log[-1])

                                    elif event.key == K_ENTER:
                                        if is_gun_craftable():
                                            """
                                            g.mb.gun_img = win.renderer.subsurface(*crafting_abs_pos, *crafting_eff_size)
                                            g.mb.gun_img = real_colorkey(g.mb.gun_img, LIGHT_GRAY)
                                            g.mb.gun_img = crop_transparent(g.mb.gun_img)
                                            g.mb.gun_img = pygame.transform.scale_by(g.mb.gun_img, 0.7)
                                            g.mb.gun_img = gun_crafter_base
                                            """
                                            g.mb.gun_img = pygame.Surface((20, 20))
                                            Entry(win.renderer, "Enter custom gun name:", custom_gun, **pw.entry_kwargs, input_required=True)

                                    elif event.key == K_BACKSPACE:
                                        pass

                                elif g.midblit == "magic-table":
                                    if event.key == K_SPACE:
                                        if g.player.main == "tool":
                                            if g.player.tool is not None:
                                                g.magic_tool = g.player.tool
                                            show_added(g.magic_tool)
                                        elif g.player.main == "block":
                                            if g.player.block:
                                                if g.player.block.endswith("-orb"):
                                                    if g.player.block in g.magic_orbs:
                                                        g.magic_orbs[g.player.block] += 1
                                                    else:
                                                        g.magic_orbs[g.player.block] = 1
                                                    show_added(g.player.block)
                                                    g.player.use_up_inv(g.player.blocki)

                                    elif event.key == K_ENTER:
                                        _r = []
                                        _g = []
                                        _b = []
                                        for name, amount in g.magic_orbs.items():
                                            color = getattr(pyengine.pgbasics, name.removesuffix("-orb").upper())
                                            _r.append(color[0])
                                            _g.append(color[1])
                                            _b.append(color[2])
                                        color = (sum(_r) / len(_r), sum(_g) / len(_g), sum(_b) / len(_b))
                                        filter = pygame.Surface((30, 30))
                                        filter.fill(color)
                                        filter.set_alpha(125)
                                        tool_name = f"enchanted_{g.player.tool}"
                                        g.w.tools[tool_name] = g.w.tools[g.player.tool].copy()
                                        g.w.tools[tool_name].blit(filter, (0, 0), special_flags=BLEND_RGB_MULT)
                                        g.player.tool = tool_name
                                        g.player.tool_health = 100
                                        stop_midblit("magic")
                                        #g.w.tools[tool_name] = SmartSurface.from_surface(pil_to_pg(PIL.ImageEnhance.Contrast(pg_to_pil(g.w.tools[g.player.tool].copy())).enhance(1.2)))

                                elif g.midblit == "chest":
                                    if g.player.main == "block":
                                        if event.key == K_BACKSPACE:
                                            if None in g.player.inventory:
                                                if g.cur_chest_item != (None, None):
                                                    g.cur_chest_item[1] -= 1
                                                    g.player.new_block(g.cur_chest_item[0])
                                                    if g.cur_chest_item[1] == 0:
                                                        g.cur_chest_item = (None, None)
                                        elif event.key == K_SPACE:
                                            if g.player.amount is not None and g.player.amount > 0:
                                                if g.cur_chest_item[0] in g.player.inventory:
                                                    g.cur_chest_item[1] += 1
                                                    g.player.use_up_inv()
                                                elif g.cur_chest_item[0] is None:
                                                    g.cur_chest_item[0] = g.player.block
                                                    g.cur_chest_item[1] += 1
                                                    g.player.use_up_inv()

                                elif g.midblit == "tool-crafter":
                                    if event.key == K_SPACE:
                                        if g.player.block in oinfo:
                                            ore = oinfo[g.player.block]
                                            if g.player.block not in g.mb.crystals:
                                                g.mb.crystals[g.player.block] = Lattice(ore["crystal"], ore["color"])
                                            else:
                                                g.mb.crystals[g.player.block].stoic += 1

                                    elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                                        if ticks() - g.mb.last_left >= 0:
                                            left = event.key == pygame.K_LEFT
                                            g.mb.compoi.sort(key=lambda x: x.oox, reverse=not left)
                                            new_target_ooxi = []
                                            for index, compos in enumerate(g.mb.compoi):
                                                index -= 1
                                                new_target_ooxi.append(g.mb.compoi[index].target_oox)
                                                # mult
                                                if g.mb.compoi[index].target_oox == 0:
                                                    compos.change_lerp("target_m", compos_mult * 1.6)
                                                else:
                                                    compos.change_lerp("target_m", compos_mult)
                                            for index, compos in enumerate(g.mb.compoi):
                                                compos.change_lerp("target_oox", new_target_ooxi[index])
                                            g.mb.last_left = ticks()

                                elif event.key in (K_SPACE, K_TAB):
                                    toggle_main()

                                if event.key == K_r:
                                    if is_gun(g.player.tool):
                                        if g.player.tool_ammo < get_gun_info(g.player.tool, "magazine")["size"]:
                                            visual.start_reloading()

                                elif event.key == K_i:
                                    g.show_info = not g.show_info
                                    if g.show_info:
                                        g.show_info_index = 0

                                elif event.key == K_p:
                                    g.player.cust_username()

                                elif event.key == K_c:
                                    create_command_entry = True

                                elif event.key == K_ESCAPE:
                                    if g.midblit:
                                        stop_midblit()
                                    elif pw.keybinds_active:
                                        pw.disable_keybinds()
                                    elif g.menu:
                                        disable_needed_widgets()
                                    else:
                                        settings()

                                elif event.key == K_ENTER:
                                    for messagebox in all_messageboxes:
                                        messagebox.close("open")

                                elif g.player.main == "block" and pygame.key.name(event.key) in ("1", "2", "3", "4", "5"):
                                    g.player.indexes["block"] = int(pygame.key.name(event.key)) - 1
                                    g.player.food_pie = g.player.def_food_pie.copy()
                                elif g.player.main == "tool" and pygame.key.name(event.key) in ("1", "2"):
                                    g.player.indexes["tool"] = int(pygame.key.name(event.key)) - 1
                                    g.player.food_pie = g.player.def_food_pie.copy()

                    elif event.type == pygame.KEYUP:
                        if event.key == pygame.K_w:
                            if g.player.yvel < 0:
                                g.player.yvel /= 3

                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mousebuttondown_event(event.button)
                        late_rects.clear()

                    elif event.type == pygame.MOUSEBUTTONUP:
                        mousebuttonup_event(event.button)

                    elif event.type == pygame.MOUSEWHEEL:
                        if g.stage == "play":
                            if g.player.main == "block":
                                main = "block"
                                max_index = 5
                            elif g.player.main == "tool":
                                main = "tool"
                                max_index = 2

                            if event.y > 0:
                                if g.player.indexes[main] > 0:
                                    g.player.indexes[main] -= 1
                                else:
                                    g.player.indexes[main] = max_index - 1
                            elif event.y < 0:
                                if g.player.indexes[main] < max_index - 1:
                                    g.player.indexes[main] += 1
                                else:
                                    g.player.indexes[main] = 0

                    elif event.type == pygame.VIDEORESIZE:
                        w, h = event.size
                        wr, wh = w / win.width, h / win.height
                        # win.renderer.scale = (wr, wh)

                    elif event.type == pygame.MOUSEMOTION:
                        g.mouse_delta = event.rel
                        if g.mouses[0]:
                            g.mouse_rel_log.append(event.rel)
                            g.mouse_log.append(g.mouse)
                            # late_rects.append([pygame.Rect(*g.mouse, 3, 3), RED])
                        if g.midblit == "tool-crafter":
                            if mouses[0]:
                                dx, dy = event.rel
                                m = 0.015
                                g.mb.sword.ya -= dx * 0.01
                                g.mb.sword.xa += dy * 0.01

                    elif event.type == pygame.JOYDEVICEADDED:
                        controller.init(event.device_index)
                        controller.activate()
                        button_s.selected = True

                    elif event.type == pygame.JOYDEVICEREMOVED:
                        controller.remove(event.instance_id)
                        MessageboxOk(win.renderer, f'Device "{controller.name}" disconnected', **pw.ok_kwargs)

                    elif event.type == pygame.JOYBUTTONDOWN:
                        print(event.button)
                        # init
                        b = controller.map[controller.name]["buttons"]
                        # x button
                        if event.button == b["cross"]:
                            g.selected_widget.command()
                            g.selected_widget = controller.next_protocol.get(g.selected_widget, g.selected_widget)
                        # arrow buttons
                        if event.button == b["down"]:
                            g.selected_widget = controller.button_protocol[g.selected_widget]
                        elif event.button == b["up"]:
                            mp = {v: k for k, v in controller.button_protocol.items()}
                            g.selected_widget = mp[g.selected_widget]

                        if pw.keybinds_active:
                            if event.button == b["cross"]:
                                set_widget_icon(g.selected_widget, controller.rmap[event.button])

                    elif event.type == pygame.JOYAXISMOTION:
                        # pre
                        a = controller.map[controller.name]["axes"]
                        if event.axis == a["Jleft"][1]:
                            if abs(event.value) >= 0.21:
                                delta = event.value - controller.map[controller.name]["last_axismo"]["Jleft"]
                                # check whether going down or up, not down-up or some shit
                                if event.value > 0 and delta < 0:
                                    controller.map[controller.name]["can_down"] = True
                                if event.value < 0 and delta > 0:
                                    controller.map[controller.name]["can_up"] = True
                                # if can go down, go down
                                cond_down = event.value > 0 and delta > 0 and controller.map[controller.name]["can_down"]
                                cond_up = event.value < 0 and delta < 0 and controller.map[controller.name]["can_up"]
                                if cond_down or cond_up:
                                    # player is moving down from middle
                                    if event.value < 0:
                                        mp = {v: k for k, v in controller.button_protocol.items()}
                                        controller.map[controller.name]["can_up"] = False
                                    else:
                                        mp = controller.button_protocol
                                        controller.map[controller.name]["can_down"] = False
                                    g.selected_widget = mp[g.selected_widget]
                                controller.map[controller.name]["last_axismo"]["Jleft"] = event.value
                        # # R2
                        if event.axis == a["R2"]:
                            delta = event.value - controller.map[controller.name]["last_axismo"]["R2"]
                            # if pressing (not releasing) [greater than 0] {cannot be equal}
                            if delta > 0:
                                if not controller.map[controller.name]["axis_down"]["R2"]:
                                    g.player.new_anim("dslash")
                                    controller.map[controller.name]["axis_down"]["R2"] = True
                            else:
                                # must be releasing then
                                controller.map[controller.name]["axis_down"]["R2"] = False
                            # set last axismo
                            controller.map[controller.name]["last_axismo"]["R2"] = event.value

                    if g.stage == "home":
                        for spr in all_main_widgets():
                            if hasattr(spr, "process_event") and callable(spr.process_event):
                                spr.process_event(event)
                                g.process_messageboxworld = False

                    # widget process events
                    process_widget_events(event, mouse)

                    # after processes
                    if create_command_entry:
                        Entry(win.renderer, "Enter your command:", player_command, **pw.entry_kwargs)

            # pending
            for entry in g.pending_entries[:]:
                entry.enable()
                g.pending_entries.remove(entry)

            # reset fpss list
            keys = pygame.key.get_pressed()
            if keys[K_LALT] and keys[K_LSHIFT] and keys[K_r] and not fps_resetted:
                fpss = []
                fps_resetted = True

            # PLAY INIT
            # logistics
            chunk_rects = []
            chunk_texts = []
            g.player.block_data = []
            g.player.ext_block_data = []
            g.player.water_data = []
            g.player.ramp_data = []
            magic_tables = []
            hovering_rect = None
            metal_detector = 0
            # post-scale renders
            grasses = []
            waters = []
            # hotbar
            hotbar_xo = -3
            tool_holders_x, tool_holders_y = (win.width / 2 - 35 + hotbar_xo, 7)
            inventory_x, inventory_y = (win.width / 2 + 21 + hotbar_xo, 7)
            inventory_font_size = 12
            # pre-scale play
            if g.stage == "play":
                # filling
                fill_rect(win.renderer, pygame.Color(SKY_BLUE), (0, 0, *win.size))
                # # day-night cycle
                # g.w.dnc_index = g.w.dnc_direc(g.w.dnc_index, fromperc(g.dt * 100, g.w.dnc_vel))
                # if g.w.dnc_index >= len(g.w.dnc_colors) - 1:
                #     g.w.dnc_index = len(g.w.dnc_colors) - 1
                #     g.w.dnc_direc = op.sub
                # elif g.w.dnc_index <= 0:
                #     g.w.dnc_index = 0
                #     g.w.dnc_direc = op.add
                #     g.w.set_dnc_colors()
                #     if g.w.hound_round_chance > 1:
                #         g.w.hound_round_chance -= 1

                # background sprites
                # for bsprite in all_background_sprites:
                #     bsprite.update()
                # processing chunks
                updated_chunks = []
                g.num_blocks = 0
                g.num_entities = 0
                # late chunk data
                for chunk in g.w.late_chunk_data:
                    if chunk in g.w.data:
                        for pos, name in g.w.late_chunk_data[chunk].copy().items():
                            g.w.modify(name, chunk, pos)
                            del g.w.late_chunk_data[chunk][pos]

                # update the chunks
                for y in range(V_CHUNKS):
                    for x in range(H_CHUNKS):
                        # init chunk data like pos and other metadata
                        target_x = x - 1 + int(round(g.scroll[0] / (CW * BS)))
                        target_y = y - 1 + int(round(g.scroll[1] / (CH * BS)))
                        target_chunk = (target_x, target_y)
                        updated_chunks.append(target_chunk)
                        # create chunk if not existing yet
                        biome = choice(bio.biomes)
                        biome = "forest"
                        if target_chunk not in g.w.data:
                            surf_terrain = generate_chunk(target_chunk, biome=biome)
                        g.w.last_chunks.insert(0, surf_terrain)
                        g.w.last_chunks = g.w.last_chunks[:1]
                        # init chunk render
                        _cpos = g.w.metadata[target_chunk]["pos"]
                        chunk_topleft = (_cpos[0] * BS - g.scroll[0], _cpos[1] * BS - g.scroll[1])
                        terrain_tex = g.w.terrains[target_chunk]
                        # terrain_tex.color = (rrr, ggg, bbb, 255)
                        # lighting_tex = g.w.lightings[target_chunk]
                        # lighting_tex.alpha = 0
                        # lighting_tex.alpha = 240 * (sin(ticks() * 0.00008) + 1) / 2
                        chunk_rect = pygame.Rect(chunk_topleft, (terrain_tex.width, terrain_tex.height))
                        # render chunk
                        win.renderer.blit(terrain_tex, chunk_rect)
                        _chunk_rect = chunk_rect
                        if "lighting_offset" in g.w.metadata[target_chunk]:
                            _chunk_rect = chunk_rect.move(g.w.metadata[target_chunk]["lighting_offset"], 0)
                        # win.renderer.blit(g.w.lightings[target_chunk], _chunk_rect)
                        # rest
                        g.w.block_data[target_chunk] = {}
                        g.w.block_rects[target_chunk] = {}

                        # updating blocks
                        if target_chunk in g.w.to_update:
                            for block in g.w.to_update[target_chunk]:
                                nbg = non_bg(block.name)
                                name = block.name
                                abs_pos = block.pos

                                # falling blocks
                                if block.name in flinfo:
                                    block.yvel += block.yacc
                                    block.ypos += block.yvel
                                    block.last_ypos = 0
                                    if int(block.ypos) > block.last_ypos:
                                        block.last_ypos = block.ypos
                                    # if ticks() - block.last_fall >= 1_000:
                                        _chunk, _pos = correct_tile(target_chunk, block.pos, 0, 1)
                                        try:
                                            if g.w.data[_chunk].get(_pos, void_block).name not in empty_blocks:
                                                raise ValueError
                                            # make sand
                                            g.w.modify(block.name, _chunk, _pos)
                                            g.w.data[_chunk][_pos].yvel = g.w.data[target_chunk][block.pos].yvel
                                            # delete prev. sand
                                            if flinfo[block.name].get("delete", False):
                                                g.w.modify("air", target_chunk, block.pos)
                                            block.last_fall = ticks()
                                        except (KeyError, ValueError):
                                            block.ypos -= block.yvel
                                            block.yvel -= block.yacc

                                # corns blocks growing
                                elif nbg in corns:
                                    version = name.split("_")[1].removeprefix("vr")
                                    if version in growable_corns:
                                        if "corn" not in block.last_growths:
                                            block.last_growths["corn"] = epoch()
                                        if epoch() - block.last_growths["corn"] >= 1:
                                            if version == "0.0":
                                                g.w.modify("corn-crop_vr1.0", target_chunk, abs_pos, overwrites=corns, remove_from_updating=True)
                                                g.w.modify("corn-crop_vr1.1", *correct_tile(target_chunk, abs_pos, 0, -1), overwrites=corns)
                                                block.last_growths["corn"] = epoch()
                                            elif version == "1.0":
                                                g.w.modify("corn-crop_vr2.0", target_chunk, abs_pos, overwrites=corns, remove_from_updating=True)
                                                g.w.modify("corn-crop_vr2.1", *correct_tile(target_chunk, abs_pos, 0, -1), overwrites=corns)
                                                block.last_growths["corn"] = epoch()
                                            elif version == "2.0":
                                                g.w.modify("corn-crop_vr3.0", target_chunk, abs_pos, overwrites=corns, remove_from_updating=True)
                                                g.w.modify("corn-crop_vr3.1", *correct_tile(target_chunk, abs_pos, 0, -1), overwrites=corns, remove_from_updating=True)
                                                g.w.modify("corn-crop_vr3.2", *correct_tile(target_chunk, abs_pos, 0, -2), overwrites=corns)
                                                block.last_growths["corn"] = epoch()
                                            elif version == "3.0":
                                                g.w.modify("corn-crop_vr4.0", target_chunk, abs_pos, full_crop=True)
                                                g.w.modify("corn-crop_vr4.1", *correct_tile(target_chunk, abs_pos, 0, -1), overwrites=corns, remove_from_updating=True, full_crop=True)
                                                g.w.modify("corn-crop_vr4.2", *correct_tile(target_chunk, abs_pos, 0, -2), overwrites=corns, full_crop=True)
                                                block.last_growths["corn"] = epoch()

                                # flowing
                                elif nbg in plants:
                                    # init
                                    block.rect.topleft = block._rect.topleft
                                    block.rect.x -= g.scroll[0]
                                    block.rect.y -= g.scroll[1]
                                    # interaction with player
                                    if g.player.rect.colliderect(block.rect):
                                        dx = block.rect.centerx - g.player.rect.centerx
                                        target_angle = (20 - abs(dx)) / 20 * 90 * sign(dx)
                                        block.plant_angle += (target_angle - block.plant_angle) * 0.1
                                    else:
                                        target_angle = 0
                                        block.plant_angle += (target_angle - block.plant_angle) * 0.1
                                    # set the variables
                                    block.plant_sin_angle = 5 * (sin(2 * pi * ticks() / 700 + block.sin - 2))
                                    pos = (block.rect.centerx + block.plant_pos[0], block.rect.centery + block.plant_pos[1])
                                    vec = block.plant_offset
                                    angle = block.plant_angle + block.plant_sin_angle
                                    # set the images to blit
                                    # [cattail]
                                    surf_img = g.w.surf_assets["blocks"][nbg]
                                    surf_img, surf_rect = rot_pivot(surf_img, angle, pos, vec)
                                    tex_img = T(surf_img)
                                    win.renderer.blit(tex_img, surf_rect)
                                    draw_rect(win.renderer, ORANGE, surf_rect)
                                    # [cattail-top]
                                    top_surf_img = g.w.surf_assets["blocks"][f"{name}-top"]
                                    top_pos = (block.rect.centerx + block.plant_pos[0], block.rect.centery + block.plant_pos[1])
                                    top_offset = Vector2(0, -45)
                                    top_surf_img, top_surf_rect = rot_pivot(top_surf_img, angle, top_pos, top_offset, nbg == "pampas")
                                    top_tex_img = T(top_surf_img)
                                    win.renderer.blit(top_tex_img, top_surf_rect)

                        # updating the entities in the chunk
                        # updating_entities[target_chunk].append(target_chunk)

                        # show the chunk borders with different colors
                        if target_chunk not in g.w.chunk_colors:
                            chunk_color = [rand(0, 255) for _ in range(3)] + [255]
                            g.w.chunk_colors[target_chunk] = chunk_color
                        else:
                            chunk_color = g.w.chunk_colors[target_chunk]

                        rect = pygame.Rect(*g.w.metadata[target_chunk]["pos"], BS, BS)
                        rect.x = rect.x * BS - g.scroll[0]
                        rect.y = rect.y * BS - g.scroll[1]
                        if pw.show_chunk_borders:
                            chunk_rects.append([(*rect.topleft, CW * BS, CH * BS), chunk_color])
                            chunk_texts.append([(target_chunk, [x, y]), (rect.x + CW * BS / 2, rect.y + CH * BS / 2 + 60)])

                        # |
                        # infamous
                        # |
                        # continue
                        # |

                        for index, (abs_pos, block) in enumerate(g.w.data[target_chunk].copy().items()):
                        #   init
                            if block in g.w.to_break:
                                try:
                                    breaking_sprs[int(block.broken)]
                                except IndexError:
                                    block.finish_breaking = (target_chunk, abs_pos)
                            # g.player.ext_block_data.append([block, block._rect])
                            # calculate_light(target_chunk, abs_pos)
                            g.num_blocks += 1
                            continue
                            name = block.name
                            nbg = non_bg(name)

                        #     hitbox = False
                        #     render = True
                        #     # rendering the block
                            (bx, by) = abs_pos

                            _rect = block._rect
                            block.rect.topleft = block._rect.topleft
                            block.rect.x -= g.scroll[0]
                            block.rect.y -= g.scroll[1]
                            img = g.w.blocks[nbg]
                            win.renderer.blit(img, block.rect)

                            # growing wheat
                            if nbg in wheats:
                                if nbg != "wheat_st4":
                                    if "wheat" not in block.last_growths:
                                        block.last_growths["wheat"] = epoch()
                                    if epoch() - block.last_growths["wheat"] >= 5:
                                        g.w.modify(f"wheat_st{int(nbg[-1]) + 1}", target_chunk, abs_pos)
                            elif nbg in corns:
                                version = name.split("_")[1].removeprefix("vr")
                                if version in growable_corns:
                                    if "corn" not in block.last_growths:
                                        block.last_growths["corn"] = epoch()
                                    if epoch() - block.last_growths["corn"] >= 2:
                                        if version == "0.0":
                                            g.w.modify("corn-crop_vr1.0", target_chunk, abs_pos, overwrites=corns)
                                            g.w.modify("corn-crop_vr1.1", *correct_tile(target_chunk, abs_pos, 0, -1), overwrites=corns)
                                            block.last_growths["corn"] = epoch()
                                        elif version == "1.0":
                                            g.w.modify("corn-crop_vr2.0", target_chunk, abs_pos, overwrites=corns)
                                            g.w.modify("corn-crop_vr2.1", *correct_tile(target_chunk, abs_pos, 0, -1), overwrites=corns)
                                            block.last_growths["corn"] = epoch()
                                        elif version == "2.0":
                                            g.w.modify("corn-crop_vr3.0", target_chunk, abs_pos, overwrites=corns)
                                            g.w.modify("corn-crop_vr3.1", *correct_tile(target_chunk, abs_pos, 0, -1), overwrites=corns)
                                            g.w.modify("corn-crop_vr3.2", *correct_tile(target_chunk, abs_pos, 0, -2), overwrites=corns)
                                            block.last_growths["corn"] = epoch()
                                        elif version == "3.0":
                                            g.w.modify("corn-crop_vr4.0", target_chunk, abs_pos)
                                            g.w.modify("corn-crop_vr4.1", *correct_tile(target_chunk, abs_pos, 0, -1), overwrites=corns)
                                            g.w.modify("corn-crop_vr4.2", *correct_tile(target_chunk, abs_pos, 0, -2), overwrites=corns)
                                            block.last_growths["corn"] = epoch()

                            # flowing lava
                            if nbg == "lava":
                                if ticks() - block.last_flow >= 200:
                                    flowns = []
                                    bottom_chunk, bottom_pos = correct_tile(target_chunk, abs_pos, 0, 1)
                                    if bottom_chunk in g.w.data:
                                        if g.w.data[bottom_chunk].get(bottom_pos, void_block).name != "lava":
                                            if g.w.data[bottom_chunk].get(bottom_pos, void_block).name in empty_blocks:
                                                flowns.append([bottom_chunk, bottom_pos])
                                        else:
                                            flowns = True
                                    if not flowns:
                                        yo = 0
                                        for xo in (-1, 1):
                                            side_chunk, side_pos = correct_tile(target_chunk, abs_pos, xo, yo)
                                            check_chunk, check_pos = correct_tile(target_chunk, abs_pos, 0, -1)
                                            if g.w.data[check_chunk].get(check_pos, void_block).name == "lava":
                                                if side_chunk in g.w.data:
                                                    if g.w.data[side_chunk].get(side_pos, void_block).name in empty_blocks:
                                                        flowns.append([side_chunk, side_pos])
                                    if isinstance(flowns, list):
                                        for flown in flowns:
                                            g.w.modify("lava", *flown)
                                            block.last_flow = ticks()

                            # update block identity (§processing moved to main)
                            if nbg == "frac-dist":
                                if ticks() - block.last_frac_dist >= 1_000:
                                    for _ in range((ticks() - block.last_frac_dist) // 1_000):
                                        p = FracDistParticle(choices(list(range(5)), [at["ppm"] for at in atinfo.values()])[0])
                                        group(p, all_gases)
                                    block.last_frac_dist = ticks()

                            # update block cache for collisions of the entities
                            if abs_pos in g.w.data[target_chunk]:
                                g.w.block_data[target_chunk][block.pos] = block

                # update the entities
                if pw.entities:
                    for chunk in updated_chunks:
                        for i, entity in enumerate(g.w.entities[chunk][:]):
                            # relocate entity to new chunk
                            entity.check_chunk_borders()
                            if entity.relocate_to is not None and entity.relocate_to in g.w.data:
                                # print(f"\n\n\nrelocated from {entity.chunk_index} to {entity.relocate_to}\n\n\n")
                                g.w.entities[entity.chunk_index].remove(entity)
                                g.w.entities[entity.relocate_to].append(entity)
                                entity.chunk_index = entity.relocate_to
                                entity.relocate_to = None
                            # update the entity
                            g.num_entities += 1
                            entity.update(g.dt, pw.show_hitboxes, g.dialogue)
                            # cool dialogue
                            if entity.dialogue:
                                g.dialogue = True
                                g.scroll_orders = [
                                    entity._rect.centerx - entity.height / 2,
                                    entity._rect.centery - entity.width / 2
                                ]
                                entity.dialogue = False
                                # win.target_zoom = (3, 3)
                            # check whether enemy has been hit this frame and add blood effect
                            if entity.taking_damage:
                                entity.set_final_rects()
                                for _ in range(1):
                                    group(BloodParticle(entity), all_other_particles)
                            # check whether the entity is dead and drop the loot
                            if entity.dead and not entity.dying:
                                # shatter particles
                                n = 3
                                w = roundn(entity.image.width / n, S)
                                h = roundn(entity.image.height / n, S)
                                for y in range(n):
                                    for x in range(n):
                                        area = pygame.Rect(x * w, y * h, w, h)
                                        group(ShatterParticle(entity, area), all_other_particles)
                                entity.dying = True
                            # show hitboxes if selected by user
                            if pw.show_hitboxes:
                                draw_rect(win.renderer, RED, entity.rect)
                                write(win.renderer, "midbottom", entity.chunk_index, orbit_fonts[12], BLACK, entity.rect.centerx, entity.rect.top - 8, tex=True)
                            # collide with attacking player
                            if g.player.anim_type in ("punch",):
                                if entity._rect.colliderect(g.player._rect):
                                    entity.take_damage(1)
                                    if entity.demon:
                                        entity.glitch()

                # breaking the blocks with tools
                for block in g.w.to_break[:]:
                    if block.finish_breaking is None:
                        rect = pygame.Rect(block.rect[0] - g.scroll[0], block.rect[1] - g.scroll[1], BS, BS)
                        win.renderer.blit(breaking_sprs[int(block.broken)], rect)
                    else:
                        g.w.modify("air", *block.finish_breaking)
                        g.w.to_break.remove(block)

                # mouse shit with chunks
                if not pw.keybinds_active:
                    if not g.menu and g.midblit is None:
                        if g.player.main == "block":
                            # init
                            target_chunk, abs_pos = pos_to_tile(g.mouse)
                            try:
                                block = g.w.data[target_chunk][abs_pos]
                                name = block.name
                            except KeyError:
                                block = name = None
                            _rect = pygame.Rect([x * BS for x in abs_pos], (BS, BS))
                            rect = pygame.Rect((_rect.x - g.scroll[0], _rect.y - g.scroll[1], BS, BS))
                            m = 0.0018
                            color = (
                                (sin(ticks() * m) + 1) * 127.5,
                                (sin((ticks() * m) - 0.333 * pi) + 1) * 127.5,
                                (sin((ticks() * m) - 0.666 * pi) + 1) * 127.5,
                                255,
                            )
                            color = ORANGE
                            draw_rect(win.renderer, color, rect)
                            write(win.renderer, "center", name, orbit_fonts[12], WHITE, *rect.center, tex=True)
                            hovering_rect = [r * S for r in rect]
                            # left mouse
                            if g.mouses[0]:
                                if not g.disabled_widgets:
                                    setto = None
                                    if g.player.block in finfo:
                                        g.player.eat()
                                    else:
                                        g.player.eating = False
                                        if g.first_affection is None:
                                            if name in ("air", None):
                                                if g.player.block:
                                                    g.first_affection = "place"
                                            else:
                                                g.first_affection = "break"
                                        if g.first_affection == "place":
                                            if not _rect.colliderect(g.player._rect):
                                                if name in empty_blocks:
                                                    setto = g.player.block
                                        elif g.first_affection == "break":
                                            if name not in empty_blocks and name not in unbreakable_blocks:
                                                emptiness = g.w.metadata[target_chunk]["underground"].get(abs_pos, "air")
                                                g.w.modify(emptiness, target_chunk, abs_pos, overwrites_all=True)
                                        if setto is not None:
                                            if mod == 1:  # left shift I think
                                                setto += "_bg"
                                            g.w.modify(setto, target_chunk, abs_pos)
                            else:
                                g.player.eating = False
                            # right mouse
                            if mouses[2]:
                                if name is not None:
                                    # rightings
                                    # crafting stuff
                                    if non_bg(name) in ("workbench", "furnace", "gun-crafter", "magic-table", "altar"):
                                        if k in g.w.metadata[target_chunk]:
                                            g.w.metadata[target_chunk][abs_pos] = {}
                                        if non_bg(name) == "workbench":
                                            pass
                                    # rotations
                                    elif bpure(name) == "ramp":
                                        g.w.data[target_chunk][abs_pos] = rotate_name(name, rotations4)
                                    else:
                                        if g.player.block == "fire":
                                            g.w.data[target_chunk][abs_pos] = [g.w.data[target_chunk][abs_pos], "fire"]

                # if not thread_active:
                #     Thread(target=update_light, daemon=True).start()

                # player collision with blocks
                for yo in range(-2, 3):
                    for xo in range(-2, 3):
                        # init
                        target_chunk, abs_pos = pos_to_tile(g.player.rect.center)
                        target_chunk, abs_pos = correct_tile(target_chunk, abs_pos, xo, yo)
                        if xo == yo == 0:
                            g.player.coordinates = abs_pos
                            g.player.current_chunk = target_chunk
                        # processing the data
                        if target_chunk in g.w.data:
                            if abs_pos in g.w.data[target_chunk]:
                                try:
                                    block = g.w.data[target_chunk][abs_pos]
                                except KeyError:
                                    continue
                                else:
                                    name = block.name
                                    _rect = pygame.Rect([x * BS for x in abs_pos], (BS, BS))
                                    rect = pygame.Rect((_rect.x - g.scroll[0], _rect.y - g.scroll[1], BS, BS))
                                    if pw.show_hitboxes:
                                        if xo == yo == 0:
                                            (win.renderer, GREEN, rect, 1)
                                        else:
                                            (win.renderer, RED, rect, 1)
                                    if name in ramp_blocks:
                                        g.player.ramp_data.append([block, _rect])
                                    else:
                                        g.player.block_data.append([block, _rect])
                                    if xo == yo == 0:
                                        metal_detector = block.ore_chance

                # breaking blocks spritesheet rendering (if you see this fuck you)

                # foregorund sprites (includes the player)
                # visual.update()
                g.player.update()

                # all_foreground_sprites.draw(win.renderer)
                # all_foreground_sprites.update()
                #

                # # death screen
                # if g.player.dead:
                #     win.renderer.blit(death_screen, (0, 0))
                #
                # # other particles
                for oparticle in all_other_particles:
                    oparticle.update()

                # show fps
                if pw.show_fps:
                    pw.show_fps_command()

                # # processing lasts
                # if ticks() - last_cloud >= rand(7_560, 14_000):
                #     group(Cloud(1), all_background_sprites)
                #     last_cloud = ticks()
                #
                # if pw.show_hitboxes:
                #     if hasattr(visual, "rect"):
                #         (win.renderer, GREEN, visual.rect, 1)

                # P L A Y  B L I T S -------------------------------------------------------------------------- #
                # blitting background
                win.renderer.blit(tool_holders_img, tool_holders_rect)
                win.renderer.blit(inventory_img, inventory_rect)

                # blitting tools
                x = tool_holders_rect.x + 3
                y = tool_holders_rect.y + 3
                for index, tool in enumerate(g.player.tools):
                    if tool is not None:
                        # tool_img = g.w.tools[tool]
                        # tw, th = tool_img.width, tool_img.height
                        # xo, yo = (0, 0)
                        # win.renderer.blit(tool_img, pygame.Rect(x + xo, y + yo, tw, th))
                        pass
                    # border if selected
                    if g.player.main == "tool":
                        if index == g.player.tooli:
                            win.renderer.blit(square_border_img, square_border_rect.move_to(topleft=(x - S, y - S)))
                            pass
                    x += 11 * S

                # blitting blocks
                """
                x = inventory_rect.x + 3
                y = inventory_rect.y + 3
                for index, block in enumerate(g.player.inventory):
                    if block is not None:
                        block_img = g.w.blocks[block]
                        bw, bh = block_img.width, block_img.height
                        win.renderer.blit(block_img, pygame.Rect(x, y, bw, bh))
                        pass
                    # border if selected
                    if g.player.main == "block":
                        if index == g.player.blocki:
                            win.renderer.blit(square_border_img, pygame.Rect(x - 3, y - 3, *square_border_rect.size))
                            pass
                    x += 11 * S
                """

            # pre-scale home
            elif g.stage == "home":
                pass

            anim_index += 0.4
            if anim_index >= 7:
                anim_index = 0

            # win.renderer.blit(Entity.imgs["hallowskull"][int(anim_index)], (0, 30))
            # win.renderer.blit(Entity.imgs["keno"][int(anim_index)], (0, 40))
            # win.renderer.blit(g.w.blocks["soil_f"], (100, 100))
            # win.renderer.blit(test_sprs[int(anim_index)], pygame.Rect(200, 200, test_sprs[int(anim_index)].width, test_sprs[int(anim_index)].height))

            # post-scale play
            if g.stage == "play":
                # saved rendering in order to fix overlapping
                for data in chunk_rects:
                    cr, color = data
                    draw_rect(win.renderer, color, cr)
                for data in chunk_texts:
                    (t1, t2), pos = data
                    write(win.renderer, "center", t1, orbit_fonts[12], CYAN, *pos, tex=True)
                for mt in magic_tables:
                    pygame.gfxdraw.aaellipse(win.renderer, *mt)

                # hovering block
                if hovering_rect is not None:
                    (win.renderer, g.w.text_color, hovering_rect, 1)

                # visual block and tool
                ui.update()

                # projectiles
                all_projectiles.update()

                # drops
                for drop in all_drops:
                    drop.update()

                # grass boi
                """
                for block, rect in grasses:
                    rect = pygame.Rect([r * S for r in rect])
                    img = g.w.blocks[block.name]
                    width, height = img.get_size()
                    img = scale3x(img)
                    angle = 45 + sin((ticks() + block.sin) * 0.01) * 2
                    dist = distance(g.player.rrect, rect)
                    img, rect = rot_center(img, angle, rect.center)
                    rect.y += height / 2 + 6
                    win.renderer.blit(img, rect)
                    break
                """

                # water boi
                """
                for block, rect in waters:
                    rect = pygame.Rect([r * S for r in rect])
                    if not block.waters:
                        for i in range(30):
                            water = {}
                            water["x"] = i
                            water["y"] = 0
                            water["v"] = 0
                            water["a"] = 0
                            block.waters.append(water)
                    for i, water in enumerate(block.waters):
                        dy = water["y"]
                        k = 0.06
                        d = 0.06
                        water["a"] = -k * dy - d * water["v"]
                        water["v"] += water["a"]
                        water["y"] += water["v"]
                        water["p"] = (int(rect.x + water["x"]), int(rect.y + water["y"]))
                        pygame.gfxdraw.vline(win.renderer, water["p"][0], water["p"][1], rect.bottom, list(WATER_BLUE) + [125])
                """

                # P L A Y  B L I T S -------------------------------------------------------------------------- #
                # write(win.renderer, "bottomright", g.player.username, orbit_fonts[12], g.w.text_color, *g.player.rect.topleft, tex=True)
                # metal_detector_perc = floor((metal_detector + 0.5) * 100)
                # write(win.renderer, "center", f"{metal_detector_perc}%", orbit_fonts[15], BLACK, g.player.rrect.centerx, g.player.rrect.centery - 60, border=WHITE)
                # win.renderer.blit(g.bar_rgb_img.subsurface(0, 0, metal_detector_perc, g.bar_rgb_img.get_height()), (100, 100))

                # sizes
                # inventory_width = inventory_img.get_width()
                # hotbar_width = tool_holders_img.get_width() + 30 + inventory_width + 30 + pouch_img.get_width()

                # writing main item names
                y = inventory_y
                yo = 69
                if g.player.main == "block" and g.player.block:
                    x = inventory_x
                    yo += 15
                    if g.player.block in gun_blocks:
                        block = gpure(g.player.block).upper()
                    else:
                        block = bshow(g.player.block).upper()
                    # write(win.renderer, "topleft", block, orbit_fonts[15], g.w.text_color, x, y + yo, tex=True)

                elif g.player.main == "tool" and g.player.tool:
                    # write tool name
                    x = tool_holders_x * S + tool_holders_width * S / 2
                    tool = tshow(g.player.tool).upper()
                    # write(win.renderer, "center", tool, orbit_fonts[inventory_font_size], g.w.text_color, x, y + yo, tex=True)
                    if is_gun(g.player.tool):
                        # write(win.renderer, "center", f"{BULLET}", helvue_fonts[22], g.w.text_color, g.mouse[0] - visual.scope_yoffset, g.mouse[1] - 30)
                        # write(win.renderer, "center", g.player.tool_ammo, orbit_fonts[16], g.w.text_color, g.mouse[0] + visual.scope_yoffset, g.mouse[1] - 30)
                        pass
                    # show info
                    if g.show_info:
                        info_xo = 10
                        info_yo = 32
                        line_x, line_y = x, y + yo + 16
                        g.show_info_index += 2
                        line_width, line_height = 85, 60
                        pygame.gfxdraw.hline(win.renderer, int(max(line_x - g.show_info_index, line_x - line_width)), int(x), line_y, g.w.text_color)
                        pygame.gfxdraw.hline(win.renderer, int(min(line_x + g.show_info_index, line_x + line_width)), int(x), line_y, g.w.text_color)
                        if g.show_info_index >= line_width:
                            pygame.gfxdraw.vline(win.renderer, int(line_x), line_y, min(line_y + (g.show_info_index - 85), line_y + line_height), g.w.text_color)
                        if g.show_info_index >= line_width + line_height:
                            damage_surf, damage_rect = write(win.renderer, "midright", f"KIC", orbit_fonts[12], g.w.text_color, x - info_xo, y + yo + info_yo * 1, blit=False)
                            damage_output_surf, damage_output_rect = write(win.renderer, "midleft", f"{oinfo[g.player.tool_ore]['toughness']}", orbit_fonts[12], g.w.text_color, x + info_xo, y + yo + info_yo * 1, blit=False)
                            win.renderer.blit(damage_surf, damage_rect)
                            win.renderer.blit(damage_output_surf, damage_output_rect)

                # selected block
                x = inventory_rect.x
                y = inventory_rect.y
                for index, block in enumerate(g.player.inventory):
                    blit_rect = pygame.Rect(x + 3, y + 3, BS, BS)
                    if block is not None:
                        if g.player.inventory_amounts[index] != float("inf"):
                            # write(win.renderer, "center", g.player.inventory_amounts[index], orbit_fonts[inventory_font_size], g.w.text_color, x + 17, y + 44, tex=True)
                            pass
                        else:
                            # write(win.renderer, "center", INF, arial_fonts[18], g.w.text_color, x + 17, y + 47, tex=True)
                            pass
                        win.renderer.blit(g.w.blocks[block], blit_rect)
                    if g.player.main == "block":
                        if index == g.player.blocki:
                            win.renderer.blit(square_border_img, square_border_rect.move_to(topleft=(blit_rect.x - S, blit_rect.y - S)))
                    x += 33

                # workbench
                co = 10
                if g.midblit == "workbench":
                    mbr = g.midblit_rect()
                    win.renderer.blit(workbench_img, mbr)
                    rect = pygame.Rect(0, 0, 0, 0)
                    x = mbr.x + 30 / 2 + 25
                    y = mbr.y + 30 + 30 / 2 + 10
                    sy = y
                    xo = 30 + 5
                    yo = 30 + 10
                    for crafting_block in g.mb.craftings:
                        # crafting material
                        img = g.w.blocks[crafting_block]
                        rect.update(x, y, img.width, img.height)
                        # draw_line(win.renderer, BLACK, (x + 30 / 2, y), workbench_center)
                        win.renderer.blit(g.w.blocks[crafting_block], rect)
                        write(win.renderer, "midright", g.mb.craftings[crafting_block], orbit_fonts[inventory_font_size], BLACK, x - 20, y, tex=True)
                        y += yo
                        if (y - sy) / yo == 5:
                            y = sy
                            x += xo
                        # calculating receiving material
                        g.mb.craftables = SmartOrderedDict()
                        for craftable in cinfo:
                            g.mb.midblit_by_what = []
                            enough = 0
                            truthy = True
                            for crafting_block in g.mb.craftings:
                                try:
                                    if cinfo[craftable]["recipe"][crafting_block] > g.mb.craftings[crafting_block]:
                                        truthy = False
                                        break
                                except KeyError:
                                    truthy = False
                                    break
                            if truthy:
                                if g.player.stats["energy"]["amount"] - cinfo[craftable].get("energy", float("-inf")) >= 0:
                                    for recipe_block in cinfo[craftable]["recipe"]:
                                        if g.mb.craftings.get(recipe_block, float("-inf")) >= cinfo[craftable]["recipe"][recipe_block]:
                                            enough += 1
                                            g.mb.midblit_by_what.append(g.mb.craftings[recipe_block] // cinfo[craftable]["recipe"][recipe_block] * cinfo[craftable].get("amount", 1))
                                    if enough == len(cinfo[craftable]["recipe"]):
                                        g.mb.craftables[craftable] = g.mb.midblit_by_what
                        # blitting images
                        _x = mbr.centerx + mbr.width / 4
                        _y = mbr.centery
                        square_border_rect.topleft = (_x, _y)
                        for index, craftable in enumerate(g.mb.craftables):
                            if len(g.mb.craftables) >= 2 and index == g.mb.craftable_index:
                                win.renderer.blit(square_border_img, square_border_rect)
                            g.mb.midblit_by_what = g.mb.craftables[craftable]
                            draw_line(win.renderer, BLACK, mbr.center, (_x, _y))
                            if craftable in g.w.blocks:
                                img = g.w.blocks[craftable]
                                rect.update(_x, _y, img.width, img.height)
                                win.renderer.blit(img, rect)
                            elif craftable in g.w.tools:
                                img = g.w.tools[craftable]
                                rect.update(_x, _y, img.width, img.height)
                                win.renderer.blit(img, rect)
                            g.mb.midblit_by_what = min(g.mb.midblit_by_what)
                            g.mb.craftables[craftable] = g.mb.midblit_by_what
                            write(win.renderer, "midbottom", g.mb.midblit_by_what, orbit_fonts[15], BLACK, _x, _y + yo, tex=True)
                            _x += yo

                # furnace
                elif g.midblit == "furnace":
                    mbr = g.midblit_rect()
                    win.renderer.blit(furnace_img, mbr)
                    x = mbr.x
                    y = mbr.y
                    red = g.mb.reductant
                    ox = g.mb.oxidant

                    if all(ox):
                        # info
                        ox_info = fueinfo[ox[0]]
                        ox_img = g.w.blocks[ox[0]]
                        w, h = ox_img.width, ox_img.height
                        # images and rects
                        rem_img = shower_sprs[int(g.mb.oxidant_remnant)]
                        rem_rect = rem_img.get_rect(topleft=(x + 24 * S, y + 9 * S + 1))
                        arr_img = arrow_sprs[int(g.mb.oxidation_index)]
                        arr_rect = arr_img.get_rect(topleft=(x + 54 * S, y + 9 * S + 1))
                        # rendering step; finally
                        win.renderer.blit(rem_img, rem_rect)
                        win.renderer.blit(arr_img, arr_rect)

                    if ox[-1] is not None and ox[-1] > 1:
                        ox_rect = ox_img.get_rect(topleft=(x + 32 * S, y + 8 * S))
                        win.renderer.blit(ox_img, ox_rect)
                        write(win.renderer, "center", ox[1] - 1, orbit_fonts[12], BLACK, x + w / 2 + 32 * S - 1, y + 19 * S + 4 * S, tex=True)

                    if all(red):
                        red_img = g.w.blocks[red[0]]
                        w, h = red_img.width, red_img.height
                        red_rect = red_img.get_rect(topleft=(x + 11 * S, y + 8 * S))
                        win.renderer.blit(red_img, red_rect)
                        write(win.renderer, "center", red[1], orbit_fonts[12], BLACK, x + w / 2 + 11 * S - 1, y + 19 * S + 4 * S, tex=True)
                        if all(ox):
                            g.mb.oxidant_remnant += ox_info["sub"]
                            if g.mb.oxidant_remnant >= len(shower_sprs):
                                g.mb.oxidant_remnant = 0
                                g.mb.oxidant[1] -= 1
                            g.mb.oxidation_index += ox_info["mj"] * 0.001
                            if g.mb.oxidation_index >= len(arrow_sprs):
                                g.mb.oxidation_index = 0
                                if red[0] in finfo:
                                    c = red[0] + "_ck"
                                    if c == g.mb.cooked[0]:
                                        g.mb.cooked[1] += 1
                                    else:
                                        g.mb.cooked = [c, 1]
                                    g.mb.reductant[1] -= 1
                                ck = g.mb.cooked

                    if all(g.mb.cooked):
                        ck_img = g.w.blocks[ck[0]]
                        ck_rect = ck_img.get_rect(topleft=(x + 70 * S, y + 8 * S))
                        w, h = ck_img.width, ck_img.height
                        win.renderer.blit(ck_img, ck_rect)
                        write(win.renderer, "center", ck[1], orbit_fonts[12], BLACK, x + w / 2 + 70 * S - 1, y + 19 * S + 4 * S, tex=True)


                # anvil
                elif g.midblit == "anvil":
                    win.renderer.blit(anvil_img, workbench_rect)
                    x = workbench_rect.x + 30 / 2 + 25
                    y = workbench_rect.y + 30 + 30 / 2 + 10
                    sy = y
                    xo = 30 + 5
                    yo = 30 + 10
                    for smithing_block in g.mb.smithings:
                        # crafting material
                        draw_line(win.renderer, BLACK, (x + 30 / 2, y), workbench_center)
                        win.renderer.blit(g.w.blocks[smithing_block], (x, y))
                        write(win.renderer, "midright", g.mb.smithings[smithing_block], orbit_fonts[15], BLACK, x - 20, y)
                        y += yo
                        if (y - sy) / yo == 5:
                            y = sy
                            x += xo
                        # calculating receiving material
                        g.mb.smithables = SmartOrderedDict()
                        for smithable in ainfo:
                            g.mb.midblit_by_what = []
                            enough = 0
                            truthy = True
                            for smithing_block in g.mb.smithings:
                                try:
                                    if ainfo[smithable]["recipe"][smithing_block] > g.mb.smithings[smithing_block]:
                                        truthy = False
                                        break
                                except KeyError:
                                    truthy = False
                                    break
                            if truthy:
                                if g.player.stats["energy"]["amount"] - ainfo[smithable].get("energy", float("-inf")) >= 0:
                                    for recipe_block in ainfo[smithable]["recipe"]:
                                        if g.mb.smithings.get(recipe_block, float("-inf")) >= ainfo[smithable]["recipe"][recipe_block]:
                                            enough += 1
                                            g.mb.midblit_by_what.append(g.mb.smithings[recipe_block] // ainfo[smithable]["recipe"][recipe_block] * ainfo[smithable].get("amount", 1))
                                    if enough == len(ainfo[smithable]["recipe"]):
                                        g.mb.smithables[smithable] = g.mb.midblit_by_what
                        # blitting images
                        _x = workbench_center[0] + workbench_rect.width / 3
                        _y = workbench_center[1]
                        for index, smithable in enumerate(g.mb.smithables):
                            if len(g.mb.smithables) >= 2 and index == g.mb.smithable_index:
                                win.renderer.blit(square_border_img, (_x, _y))
                            g.mb.midblit_by_what = g.mb.smithables[smithable]
                            draw_line(win.renderer, BLACK, workbench_center, (_x, _y))
                            if smithable in g.w.blocks:
                                win.renderer.blit(g.w.blocks[smithable], (_x, _y))
                            elif smithable in g.w.tools:
                                win.renderer.blit(g.w.tools[smithable], (_x, _y))
                            g.mb.midblit_by_what = min(g.mb.midblit_by_what)
                            g.mb.smithables[smithable] = g.mb.midblit_by_what
                            write(win.renderer, "midbottom", g.mb.midblit_by_what, orbit_fonts[15], BLACK, _x, _y + yo)
                            _x += yo
                    if g.mb.smither is not None:
                        win.renderer.blit(g.w.tools[g.mb.smither], workbench_center)

                # gun crafter
                elif g.midblit == "gun-crafter":
                    mbr = g.midblit_rect()
                    # gun_crafter_base.blit(gun_crafter_img, (0, 0))
                    win.renderer.blit(gun_crafter_img, mbr)
                    for part, name in g.mb.gun_parts.items():
                        pos = gun_crafter_part_poss[part]
                        if name is None:
                            if part not in g.extra_gun_parts:
                                write(win.renderer, "center", "?", orbit_fonts[20], BLACK, mbr.x + pos[0], mbr.y + pos[1], tex=True)
                                #pygame.gfxdraw.aacircle(win.renderer, *pos, 5, BLACK)
                                #pygame.draw.circle(win.renderer, BLACK, pos, 5)
                        else:
                            img = g.w.blocks[name]
                            o = gun_crafter_part_poss[part]
                            r = img.get_rect(topleft=(mbr.x + o[0], mbr.y + o[1]))
                            win.renderer.blit(img, r)
                    # win.renderer.blit(gun_crafter_base, workbench_rect)
                    if is_gun_craftable():
                        write(win.renderer, "center", "Gun is ready to craft", orbit_fonts[18], BLACK, workbench_rect.centerx, workbench_rect.centery + 30, tex=True)

                # magic table
                elif g.midblit == "magic-table":
                    win.renderer.blit(magic_table_img, workbench_rect)
                    yo = 30 + 10
                    x = crafting_x
                    y = crafting_y - yo
                    tx = crafting_x - workbench_rect.width / 3
                    ty = crafting_y
                    for magic_orb in g.mb.magic_orbs:
                        if g.mb.magic_tool is not None:
                            draw_line(win.renderer, BLACK, (tx, ty), (x, y))
                        win.renderer.blit(g.w.blocks[magic_orb], (x, y))
                        y += yo
                    if g.mb.magic_tool is not None:
                        win.renderer.blit(g.w.tools[g.mb.magic_tool], (tx, ty))

                # altar
                elif g.midblit == "altar":
                    win.renderer.blit(altar_img, workbench_rect)
                    x = workbench_rect.x + 30 / 2 + 25
                    y = workbench_rect.y + 30 + 30 / 2 + 10
                    sy = y
                    xo = 30 + 5
                    yo = 30 + 10
                    for offering in g.mb.offerings:
                        win.renderer.blit(g.w.blocks[offering], (x, y))
                        write(win.renderer, "midright", g.mb.offerings[offering], orbit_fonts[15], BLACK, x - 20, y)

                # chest
                elif g.midblit == "chest":
                    win.renderer.blit(chest_template, chest_rect)
                    ogx, ogy = chest_rect_start
                    x, y = ogx, ogy
                    row = 0
                    for name, amount in g.chest:
                        if name is not None:
                            write(win.renderer, "center", amount, orbit_fonts[15], g.w.text_color, x + 14, y + 39)
                            win.renderer.blit(g.w.blocks[name], (x, y))
                        x += 33
                        if row == 4:
                            x = ogx
                            y += 51
                            row = -1
                        row += 1
                    win.renderer.blit(square_border_img, g.chest_pos)
                    for rect in chest_rects:
                        if rect.collidepoint(g.mouse):
                            with suppress(IndexError, AttributeError):
                                write(win.renderer, "center", bshow(g.chest[chest_indexes[rect.topleft]][0]), orbit_fonts[15], g.w.text_color, workbench_rect.centerx, 150)

                # tool crafter
                elif g.midblit == "tool-crafter":
                    # main
                    mbr = g.midblit_rect()
                    # hitboxes
                    if pw.show_hitboxes:
                        draw_rect(win.renderer, RED, pw.tool_crafter_selector_range_rect)
                    # rest
                    centerx = mbr.x + tool_crafter_sword_width + tool_crafter_info_width / 2
                    win.renderer.blit(tool_crafter_img, mbr)
                    # update positions of the ones you know which ones i forgot name brain fog
                    g.mb.sword.oox, g.mb.sword.ooy = (
                        mbr.x + tool_crafter_sword_width / 2,
                        mbr.y + (tool_crafter_rect.height + pw.tool_crafter_kwargs["height"]) / 2
                    )
                    # composes update and sword
                    # for index, compos in enumerate(g.mb.compoi):
                    #     compos.oox, compos.oy = (
                    #         mbr.x + tool_crafter_sword_width + tool_crafter_info_width / 2 + compos.oox,
                    #         mbr.y + 60
                    #     )
                    #     compos.update()
                    g.mb.sword.update()

                    # radar charts
                    fill_rect(win.renderer, RED, (g.mb.sword.oox - 3, g.mb.sword.ooy - 3, 6, 6))
                    # radar chart
                    g.mb.radar_chart.x, g.mb.radar_chart.y = (mbr.centerx + 50, mbr.centery)
                    # g.mb.radar_chart.update()
                    # tool crafter button
                    pw.tool_crafter_selector.rect.topleft = (mbr.x + 3, mbr.y + 3)
                    pw.tool_crafter_rotate.rect.topleft = (mbr.x + 3, mbr.y + 3 + pw.tool_crafter_selector.rect.height)
                    # draw the connections
                    num_atoms = sum(v.stoic for v in g.mb.crystals.values())
                    molar_ratia = {}
                    for xo, (name, lattice) in enumerate(g.mb.crystals.items()):
                        # draw_line(win.renderer, (g.mb.sword.oox, g.mb.sword.ooy), (crystal.oox, crystal.ooy), BLACK)
                        # render the lattice structures
                        crystal = lattice.crystal
                        crystal.oox, crystal.ooy = mbr.topleft
                        crystal.oox += 182 + xo * 100
                        crystal.ooy += 80
                        x, y = crystal.oox, crystal.ooy
                        write(win.renderer, "midtop", name, orbit_fonts[15], WHITE, x, y + 50, tex=True)
                        crystal.update()
                        # remaining text
                        molar_ratio = lattice.stoic / num_atoms
                        molar_ratia[name] = molar_rsatio
                        write(win.renderer, "midtop", f"{molar_ratio:.2f}", orbit_fonts[12], MINT, x, y + 70, tex=True)
                    if g.mb.crystals:
                        # cofigurational entropy
                        write(win.renderer, "midtop", "".join(oinfo[name]["atom"] for name in sorted(g.mb.crystals)), orbit_fonts[15], WHITE, centerx, y - 70, tex=True)
                        s_conf = round(log(len(g.mb.crystals)), 2)
                        # calculating yield strength based on VEC and average atomic size
                        vec = sum(oinfo[name]["VEC"] * molar_ratia[name] for name in g.mb.crystals)
                        ea = sum(oinfo[name]["e/a"] * molar_ratia[name] for name in g.mb.crystals)
                        avg_radius = sum(oinfo[name]["radius"] * molar_ratia[name] for name in g.mb.crystals)
                        if ea < 1.53:
                            if avg_radius < 1.365:
                                ptrint("hcp")
                            else:
                                ptrint("fcc")
                        elif ea > 1.88:
                            if avg_radius > 1.387:
                                ptrint("hcp")
                            else:
                                ptrint("bcc")
                        else:
                            ptrint("bcc and fcc")
                        impact_toughness = 3461.4 * vec ** 3 - 80552 * vec ** 2 + 625259 * vec - 2 * 10 ** 6
                        write(win.renderer, "midtop", f"VEC = {vec:.2f}", orbit_fonts[15], YELLOW, centerx, y + 90 , tex=True)
                        write(win.renderer, "midtop", f"impact toughness  = {impact_toughness:.2f}", orbit_fonts[15], YELLOW, centerx, y + 120 , tex=True)

                elif g.midblit == "frac-dist":
                    mbr = g.midblit_rect()
                    mbr.y -= 120
                    win.renderer.blit(midblits["frac-dist"], mbr)
                    for y, elem in enumerate(gas_blocks):
                        write(win.renderer, "center", g.mb.frac_dist[elem], orbit_fonts[16], BLACK, mbr.centerx, mbr.y + y * 33 + 30, tex=True)
                    for gas in all_gases:
                        gas.update()

                # show background selector
                if g.mod == 1:
                    if no_widgets(Entry):
                        if g.player.main == "block" and g.player.block:
                            write(win.renderer, "center", "[BACKGROUND]", orbit_fonts[13], g.w.text_color, win.width / 2 + 20 + hotbar_xo, 110)

                # applyping regeneration (player bars)
                if g.w.mode == "adventure":
                    if g.player.stats["lives"]["amount"] + 1 <= 100:
                        if ticks() - g.player.stats["lives"]["last_regen"] >= g.player.stats["lives"]["regen_time"]:
                            g.player.stats["lives"]["amount"] += 1
                            g.player.stats["lives"]["regen_time"] -= 0.5
                            g.player.stats["lives"]["last_regen"] = ticks()

                    # player food chart
                    if "image" in g.player.food_pie and "rect" in g.player.food_pie:
                        g.player.food_pie["rect"].midbottom = (g.player.rrect.centerx, g.player.rrect.top - 25)
                        win.renderer.blit(g.player.food_pie["image"], g.player.food_pie["rect"])
                        if pw.show_hitboxes:
                            (win.renderer, GREEN, g.player.food_pie["rect"], 1)

                if g.saving_structure:
                    write(win.renderer, "midtop", "structure", orbit_fonts[9], DARK_GREEN, win.width - 30, 50, tex=True)

            # post-scale home
            elif g.stage == "home":
                fill_rect(win.renderer, LIGHT_GRAY, (0, 0, *win.size))

                write(win.renderer, "center", "Blockingdom", orbit_fonts[50], BLACK, win.width // 2, 58, tex=True)
                sp = 0.1
                xo = (win.width / 2 - g.mouse[0]) * sp
                yo = (win.height / 2 - g.mouse[1]) * sp - 200
                #win.renderer.blit(g.home_bg_img, (win.width / 2 - g.home_bg_size[0] / 2 + xo, win.height / 2 - g.home_bg_size[1] / 2 + yo))
                if Platform.os == "windows":
                    #win.renderer.blit(g.menu_surf, (0, 0))
                    pass

                #win.renderer.blit(logo_img, (win.width / 2 - logo_img.width / 2, 100 + sin(ticks() * 0.0015) * 7))
                # home sprites were here
                if g.home_stage == "worlds":
                    # worlds buttons were here
                    pass

                elif g.home_stage == "settings":
                    # settings buttons were here
                    pass

                all_messageboxes.update()

                # updating the widgets
                updating_buttons = [button for button in iter_buttons() if not button.disabled]
                updating_worldbuttons = [worldbutton for worldbutton in all_home_world_world_buttons if is_drawable(worldbutton)]
                updating_settingsbuttons = [settingsbutton for settingsbutton in all_home_settings_buttons if is_drawable(settingsbutton) and not isinstance(settingsbutton, StaticOptionMenu)]
                updating_static_buttons = [static_button for static_button in all_home_world_static_buttons if is_drawable(static_button)]
                # update_button_behavior(updating_worldbuttons + updating_buttons + updating_settingsbuttons + updating_static_buttons + [button_s, button_w, button_c])
                all_home_sprites.update()

                if g.home_stage == "worlds":
                    all_home_world_world_buttons.update()
                    all_home_world_static_buttons.update()

                elif g.home_stage == "settings":
                    all_home_settings_buttons.update()

            # widgets
            draw_and_update_widgets()
            if g.selected_widget is not None:
                draw_rect(win.renderer, ORANGE, g.selected_widget.rect)

            # late stuff for debugging
            for rect, color in late_rects:
                fill_rect(win.renderer, color, rect)

            # updating the window
            for string in strings:
                string.draw()
                string.src.draw()
                string.dest.draw()

            # show controller battery
            if controller.joystick is not None:
                battery = str(controller.joystick.get_power_level())
                write(win.renderer, "topright", f"{controller.name} [{battery}]{'%' if isinstance(battery, int) else ''}", orbit_fonts[13], BLACK, win.width - 8, 6, tex=True)

            """
            img = g.w.blocks["dynamite"]
            mr = pygame.Rect(g.mouse, (img.width, img.height))
            win.renderer.blit(img, mr)
            """

            # poly.update()
            # night.alpha = 255 * (sin(ticks() * 0.002) + 1) * 0.5

            # i += 0.1
            # if i >= 4:
            #     i = 0
            # image = anim.imgs["Necromancer"]["run"]["images"][int(i)]
            # rect = anim.rects["Necromancer"]["run"]
            # rect = pygame.Rect(rect.x + 4 * 100, rect.y + 50, *rect.size)
            # win.renderer.blit(image, rect)

            # even more debug
            # _light_rect.center = g.mouse
            # win.renderer.blit(light_tex, _light_rect)

            # zoom window for some cool reason
            if win.target_zoom:
                m = 0.1
                win.renderer.scale = (
                    win.renderer.scale[0] + m * (win.target_zoom[0] - win.renderer.scale[0]),
                    win.renderer.scale[1] + m * (win.target_zoom[1] - win.renderer.scale[1]),
                )
            else:
                # scale
                win.renderer.scale = win.scale

            # refreshing the window
            win.renderer.present()

            # pybag
            await asyncio.sleep(0)

            if ExitHandler.must_save:
                empty_group(all_drops)
                destroy_widgets()
                ExitHandler.save("home")
                g.stage = "home"
                g.menu = False

        # cleanup
        if cprof:
            pritn("CAUTION - CPROFILE WAS ACTIVE")
        ExitHandler.save("quit")

if __name__ == "__main__":
    # main(debug=g.debug)
    # asyncio.run(main(debug=g.debug))
    import cProfile; cProfile.run("asyncio.run(main(debug=g.debug, cprof=True))", sort="cumtime")
