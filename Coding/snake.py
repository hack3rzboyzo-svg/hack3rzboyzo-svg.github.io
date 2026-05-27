#!/usr/bin/env python3

import pygame
import random
import sys
import time

pygame.init()

# Screen
WIDTH, HEIGHT = 600, 400
CELL = 10
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake")

clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
YELLOW = (255, 255, 0)

# Font
font = pygame.font.SysFont(None, 90)

def reset_game():
    snake = [(100, 100), (80, 100), (60, 100)]
    direction = (CELL, 0)
    apple = (
        random.randrange(0, WIDTH, CELL),
        random.randrange(0, HEIGHT, CELL)
    )
    return snake, direction, apple

def flash_lose_text():
    text = font.render("YOU LOSE", True, YELLOW)
    rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))

    flashes = 67        # ⚠️ CHANGE THIS to a lower number if needed
    duration = 2.0       # seconds
    delay = duration / flashes

    for i in range(flashes):
        screen.fill(BLACK)
        if i % 2 == 0:
            screen.blit(text, rect)
        pygame.display.flip()
        time.sleep(delay)

# Initialize game
snake, direction, apple = reset_game()

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
    head_x = snake[0][0] + direction[0]
    head_y = snake[0][1] + direction[1]
    new_head = (head_x, head_y)

    # Crash detection
    if (new_head in snake or
        head_x < 0 or head_x >= WIDTH or
        head_y < 0 or head_y >= HEIGHT):
        flash_lose_text()
        snake, direction, apple = reset_game()
        continue

    snake.insert(0, new_head)

    if new_head == apple:
        apple = (
            random.randrange(0, WIDTH, CELL),
            random.randrange(0, HEIGHT, CELL)
        )
    else:
        snake.pop()

    # Draw
    screen.fill(BLACK)
    for s in snake:
        pygame.draw.rect(screen, GREEN, (*s, CELL, CELL))
    pygame.draw.rect(screen, RED, (*apple, CELL, CELL))

    pygame.display.flip()
    clock.tick(10)

