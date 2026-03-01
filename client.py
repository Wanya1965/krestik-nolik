import pygame
import socket
import threading
import json
import sys

# Инициализация Pygame
pygame.init()

# Настройки окна
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Морской бой - Клиент")
font = pygame.font.SysFont(None, 24)

# Цвета
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
GREEN = (0, 200, 0)
RED_COLOR = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)

# Поля
GRID_SIZE = 10
CELL_SIZE = 30
OFFSET_X = 50
OFFSET_Y = 150

# Игровые параметры
MAX_SHIPS = 10

# Игровое состояние
placing_ships = True
ready_sent = False
game_started = False
my_turn = False
winner = None
both_ready = False

# Массив для размещения кораблей
ships = []

# Для хранения попаданий по противнику
enemy_shots = {}  # (x,y): hit/miss

# Создаем соединение
HOST = '127.0.0.1'
PORT = 65432
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def connect_to_server():
    try:
        client_socket.connect((HOST, PORT))
        threading.Thread(target=listen_server, daemon=True).start()
    except Exception as e:
        print("Ошибка подключения:", e)
        sys.exit()

def listen_server():
    global game_started, my_turn, winner, both_ready
    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            message = json.loads(data.decode())
            handle_server_message(message)
        except:
            break

def handle_server_message(msg):
    global game_started, my_turn, winner, both_ready, enemy_shots
    msg_type = msg['type']
    if msg_type == 'welcome':
        print(f"Подключен как Игрок {msg['player_id']+1}")
    elif msg_type == 'start':
        game_started = True
        first_player = msg['first_player']
        my_turn = (first_player == 0)
        print("Игра началась!")
        if my_turn:
            print("Ваш ход")
        else:
            print("Ожидайте хода противника")
    elif msg_type == 'both_ready':
        both_ready = True
        print("Оба игрока готовы. Игра начинается.")
    elif msg_type == 'move_result':
        hit = msg['hit']
        x, y = msg['x'], msg['y']
        print(f"Ваш выстрел в ({x+1},{y+1}) — {'Попадание' if hit else 'Промах'}")
        # Запоминаем результат
        enemy_shots[(x,y)] = hit
        my_turn = False
    elif msg_type == 'attacked':
        x, y = msg['x'], msg['y']
        hit = msg['hit']
        print(f"Противник выстрелил в ({x+1},{y+1}) — {'Попадание' if hit else 'Промах'}")
        my_turn = True
        if 'winner' in msg:
            winner = msg['winner']
            print(f"Победил Игрок {winner+1}")
    elif msg_type == 'next_turn':
        my_turn = (msg['player'] == 0)
        if my_turn:
            print("Ваш ход")
        else:
            print("Ожидайте хода противника")
    elif msg_type == 'game_over':
        winner = msg['winner']
        print(f"Игра окончена! Победил Игрок {winner+1}")

def draw_grid(offset_x, offset_y, show_ships=False, ships_list=None, reveal_ships=False):
    # Верхние буквы
    for i in range(GRID_SIZE):
        letter = chr(ord('А') + i)
        text = font.render(letter, True, DARK_GRAY)
        screen.blit(text, (offset_x + i * CELL_SIZE + CELL_SIZE/2 - 8, offset_y - 25))
    # Левые цифры
    for j in range(GRID_SIZE):
        number = str(j+1)
        text = font.render(number, True, DARK_GRAY)
        screen.blit(text, (offset_x - 25, offset_y + j*CELL_SIZE + CELL_SIZE/2 - 8))
    # Клетки
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            rect = pygame.Rect(offset_x + x*CELL_SIZE, offset_y + y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, GRAY, rect, 1)
            # Показ своих кораблей
            if show_ships and ships_list and (x, y) in ships_list:
                pygame.draw.rect(screen, BLUE, rect)
            # Для поля противника - показывать попадания
            if reveal_ships and (x, y) in ships_list:
                pygame.draw.rect(screen, GREEN, rect)
            # Отображение попаданий по противнику
            if (x, y) in enemy_shots:
                color = GREEN if enemy_shots[(x, y)] else RED_COLOR
                pygame.draw.rect(screen, color, rect)
                if enemy_shots[(x, y)]:
                    # Надпись "Попал в корабль - 1"
                    text = font.render("Попал в корабль - 1", True, BLACK)
                    screen.blit(text, (rect.x + 2, rect.y + CELL_SIZE - 20))
    return

