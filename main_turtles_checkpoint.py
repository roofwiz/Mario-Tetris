import pygame
import random
import sys
import json
import os
import math
from settings import game_settings

# --- Game Configuration ---
GRID_WIDTH, GRID_HEIGHT = 10, 20
BLOCK_SIZE = 24

# Derived screen dimensions
PLAYFIELD_WIDTH = GRID_WIDTH * BLOCK_SIZE
PLAYFIELD_HEIGHT = GRID_HEIGHT * BLOCK_SIZE
LEFT_MARGIN = 40
RIGHT_PANEL_WIDTH = 240
WINDOW_WIDTH = LEFT_MARGIN + PLAYFIELD_WIDTH + RIGHT_PANEL_WIDTH
WINDOW_HEIGHT = PLAYFIELD_HEIGHT + 100 # Padding at top and bottom

# Playfield position
PLAYFIELD_X = LEFT_MARGIN
PLAYFIELD_Y = (WINDOW_HEIGHT - PLAYFIELD_HEIGHT) // 2 # Center vertically

# --- DAS Configuration ---
DAS_DELAY = 0.2  # Initial delay before auto-repeat
DAS_REPEAT = 0.05 # Speed of auto-repeat

# --- Colors & Style ---
C_BLACK = (10, 10, 10)
C_DARK_BLUE = (20, 20, 40)
C_GRID_BG = (30, 30, 50)
C_NEON_PINK = (255, 20, 147)
C_WHITE = (240, 240, 240)
C_RED = (255, 50, 50)
C_GREEN = (50, 255, 50)
C_GHOST = (128, 128, 128, 100) 

# --- Levels ---
LINES_TO_CLEAR_LEVEL = 10

# Tetromino shapes and colors
TETROMINO_DATA = {
    'I': {'shape': [[1, 1, 1, 1]], 'color': (0, 255, 255)},
    'O': {'shape': [[1, 1], [1, 1]], 'color': (255, 255, 0)},
    'T': {'shape': [[0, 1, 0], [1, 1, 1]], 'color': (128, 0, 128)},
    'L': {'shape': [[0, 0, 1], [1, 1, 1]], 'color': (255, 165, 0)},
    'J': {'shape': [[1, 0, 0], [1, 1, 1]], 'color': (0, 0, 255)},
    'S': {'shape': [[0, 1, 1], [1, 1, 0]], 'color': (0, 255, 0)},
    'Z': {'shape': [[1, 1, 0], [0, 1, 1]], 'color': (255, 0, 0)}
}

