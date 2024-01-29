from pyengine.pgbasics import *
#
from .prim_data import *
from .settings import *


# C O N S T A N T S
APURPLE = PURPLE[:3] + (30,)

# B A S E  E N T I T Y --------------------------------------------------------------------------------- #
class BaseEntity(SmartVector):  # removed Scrollable inheritance, added SmartVector
                                # thank you past Leo for this, now I'm stuck on the fucking chicken bug manipulating spacetime
    _img_metadata = {
            "chicken": {
                "walk": {"frames": 2},
            },

            "portal": {
                "walk": {"frames": 7},
            },

            "camel": {
                "walk": {"img_mult": randf(0.8, 1.2)},
            },

            "fluff_camel": {
                "walk": {"frames": 4},
            },

            "penguin": {
                "walk": {"frames": 4},
                "penguin_sliding": {"frames": 4, "rotation": -90}
            },

            "snowman": {
                "walk": {"frames": 4},
            },

            "hallowskull": {
                "walk": {"frames": 4},
                "rise": {"frames": 5},
            },

            "keno": {
                "idle": {"frames": 3},
                "walk": {"frames": 10},
            },

            "bok-bok": {
                "walk": {"frames": 4},
            },
    }
    imgs = {}
    for mob_type in os.listdir(path("assets", "Images", "Mobs")):
        imgs[mob_type] = {}
        for mob_file in os.listdir(path("assets", "Images", "Mobs", mob_type)):
            mob_name, _ = os.path.splitext(mob_file)
            kwargs = _img_metadata[mob_type][mob_name]
            img = imgload3("assets", "Images", "Mobs", mob_type, mob_file, **kwargs)
            imgs[mob_type][mob_name] = img
    def __init__(self, img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, flip_flip=False, **kwargs):
        # init
        self.dead = False
        self.dying = False
        self.anim = 0
        self.species = traits[0]
        self.init_images("walk", "images", flip_flip=flip_flip)
        self.demon = "demon" in traits
        self.og_chunk_index = self.chunk_index = chunk_index
        self.rel_pos = rel_pos
        self.x = chunk_index[0] * CW * BS + rel_pos[0] * BS
        self.y = chunk_index[1] * CH * BS + rel_pos[1] * BS
        self.pos = self.x, self.y
        self._rect = self.image.get_rect()
        self.rect = self._rect.copy()
        self.smart_vector = smart_vector
        self.traits = traits
        self.block_data = []
        self.gravity = 0.08
        self.grounded = True
        # Arbeehdee and Rilocto
        self.relocate_to = None
        self.request_block_data = True
        self.dialogue = False
        # rest
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
        self.index = 0
        self.paused = False

        # species
        if self.species == "penguin":
            self.penguin_spinning = False
            self.penguin_sliding = False

        # extra traits
        if "mob" in self.traits:
            self.health_bar_border = pygame.Rect(0, 0, 80, 12)
            self.health_bar_prev = pygame.Rect(0, 0, 0, 0)
            self.health_bar = pygame.Rect(0, 0, 0, 0)
        if "demon" in self.traits:
            self.bar_rgb = lerp(RED, PURPLE, 50) + lerp(PURPLE, RED, 51) + (255,)
            self.demon = True
        else:
            self.bar_rgb = bar_rgb
        # lasts
        self.taking_damage = False
        self.last_took_damage = ticks()
        self.glitching = False
        self.last_glitched = ticks()

        # other attrs
        self.ray_cooldown = False
        self.dying = False
        self.initted_images = False

        # glitching attrs
        # r
        self.mask_surf_red = self.mask.to_surface(setcolor=(255, 40, 40, 127))
        self.mask_surf_red.set_colorkey(BLACK)
        self.mask_surf_red = Texture.from_surface(win.renderer, self.mask_surf_red)
        # g
        self.mask_surf_green = self.mask.to_surface(setcolor=(0, 255, 0, 127))
        self.mask_surf_green.set_colorkey(BLACK)
        self.mask_surf_green = Texture.from_surface(win.renderer, self.mask_surf_green)
        # b
        self.mask_surf_blue = self.mask.to_surface(setcolor=(0, 0, 255, 127))
        self.mask_surf_blue.set_colorkey(BLACK)
        self.mask_surf_blue = Texture.from_surface(win.renderer, self.mask_surf_blue)
        # damage mask
        damage_mask = self.mask.to_surface(setcolor=(255, 0, 0, 120))
        damage_mask_f = flip(damage_mask, True, False)
        damage_mask.set_colorkey(BLACK)
        damage_mask_f.set_colorkey(BLACK)
        damage_mask = Texture.from_surface(win.renderer, damage_mask)
        damage_mask_f = Texture.from_surface(win.renderer, damage_mask_f)
        if flip_flip:
            damage_mask, damage_mask_f = damage_mask_f, damage_mask
        self.damage_mask = {
            1: damage_mask,
            -1: damage_mask_f
        }

    def update__rect(self, *args):
        # print(self.y, self._rect.y, args)
        self._rect.topleft = (int(self.x), int(self.y))

    # the base update that every entity undergoes
    # entity update
    def update(self, dt, show_hitboxes, dialogue):
        if not self.dead:
            self.show_hitboxes = show_hitboxes
            # update the specific update of the species
            self.spec_update()
            # init rect
            # move x
            self.collide(dialogue)

            # bok-bok
            if self.species == "bok-bok":
                # direction change
                if (g.player._rect.centerx > self._rect.centerx and self.xvel < 0) \
                        or (self._rect.centerx > g.player._rect.centerx and self.xvel > 0):
                    delay(self.set_xvel, 0.6, -self.xvel)
                self.jump_over_obstacles()

                # colliding with the player
                if self._rect.colliderect(g.player._rect):
                    # g.player.flinch(0.1 * self.xbound, -2)
                    pass

            # collision with player
            if g.player.anim_type == "stab" and self.rect.colliderect(g.player.rect):
                self.take_damage(40)
                self.flinch(5)

            # rest
            if not self.glitching:
                getattr(self, "spec_animate", self.animate)(dt)

            self.draw()

            self.regenerate()
            self.display_hp()

    def collide(self, dialogue):
        if not dialogue:
            # move y
            self.yvel += self.gravity
            self.y += self.yvel
            self.update__rect()
            # collide y
            for col in self.get_cols(hor=False):
                self.bottom = col.top
                self.yvel = 0
                self.grounded = True
                if self.taking_damage:
                    self.stop_taking_damage()
            self.update__rect()
            self.x += self.xvel
            self.update__rect()
            # collide x
            for col in self.get_cols(hor=True):
                if self.xvel > 0:
                    self.right = col.left
                else:
                    self.left = col.left
            self.update__rect()
            # scroll the actual "rect"
        self.rect.topleft = (self._rect.x - g.scroll[0], self._rect.y - g.scroll[1])

    def check_chunk_borders(self):
        chunk_x = floor(self.x / (CW * BS))
        chunk_y = floor(self.y / (CH * BS))
        if (chunk_x, chunk_y) != self.chunk_index:
            self.relocate_to = (chunk_x, chunk_y)

    def jump_over_obstacles(self, yvel=-3):
        m = 1 if self.xvel >= 0 else -1
        h = 2 * BS
        _ahead = pygame.Rect(self._rect.x + m * 10, self._rect.y - self._rect.height, self._rect.width, h)
        ahead = pygame.Rect(_ahead.x - g.scroll[0], _ahead.y - g.scroll[1], *_ahead.size)
        if self.show_hitboxes:
            draw_rect(win.renderer, PURPLE, ahead)
        if self.grounded:
            cols = self.get_cols(rep_rect=_ahead)
            if len(cols) >= 2:
                self.xvel *= -1
                # self.dialogue = True
            elif len(cols) == 1:
                self.set_yvel(yvel)

    def set_xvel(self, value):
        self.xvel = value

    def get_cols(self, hor=True, return_type="default", rep_rect=None):  # replacement rect
        _self_rect = rep_rect if rep_rect is not None else self._rect
        self_rect = pygame.Rect(_self_rect.x - g.scroll[0], _self_rect.y - g.scroll[1], *_self_rect.size)
        block_x = floor(self.x / BS)
        block_y = floor(self.y / BS)
        block_pos = (block_x, block_y)
        xrange = (-4, 5)
        yrange = (-1, 4)
        ret = []
        good = lambda: block_pos == (16, 5) and self.chunk_index == (0, 0) and not hor
        # pritn(self.x / BS, self.y / BS)
        if self.show_hitboxes and rep_rect is None:
            draw_rect(win.renderer, GREEN, self_rect)
        for yo in range(*yrange):
            for xo in range(*xrange):
                chunk = self.chunk_index
                pos = (block_pos[0] + xo, block_pos[1] + yo)
                chunk, pos = correct_tile(self.chunk_index, block_pos, xo, yo)
                if chunk in g.w.data:
                    if pos in g.w.data[chunk]:
                        block = g.w.data[chunk][pos]
                        if is_hard(block.name):
                            _rect = block._rect
                            rect = pygame.Rect(_rect.x - g.scroll[0], _rect.y - g.scroll[1], BS, BS)
                            if self.show_hitboxes:
                                draw_rect(win.renderer, ORANGE[:3] + (125,) if hor else PURPLE[:3] + (125,), rect)
                            if _self_rect.colliderect(_rect):
                                if self.show_hitboxes:
                                    fill_rect(win.renderer, ORANGE[:3] + (125,) if hor else PURPLE[:3] + (125,), rect)
                                if return_type == "default":
                                    ret.append(_rect)
                            if return_type == "_rect":
                                ret.append(_rect)

        # print("x" if hor else "y", block_pos, self.chunk_index, _self_rect.y, ret)
        return ret

    def get_rects(self):
        return [data._rect for data in self.block_data]

    def flinch(self, height):
        def inner():
            self.set_yvel(-sqrt(2 * self.gravity * height))
            fv = 0.6
            og_xvel = self.xvel
            self.xvel = fv if g.player.direc == "right" else -fv
            sleep(0.4)
            self.xvel = og_xvel
        DThread(target=inner).start()

    def glitch(self):
        self.last_glitched = ticks()
        self.glitching = True

    def stop_taking_damage(self):
        if self.taking_damage:
            self.xvel = self.def_xvel
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
    def x_taken(self):
        return self._rect.x - self.og_pos[0]

    @property
    def y_taken(self):
        return self._rect.y - self.og_pos[1]

    def get_rect(self):
        return self._rect

    def init_images(self, img_data, type_, flip_flip=False):
        if type_ == "images":
            # load surfaces
            self.images = BaseEntity.imgs[self.species][img_data]
            self.h_images = [flip(img, True, False) for img in self.images]
            if flip_flip:
                self.images, self.h_images = self.h_images, self.images
            img = self.images[0]
            # init mask
            self.mask = pygame.mask.from_surface(img)
            # load textures
            self.images = [Texture.from_surface(win.renderer, img) for img in self.images]
            self.h_images = [Texture.from_surface(win.renderer, img) for img in self.h_images]
            self.image = self.images[0]
            # load rest
            self.red_filter = pygame.Surface((30, 30))
            self.red_filter.fill(RED)
            self.red_filter = Texture.from_surface(win.renderer, self.red_filter)

    def set_yvel(self, value):
        self.yvel = value
        if value < 0:
            self.grounded = False

    def movex(self, amount):
        if not self.dying:
            self.x += amount
            self.dx += amount
            if self.dx >= 30:
                self.dx = 0
                self.index += 1

    def draw(self):  # entity draw
        if self.glitching:
            o = S * 2
            win.renderer.blit(self.mask_surf_red, self.rect.move(-o, 0))
            win.renderer.blit(self.mask_surf_green, self.rect.move(o, 0))
            win.renderer.blit(self.mask_surf_blue, self.rect.move(0, -o))
        # blit mob
        win.renderer.blit(self.image, self.rect)
        # blit mob blood
        if self.taking_damage:
            #image.fill((255, 0, 0, 125), special_flags=BLEND_RGB_ADD)
            # image = red_filter(self.image.to_surface())
            # image = Texture.from_surface(win.renderer, image)
            if not self.demon:
                win.renderer.blit(self.damage_mask[self.xbound], self.rect)

    def animate(self, dt):
        self.anim += g.p.anim_fps * dt
        try:
            self.images[int(self.anim)]
        except IndexError:
            self.anim = 0
        finally:
            self.image = (self.images if self.xvel <= 0 else self.h_images)[int(self.anim)]

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
                self.image = (self.images if self.xvel <= 0 else self.h_images)[int(self.anim)]
        if not self.penguin_spinning and not self.penguin_sliding and chance(1 / 500):
            self.penguRin_spinning = True
        elif not self.penguin_sliding and not self.penguin_spinning and chance(1 / 1000):
            self.penguin_sliding = True
            self.xvel = 0.4
        elif self.penguin_sliding and chance(1 / 500):
            self.penguin_sliding = False
            self.xvel = 0.2

    def regenerate(self):
        # if self.taking_damage and ticks() - self.last_took_damage >= 1000:
        #     self.taking_damage = False
        # if self.glitching and ticks() - self.last_glitched >= 300:
        #     self.glitching = False
        pass

    def display_hp(self):
        if self.hp < self.max_hp:
            # discrete logistic curve for smooth ass animation (smort)
            self.prev_hp = self.prev_hp + 0.0005 * self.prev_hp * (self.hp - self.prev_hp)
            # rest (dum dum)
            w = self.hp / self.max_hp * self.health_bar_border.width
            pw = self.prev_hp / self.max_hp * self.health_bar_border.width
            self.health_bar_prev.update(self.health_bar.topleft, (pw, self.health_bar_border.height))
            self.health_bar.update(self.health_bar.topleft, (w, self.health_bar_border.height))
            self.health_bar_border.centerx = self.rect.centerx
            self.health_bar_border.bottom = self.rect.top - 20
            self.health_bar.topleft = self.health_bar_border.topleft
            fill_rect(win.renderer, PINK, self.health_bar_prev)
            fill_rect(win.renderer, PURPLE, self.health_bar)
            draw_rect(win.renderer, BLACK, self.health_bar_border)
            if self.hp == 0:
                if self.prev_hp / self.hp_before_death <= 0.35:
                    self.die()

    def take_damage(self, amount):
        if not self.taking_damage:
            self.taking_damage = True
            self.last_took_damage = ticks()
            self.prev_hp = self.hp
            if self.hp - amount <= 0:
                self.hp_before_death = self.hp
                self.hp = 0
                self.die()
            else:
                self.hp -= amount

    def die(self):
        self.dead = True
        self.final_rects = self.get_cols(return_type="_rect")