def handle_click(x_mouse, y_mouse):
    global ships, placing_ships, ready_sent
    # Размещение кораблей
    if placing_ships:
        if OFFSET_X <= x_mouse <= OFFSET_X + GRID_SIZE * CELL_SIZE and OFFSET_Y <= y_mouse <= OFFSET_Y + GRID_SIZE * CELL_SIZE:
            x_cell = (x_mouse - OFFSET_X) // CELL_SIZE
            y_cell = (y_mouse - OFFSET_Y) // CELL_SIZE
            if len(ships) >= MAX_SHIPS:
                return
            if (x_cell, y_cell) not in ships:
                if can_place_ship(x_cell, y_cell):
                    ships.append((x_cell, y_cell))
        return
    # Нажатие на кнопку "Готов"
    if not game_started and ready_button_rect.collidepoint(x_mouse, y_mouse):
        if len(ships) == MAX_SHIPS:
            send_ships()
            ready_sent = True
        return
    # Выстрел по противнику
    if game_started and my_turn:
        opponent_offset_x = OFFSET_X + GRID_SIZE*CELL_SIZE + 50
        if opponent_offset_x <= x_mouse <= opponent_offset_x + GRID_SIZE * CELL_SIZE and OFFSET_Y <= y_mouse <= OFFSET_Y + GRID_SIZE * CELL_SIZE:
            x_cell = (x_mouse - opponent_offset_x) // CELL_SIZE
            y_cell = (y_mouse - OFFSET_Y) // CELL_SIZE
            send_move(x_cell, y_cell)

def can_place_ship(x, y):
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                if (nx, ny) in ships:
                    if (nx, ny) != (x, y):
                        return False
    return True

def send_ships():
    data = {'type': 'place_ships', 'ships': [{'x': x, 'y': y} for (x, y) in ships]}
    client_socket.sendall(json.dumps(data).encode())

def send_move(x, y):
    data = {'type': 'move', 'x': x, 'y': y}
    client_socket.sendall(json.dumps(data).encode())

# Кнопка "Готов"
ready_button_rect = pygame.Rect(700, 50, 150, 50)
button_pressed = False

def main():
    global placing_ships, ready_sent, game_started, my_turn, both_ready, button_pressed
    connect_to_server()

    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client_socket.close()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                handle_click(mx, my)
                # Обработка кнопки "Готов"
                if ready_button_rect.collidepoint(mx, my) and not button_pressed:
                    if len(ships) == MAX_SHIPS:
                        button_pressed = True
                        send_ships()
                        ready_sent = True

        # Рисование
        screen.fill(WHITE)

        # Поле своих кораблей
        draw_grid(OFFSET_X, OFFSET_Y, show_ships=True, ships_list=ships)

        if not game_started:
            # Информация о размещении
            info_text = font.render(f"Разместите все {MAX_SHIPS} кораблей. Нажмите 'Готов' для начала.", True, DARK_GRAY)
            screen.blit(info_text, (50, 20))
            # Кнопка "Готов"
            color = RED_COLOR if button_pressed else GREEN
            pygame.draw.rect(screen, color, ready_button_rect)
            ready_text = font.render("Готов", True, (255,255,255))
            screen.blit(ready_text, (ready_button_rect.x + 50, ready_button_rect.y + 15))
        else:
            # Поле противника
            opponent_offset_x = OFFSET_X + GRID_SIZE*CELL_SIZE + 50
            draw_grid(opponent_offset_x, OFFSET_Y)
            # Надписи
            label1 = font.render("Ваши корабли", True, DARK_GRAY)
            screen.blit(label1, (OFFSET_X, OFFSET_Y - 40))
            label2 = font.render("Противник", True, DARK_GRAY)
            screen.blit(label2, (opponent_offset_x, OFFSET_Y - 40))
            # Статус
            status_text = "Ваш ход" if my_turn else "Ожидайте хода"
            color_status = GREEN if my_turn else DARK_GRAY
            status_render = font.render(status_text, True, color_status)
            screen.blit(status_render, (50, 20))
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()