#!/usr/bin/env python3

import pygame
import random
import sys

pygame.init()

# Screen
WIDTH, HEIGHT = 600, 400
CELL = 10
COLS = WIDTH // CELL
ROWS = HEIGHT // CELL

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake")

clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
GOLD = (255, 215, 0)
YELLOW = (255, 255, 0)

# Font
font = pygame.font.SysFont(None, 60)

POWER_DURATION = 10000  # ms (10 seconds)

def random_cell():
    return (
        random.randrange(0, WIDTH, CELL),
        random.randrange(0, HEIGHT, CELL)
    )

def reset_game():
    snake = [(100, 100), (80, 100), (60, 100)]
    direction = (CELL, 0)
    apple = random_cell()
    golden = random_cell()
    power_active = False
    power_start = 0
    return snake, direction, apple, golden, power_active, power_start

def flash_lose_text():
    text = font.render("YOU LOSE", True, YELLOW)
    rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))

    flashes = 60  # safer value
    for i in range(flashes):
        screen.fill(BLACK)
        if i % 2 == 0:
            screen.blit(text, rect)
        pygame.display.flip()
        pygame.time.delay(30)

# Initialize
snake, direction, apple, golden, power_active, power_start = reset_game()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and direction != (0, CELL):
                direction = (0, -CELL)
            elif event.key == pygame.K_DOWN and direction != (0, -CELL):
                direction = (0, CELL)
            elif event.key == pygame.K_LEFT and direction != (CELL, 0):
                direction = (-CELL, 0)
            elif event.key == pygame.K_RIGHT and direction != (-CELL, 0):
                direction = (CELL, 0)

    # Move snake
    head = (snake[0][0] + direction[0], snake[0][1] + direction[1])

    # Crash
    if (head in snake or
        head[0] < 0 or head[0] >= WIDTH or
        head[1] < 0 or head[1] >= HEIGHT):
        flash_lose_text()
        snake, direction, apple, golden, power_active, power_start = reset_game()
        continue

    snake.insert(0, head)

    # Power mode timeout
    if power_active and pygame.time.get_ticks() - power_start > POWER_DURATION:
        power_active = False

    ate = False

    # Normal apple
    if head == apple:
        apple = random_cell()
        ate = True

    # Golden apple
    if head == golden:
        power_active = True
        power_start = pygame.time.get_ticks()
        golden = random_cell()
        ate = True

    # Checkerboard apples during power mode
    if power_active:
        cx = head[0] // CELL
        cy = head[1] // CELL
        if (cx + cy) % 2 == 0:
            ate = True

    if not ate:
        snake.pop()

    # Move golden apple randomly
    gx, gy = golden
    golden = (
        (gx + random.choice([-CELL, 0, CELL])) % WIDTH,
        (gy + random.choice([-CELL, 0, CELL])) % HEIGHT
    )

    # Draw
    screen.fill(BLACK)

    # Checkerboard apples
    if power_active:
        for y in range(ROWS):
            for x in range(COLS):
                if (x + y) % 2 == 0:
                    pygame.draw.rect(
                        screen,
                        RED,
                        (x * CELL, y * CELL, CELL, CELL)
                    )

    # Normal apple
    pygame.draw.rect(screen, RED, (*apple, CELL, CELL))

    # Golden apple
    pygame.draw.rect(screen, GOLD, (*golden, CELL, CELL))

    # Snake
    for s in snake:
        pygame.draw.rect(screen, GREEN, (*s, CELL, CELL))

    pygame.display.flip()
    clock.tick(10)

