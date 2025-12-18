import pygame
import random
import sys
import json
import os

# --- Game Configuration ---
GRID_WIDTH, GRID_HEIGHT = 10, 20
BLOCK_SIZE = 24
LIFE_DRAIN_SECONDS = 10.0

# Derived screen dimensions
PLAYFIELD_WIDTH = GRID_WIDTH * BLOCK_SIZE
PLAYFIELD_HEIGHT = GRID_HEIGHT * BLOCK_SIZE
LEFT_MARGIN = 40
RIGHT_PANEL_WIDTH = 240
WINDOW_WIDTH = LEFT_MARGIN + PLAYFIELD_WIDTH + RIGHT_PANEL_WIDTH
WINDOW_HEIGHT = PLAYFIELD_HEIGHT + 40 # Padding at top and bottom

# Playfield position
PLAYFIELD_X = LEFT_MARGIN
PLAYFIELD_Y = (WINDOW_HEIGHT - PLAYFIELD_HEIGHT) // 2 # Center vertically

# --- Colors & Style ---
C_BLACK = (10, 10, 10)
C_DARK_BLUE = (20, 20, 40)
C_GRID_BG = (30, 30, 50)
C_NEON_PINK = (255, 20, 147)
C_WHITE = (240, 240, 240)
C_GHOST = (128, 128, 128, 100) # Semi-transparent grey for ghost

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
# (row, col) offsets to test for rotation
WALL_KICK_DATA = {
    # Standard kicks for J, L, S, T, Z
    'JLSTZ': [
        [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)], # 0->R
        [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],    # R->0
        [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],    # R->2
        [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)], # 2->R
        [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],    # 2->L
        [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)], # L->2
        [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)], # L->0
        [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],    # 0->L
    ],
    # Special kicks for I piece
    'I': [
        [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],  # 0->R
        [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],  # R->0
        [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],  # R->2
        [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],  # 2->R
        [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],  # 2->L
        [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],  # L->2
        [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],  # L->0
        [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],  # 0->L
    ]
}

def draw_block(surface, grid_x, grid_y, color, is_ghost=False, alpha=255, offset_x=0, offset_y=0):
    """Draws a single block at the given grid coordinates."""
    x = PLAYFIELD_X + grid_x * BLOCK_SIZE + offset_x
    y = PLAYFIELD_Y + grid_y * BLOCK_SIZE + offset_y
    
    if is_ghost:
        s = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), (0, 0, BLOCK_SIZE, BLOCK_SIZE), 3, border_radius=3)
        surface.blit(s, (x, y))
    else:
        # Draw the block (filled rectangle)
        pygame.draw.rect(surface, color, (x, y, BLOCK_SIZE, BLOCK_SIZE))
        
        # Draw the inner border for definition
        light_color = (min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] + 50))
        dark_color = (max(0, color[0] - 50), max(0, color[1] - 50), max(0, color[2] - 50))
        pygame.draw.line(surface, light_color, (x, y), (x + BLOCK_SIZE - 1, y))
        pygame.draw.line(surface, light_color, (x, y), (x, y + BLOCK_SIZE - 1))
        pygame.draw.line(surface, dark_color, (x + BLOCK_SIZE - 1, y), (x + BLOCK_SIZE - 1, y + BLOCK_SIZE - 1))
        pygame.draw.line(surface, dark_color, (x, y + BLOCK_SIZE - 1), (x + BLOCK_SIZE - 1, y + BLOCK_SIZE - 1))

class SpriteManager:
    """Loads and manages all sprites from a single spritesheet."""
    def __init__(self):
        self.spritesheet = None
        self.sprite_data = {
            "koopa_green": {
                "walk_1": {"x": 96, "y": 0, "w": 16, "h": 24},
                "walk_2": {"x": 112, "y": 0, "w": 16, "h": 24}
            },
            "koopa_red": {
                "walk_1": {"x": 96, "y": 24, "w": 16, "h": 24},
                "walk_2": {"x": 112, "y": 24, "w": 16, "h": 24}
            },
            "spiny": {
                "walk_1": {"x": 0, "y": 120, "w": 16, "h": 16},
                "walk_2": {"x": 16, "y": 120, "w": 16, "h": 16}
            },
            "buzzy_beetle": {
                "walk_1": {"x": 48, "y": 8, "w": 16, "h": 16},
                "walk_2": {"x": 64, "y": 8, "w": 16, "h": 16}
            }
        }
        try:
            path = os.path.join('assets', 'marioallsprite.png')
            self.spritesheet = pygame.image.load(path).convert_alpha()
            print("Spritesheet 'marioallsprite.png' loaded successfully.")
        except (pygame.error, FileNotFoundError) as e:
            print(f"FATAL: Could not load 'marioallsprite.png'. Enemy sprites will not be available. Error: {e}")

    def get_sprite(self, char_name, frame_name, scale_factor=2.0):
        if not self.spritesheet: return None
        try:
            coords = self.sprite_data[char_name][frame_name]
            rect = pygame.Rect(coords['x'], coords['y'], coords['w'], coords['h'])

            # --- Robustness Improvement: Add a safety check ---
            if not self.spritesheet.get_rect().contains(rect):
                print(f"ERROR: Sprite '{char_name}':'{frame_name}' with rect {rect} is outside the spritesheet dimensions {self.spritesheet.get_rect()}.")
                return None
            # --- End of safety check ---

            image = self.spritesheet.subsurface(rect)
            
            # Scale based on height to maintain aspect ratio
            new_height = int(BLOCK_SIZE * scale_factor)
            aspect_ratio = image.get_width() / image.get_height()
            new_width = int(new_height * aspect_ratio)
            
            return pygame.transform.scale(image, (new_width, new_height))
        except KeyError:
            print(f"Warning: Sprite '{char_name}':'{frame_name}' not found in sprite_data.")
            return None

    def get_animation_frames(self, char_name, scale_factor=2.0):
        if not self.spritesheet: return []
        frames = []
        if char_name in self.sprite_data:
            for frame_name in self.sprite_data[char_name]:
                frame = self.get_sprite(char_name, frame_name, scale_factor)
                if frame:
                    frames.append(frame)
        return frames

