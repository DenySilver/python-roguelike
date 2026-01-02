import pygame
from settings import TILE_SIZE

class SpriteSheet:
    def __init__(self, filename):
        try:
            self.sheet = pygame.image.load(filename).convert()
            self.bg_color = self.sheet.get_at((0, 0))
            if isinstance(self.bg_color, pygame.Color):
                self.bg_color = (self.bg_color.r, self.bg_color.g, self.bg_color.b)
        except pygame.error as e:
            print(f"Error loading {filename}: {e}")
            raise SystemExit(e)

    def get_sprite(self, x, y, width, height, color=None):
        image = pygame.Surface((width, height)).convert()
        image.blit(self.sheet, (0, 0), (x, y, width, height))
        image.set_colorkey(self.bg_color)
        if color:
            colored_surface = pygame.Surface(image.get_size()).convert_alpha()
            colored_surface.fill(color)
            image.blit(colored_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
        return image