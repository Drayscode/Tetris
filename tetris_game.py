# tetris_game.py
# Retro arcade-style Tetris with:
# - Framed classic Tetris UI
# - GAME and SUMMARY tabs
# - Persistent high scores
# - Statistics panel on the Summary tab
# - Next-piece preview
# - Level-scaled gravity
# - Ghost placement preview and guide lines
# - Hard drop with glow trail
# - Tetris line-clear animation and popup
#
# Controls:
# R       Rotate clockwise
# A       Move left
# D       Move right
# S       Soft drop
# Space   Hard drop
# Tab     Switch GAME / SUMMARY tabs
# W       Restart after game over
# Esc     Pause
# P       Quit

import json
import math
import os
import random
import sys
import pygame


# -------------------------
# Window and layout settings
# -------------------------

CELL_SIZE = 24

BOARD_WIDTH = 10
BOARD_HEIGHT = 20

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 640
FPS = 60

# Central playfield location.
BOARD_X = 280
BOARD_Y = 105
BOARD_PIXEL_WIDTH = BOARD_WIDTH * CELL_SIZE
BOARD_PIXEL_HEIGHT = BOARD_HEIGHT * CELL_SIZE

PLAYFIELD_RECT = pygame.Rect(
    BOARD_X,
    BOARD_Y,
    BOARD_PIXEL_WIDTH,
    BOARD_PIXEL_HEIGHT
)

# Main GAME-tab panels.
HEADER_RECT = pygame.Rect(25, 35, 495, 55)
NEXT_RECT = pygame.Rect(550, 215, 225, 150)
CONTROLS_RECT = pygame.Rect(550, 535, 225, 80)

# Clickable tab controls.
GAME_TAB_RECT = pygame.Rect(25, 4, 108, 25)
SUMMARY_TAB_RECT = pygame.Rect(138, 4, 132, 25)

# SUMMARY-tab panels.
SUMMARY_SCORE_RECT = pygame.Rect(35, 115, 320, 210)
SUMMARY_STATISTICS_RECT = pygame.Rect(35, 350, 320, 255)
SUMMARY_LEADERBOARD_RECT = pygame.Rect(385, 115, 380, 490)

# Gravity timing.
NORMAL_FALL_DELAY = 650
SOFT_DROP_DELAY = 60
MIN_FALL_DELAY = 16

# Animation durations.
LINE_CLEAR_ANIMATION_MS = 280
TETRIS_POPUP_DURATION_MS = 950
HARD_DROP_GLOW_DURATION_MS = 180

# Ghost-piece settings.
GHOST_BLOCK_ALPHA = 70
GUIDE_LINE_ALPHA = 150

# Local leaderboard storage.
HIGH_SCORE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tetris_high_scores.json"
)
MAX_HIGH_SCORES = 10


# ----------------
# Retro color palette
# ----------------

BACKGROUND_COLOR = (18, 27, 75)
PANEL_BACKGROUND_COLOR = (25, 40, 105)
PANEL_INNER_COLOR = (15, 25, 68)
PLAYFIELD_COLOR = (8, 18, 54)
GRID_COLOR = (40, 62, 135)

WHITE = (245, 247, 255)
LIGHT_BLUE = (125, 195, 255)
DARK_BLUE = (8, 14, 45)
YELLOW = (255, 226, 65)
RED = (235, 72, 76)
BLUE = (70, 130, 255)
CYAN = (75, 220, 240)
PURPLE = (183, 95, 225)
ORANGE = (255, 155, 60)
GREEN = (90, 210, 115)

GAME_OVER_OVERLAY = (0, 0, 0, 175)

COLORS = {
    "I": CYAN,
    "O": YELLOW,
    "T": PURPLE,
    "S": GREEN,
    "Z": RED,
    "J": BLUE,
    "L": ORANGE
}

CONFETTI_COLORS = [
    RED,
    YELLOW,
    CYAN,
    BLUE,
    PURPLE,
    WHITE
]


# ------------------------
# Tetris shape definitions
# ------------------------

SHAPES = {
    "I": [
        (0, 1),
        (1, 1),
        (2, 1),
        (3, 1)
    ],
    "O": [
        (0, 0),
        (1, 0),
        (0, 1),
        (1, 1)
    ],
    "T": [
        (1, 0),
        (0, 1),
        (1, 1),
        (2, 1)
    ],
    "S": [
        (1, 0),
        (2, 0),
        (0, 1),
        (1, 1)
    ],
    "Z": [
        (0, 0),
        (1, 0),
        (1, 1),
        (2, 1)
    ],
    "J": [
        (0, 0),
        (0, 1),
        (1, 1),
        (2, 1)
    ],
    "L": [
        (2, 0),
        (0, 1),
        (1, 1),
        (2, 1)
    ]
}


class Piece:
    """
    Represents a falling Tetris piece.
    """

    def __init__(self, piece_type):
        self.piece_type = piece_type
        self.blocks = list(SHAPES[piece_type])
        self.color = COLORS[piece_type]
        self.x = BOARD_WIDTH // 2 - 2
        self.y = 0

    def rotated_blocks(self):
        """
        Return blocks rotated clockwise.
        """
        if self.piece_type == "O":
            return list(self.blocks)

        rotated = [(-block_y, block_x) for block_x, block_y in self.blocks]

        min_x = min(block_x for block_x, block_y in rotated)
        min_y = min(block_y for block_x, block_y in rotated)

        return [
            (block_x - min_x, block_y - min_y)
            for block_x, block_y in rotated
        ]