class Turtle:
    """Base class for all turtle-like enemies."""
    ENEMY_TYPE = 'green' # Default type

    def __init__(self, is_golden=False, enemy_type=None):
        self.x = random.randint(0, GRID_WIDTH - 1)
        self.y = -1.0
        self.speed = 1.5 # blocks per second
        self.state = 'active' # 'active', 'landed', 'dying'
        self.direction = random.choice([-1, 1]) # For walking back and forth
        # Animation state
        self.is_golden = is_golden
        self.enemy_type = enemy_type if enemy_type else self.ENEMY_TYPE
        self.walk_frames_right = self.get_frames()
        self.walk_frames_left = [pygame.transform.flip(f, True, False) for f in self.walk_frames_right] if self.walk_frames_right else []
        self.dying_frames = [pygame.transform.flip(f, False, True) for f in self.walk_frames_right] if self.walk_frames_right else []
        self.current_frame = 0
        self.last_update = pygame.time.get_ticks()
        self.move_timer = 0
        self.move_interval = 0.5 # seconds to move one block when landed
        self.landed_timer = 0 # Timer for life drain
        self.animation_speed = 200 # milliseconds per frame (0.2 seconds)

    def get_frames(self):
        if self.is_golden:
            return Tetris.GOLDEN_TURTLE_FRAMES
        if self.enemy_type == 'red' and Tetris.RED_TURTLE_FRAMES:
            return Tetris.RED_TURTLE_FRAMES
        if self.enemy_type == 'spiny' and Tetris.SPINY_FRAMES:
            return Tetris.SPINY_FRAMES
        return Tetris.TURTLE_FRAMES # Default to green

    def update_animation(self):
        now = pygame.time.get_ticks()
        
        # Determine which animation frames to use
        if self.state == 'dying' and self.dying_frames:
            frames_to_use = self.dying_frames
        elif self.state in ['active', 'landed']:
            if self.direction == 1:
                frames_to_use = self.walk_frames_right
            else:
                frames_to_use = self.walk_frames_left
        else:
            return # No frames to animate

        if now - self.last_update > self.animation_speed:
            self.last_update = now
            self.current_frame = (self.current_frame + 1) % len(frames_to_use)

    def update_movement(self, delta_time, game_grid):
        """Handles gravity and walking logic based on the Tetris grid."""
        if self.state == 'dying':
            # Let the dying animation fall off screen
            self.y += 10 * delta_time
            if self.y > GRID_HEIGHT:
                return True # Indicate removal
            return False

        if self.state == 'active':
            # --- 1. Gravity (Falling) ---
            self.y += self.speed * delta_time # y is a float
            
            # Check for collision with the grid
            landed_y = int(self.y + 1)
            grid_x = int(self.x) # x is an integer on the grid
            
            if landed_y >= GRID_HEIGHT or (0 <= grid_x < GRID_WIDTH and 0 <= landed_y < GRID_HEIGHT and game_grid.grid[landed_y][grid_x] != (0, 0, 0)):
                self.y = landed_y - 1 # Snap to the block above
                self.state = 'landed'
                self.move_timer = 0 # Start walk timer

        elif self.state == 'landed':
            self.landed_timer += delta_time # Life drain timer
            self.move_timer += delta_time
            if self.move_timer >= self.move_interval:
                self.move_timer -= self.move_interval
                
                current_x = int(self.x)
                next_x = current_x + self.direction
                
                # Check for walking off the edge or hitting a wall
                if not (0 <= next_x < GRID_WIDTH):
                    self.direction *= -1 # Hit side of playfield, turn around
                else:
                    # Check conditions at the *next* position
                    block_in_front = game_grid.grid[int(self.y)][next_x] != (0, 0, 0)
                    y_below = int(self.y) + 1
                    has_ground_below = (y_below >= GRID_HEIGHT) or (game_grid.grid[y_below][next_x] != (0, 0, 0))
                    
                    # "Smart" turtles (red) turn at edges. "Dumb" turtles (green/spiny) fall.
                    is_smart = self.enemy_type == 'red'
                    
                    if block_in_front or (is_smart and not has_ground_below):
                        self.direction *= -1 # Turn around
                    elif not is_smart and not has_ground_below:
                        self.x = next_x # Move one step
                        self.state = 'active' # ...and start falling
                    else:
                        self.x = next_x # Move normally
                    
        return False # Do not remove

    def draw(self, surface):
        """Draws the current frame of the turtle/enemy."""
        frames_to_use = []
        if self.state == 'dying':
            frames_to_use = self.dying_frames
        elif self.direction == 1:
            frames_to_use = self.walk_frames_right
        else:
            frames_to_use = self.walk_frames_left
            
        if not frames_to_use: return # No frames to draw
        
        frame = frames_to_use[self.current_frame % len(frames_to_use)]
        
        sprite_w, sprite_h = frame.get_size()
        
        # Apply global alignment offsets from the config
        offset_x, offset_y = Tetris.ALIGNMENT_OFFSETS['x'], Tetris.ALIGNMENT_OFFSETS['y']

        # Center the sprite horizontally in the grid cell
        screen_x = PLAYFIELD_X + int(self.x) * BLOCK_SIZE + (BLOCK_SIZE - sprite_w) / 2 + offset_x
        screen_y = PLAYFIELD_Y + self.y * BLOCK_SIZE
        # Align the bottom of the sprite with the bottom of the grid cell
        surface.blit(frame, (screen_x, screen_y + BLOCK_SIZE - sprite_h + offset_y))

        # Draw a timer bar above the turtle if it's landed
        if self.state == 'landed':
            progress = min(self.landed_timer / LIFE_DRAIN_SECONDS, 1.0)
            bar_width = BLOCK_SIZE
            bar_height = 4
            # Position the bar above the sprite's bounding box
            bar_x = PLAYFIELD_X + int(self.x) * BLOCK_SIZE
            bar_y = screen_y + (BLOCK_SIZE - sprite_h) - bar_height - 2 # 2px padding
            pygame.draw.rect(surface, C_GRID_BG, (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, bar_width * progress, bar_height))

    def handle_stomp(self, game):
        """Default stomp behavior for green/golden turtles."""
        game.sound_manager.play('stomp')
        self.state = 'dying'
        self.current_frame = 0
        stomp_bonus = 0
        if self.is_golden:
            stomp_bonus = 2500
            game.lives = min(game.lives + 1, 5)
            game.sound_manager.play('life')
        else:
            stomp_bonus = 500
            game.turtles_stomped += 1
            if game.turtles_stomped > 0 and game.turtles_stomped % 3 == 0:
                game.lives = min(game.lives + 1, 5)
                game.sound_manager.play('life')
        return stomp_bonus

class RedTurtle(Turtle):
    ENEMY_TYPE = 'red'

class Spiny(Turtle):
    ENEMY_TYPE = 'spiny'

    def handle_stomp(self, game):
        """Spinies cannot be stomped and will hurt the player instead."""
        # A small visual/audio cue that the stomp failed
        game.sound_manager.play('stomp') # Or a different "thud" sound
        
        # Player loses a life
        game.lives -= 1
        game.is_losing_life = True # Trigger UI flash
        game.sound_manager.play('lifelost')
        # No points are awarded
        return 0

class BuzzyBeetle(Turtle):
    ENEMY_TYPE = 'buzzy_beetle'

    def handle_stomp(self, game):
        """Buzzy Beetles cannot be stomped. Play a 'thud' sound."""
        game.sound_manager.play('lock') # A metallic thud sound
        return 0 # No points, no damage
class Cloud:
    def __init__(self):
        self.frames = Tetris.CLOUD_FRAMES
        self.x = -BLOCK_SIZE * 3 # Start off-screen
        self.y = 5 # A small positive value to keep it visible at the top
        self.speed = 40 # pixels per second
        self.direction = 1
        self.current_frame = 0
        self.last_update = pygame.time.get_ticks()
        self.animation_speed = 500 # ms per frame
        self.drop_timer = 0
        self.drop_interval = random.uniform(15, 30) # Time between turtle drops

    def update(self, delta_time):
        # Movement
        self.x += self.speed * self.direction * delta_time
        if self.x > WINDOW_WIDTH or self.x < - (BLOCK_SIZE * 3):
            self.direction *= -1

        # Animation
        now = pygame.time.get_ticks()
        if now - self.last_update > self.animation_speed:
            self.last_update = now
            self.current_frame = (self.current_frame + 1) % len(self.frames)

class Particle:
    """A single particle for visual effects."""
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-1.5, 1.5)
        self.vy = random.uniform(-3, -1)
        self.color = color
        self.lifetime = random.uniform(0.4, 0.8) # seconds
        self.gravity = 8.0

    def update(self, delta_time):
        self.vy += self.gravity * delta_time
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= delta_time

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), 2)

class Tetromino:
    def __init__(self, shape_name):
        self.name = shape_name
        self.shape = TETROMINO_DATA[shape_name]['shape']
        self.color = TETROMINO_DATA[shape_name]['color']
        self.rotation = 0  # 0: 0, 1: 90, 2: 180, 3: 270
        self.x = GRID_WIDTH // 2 - len(self.shape[0]) // 2
        self.y = 0

    def get_rotated_shape(self, shape=None):
        if shape is None:
            shape = self.shape
        return [list(row) for row in zip(*shape[::-1])]