# Wall Kick Data (SRS-like)
WALL_KICK_DATA = {
    'JLSTZ': [
        [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
        [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
        [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
        [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
        [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
        [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
        [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
        [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    ],
    'I': [
        [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
        [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
        [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
        [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
        [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
        [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
        [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
        [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
    ]
}

# --- Global Helper Functions ---
def draw_block(screen, x, y, color):
    """Draws a single Tetris block on the grid."""
    px = PLAYFIELD_X + x * BLOCK_SIZE
    py = PLAYFIELD_Y + y * BLOCK_SIZE
    pygame.draw.rect(screen, color, (px, py, BLOCK_SIZE, BLOCK_SIZE))
    # Bevel effect
    pygame.draw.rect(screen, (255, 255, 255), (px, py, BLOCK_SIZE, BLOCK_SIZE), 1)

def draw_heart(surface, x, y, size):
    """Draws an 8-bit style heart."""
    # Pixel art approximations
    color = C_RED
    border = C_WHITE
    # Main body
    pygame.draw.rect(surface, color, (x + 4, y + 4, size - 8, size - 8))
    pygame.draw.rect(surface, color, (x + 2, y + 2, 6, 6))
    pygame.draw.rect(surface, color, (x + size - 8, y + 2, 6, 6))
    pygame.draw.rect(surface, color, (x + size//2 - 2, y + size - 6, 4, 4))
    
    # Border (Optional, simple box for now to match 8-bit style)
    pygame.draw.rect(surface, border, (x, y, size, size), 2)

class SpriteManager:
    def __init__(self):
        self.spritesheet = None
        # Load Coords from Settings
        self.sprite_data = game_settings.config.get('sprite_coords', {})

        try:
            path = game_settings.get_asset_path('images', 'spritesheet')
            if path and os.path.exists(path):
                self.spritesheet = pygame.image.load(path).convert_alpha()
                print("Spritesheet loaded.")
            else:
                print("Spritesheet NOT found. Enemies will be invisible/missing.")
        except Exception as e:
            print(f"Error loading spritesheet: {e}")

    def get_sprite(self, char_name, frame_name, scale_factor=2.0):
        if not self.spritesheet: return None
        try:
            coords = self.sprite_data[char_name][frame_name]
            rect = pygame.Rect(coords['x'], coords['y'], coords['w'], coords['h'])
            if not self.spritesheet.get_rect().contains(rect): return None
            image = self.spritesheet.subsurface(rect)
            new_height = int(BLOCK_SIZE * scale_factor)
            aspect = image.get_width() / image.get_height()
            new_width = int(new_height * aspect)
            return pygame.transform.scale(image, (new_width, new_height))
        except KeyError: return None

    def get_animation_frames(self, char_name, scale_factor=1.5, prefix=None): # Tuned scale factor
        if not self.spritesheet: return []
        frames = []
        if char_name in self.sprite_data:
            # Sort keys to ensure order (e.g. fly_1 before fly_2)
            keys = sorted(self.sprite_data[char_name].keys())
            for frame_name in keys:
                if prefix and not frame_name.startswith(prefix): continue
                
                frame = self.get_sprite(char_name, frame_name, scale_factor)
                if frame: frames.append(frame)
        return frames

    def get_cloud_image(self, size=(32, 24)):
        # Use sprite sheet cloud if possible
        if self.spritesheet:
            cloud = self.get_sprite("cloud", "walk_1", scale_factor=1.0)
            if cloud: return pygame.transform.scale(cloud, size)
            
        # Fallback to single file if sheet fails
        try:
            path = game_settings.get_asset_path('images', 'cloud_fallback')
            if path and os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.scale(img, size)
        except: return None

class Turtle:
    ENEMY_TYPE = 'green'
    def __init__(self, is_golden=False, enemy_type=None):
        self.x = random.randint(0, GRID_WIDTH - 1)
        self.y = -2.0
        self.speed = 1.5 
        self.state = 'active'
        self.direction = random.choice([-1, 1])
        self.is_golden = is_golden
        self.enemy_type = enemy_type if enemy_type else self.ENEMY_TYPE
        
        # Frame Loading Logic
        raw_frames = self.get_frames()
        if isinstance(raw_frames, dict):
             self.fly_frames = raw_frames.get('fly', [])
             self.walk_frames = raw_frames.get('walk', [])
             self.shell_frames = raw_frames.get('shell', [])
        else:
             self.fly_frames = []
             self.walk_frames = raw_frames
             self.shell_frames = []

        # Generate directional frames
        self.walk_frames_left = self.walk_frames
        self.walk_frames_right = [pygame.transform.flip(f, True, False) for f in self.walk_frames_left]
        
        self.fly_frames_left = self.fly_frames
        self.fly_frames_right = [pygame.transform.flip(f, True, False) for f in self.fly_frames_left]
        
        self.shell_frames_left = self.shell_frames
        self.shell_frames_right = [pygame.transform.flip(f, True, False) for f in self.shell_frames_left]
        
        # Golden Tint (Apply to all if generic method used or just handle separately)
        # Using pre-generated GOLDEN_TURTLE_FRAMES which is just a list (walk only for now)
        if self.is_golden and not self.walk_frames:
             pass # Golden frames are likely just walk frames in list format
             
        self.current_frame = 0
        self.last_update = pygame.time.get_ticks()
        self.move_timer = 0
        self.move_interval = 0.5 
        self.landed_timer = 0
        self.max_lifetime = 15.0 
        self.animation_speed = 200 
        self.dying_timer = 0 
        
        # Turn counter for smart turtles
        self.turns_at_edge = 0

    def get_frames(self):
        if self.is_golden: return Tetris.GOLDEN_TURTLE_FRAMES
        if self.enemy_type == 'red': return Tetris.RED_TURTLE_FRAMES
        if self.enemy_type == 'spiny': return Tetris.SPINY_FRAMES
        return Tetris.TURTLE_FRAMES

    def update_animation(self):
        now = pygame.time.get_ticks()
        frames = []
        if self.state == 'dying': 
            frames = self.shell_frames_right if self.direction == 1 else self.shell_frames_left
            if not frames: frames = self.walk_frames_right # Fallback
            
        elif self.state == 'flying':
            frames = self.fly_frames_right if self.direction == 1 else self.fly_frames_left
            
        elif self.state in ['active', 'landed']:
            frames = self.walk_frames_right if self.direction == 1 else self.walk_frames_left
        
        if frames and now - self.last_update > self.animation_speed:
            self.last_update = now
            self.current_frame = (self.current_frame + 1) % len(frames)

    def update_movement(self, delta_time, game_grid):
        if self.state == 'dying':
            self.dying_timer += delta_time
            self.y += 10 * delta_time
            return self.dying_timer > 2.0 # Longer death for shell spin visibility

        if self.state == 'falling_out':
            self.y += 10 * delta_time 
            return self.y > GRID_HEIGHT + 2

        if self.state == 'flying':
             # Flying Logic (Horizontal with slight descent or hover)
             self.x += self.direction * self.speed * delta_time
             self.y += 0.5 * delta_time # Very slow descent
             
             # Bounce Walls
             if self.x <= 0: self.direction = 1; self.x = 0
             if self.x >= GRID_WIDTH - 1: self.direction = -1; self.x = GRID_WIDTH - 1
             
             # Check Collision (Grid or Floor)
             ix, iy = int(self.x), int(self.y)
             if iy >= GRID_HEIGHT or (0 <= ix < GRID_WIDTH and 0 <= iy < GRID_HEIGHT and game_grid.grid[iy][ix] != (0,0,0)):
                 self.state = 'active'
                 # Push out of wall
                 self.y = iy - 1
             return False

        if self.state == 'active':
            self.y += self.speed * delta_time
            landed_y = int(self.y + 1)
            landed_x = int(self.x)
            
            if landed_y >= GRID_HEIGHT or (0 <= landed_x < GRID_WIDTH and 0 <= landed_y < GRID_HEIGHT and game_grid.grid[landed_y][landed_x] != (0, 0, 0)):
                self.y = landed_y - 1 
                self.state = 'landed'
                self.move_timer = 0

        elif self.state == 'landed':
            self.landed_timer += delta_time
            if self.landed_timer > self.max_lifetime:
                self.state = 'falling_out'
                return False

            self.move_timer += delta_time
            if self.move_timer >= self.move_interval:
                self.move_timer -= self.move_interval
                next_x = int(self.x + self.direction)
                
                if 0 <= next_x < GRID_WIDTH:
                    # Logic to check walls and holes
                    block_below_next = int(self.y) + 1
                    block_in_front = game_grid.grid[int(self.y)][next_x] != (0, 0, 0)
                    has_ground = block_below_next < GRID_HEIGHT and game_grid.grid[block_below_next][next_x] != (0, 0, 0)
                    
                    if self.enemy_type == 'red':
                         # SMART TURN LOGIC
                         if block_in_front or not has_ground: 
                             if self.turns_at_edge < 3: # Turn around 3 times max
                                 self.direction *= -1
                                 self.turns_at_edge += 1
                             else:
                                 # Allowed to fall
                                 self.x = next_x
                                 self.state = 'active'
                         else: 
                             self.x = next_x
                             self.state = 'landed'
                    else: 
                        # Green / Spiny fall off edges blindly
                        if not has_ground and not block_in_front:
                            self.state = 'active'; self.x = next_x
                        elif block_in_front: self.direction *= -1
                        else: self.x = next_x
                else:
                    self.direction *= -1 
        return False

    def handle_stomp(self, game):
        game.sound_manager.play('stomp')
        self.state = 'dying'
        if self.is_golden:
            game.lives = min(game.lives + 1, 5)
            game.sound_manager.play('life')
            return 2500
        else:
            game.turtles_stomped += 1
            if game.turtles_stomped % 5 == 0:
                game.lives = min(game.lives + 1, 5)
                game.sound_manager.play('life')
            return 500

class RedTurtle(Turtle): 
    ENEMY_TYPE = 'red'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = 'flying' # Start flying
class Spiny(Turtle):
    ENEMY_TYPE = 'spiny'
    def handle_stomp(self, game):
        game.sound_manager.play('stomp')
        if game.lives > 0:
            hx = WINDOW_WIDTH - 220 + ((game.lives - 1) * 30)
            hy = 110
            game.falling_hearts.append({'x': hx, 'y': hy, 'vy': -5})

        game.lives -= 1
        game.is_losing_life = True
        return 0

class Cloud:
    def __init__(self, sprite_manager):
        self.image = sprite_manager.get_cloud_image((64, 48))
        
        self.x = random.randint(0, WINDOW_WIDTH)
        self.y = random.randint(0, 200)
        self.speed = random.uniform(10, 30)
        self.direction = 1
        
    def update(self, delta_time):
        self.x += self.speed * delta_time
        if self.x > WINDOW_WIDTH + 50: 
            self.x = -100
            self.y = random.randint(0, 200)

    def draw(self, surface):
        if self.image:
            surface.blit(self.image, (self.x, self.y))

class PopupText:
    def __init__(self, x, y, text, color=(255, 255, 255)):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 1.0 # Seconds
        self.dy = -30
        
    def update(self, dt):
        self.life -= dt
        self.y += self.dy * dt
        
    def draw(self, surface, font):
        if self.life > 0:
            surf = font.render(self.text, True, self.color)
            surface.blit(surf, (self.x, self.y))

class BonusPlayer:
    def __init__(self, x, y, sprite_manager):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.facing_right = True
        self.width = 16
        self.height = 16
        self.sprite_manager = sprite_manager
        
    def update(self, dt, blocks):
        # Physics Constants
        GRAVITY = 800
        MOVE_SPEED = 150
        JUMP_FORCE = -350
        
        keys = pygame.key.get_pressed()
        
        # Horizontal Movement
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -MOVE_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT]:
            self.vx = MOVE_SPEED
            self.facing_right = True
            
        # Apply X move
        self.x += self.vx * dt
        
        # Collision X
        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for b in blocks:
            if player_rect.colliderect(b):
                if self.vx > 0: self.x = b.left - self.width
                elif self.vx < 0: self.x = b.right
        
        # Vertical Movement
        self.vy += GRAVITY * dt
        self.y += self.vy * dt
        
        # Collision Y
        self.on_ground = False
        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for b in blocks:
            if player_rect.colliderect(b):
                if self.vy > 0: 
                    self.y = b.top - self.height
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.y = b.bottom
                    self.vy = 0
        
        # Screen Bounds
        if self.x < 0: self.x = 0
        if self.x > WINDOW_WIDTH - self.width: self.x = WINDOW_WIDTH - self.width
        if self.y > WINDOW_HEIGHT: # Fall off
            self.y = 0
            self.vy = 0
            
        # Jump
        if keys[pygame.K_UP] and self.on_ground:
            self.vy = JUMP_FORCE

    def draw(self, surface):
        color = (255, 0, 0)
        # Try to use Mario sprite if available
        sprite = None
        # Access global or pass in? Passed in sprite_manager.
        if self.sprite_manager:
            sprite = self.sprite_manager.get_sprite("mario", "stand", scale_factor=1.0)
            
        if sprite:
            if not self.facing_right:
                sprite = pygame.transform.flip(sprite, True, False)
            surface.blit(sprite, (self.x, self.y))
        else:
            pygame.draw.rect(surface, color, (self.x, self.y, self.width, self.height))

class BonusGame:
    def __init__(self, tetris_ref):
        self.tetris = tetris_ref
        self.active = False
        self.timer = 15.0 # 15 Seconds bonus round
        self.score = 0
        
        # Level Generation
        self.blocks = []
        self.coins = []
        
        # Floor
        for i in range(0, WINDOW_WIDTH, 20):
             self.blocks.append(pygame.Rect(i, WINDOW_HEIGHT - 20, 20, 20))
             
        # Platforms
        self.blocks.append(pygame.Rect(100, 300, 100, 20))
        self.blocks.append(pygame.Rect(300, 250, 100, 20))
        
        # Coins
        self.coins.append(pygame.Rect(150, 270, 10, 10))
        self.coins.append(pygame.Rect(350, 220, 10, 10))
        self.coins.append(pygame.Rect(250, 150, 10, 10))
        
        self.player = BonusPlayer(50, 300, tetris_ref.sprite_manager)
        
    def start(self):
        self.active = True
        self.timer = 15.0
        self.player.x, self.player.y = 50, WINDOW_HEIGHT - 60
        self.player.vy = 0
        
    def update(self, dt):
        if not self.active: return
        
        self.timer -= dt
        if self.timer <= 0:
            self.active = False
            self.tetris.game_state = 'PLAYING'
            return
            
        self.player.update(dt, self.blocks)
        
        # Coin Collection
        player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
        for c in self.coins[:]:
            if player_rect.colliderect(c):
                self.coins.remove(c)
                self.score += 100
                self.tetris.score += 100
                # Play sound?
                
    def draw(self, surface):
        # BG
        surface.fill((100, 100, 255)) # Sky Blue
        
        # Blocks
        for b in self.blocks:
            pygame.draw.rect(surface, (139, 69, 19), b) # Brown
            pygame.draw.rect(surface, (0,0,0), b, 1)
            
        # Coins
        for c in self.coins:
            pygame.draw.circle(surface, (255, 215, 0), c.center, 5)
            
        # Player
        self.player.draw(surface)
        
        # HUD
        font = self.tetris.font_small
        timer_surf = font.render(f"BONUS TIME: {int(self.timer)}", True, (255, 255, 255))
        surface.blit(timer_surf, (WINDOW_WIDTH//2 - 50, 20))

class Lakitu(Turtle):
    def __init__(self, tetris_ref):
        super().__init__()
        self.tetris = tetris_ref
        self.y = 1
        self.x = -5
        self.speed = 3.0
        self.direction = 1
        self.throw_timer = 0
        self.state = 'active'
        self.hover_offset = 0
        
        # Load sprites
        self.cloud_sprite = tetris_ref.sprite_manager.get_cloud_image((32, 24))
        self.koopa_sprite = tetris_ref.TURTLE_FRAMES[0] if tetris_ref.TURTLE_FRAMES else None
        
    def update(self, dt):
        self.hover_offset += dt * 5
        self.y = 1 + math.sin(self.hover_offset) * 0.5
        
        self.x += self.speed * dt * self.direction
        if self.x > GRID_WIDTH + 2:
            self.direction = -1
        elif self.x < -2:
            self.direction = 1
            
        self.throw_timer += dt
        if self.throw_timer > 5.0:
            self.throw_timer = 0
            if random.random() < 0.5:
                # Throw Spiny
                s = Spiny()
                s.x = max(0, min(GRID_WIDTH-1, int(self.x)))
                s.y = self.y
                s.state = 'active' # Fall
                self.tetris.turtles.append(s)
                self.tetris.popups.append(PopupText(PLAYFIELD_X + self.x*BLOCK_SIZE, PLAYFIELD_Y + self.y*BLOCK_SIZE, "SPINY!", C_RED))
            else:
                # Flip Gravity
                self.tetris.trigger_antigravity(10.0)

    def draw(self, surface):
        px = PLAYFIELD_X + self.x * BLOCK_SIZE
        py = PLAYFIELD_Y + self.y * BLOCK_SIZE
        
        # Draw Cloud
        if self.cloud_sprite:
            surface.blit(self.cloud_sprite, (px - 4, py + 8))
        else:
             pygame.draw.rect(surface, (200, 200, 200), (px, py+8, 32, 16))
             
        # Draw Koopa riding
        if self.koopa_sprite:
             # Draw full for now, shifted up
             surface.blit(self.koopa_sprite, (px, py - 6))
        else:
             pygame.draw.rect(surface, (0, 255, 0), (px + 4, py - 6, 16, 16))



class Tetromino:
    def __init__(self, shape_name):
        self.name = shape_name
        self.shape = TETROMINO_DATA[shape_name]['shape']
        self.color = TETROMINO_DATA[shape_name]['color']
        self.rotation = 0
        self.x = GRID_WIDTH // 2 - len(self.shape[0]) // 2
        self.y = 0

    def get_rotated_shape(self):
        return [list(row) for row in zip(*self.shape[::-1])]


def draw_3d_block(surface, color, x, y, size):
    # Main Face
    pygame.draw.rect(surface, color, (x, y, size, size))
    
    # Highlights (Bevel)
    r, g, b = color[:3]
    light = (min(255, r+60), min(255, g+60), min(255, b+60))
    dark = (max(0, r-60), max(0, g-60), max(0, b-60))
    
    b_sz = 4 # Bevel size
    
    # Top/Left Light
    pygame.draw.rect(surface, light, (x, y, size, b_sz)) # Top
    pygame.draw.rect(surface, light, (x, y, b_sz, size)) # Left
    
    # Bottom/Right Dark
    pygame.draw.rect(surface, dark, (x, y+size-b_sz, size, b_sz)) # Bottom
    pygame.draw.rect(surface, dark, (x+size-b_sz, y, b_sz, size)) # Right
    
    # Inner Face
    pygame.draw.rect(surface, color, (x+b_sz, y+b_sz, size-2*b_sz, size-2*b_sz))

class Grid:
    def __init__(self):
        self.grid = [[(0, 0, 0) for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.animation_timer = 0

    def check_collision(self, piece):
        for y, row in enumerate(piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    gx, gy = piece.x + x, piece.y + y
                    if not (0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT and self.grid[gy][gx] == (0, 0, 0)):
                        return True
        return False

    def lock_piece(self, piece):
        for y, row in enumerate(piece.shape):
            for x, cell in enumerate(row):
                if cell: self.grid[piece.y + y][piece.x + x] = piece.color

    def clear_lines(self):
        new_grid = [row for row in self.grid if row.count((0, 0, 0)) > 0]
        lines_cleared = GRID_HEIGHT - len(new_grid)
        for _ in range(lines_cleared): new_grid.insert(0, [(0, 0, 0)] * GRID_WIDTH)
        self.grid = new_grid
        return lines_cleared

    def draw(self, screen):
        self.animation_timer = (self.animation_timer + 1) % 120
        alpha = 5 + abs(60 - self.animation_timer) // 6
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x] != (0, 0, 0):
                    # Draw 3D Block
                    draw_3d_block(screen, self.grid[y][x], PLAYFIELD_X + x * BLOCK_SIZE, PLAYFIELD_Y + y * BLOCK_SIZE, BLOCK_SIZE)
                pygame.draw.rect(screen, (C_GRID_BG[0]+alpha, C_GRID_BG[1]+alpha, C_GRID_BG[2]+alpha),
                                 (PLAYFIELD_X + x * BLOCK_SIZE, PLAYFIELD_Y + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 1)

class SoundManager:
    def __init__(self):
        self.sounds = {}
        try:
            pygame.mixer.init()
            # Try loading sounds, ignore errors for individual files to prevent crash
            self.safe_load('rotate', 'rotate')
            self.safe_load('lock', 'lock')
            self.safe_load('clear', 'clear')
            self.safe_load('stomp', 'stomp')
            self.safe_load('life', 'life')
            self.safe_load('damage', 'damage')
            self.safe_load('gameover', 'gameover')
            self.safe_load('move', 'rotate') # Fallback/Reuse
            
            # Music
            music_path = game_settings.get_asset_path('sounds', 'music')
            if music_path and os.path.exists(music_path):
                try:
                    pygame.mixer.music.load(music_path)
                    pygame.mixer.music.set_volume(0.4)
                except: print("Music load failed")
            
        except Exception as e:
            print(f"Sound init global error: {e}")

    def safe_load(self, name, key):
        path = game_settings.get_asset_path('sounds', key)
        if path and os.path.exists(path):
            try:
                self.sounds[name] = pygame.mixer.Sound(path)
            except Exception as e:
                print(f"Failed to load sound {key}: {e}")

    def play(self, name):
        if name in self.sounds:
            try: self.sounds[name].play()
            except: pass

    def play_music(self):
        try:
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)
        except: pass
    
    def stop_music(self):
        pygame.mixer.music.stop()

class IntroScene:
    def __init__(self, sprite_manager):
        self.sprite_manager = sprite_manager
        
        # Load Sprites
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
        self.ground_y = WINDOW_HEIGHT - 100
        
        self.state = 'WALKING' # WALKING, HIGH_FIVE, WAITING
        self.jump_y = 0
        
        self.blink_timer = 0
        
    def update(self, dt):
        self.timer += dt
        self.blink_timer += dt
        
        if self.state == 'WALKING':
            speed = 100
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
        surface.fill(C_BLACK)
        
        # Draw Floor
        pygame.draw.rect(surface, (139, 69, 19), (0, self.ground_y + 45, WINDOW_WIDTH, WINDOW_HEIGHT))
        
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
            
            font_small = pygame.font.SysFont('Arial', 20)
            if self.blink_timer % 1.0 < 0.5:
                start = font_small.render("PRESS ENTER", True, C_WHITE)
                surface.blit(start, start.get_rect(center=(WINDOW_WIDTH//2, self.ground_y + 100)))

            surface.blit(title, title.get_rect(center=(WINDOW_WIDTH//2, 100)))

class TouchControls:
    def __init__(self, screen_dimensions):
        self.collapsed = False
        self.height = 150 # Height of the controller panel
        self.screen_w, self.screen_h = screen_dimensions
        
        # Recalculate layout
        self.update_layout(self.screen_w, self.screen_h)

    def update_layout(self, w, h):
        self.screen_w, self.screen_h = w, h
        panel_y = h - self.height
        
        # Center d-pad on RIGHT (Swapped)
        cy = panel_y + self.height // 2
        rx = w - 210 # Base x for right side cluster
        
        self.btn_left = pygame.Rect(rx, cy - 30, 60, 60)
        self.btn_down = pygame.Rect(rx + 70, cy, 60, 60) # Offset down
        self.btn_right = pygame.Rect(rx + 140, cy - 30, 60, 60)
        
        # Actions on LEFT (Swapped)
        lx = 60 # Base x for left side
        
        self.btn_b = pygame.Rect(lx, cy, 70, 70) # B is outer/lower usually
        self.btn_a = pygame.Rect(lx + 90, cy - 30, 70, 70) # A is inner/higher
        
        # Toggle Button (Top Right of Controller Area)
        self.btn_toggle = pygame.Rect(w // 2 - 40, panel_y - 20, 80, 20)

        # Colors
        c_face = (200, 200, 200, 255) # Light Grey D-Pad
        c_a = (220, 40, 40, 255) # Red A
        c_b = (220, 200, 40, 255) # Yellow B

        self.buttons = [
            {'rect': self.btn_left, 'color': c_face, 'action': 'LEFT', 'label': '<', 'shape': 'rect'},
            {'rect': self.btn_right, 'color': c_face, 'action': 'RIGHT', 'label': '>', 'shape': 'rect'},
            {'rect': self.btn_down, 'color': c_face, 'action': 'DOWN', 'label': 'v', 'shape': 'rect'},
            {'rect': self.btn_a, 'color': c_a, 'action': 'ROTATE', 'label': 'A', 'shape': 'circle'},
            {'rect': self.btn_b, 'color': c_b, 'action': 'HARD_DROP', 'label': 'B', 'shape': 'circle'}
        ]

    def draw(self, surface, font):
        if self.collapsed:
             # Just draw toggle tab
             pygame.draw.rect(surface, (100, 100, 100), self.btn_toggle, border_radius=5)
             lbl = font.render("^", True, (255,255,255))
             surface.blit(lbl, lbl.get_rect(center=self.btn_toggle.center))
             return

        # Draw Panel BG (Metallic/Plastic Look)
        panel_rect = pygame.Rect(0, self.screen_h - self.height, self.screen_w, self.height)
        pygame.draw.rect(surface, (30, 30, 35), panel_rect)
        pygame.draw.line(surface, (150, 150, 150), (0, panel_rect.top), (self.screen_w, panel_rect.top), 2)
        
        # Toggle Tab
        pygame.draw.rect(surface, (100, 100, 100), self.btn_toggle, border_radius=5)
        lbl = font.render("v", True, (255,255,255))
        surface.blit(lbl, lbl.get_rect(center=self.btn_toggle.center))

        for b in self.buttons:
            r = b['rect']
            c = b['color']
            
            # Simple 3D Effect: Darker shadow bottom-right, Lighter highlight top-left
            shadow_off = 4
            
            if b.get('shape') == 'circle':
                 # Shadow
                 pygame.draw.circle(surface, (20, 20, 20), (r.centerx + shadow_off, r.centery + shadow_off), r.w//2)
                 # Main Body
                 pygame.draw.circle(surface, c, r.center, r.w//2)
                 # Highlight (Bevel)
                 pygame.draw.circle(surface, (255, 255, 255), (r.centerx - 2, r.centery - 2), r.w//2, 2)
                 
            else: # Rect (D-Padish)
                 # Shadow
                 s_rect = r.move(shadow_off, shadow_off)
                 pygame.draw.rect(surface, (20, 20, 20), s_rect, border_radius=5)
                 # Main Body
                 pygame.draw.rect(surface, c, r, border_radius=5)
                 # Highlight
                 pygame.draw.rect(surface, (255, 255, 255), r, 2, border_radius=5)

            # Label (with slight shadow)
            txt_s = font.render(b['label'], True, (0, 0, 0))
            surface.blit(txt_s, txt_s.get_rect(center=(r.centerx+1, r.centery+1)))
            
            txt = font.render(b['label'], True, (255, 255, 255))
            surface.blit(txt, txt.get_rect(center=b['rect'].center))

    def handle_input(self, pos):
        # Toggle Check
        if self.btn_toggle.collidepoint(pos):
             return 'TOGGLE_CONTROLS'
             
        if self.collapsed: return None

        for b in self.buttons:
            dx = pos[0] - b['rect'].centerx
            dy = pos[1] - b['rect'].centery
            if math.sqrt(dx*dx + dy*dy) < b['rect'].w//2:
                return b['action']
        return None


class Tetris:
    TURTLE_FRAMES = []
    RED_TURTLE_FRAMES = []
    SPINY_FRAMES = []
    GOLDEN_TURTLE_FRAMES = []
    CLOUD_FRAMES = []
    TURTLE_LIFE_ICON = None

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Mario Tetris Redux")
        self.clock = pygame.time.Clock()
        self.game_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        
        # --- Init Assets ---
        
        self.mario_life_icon = None
        self.bonus_game = None # Init placeholder
        
        # --- Init Assets ---
        self.sprite_manager = SpriteManager()
        
        # Load Complex Frames (Dicts)
        Tetris.TURTLE_FRAMES = {
            'fly': self.sprite_manager.get_animation_frames('koopa_green', prefix='fly'),
            'walk': self.sprite_manager.get_animation_frames('koopa_green', prefix='walk'),
            'shell': self.sprite_manager.get_animation_frames('koopa_green', prefix='shell')
        }
        
        Tetris.RED_TURTLE_FRAMES = {
            'fly': self.sprite_manager.get_animation_frames('koopa_red', prefix='fly'),
            'walk': self.sprite_manager.get_animation_frames('koopa_red', prefix='walk'),
            'shell': self.sprite_manager.get_animation_frames('koopa_red', prefix='shell')
        }
        
        Tetris.SPINY_FRAMES = self.sprite_manager.get_animation_frames('spiny')
        
        # Tint Golden (Based on Walk frames)
        for f in Tetris.TURTLE_FRAMES['walk']:
            gf = f.copy()
            gf.fill((255, 215, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
            Tetris.GOLDEN_TURTLE_FRAMES.append(gf)

        # Load Mario Life Icon
        self.mario_life_icon = self.sprite_manager.get_sprite('mario', 'stand', scale_factor=1.5)
        if self.mario_life_icon:
            Tetris.TURTLE_LIFE_ICON = self.mario_life_icon
        elif Tetris.TURTLE_FRAMES and 'walk' in Tetris.TURTLE_FRAMES and Tetris.TURTLE_FRAMES['walk']:
            Tetris.TURTLE_LIFE_ICON = pygame.transform.scale(Tetris.TURTLE_FRAMES['walk'][0], (24, 24))

        self.sound_manager = SoundManager()
        self.sound_manager.play_music()
        
        self.clouds = [] # Disabled clouds (user reported as fire sprite)
        self.bonus_game = BonusGame(self) # Initialize Bonus Game
        self.intro_scene = IntroScene(self.sprite_manager)
        
        # Mobile Controls
        self.touch_controls = TouchControls((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.show_touch_controls = True # Default On for testing
        
        # Load Font
        self.font_path = game_settings.get_asset_path('fonts', 'main')
        if not self.font_path: self.font_path = os.path.join('assets', 'PressStart2P-Regular.ttf') # Fallback
        
        self.font_big = pygame.font.Font(self.font_path, 30) if os.path.exists(self.font_path) else pygame.font.SysFont('Arial', 40, bold=True)
        self.font_small = pygame.font.Font(self.font_path, 12) if os.path.exists(self.font_path) else pygame.font.SysFont('Arial', 16)
        
        self.highscore = 0
        self.highscore_file = "highscore.json"
        self.load_highscore()
        
        self.intro_timer = 0
        
        # Scaling Init
        self.fullscreen = False
        sw, sh = self.screen.get_size()
        scale_w = sw / WINDOW_WIDTH
        scale_h = sh / WINDOW_HEIGHT
        self.scale = min(scale_w, scale_h)
        self.offset_x = (sw - (WINDOW_WIDTH * self.scale)) // 2
        self.offset_y = (sh - (WINDOW_HEIGHT * self.scale)) // 2

        self.reset_game()
        self.game_state = 'INTRO'

    def reset_game(self):
        # Basic Stats (Init first to prevent draw crashes)
        self.auto_play = False 
        self.score = 0
        self.lives = 5
        self.level = 1
        self.world = 1
        self.level_in_world = 1
        self.lines_this_level = 0
        self.lines_cleared_total = 0
        self.total_time = 0
        self.turtles = []
        self.turtles_stomped = 0
        self.turtle_spawn_timer = 5.0
        self.stomp_combo = 0
        self.stomp_combo = 0
        self.b2b_chain = 0
        
        self.falling_hearts = []
        self.popups = []

        # Antigravity & Specials
        self.antigravity_active = False 
        self.antigravity_timer = 0.0
        self.lakitu = None
        self.lakitu_timer = 0
        self.p_wing_active = False
        self.p_wing_timer = 0
        self.star_active = False
        self.star_timer = 0
        self.damage_flash_timer = 0
        
        self.grid = Grid()
        self.bag = []
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        
        self.fall_timer = 0
        self.is_losing_life = False
        self.world_clear_timer = 0
        
        # Input Flags
        self.das_timer = 0
        self.das_direction = 0
        self.key_down_held = False
        
    def calculate_speed(self):
        # Formula: (World * 4) + Level
        difficulty_index = (self.world - 1) * 4 + self.level_in_world
        # Base speed 0.8s, gets faster. Cap at 0.05s.
        return max(0.05, 1.0 - (difficulty_index - 1) * 0.05)

    def trigger_antigravity(self, duration):
        self.antigravity_active = True
        self.antigravity_timer = duration
        self.popups.append(PopupText(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2, "GRAVITY SHIFT!", C_NEON_PINK))
        self.sound_manager.play('rotate') 

    def trigger_star_power(self, duration):
        self.star_active = True
        self.star_timer = duration
        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "STAR POWER!", C_GOLD))
        self.sound_manager.play('level_up')
        
    def load_highscore(self):
        try:
            if os.path.exists(self.highscore_file):
                with open(self.highscore_file, 'r') as f:
                    data = json.load(f)
                    self.highscore = data.get('highscore', 0)
        except Exception as e:
            print(f"Error loading highscore: {e}")
            self.highscore = 0

    def save_highscore(self):
        try:
            with open(self.highscore_file, 'w') as f:
                json.dump({'highscore': self.highscore}, f)
        except Exception as e:
            print(f"Error saving highscore: {e}")
            
    def check_highscore(self):
        if self.score > self.highscore:
            self.highscore = self.score
            return True
        return False
        
    def new_piece(self):
        if not self.bag:
            self.bag = list(TETROMINO_DATA.keys())
            random.shuffle(self.bag)
        p = Tetromino(self.bag.pop())
        
        # Adjust spawn based on gravity
        if self.antigravity_active:
            p.y = GRID_HEIGHT - len(p.shape)
        else:
            p.y = 0
        return p

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        
        sw, sh = self.screen.get_size()
        scale_w = sw / WINDOW_WIDTH
        scale_h = sh / WINDOW_HEIGHT
        self.scale = min(scale_w, scale_h)
        self.offset_x = (sw - (WINDOW_WIDTH * self.scale)) // 2
        self.offset_y = (sh - (WINDOW_HEIGHT * self.scale)) // 2

    def update(self, dt):
        if self.game_state == 'INTRO':
             self.intro_scene.update(dt)
             try:
                 if pygame.key.get_pressed()[pygame.K_RETURN] and self.intro_scene.state == 'WAITING':
                      print("Starting Game...")
                      self.reset_game()
                      self.game_state = 'PLAYING'
             except Exception as e:
                 print(f"CRASH IN UPDATE: {e}")
                 import traceback
                 traceback.print_exc()
             return
             
        # AI Hook
        if hasattr(self, 'trigger_ai'): self.trigger_ai()
        if self.game_state == 'BONUS':
             self.bonus_game.update(dt)
             return

        if self.game_state == 'GAMEOVER':
             self.check_highscore()
             self.save_highscore()
             if pygame.key.get_pressed()[pygame.K_RETURN]:
                 self.reset_game()
             return

        if self.game_state == 'WORLD_CLEAR':
             self.world_clear_timer -= dt
             if self.world_clear_timer <= 0:
                 self.game_state = 'PLAYING'
             return

        self.total_time += dt
        
        # Update Clouds & Popups
        # Update Clouds & Popups
        for c in self.clouds: c.update(dt)
        for p in self.popups[:]:
            p.update(dt)
            if p.life <= 0: self.popups.remove(p)

        # Polled Input for Soft Drop (More Responsive)
        keys = pygame.key.get_pressed()
        self.key_down_held = keys[pygame.K_DOWN] or (self.show_touch_controls and pygame.mouse.get_pressed()[0] and self.touch_controls.handle_input(pygame.mouse.get_pos()) == 'DOWN')

        # DAS Logic
        if self.das_direction != 0:
            self.das_timer += dt
            if self.das_timer > DAS_DELAY:
                # Repeat move
                if self.das_timer > DAS_DELAY + DAS_REPEAT:
                    self.das_timer -= DAS_REPEAT # Keep remainder
                    self.current_piece.x += self.das_direction
                    if self.grid.check_collision(self.current_piece):
                        self.current_piece.x -= self.das_direction # Wall hit

        # Lakitu Logic
        if self.lakitu:
            self.lakitu.update(dt)
            # Lakitu leaves after some time? For now stays until dismissed or something.
            # Let's say leaves after 15s
            if self.lakitu.throw_timer > 15: 
                 pass 
        elif self.level >= 3:
            self.lakitu_timer += dt
            if self.lakitu_timer > 20: # Spawn Lakitu every 20s
                self.lakitu = Lakitu(self)
                self.lakitu_timer = 0
                self.popups.append(PopupText(WINDOW_WIDTH//2, 50, "LAKITU!", C_RED)) 

        # P-Wing Logic
        if self.p_wing_active:
            self.p_wing_timer -= dt
            if self.p_wing_timer <= 0:
                self.p_wing_active = False
                self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "P-WING EXPIRED", C_WHITE))

        # Antigravity Logic
        if self.antigravity_active:
            self.antigravity_timer -= dt
            if self.antigravity_timer <= 0:
                self.antigravity_active = False
                self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "GRAVITY RESTORED", C_GREEN))

        # Star Logic
        if self.star_active:
            self.star_timer -= dt
            if self.star_timer <= 0:
                 self.star_active = False
                 self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "STAR END", C_RED))

        # Piece Gravity
        self.fall_timer += dt
        
        # Leveling: Base gravity gets faster
        gravity_delay = self.calculate_speed()
        
        # Direction determined by antigravity state
        g_dir = -1 if self.antigravity_active else 1
        
        
        # Determine actual gravity delay
        actual_delay = gravity_delay
        # Soft Drop Speed: 0.05s (20Hz) - Fast and visible
        if self.key_down_held and not self.p_wing_active:
             actual_delay = 0.05 
             
        if self.fall_timer > actual_delay:
            self.fall_timer = 0
            self.current_piece.y += g_dir
            if self.grid.check_collision(self.current_piece):
                self.current_piece.y -= g_dir
                self.sound_manager.play('lock')
                self.grid.lock_piece(self.current_piece)
                
                # Check Stomps (and now Spiny Hazard)
                stomp_points = 0
                enemies_stomped_this_turn = 0
                
                for t in self.turtles[:]:
                     if t.state in ['active', 'landed']:
                         t_rect = pygame.Rect(t.x, t.y, 1, 1)
                         p_rect = pygame.Rect(self.current_piece.x, self.current_piece.y, len(self.current_piece.shape[0]), len(self.current_piece.shape))
                         if p_rect.colliderect(t_rect):
                            # Collision with current piece?
                            if t.state != 'dead':
                                piece_rects = []
                                for y, row in enumerate(self.current_piece.shape):
                                    for x, cell in enumerate(row):
                                         if cell:
                                             px = (self.current_piece.x + x) * BLOCK_SIZE
                                             py = (self.current_piece.y + y) * BLOCK_SIZE
                                             piece_rects.append(pygame.Rect(px, py, BLOCK_SIZE, BLOCK_SIZE))
                                
                                turtle_rect = pygame.Rect(t.x * BLOCK_SIZE, t.y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                                
                                for r in piece_rects:
                                    if r.colliderect(turtle_rect):
                                        # STAR POWER: Kill enemy immediately
                                        if self.star_active:
                                             self.score += 500
                                             t.state = 'dead'
                                             self.popups.append(PopupText(t.x*BLOCK_SIZE + PLAYFIELD_X, t.y*BLOCK_SIZE + PLAYFIELD_Y, "STAR HIT!", C_GOLD))
                                             self.sound_manager.play('stomp')
                                             break

                                        if t.enemy_type == 'spiny':
                                            # Hazard!
                                            self.lives -= 1
                                            self.damage_flash_timer = 0.2 # Flash red 0.2s
                                            self.stomp_combo = 0 # Reset combo on damage
                                            self.sound_manager.play('damage')
                                            ppx = PLAYFIELD_X + t.x * BLOCK_SIZE
                                            ppy = PLAYFIELD_Y + t.y * BLOCK_SIZE
                                            self.popups.append(PopupText(ppx, ppy, "-1 LIFE", C_RED))
                                            if self.lives <= 0: self.game_state = 'GAMEOVER'
                                        else:
                                            pts = t.handle_stomp(self)
                                            stomp_points += pts
                                            enemies_stomped_this_turn += 1
                                            self.turtles_stomped += 1 # Total tracker
                                            
                                            ppx = PLAYFIELD_X + t.x * BLOCK_SIZE
                                            ppy = PLAYFIELD_Y + t.y * BLOCK_SIZE
                                            self.popups.append(PopupText(ppx, ppy, str(pts), C_GREEN))
                                            
                                            # Bonus Round Trigger (Every 3 stomps) - REMOVED per user request
                                            # if self.turtles_stomped > 0 and self.turtles_stomped % 3 == 0:
                                            #      self.game_state = 'BONUS'
                                            #      self.bonus_game.start()

                # Combo Logic
                if enemies_stomped_this_turn > 0:
                    self.stomp_combo += enemies_stomped_this_turn
                    if self.stomp_combo >= 3:
                        # Extra life only if < 5 per requirements, but combo gives life? 
                        # Requirement: "Stomping a Golden Turtle adds 1 heart". 
                        # Standard combo life seems okay but let's cap at 5.
                        self.lives = min(self.lives + 1, 5) 
                        self.sound_manager.play('life')
                        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 40, "1UP! COMBO", (255, 215, 0)))
                        self.stomp_combo -= 3 
                else:
                    self.stomp_combo = 0 # Reset if locked without stomp
                
                self.score += stomp_points

                cleared = self.grid.clear_lines()
                if cleared > 0:
                    self.sound_manager.play('clear')
                    self.lines_cleared_total += cleared
                    self.lines_this_level += cleared
                    
                    # Logic for Level Up (1-1 -> 1-2 etc)
                    if self.lines_this_level >= LINES_TO_CLEAR_LEVEL:
                        self.lines_this_level = 0
                        self.level_in_world += 1
                        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2, "LEVEL UP!", C_WHITE))
                        self.sound_manager.play('level_up')
                        
                        if self.level_in_world > 4:
                            self.world += 1
                            self.level_in_world = 1
                            # Trigger Bonus Game Between Worlds
                            self.game_state = 'BONUS'
                            self.bonus_game.start()
                            # After bonus it should go to WORLD_CLEAR or PLAYING. 
                            # BonusGame needs to handle return state. 
                            # For now, let's trigger it.
                            self.game_state = 'WORLD_CLEAR'
                            self.world_clear_timer = 3.0
                            self.sound_manager.play('world_clear')
                        else:
                             pass
                            
                    # Update internal 'level' for scoring multiplier
                    self.level = (self.world - 1) * 4 + self.level_in_world
                    
                    # Scoring 2.0
                    base_pts = [0, 100, 300, 500, 800][cleared] * self.level
                    multiplier = 1.0
                    
                    # Stomp Bonus (2x)
                    if enemies_stomped_this_turn > 0:
                        multiplier *= 2.0
                        self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 20, "STOMP BONUS x2", C_WHITE))
                        
                    # Back-to-Back Tetris (1.5x)
                    if cleared == 4:
                        if self.b2b_chain > 0:
                            multiplier *= 1.5
                            self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 40, "B2B TETRIS x1.5", (255, 215, 0)))
                        self.b2b_chain += 1
                    else:
                        self.b2b_chain = 0
                        
                    pts = int(base_pts * multiplier)
                    self.score += pts
                    
                    self.popups.append(PopupText(WINDOW_WIDTH//2 - 50, WINDOW_HEIGHT//2, f"+{pts}", C_NEON_PINK))
                    if cleared >= 4:
                         self.popups.append(PopupText(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2 - 30, "TETRIS!", C_NEON_PINK))
                         
                    # Chance for Power-Ups on Tetris
                    if cleared >= 4:
                         r = random.random()
                         if r < 0.1: # 10% Chance for Star
                              self.trigger_star_power(10.0)
                         elif r < 0.4: # 30% Chance for P-Wing (was 30% global)
                              self.p_wing_active = True
                              self.p_wing_timer = 10.0
                              self.popups.append(PopupText(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 60, "P-WING ACTIVE!", (255, 215, 0)))

                self.current_piece = self.next_piece
                self.next_piece = self.new_piece()
                
                if self.grid.check_collision(self.current_piece):
                    self.sound_manager.play('gameover')
                    self.game_state = 'GAMEOVER' # Game Over Restart

        # Turtle Logic
        self.turtle_spawn_timer += dt
        # Spawn faster at higher levels
        spawn_rate = max(2.0, 5.0 - (self.level * 0.2))
        
        if self.turtle_spawn_timer > spawn_rate: 
            self.turtle_spawn_timer = 0
            # Randomly choose type based on Level
            r = random.random()
            
            # Level 1: Only Green (and rare Golden)
            if self.level == 1:
                if r < 0.05: t = Turtle(is_golden=True)
                else: 
                    t = Turtle()
                    print(f"DEBUG: Spawning Green Turtle! Frames: {len(t.walk_frames_right)}")
            
            # Level 2: Green + Red
            elif self.level == 2:
                if r < 0.05: t = Turtle(is_golden=True)
                elif r < 0.35: t = RedTurtle()
                else: t = Turtle()
                
            # Level 3+: Full Roster (Spiny, Red, Green)
            else:
                if r < 0.05: t = Turtle(is_golden=True)
                elif r < 0.25: t = Spiny()
                elif r < 0.45: t = RedTurtle()
                else: t = Turtle()
                
            self.turtles.append(t)

        for t in self.turtles[:]:
            t.update_animation()
            remove = t.update_movement(dt, self.grid)
            if remove:
                # Check if it fell out (escaped) vs died
                if t.state == 'falling_out':
                    if self.lives > 0:
                        hx = WINDOW_WIDTH - 220 + ((self.lives - 1) * 30)
                        hy = 110
                        self.falling_hearts.append({'x': hx, 'y': hy, 'vy': -5})

                    self.lives -= 1
                    self.damage_flash_timer = 0.2
                    
                    if self.lives > 0:
                         self.sound_manager.play('damage') # Short damage sound
                    else:
                         self.sound_manager.play('gameover') # Full death/game over sound (Shortened damage sound requested for lives lost) - wait, user said "shortened version... full play when last life". 
                         # 'damage' is likely the short sound. 'gameover' is the full sound.
                         self.game_state = 'GAMEOVER'
                self.turtles.remove(t)

        # Update falling hearts
        for heart in self.falling_hearts[:]:
            heart['y'] += heart['vy']
            heart['vy'] += 0.5 # Gravity
            if heart['y'] > WINDOW_HEIGHT:
                self.falling_hearts.remove(heart)
                
        # Damage Flash Timer
        if self.damage_flash_timer > 0:
             self.damage_flash_timer -= dt

    def draw(self):
        if self.game_state == 'INTRO':
            self.intro_scene.draw(self.screen)
            pygame.display.flip()
            return

        if self.game_state == 'BONUS':
            self.bonus_game.draw(self.screen)
            pygame.display.flip()
            return
            
        if self.game_state == 'GAMEOVER':
            self.draw_game_over()
            return

        if self.game_state == 'WORLD_CLEAR':
            self.draw_world_clear()
            return

        # Draw To Virtual Surface
        self.game_surface.fill(C_DARK_BLUE)
        
        # Draw Clouds
        for c in self.clouds: c.draw(self.game_surface)
        
        self.grid.draw(self.game_surface)
        
        
        # Star Power Effect (Rainbow/Gold tint)
        if self.star_active:
             s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
             s.set_alpha(50)
             # Cycle colors
             cols = [(255, 0, 0), (255, 165, 0), (255, 255, 0), (0, 255, 0), (0, 0, 255), (75, 0, 130)]
             tick = pygame.time.get_ticks() // 100
             s.fill(cols[tick % len(cols)])
             self.game_surface.blit(s, (0, 0))

        # Low Health Flash or Damage Flash
        if self.damage_flash_timer > 0:
             s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
             s.set_alpha(150)
             s.fill(C_RED)
             self.game_surface.blit(s, (0, 0))
        elif self.lives == 1 and (pygame.time.get_ticks() % 500 < 250):
            s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            s.set_alpha(50)
            s.fill(C_RED)
            self.game_surface.blit(s, (0, 0))
        

        
        # Draw Popups
        for p in self.popups:
            p.draw(self.game_surface, self.font_small)
        
        # Scale and Blit to Screen
        # Draw Ghost Piece
        ghost_y = self.current_piece.y
        g_dir = -1 if self.antigravity_active else 1
        
        
        # Check Mouse/Touch Input for Controller
        if self.show_touch_controls:
             # Basic Mouse Emulation for Touch
             if pygame.mouse.get_pressed()[0]:
                 action = self.touch_controls.handle_input(pygame.mouse.get_pos())
                 if action == 'TOGGLE_CONTROLS':
                     self.touch_controls.collapsed = not self.touch_controls.collapsed
                     # Force a resize update next frame
                     pygame.time.wait(100) # Debounce
                 elif action:
                     # Map actions
                     if action == 'LEFT': self.action_move(-1)
                     elif action == 'RIGHT': self.action_move(1)
                     elif action == 'DOWN': self.key_down_held = True # Use soft drop flag for smooth control
                     elif action == 'ROTATE': self.action_rotate()
                     elif action == 'HARD_DROP': self.action_hard_drop()
             else:
                 # Reset if mouse not held
                 self.key_down_held = False # TODO: This might conflict with keyboard if used simultaneously
                 # But reasonable for now since we prioritize touch if active

        while not self.grid.check_collision(self.current_piece) and abs(self.current_piece.y) < GRID_HEIGHT * 2:
             self.current_piece.y += g_dir
        self.current_piece.y -= g_dir
        
        # Draw ghost logic 
        for y, row in enumerate(self.current_piece.shape):
            for x, cell in enumerate(row):
                 if cell:
                    px = PLAYFIELD_X + (self.current_piece.x + x) * BLOCK_SIZE
                    py = PLAYFIELD_Y + (self.current_piece.y + y) * BLOCK_SIZE
                    pygame.draw.rect(self.game_surface, C_GHOST, (px, py, BLOCK_SIZE, BLOCK_SIZE))
                    pygame.draw.rect(self.game_surface, (255, 255, 255), (px, py, BLOCK_SIZE, BLOCK_SIZE), 1)

        self.current_piece.y = ghost_y # Reset

        # Draw Active Piece
        for y, row in enumerate(self.current_piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    px = PLAYFIELD_X + (self.current_piece.x + x) * BLOCK_SIZE
                    px = PLAYFIELD_X + (self.current_piece.x + x) * BLOCK_SIZE
                    py = PLAYFIELD_Y + (self.current_piece.y + y) * BLOCK_SIZE
                    draw_3d_block(self.game_surface, self.current_piece.color, px, py, BLOCK_SIZE)

        # Draw Turtles
        for t in self.turtles:
            px = PLAYFIELD_X + t.x * BLOCK_SIZE
            py = PLAYFIELD_Y + t.y * BLOCK_SIZE
            if t.state != 'dead':
                # DEBUG: Draw box to see if logic works
                # pygame.draw.rect(self.game_surface, (255, 0, 0), (px, py, BLOCK_SIZE, BLOCK_SIZE), 2)
                
                # Use frames based on state
                current_img = None
                
                # Determine correct list
                target_frames = None
                if t.state == 'flying':
                    target_frames = t.fly_frames_right if t.direction == 1 else t.fly_frames_left
                elif t.state == 'dying':
                    target_frames = t.shell_frames_right if t.direction == 1 else t.shell_frames_left
                else:
                    target_frames = t.walk_frames_right if t.direction == 1 else t.walk_frames_left
                
                if target_frames:
                     current_img = target_frames[t.current_frame % len(target_frames)]
                
                if current_img:
                    self.game_surface.blit(current_img, (px, py))
                else:
                    # Fallback if no frames
                    pygame.draw.rect(self.game_surface, (0, 255, 0), (px, py, BLOCK_SIZE, BLOCK_SIZE))

            
            # Draw Enemy Timer Bar
            if t.state == 'landed':
                bar_width = BLOCK_SIZE
                bar_height = 4
                fill_pct = 1.0 - (t.landed_timer / t.max_lifetime)
                fill_w = int(bar_width * max(0, fill_pct))
                
                # Background bar
                pygame.draw.rect(self.game_surface, (50, 0, 0), (px, py - 8, bar_width, bar_height))
                # Fill bar
                col = C_GREEN if fill_pct > 0.5 else C_RED
                pygame.draw.rect(self.game_surface, col, (px, py - 8, fill_w, bar_height))

        # Draw Lakitu
        if self.lakitu: self.lakitu.draw(self.game_surface)

        # Draw Sidebar
        score_surf = self.font_big.render(f"SCORE", True, C_NEON_PINK)
        score_val = self.font_small.render(f"{int(self.score):06d}", True, C_WHITE)
        self.game_surface.blit(score_surf, (WINDOW_WIDTH - 220, 50))
        self.game_surface.blit(score_val, (WINDOW_WIDTH - 220, 90))
        
        # High Score
        high_surf = self.font_small.render(f"TOP: {max(int(self.score), int(self.highscore)):06d}", True, C_NEON_PINK)
        self.game_surface.blit(high_surf, (WINDOW_WIDTH - 220, 110))
        
        # Time
        time_surf = self.font_small.render(f"TIME: {int(self.total_time)}", True, (200, 200, 255))
        self.game_surface.blit(time_surf, (WINDOW_WIDTH - 220, 20))
        
        lvl_surf = self.font_small.render(f"WORLD: {self.world}-{self.level_in_world}", True, C_WHITE)
        self.game_surface.blit(lvl_surf, (WINDOW_WIDTH - 220, 120))
        
        # Draw Antigravity Timer (Prominently Center if Active)
        if self.antigravity_active:
             timer_text = f"ANTIGRAVITY: {int(self.antigravity_timer) + 1}"
             timer_surf = self.font_big.render(timer_text, True, C_NEON_PINK)
             # Center it
             cx, cy = WINDOW_WIDTH // 2 - RIGHT_PANEL_WIDTH // 2, 80
             self.game_surface.blit(timer_surf, timer_surf.get_rect(center=(cx, cy)))
             
        # Sidebar gravity status (Optional backup)
        grav_text = "GRAV: NORMAL" if not self.antigravity_active else "GRAV: INVERTED"
        grav_col = C_GREEN if not self.antigravity_active else C_RED
        grav_surf = self.font_small.render(grav_text, True, grav_col)
        self.game_surface.blit(grav_surf, (WINDOW_WIDTH - 220, 140))
        
        # Draw Lives (Hearts)
        lives_label = self.font_small.render("LIVES:", True, C_WHITE)
        self.game_surface.blit(lives_label, (WINDOW_WIDTH - 220, 160))
        for i in range(self.lives):
            if self.mario_life_icon:
                 self.game_surface.blit(self.mario_life_icon, (WINDOW_WIDTH - 220 + (i * 30), 190))
            else:
                 draw_heart(self.game_surface, WINDOW_WIDTH - 215 + (i * 35), 190, 24)
            
        # Draw Falling Hearts
        for heart in self.falling_hearts:
            draw_heart(self.game_surface, heart['x'], heart['y'], 24)

        # Draw Stomped Counter
        if Tetris.TURTLE_FRAMES and 'walk' in Tetris.TURTLE_FRAMES:
            # Use Green Turtle as icon
            icon = Tetris.TURTLE_FRAMES['walk'][0] # Use first frame
            if icon:
                self.game_surface.blit(icon, (WINDOW_WIDTH - 220, 230))
                
            count_surf = self.font_small.render(f"x {self.turtles_stomped}", True, C_WHITE)
            self.game_surface.blit(count_surf, (WINDOW_WIDTH - 190, 235))

        
        # Calculate final window dimensions based on controller state
        target_h = WINDOW_HEIGHT
        if self.show_touch_controls and not self.touch_controls.collapsed:
            target_h += self.touch_controls.height

        # Resize if Needed (Simple check, ideally optimized)
        if self.screen.get_height() != target_h:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, target_h), pygame.RESIZABLE)
            self.touch_controls.update_layout(WINDOW_WIDTH, target_h)

        # Draw Game Surface (Always Top)
        game_rect = self.game_surface.get_rect(topleft=(0,0))
        self.screen.blit(self.game_surface, game_rect)
        
        # Draw Touch Controls at Bottom
        if self.show_touch_controls:
             self.touch_controls.draw(self.screen, self.font_small)
             
        pygame.display.flip()

    def log_event(self, message):
        try:
            with open("game_log.txt", "a") as f:
                f.write(f"[{pygame.time.get_ticks()}] {message}\n")
        except: pass

    # Removed accidental update override from here


    def run_ai(self):
        # fast drop
        self.action_hard_drop()
        # Random move for now to prove input works, real AI is complex
        move = random.choice([-1, 0, 1])
        self.action_move(move)
        if random.random() < 0.2: self.action_rotate()

    
    # AI logic hooks
    def trigger_ai(self):
        # AI Toggle
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] and not hasattr(self, 'ai_cooldown'):
             self.auto_play = not getattr(self, 'auto_play', False)
             self.ai_cooldown = 20
             self.log_event(f"AI Toggled: {self.auto_play}")
        
        if hasattr(self, 'ai_cooldown') and self.ai_cooldown > 0: self.ai_cooldown -= 1
        
        if getattr(self, 'auto_play', False) and self.game_state == 'PLAYING':
            if self.fall_timer > 0.1: 
                 self.run_ai()


    def draw_intro(self):
        self.screen.fill(C_BLACK)
        
        title = self.font_big.render("MARIO TETRIS", True, C_NEON_PINK)
        start = self.font_small.render("PRESS ENTER TO START", True, C_WHITE)
        esc = self.font_small.render("PRESS ESC TO QUIT", True, C_WHITE)
        
        cx, cy = self.screen.get_rect().center
        self.screen.blit(title, title.get_rect(center=(cx, cy - 50)))
        
        if pygame.time.get_ticks() % 1000 < 500: # Blink
            self.screen.blit(start, start.get_rect(center=(cx, cy + 50)))
        self.screen.blit(esc, esc.get_rect(center=(cx, cy + 100)))
        pygame.display.flip()

    def draw_game_over(self):
        self.screen.fill((50, 0, 0))
        font_big = pygame.font.SysFont('Arial', 60, bold=True)
        font_small = pygame.font.SysFont('Arial', 30)
        
        title = font_big.render("GAME OVER", True, C_WHITE)
        score = font_small.render(f"FINAL SCORE: {self.score}", True, (255, 215, 0))
        retry = font_small.render("PRESS ENTER TO RETRY", True, C_WHITE)
        
        cx, cy = self.screen.get_rect().center
        self.screen.blit(title, title.get_rect(center=(cx, cy - 50)))
        self.screen.blit(score, score.get_rect(center=(cx, cy + 20)))
        self.screen.blit(retry, retry.get_rect(center=(cx, cy + 80)))
        pygame.display.flip()

    def draw_world_clear(self):
        self.screen.fill(C_BLACK)
        title = self.font_big.render(f"WORLD {self.world-1} CLEARED!", True, C_NEON_PINK)
        sub = self.font_small.render("PREPARE FOR NEXT WORLD...", True, C_WHITE)
        
        cx, cy = self.screen.get_rect().center
        self.screen.blit(title, title.get_rect(center=(cx, cy - 30)))
        self.screen.blit(sub, sub.get_rect(center=(cx, cy + 20)))
        pygame.display.flip()

    # --- Input Actions ---
    def action_move(self, dx):
        self.current_piece.x += dx
        if self.grid.check_collision(self.current_piece): self.current_piece.x -= dx
        else: self.sound_manager.play('move')
        self.das_direction = dx
        self.das_timer = 0

    def action_rotate(self):
        self.sound_manager.play('rotate')
        # Simple rotation logic
        # For full Super Rotation System (SRS) we would try kicks, but for now simple revert
        original_shape = self.current_piece.shape
        self.current_piece.shape = self.current_piece.get_rotated_shape()
        if self.grid.check_collision(self.current_piece): 
             self.current_piece.shape = original_shape

    def action_hard_drop(self):
        g_dir = -1 if self.antigravity_active else 1
        # Drop until collision (with safety limit)
        while not self.grid.check_collision(self.current_piece) and abs(self.current_piece.y) < GRID_HEIGHT * 2:
             self.current_piece.y += g_dir
        self.current_piece.y -= g_dir
        # Force lock next frame
        self.fall_timer = 999 

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state == 'PLAYING': self.game_state = 'INTRO'
                        else: return
                    if self.game_state == 'INTRO' or self.game_state == 'GAMEOVER':
                        if event.key == pygame.K_RETURN:
                            self.reset_game()
                            self.game_state = 'PLAYING'

                    if event.key == pygame.K_LEFT: 
                        self.current_piece.x -= 1
                        if self.grid.check_collision(self.current_piece): self.current_piece.x += 1
                        else: self.sound_manager.play('move')
                        self.das_direction = -1
                        self.das_timer = 0
                        
                    if event.key == pygame.K_RIGHT: 
                        self.current_piece.x += 1
                        if self.grid.check_collision(self.current_piece): self.current_piece.x -= 1
                        else: self.sound_manager.play('move')
                        self.das_direction = 1
                        self.das_timer = 0
                        
                        self.das_timer = 0
                        
                    if event.key == pygame.K_UP: 
                        self.sound_manager.play('rotate')
                        old_rot = self.current_piece.rotation
                        self.current_piece.shape = self.current_piece.get_rotated_shape()
                        if self.grid.check_collision(self.current_piece): 
                            self.current_piece.shape = TETROMINO_DATA[self.current_piece.name]['shape'] # Revert simple

                        if self.grid.check_collision(self.current_piece): 
                            self.current_piece.shape = TETROMINO_DATA[self.current_piece.name]['shape'] # Revert simple

                    if event.key == pygame.K_DOWN: 
                        if self.p_wing_active:
                            # Manual Move P-Wing
                            self.current_piece.y += 1
                            if self.grid.check_collision(self.current_piece): self.current_piece.y -= 1
                        # Else handled by polled input in update()

                    if event.key == pygame.K_UP:
                        # Modified: If P-Wing, this is UP move. If not, it's Rotate (handled above, wait).
                        # Usually UP is rotate. We need a separate key or override. 
                        # Let's map Rotate to Z/X or Up.
                        # If P-Wing, maybe we use W/S? Or Shift? 
                        # User request: "manual control ... (up/down)"
                        # Conflict: Up is Rotate.
                        # Solution: If P-Wing, Up moves Up? Then how to rotate?
                        # Let's use 'Z' for rotate as well? Or just override geometry. 
                        # Let's add specific P-Wing controls or repurpose.
                        # Actually standard Tetris uses Up for Rotate.
                        # If P-Wing active, maybe 'W' and 'S' for vertical?
                        # Or user wants "Up" to fly?
                        # I'll stick UP as Rotate. 
                        # I will add 'W' and 'S' for P-Wing vertical, or keep Down as Soft Drop.
                        # Let's make P-Wing use UP/DOWN and move Rotate to 'Z'/'X' or just 'CONTROL'.
                        # Let's keep UP as Rotate and add 'W' for Upward flight.
                        pass # Kept UP as rotate for now, handled above.
                        
                    if event.key == pygame.K_w and self.p_wing_active:
                         self.current_piece.y -= 1
                         if self.grid.check_collision(self.current_piece): self.current_piece.y += 1
                    
                    if event.key == pygame.K_z: # Alt Rotate
                        self.sound_manager.play('rotate')
                        self.current_piece.shape = self.current_piece.get_rotated_shape()
                        if self.grid.check_collision(self.current_piece): 
                            self.current_piece.shape = TETROMINO_DATA[self.current_piece.name]['shape']
                            
                    if event.key == pygame.K_f: self.toggle_fullscreen()
                    if event.key == pygame.K_m: self.show_touch_controls = not self.show_touch_controls
                    if event.key == pygame.K_SPACE: self.action_hard_drop()
                    
                if event.type == pygame.MOUSEBUTTONDOWN and self.show_touch_controls:
                    action = self.touch_controls.handle_input(event.pos)
                    if action == 'LEFT': self.action_move(-1)
                    if action == 'RIGHT': self.action_move(1)
                    if action == 'DOWN': self.key_down_held = True
                    if action == 'ROTATE': self.action_rotate()
                    if action == 'HARD_DROP': self.action_hard_drop()
                
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                        self.das_direction = 0
                    # Down key handled via polling now, no need to clear here explicitly, but safe to keep or remove.
                    # self.key_down_held = False 
                
                if event.type == pygame.MOUSEBUTTONUP:
                    self.key_down_held = False
                    
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN: self.key_down_held = False
                    if event.key == pygame.K_LEFT and self.das_direction == -1: self.das_direction = 0
                    if event.key == pygame.K_RIGHT and self.das_direction == 1: self.das_direction = 0
            
            self.update(dt)
            self.draw()

if __name__ == "__main__":
    try:
        game = Tetris()
        game.run()
    except Exception as e:
        import traceback
        with open("crash.txt", "w") as f:
            f.write(traceback.format_exc())
        print(e)
        input("Press Enter to Exit") # Keep window open if user runs manually