# --------------------------
# Game state helper functions
# --------------------------

def create_empty_board():
    """
    Create an empty game board.
    """
    return [
        [None for _ in range(BOARD_WIDTH)]
        for _ in range(BOARD_HEIGHT)
    ]


def create_random_piece():
    """
    Return a randomly selected piece.
    """
    return Piece(random.choice(list(SHAPES.keys())))


def create_piece_statistics():
    """
    Create the per-piece statistics dictionary.
    """
    return {
        piece_type: 0
        for piece_type in SHAPES
    }


def get_fall_delay(level, soft_drop=False):
    """
    Return gravity delay scaled by level.

    Lower delay means faster falling.
    """
    base_delay = SOFT_DROP_DELAY if soft_drop else NORMAL_FALL_DELAY
    safe_level = max(level, 1)

    return max(MIN_FALL_DELAY, base_delay / safe_level)


def valid_position(board, piece, offset_x=0, offset_y=0, blocks=None):
    """
    Check whether a piece can safely occupy a requested position.
    """
    if blocks is None:
        blocks = piece.blocks

    for block_x, block_y in blocks:
        board_x = piece.x + block_x + offset_x
        board_y = piece.y + block_y + offset_y

        if board_x < 0 or board_x >= BOARD_WIDTH:
            return False

        if board_y >= BOARD_HEIGHT:
            return False

        if board_y >= 0 and board[board_y][board_x] is not None:
            return False

    return True


def lock_piece(board, piece):
    """
    Permanently place a piece on the board.
    """
    for block_x, block_y in piece.blocks:
        board_x = piece.x + block_x
        board_y = piece.y + block_y

        if board_y >= 0:
            board[board_y][board_x] = piece.color


def get_drop_distance(board, piece):
    """
    Return the number of rows the piece can drop before landing.
    """
    distance = 0

    while valid_position(board, piece, offset_y=distance + 1):
        distance += 1

    return distance


def find_completed_rows(board):
    """
    Return a list of fully occupied row indexes.
    """
    return [
        row_index
        for row_index, row in enumerate(board)
        if all(cell is not None for cell in row)
    ]


def clear_completed_lines(board, rows_to_clear=None):
    """
    Remove selected completed rows and return the number removed.
    """
    if rows_to_clear is None:
        rows_to_clear = find_completed_rows(board)

    rows_to_clear = set(rows_to_clear)

    if not rows_to_clear:
        return 0

    remaining_rows = [
        row
        for row_index, row in enumerate(board)
        if row_index not in rows_to_clear
    ]

    cleared_lines = len(rows_to_clear)

    while len(remaining_rows) < BOARD_HEIGHT:
        remaining_rows.insert(
            0,
            [None for _ in range(BOARD_WIDTH)]
        )

    for row_index in range(BOARD_HEIGHT):
        board[row_index] = remaining_rows[row_index]

    return cleared_lines


def score_for_lines(lines_cleared, level):
    """
    Return Tetris-style score value.
    """
    values = {
        0: 0,
        1: 100,
        2: 300,
        3: 500,
        4: 800
    }

    return values.get(lines_cleared, 0) * level


def reset_game():
    """
    Create a fresh game state.
    """
    board = create_empty_board()
    current_piece = create_random_piece()
    next_piece = create_random_piece()

    score = 0
    lines = 0
    level = 1
    game_over = False
    paused = False
    piece_statistics = create_piece_statistics()

    return (
        board,
        current_piece,
        next_piece,
        score,
        lines,
        level,
        game_over,
        paused,
        piece_statistics
    )


# ---------------------
# High score persistence
# ---------------------

def load_high_scores():
    """
    Load saved high scores from disk.
    """
    try:
        with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as score_file:
            saved_scores = json.load(score_file)

        valid_scores = [
            score
            for score in saved_scores
            if type(score) is int and score >= 0
        ]

        return sorted(valid_scores, reverse=True)[:MAX_HIGH_SCORES]

    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save_high_scores(high_scores):
    """
    Save high scores locally.
    """
    try:
        with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as score_file:
            json.dump(high_scores[:MAX_HIGH_SCORES], score_file)
    except OSError:
        pass


def record_score(high_scores, score):
    """
    Save a completed score and calculate player placement.
    """
    previous_best = high_scores[0] if high_scores else None

    if previous_best is None:
        is_new_high_score = score > 0
    else:
        is_new_high_score = score > previous_best

    updated_scores = sorted(high_scores + [score], reverse=True)
    placement = updated_scores.index(score) + 1

    high_scores[:] = updated_scores[:MAX_HIGH_SCORES]
    save_high_scores(high_scores)

    return placement, is_new_high_score


# ------------------------
# Celebration visual effects
# ------------------------

def create_confetti():
    """
    Create confetti particles for a new high score.
    """
    particles = []

    for _ in range(180):
        particles.append({
            "x": random.uniform(0, WINDOW_WIDTH),
            "y": random.uniform(-100, WINDOW_HEIGHT * 0.35),
            "vx": random.uniform(-140, 140),
            "vy": random.uniform(60, 250),
            "size": random.randint(5, 10),
            "color": random.choice(CONFETTI_COLORS),
            "life": random.uniform(2.5, 4.5)
        })

    return particles