# M O B S ------------------------------------------------------------------------------------------------ #
class Chicken(BaseEntity):
    def __init__(self, img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, **kwargs):
        super().__init__(img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, flip_flip=True, **kwargs)
        self.drops = {"chicken": 2}
        self.def_xvel = self.xvel = 0.3
        self.max_hp = self.hp = 70

    def spec_update(self):
        self.jump_over_obstacles()


class FluffCamel(BaseEntity):
    def __init__(self, img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, **kwargs):
        super().__init__(img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, flip_flip=True, **kwargs)
        self.def_xvel = xvel = 0.3
        self.max_hp = self.hp = 70

    def spec_update(self):
        # self.movex(1)
        # self.jump_over_obstacles()
        pass


# D E M O N S -------------------------------------------------------------------------------------------- #
class Hallowskull(BaseEntity):
    chance = 100
    def __init__(self, img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, **kwargs):
        super().__init__(img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, **kwargs)
        self.def_xvel = self.xvel = 0.3 * 0
        self.max_hp = self.hp = 250
        self.drops = {"chicken": 1}

    def spec_update(self):
        # self.movex(1)
        # self.jump_over_obstacles()
        # self.xvel, self.yvel = two_pos_to_vel(self._rect.center, g.player._rect.center)
        pass


class Keno(BaseEntity):
    chance = 100
    def __init__(self, img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, **kwargs):
        super().__init__(img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, **kwargs)
        self.def_xvel = self.xvel = 0.3 * 0
        self.max_hp = self.hp = 250
        self.drops = {"chicken": 1}

    def spec_update(self):
        # self.movex(1)
        # self.jump_over_obstacles()
        # self.xvel, self.yvel = two_pos_to_vel(self._rect.center, g.player._rect.center)
        pass
