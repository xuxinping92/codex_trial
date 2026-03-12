import random
import sys
from dataclasses import dataclass

import pygame


# ----------------------- 游戏配置 -----------------------
CELL_SIZE = 30
GRID_WIDTH = 10
GRID_HEIGHT = 20
PLAYFIELD_WIDTH = GRID_WIDTH * CELL_SIZE
PLAYFIELD_HEIGHT = GRID_HEIGHT * CELL_SIZE
SIDE_PANEL_WIDTH = 220
WINDOW_WIDTH = PLAYFIELD_WIDTH + SIDE_PANEL_WIDTH
WINDOW_HEIGHT = PLAYFIELD_HEIGHT
FPS = 60

FALL_EVENT = pygame.USEREVENT + 1
BASE_FALL_MS = 700
MIN_FALL_MS = 100

BG_COLOR = (20, 20, 28)
GRID_COLOR = (45, 45, 60)
TEXT_COLOR = (230, 230, 240)
GHOST_ALPHA = 70

SHAPES = {
    "I": [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
    ],
    "O": [
        [(1, 0), (2, 0), (1, 1), (2, 1)],
    ],
    "T": [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "S": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
    ],
    "Z": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
    ],
    "J": [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
    "L": [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
}

COLORS = {
    "I": (0, 200, 220),
    "O": (240, 220, 70),
    "T": (170, 100, 230),
    "S": (100, 210, 110),
    "Z": (230, 90, 90),
    "J": (90, 140, 220),
    "L": (240, 150, 70),
}

LINE_SCORES = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}


@dataclass
class Piece:
    shape: str
    rotation: int
    x: int
    y: int

    @property
    def blocks(self):
        return SHAPES[self.shape][self.rotation]

    def cells(self):
        for bx, by in self.blocks:
            yield self.x + bx, self.y + by


