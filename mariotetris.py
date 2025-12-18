- import pygame

import random

import sys

import json

import os



# --- Game Configuration ---

GRID_WIDTH, GRID_HEIGHT = 10, 20

BLOCK_SIZE = 24



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



class SpriteManager:

    """Loads and manages all sprites from a single spritesheet."""

    def __init__(self):

        self.spritesheet = None

        self.sprite_data = {

            "koopa_green": {

                "walk_1": {"x": 288, "y": 544, "w": 16, "h": 24},

                "walk_2": {"x": 338, "y": 544, "w": 16, "h": 24}

            },

            "koopa_red": {

                "walk_1": {"x": 288, "y": 640, "w": 16, "h": 24},

                "walk_2": {"x": 338, "y": 640, "w": 16, "h": 24}

            },

            "spiny": {

                "walk_1": {"x": 160, "y": 8, "w": 16, "h": 16}, # Placeholder

                "walk_2": {"x": 176, "y": 8, "w": 16, "h": 16}  # Placeholder

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

        self.dying_timer = 0 # Timer for removal after stomp



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

            self.dying_timer += delta_time

            if self.dying_timer > 1.0: # Remove after 1 second

                return True # Indicate removal

            # Let the dying animation fall off screen

            self.y += 10 * delta_time

            return False



        if self.state == 'active':

            # --- 1. Gravity (Falling) ---

            self.y += self.speed * delta_time

           

            # Check for collision with the grid

            landed_y = int(self.y + 1)

            landed_x = int(self.x)

           

            if landed_y >= GRID_HEIGHT or (0 <= landed_x < GRID_WIDTH and 0 <= landed_y < GRID_HEIGHT and game_grid.grid[landed_y][landed_x] != (0, 0, 0)):

                self.y = landed_y - 1 # Snap to the block above

                self.state = 'landed'

                self.move_timer = 0 # Start walk timer



        elif self.state == 'landed':

            self.landed_timer += delta_time

            # --- 2. Life Drain Timer ---

            if self.landed_timer > 15.0: # 15 seconds life limit

                return True # Signal game to remove turtle and penalize player



            # --- 3. Walking ---

            self.move_timer += delta_time

            if self.move_timer >= self.move_interval:

                self.move_timer -= self.move_interval

               

                next_x = int(self.x + self.direction)

               

                # Check for walking off the edge or hitting a wall

                if 0 <= next_x < GRID_WIDTH:

                    block_below_next_x = int(self.y) + 1

                   

                    block_in_front = game_grid.grid[int(self.y)][next_x] != (0, 0, 0)

                    has_ground = block_below_next_x < GRID_HEIGHT and game_grid.grid[block_below_next_x][next_x] != (0, 0, 0)

                   

                    if self.enemy_type in ['green', 'spiny']:

                        if not has_ground and not block_in_front:

                            self.state = 'active'; self.x = next_x

                        elif block_in_front: self.direction *= -1

                        else: self.x = next_x

                    elif self.enemy_type == 'red':

                        if block_in_front or not has_ground: self.direction *= -1

                        else: self.x = next_x

                else:

                    self.direction *= -1 # Hit side of playfield

                   

        return False # Do not remove



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

        # No points are awarded

        return 0



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

        new_grid = [row for row in self.grid if row.count((0, 0, 0)) > 0]

        lines_cleared = GRID_HEIGHT - len(new_grid)

        for _ in range(lines_cleared):

            new_grid.insert(0, [(0, 0, 0) for _ in range(GRID_WIDTH)])

        self.grid = new_grid

        return lines_cleared



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

                self.sounds['stomp'] = pygame.mixer.Sound('sounds/stomp.wav')

            except pygame.error as e: print(f"Warning: Could not load 'stomp.wav': {e}")

           

            pygame.mixer.music.load('sounds/music.mp3') # Pre-load the music

            print("SoundManager initialized.")

        except pygame.error as e:

            print(f"SoundManager Error: {e}. Sounds/music disabled.")

            self.sounds = None



        # Music playlist and end event

        self.music_playlist = ['sounds/music.mp3']

        self.current_song_index = 0

        self.MUSIC_END_EVENT = pygame.USEREVENT + 1

        pygame.mixer.music.set_endevent(self.MUSIC_END_EVENT)

        self.music_on = True

        self.volume = 0.3  # Start at 30% volume

        if self.sounds:

            self.set_volume(self.volume)  # Apply the initial volume



    def play(self, sound_name):

        if self.sounds and sound_name in self.sounds:

            self.sounds[sound_name].play()



    def play_music(self):

        if self.sounds and self.music_on:

            try:

                pygame.mixer.music.play(loops=-1, fade_ms=2000)

            except pygame.error as e:

                print(f"Could not load or play music: {self.music_playlist[self.current_song_index]}. Error: {e}")

                self.music_on = False # Stop trying to play if it fails



    def toggle_music(self):

        self.music_on = not self.music_on

        if self.music_on:

            pygame.mixer.music.play(fade_ms=500)

        else:

            pygame.mixer.music.fadeout(500)

        return self.music_on



    def play_next_song(self):

        if not self.sounds: return

        # Loop the same song

        self.current_song_index = 0

        self.play_music()



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

            Tetris.SPINY_FRAMES = sprite_manager.get_animation_frames('spiny')



            # Fallback for red turtle if sprites are missing

            if not Tetris.RED_TURTLE_FRAMES: Tetris.RED_TURTLE_FRAMES = Tetris.TURTLE_FRAMES

            # Fallback for spiny

            if not Tetris.SPINY_FRAMES: Tetris.SPINY_FRAMES = Tetris.TURTLE_FRAMES



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

        self.music_button_rect = None

        self.hold_button_rect = None

        self.new_game_button_rect = None

        self.fullscreen = False

        self.minimize_button_rect = None

        self.pause_button_rect = None

        self.volume_slider_rect = None

        self.volume_knob_rect = None

        self.dragging_volume = False

        self.is_losing_life = False # Flag for flashing lives UI

        self.game_state = 'START_SCREEN' # 'START_SCREEN', 'PLAYING', 'NAME_ENTRY', 'GAME_OVER'



        # Store these for toggling fullscreen

        self.screen_width = WINDOW_WIDTH

        self.screen_height = WINDOW_HEIGHT



        # --- Dynamic Scaling Setup ---

        # The game is rendered to this surface, which is then scaled to the display

        self.game_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)

        self.scaled_surface = self.game_surface # To cache the scaled surface



        self.toggle_fullscreen() # Start in fullscreen

        # --- End Dynamic Scaling ---



        # For start screen animation

        self.start_screen_turtle = Turtle() if Tetris.TURTLE_FRAMES else None

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



    def check_if_high_score(self):

        """Checks if the current score is high enough for the leaderboard."""

        return self.score > self.high_scores[-1]["score"]



    def reset_game(self):

        # This sets up the variables for a new game, but doesn't change the state itself

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

        self.lives = 5

        self.turtles_stomped = 0

        # Timers and controls

        self.fall_timer = 0

        self.lock_timer = 0

        self.das_timer = 0

        self.das_direction = 0

        self.key_down_held = False

        # Turtle state

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

        self.grid.lock_piece(self.current_piece)

        self.sound_manager.play('lock')

        lines_cleared = self.grid.clear_lines()



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

            self.combo += 1

            # Scoring: base points + level bonus + combo bonus

            base_points = [0, 100, 300, 500, 800][lines_cleared]

            self.score += (base_points * self.level) + (self.combo * 50 * self.level)

            # Check for defeated spinies on cleared lines

            cleared_y_coords = [y for y, row in enumerate(self.grid.grid) if all(c != (0,0,0) for c in row)]

            for turtle in self.turtles[:]:

                if turtle.enemy_type == 'spiny' and int(turtle.y) in cleared_y_coords:

                    self.turtles.remove(turtle)

                    self.score += 1000 # Bonus for clearing a spiny

            self.total_lines_cleared += lines_cleared

            self.level = self.total_lines_cleared // 10 + 1

        else:

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



    def handle_input(self, delta_time):

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                return False

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE: return False

               

                if self.game_state == 'START_SCREEN':

                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:

                        self.game_state = 'PLAYING'

                        self.sound_manager.play_music()

                    continue



                if self.game_state == 'GAME_OVER':

                    if event.key == pygame.K_r: self.reset_game() # Only check for keyboard reset here

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

                        self.game_state = 'PLAYING'

                        self.sound_manager.play_music()

                continue

            if self.game_state == 'GAME_OVER':

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                    scaled_pos = self._get_scaled_mouse_pos(event.pos)

                    if self.new_game_button_rect and self.new_game_button_rect