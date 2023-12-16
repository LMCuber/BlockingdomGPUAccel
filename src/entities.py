from pyengine.pgbasics import *
#
from .prim_data import *
from .settings import *


# B A S E  E N T I T Y --------------------------------------------------------------------------------- #
class BaseEntity(SmartVector):  # removed Scrollable inheritance, added SmartVector
    _img_metadata = {
            "chicken": {
                "walk": {"frames": 4},
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
    def __init__(self, img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, **kwargs):
        # init
        self.anim = 0
        self.species = traits[0]
        self.init_images("walk", "images")
        self.og_chunk_index = self.chunk_index = chunk_index
        self.x = chunk_index[0] * CW * BS + rel_pos[0] * BS
        self.y = chunk_index[1] * CH * BS + rel_pos[1] * BS - 100
        self.pos = self.x, self.y
        self._rect = self.image.get_rect()
        self.rect = self._rect.copy()
        self.smart_vector = smart_vector
        self.traits = traits
        self.block_data = []
        # Arbeehdee and Rilocto
        self.relocate_to = None
        self.request_block_data = True
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
            self.health_bar = pygame.Rect(0, 0, 0, 0)
        if "demon" in self.traits:
            self.bar_rgb = lerp(RED, PURPLE, 50) + lerp(PURPLE, RED, 51)
            self.demon = True
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

    @property
    def sign(self):
        return sign(self.xvel)

    def update__rect(self):
        self._rect.topleft = (int(self.x), int(self.y))

    # the base update that every entity undergoes
    def update(self, dt):
        self.draw()
        return
        # update the specific update of the species
        self.spec_update()
        # init rect
        # move x
        self.collide()
        # bok-bok
        if self.species == "bok-bok":
            # direction change
            if (g.player._rect.centerx > self._rect.centerx and self.xvel < 0) \
                    or (self._rect.centerx > g.player._rect.centerx and self.xvel > 0):
                delay(self.set_xvel, 0.6, -self.xvel)
            self.jump_over_obstacles()

            # colliding with the player
            if self._rect.colliderect(g.player._rect):
                # g.player.flinch(0.1 * self.sign, -2)
                pass

        # rest
        if not self.glitching:
            getattr(self, "spec_animate", self.animate)(dt)

        self.draw()

        # perhaps request relocation?
        self.check_chunk_borders()

        self.regenerate()
        self.display_hp()

    def collide(self):
        self.x += self.xvel
        # update _rect
        self.update__rect()
        # collide x
        for col in self.get_cols():
            if self.xvel > 0:
                self.right = col.left
            else:
                self.left = col.left
        self.update__rect()
        # move y
        self.yvel += self.gravity
        self.y += self.yvel
        self.update__rect()
        # collide y
        for col in self.get_cols():
            self.bottom = col.top
            self.yvel = 0
        # update _rect
        self.update__rect()
        # scroll the actual "rect"
        self.rect.topleft = (self._rect.x - g.scroll[0], self._rect.y - g.scroll[1])

    def check_chunk_borders(self):
        chunk_x = floor(self.centerx / (CW * BS))
        chunk_y = floor(self.centery / (CH * BS))
        # print(self.centerx / (CW * BS), self.centery / (CH * BS))
        if (chunk_x, chunk_y) != self.chunk_index:
            self.relocate_to = (chunk_x, chunk_y)
            self.request_block_data = True

    def jump_over_obstacles(self, yvel=-2):
        s = 1 if self.xvel >= 0 else -1
        ahead = pygame.Rect(self._rect.x + 10 * s, self._rect.y, *self.rect.size)
        if self.get_cols(ahead):
            self.yvel = yvel

    def set_xvel(self, value):
        self.xvel = value

    def get_cols(self):
        block_x = floor(self.x / BS)
        block_y = floor(self.y / BS)
        block_pos = (block_x, block_y)
        xrange = (-1, 2)
        yrange = (0, 3)
        for yo in range(*yrange):
            for xo in range(*xrange):
                chunk, pos = correct_tile(self.chunk_index, block_pos, xo, yo)
                if chunk in g.w.block_data:
                    if pos in g.w.block_data[chunk]:
                        block = g.w.block_data[chunk][pos]
                        _rect, rect = block._rect, block.rect
                        draw_rect(win.renderer, rect, RED)
                        if self.rect.colliderect(rect):
                            yield _rect
                            # pass
        return []

    def get_rects(self):
        return [data._rect for data in self.block_data]

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

    def init_images(self, img_data, type_):
        if type_ == "images":
            # load surfaces
            self.images = BaseEntity.imgs[self.species][img_data]
            self.h_images = [flip(img, True, False) for img in self.images]
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
        if self.taking_damage:
            #image.fill((255, 0, 0, 125), special_flags=BLEND_RGB_ADD)
            # image = red_filter(self.image.to_surface())
            # image = Texture.from_surface(win.renderer, image)
            if not self.demon:
                win.renderer.blit(self.red_filter, self.rect)
        win.renderer.blit(self.image, self.rect)

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
        if self.taking_damage and ticks() - self.last_took_damage >= 300:
            self.taking_damage = False
        if self.glitching and ticks() - self.last_glitched >= 300:
            self.glitching = False

    def display_hp(self):
        if self.hp < self.max_hp:
            w = self.hp / self.max_hp * self.health_bar_border.width
            self.health_bar.update(self.health_bar.topleft, (w, self.health_bar_border.height))
            self.health_bar_border.centerx = self.rect.centerx
            self.health_bar_border.bottom = self.rect.top - 20
            self.health_bar.topleft = self.health_bar_border.topleft
            fill_rect(win.renderer, self.health_bar, PURPLE)
            draw_rect(win.renderer, self.health_bar_border, BLACK)

    def take_damage(self, amount):
        self.taking_damage = True
        self.last_took_damage = ticks()
        self.hp -= amount


# M O B S ------------------------------------------------------------------------------------------------ #
class Chicken(BaseEntity):
    def __init__(self, img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, **kwargs):
        super().__init__(img_data, traits, chunk_index, rel_pos, anchor="bottomleft", smart_vector=True, **kwargs)
        self.xvel = 0.3 * 0
        self.gravity = 0.002

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
        self.gravity = 0.002 * 0
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
        self.gravity = 0.002 * 0
        self.max_hp = self.hp = 250
        self.drops = {"chicken": 1}

    def spec_update(self):
        self.movex(1)
        self.jump_over_obstacles()
        self.xvel, self.yvel = two_pos_to_vel(self._rect.center, g.player._rect.center)
        pass
