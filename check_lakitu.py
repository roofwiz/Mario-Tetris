
import pygame
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"

def check_lakitu():
    pygame.init()
    sheet = pygame.image.load('assets/marioallsprite.png')
    # Save a strip around y=310
    strip = sheet.subsurface((0, 310, sheet.get_width(), 40))
    pygame.image.save(strip, 'lakitu_check.png')
    print("Saved lakitu_check.png")

if __name__ == "__main__":
    check_lakitu()
