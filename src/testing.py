import pygame
import random
import cProfile


pygame.init()

asd = {"asd": 2, "dsa": 3}



def Rect(*args):
    return pygame.Rect


def main():
    for i in range(100000000):
        rect = asd["dsa"]


cProfile.run("main()", sort="cumtime")