def update_confetti(particles, delta_seconds):
    """
    Update confetti particle positions.
    """
    active_particles = []

    for particle in particles:
        particle["x"] += particle["vx"] * delta_seconds
        particle["y"] += particle["vy"] * delta_seconds
        particle["vy"] += 420 * delta_seconds
        particle["life"] -= delta_seconds

        if particle["life"] > 0 and particle["y"] < WINDOW_HEIGHT + 30:
            active_particles.append(particle)

    return active_particles


def draw_confetti(surface, particles):
    """
    Draw confetti particles.
    """
    for particle in particles:
        rect = pygame.Rect(
            int(particle["x"]),
            int(particle["y"]),
            particle["size"],
            particle["size"] + 4
        )

        pygame.draw.rect(
            surface,
            particle["color"],
            rect
        )


def create_hard_drop_effect(piece, start_y, end_y, current_time):
    """
    Create visual data for a brief hard-drop glow trail.
    """
    return {
        "piece_x": piece.x,
        "start_y": start_y,
        "end_y": end_y,
        "blocks": list(piece.blocks),
        "color": piece.color,
        "end_time": current_time + HARD_DROP_GLOW_DURATION_MS
    }


# -----------------------
# Retro UI drawing helpers
# -----------------------

def draw_retro_box(surface, rect, title, fonts, title_color=WHITE):
    """
    Draw a double-bordered retro arcade panel.
    """
    pygame.draw.rect(surface, DARK_BLUE, rect)
    pygame.draw.rect(surface, LIGHT_BLUE, rect, width=3)

    inner_rect = rect.inflate(-8, -8)
    pygame.draw.rect(surface, PANEL_INNER_COLOR, inner_rect)
    pygame.draw.rect(surface, WHITE, inner_rect, width=1)

    if title:
        title_surface = fonts["label"].render(title, True, title_color)
        title_rect = title_surface.get_rect(
            center=(rect.centerx, rect.top)
        )

        title_background = title_rect.inflate(12, 4)

        pygame.draw.rect(
            surface,
            BACKGROUND_COLOR,
            title_background
        )

        surface.blit(title_surface, title_rect)


def draw_centered_text(surface, text, font, color, center):
    """
    Draw text centered at a position.
    """
    text_surface = font.render(str(text), True, color)
    text_rect = text_surface.get_rect(center=center)
    surface.blit(text_surface, text_rect)


def draw_right_aligned_text(surface, text, font, color, right_x, y):
    """
    Draw text right-aligned at a position.
    """
    text_surface = font.render(str(text), True, color)
    text_rect = text_surface.get_rect(topright=(right_x, y))
    surface.blit(text_surface, text_rect)


def draw_preview_block(surface, pixel_x, pixel_y, size, color):
    """
    Draw a bold, classic arcade block using pixel coordinates.
    """
    block_rect = pygame.Rect(
        pixel_x,
        pixel_y,
        size,
        size
    )

    pygame.draw.rect(surface, color, block_rect)

    highlight = tuple(min(channel + 75, 255) for channel in color)

    pygame.draw.line(
        surface,
        highlight,
        (pixel_x + 2, pixel_y + 2),
        (pixel_x + size - 3, pixel_y + 2),
        width=2
    )

    pygame.draw.line(
        surface,
        highlight,
        (pixel_x + 2, pixel_y + 2),
        (pixel_x + 2, pixel_y + size - 3),
        width=2
    )

    pygame.draw.rect(
        surface,
        DARK_BLUE,
        block_rect,
        width=2
    )


def draw_block(surface, column, row, color):
    """
    Draw one board block at a grid coordinate.
    """
    pixel_x = BOARD_X + column * CELL_SIZE
    pixel_y = BOARD_Y + row * CELL_SIZE

    draw_preview_block(
        surface,
        pixel_x + 1,
        pixel_y + 1,
        CELL_SIZE - 2,
        color
    )


def draw_ghost_block(surface, column, row, color):
    """
    Draw a transparent predicted landing block.
    """
    if row < 0:
        return

    ghost_surface = pygame.Surface(
        (CELL_SIZE, CELL_SIZE),
        pygame.SRCALPHA
    )

    rect = pygame.Rect(
        2,
        2,
        CELL_SIZE - 4,
        CELL_SIZE - 4
    )

    pygame.draw.rect(
        ghost_surface,
        color + (GHOST_BLOCK_ALPHA,),
        rect
    )

    bright_color = tuple(min(channel + 70, 255) for channel in color)

    pygame.draw.rect(
        ghost_surface,
        bright_color + (200,),
        rect,
        width=2
    )

    surface.blit(
        ghost_surface,
        (
            BOARD_X + column * CELL_SIZE,
            BOARD_Y + row * CELL_SIZE
        )
    )


def draw_dashed_vertical_line(surface, x, start_y, end_y, color):
    """
    Draw a glowing dashed vertical placement guide.
    """
    if end_y < start_y:
        return

    guide_surface = pygame.Surface(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.SRCALPHA
    )

    dash_height = 7
    dash_gap = 7

    for y in range(int(start_y), int(end_y), dash_height + dash_gap):
        pygame.draw.line(
            guide_surface,
            color + (GUIDE_LINE_ALPHA,),
            (x, y),
            (x, min(y + dash_height, end_y)),
            width=2
        )

    surface.blit(guide_surface, (0, 0))


