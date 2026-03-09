import pygame
import socket
import threading
import json
import sys

# Инициализация Pygame
pygame.init()

# Настройки окна
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Морской бой - Клиент")
font = pygame.font.SysFont(None, 24)
big_font = pygame.font.SysFont(None, 36)

# Цвета
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
GREEN = (0, 200, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)

# Поля
GRID_SIZE = 10
CELL_SIZE = 30
OFFSET_X = 50
OFFSET_Y = 150
OPPONENT_OFFSET_X = OFFSET_X + GRID_SIZE * CELL_SIZE + 150

# Игровые параметры
MAX_SHIPS = 10

# Глобальные переменные
my_ships = []
my_shots = {}
enemy_shots = {}
hit_counter = 0

# Состояния
placing = True
waiting = False
playing = False
my_turn = False
player_id = None
winner = None

# Сокет
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
HOST = '127.0.0.1'
PORT = 65432

# Для отладки
last_message = ""

def connect_to_server():
    try:
        client_socket.connect((HOST, PORT))
        print("Подключен к серверу")
        thread = threading.Thread(target=receive_messages, daemon=True)
        thread.start()
        return True
    except:
        return False

def receive_messages():
    global playing, my_turn, player_id, my_shots, enemy_shots, hit_counter, winner, waiting, placing, last_message
    
    buffer = ""
    while True:
        try:
            data = client_socket.recv(4096).decode()
            if not data:
                break
            buffer += data
            print(f"Получены данные: {data}")  # Отладка
            
            while '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                if message.strip():
                    try:
                        msg = json.loads(message)
                        msg_type = msg['type']
                        print(f"Тип сообщения: {msg_type}")  # Отладка
                        last_message = f"Последнее сообщение: {msg_type}"
                        
                        if msg_type == 'welcome':
                            player_id = msg['player_id']
                            print(f"Я игрок {player_id + 1}")
                            
                        elif msg_type == 'placement_ok' or msg_type == 'placement_confirmed':
                            print("Корабли приняты!")
                            placing = False
                            waiting = True
                            
                        elif msg_type == 'start_game' or msg_type == 'game_start':
                            print("ИГРА НАЧАЛАСЬ!")
                            playing = True
                            waiting = False
                            # Проверяем разные форматы сообщения
                            if 'first_player' in msg:
                                first_player = msg['first_player']
                            else:
                                first_player = 0
                            my_turn = (first_player == player_id)
                            print(f"Мой ход: {my_turn}")
                            
                        elif msg_type == 'move_result':
                            x = msg['x']
                            y = msg['y']
                            hit = msg['hit']
                            my_shots[(x, y)] = hit
                            if hit:
                                hit_counter += 1
                            print(f"Результат выстрела: попадание={hit}")
                            
                        elif msg_type == 'enemy_move' or msg_type == 'attacked':
                            x = msg['x']
                            y = msg['y']
                            hit = msg['hit']
                            enemy_shots[(x, y)] = hit
                            print(f"Противник выстрелил: попадание={hit}")
                            
                        elif msg_type == 'turn' or msg_type == 'next_turn':
                            if 'player' in msg:
                                my_turn = (msg['player'] == player_id)
                            print(f"Смена хода. Мой ход: {my_turn}")
                            
                        elif msg_type == 'game_over':
                            winner = msg['winner']
                            print(f"Победитель: игрок {winner + 1}")
                            
                    except json.JSONDecodeError as e:
                        print(f"Ошибка JSON: {e}")
        except Exception as e:
            print(f"Ошибка приема: {e}")
            break

def can_place_ship(x, y):
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 10 and 0 <= ny < 10:
                if (nx, ny) in my_ships:
                    return False
    return True

def send_ships():
    ships_data = [{'x': x, 'y': y} for x, y in my_ships]
    message = {'type': 'place_ships', 'ships': ships_data}
    try:
        client_socket.sendall((json.dumps(message) + '\n').encode())
        print("Корабли отправлены")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def send_move(x, y):
    message = {'type': 'move', 'x': x, 'y': y}
    try:
        client_socket.sendall((json.dumps(message) + '\n').encode())
        print(f"Ход отправлен: {x+1},{y+1}")
    except Exception as e:
        print(f"Ошибка отправки хода: {e}")

