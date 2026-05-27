#!/usr/bin/env python3

import pygame
import random
import sys
import time

pygame.init()

# --------------------- SETTINGS ---------------------
WIDTH, HEIGHT = 600, 400
CELL = 10
COLS = WIDTH // CELL
ROWS = HEIGHT // CELL
FPS = 10

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Game With Menu & Maze")

clock = pygame.time.Clock()

# --------------------- COLORS ---------------------
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
GOLD = (255, 215, 0)
BLUE = (50, 150, 255)
YELLOW = (255, 255, 0)
GRAY = (200, 200, 200)
DARK = (40, 40, 40)

font = pygame.font.SysFont(None, 60)
small_font = pygame.font.SysFont(None, 30)

POWER_DURATION = 10000  # ms

# --------------------- GLOBAL GAME STATE ---------------------
mode = "normal"   # "normal" or "maze"
difficulty = None  # "easy", "hard", "impossible"
in_game = False
paused = False

def draw_text(text, color, x, y, font_obj):
    surf = font_obj.render(text, True, color)
    rect = surf.get_rect(center=(x, y))
    screen.blit(surf, rect)

# ---------------- MENU / LOBBY BUTTON ----------------
def draw_lobby_button():
    pygame.draw.rect(screen, GRAY, (WIDTH - 100, 0, 100, 30))
    draw_text("Menu", BLACK, WIDTH - 50, 15, small_font)

def is_click_lobby(x, y):
    return WIDTH - 100 <= x <= WIDTH and 0 <= y <= 30

# ---------------- GAME RESET ----------------
def random_cell():
    return (
        random.randrange(0, WIDTH, CELL),
        random.randrange(0, HEIGHT, CELL)
    )

def reset_game():
    snake = [(100, 100), (80, 100), (60, 100)]
    direction = (CELL, 0)
    apples = [random_cell() for _ in range(random.randint(1, 10))]

    golden = random_cell()
    gold_timer = pygame.time.get_ticks()

    power = False
    power_start = 0

    walls = []
    if mode == "maze":
        walls = make_maze(difficulty)

    return snake, direction, apples, golden, gold_timer, power, power_start, walls

# ---------------- MAZE GENERATOR ----------------
def make_maze(diff):
    walls = []
    # Easy open spacing
    spacing = { "easy": 6, "hard": 4, "impossible": 2 }.get(diff, 6)
    for r in range(ROWS):
        for c in range(COLS):
            if r % spacing == 0 and c % spacing == 0:
                walls.append((c * CELL, r * CELL))
    return walls

# ---------------- FLASH “YOU LOSE” ----------------
def flash_lose():
    for i in range(40):
        screen.fill(BLACK)
        if i % 2 == 0:
            draw_text("YOU LOSE", YELLOW, WIDTH // 2, HEIGHT // 2, font)
        pygame.display.flip()
        pygame.time.delay(30)

# ---------------- GAME LOOP ----------------
snake, direction, apples, golden, gold_timer, power, power_start, walls = reset_game()

while True:
    # ---------- EVENT HANDLING ----------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if paused and not in_game:
                # In the pause menu: detect clicked option
                # Buttons are rendered later
                pass
            elif is_click_lobby(mx, my):
                paused = True

        if event.type == pygame.KEYDOWN:
            if paused:
                # MENU NAVIGATION
                if event.key == pygame.K_1:
                    mode = "normal"
                    in_game = True
                    paused = False
                    snake, direction, apples, golden, gold_timer, power, power_start, walls = reset_game()
                elif event.key == pygame.K_2:
                    mode = "maze"; difficulty = "easy"
                    in_game = True; paused = False
                    snake, direction, apples, golden, gold_timer, power, power_start, walls = reset_game()
                elif event.key == pygame.K_3:
                    mode = "maze"; difficulty = "hard"
                    in_game = True; paused = False
                    snake, direction, apples, golden, gold_timer, power, power_start, walls = reset_game()
                elif event.key == pygame.K_4:
                    mode = "maze"; difficulty = "impossible"
                    in_game = True; paused = False
                    snake, direction, apples, golden, gold_timer, power, power_start, walls = reset_game()
            else:
                # Normal game controls
                if event.key == pygame.K_UP and direction != (0, CELL):
                    direction = (0, -CELL)
                elif event.key == pygame.K_DOWN and direction != (0, -CELL):
                    direction = (0, CELL)
                elif event.key == pygame.K_LEFT and direction != (CELL, 0):
                    direction = (-CELL, 0)
                elif event.key == pygame.K_RIGHT and direction != (-CELL, 0):
                    direction = (CELL, 0)

    # ---------- DRAW FRAME ----------
    screen.fill(DARK)

    if paused and not in_game:
        draw_text("PAUSED", WHITE, WIDTH // 2, 60, font)
        draw_text("1 Normal Mode", WHITE, WIDTH // 2, 140, small_font)
        draw_text("2 Maze Easy", WHITE, WIDTH // 2, 180, small_font)
        draw_text("3 Maze Hard", WHITE, WIDTH // 2, 220, small_font)
        draw_text("4 Maze Impossible", WHITE, WIDTH // 2, 260, small_font)
        pygame.display.flip()
        continue

    # ---------- GAME LOGIC ----------
    # Snake movement
    head = (snake[0][0] + direction[0], snake[0][1] + direction[1])

    if head in snake or head[0] < 0 or head[0] >= WIDTH or head[1] < 0 or head[1] >= HEIGHT:
        flash_lose()
        snake, direction, apples, golden, gold_timer, power, power_start, walls = reset_game()
        continue

    if mode == "maze" and (head in walls):
        flash_lose()
        snake, direction, apples, golden, gold_timer, power, power_start, walls = reset_game()
        continue

    snake.insert(0, head)

    # Apples eaten?
    ate = False
    if head in apples:
        apples.remove(head)
        ate = True
        if len(apples) < 10:
            apples.append(random_cell())

    # Golden apple logic: stays for 2.5 sec then moves within 5×5
    now = pygame.time.get_ticks()
    if now - gold_timer > 2500:
        gold_timer = now
        gx, gy = golden
        offsets = [-2*CELL, -CELL, 0, CELL, 2*CELL]
        newx = gx + random.choice(offsets)
        newy = gy + random.choice(offsets)
        newx = max(0, min(WIDTH - CELL, newx))
        newy = max(0, min(HEIGHT - CELL, newy))
        golden = (newx, newy)

    if head == golden:
        power = True
        power_start = now
        ate = True

    if power and now - power_start > POWER_DURATION:
        power = False

    if not ate:
        snake.pop()

    # ---------- DRAW GAME ----------
    # Maze walls
    for w in walls:
        pygame.draw.rect(screen, BLUE, (*w, CELL, CELL))

    # Normal apples
    for a in apples:
        pygame.draw.rect(screen, RED, (*a, CELL, CELL))

    # Draw golden apple
    pygame.draw.rect(screen, GOLD, (*golden, CELL, CELL))

    # Draw snake
    for seg in snake:
        pygame.draw.rect(screen, GREEN, (*seg, CELL, CELL))

    # Lobby button
    draw_lobby_button()

    pygame.display.flip()
    clock.tick(FPS)

