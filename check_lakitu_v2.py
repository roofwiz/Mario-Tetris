
import pygame
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"

def check_lakitu_v2():
    pygame.init()
    sheet = pygame.image.load('assets/marioallsprite.png')
    # Save a strip from y=240 to y=320
    strip = sheet.subsurface((0, 240, sheet.get_width(), 80))
    pygame.image.save(strip, 'lakitu_check_v2.png')
    print("Saved lakitu_check_v2.png")

if __name__ == "__main__":
    check_lakitu_v2()
