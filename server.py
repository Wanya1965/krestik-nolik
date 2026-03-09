import socket
import threading
import json
import time

# Настройки сервера
HOST = '127.0.0.1'
PORT = 65432

# Игроки
players = [None, None]  # Два игрока
players_ready = [False, False]  # Готовность игроков
players_ships = [{}, {}]  # Корабли игроков

# Игровое состояние
current_turn = 0  # Кто ходит (0 или 1)
game_started = False
game_over = False
winner = None

# Блокировка для потокобезопасности
lock = threading.Lock()

def handle_client(conn, addr, player_id):
    """Обработка подключения клиента"""
    global game_started, current_turn, game_over, winner
    
    print(f"Игрок {player_id + 1} подключен: {addr}")
    
    try:
        # Отправляем приветствие с ID игрока
        welcome_msg = {'type': 'welcome', 'player_id': player_id}
        conn.sendall((json.dumps(welcome_msg) + '\n').encode())
        
        buffer = ""
        while True:
            data = conn.recv(4096).decode()
            if not data:
                break
                
            buffer += data
            while '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                if message.strip():
                    try:
                        msg = json.loads(message)
                        print(f"Игрок {player_id + 1} отправил: {msg['type']}")
                        
                        with lock:
                            if msg['type'] == 'place_ships':
                                # Получаем корабли игрока
                                ships = msg['ships']
                                players_ships[player_id] = {(s['x'], s['y']): True for s in ships}
                                players_ready[player_id] = True
                                print(f"Игрок {player_id + 1} разместил {len(ships)} кораблей")
                                
                                # Подтверждаем получение
                                confirm_msg = {'type': 'placement_ok'}
                                conn.sendall((json.dumps(confirm_msg) + '\n').encode())
                                
                                # Проверяем, готовы ли оба игрока
                                if players_ready[0] and players_ready[1] and not game_started:
                                    print("ОБА ИГРОКА ГОТОВЫ! ЗАПУСК ИГРЫ...")
                                    game_started = True
                                    current_turn = 0  # Первый игрок начинает
                                    
                                    # Отправляем обоим игрокам сообщение о начале игры
                                    start_msg = {'type': 'game_start', 'first_player': current_turn}
                                    for p_conn in [players[0], players[1]]:
                                        if p_conn:
                                            p_conn.sendall((json.dumps(start_msg) + '\n').encode())
                                    
                                    print(f"Игра началась! Первый ходит Игрок {current_turn + 1}")
                            
                            elif msg['type'] == 'move':
                                if game_started and not game_over:
                                    x, y = msg['x'], msg['y']
                                    opponent_id = 1 - player_id
                                    
                                    # Проверяем попадание
                                    hit = (x, y) in players_ships[opponent_id]
                                    
                                    print(f"Игрок {player_id + 1} стреляет в ({x+1},{y+1}) - {'ПОПАДАНИЕ' if hit else 'ПРОМАХ'}")
                                    
                                    # Отправляем результат стрелявшему
                                    result_msg = {'type': 'move_result', 'x': x, 'y': y, 'hit': hit}
                                    conn.sendall((json.dumps(result_msg) + '\n').encode())
                                    
                                    # Отправляем противнику информацию о выстреле
                                    enemy_msg = {'type': 'enemy_move', 'x': x, 'y': y, 'hit': hit}
                                    players[opponent_id].sendall((json.dumps(enemy_msg) + '\n').encode())
                                    
                                    if hit:
                                        # Удаляем подбитый корабль
                                        del players_ships[opponent_id][(x, y)]
                                        
                                        # Проверяем победу
                                        if len(players_ships[opponent_id]) == 0:
                                            game_over = True
                                            winner = player_id
                                            print(f"ИГРОК {player_id + 1} ПОБЕДИЛ!")
                                            
                                            # Отправляем сообщение о победе обоим
                                            over_msg = {'type': 'game_over', 'winner': winner}
                                            for p_conn in [players[0], players[1]]:
                                                if p_conn:
                                                    p_conn.sendall((json.dumps(over_msg) + '\n').encode())
                                    else:
                                        # Меняем ход при промахе
                                        current_turn = opponent_id
                                        turn_msg = {'type': 'turn', 'player': current_turn}
                                        for p_conn in [players[0], players[1]]:
                                            if p_conn:
                                                p_conn.sendall((json.dumps(turn_msg) + '\n').encode())
                                        
                                        print(f"Теперь ходит Игрок {current_turn + 1}")
                                    
                    except json.JSONDecodeError as e:
                        print(f"Ошибка JSON: {e}")
                        
    except Exception as e:
        print(f"Ошибка с игроком {player_id + 1}: {e}")
    finally:
        conn.close()
        with lock:
            players[player_id] = None
            players_ready[player_id] = False
        print(f"Игрок {player_id + 1} отключился")

def main():
    """Запуск сервера"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(2)
    
    print(f"Сервер запущен на {HOST}:{PORT}")
    print("Ожидание игроков...")
    
    try:
        while True:
            conn, addr = server.accept()
            
            # Ищем свободное место для игрока
            with lock:
                player_id = None
                for i in range(2):
                    if players[i] is None:
                        players[i] = conn
                        player_id = i
                        break
            
            if player_id is not None:
                # Запускаем поток для обработки игрока
                thread = threading.Thread(target=handle_client, args=(conn, addr, player_id))
                thread.daemon = True
                thread.start()
            else:
                # Сервер полон
                conn.sendall((json.dumps({'type': 'error', 'message': 'Server is full'}) + '\n').encode())
                conn.close()
                
    except KeyboardInterrupt:
        print("\nСервер остановлен")
    finally:
        server.close()

if __name__ == "__main__":
    main()