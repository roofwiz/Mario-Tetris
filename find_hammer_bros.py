
import pygame
import json
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"

def find_hammer_bros():
    pygame.init()
    sheet = pygame.image.load('assets/marioallsprite.png')
    # Try to find common locations
    # Row above Bowser (y=397)
    strip = sheet.subsurface((0, 320, sheet.get_width(), 70))
    pygame.image.save(strip, 'hammer_bro_check_v2.png')
    print("Saved strip to hammer_bro_check_v2.png")

if __name__ == "__main__":
    find_hammer_bros()