def draw_placement_preview(surface, board, piece):
    """
    Draw guide lines and the transparent ghost landing piece.
    """
    if piece is None:
        return

    drop_distance = get_drop_distance(board, piece)
    landing_y = piece.y + drop_distance

    occupied_columns = [
        piece.x + block_x
        for block_x, block_y in piece.blocks
    ]

    left_column = min(occupied_columns)
    right_column = max(occupied_columns)

    start_y = BOARD_Y + min(
        piece.y + block_y
        for block_x, block_y in piece.blocks
    ) * CELL_SIZE

    end_y = BOARD_Y + (
        max(
            landing_y + block_y
            for block_x, block_y in piece.blocks
        ) + 1
    ) * CELL_SIZE

    guide_color = tuple(
        min(channel + 55, 255)
        for channel in piece.color
    )

    draw_dashed_vertical_line(
        surface,
        BOARD_X + left_column * CELL_SIZE + CELL_SIZE // 2,
        start_y,
        end_y,
        guide_color
    )

    draw_dashed_vertical_line(
        surface,
        BOARD_X + right_column * CELL_SIZE + CELL_SIZE // 2,
        start_y,
        end_y,
        guide_color
    )

    for block_x, block_y in piece.blocks:
        draw_ghost_block(
            surface,
            piece.x + block_x,
            landing_y + block_y,
            piece.color
        )


def draw_hard_drop_effect(surface, hard_drop_effect):
    """
    Draw glowing hard-drop motion trails.
    """
    if hard_drop_effect is None:
        return

    current_time = pygame.time.get_ticks()
    time_remaining = hard_drop_effect["end_time"] - current_time

    if time_remaining <= 0:
        return

    intensity = time_remaining / HARD_DROP_GLOW_DURATION_MS
    color = hard_drop_effect["color"]
    bright_color = tuple(min(channel + 90, 255) for channel in color)

    trail_surface = pygame.Surface(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.SRCALPHA
    )

    for block_x, block_y in hard_drop_effect["blocks"]:
        column = hard_drop_effect["piece_x"] + block_x

        start_row = hard_drop_effect["start_y"] + block_y
        end_row = hard_drop_effect["end_y"] + block_y

        top_pixel = BOARD_Y + start_row * CELL_SIZE + 3
        bottom_pixel = BOARD_Y + (end_row + 1) * CELL_SIZE - 3

        trail_rect = pygame.Rect(
            BOARD_X + column * CELL_SIZE + 7,
            top_pixel,
            CELL_SIZE - 14,
            max(CELL_SIZE - 6, bottom_pixel - top_pixel)
        )

        pygame.draw.rect(
            trail_surface,
            color + (int(115 * intensity),),
            trail_rect,
            border_radius=5
        )

        landing_rect = pygame.Rect(
            BOARD_X + column * CELL_SIZE + 1,
            BOARD_Y + end_row * CELL_SIZE + 1,
            CELL_SIZE - 2,
            CELL_SIZE - 2
        )

        pygame.draw.rect(
            trail_surface,
            bright_color + (int(240 * intensity),),
            landing_rect,
            width=3
        )

    surface.blit(trail_surface, (0, 0))


def draw_glowing_row(surface, row, glow_strength):
    """
    Draw bright glow over a completed row before it disappears.
    """
    pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() / 35)
    glow_alpha = int((120 + 120 * pulse) * glow_strength)

    glow_surface = pygame.Surface(
        (BOARD_PIXEL_WIDTH, CELL_SIZE),
        pygame.SRCALPHA
    )

    glow_surface.fill((255, 245, 100, glow_alpha))

    surface.blit(
        glow_surface,
        (BOARD_X, BOARD_Y + row * CELL_SIZE)
    )

    for column in range(BOARD_WIDTH):
        rect = pygame.Rect(
            BOARD_X + column * CELL_SIZE + 1,
            BOARD_Y + row * CELL_SIZE + 1,
            CELL_SIZE - 2,
            CELL_SIZE - 2
        )

        pygame.draw.rect(
            surface,
            WHITE,
            rect,
            width=2
        )


# -------------------------
# Main board and UI drawing
# -------------------------

def draw_playfield(surface, board, glowing_rows=None, glow_strength=1.0):
    """
    Draw the framed central playfield and settled blocks.
    """
    if glowing_rows is None:
        glowing_rows = []

    frame_rect = PLAYFIELD_RECT.inflate(14, 14)

    pygame.draw.rect(surface, DARK_BLUE, frame_rect)
    pygame.draw.rect(surface, LIGHT_BLUE, frame_rect, width=4)

    pygame.draw.rect(surface, WHITE, PLAYFIELD_RECT, width=1)
    pygame.draw.rect(surface, PLAYFIELD_COLOR, PLAYFIELD_RECT)

    for row in range(BOARD_HEIGHT):
        for column in range(BOARD_WIDTH):
            cell_rect = pygame.Rect(
                BOARD_X + column * CELL_SIZE,
                BOARD_Y + row * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE
            )

            pygame.draw.rect(
                surface,
                GRID_COLOR,
                cell_rect,
                width=1
            )

    for row in range(BOARD_HEIGHT):
        for column in range(BOARD_WIDTH):
            color = board[row][column]

            if color is not None:
                draw_block(surface, column, row, color)

    for row in glowing_rows:
        draw_glowing_row(surface, row, glow_strength)


def draw_piece(surface, piece):
    """
    Draw the active falling piece.
    """
    if piece is None:
        return

    for block_x, block_y in piece.blocks:
        board_x = piece.x + block_x
        board_y = piece.y + block_y

        if board_y >= 0:
            draw_block(surface, board_x, board_y, piece.color)