class Tetris:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("俄罗斯方块 - Pygame")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("simhei", 24)
        self.small_font = pygame.font.SysFont("simhei", 20)
        self.reset_game()

    def reset_game(self):
        self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.game_over = False

        self.bag = []
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.update_fall_speed()

    def refill_bag(self):
        self.bag = list(SHAPES.keys())
        random.shuffle(self.bag)

    def new_piece(self):
        if not self.bag:
            self.refill_bag()
        shape = self.bag.pop()
        return Piece(shape=shape, rotation=0, x=3, y=0)

    def valid_position(self, piece: Piece):
        for x, y in piece.cells():
            if x < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT:
                return False
            if y >= 0 and self.grid[y][x] is not None:
                return False
        return True

    def lock_piece(self):
        for x, y in self.current_piece.cells():
            if y < 0:
                self.game_over = True
                return
            self.grid[y][x] = self.current_piece.shape

        cleared = self.clear_lines()
        self.lines_cleared += cleared
        self.score += LINE_SCORES[cleared] * self.level
        self.level = 1 + self.lines_cleared // 10
        self.update_fall_speed()

        self.current_piece = self.next_piece
        self.next_piece = self.new_piece()
        if not self.valid_position(self.current_piece):
            self.game_over = True

    def clear_lines(self):
        new_grid = [row for row in self.grid if any(cell is None for cell in row)]
        cleared = GRID_HEIGHT - len(new_grid)
        while len(new_grid) < GRID_HEIGHT:
            new_grid.insert(0, [None for _ in range(GRID_WIDTH)])
        self.grid = new_grid
        return cleared

    def update_fall_speed(self):
        speed = max(MIN_FALL_MS, BASE_FALL_MS - (self.level - 1) * 60)
        pygame.time.set_timer(FALL_EVENT, speed)

    def move(self, dx, dy):
        moved = Piece(
            shape=self.current_piece.shape,
            rotation=self.current_piece.rotation,
            x=self.current_piece.x + dx,
            y=self.current_piece.y + dy,
        )
        if self.valid_position(moved):
            self.current_piece = moved
            return True
        return False

    def rotate(self):
        rotations = len(SHAPES[self.current_piece.shape])
        rotated = Piece(
            shape=self.current_piece.shape,
            rotation=(self.current_piece.rotation + 1) % rotations,
            x=self.current_piece.x,
            y=self.current_piece.y,
        )
        # 简单墙踢逻辑
        for dx in (0, -1, 1, -2, 2):
            kicked = Piece(rotated.shape, rotated.rotation, rotated.x + dx, rotated.y)
            if self.valid_position(kicked):
                self.current_piece = kicked
                return

    def hard_drop(self):
        while self.move(0, 1):
            self.score += 2
        self.lock_piece()

    def soft_drop(self):
        if self.move(0, 1):
            self.score += 1
        else:
            self.lock_piece()

    def ghost_piece(self):
        ghost = Piece(
            self.current_piece.shape,
            self.current_piece.rotation,
            self.current_piece.x,
            self.current_piece.y,
        )
        while True:
            test = Piece(ghost.shape, ghost.rotation, ghost.x, ghost.y + 1)
            if self.valid_position(test):
                ghost = test
            else:
                return ghost

    def draw_block(self, x, y, color, alpha=255):
        if y < 0:
            return
        block = pygame.Surface((CELL_SIZE - 1, CELL_SIZE - 1), pygame.SRCALPHA)
        block.fill((*color, alpha))
        self.screen.blit(block, (x * CELL_SIZE, y * CELL_SIZE))

    def draw_grid(self):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                pygame.draw.rect(
                    self.screen,
                    GRID_COLOR,
                    (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE),
                    1,
                )
                shape = self.grid[y][x]
                if shape:
                    self.draw_block(x, y, COLORS[shape])

        ghost = self.ghost_piece()
        for gx, gy in ghost.cells():
            self.draw_block(gx, gy, COLORS[ghost.shape], alpha=GHOST_ALPHA)

        for px, py in self.current_piece.cells():
            self.draw_block(px, py, COLORS[self.current_piece.shape])

    def draw_next_piece(self):
        panel_x = PLAYFIELD_WIDTH + 20
        panel_y = 120

        title = self.small_font.render("下一个", True, TEXT_COLOR)
        self.screen.blit(title, (panel_x, panel_y - 40))

        for bx, by in SHAPES[self.next_piece.shape][0]:
            x = panel_x + bx * 24
            y = panel_y + by * 24
            pygame.draw.rect(self.screen, COLORS[self.next_piece.shape], (x, y, 22, 22))

    def draw_panel(self):
        panel_x = PLAYFIELD_WIDTH + 20

        score_surf = self.small_font.render(f"分数: {self.score}", True, TEXT_COLOR)
        level_surf = self.small_font.render(f"等级: {self.level}", True, TEXT_COLOR)
        line_surf = self.small_font.render(f"消行: {self.lines_cleared}", True, TEXT_COLOR)

        self.screen.blit(score_surf, (panel_x, 20))
        self.screen.blit(level_surf, (panel_x, 55))
        self.screen.blit(line_surf, (panel_x, 90))

        self.draw_next_piece()

        help_lines = [
            "← → : 左右移动",
            "↑ : 旋转",
            "↓ : 软降",
            "空格 : 硬降",
            "R : 重新开始",
            "ESC : 退出",
        ]
        y = 320
        for line in help_lines:
            surf = pygame.font.SysFont("simhei", 18).render(line, True, (180, 180, 200))
            self.screen.blit(surf, (panel_x, y))
            y += 28

    def draw_game_over(self):
        overlay = pygame.Surface((PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        text1 = self.font.render("游戏结束", True, (255, 120, 120))
        text2 = self.small_font.render("按 R 重新开始", True, TEXT_COLOR)

        self.screen.blit(text1, (PLAYFIELD_WIDTH // 2 - text1.get_width() // 2, 240))
        self.screen.blit(text2, (PLAYFIELD_WIDTH // 2 - text2.get_width() // 2, 280))

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

            if event.key == pygame.K_r:
                self.reset_game()
                return

            if self.game_over:
                return

            if event.key == pygame.K_LEFT:
                self.move(-1, 0)
            elif event.key == pygame.K_RIGHT:
                self.move(1, 0)
            elif event.key == pygame.K_DOWN:
                self.soft_drop()
            elif event.key == pygame.K_UP:
                self.rotate()
            elif event.key == pygame.K_SPACE:
                self.hard_drop()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == FALL_EVENT and not self.game_over:
                    if not self.move(0, 1):
                        self.lock_piece()
                self.handle_input(event)

            self.screen.fill(BG_COLOR)
            self.draw_grid()
            self.draw_panel()
            if self.game_over:
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Tetris().run()
