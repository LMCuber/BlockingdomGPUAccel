import pygame


def draw_rect(ren, rect, color, outline=1):
    pygame.draw.rect(ren, color, rect, outline)


def fill_rect(ren, rect, color):
    pygame.draw.rect(ren, color, rect)


functions = ["draw_rect", "fill_rect"]