def draw_tabs(surface, active_tab, fonts):
    """
    Draw clickable GAME and SUMMARY tabs.
    """
    tabs = [
        ("GAME", GAME_TAB_RECT, "game"),
        ("SUMMARY", SUMMARY_TAB_RECT, "summary")
    ]

    for label, rect, tab_name in tabs:
        is_active = active_tab == tab_name

        background = LIGHT_BLUE if is_active else PANEL_INNER_COLOR
        text_color = DARK_BLUE if is_active else WHITE
        border_color = WHITE if is_active else LIGHT_BLUE

        pygame.draw.rect(surface, background, rect)
        pygame.draw.rect(surface, border_color, rect, width=2)

        draw_centered_text(
            surface,
            label,
            fonts["tiny"],
            text_color,
            rect.center
        )


def draw_header(surface, lines, fonts):
    """
    Draw the minimal game header.
    """
    draw_retro_box(surface, HEADER_RECT, "", fonts)

    draw_centered_text(
        surface,
        "A-TYPE",
        fonts["header"],
        WHITE,
        (HEADER_RECT.left + 120, HEADER_RECT.centery)
    )

    draw_centered_text(
        surface,
        "LINES",
        fonts["label"],
        LIGHT_BLUE,
        (HEADER_RECT.right - 112, HEADER_RECT.top + 16)
    )

    draw_centered_text(
        surface,
        f"{lines:03d}",
        fonts["number_small"],
        WHITE,
        (HEADER_RECT.right - 112, HEADER_RECT.top + 37)
    )


def draw_mini_piece(surface, piece_type, x, y, cell_size=10):
    """
    Draw a mini tetromino icon.
    """
    shape = SHAPES[piece_type]
    color = COLORS[piece_type]

    max_x = max(block_x for block_x, block_y in shape)
    max_y = max(block_y for block_x, block_y in shape)

    shape_width = (max_x + 1) * cell_size
    shape_height = (max_y + 1) * cell_size

    start_x = x - shape_width // 2
    start_y = y - shape_height // 2

    for block_x, block_y in shape:
        draw_preview_block(
            surface,
            start_x + block_x * cell_size,
            start_y + block_y * cell_size,
            cell_size,
            color
        )


def draw_next_piece_panel(surface, next_piece, fonts):
    """
    Draw the NEXT panel and upcoming piece.
    """
    draw_retro_box(surface, NEXT_RECT, "NEXT", fonts)

    max_x = max(block_x for block_x, block_y in next_piece.blocks)
    max_y = max(block_y for block_x, block_y in next_piece.blocks)

    preview_cell_size = 22
    shape_width = (max_x + 1) * preview_cell_size
    shape_height = (max_y + 1) * preview_cell_size

    start_x = NEXT_RECT.centerx - shape_width // 2
    start_y = NEXT_RECT.centery - shape_height // 2 + 12

    for block_x, block_y in next_piece.blocks:
        draw_preview_block(
            surface,
            start_x + block_x * preview_cell_size,
            start_y + block_y * preview_cell_size,
            preview_cell_size,
            next_piece.color
        )


def draw_controls_panel(surface, fonts):
    """
    Draw controls on the main GAME tab.
    """
    draw_retro_box(surface, CONTROLS_RECT, "CONTROLS", fonts)

    controls = [
        "R ROTATE     A/D MOVE",
        "S SOFT DROP  SPACE DROP",
        "TAB SUMMARY  ESC PAUSE"
    ]

    y = CONTROLS_RECT.top + 22

    for instruction in controls:
        draw_centered_text(
            surface,
            instruction,
            fonts["tiny"],
            WHITE,
            (CONTROLS_RECT.centerx, y)
        )

        y += 19


# ---------------------
# Summary tab rendering
# ---------------------

def draw_summary_score_panel(surface, score, lines, level, high_scores, fonts):
    """
    Draw current score, top score, lines, and level.
    """
    draw_retro_box(
        surface,
        SUMMARY_SCORE_RECT,
        "GAME SUMMARY",
        fonts
    )

    top_score = high_scores[0] if high_scores else 0

    summary_items = [
        ("TOP SCORE", f"{top_score:06d}", LIGHT_BLUE),
        ("CURRENT SCORE", f"{score:06d}", YELLOW),
        ("LINES CLEARED", f"{lines:03d}", WHITE),
        ("LEVEL", f"{level:02d}", YELLOW)
    ]

    y_position = SUMMARY_SCORE_RECT.top + 35

    for label, value, value_color in summary_items:
        draw_centered_text(
            surface,
            label,
            fonts["tiny"],
            LIGHT_BLUE,
            (SUMMARY_SCORE_RECT.centerx, y_position)
        )

        draw_centered_text(
            surface,
            value,
            fonts["number_small"],
            value_color,
            (SUMMARY_SCORE_RECT.centerx, y_position + 18)
        )

        y_position += 42


def draw_summary_statistics_panel(surface, piece_statistics, fonts):
    """
    Draw compact piece statistics on the Summary tab.
    """
    draw_retro_box(
        surface,
        SUMMARY_STATISTICS_RECT,
        "STATISTICS",
        fonts
    )

    row_y = SUMMARY_STATISTICS_RECT.top + 42

    for piece_type in ["I", "O", "T", "S", "Z", "J", "L"]:
        draw_mini_piece(
            surface,
            piece_type,
            SUMMARY_STATISTICS_RECT.left + 80,
            row_y,
            cell_size=8
        )

        draw_right_aligned_text(
            surface,
            f"{piece_statistics[piece_type]:03d}",
            fonts["number_small"],
            WHITE,
            SUMMARY_STATISTICS_RECT.right - 35,
            row_y - 10
        )

        row_y += 29


