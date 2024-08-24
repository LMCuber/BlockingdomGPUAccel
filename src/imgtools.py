import pygame
from pygame._sdl2.video import Window, Renderer, Texture, Image
import os
import pymunk
from math import floor, ceil


def T(surf):
    return Texture.from_surface(win.renderer, surf)


def I(surf):
    return Image(T(surf))


class WindowHandler:
    def __init__(self, size, scale=(1, 1), *args, debug=False, vsync=0, gpu_accel=True, **kwargs):
        self.gpu_accel = gpu_accel
        if self.gpu_accel:
            self.window = Window(title=f"Blockingdom [{size[0]}x{size[1]}]", size=size)
            self.window.resizable = True
            self.renderer = Renderer(self.window, vsync=vsync)
            self.scale = scale
            self.surf_renderer = pygame.Surface(size, pygame.SRCALPHA)
            self.rect = pygame.Rect(0, 0, *size)
        else:
            self.window = pygame.display.set_mode(size)
            self.renderer = self.window.get_surface()
        self.size = size
        self.width, self.height = self.size
        self.width //= self.scale[0]
        self.height //= self.scale[1]
        self.center = [s // 2 for s in size]
        self.centerx, self.centery = self.center
        self.space = pymunk.Space()
        self.space.gravity = (0, -900)
        self.target_zoom = []

    def update_caption(self):
        """pygame.display.set_caption("\u15FF"   # because
                                   "\u0234"      # because
                                   "\u1F6E"      # because
                                   "\u263E"      # because
                                   "\u049C"      # because
                                   "\u0390"      # because
                                   "\u2135"      # because
                                   "\u0193"      # because
                                   "\u15EB"      # because
                                   "\u03A6"      # because
                                   "\u722A"
                                   "")  # because"""
        pygame.display.set_caption(f"Blockingdom {System.version}")


S = 3
BP = 10
BS = BP * S
HL, VL = 27, 20
L = VL * HL
CW, CH = 16, 16
MHL = HL * BS / S
MVL = VL * BS / S
wb_icon_size = 300, 70
# win = WindowHandler((1280, 720), scale=(3, 3))
win = WindowHandler((1280, 720), scale=(1, 1))
# win = WindowHandler((pygame.display.Info().current_w, pygame.display.Info().current_h))
H_CHUNKS = floor(win.width / (CW * BS)) + 2 * (win.width / (CW * BS) != 0) + 1
V_CHUNKS = floor(win.height / (CH * BS)) + 2 * (win.height / (CW * BS) != 0) + 1
# V_CHUNKS, H_CHUNKS = 2, 2


def iimgload(*path, frames=1, **kwargs):
    img = pygame.image.load(os.path.join(*path))
    tex = T(img)
    img = Image(tex)
    if frames > 1:
        img = [img]
    return img


def timgload(*path, frames=1, vertical_frames=False, **kwargs):
    img = pygame.image.load(os.path.join(*path))
    # img = pygame.transform.scale_by(img, S)
    if frames > 1:
        imgs = []
        frame_width = img.get_width() / (frames if not vertical_frames else 1)
        frame_height = img.get_height() / (frames if vertical_frames else 1)
        imgs = [img.subsurface(i * frame_width * (not vertical_frames), i * frame_height * vertical_frames, frame_width, frame_height) for i in range(frames)]
        texs = [T(img) for img in imgs]
        return texs
    else:
        tex = T(img)
        return tex


def timgload3(*path, frames=1, vertical_frames=False, **kwargs):
    img = pygame.image.load(os.path.join(*path))
    img = pygame.transform.scale_by(img, S)
    if frames > 1:
        imgs = []
        frame_width = img.get_width() / (frames if not vertical_frames else 1)
        frame_height = img.get_height() / (frames if vertical_frames else 1)
        imgs = [img.subsurface(i * frame_width * (not vertical_frames), i * frame_height * vertical_frames, frame_width, frame_height) for i in range(frames)]
        texs = [T(img) for img in imgs]
        return texs
    else:
        tex = T(img)
        return tex


def imgload(*path, frames=1, vertical_frames=False, **kwargs):
    img = pygame.image.load(os.path.join(*path))
    if frames > 1:
        imgs = []
        frame_width = img.get_width() / (frames if not vertical_frames else 1)
        frame_height = img.get_height() / (frames if vertical_frames else 1)
        imgs = [img.subsurface(i * frame_width * (not vertical_frames), i * frame_height * vertical_frames, frame_width, frame_height) for i in range(frames)]
        return imgs
    else:
        return img


def imgload3(*path, frames=1, vertical_frames=False, **kwargs):
    img = pygame.image.load(os.path.join(*path))
    img = pygame.transform.scale_by(img, S)
    if frames > 1:
        imgs = []
        frame_width = img.get_width() / (frames if not vertical_frames else 1)
        frame_height = img.get_height() / (frames if vertical_frames else 1)
        imgs = [img.subsurface(i * frame_width * (not vertical_frames), i * frame_height * vertical_frames, frame_width, frame_height) for i in range(frames)]
        return imgs
    else:
        return img


def iimgload3(*path, frames=1, **kwargs):
    img = pygame.image.load(os.path.join(*path))
    img = pygame.transform.scale_by(img, S)
    tex = T(img)
    img = Image(tex)
    if frames > 1:
        img = [img]
    return img


def scale2x(img):
    return img


def scale3x(img):
    return img


def iscale_by(image, mult):
    return Image(T(pygame.transform.scale_by(image, mult)))


def img_mult(a, b):
    return a
