import pygame
import pygame.gfxdraw
import sys
from math import sin, cos, e
from random import randint, uniform, random
from pygame.math import Vector2


def f(x, y):
    x = x / HEIGHT * 20 - 10
    y = y / HEIGHT * 20 - 10
    return 10 * e ** (-((x ** 2 + y ** 2) * 0.05))


class Particle:
    def __init__(self):
        self.pos = Vector2(randint(0, WIDTH), randint(0, HEIGHT))
        self.vel = Vector2(0, 0)
        self.best_pos = self.pos.copy()
        self.update_best()

    def draw(self):
        pygame.draw.circle(WIN, (236, 0, 0), self.pos, 2)
        pygame.draw.line(WIN, (0, 0, 240), self.pos, self.best_pos)

    def update_vel(self):
        R1, R2 = random(), random()
        self.vel = W * self.vel + C1 * R1 * (self.best_pos - self.pos) + C2 * R2 * (global_best_pos - self.pos)

    def update_pos(self):
        self.pos += self.vel
        #
        self.update_best()
        self.pos.x = max(min(self.pos.x, WIDTH), 0)
        self.pos.y = max(min(self.pos.y, HEIGHT), 0)

    def update_best(self):
        global global_best_pos
        if f(self.pos.x, self.pos.y) > f(*global_best_pos):
            global_best_pos = Vector2(self.pos)
        elif f(self.pos.x, self.pos.y) > f(*self.best_pos):
            self.best_pos = Vector2(self.pos)

    def update(self):
        self.update_vel()
        self.update_pos()
        self.draw()


pygame.init()
WIDTH, HEIGHT = 800, 800
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
graph = pygame.Surface((WIDTH, HEIGHT))
clock = pygame.time.Clock()
for y in range(graph.get_height()):
    for x in range(graph.get_width()):
        graph.set_at((x, y), [(f(x, y)) / 10 * 255] * 3)
        # graph.set_at((x, y), [200, 200, 200])


global_best_pos = Vector2(WIDTH / 2, HEIGHT / 2)
M = 0.1
W, C1, C2 = 0.5 * M, 0.9 * M, 0.9 * M
all_particles = []
for _ in range(100):
    all_particles.append(Particle())


running = __name__ == "__main__"
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    WIN.blit(graph, (0, 0))

    pygame.gfxdraw.filled_circle(WIN, int(global_best_pos.x), int(global_best_pos.y), 6, (0, 240, 0))
    for particle in all_particles:
        particle.update()

    pygame.display.update()

pygame.quit()
sys.exit()
