import math
import random
from dataclasses import dataclass

import pygame

# --- Display / world constants ---
TILE_SIZE = 24
MAP_WIDTH = 50
MAP_HEIGHT = 32
SCREEN_WIDTH = MAP_WIDTH * TILE_SIZE
SCREEN_HEIGHT = MAP_HEIGHT * TILE_SIZE
UI_PANEL_HEIGHT = 150
WINDOW_HEIGHT = SCREEN_HEIGHT + UI_PANEL_HEIGHT
FPS = 60

# --- Dungeon generation constants ---
MAX_ROOMS = 20
ROOM_MIN_SIZE = 5
ROOM_MAX_SIZE = 10
MAX_ENEMIES_PER_ROOM = 3
MAX_ITEMS_PER_ROOM = 2

# --- Gameplay constants ---
PLAYER_FOV_RADIUS = 8
ENEMY_SIGHT_RADIUS = 7
PLAYER_BASE_HP = 30
PLAYER_BASE_ATTACK = 7
PLAYER_BASE_DEFENSE = 2


@dataclass
class RectRoom:
    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self):
        return self.x + self.w

    @property
    def y2(self):
        return self.y + self.h

    def center(self):
        return self.x + self.w // 2, self.y + self.h // 2

    def intersects(self, other: "RectRoom"):
        return self.x <= other.x2 and self.x2 >= other.x and self.y <= other.y2 and self.y2 >= other.y


class Tile:
    def __init__(self, blocked: bool, block_sight: bool | None = None):
        self.blocked = blocked
        self.block_sight = blocked if block_sight is None else block_sight
        self.explored = False
        self.visible = False


class Entity:
    def __init__(self, x, y, char, color, name):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name


class Fighter:
    def __init__(self, hp, attack, defense):
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense


class Item:
    def __init__(self, name, icon, color, use_type, value):
        self.name = name
        self.icon = icon
        self.color = color
        self.use_type = use_type
        self.value = value


class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, "@", (245, 245, 240), "Player")
        self.fighter = Fighter(PLAYER_BASE_HP, PLAYER_BASE_ATTACK, PLAYER_BASE_DEFENSE)
        self.inventory = []


