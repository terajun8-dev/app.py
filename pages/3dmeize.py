import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# 3Dグリッドの設定
width, height = 800, 600
screen = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
glEnable(GL_DEPTH_TEST)

# 迷路のグリッドを描画（例: 2Dグリッドを3Dに変換）
def draw_grid():
    glBegin(GL_LINES)
    for x in range(0, width, 10):
        for y in range(0, height, 10):
            glColor3f(1, 0, 0)  # 赤
            glVertex3f(x, y, 0)
    glEnd()

# キー入力で移動
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[K_LEFT]:
        glTranslatef(-1, 0, 0)
    elif keys[K_RIGHT]:
        glTranslatef(1, 0, 0)
    elif keys[K_UP]:
        glTranslatef(0, -1, 0)
    else:
        glTranslatef(0, 0, 0)

    draw_grid()
    pygame.display.flip()
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    pygame.time.wait(10)

pygame.quit()
