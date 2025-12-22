import pygame
import math
import os
import random
from src.config import WINDOW_WIDTH, WINDOW_HEIGHT, C_WHITE, C_BLACK, C_NEON_PINK

class IntroScene:
    def __init__(self, sprite_manager):
        self.sprite_manager = sprite_manager
        self.mario_stand = sprite_manager.get_sprite('mario', 'stand', 3.0)
        self.mario_walk = sprite_manager.get_sprite('mario', 'walk', 3.0)
        
        self.luigi_stand = sprite_manager.get_sprite('luigi', 'stand', 3.0)
        self.luigi_walk = sprite_manager.get_sprite('luigi', 'walk', 3.0)
        
        # Tint Luigi Green (Simple override)
        if self.luigi_stand:
            self.luigi_stand.fill((0, 255, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
        if self.luigi_walk:
            self.luigi_walk.fill((0, 255, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
            
        self.timer = 0
        self.mario_x = -50
        self.luigi_x = -100
        self.ground_y = WINDOW_HEIGHT - 200  # Higher up so text fits below
        
        self.state = 'WALKING' # WALKING, HIGH_FIVE, WAITING
        self.jump_y = 0
        
        self.blink_timer = 0
        
        # Classic Mario Blue Background
        self.bg_color = (92, 148, 252) # Overworld Blue
        
    def update(self, dt):
        self.timer += dt
        self.blink_timer += dt
        
        if self.state == 'WALKING':
            speed = 200 # Increased speed
            if self.mario_x < WINDOW_WIDTH // 2 - 40:
                self.mario_x += speed * dt
            if self.luigi_x < WINDOW_WIDTH // 2 + 10:
                self.luigi_x += speed * dt
            
            if self.mario_x >= WINDOW_WIDTH // 2 - 40 and self.luigi_x >= WINDOW_WIDTH // 2 + 10:
                self.state = 'JUMP'
                self.timer = 0
                
        elif self.state == 'JUMP':
            # Simple jump arc
            if self.timer < 0.5:
                self.jump_y = -math.sin(self.timer * math.pi * 2) * 50
            else:
                self.jump_y = 0
                self.state = 'WAITING'
                
    def draw(self, surface):
        # Enhanced background with gradient sky
        # Draw sky gradient (lighter at top, darker at bottom)
        for y in range(WINDOW_HEIGHT):
            # Gradient from light blue to darker blue
            ratio = y / WINDOW_HEIGHT
            r = int(92 + (60 - 92) * ratio)
            g = int(148 + (120 - 148) * ratio)
            b = int(252 + (200 - 252) * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))
        
        # Draw hills in background for depth
        hill_color = (60, 140, 60)
        # Far hill
        pygame.draw.ellipse(surface, hill_color, 
                          (WINDOW_WIDTH * 0.1, self.ground_y + 20, WINDOW_WIDTH * 0.4, 120))
        # Near hill
        pygame.draw.ellipse(surface, (50, 130, 50), 
                          (WINDOW_WIDTH * 0.5, self.ground_y + 40, WINDOW_WIDTH * 0.5, 100))
        
        # Draw clouds
        cloud_color = (255, 255, 255)
        # Cloud 1
        pygame.draw.circle(surface, cloud_color, (100, 80), 30)
        pygame.draw.circle(surface, cloud_color, (130, 80), 35)
        pygame.draw.circle(surface, cloud_color, (160, 80), 30)
        # Cloud 2
        pygame.draw.circle(surface, cloud_color, (WINDOW_WIDTH - 150, 120), 25)
        pygame.draw.circle(surface, cloud_color, (WINDOW_WIDTH - 120, 120), 30)
        pygame.draw.circle(surface, cloud_color, (WINDOW_WIDTH - 90, 120), 25)
        # Cloud 3
        pygame.draw.circle(surface, cloud_color, (WINDOW_WIDTH // 2, 60), 28)
        pygame.draw.circle(surface, cloud_color, (WINDOW_WIDTH // 2 + 30, 60), 32)
        pygame.draw.circle(surface, cloud_color, (WINDOW_WIDTH // 2 + 60, 60), 28)
        
        # Draw improved ground
        ground_top = self.ground_y + 80
        # Grass layer
        pygame.draw.rect(surface, (34, 139, 34), (0, ground_top, WINDOW_WIDTH, 15))
        # Dirt layer
        pygame.draw.rect(surface, (139, 69, 19), (0, ground_top + 15, WINDOW_WIDTH, WINDOW_HEIGHT))
        
        # Add grass blades for detail
        grass_blade_color = (0, 180, 0)
        for x in range(0, WINDOW_WIDTH, 20):
            offset = (x // 20) % 3
            pygame.draw.line(surface, grass_blade_color, 
                           (x + offset * 3, ground_top), 
                           (x + offset * 3, ground_top - 8), 2)
        
        # Determine Frame
        mario_img = self.mario_walk if (int(self.timer * 10) % 2 == 0 and self.state == 'WALKING') else self.mario_stand
        luigi_img = self.luigi_walk if (int(self.timer * 10) % 2 == 0 and self.state == 'WALKING') else self.luigi_stand
        
        # Draw Mario
        if mario_img:
            surface.blit(mario_img, (self.mario_x, self.ground_y + self.jump_y))
            
        # Draw Luigi
        if luigi_img:
            surface.blit(luigi_img, (self.luigi_x, self.ground_y + self.jump_y))
            
        # Draw Text
        if self.state == 'WAITING':
            font_big = pygame.font.SysFont('Arial', 40, bold=True)
            title = font_big.render("SUPER BLOCK BROS", True, C_NEON_PINK)
            # Add shadow to title
            title_shadow = font_big.render("SUPER BLOCK BROS", True, C_BLACK)
            
            font_small = pygame.font.SysFont('Arial', 20)
            
            cx = WINDOW_WIDTH // 2
            
            # Title
            surface.blit(title_shadow, title_shadow.get_rect(center=(cx+2, 82)))
            surface.blit(title, title.get_rect(center=(cx, 80)))
            
            if self.blink_timer % 1.0 < 0.5:
                start = font_small.render("PRESS ENTER", True, C_WHITE)
                surface.blit(start, start.get_rect(center=(cx, self.ground_y + 140)))

            
            # Settings Button (gear icon in corner)
            self.settings_btn_rect = pygame.Rect(WINDOW_WIDTH - 50, 10, 40, 40)
            pygame.draw.rect(surface, (60, 60, 80), self.settings_btn_rect, border_radius=8)
            pygame.draw.rect(surface, (150, 150, 150), self.settings_btn_rect, 2, border_radius=8)
            
            # Draw gear icon (simple representation)
            gear_x, gear_y = self.settings_btn_rect.center
            for angle in range(0, 360, 45):
                dx = int(14 * math.cos(math.radians(angle)))
                dy = int(14 * math.sin(math.radians(angle)))
                pygame.draw.circle(surface, (200, 200, 200), (gear_x + dx, gear_y + dy), 4)
            
            # "Settings" tooltip on hover
            mx, my = pygame.mouse.get_pos()
            if self.settings_btn_rect.collidepoint(mx, my):
                tooltip = font_small.render("Asset Editor", True, (255, 215, 0))
                surface.blit(tooltip, (WINDOW_WIDTH - 130, 55))
        else:
            self.settings_btn_rect = None
    
    def handle_click(self, pos):
        """Handle clicks on intro screen. Returns 'settings' if settings clicked."""
        if hasattr(self, 'settings_btn_rect') and self.settings_btn_rect and self.settings_btn_rect.collidepoint(pos):
            return 'settings'
        return None