class Enemy(Entity):
    def __init__(self, x, y, kind="Goblin"):
        if kind == "Orc":
            super().__init__(x, y, "O", (120, 200, 120), kind)
            self.fighter = Fighter(16, 6, 1)
        else:
            super().__init__(x, y, "g", (70, 190, 70), kind)
            self.fighter = Fighter(10, 4, 0)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Roguelike Dungeon Crawler")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22)
        self.small_font = pygame.font.SysFont("consolas", 18)

        self.map = [[Tile(True) for _ in range(MAP_HEIGHT)] for _ in range(MAP_WIDTH)]
        self.player = Player(1, 1)
        self.enemies = []
        self.items = {}  # (x, y) -> Item
        self.messages = []
        self.game_over = False

        self.generate_dungeon()
        self.compute_fov()
        self.push_message("Explore the dungeon. Arrow keys/WASD to move.")
        self.push_message("G to pick up, I to use potion. Reach enemies to fight.")

    def push_message(self, msg):
        self.messages.append(msg)
        if len(self.messages) > 7:
            self.messages.pop(0)

    def carve_room(self, room: RectRoom):
        for x in range(room.x + 1, room.x2):
            for y in range(room.y + 1, room.y2):
                self.map[x][y].blocked = False
                self.map[x][y].block_sight = False

    def carve_h_tunnel(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.map[x][y].blocked = False
            self.map[x][y].block_sight = False

    def carve_v_tunnel(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.map[x][y].blocked = False
            self.map[x][y].block_sight = False

    def random_item(self):
        roll = random.random()
        if roll < 0.7:
            return Item("Healing Potion", "!", (255, 90, 90), "heal", random.randint(6, 12))
        return Item("Bomb", "*", (255, 180, 50), "bomb", random.randint(5, 9))

    def generate_dungeon(self):
        rooms = []
        self.enemies.clear()
        self.items.clear()

        for _ in range(MAX_ROOMS):
            w = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
            h = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
            x = random.randint(1, MAP_WIDTH - w - 2)
            y = random.randint(1, MAP_HEIGHT - h - 2)
            new_room = RectRoom(x, y, w, h)

            if any(new_room.intersects(other) for other in rooms):
                continue

            self.carve_room(new_room)
            cx, cy = new_room.center()

            if not rooms:
                self.player.x, self.player.y = cx, cy
            else:
                px, py = rooms[-1].center()
                if random.random() < 0.5:
                    self.carve_h_tunnel(px, cx, py)
                    self.carve_v_tunnel(py, cy, cx)
                else:
                    self.carve_v_tunnel(py, cy, px)
                    self.carve_h_tunnel(px, cx, cy)

            enemies_here = random.randint(0, MAX_ENEMIES_PER_ROOM)
            for _ in range(enemies_here):
                ex = random.randint(new_room.x + 1, new_room.x2 - 1)
                ey = random.randint(new_room.y + 1, new_room.y2 - 1)
                if (ex, ey) == (self.player.x, self.player.y) or self.entity_at(ex, ey):
                    continue
                self.enemies.append(Enemy(ex, ey, "Orc" if random.random() < 0.3 else "Goblin"))

            items_here = random.randint(0, MAX_ITEMS_PER_ROOM)
            for _ in range(items_here):
                ix = random.randint(new_room.x + 1, new_room.x2 - 1)
                iy = random.randint(new_room.y + 1, new_room.y2 - 1)
                if (ix, iy) == (self.player.x, self.player.y) or self.entity_at(ix, iy):
                    continue
                if (ix, iy) not in self.items:
                    self.items[(ix, iy)] = self.random_item()

            rooms.append(new_room)

    def in_bounds(self, x, y):
        return 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT

    def is_blocked(self, x, y):
        if not self.in_bounds(x, y):
            return True
        if self.map[x][y].blocked:
            return True
        return self.entity_at(x, y) is not None

    def entity_at(self, x, y):
        for enemy in self.enemies:
            if enemy.x == x and enemy.y == y:
                return enemy
        return None

    def line_of_sight(self, x0, y0, x1, y1):
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            if (x0, y0) != (x1, y1) and self.map[x0][y0].block_sight:
                return False
            if (x0, y0) == (x1, y1):
                return True
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def compute_fov(self):
        for x in range(MAP_WIDTH):
            for y in range(MAP_HEIGHT):
                self.map[x][y].visible = False

        px, py = self.player.x, self.player.y
        for x in range(max(0, px - PLAYER_FOV_RADIUS), min(MAP_WIDTH, px + PLAYER_FOV_RADIUS + 1)):
            for y in range(max(0, py - PLAYER_FOV_RADIUS), min(MAP_HEIGHT, py + PLAYER_FOV_RADIUS + 1)):
                if math.dist((px, py), (x, y)) <= PLAYER_FOV_RADIUS:
                    if self.line_of_sight(px, py, x, y):
                        self.map[x][y].visible = True
                        self.map[x][y].explored = True

    def attack(self, attacker_name, atk_stats: Fighter, defender_name, def_stats: Fighter):
        damage = max(1, atk_stats.attack - def_stats.defense + random.randint(-1, 2))
        def_stats.hp -= damage
        self.push_message(f"{attacker_name} attacks {defender_name} for {damage} damage.")
        return def_stats.hp <= 0

    def try_move_player(self, dx, dy):
        if self.game_over:
            return
        nx, ny = self.player.x + dx, self.player.y + dy
        if not self.in_bounds(nx, ny) or self.map[nx][ny].blocked:
            return

        target = self.entity_at(nx, ny)
        acted = False
        if target:
            acted = True
            killed = self.attack(self.player.name, self.player.fighter, target.name, target.fighter)
            if killed:
                self.push_message(f"{target.name} is slain!")
                self.enemies.remove(target)
        else:
            self.player.x, self.player.y = nx, ny
            acted = True

        if acted:
            self.compute_fov()
            self.enemy_turns()
            self.compute_fov()

    def enemy_turns(self):
        for enemy in list(self.enemies):
            if enemy.fighter.hp <= 0:
                continue

            dist = math.dist((enemy.x, enemy.y), (self.player.x, self.player.y))
            sees_player = dist <= ENEMY_SIGHT_RADIUS and self.line_of_sight(enemy.x, enemy.y, self.player.x, self.player.y)

            if dist <= 1.5:
                dead = self.attack(enemy.name, enemy.fighter, "Player", self.player.fighter)
                if dead:
                    self.game_over = True
                    self.push_message("You died! Press R to restart or ESC to quit.")
                    return
            elif sees_player:
                dx = 0 if enemy.x == self.player.x else (1 if self.player.x > enemy.x else -1)
                dy = 0 if enemy.y == self.player.y else (1 if self.player.y > enemy.y else -1)
                if not self.is_blocked(enemy.x + dx, enemy.y + dy) and (enemy.x + dx, enemy.y + dy) != (self.player.x, self.player.y):
                    enemy.x += dx
                    enemy.y += dy
            else:
                # Random patrol behavior when player unseen.
                if random.random() < 0.4:
                    dx, dy = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)])
                    tx, ty = enemy.x + dx, enemy.y + dy
                    if self.in_bounds(tx, ty) and not self.map[tx][ty].blocked and not self.entity_at(tx, ty) and (tx, ty) != (self.player.x, self.player.y):
                        enemy.x, enemy.y = tx, ty

    def pickup_item(self):
        pos = (self.player.x, self.player.y)
        if pos in self.items:
            item = self.items.pop(pos)
            self.player.inventory.append(item)
            self.push_message(f"Picked up {item.name}.")
        else:
            self.push_message("There is nothing to pick up here.")

    def use_item(self):
        if not self.player.inventory:
            self.push_message("Inventory is empty.")
            return

        # Simple use policy: first healing potion, otherwise first item.
        index = 0
        for i, item in enumerate(self.player.inventory):
            if item.use_type == "heal":
                index = i
                break
        item = self.player.inventory.pop(index)

        if item.use_type == "heal":
            before = self.player.fighter.hp
            self.player.fighter.hp = min(self.player.fighter.max_hp, self.player.fighter.hp + item.value)
            healed = self.player.fighter.hp - before
            self.push_message(f"Used {item.name}, healed {healed} HP.")
        elif item.use_type == "bomb":
            hit_any = False
            for enemy in list(self.enemies):
                if math.dist((enemy.x, enemy.y), (self.player.x, self.player.y)) <= 2.5:
                    hit_any = True
                    enemy.fighter.hp -= item.value
                    self.push_message(f"{enemy.name} takes {item.value} bomb damage.")
                    if enemy.fighter.hp <= 0:
                        self.push_message(f"{enemy.name} is blown up!")
                        self.enemies.remove(enemy)
            if not hit_any:
                self.push_message("Bomb explodes harmlessly.")

        self.enemy_turns()
        self.compute_fov()

    def restart(self):
        self.map = [[Tile(True) for _ in range(MAP_HEIGHT)] for _ in range(MAP_WIDTH)]
        self.player = Player(1, 1)
        self.enemies = []
        self.items = {}
        self.messages = []
        self.game_over = False
        self.generate_dungeon()
        self.compute_fov()
        self.push_message("New run started.")

    def draw(self):
        self.screen.fill((0, 0, 0))

        # Tiles
        for x in range(MAP_WIDTH):
            for y in range(MAP_HEIGHT):
                tile = self.map[x][y]
                sx, sy = x * TILE_SIZE, y * TILE_SIZE
                if tile.visible:
                    color = (85, 85, 95) if tile.blocked else (50, 55, 62)
                    pygame.draw.rect(self.screen, color, (sx, sy, TILE_SIZE, TILE_SIZE))
                elif tile.explored:
                    color = (35, 35, 40) if tile.blocked else (24, 28, 34)
                    pygame.draw.rect(self.screen, color, (sx, sy, TILE_SIZE, TILE_SIZE))

        # Items
        for (x, y), item in self.items.items():
            if self.map[x][y].visible:
                text = self.font.render(item.icon, True, item.color)
                self.screen.blit(text, (x * TILE_SIZE + 5, y * TILE_SIZE + 1))

        # Enemies
        for enemy in self.enemies:
            if self.map[enemy.x][enemy.y].visible:
                text = self.font.render(enemy.char, True, enemy.color)
                self.screen.blit(text, (enemy.x * TILE_SIZE + 4, enemy.y * TILE_SIZE + 1))

        # Player
        text = self.font.render(self.player.char, True, self.player.color)
        self.screen.blit(text, (self.player.x * TILE_SIZE + 4, self.player.y * TILE_SIZE + 1))

        # UI panel
        panel_y = SCREEN_HEIGHT
        pygame.draw.rect(self.screen, (20, 20, 22), (0, panel_y, SCREEN_WIDTH, UI_PANEL_HEIGHT))
        pygame.draw.line(self.screen, (75, 75, 80), (0, panel_y), (SCREEN_WIDTH, panel_y), 2)

        hp_text = f"HP: {self.player.fighter.hp}/{self.player.fighter.max_hp}"
        inv_names = ", ".join(item.name for item in self.player.inventory) or "(empty)"
        meta = f"Enemies: {len(self.enemies)} | Inventory: {inv_names}"
        ctl = "Move: Arrows/WASD | G: pickup | I: use item | R: restart | ESC: quit"

        self.screen.blit(self.small_font.render(hp_text, True, (220, 90, 90)), (10, panel_y + 8))
        self.screen.blit(self.small_font.render(meta, True, (220, 220, 220)), (10, panel_y + 34))
        self.screen.blit(self.small_font.render(ctl, True, (180, 180, 200)), (10, panel_y + 60))

        msg_y = panel_y + 86
        for msg in self.messages[-3:]:
            self.screen.blit(self.small_font.render(msg, True, (210, 210, 180)), (10, msg_y))
            msg_y += 20

        if self.game_over:
            over = self.font.render("YOU DIED", True, (255, 80, 80))
            self.screen.blit(over, (SCREEN_WIDTH // 2 - over.get_width() // 2, SCREEN_HEIGHT // 2 - 20))

        pygame.display.flip()

    def handle_key(self, key):
        keymap = {
            pygame.K_UP: (0, -1),
            pygame.K_DOWN: (0, 1),
            pygame.K_LEFT: (-1, 0),
            pygame.K_RIGHT: (1, 0),
            pygame.K_w: (0, -1),
            pygame.K_s: (0, 1),
            pygame.K_a: (-1, 0),
            pygame.K_d: (1, 0),
        }
        if key in keymap:
            self.try_move_player(*keymap[key])
        elif key == pygame.K_g:
            self.pickup_item()
        elif key == pygame.K_i:
            self.use_item()
        elif key == pygame.K_r:
            self.restart()

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        self.handle_key(event.key)

            self.draw()

        pygame.quit()


if __name__ == "__main__":
    Game().run()
