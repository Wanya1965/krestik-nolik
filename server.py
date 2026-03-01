import socket
import threading
import json
import random

HOST = '127.0.0.1'
PORT = 65432

class GameServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(2)
        self.clients = []
        self.addresses = []
        self.player_ready = [False, False]
        self.player_ships = [[], []]
        self.player_turn = None
        self.game_started = False
        self.lock = threading.Lock()

    def start(self):
        print("Сервер запущен, ожидаем подключение двух игроков...")
        while len(self.clients) < 2:
            client_socket, addr = self.server_socket.accept()
            self.clients.append(client_socket)
            print(f"Игрок {len(self.clients)} подключен: {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket, len(self.clients)-1)).start()

    def handle_client(self, client, player_id):
        # Отправляем приветствие
        self.send_message(client, {'type': 'welcome', 'player_id': player_id})
        # Ждем от клиента сообщений
        while True:
            try:
                data = client.recv(4096)
                if not data:
                    break
                message = json.loads(data.decode())
                self.process_message(message, player_id)
            except:
                break
        print(f"Игрок {player_id + 1} отключился")
        self.clients.remove(client)
        client.close()

    def process_message(self, message, player_id):
        with self.lock:
            msg_type = message['type']
            if msg_type == 'ready':
                self.player_ready[player_id] = True
                print(f"Игрок {player_id+1} подтвердил готовность")
                if all(self.player_ready):
                    self.start_game()
            elif msg_type == 'place_ships':
                self.player_ships[player_id] = message['ships']
                print(f"Игрок {player_id+1} разместил корабли")
            elif msg_type == 'move':
                if self.game_started and self.player_turn == player_id:
                    x, y = message['x'], message['y']
                    self.process_move(player_id, x, y)

    def start_game(self):
        # Жеребьевка первого хода
        self.player_turn = random.randint(0, 1)
        self.game_started = True
        self.send_to_all({'type': 'start', 'first_player': self.player_turn})
        print("Игра началась, ходит игрок", self.player_turn + 1)

    def process_move(self, player_id, x, y):
        opponent_id = 1 - player_id
        # Проверка попадания
        hit = False
        for ship in self.player_ships[opponent_id]:
            if ship['x'] == x and ship['y'] == y:
                hit = True
                self.player_ships[opponent_id].remove(ship)
                break
        # Отправляем результат хода
        self.send_message(self.clients[player_id], {'type': 'move_result', 'hit': hit, 'x': x, 'y': y})
        self.send_message(self.clients[opponent_id], {'type': 'attacked', 'x': x, 'y': y, 'hit': hit})
        # Проверка победы
        if len(self.player_ships[opponent_id]) == 0:
            self.send_to_all({'type': 'game_over', 'winner': player_id})
            self.game_started = False
        else:
            # Передача хода
            self.player_turn = opponent_id
            self.send_to_all({'type': 'next_turn', 'player': self.player_turn})

    def send_message(self, client, message):
        try:
            client.sendall(json.dumps(message).encode())
        except:
            pass

    def send_to_all(self, message):
        for c in self.clients:
            self.send_message(c, message)

if __name__ == "__main__":
    server = GameServer()
    server.start()