def draw_summary_leaderboard(surface, high_scores, fonts):
    """
    Draw saved top scores.
    """
    draw_retro_box(
        surface,
        SUMMARY_LEADERBOARD_RECT,
        "TOP SCORES",
        fonts
    )

    if not high_scores:
        draw_centered_text(
            surface,
            "NO SCORES YET",
            fonts["label"],
            LIGHT_BLUE,
            SUMMARY_LEADERBOARD_RECT.center
        )
        return

    y_position = SUMMARY_LEADERBOARD_RECT.top + 45

    for rank, saved_score in enumerate(
        high_scores[:MAX_HIGH_SCORES],
        start=1
    ):
        rank_color = YELLOW if rank == 1 else LIGHT_BLUE
        score_color = YELLOW if rank == 1 else WHITE

        draw_right_aligned_text(
            surface,
            f"{rank:02d}",
            fonts["number_small"],
            rank_color,
            SUMMARY_LEADERBOARD_RECT.left + 75,
            y_position
        )

        draw_right_aligned_text(
            surface,
            f"{saved_score:06d}",
            fonts["number_small"],
            score_color,
            SUMMARY_LEADERBOARD_RECT.right - 52,
            y_position
        )

        y_position += 34


def draw_summary_screen(
    surface,
    score,
    lines,
    level,
    high_scores,
    piece_statistics,
    fonts
):
    """
    Draw the full Summary tab.
    """
    draw_centered_text(
        surface,
        "PLAYER SUMMARY",
        fonts["header"],
        WHITE,
        (WINDOW_WIDTH // 2, 67)
    )

    draw_summary_score_panel(
        surface,
        score,
        lines,
        level,
        high_scores,
        fonts
    )

    draw_summary_statistics_panel(
        surface,
        piece_statistics,
        fonts
    )

    draw_summary_leaderboard(
        surface,
        high_scores,
        fonts
    )

    draw_centered_text(
        surface,
        "PRESS TAB TO RETURN TO GAME",
        fonts["tiny"],
        LIGHT_BLUE,
        (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 20)
    )


# --------------------
# Overlays and pop-ups
# --------------------

def draw_tetris_popup(surface, popup_end_time, arcade_font):
    """
    Draw a bold flashing TETRIS! popup.
    """
    current_time = pygame.time.get_ticks()
    time_remaining = popup_end_time - current_time

    if time_remaining <= 0:
        return

    progress = 1 - (time_remaining / TETRIS_POPUP_DURATION_MS)
    scale = 0.85 + 0.45 * math.sin(progress * math.pi)

    color = YELLOW if (current_time // 90) % 2 == 0 else RED

    shadow_text = arcade_font.render("TETRIS!", True, DARK_BLUE)
    outline_text = arcade_font.render("TETRIS!", True, WHITE)
    main_text = arcade_font.render("TETRIS!", True, color)

    shadow_text = pygame.transform.rotozoom(shadow_text, 0, scale)
    outline_text = pygame.transform.rotozoom(outline_text, 0, scale)
    main_text = pygame.transform.rotozoom(main_text, 0, scale)

    center_x = PLAYFIELD_RECT.centerx
    center_y = PLAYFIELD_RECT.centery - 35

    shadow_rect = shadow_text.get_rect(
        center=(center_x + 7, center_y + 8)
    )
    surface.blit(shadow_text, shadow_rect)

    for offset_x, offset_y in [
        (-3, 0),
        (3, 0),
        (0, -3),
        (0, 3),
        (-2, -2),
        (2, 2),
        (-2, 2),
        (2, -2)
    ]:
        outline_rect = outline_text.get_rect(
            center=(center_x + offset_x, center_y + offset_y)
        )
        surface.blit(outline_text, outline_rect)

    main_rect = main_text.get_rect(center=(center_x, center_y))
    surface.blit(main_text, main_rect)


def draw_game_over(
    surface,
    score,
    placement,
    is_new_high_score,
    large_font,
    body_font
):
    """
    Draw the game-over overlay.
    """
    overlay = pygame.Surface(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.SRCALPHA
    )
    overlay.fill(GAME_OVER_OVERLAY)
    surface.blit(overlay, (0, 0))

    center_x = PLAYFIELD_RECT.centerx
    center_y = PLAYFIELD_RECT.centery

    title = large_font.render("GAME OVER", True, WHITE)
    title_rect = title.get_rect(center=(center_x, center_y - 70))
    surface.blit(title, title_rect)

    score_text = body_font.render(
        f"SCORE {score:06d}",
        True,
        WHITE
    )
    score_rect = score_text.get_rect(center=(center_x, center_y - 25))
    surface.blit(score_text, score_rect)

    placement_text = body_font.render(
        f"PLACEMENT #{placement}",
        True,
        WHITE
    )
    placement_rect = placement_text.get_rect(
        center=(center_x, center_y + 8)
    )
    surface.blit(placement_text, placement_rect)

    if is_new_high_score:
        high_score_text = body_font.render(
            "NEW TOP SCORE!",
            True,
            YELLOW
        )
        high_score_rect = high_score_text.get_rect(
            center=(center_x, center_y + 42)
        )
        surface.blit(high_score_text, high_score_rect)

        restart_y = center_y + 80
    else:
        restart_y = center_y + 50

    restart_text = body_font.render(
        "PRESS W TO PLAY AGAIN",
        True,
        WHITE
    )
    restart_rect = restart_text.get_rect(
        center=(center_x, restart_y)
    )
    surface.blit(restart_text, restart_rect)


def draw_pause_screen(surface, large_font, body_font):
    """
    Draw the paused-game overlay.
    """
    overlay = pygame.Surface(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.SRCALPHA
    )
    overlay.fill((0, 0, 0, 170))
    surface.blit(overlay, (0, 0))

    title = large_font.render("PAUSED", True, WHITE)
    title_rect = title.get_rect(
        center=(PLAYFIELD_RECT.centerx, PLAYFIELD_RECT.centery - 20)
    )
    surface.blit(title, title_rect)

    message = body_font.render(
        "PRESS ESC TO CONTINUE",
        True,
        WHITE
    )
    message_rect = message.get_rect(
        center=(PLAYFIELD_RECT.centerx, PLAYFIELD_RECT.centery + 25)
    )
    surface.blit(message, message_rect)


# ----------------
# Main game loop
# ----------------

def main():
    """
    Initialize Pygame and run the game.
    """
    pygame.init()

    screen = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT)
    )
    pygame.display.set_caption("Retro Arcade Tetris")

    clock = pygame.time.Clock()

    fonts = {
        "header": pygame.font.SysFont(
            "couriernew",
            25,
            bold=True
        ),
        "label": pygame.font.SysFont(
            "couriernew",
            20,
            bold=True
        ),
        "number": pygame.font.SysFont(
            "couriernew",
            24,
            bold=True
        ),
        "number_small": pygame.font.SysFont(
            "couriernew",
            20,
            bold=True
        ),
        "level": pygame.font.SysFont(
            "couriernew",
            48,
            bold=True
        ),
        "tiny": pygame.font.SysFont(
            "couriernew",
            12,
            bold=True
        )
    }

    game_over_title_font = pygame.font.SysFont(
        "couriernew",
        38,
        bold=True
    )

    game_over_body_font = pygame.font.SysFont(
        "couriernew",
        19,
        bold=True
    )

    tetris_popup_font = pygame.font.SysFont(
        "arialblack",
        55,
        bold=True
    )

    (
        board,
        current_piece,
        next_piece,
        score,
        lines,
        level,
        game_over,
        paused,
        piece_statistics
    ) = reset_game()

    high_scores = load_high_scores()

    placement = None
    is_new_high_score = False
    confetti_particles = []

    clearing_rows = []
    line_clear_end_time = 0

    tetris_popup_end_time = 0
    hard_drop_effect = None

    # The game begins on the GAME tab.
    active_tab = "game"

    last_fall_time = pygame.time.get_ticks()
    running = True

    while running:
        current_time = pygame.time.get_ticks()
        line_clear_active = bool(clearing_rows)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not game_over:
                    mouse_position = event.pos

                    if GAME_TAB_RECT.collidepoint(mouse_position):
                        active_tab = "game"
                        last_fall_time = pygame.time.get_ticks()

                    elif SUMMARY_TAB_RECT.collidepoint(mouse_position):
                        active_tab = "summary"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    running = False

                # Tab switches between the GAME and SUMMARY views.
                if event.key == pygame.K_TAB and not game_over:
                    if active_tab == "game":
                        active_tab = "summary"
                    else:
                        active_tab = "game"
                        last_fall_time = pygame.time.get_ticks()

                if event.key == pygame.K_ESCAPE and not game_over:
                    paused = not paused

                    if not paused:
                        last_fall_time = pygame.time.get_ticks()

                if game_over and event.key == pygame.K_w:
                    (
                        board,
                        current_piece,
                        next_piece,
                        score,
                        lines,
                        level,
                        game_over,
                        paused,
                        piece_statistics
                    ) = reset_game()

                    placement = None
                    is_new_high_score = False
                    confetti_particles = []

                    clearing_rows = []
                    line_clear_end_time = 0
                    tetris_popup_end_time = 0
                    hard_drop_effect = None
                    active_tab = "game"

                    last_fall_time = pygame.time.get_ticks()

                # Controls work only on the GAME tab.
                if (
                    active_tab == "game"
                    and not game_over
                    and not paused
                    and not line_clear_active
                ):
                    if event.key == pygame.K_a:
                        if valid_position(
                            board,
                            current_piece,
                            offset_x=-1
                        ):
                            current_piece.x -= 1

                    elif event.key == pygame.K_d:
                        if valid_position(
                            board,
                            current_piece,
                            offset_x=1
                        ):
                            current_piece.x += 1

                    elif event.key == pygame.K_r:
                        rotated = current_piece.rotated_blocks()

                        if valid_position(
                            board,
                            current_piece,
                            blocks=rotated
                        ):
                            current_piece.blocks = rotated

                        elif valid_position(
                            board,
                            current_piece,
                            offset_x=1,
                            blocks=rotated
                        ):
                            current_piece.x += 1
                            current_piece.blocks = rotated

                        elif valid_position(
                            board,
                            current_piece,
                            offset_x=-1,
                            blocks=rotated
                        ):
                            current_piece.x -= 1
                            current_piece.blocks = rotated

                    elif event.key == pygame.K_SPACE:
                        hard_drop_start_y = current_piece.y

                        hard_drop_distance = get_drop_distance(
                            board,
                            current_piece
                        )

                        current_piece.y += hard_drop_distance

                        hard_drop_effect = create_hard_drop_effect(
                            current_piece,
                            hard_drop_start_y,
                            current_piece.y,
                            current_time
                        )

                        piece_statistics[
                            current_piece.piece_type
                        ] += 1

                        lock_piece(board, current_piece)
                        current_piece = None

                        clearing_rows = find_completed_rows(board)

                        if clearing_rows:
                            line_clear_end_time = (
                                current_time
                                + LINE_CLEAR_ANIMATION_MS
                            )

                            if len(clearing_rows) == 4:
                                tetris_popup_end_time = (
                                    current_time
                                    + TETRIS_POPUP_DURATION_MS
                                )

                        else:
                            current_piece = next_piece
                            next_piece = create_random_piece()

                            if not valid_position(
                                board,
                                current_piece
                            ):
                                game_over = True

                                (
                                    placement,
                                    is_new_high_score
                                ) = record_score(
                                    high_scores,
                                    score
                                )

                                if is_new_high_score:
                                    confetti_particles = create_confetti()

                        last_fall_time = current_time

        pressed_keys = pygame.key.get_pressed()

        fall_delay = get_fall_delay(
            level,
            soft_drop=pressed_keys[pygame.K_s]
        )

        current_time = pygame.time.get_ticks()

        # Complete line clearing after the glow animation.
        if (
            active_tab == "game"
            and clearing_rows
            and not paused
            and current_time >= line_clear_end_time
        ):
            cleared_lines = clear_completed_lines(
                board,
                clearing_rows
            )

            lines += cleared_lines
            level = 1 + lines // 10
            score += score_for_lines(cleared_lines, level)

            clearing_rows = []

            current_piece = next_piece
            next_piece = create_random_piece()

            if not valid_position(board, current_piece):
                game_over = True

                (
                    placement,
                    is_new_high_score
                ) = record_score(
                    high_scores,
                    score
                )

                if is_new_high_score:
                    confetti_particles = create_confetti()

            last_fall_time = current_time

        # Apply normal gravity only while the GAME tab is open.
        if (
            active_tab == "game"
            and not game_over
            and not paused
            and not clearing_rows
            and current_piece is not None
            and current_time - last_fall_time >= fall_delay
        ):
            if valid_position(
                board,
                current_piece,
                offset_y=1
            ):
                current_piece.y += 1

            else:
                piece_statistics[
                    current_piece.piece_type
                ] += 1

                lock_piece(board, current_piece)
                current_piece = None

                clearing_rows = find_completed_rows(board)

                if clearing_rows:
                    line_clear_end_time = (
                        current_time
                        + LINE_CLEAR_ANIMATION_MS
                    )

                    if len(clearing_rows) == 4:
                        tetris_popup_end_time = (
                            current_time
                            + TETRIS_POPUP_DURATION_MS
                        )

                else:
                    current_piece = next_piece
                    next_piece = create_random_piece()

                    if not valid_position(board, current_piece):
                        game_over = True

                        (
                            placement,
                            is_new_high_score
                        ) = record_score(
                            high_scores,
                            score
                        )

                        if is_new_high_score:
                            confetti_particles = create_confetti()

            last_fall_time = current_time

        delta_seconds = clock.get_time() / 1000.0

        if confetti_particles:
            confetti_particles = update_confetti(
                confetti_particles,
                delta_seconds
            )

        if (
            hard_drop_effect is not None
            and current_time >= hard_drop_effect["end_time"]
        ):
            hard_drop_effect = None

        # -----------------
        # Render game frame
        # -----------------

        screen.fill(BACKGROUND_COLOR)

        draw_tabs(
            screen,
            active_tab,
            fonts
        )

        if active_tab == "game":
            if clearing_rows:
                time_remaining = max(
                    0,
                    line_clear_end_time - pygame.time.get_ticks()
                )

                glow_strength = (
                    time_remaining / LINE_CLEAR_ANIMATION_MS
                )
            else:
                glow_strength = 0

            draw_header(screen, lines, fonts)

            draw_playfield(
                screen,
                board,
                glowing_rows=clearing_rows,
                glow_strength=glow_strength
            )

            if current_piece is not None and not clearing_rows:
                draw_placement_preview(
                    screen,
                    board,
                    current_piece
                )

            draw_hard_drop_effect(
                screen,
                hard_drop_effect
            )

            draw_piece(screen, current_piece)

            draw_next_piece_panel(
                screen,
                next_piece,
                fonts
            )

            draw_controls_panel(
                screen,
                fonts
            )

            draw_tetris_popup(
                screen,
                tetris_popup_end_time,
                tetris_popup_font
            )

        else:
            draw_summary_screen(
                screen,
                score,
                lines,
                level,
                high_scores,
                piece_statistics,
                fonts
            )

        if game_over and active_tab == "game":
            draw_game_over(
                screen,
                score,
                placement,
                is_new_high_score,
                game_over_title_font,
                game_over_body_font
            )

            draw_confetti(
                screen,
                confetti_particles
            )

        if paused and active_tab == "game":
            draw_pause_screen(
                screen,
                game_over_title_font,
                game_over_body_font
            )

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()