def draw_my_grid():
    # Буквы
    for i in range(10):
        letter = chr(ord('А') + i)
        text = font.render(letter, True, BLACK)
        screen.blit(text, (OFFSET_X + i * CELL_SIZE + 8, OFFSET_Y - 25))
    
    # Цифры
    for i in range(10):
        number = str(i + 1)
        text = font.render(number, True, BLACK)
        screen.blit(text, (OFFSET_X - 25, OFFSET_Y + i * CELL_SIZE + 8))
    
    # Клетки
    for y in range(10):
        for x in range(10):
            rect = pygame.Rect(OFFSET_X + x * CELL_SIZE, OFFSET_Y + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            
            # Свои корабли
            if (x, y) in my_ships:
                pygame.draw.rect(screen, BLUE, rect)
            else:
                pygame.draw.rect(screen, WHITE, rect)
            
            # Выстрелы противника
            if (x, y) in enemy_shots:
                if enemy_shots[(x, y)]:
                    pygame.draw.rect(screen, RED, rect)
                    pygame.draw.line(screen, BLACK, rect.topleft, rect.bottomright, 2)
                    pygame.draw.line(screen, BLACK, rect.topright, rect.bottomleft, 2)
                else:
                    pygame.draw.circle(screen, DARK_GRAY, rect.center, 5)
            
            pygame.draw.rect(screen, BLACK, rect, 1)

def draw_enemy_grid():
    # Буквы
    for i in range(10):
        letter = chr(ord('А') + i)
        text = font.render(letter, True, BLACK)
        screen.blit(text, (OPPONENT_OFFSET_X + i * CELL_SIZE + 8, OFFSET_Y - 25))
    
    # Цифры
    for i in range(10):
        number = str(i + 1)
        text = font.render(number, True, BLACK)
        screen.blit(text, (OPPONENT_OFFSET_X - 25, OFFSET_Y + i * CELL_SIZE + 8))
    
    # Клетки
    for y in range(10):
        for x in range(10):
            rect = pygame.Rect(OPPONENT_OFFSET_X + x * CELL_SIZE, OFFSET_Y + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            
            pygame.draw.rect(screen, WHITE, rect)
            
            # Мои выстрелы
            if (x, y) in my_shots:
                if my_shots[(x, y)]:
                    pygame.draw.rect(screen, RED, rect)
                    pygame.draw.line(screen, BLACK, rect.topleft, rect.bottomright, 2)
                    pygame.draw.line(screen, BLACK, rect.topright, rect.bottomleft, 2)
                else:
                    pygame.draw.circle(screen, DARK_GRAY, rect.center, 5)
            
            pygame.draw.rect(screen, BLACK, rect, 1)

def main():
    global placing, waiting, playing, my_turn, hit_counter, winner, my_ships, last_message
    
    if not connect_to_server():
        print("Не удалось подключиться")
        return
    
    clock = pygame.time.Clock()
    ready_button = pygame.Rect(900, 50, 150, 50)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                
                # Размещение кораблей
                if placing:
                    # Клик по полю
                    if (OFFSET_X <= x <= OFFSET_X + 10 * CELL_SIZE and 
                        OFFSET_Y <= y <= OFFSET_Y + 10 * CELL_SIZE):
                        
                        grid_x = (x - OFFSET_X) // CELL_SIZE
                        grid_y = (y - OFFSET_Y) // CELL_SIZE
                        
                        if len(my_ships) < MAX_SHIPS:
                            if (grid_x, grid_y) not in my_ships:
                                if can_place_ship(grid_x, grid_y):
                                    my_ships.append((grid_x, grid_y))
                                    print(f"Корабль {len(my_ships)}/{MAX_SHIPS}")
                    
                    # Клик по кнопке
                    if ready_button.collidepoint(x, y):
                        print("Клик по кнопке ГОТОВ")
                        if len(my_ships) == MAX_SHIPS:
                            send_ships()
                            placing = False
                            waiting = True
                            print("Переход в режим ожидания")
                        else:
                            print(f"Нужно {MAX_SHIPS} кораблей, сейчас {len(my_ships)}")
                
                # Выстрелы
                elif playing and my_turn and winner is None:
                    if (OPPONENT_OFFSET_X <= x <= OPPONENT_OFFSET_X + 10 * CELL_SIZE and 
                        OFFSET_Y <= y <= OFFSET_Y + 10 * CELL_SIZE):
                        
                        grid_x = (x - OPPONENT_OFFSET_X) // CELL_SIZE
                        grid_y = (y - OFFSET_Y) // CELL_SIZE
                        
                        if (grid_x, grid_y) not in my_shots:
                            send_move(grid_x, grid_y)
        
        # Отрисовка
        screen.fill(WHITE)
        
        if placing:
            # Режим размещения
            text1 = font.render(f"Разместите корабли: {len(my_ships)}/{MAX_SHIPS}", True, BLACK)
            screen.blit(text1, (50, 20))
            
            # Кнопка
            if len(my_ships) == MAX_SHIPS:
                pygame.draw.rect(screen, GREEN, ready_button)
            else:
                pygame.draw.rect(screen, GRAY, ready_button)
            pygame.draw.rect(screen, BLACK, ready_button, 2)
            
            ready_text = font.render("ГОТОВ", True, BLACK)
            text_rect = ready_text.get_rect(center=ready_button.center)
            screen.blit(ready_text, text_rect)
            
            # Поле
            draw_my_grid()
            
        elif waiting:
            # Ожидание второго игрока
            text = big_font.render("ОЖИДАНИЕ ВТОРОГО ИГРОКА...", True, BLUE)
            text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))
            screen.blit(text, text_rect)
            
            # Информация о том, что корабли отправлены
            info = font.render("Ваши корабли отправлены. Ожидание противника...", True, DARK_GRAY)
            info_rect = info.get_rect(center=(WIDTH//2, HEIGHT//2))
            screen.blit(info, info_rect)
            
            # Показываем свои корабли
            draw_my_grid()
            
            # Отладка
            debug = font.render(last_message, True, RED)
            screen.blit(debug, (50, HEIGHT - 30))
            
        elif playing:
            # Игра
            label1 = font.render("ВАШИ КОРАБЛИ", True, BLACK)
            screen.blit(label1, (OFFSET_X, OFFSET_Y - 40))
            draw_my_grid()
            
            label2 = font.render("ПРОТИВНИК", True, BLACK)
            screen.blit(label2, (OPPONENT_OFFSET_X, OFFSET_Y - 40))
            draw_enemy_grid()
            
            # Статус
            if winner is not None:
                if winner == player_id:
                    status = "ВЫ ПОБЕДИЛИ!"
                    color = GREEN
                else:
                    status = "ВЫ ПРОИГРАЛИ!"
                    color = RED
            else:
                status = "ВАШ ХОД" if my_turn else "ХОД ПРОТИВНИКА"
                color = GREEN if my_turn else RED
            
            status_text = big_font.render(status, True, color)
            screen.blit(status_text, (50, 20))
            
            # Счетчик
            hits_text = font.render(f"Попаданий: {hit_counter}", True, BLUE)
            screen.blit(hits_text, (50, 60))
        
        pygame.display.flip()
        clock.tick(30)
    
    client_socket.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()