class Grid:
    def __init__(self):
        self.grid = [[(0, 0, 0) for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.animation_timer = 0

    def check_collision(self, piece):
        for y, row in enumerate(piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    grid_x, grid_y = piece.x + x, piece.y + y
                    if not (0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT and self.grid[grid_y][grid_x] == (0, 0, 0)):
                        return True
        return False

    def lock_piece(self, piece):
        for y, row in enumerate(piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    self.grid[piece.y + y][piece.x + x] = piece.color

    def clear_lines(self):
        lines_cleared = 0
        cleared_y_coords = [i for i, row in enumerate(self.grid) if all(c != (0,0,0) for c in row)]
        if not cleared_y_coords:
            return 0, []

        new_grid = [row for row in self.grid if row.count((0, 0, 0)) > 0]
        lines_cleared = GRID_HEIGHT - len(new_grid)
        for _ in range(lines_cleared):
            new_grid.insert(0, [(0, 0, 0) for _ in range(GRID_WIDTH)])
        self.grid = new_grid
        return lines_cleared, cleared_y_coords

    def draw(self, screen):
        # Draw animated background grid
        self.animation_timer = (self.animation_timer + 1) % 120
        alpha = 5 + abs(60 - self.animation_timer) // 6

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                # Draw main grid blocks
                if self.grid[y][x] != (0, 0, 0):
                    draw_block(screen, x, y, self.grid[y][x])
                # Draw background grid lines
                pygame.draw.rect(screen, (C_GRID_BG[0] + alpha, C_GRID_BG[1] + alpha, C_GRID_BG[2] + alpha),
                                 (PLAYFIELD_X + x * BLOCK_SIZE, PLAYFIELD_Y + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 1)

class SoundManager:
    def __init__(self):
        self.sounds = {}
        try:
            pygame.mixer.init()
            try:
                self.sounds['rotate'] = pygame.mixer.Sound('sounds/rotate.wav')
            except pygame.error as e:
                print(f"Warning: Could not load 'rotate.wav': {e}")
            try:
                self.sounds['clear'] = pygame.mixer.Sound('sounds/clear.wav')
            except pygame.error as e: print(f"Warning: Could not load 'clear.wav': {e}")
            try:
                self.sounds['lock'] = pygame.mixer.Sound('sounds/lock.wav')
            except pygame.error as e: print(f"Warning: Could not load 'lock.wav': {e}")
            try:
                self.sounds['gameover'] = pygame.mixer.Sound('sounds/gameover.wav')
            except pygame.error as e: print(f"Warning: Could not load 'gameover.wav': {e}")
            try:
                self.sounds['life'] = pygame.mixer.Sound('sounds/life.wav')
            except pygame.error as e: print(f"Warning: Could not load 'life.wav': {e}")
            try:
                self.sounds['lifelost'] = pygame.mixer.Sound('sounds/lifelost.mp3')
            except pygame.error as e: print(f"Warning: Could not load 'lifelost.mp3': {e}")
            try:
                self.sounds['stomp'] = pygame.mixer.Sound('sounds/stomp.wav')
            except pygame.error as e: print(f"Warning: Could not load 'stomp.wav': {e}")
            
            self.music_files = {
                'normal': 'sounds/music.mp3',
                'hurry': 'sounds/music2.mp3',
                'underground': 'sounds/undergroundtheme.mp3'
            }
            pygame.mixer.music.load(self.music_files['normal']) # Pre-load the normal music
            print("SoundManager initialized.")
        except pygame.error as e:
            print(f"SoundManager Error: {e}. Sounds/music disabled.")
            self.sounds = None

        # Music state
        self.current_music_mode = None # 'normal', 'hurry'
        self.MUSIC_END_EVENT = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.MUSIC_END_EVENT)
        self.music_on = True
        self.volume = 0.3  # Start at 30% volume
        if self.sounds:
            self.set_volume(self.volume)  # Apply the initial volume

    def play(self, sound_name):
        if self.sounds and sound_name in self.sounds:
            self.sounds[sound_name].play()

    def set_music_mode(self, mode, force_restart=False, loops=-1):
        """Sets the music to 'normal' or 'hurry'."""
        if not self.sounds or not self.music_on:
            return
        
        if mode == self.current_music_mode and not force_restart:
            return # Already playing the correct music, do nothing.

        if mode in self.music_files:
            try:
                pygame.mixer.music.load(self.music_files[mode])
                pygame.mixer.music.play(loops=loops, fade_ms=500) # Fade in new music
                self.current_music_mode = mode
            except pygame.error as e:
                print(f"Could not load or play music: {self.music_files[mode]}. Error: {e}")

    def play_initial_music(self):
        if self.sounds and self.music_on:
            self.set_music_mode('normal', force_restart=True)
            
    def toggle_music(self):
        self.music_on = not self.music_on
        if self.music_on:
            pygame.mixer.music.play(fade_ms=500)
        else:
            pygame.mixer.music.fadeout(500)
        return self.music_on

    def play_next_song(self):
        if not self.sounds: return
        # If the underground theme just finished, go back to normal music.
        if self.current_music_mode == 'underground':
            self.set_music_mode('normal', force_restart=True)
        # Otherwise, just loop the current song (normal or hurry)
        elif self.current_music_mode:
            self.set_music_mode(self.current_music_mode, force_restart=True, loops=-1)

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        if self.sounds:
            pygame.mixer.music.set_volume(self.volume)
            for sound in self.sounds.values():
                sound.set_volume(self.volume)

class Tetris:
    TURTLE_FRAMES = None # Class variable to hold turtle frames
    TURTLE_LIFE_ICON = None # For the UI
    CLOUD_FRAMES = None # Class variable for cloud frames
    GOLDEN_TURTLE_FRAMES = None # Class variable for golden turtle
    RED_TURTLE_FRAMES = None
    SPINY_FRAMES = None
    BUZZY_BEETLE_FRAMES = None
    ALIGNMENT_OFFSETS = {'x': 0, 'y': 0} # Global offsets for all enemies

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Turtle Tetris")
        self.clock = pygame.time.Clock()

        # --- Font Loading ---
        try:
            font_path = os.path.join('assets', 'PressStart2P-Regular.ttf')
            self.title_font = pygame.font.Font(font_path, 28)
            self.ui_font = pygame.font.Font(font_path, 16)
            self.game_over_font = pygame.font.Font(font_path, 40)
            self.small_ui_font = pygame.font.Font(font_path, 12)
        except pygame.error:
            print("Warning: Custom font not found. Falling back to default.")
            self.title_font = pygame.font.Font(None, 40)
            self.ui_font = pygame.font.Font(None, 30)
            self.game_over_font = pygame.font.Font(None, 70)
            self.small_ui_font = pygame.font.Font(None, 22)
        
        # --- New Sprite Loading System ---
        sprite_manager = SpriteManager()
        if sprite_manager.spritesheet:
            Tetris.TURTLE_FRAMES = sprite_manager.get_animation_frames('koopa_green')
            Tetris.RED_TURTLE_FRAMES = sprite_manager.get_animation_frames('koopa_red')
            Tetris.SPINY_FRAMES = sprite_manager.get_animation_frames('spiny', scale_factor=2.5)
            Tetris.BUZZY_BEETLE_FRAMES = sprite_manager.get_animation_frames('buzzy_beetle', scale_factor=2.5)

            # Fallback for red turtle if sprites are missing
            if not Tetris.RED_TURTLE_FRAMES: Tetris.RED_TURTLE_FRAMES = Tetris.TURTLE_FRAMES
            # Fallback for spiny
            if not Tetris.SPINY_FRAMES: Tetris.SPINY_FRAMES = Tetris.TURTLE_FRAMES
            # Fallback for buzzy beetle
            if not Tetris.BUZZY_BEETLE_FRAMES: Tetris.BUZZY_BEETLE_FRAMES = Tetris.TURTLE_FRAMES

            # Create golden frames by tinting the base turtle frames
            golden_frames = []
            for frame in Tetris.TURTLE_FRAMES:
                golden_frame = frame.copy()
                tint_surface = pygame.Surface(golden_frame.get_size(), pygame.SRCALPHA)
                tint_surface.fill((255, 223, 0, 100))  # Semi-transparent golden-yellow
                golden_frame.blit(tint_surface, (0, 0))
                golden_frames.append(golden_frame)
            Tetris.GOLDEN_TURTLE_FRAMES = golden_frames

        if Tetris.TURTLE_LIFE_ICON is None and Tetris.TURTLE_FRAMES:
            Tetris.TURTLE_LIFE_ICON = pygame.transform.scale(Tetris.TURTLE_FRAMES[0], (35, 35))
        self.sound_manager = SoundManager()
        self.high_score = 0
        self.load_high_scores()
        self.load_config() # Load alignment offsets
        self.music_button_rect = None
        self.hold_button_rect = None
        self.new_game_button_rect = None
        self.fullscreen = False
        self.minimize_button_rect = None
        self.start_green_button_rect = None
        self.start_red_button_rect = None
        self.start_spiny_button_rect = None
        self.start_progressive_button_rect = None
        self.start_buzzy_button_rect = None

        self.pause_button_rect = None
        self.volume_slider_rect = None
        self.volume_knob_rect = None
        self.dragging_volume = False
        self.is_losing_life = False # Flag for flashing lives UI
        self.game_state = 'START_SCREEN' # 'START_SCREEN', 'PLAYING', 'ALIGNMENT', 'NAME_ENTRY', 'GAME_OVER'

        # Store these for toggling fullscreen
        self.monitor_size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        self.screen_width = WINDOW_WIDTH
        self.screen_height = WINDOW_HEIGHT

        # --- Dynamic Scaling Setup ---
        # The game is rendered to this surface, which is then scaled to the display
        self.game_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        self.scaled_surface = self.game_surface # To cache the scaled surface

        # self.toggle_fullscreen() # Start in fullscreen
        # --- End Dynamic Scaling ---

        # For start screen animation
        self.start_screen_characters = []
        if Tetris.TURTLE_FRAMES: self.start_screen_characters.append(Turtle())
        if Tetris.RED_TURTLE_FRAMES: self.start_screen_characters.append(RedTurtle())
        if Tetris.SPINY_FRAMES: self.start_screen_characters.append(Spiny())
        if Tetris.BUZZY_BEETLE_FRAMES: self.start_screen_characters.append(BuzzyBeetle())
        for i, char in enumerate(self.start_screen_characters):
            char.y = 4 + i * 1.5 # Stagger them vertically
            char.x = -2.0 - i * 3.0 # Stagger them horizontally off-screen
            char.speed = 4.0 # Make them run faster for the intro
        self.alignment_char_index = 0

        self.start_game_button_rect = None
        self.needs_render = True # Flag to trigger re-scaling
        self.reset_game()

    def load_high_scores(self):
        """Loads high scores from a JSON file."""
        try:
            with open("highscores.json", "r") as f:
                self.high_scores = json.load(f)
        except (FileNotFoundError, ValueError):
            # Default high scores
            self.high_scores = [
                {"name": "GEM", "score": 5000},
                {"name": "INI", "score": 4000},
                {"name": "PRO", "score": 3000},
                {"name": "DEV", "score": 2000},
                {"name": "BOT", "score": 1000},
            ]

    def save_high_scores(self):
        """Saves the high score list to a JSON file."""
        with open("highscores.json", "w") as f:
            json.dump(self.high_scores, f, indent=4)

    def load_config(self):
        """Loads configuration like alignment offsets from a JSON file."""
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                Tetris.ALIGNMENT_OFFSETS = config.get('alignment_offsets', {'x': 0, 'y': 0})
        except (FileNotFoundError, ValueError):
            # If file doesn't exist or is invalid, use defaults
            Tetris.ALIGNMENT_OFFSETS = {'x': 0, 'y': 0}

    def save_config(self):
        """Saves the current configuration to a JSON file."""
        with open("config.json", "w") as f:
            json.dump({'alignment_offsets': Tetris.ALIGNMENT_OFFSETS}, f, indent=4)

    def check_if_high_score(self):
        """Checks if the current score is high enough for the leaderboard."""
        return self.score > self.high_scores[-1]["score"]

    def reset_game(self):
        # This sets up the variables for a new game, but doesn't change the state itself
        self.game_state = 'START_SCREEN'
        self.grid = Grid()
        self.bag = list(TETROMINO_DATA.keys())
        random.shuffle(self.bag)
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.held_piece = None
        self.can_hold = True
        self.paused = False
        self.score = 0
        self.level = 1
        self.total_lines_cleared = 0
        self.combo = -1
        self.player_name = ""
        self.enemy_mode = 'progressive' # 'progressive', 'green', 'red', 'spiny'
        self.lives = 5
        # --- Customizable Enemy Progression ---
        # Defines the order enemies appear in 'progressive' mode based on stomp count tiers.
        self.progressive_enemy_order = ['green', 'red', 'buzzy_beetle', 'spiny']

        self.turtles_stomped = 0 
        # Timers and controls
        self.fall_timer = 0
        self.lock_timer = 0
        self.das_timer = 0
        self.das_direction = 0
        self.key_down_held = False
        self.last_move_was_rotate = False
        self.t_spin_message_timer = 0
        self.is_back_to_back = False
        self.b2b_message_timer = 0
        # Turtle state
        self.particles = []
        self.game_time_elapsed = 0.0
        self.played_underground_theme = False
        self.tour_active = False
        self.tour_step = 0
        self.how_to_play_button_rect = None
        self.turtles = [] # List of active turtles
        # For levels 1-3, turtles spawn on a timer
        self.turtle_spawn_timer = 0
        self.turtle_spawn_interval = random.uniform(20, 35)
        self.cloud = Cloud() if Tetris.CLOUD_FRAMES else None



    def new_piece(self):
        if not self.bag:
            self.bag = list(TETROMINO_DATA.keys())
            random.shuffle(self.bag)
        return Tetromino(self.bag.pop())

    def move(self, dx, dy):
        self.current_piece.x += dx
        self.current_piece.y += dy
        if self.grid.check_collision(self.current_piece):
            self.current_piece.x -= dx
            self.current_piece.y -= dy
            self.last_move_was_rotate = False
            return False
        return True

    def rotate(self):
        original_shape = self.current_piece.shape
        original_rotation = self.current_piece.rotation
        self.current_piece.shape = self.current_piece.get_rotated_shape()
        self.current_piece.rotation = (self.current_piece.rotation + 1) % 4

        kick_table = WALL_KICK_DATA['I'] if self.current_piece.name == 'I' else WALL_KICK_DATA['JLSTZ']
        # This logic is simplified; a full SRS implementation is more complex
        # We'll use a basic lookup for clockwise rotation (0->R, R->2, etc.)
        rotation_index = (original_rotation * 2) % 8

        for kick_x, kick_y in kick_table[rotation_index]:
            self.current_piece.x += kick_x
            self.current_piece.y -= kick_y # Pygame Y is inverted
            if not self.grid.check_collision(self.current_piece):
                self.sound_manager.play('rotate')
                self.last_move_was_rotate = True
                return
            self.current_piece.x -= kick_x
            self.current_piece.y += kick_y

        # If all kicks fail, revert rotation
        self.current_piece.shape = original_shape
        self.current_piece.rotation = original_rotation

    def hard_drop(self):
        distance = 0
        while self.move(0, 1):
            distance += 1
        self.score += distance * 2
        self.last_move_was_rotate = False
        self.lock_current_piece()

    def hold(self):
        if not self.can_hold: return
        self.can_hold = False
        if self.held_piece is None:
            self.held_piece = self.current_piece
            self.current_piece = self.next_piece
            self.next_piece = self.new_piece()
        else:
            self.current_piece, self.held_piece = self.held_piece, self.current_piece
        
        self.held_piece.x = GRID_WIDTH // 2 - len(self.held_piece.shape[0]) // 2
        self.held_piece.y = 0
        self.current_piece.x = GRID_WIDTH // 2 - len(self.current_piece.shape[0]) // 2
        self.current_piece.y = 0

        if self.grid.check_collision(self.current_piece):
            if self.check_if_high_score():
                self.game_state = 'NAME_ENTRY'
            else:
                self.game_state = 'GAME_OVER'
            self.sound_manager.play('gameover') 

    def lock_current_piece(self):
        piece_center_x = self.current_piece.x + len(self.current_piece.shape[0]) / 2
        piece_center_y = self.current_piece.y + len(self.current_piece.shape) / 2

        is_t_spin = self._check_t_spin()

        self.grid.lock_piece(self.current_piece)
        self.sound_manager.play('lock')
        self.last_move_was_rotate = False # Reset after lock

        lines_cleared, cleared_y_coords = self.grid.clear_lines()

        # --- Turtle Stomp Check ---
        stomp_bonus = 0
        stomp_made = False
        for turtle in self.turtles:
            if turtle.state in ['active', 'landed']:
                for y, row in enumerate(self.current_piece.shape): # Check if any part of the new piece hits a turtle
                    for x, cell in enumerate(row): # yapf: disable
                        if cell and self.current_piece.x + x == turtle.x and self.current_piece.y + y == int(turtle.y): # Stomp collision
                            stomp_bonus += turtle.handle_stomp(self)
                            stomp_made = True
                            break
                    if stomp_made: 
                        break # Only one stomp sound per piece lock

        if lines_cleared > 0:
            self.sound_manager.play('clear')
            
            is_difficult_clear = (is_t_spin and lines_cleared > 0) or (lines_cleared == 4)
            b2b_bonus = 1.0

            if is_difficult_clear:
                if self.is_back_to_back:
                    b2b_bonus = 1.5 # 50% bonus for B2B
                    self.b2b_message_timer = 1.0 # Show B2B message
                self.is_back_to_back = True # Set for the next difficult clear
            else: # Simple clear breaks the B2B chain
                self.is_back_to_back = False

            if is_t_spin:
                self.t_spin_message_timer = 1.0 # Show message for 1 second
                self.create_particle_explosion(piece_center_x, piece_center_y, self.current_piece.color, count=30)
                base_points = [0, 800, 1200, 1600][lines_cleared] # T-Spin Single/Double/Triple
            else:
                base_points = [0, 100, 300, 500, 800][lines_cleared] # Standard clear
            
            # Apply B2B bonus to the base points and calculate final score
            final_base_points = int(base_points * b2b_bonus)
            self.combo += 1
            self.score += (final_base_points * self.level) + (max(0, self.combo) * 50 * self.level)

            # Special effect for Tetris
            if lines_cleared == 4:
                for y in cleared_y_coords:
                    for x in range(GRID_WIDTH):
                        self.create_particle_explosion(x, y, C_WHITE, count=5)

            # Check for defeated enemies on cleared lines
            for turtle in self.turtles[:]:
                if turtle.enemy_type in ['spiny', 'buzzy_beetle'] and int(turtle.y) in cleared_y_coords:
                    self.turtles.remove(turtle)
                    self.score += 1000 # Bonus for clearing a spiny
            self.total_lines_cleared += lines_cleared
            self.level = self.total_lines_cleared // 10 + 1
        else:
            if is_t_spin: # T-Spin Mini (0 lines cleared)
                b2b_bonus = 1.0
                if self.is_back_to_back:
                    b2b_bonus = 1.5
                    self.b2b_message_timer = 1.0
                self.is_back_to_back = True # T-Spin Mini continues/starts a B2B chain

                self.create_particle_explosion(piece_center_x, piece_center_y, self.current_piece.color, count=20)
                self.t_spin_message_timer = 1.0
                
                base_points = 100
                self.score += int(base_points * b2b_bonus) * self.level

            self.combo = -1
        
        self.score += stomp_bonus

        self.can_hold = True
        self.current_piece = self.next_piece
        self.next_piece = self.new_piece()

        if self.grid.check_collision(self.current_piece):
            if self.check_if_high_score():
                self.game_state = 'NAME_ENTRY'
            else:
                self.game_state = 'GAME_OVER'
            self.sound_manager.play('gameover') 

    def _check_t_spin(self):
        """Checks if the locked piece performed a valid T-Spin."""
        if not self.current_piece or self.current_piece.name != 'T' or not self.last_move_was_rotate:
            return False

        # The center of the T-piece's 3x3 bounding box
        cx, cy = self.current_piece.x + 1, self.current_piece.y + 1

        # The four corners around the T-piece center
        corners = [
            (cx - 1, cy - 1), # Top-left
            (cx + 1, cy - 1), # Top-right
            (cx - 1, cy + 1), # Bottom-left
            (cx + 1, cy + 1), # Bottom-right
        ]

        occupied_corners = 0
        for corner_x, corner_y in corners:
            # Check if corner is outside bounds or occupied in the grid
            if not (0 <= corner_x < GRID_WIDTH and 0 <= corner_y < GRID_HEIGHT) or \
               self.grid.grid[corner_y][corner_x] != (0, 0, 0):
                occupied_corners += 1

        # A T-Spin requires at least 3 occupied corners
        return occupied_corners >= 3

    def create_particle_explosion(self, grid_x, grid_y, color, count=20):
        """Creates a burst of particles at a specific grid location."""
        screen_x = PLAYFIELD_X + grid_x * BLOCK_SIZE
        screen_y = PLAYFIELD_Y + grid_y * BLOCK_SIZE
        for _ in range(count):
            self.particles.append(Particle(screen_x, screen_y, color))



    def handle_input(self, delta_time):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: return False
                
                if self.game_state == 'START_SCREEN':
                    if event.key == pygame.K_F1:
                        self.game_state = 'ALIGNMENT'
                        continue
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        self.game_state = 'PLAYING'
                        self.sound_manager.play_initial_music()
                    continue

                if self.game_state == 'GAME_OVER':
                    if event.key == pygame.K_r: self.reset_game() # Only check for keyboard reset here
                    else: continue

                if self.game_state == 'ALIGNMENT':
                    if event.key in [pygame.K_F1, pygame.K_ESCAPE]:
                        self.game_state = 'START_SCREEN'
                    elif event.key == pygame.K_LEFT: Tetris.ALIGNMENT_OFFSETS['x'] -= 1
                    elif event.key == pygame.K_RIGHT: Tetris.ALIGNMENT_OFFSETS['x'] += 1
                    elif event.key == pygame.K_UP: Tetris.ALIGNMENT_OFFSETS['y'] -= 1
                    elif event.key == pygame.K_DOWN: Tetris.ALIGNMENT_OFFSETS['y'] += 1
                    elif event.key == pygame.K_TAB:
                        self.alignment_char_index = (self.alignment_char_index + 1) % len(self.start_screen_characters)
                    elif event.key == pygame.K_s:
                        self.save_config()
                        # You might want a visual confirmation here
                    continue
                
                if self.game_state == 'NAME_ENTRY':
                    if event.key == pygame.K_RETURN:
                        self.high_scores.append({"name": self.player_name or "???", "score": self.score})
                        self.high_scores.sort(key=lambda x: x["score"], reverse=True)
                        self.high_scores = self.high_scores[:5] # Keep top 5
                        self.save_high_scores()
                        self.game_state = 'GAME_OVER'
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name = self.player_name[:-1]
                    elif len(self.player_name) < 3 and event.unicode.isalnum():
                        self.player_name += event.unicode.upper()
                    continue
                if event.key == pygame.K_p: self.paused = not self.paused
                if self.paused: continue

                if event.key == pygame.K_LEFT: self.das_direction = -1; self.das_timer = 0; self.move(-1, 0)
                if event.key == pygame.K_RIGHT: self.das_direction = 1; self.das_timer = 0; self.move(1, 0)
                if event.key == pygame.K_DOWN: self.key_down_held = True
                if event.key == pygame.K_UP: self.rotate()
                if event.key == pygame.K_SPACE: self.hard_drop()
                if event.key == pygame.K_c: self.hold()
                if event.key == pygame.K_F11: self.toggle_fullscreen()
            
            # --- Mouse Input Handling ---
            if self.game_state == 'START_SCREEN':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    scaled_pos = self._get_scaled_mouse_pos(event.pos)
                    if self.start_game_button_rect and self.start_game_button_rect.collidepoint(scaled_pos):
                        self.reset_game()
                        self.game_state = 'PLAYING' # Override reset
                        self.sound_manager.play_initial_music()
                    if self.start_green_button_rect and self.start_green_button_rect.collidepoint(scaled_pos):
                        self.reset_game()
                        self.enemy_mode = 'green'
                        self.game_state = 'PLAYING'
                        self.sound_manager.play_initial_music()
                    if self.start_red_button_rect and self.start_red_button_rect.collidepoint(scaled_pos):
                        self.reset_game()
                        self.enemy_mode = 'red'
                        self.game_state = 'PLAYING'
                        self.sound_manager.play_initial_music()
                    if self.start_spiny_button_rect and self.start_spiny_button_rect.collidepoint(scaled_pos):
                        self.reset_game()
                        self.enemy_mode = 'spiny'
                        self.game_state = 'PLAYING'
                        self.sound_manager.play_initial_music()
                    if self.start_progressive_button_rect and self.start_progressive_button_rect.collidepoint(scaled_pos):
                        self.reset_game()
                        self.enemy_mode = 'progressive'
                        self.game_state = 'PLAYING'
                        self.sound_manager.play_initial_music()
                    if self.start_buzzy_button_rect and self.start_buzzy_button_rect.collidepoint(scaled_pos):
                        self.reset_game()
                        self.enemy_mode = 'buzzy_beetle'
                        self.game_state = 'PLAYING'
                        self.sound_manager.play_initial_music()
                    if self.how_to_play_button_rect and self.how_to_play_button_rect.collidepoint(scaled_pos):
                        self.tour_active = True
                        self.tour_step = 0
                    
                    # Handle tour navigation
                    if self.tour_active:
                        if self.tour_next_button_rect and self.tour_next_button_rect.collidepoint(scaled_pos):
                            self.tour_step += 1
                            if self.tour_step >= len(TOUR_DATA):
                                self.tour_active = False
                        if self.tour_skip_button_rect and self.tour_skip_button_rect.collidepoint(scaled_pos):
                            self.tour_active = False

                        self.sound_manager.play_initial_music()
                continue
            if self.game_state == 'GAME_OVER':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    scaled_pos = self._get_scaled_mouse_pos(event.pos)
                    if self.new_game_button_rect and self.new_game_button_rect.collidepoint(scaled_pos):
                        self.reset_game() # This now sets state to 'PLAYING'
                continue # Skip all other input handling when game is over
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.game_state != 'PLAYING': continue # Ignore game clicks if not playing
                scaled_pos = self._get_scaled_mouse_pos(event.pos)
                if self.music_button_rect and self.music_button_rect.collidepoint(scaled_pos):
                    self.sound_manager.toggle_music()
                if self.hold_button_rect and self.hold_button_rect.collidepoint(scaled_pos):
                    self.hold()
                if self.pause_button_rect and self.pause_button_rect.collidepoint(scaled_pos):
                    self.paused = not self.paused
                if self.volume_knob_rect and self.volume_knob_rect.collidepoint(scaled_pos):
                    self.dragging_volume = True
                elif self.volume_slider_rect and self.volume_slider_rect.collidepoint(scaled_pos):
                    # Allow clicking on the slider bar to set volume
                    self.dragging_volume = True
                    self.update_volume_from_mouse(event.pos)
                    self.dragging_volume = False # Set to false so it doesn't stick

                if self.minimize_button_rect and self.minimize_button_rect.collidepoint(scaled_pos):
                    pygame.display.iconify()


            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging_volume = False

            if event.type == pygame.MOUSEMOTION:
                if self.dragging_volume:
                    self.update_volume_from_mouse(event.pos)
            
            if event.type == self.sound_manager.MUSIC_END_EVENT:
                if self.sound_manager.music_on:
                    self.sound_manager.play_next_song()

            if event.type == pygame.VIDEORESIZE:
                self.screen_width, self.screen_height = event.size
                self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
                self.needs_render = True # Trigger a re-scale and blit

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT and self.das_direction == -1: self.das_direction = 0
                if event.key == pygame.K_RIGHT and self.das_direction == 1: self.das_direction = 0
                if event.key == pygame.K_DOWN: self.key_down_held = False

        return True

    def _get_scaled_mouse_pos(self, screen_pos):
        """Translates screen mouse coordinates to game surface coordinates."""
        scale = min(self.screen_width / WINDOW_WIDTH, self.screen_height / WINDOW_HEIGHT)
        scaled_width, scaled_height = int(WINDOW_WIDTH * scale), int(WINDOW_HEIGHT * scale)
        blit_x = (self.screen_width - scaled_width) / 2
        blit_y = (self.screen_height - scaled_height) / 2
        
        return ((screen_pos[0] - blit_x) / scale, (screen_pos[1] - blit_y) / scale)

    def update_volume_from_mouse(self, mouse_pos):
        game_mouse_x, _ = self._get_scaled_mouse_pos(mouse_pos)
        if self.volume_slider_rect:
            volume = (game_mouse_x - self.volume_slider_rect.left) / self.volume_slider_rect.width
            volume = max(0.0, min(1.0, volume))
            self.sound_manager.set_volume(volume)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        
        if self.fullscreen:
            self.screen_width, self.screen_height = self.monitor_size
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.FULLSCREEN | pygame.RESIZABLE)
        else:
            self.screen_width, self.screen_height = WINDOW_WIDTH, WINDOW_HEIGHT
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        self.needs_render = True

    def update(self, delta_time):
        if self.game_state == 'START_SCREEN':
            self.sound_manager.set_music_mode('hurry')
            for char in self.start_screen_characters:
                char.update_animation()
                char.x += char.speed * char.direction * delta_time
                # Wrap around screen
                if char.x > WINDOW_WIDTH / BLOCK_SIZE + 2:
                    char.x = -2.0
                elif char.x < -2.0:
                    char.x = WINDOW_WIDTH / BLOCK_SIZE + 2
            return # Don't run game logic on start screen

        if self.game_state == 'ALIGNMENT':
            return # No game logic in alignment mode

        if self.game_state != 'PLAYING' or self.paused: return

        # --- Delayed Auto Shift (DAS) ---
        if self.das_direction != 0:
            self.das_timer += delta_time
            # Reset rotation flag if player moves piece sideways
            if self.last_move_was_rotate:
                self.last_move_was_rotate = False

            if self.das_timer > 0.15: # DAS delay
                # To make DAS feel smooth, we can move every few frames after the initial delay
                if (self.das_timer - 0.15) % 0.06 < delta_time: # Move every 60ms
                    self.move(self.das_direction, 0)

        # Gravity
        # Reset the life-loss warning flag at the start of the update
        self.is_losing_life = False

        # --- Timed Music Change ---
        self.game_time_elapsed += delta_time
        if not self.played_underground_theme and self.game_time_elapsed >= 90.0:
            # Play underground theme once (loops=0)
            self.sound_manager.set_music_mode('underground', force_restart=True, loops=0)
            self.played_underground_theme = True

        # Update particles
        self.particles = [p for p in self.particles if p.lifetime > 0]
        for p in self.particles: p.update(delta_time)

        if self.b2b_message_timer > 0:
            self.b2b_message_timer -= delta_time

        if self.t_spin_message_timer > 0:
            self.t_spin_message_timer -= delta_time

        fall_speed = self._get_fall_speed()
        soft_drop_speed = 0.05
        self.fall_timer += delta_time

        effective_fall_speed = soft_drop_speed if self.key_down_held else fall_speed
        if self.fall_timer >= effective_fall_speed:
            self.fall_timer = 0
            if not self.move(0, 1):
                self.lock_timer += effective_fall_speed
            elif self.last_move_was_rotate:
                self.last_move_was_rotate = False # Any vertical movement invalidates T-Spin
            else:
                self.lock_timer = 0 # Reset lock timer if piece moves down

        # Lock Delay
        if self.lock_timer > 0.5: # 500ms lock delay
            self.lock_current_piece()
            self.lock_timer = 0
        
        # --- Level-Based Enemy Logic ---
        # Levels 1-3: Spikes spawn randomly from the top
        if 1 <= self.level <= 3:
            self.turtle_spawn_timer += delta_time
            if self.turtle_spawn_timer > self.turtle_spawn_interval:
                self.spawn_enemy()
                self.turtle_spawn_timer = 0
                self.turtle_spawn_interval = random.uniform(max(10, 20 - self.level), max(15, 35 - self.level * 2))

        # Levels 4+: The Cloud appears and drops the Spikes
        elif self.level >= 4:
            if self.cloud:
                self.cloud.update(delta_time)
                self.cloud.drop_timer += delta_time
                if self.cloud.drop_timer > self.cloud.drop_interval:
                    self.spawn_enemy(from_cloud=True)
                    self.cloud.drop_timer = 0
                    if self.level >= 8: self.cloud.drop_interval = random.uniform(8, 15)
                    else: self.cloud.drop_interval = random.uniform(15, 25)
        
        # --- Enemy Movement and Removal ---
        turtles_to_remove = []
        for turtle in self.turtles:
            turtle.update_animation()
            if turtle.state == 'landed':
                self.is_losing_life = True # A turtle is landed, so lives are in danger

            if turtle.update_movement(delta_time, self.grid):
                turtles_to_remove.append(turtle)

        # --- Music Control based on enemy state ---
        if any(t.state == 'landed' for t in self.turtles):
            self.sound_manager.set_music_mode('hurry')
        else:
            self.sound_manager.set_music_mode('normal')

        # Check for life drain from landed turtles
        for turtle in self.turtles:
            if turtle.state == 'landed' and turtle.landed_timer >= LIFE_DRAIN_SECONDS:
                self.lives = max(0, self.lives - 1)
                self.is_losing_life = True # Triggers UI bar
                if self.lives == 0:
                    self.game_state = 'GAME_OVER' if not self.check_if_high_score() else 'NAME_ENTRY'
                    self.sound_manager.play('gameover')
                self.sound_manager.play('lifelost')
                turtles_to_remove.append(turtle) # Remove turtle after it drains a life

        for turtle in turtles_to_remove:
            if turtle in self.turtles:
                self.turtles.remove(turtle)

    def _get_fall_speed(self):
        """Calculates fall speed based on level. Speed increases as level goes up."""
        return max(0.1, 0.8 - (self.level - 1) * 0.05)

    def spawn_enemy(self, from_cloud=False):
        """Spawns a new enemy based on game progress."""
        enemy_type = self.enemy_mode
        
        if self.enemy_mode == 'progressive':
            # Determine enemy type based on number of stomps and the custom order
            stomp_tier = self.turtles_stomped // 3
            # Clamp the tier to the length of the order list
            tier_index = min(stomp_tier, len(self.progressive_enemy_order) - 1)
            enemy_type = self.progressive_enemy_order[tier_index]

        # If enemy_mode is 'green', 'red', or 'spiny', it will use that directly.
        # Create the enemy
        new_turtle = self._create_enemy(enemy_type)

        # Set position (either from cloud or random at top)
        if from_cloud and self.cloud:
            new_turtle.x = int(self.cloud.x + (self.cloud.frames[0].get_width() / 2)) // BLOCK_SIZE
            new_turtle.x = max(0, min(GRID_WIDTH - 1, new_turtle.x))
            new_turtle.y = (self.cloud.y + self.cloud.frames[0].get_height()) / BLOCK_SIZE
        
        # Check if spawn point is clear before adding
        if self.grid.grid[0][int(new_turtle.x)] == (0, 0, 0):
            self.turtles.append(new_turtle)
            print(f"Spawned {new_turtle.ENEMY_TYPE} at ({new_turtle.x}, {new_turtle.y})")

    def _create_enemy(self, enemy_type):
        """Factory method to create an enemy of a specific type."""
        if enemy_type == 'red':
            return RedTurtle()
        if enemy_type == 'spiny':
            return Spiny()
        if enemy_type == 'buzzy_beetle':
            return BuzzyBeetle()
        return Turtle() # Default to green

    def draw(self):
        if self.needs_render:
            self.game_surface.fill(C_DARK_BLUE)
            self.grid.draw(self.game_surface)
            self.draw_current_and_ghost(self.game_surface)
            if self.level >= 4 and self.cloud: self.draw_cloud(self.game_surface)
            for turtle in self.turtles:
                turtle.draw(self.game_surface)
            self.draw_ui(self.game_surface)

            if self.game_state == 'GAME_OVER': self.draw_game_over_screen(self.game_surface)
            if self.game_state == 'START_SCREEN': self.draw_start_screen(self.game_surface)
            if self.game_state == 'NAME_ENTRY': self.draw_name_entry_screen(self.game_surface)
            if self.game_state == 'ALIGNMENT': self.draw_alignment_screen(self.game_surface)
            if self.paused and self.game_state == 'PLAYING': self.draw_pause_screen(self.game_surface)
            
            # Draw particles on top of everything else in the game world
            for p in self.particles:
                p.draw(self.game_surface)

            scale = min(self.screen_width / WINDOW_WIDTH, self.screen_height / WINDOW_HEIGHT)
            scaled_width, scaled_height = int(WINDOW_WIDTH * scale), int(WINDOW_HEIGHT * scale)
            self.scaled_surface = pygame.transform.scale(self.game_surface, (scaled_width, scaled_height))
            self.needs_render = False

        self.screen.fill(C_BLACK)
        blit_x = (self.screen_width - self.scaled_surface.get_width()) / 2
        blit_y = (self.screen_height - self.scaled_surface.get_height()) / 2
        self.screen.blit(self.scaled_surface, (blit_x, blit_y))
        pygame.display.flip()

    def draw_current_and_ghost(self, surface):
        if self.current_piece:
            ghost = Tetromino(self.current_piece.name)
            ghost.shape = self.current_piece.shape
            ghost.x, ghost.y = self.current_piece.x, self.current_piece.y
            while not self.grid.check_collision(ghost):
                ghost.y += 1
            ghost.y -= 1
            for y, row in enumerate(ghost.shape):
                for x, cell in enumerate(row):
                    if cell:
                        draw_block(surface, ghost.x + x, ghost.y + y, ghost.color, is_ghost=True, alpha=100)
            for y, row in enumerate(self.current_piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        draw_block(surface, self.current_piece.x + x, self.current_piece.y + y, self.current_piece.color)

    def draw_ui(self, surface):
        right_panel_x = PLAYFIELD_X + PLAYFIELD_WIDTH + 40
        y_pos = PLAYFIELD_Y
        draw_text(surface, "SCORE", self.small_ui_font, C_NEON_PINK, right_panel_x, y_pos)
        draw_text(surface, f"{self.score}", self.small_ui_font, C_WHITE, right_panel_x, y_pos + 20)
        y_pos += 55
        top_score_name = self.high_scores[0]['name']
        top_score_value = self.high_scores[0]['score']
        draw_text(surface, f"#1: {top_score_name}", self.small_ui_font, C_NEON_PINK, right_panel_x, y_pos)
        draw_text(surface, f"{top_score_value}", self.small_ui_font, C_WHITE, right_panel_x, y_pos + 20)
        y_pos += 55
        draw_text(surface, "LINES", self.small_ui_font, C_NEON_PINK, right_panel_x, y_pos)
        draw_text(surface, f"{self.total_lines_cleared}", self.small_ui_font, C_WHITE, right_panel_x, y_pos + 20)
        draw_text(surface, "LEVEL", self.small_ui_font, C_NEON_PINK, right_panel_x + 80, y_pos)
        draw_text(surface, f"{self.level}", self.small_ui_font, C_WHITE, right_panel_x + 80, y_pos + 20)
        y_pos += 55
        draw_text(surface, "LIVES:", self.small_ui_font, C_NEON_PINK, right_panel_x, y_pos)
        
        # --- New Life Drain Timer Bar ---
        # Show the progress of the most dangerous turtle (the one with the highest timer)
        landed_turtles = [t for t in self.turtles if t.state == 'landed']
        if landed_turtles:
            most_urgent_turtle = max(landed_turtles, key=lambda t: t.landed_timer)
            progress = min(most_urgent_turtle.landed_timer / LIFE_DRAIN_SECONDS, 1.0)

            bar_width = 150
            bar_height = 5
            bar_x = right_panel_x
            bar_y = y_pos + 55 # Position below the life icons
            pygame.draw.rect(surface, C_GRID_BG, (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, bar_width * progress, bar_height))

        if Tetris.TURTLE_LIFE_ICON:
            for i in range(self.lives):
                surface.blit(Tetris.TURTLE_LIFE_ICON, (right_panel_x + i * 30, y_pos + 20))
        y_pos += 70 # Adjusted for the new timer bar
        draw_text(surface, "ENEMY STOMPED", self.small_ui_font, C_NEON_PINK, right_panel_x, y_pos)
        draw_text(surface, f"{self.turtles_stomped}", self.small_ui_font, C_WHITE, right_panel_x, y_pos + 20)
        y_pos += 60
        draw_text(surface, "NEXT", self.small_ui_font, C_NEON_PINK, right_panel_x, y_pos)
        if self.next_piece:
            draw_piece_preview(surface, self.next_piece, right_panel_x, y_pos + 30)
        y_pos += 120
        draw_text(surface, "HOLD", self.small_ui_font, C_NEON_PINK, right_panel_x, y_pos)
        if self.held_piece:
            draw_piece_preview(surface, self.held_piece, right_panel_x, y_pos + 30)
        y_pos += 120
        self.hold_button_rect = draw_ui_button(surface, "Hold (C)", self.small_ui_font, right_panel_x, y_pos)
        pause_text = "Resume (P)" if self.paused else "Pause (P)"
        self.pause_button_rect = draw_ui_button(surface, pause_text, self.small_ui_font, right_panel_x, y_pos + 40)
        music_status = "ON" if self.sound_manager.music_on else "OFF"
        self.music_button_rect = draw_ui_button(surface, f"Music: {music_status}", self.small_ui_font, right_panel_x, y_pos + 80) 
        self.minimize_button_rect = draw_ui_button(surface, "Minimize", self.small_ui_font, right_panel_x, y_pos + 120)
        y_pos += 180
        self.draw_volume_slider(surface, right_panel_x, y_pos)
        if self.combo > 0:
            combo_text = self.ui_font.render(f"COMBO x{self.combo + 1}!", True, C_NEON_PINK)
            combo_rect = combo_text.get_rect(center=(PLAYFIELD_X + PLAYFIELD_WIDTH / 2, PLAYFIELD_Y + PLAYFIELD_HEIGHT - 30))
            surface.blit(combo_text, combo_rect)
        if self.t_spin_message_timer > 0:
            t_spin_text = self.ui_font.render("T-SPIN!", True, C_NEON_PINK)
            t_spin_rect = t_spin_text.get_rect(center=(PLAYFIELD_X + PLAYFIELD_WIDTH / 2, PLAYFIELD_Y + PLAYFIELD_HEIGHT - 60))
            surface.blit(t_spin_text, t_spin_rect)
        if self.b2b_message_timer > 0:
            b2b_text = self.ui_font.render("BACK-TO-BACK!", True, C_NEON_PINK)
            b2b_rect = b2b_text.get_rect(center=(PLAYFIELD_X + PLAYFIELD_WIDTH / 2, PLAYFIELD_Y + PLAYFIELD_HEIGHT - 85))
            surface.blit(b2b_text, b2b_rect)

    def draw_cloud(self, surface):
        if self.cloud and self.cloud.frames:
            image_to_draw = self.cloud.frames[self.cloud.current_frame]
            surface.blit(image_to_draw, (self.cloud.x, self.cloud.y))

    def draw_game_over_screen(self, surface):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        draw_text(surface, "GAME OVER", self.game_over_font, C_NEON_PINK, WINDOW_WIDTH / 2, 100, center=True)

        draw_text(surface, "HIGH SCORES", self.title_font, C_NEON_PINK, WINDOW_WIDTH / 2, 200, center=True)
        for i, entry in enumerate(self.high_scores):
            y_pos = 250 + i * 40
            draw_text(surface, f"{i+1}. {entry['name']}", self.title_font, C_WHITE, WINDOW_WIDTH / 2 - 80, y_pos, center=False)
            draw_text(surface, f"{entry['score']}", self.title_font, C_WHITE, WINDOW_WIDTH / 2 + 80, y_pos, center=False)
        
        self.new_game_button_rect = draw_ui_button(surface, "Play Again (R)", self.title_font, WINDOW_WIDTH / 2, WINDOW_HEIGHT - 100, center=True)

    def draw_start_screen(self, surface):
        self.draw_pixel_art_background(surface)
        draw_text(surface, "Turtle Tetris", self.game_over_font, C_NEON_PINK, WINDOW_WIDTH / 2, 60, center=True)

        # --- Command List ---
        commands = [
            ("CONTROLS", self.ui_font, C_NEON_PINK),
            ("", self.small_ui_font, C_WHITE),
            ("Move", "Arrows", C_WHITE),
            ("Rotate", "Up", C_WHITE),
            ("Soft Drop", "Down", C_WHITE),
            ("Hard Drop", "Space", C_WHITE),
            ("Hold", "C", C_WHITE),
            ("Pause", "P", C_WHITE),
            ("Fullscreen", "F11", C_WHITE),
        ]
        y_pos = 150
        for item in commands:
            if len(item) == 3:
                key, desc, color = item
                draw_text(surface, key, self.small_ui_font, color, 40, y_pos)
                draw_text(surface, desc, self.small_ui_font, color, 160, y_pos)
                y_pos += 20
            else: # Title or spacer
                title, font, color = item
                draw_text(surface, title, font, color, 40, y_pos)
                y_pos += font.get_height()

        for char in self.start_screen_characters: char.draw(surface)
        
        draw_text(surface, "CHOOSE YOUR CHALLENGE", self.ui_font, C_NEON_PINK, WINDOW_WIDTH / 2, 200, center=True)
        
        # --- Enemy Selection Buttons ---
        button_y = WINDOW_HEIGHT - 120
        button_width = 160
        button_spacing = 10
        total_width = 5 * button_width + 4 * button_spacing # Adjusted for 5 buttons
        start_x = (WINDOW_WIDTH - total_width) / 2 + (button_width / 2)

        # Repositioning logic for 5 buttons
        positions = [start_x + i * (button_width + button_spacing) for i in range(5)]

        # Green Turtle
        if Tetris.TURTLE_FRAMES:
            surface.blit(Tetris.TURTLE_FRAMES[0], Tetris.TURTLE_FRAMES[0].get_rect(center=(positions[0], button_y - 50)))
        self.start_green_button_rect = draw_ui_button(surface, "Green Only", self.small_ui_font, start_x, button_y, center=True)
        # Red Turtle
        if Tetris.RED_TURTLE_FRAMES:
            surface.blit(Tetris.RED_TURTLE_FRAMES[0], Tetris.RED_TURTLE_FRAMES[0].get_rect(center=(start_x + button_width + button_spacing, button_y - 50)))
        self.start_red_button_rect = draw_ui_button(surface, "Red Only", self.small_ui_font, start_x + button_width + button_spacing, button_y, center=True)
        # Spiny
        if Tetris.SPINY_FRAMES:
            surface.blit(Tetris.SPINY_FRAMES[0], Tetris.SPINY_FRAMES[0].get_rect(center=(start_x + 2 * (button_width + button_spacing), button_y - 50)))
        self.start_spiny_button_rect = draw_ui_button(surface, "Spiny Siege", self.small_ui_font, start_x + 2 * (button_width + button_spacing), button_y, center=True)
        # Buzzy Beetle
        if Tetris.BUZZY_BEETLE_FRAMES:
            surface.blit(Tetris.BUZZY_BEETLE_FRAMES[0], Tetris.BUZZY_BEETLE_FRAMES[0].get_rect(center=(start_x + 3 * (button_width + button_spacing), button_y - 50)))
        self.start_buzzy_button_rect = draw_ui_button(surface, "Buzzy Blitz", self.small_ui_font, start_x + 3 * (button_width + button_spacing), button_y, center=True)
        # Progressive Mode
        draw_text(surface, "?", self.game_over_font, C_NEON_PINK, start_x + 4 * (button_width + button_spacing), button_y - 50, center=True)
        self.start_progressive_button_rect = draw_ui_button(surface, "Progressive", self.small_ui_font, start_x + 4 * (button_width + button_spacing), button_y, center=True)
        
        self.how_to_play_button_rect = draw_ui_button(surface, "How to Play", self.small_ui_font, WINDOW_WIDTH / 2, WINDOW_HEIGHT - 55, center=True)
        draw_text(surface, "Press F1 for Sprite Alignment Tool", self.small_ui_font, C_WHITE, WINDOW_WIDTH / 2, WINDOW_HEIGHT - 20, center=True)

        # --- Interactive Tour ---
        if self.tour_active:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))
            
            step_data = TOUR_DATA[self.tour_step]
            self.tour_next_button_rect, self.tour_skip_button_rect = draw_speech_bubble(surface, step_data, self.small_ui_font)

    def draw_alignment_screen(self, surface):
        surface.fill(C_DARK_BLUE)
        center_x, center_y = WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2

        # Draw alignment box
        box_size = BLOCK_SIZE * 3
        box_rect = pygame.Rect(0, 0, box_size, box_size)
        box_rect.center = (center_x, center_y)
        pygame.draw.rect(surface, C_GRID_BG, box_rect)
        pygame.draw.rect(surface, C_NEON_PINK, box_rect, 1)

        # Draw character
        char_to_draw = self.start_screen_characters[self.alignment_char_index]
        frame = char_to_draw.walk_frames_right[0]
        offset_x, offset_y = Tetris.ALIGNMENT_OFFSETS['x'], Tetris.ALIGNMENT_OFFSETS['y']
        frame_rect = frame.get_rect(center=(center_x + offset_x, center_y + offset_y))
        surface.blit(frame, frame_rect)

        # Draw instructions and info
        draw_text(surface, "Sprite Alignment Tool", self.ui_font, C_NEON_PINK, center_x, 50, center=True)
        draw_text(surface, f"Offsets: X={offset_x}, Y={offset_y}", self.ui_font, C_WHITE, center_x, 90, center=True)
        draw_text(surface, f"Current: {char_to_draw.enemy_type.title()}", self.ui_font, C_WHITE, center_x, 120, center=True)

        instructions = ["Use Arrow Keys to move", "TAB to cycle character", "S to Save offsets", "F1 or ESC to exit"]
        for i, text in enumerate(instructions):
            draw_text(surface, text, self.small_ui_font, C_WHITE, center_x, WINDOW_HEIGHT - 100 + i * 20, center=True)

    def draw_name_entry_screen(self, surface):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        draw_text(surface, "NEW HIGH SCORE!", self.game_over_font, C_NEON_PINK, WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 150, center=True)
        draw_text(surface, "Enter Your Name (3 letters)", self.title_font, C_WHITE, WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 50, center=True)
        cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        display_name = self.player_name + cursor
        draw_text(surface, display_name, self.game_over_font, C_WHITE, WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 20, center=True)
        draw_text(surface, "Press ENTER to confirm", self.ui_font, C_WHITE, WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 100, center=True)

    def draw_pause_screen(self, surface):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        draw_text(surface, "PAUSED", self.game_over_font, C_NEON_PINK, WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2, center=True)

    def draw_volume_slider(self, surface, x, y):
        draw_text(surface, "Volume", self.small_ui_font, C_NEON_PINK, x, y)
        slider_width = 150; slider_height = 8
        self.volume_slider_rect = pygame.Rect(x, y + 30, slider_width, slider_height)
        pygame.draw.rect(surface, C_GRID_BG, self.volume_slider_rect, border_radius=4)
        knob_radius = 8
        knob_x = self.volume_slider_rect.left + self.sound_manager.volume * self.volume_slider_rect.width
        knob_y = self.volume_slider_rect.centery
        self.volume_knob_rect = pygame.Rect(knob_x - knob_radius, knob_y - knob_radius, knob_radius * 2, knob_radius * 2)
        pygame.draw.circle(surface, C_NEON_PINK, (knob_x, knob_y), knob_radius)

    def draw_pixel_art_background(self, surface):
        surface.fill((92, 148, 252))
        pygame.draw.rect(surface, (221, 117, 6), (0, WINDOW_HEIGHT - 60, WINDOW_WIDTH, 60))
        pygame.draw.circle(surface, (0, 168, 0), (WINDOW_WIDTH - 150, WINDOW_HEIGHT - 60), 100)
        pygame.draw.circle(surface, (0, 220, 0), (WINDOW_WIDTH - 180, WINDOW_HEIGHT - 60), 70)
        pygame.draw.circle(surface, (0, 168, 0), (150, WINDOW_HEIGHT - 60), 120)
        pygame.draw.circle(surface, (0, 220, 0), (180, WINDOW_HEIGHT - 60), 90)

    def run(self):
        self.running = True
        if self.game_state == 'PLAYING':
            self.sound_manager.play_initial_music()

        while self.running:
            delta_time = self.clock.tick(60) / 1000.0
            self.running = self.handle_input(delta_time)
            self.update(delta_time)
            self.needs_render = True
            self.draw()
        
        if self.sound_manager.sounds: pygame.mixer.music.fadeout(500)
        self.save_high_scores()
        pygame.quit()
        sys.exit()

def draw_piece_preview(screen, piece, start_x, start_y):
    offset_x = (4 - len(piece.shape[0])) * BLOCK_SIZE / 2
    offset_y = (4 - len(piece.shape)) * BLOCK_SIZE / 2
    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                px = start_x + x * BLOCK_SIZE + offset_x
                py = start_y + y * BLOCK_SIZE + offset_y
                draw_block(screen, 0, 0, piece.color, offset_x=px-PLAYFIELD_X, offset_y=py-PLAYFIELD_Y)

def draw_ui_button(screen, text, font, x, y, center=False):
    text_surface = font.render(text, True, C_WHITE)
    if center: button_rect = text_surface.get_rect(center=(x, y))
    else: button_rect = text_surface.get_rect(topleft=(x, y))
    button_rect.inflate_ip(10, 6)
    pygame.draw.rect(screen, C_GRID_BG, button_rect, border_radius=5)
    pygame.draw.rect(screen, C_NEON_PINK, button_rect, 2, border_radius=5)
    screen.blit(text_surface, text_surface.get_rect(center=button_rect.center))
    return button_rect

def draw_text_block(surface, lines, center_x, start_y):
    surfaces = []
    for text, font, color in lines:
        text_surf = font.render(text, True, color)
        surfaces.append(text_surf)
    current_y = start_y
    for text_surf in surfaces:
        x = center_x - text_surf.get_width() / 2
        surface.blit(text_surf, (x, current_y))
        current_y += text_surf.get_height()

def draw_text(screen, text, font, color, x, y, center=False):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    screen.blit(text_surface, text_rect)

TOUR_DATA = [
    {"text": "This is the Playfield. Clear lines by filling them with blocks!", "pos": (PLAYFIELD_X + PLAYFIELD_WIDTH / 2, PLAYFIELD_Y + 50), "point_dir": "down"},
    {"text": "This panel shows your Score, Level, and current High Score.", "pos": (PLAYFIELD_X + PLAYFIELD_WIDTH + 120, PLAYFIELD_Y + 80), "point_dir": "left"},
    {"text": "Watch out for enemies! Stomp them by landing a piece on them.", "pos": (PLAYFIELD_X + PLAYFIELD_WIDTH / 2, PLAYFIELD_Y + 200), "point_dir": "up"},
    {"text": "If an enemy reaches a completed block, a timer starts. Stomp them before you lose a life!", "pos": (PLAYFIELD_X + PLAYFIELD_WIDTH / 2, PLAYFIELD_Y + 300), "point_dir": "up"},
    {"text": "This shows the Next piece. Plan ahead!", "pos": (PLAYFIELD_X + PLAYFIELD_WIDTH + 120, PLAYFIELD_Y + 350), "point_dir": "left"},
    {"text": "Use the Hold queue to save a piece for later. Press 'C' to swap!", "pos": (PLAYFIELD_X + PLAYFIELD_WIDTH + 120, PLAYFIELD_Y + 470), "point_dir": "left"},
    {"text": "You're ready to play! Choose a mode to begin.", "pos": (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2), "point_dir": "none"},
]

def draw_speech_bubble(surface, step_data, font):
    """Draws a text bubble for the tutorial."""
    text = step_data["text"]
    pos = step_data["pos"]
    point_dir = step_data["point_dir"]

    # Create text surfaces
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        if font.size(current_line + " " + word)[0] < 200:
            current_line += " " + word
        else:
            lines.append(current_line.strip())
            current_line = word
    lines.append(current_line.strip())
    
    text_surfaces = [font.render(line, True, C_WHITE) for line in lines]
    text_height = sum(s.get_height() for s in text_surfaces)
    text_width = max(s.get_width() for s in text_surfaces)

    bubble_rect = pygame.Rect(0, 0, text_width + 20, text_height + 60)
    bubble_rect.center = pos
    pygame.draw.rect(surface, C_GRID_BG, bubble_rect, border_radius=10)
    pygame.draw.rect(surface, C_NEON_PINK, bubble_rect, 2, border_radius=10)

    for i, ts in enumerate(text_surfaces):
        surface.blit(ts, (bubble_rect.x + 10, bubble_rect.y + 10 + i * font.get_height()))

    next_button = draw_ui_button(surface, "Next", font, bubble_rect.right - 40, bubble_rect.bottom - 20, center=True)
    skip_button = draw_ui_button(surface, "Skip Tour", font, bubble_rect.left + 50, bubble_rect.bottom - 20, center=True)
    return next_button, skip_button

def draw_text(screen, text, font, color, x, y, center=False):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    screen.blit(text_surface, text_rect)

if __name__ == "__main__":
    game = Tetris()
    game.run()
