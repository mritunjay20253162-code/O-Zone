import tkinter as tk
from tkinter import messagebox, simpledialog
import socket
import threading
import time
import math

# --- Constants ---
PLAYER_X = 'X'
PLAYER_O = 'O'
EMPTY = ' '

# ==========================================
# 1. UNIVERSAL GAME LOGIC (2D Only)
# ==========================================
class GameLogic:
    def __init__(self, n):
        self.n = n
        self.total_cells = n * n
        self.board = [EMPTY] * self.total_cells
        self.move_queues = {PLAYER_X: [], PLAYER_O: []}

    def check_winner(self, player):
        n = self.n
        b = self.board
        # Rows
        for r in range(n):
            if all(b[r*n + c] == player for c in range(n)): return True
        # Columns
        for c in range(n):
            if all(b[r*n + c] == player for r in range(n)): return True
        # Diagonals
        if all(b[i*n + i] == player for i in range(n)): return True
        if all(b[i*n + (n-1-i)] == player for i in range(n)): return True
        return False

    def make_move(self, pos, player):
        self.board[pos] = player
        self.move_queues[player].append(pos)
        removed = None
        # FIFO Rule: Max pieces = N (e.g., 3 for 3x3)
        if len(self.move_queues[player]) > self.n:
            removed = self.move_queues[player].pop(0)
            self.board[removed] = EMPTY
        return removed

    def undo_move(self, pos, player, removed):
        self.board[pos] = EMPTY
        self.move_queues[player].pop()
        if removed is not None:
            self.board[removed] = player
            self.move_queues[player].insert(0, removed)

    def get_valid_moves(self):
        return [i for i, x in enumerate(self.board) if x == EMPTY]

    # --- Minimax for AI (Offline) ---
    def best_move_ai(self):
        best_val = -math.inf
        best_move = None
        # Depth adjustment: 5 for 3x3, 3 for 4x4, 2 for 5x5 (to prevent lag)
        depth_limit = 5 if self.n == 3 else (3 if self.n == 4 else 2)
        
        for move in self.get_valid_moves():
            rem = self.make_move(move, PLAYER_O)
            val = self.minimax(0, False, -math.inf, math.inf, depth_limit)
            self.undo_move(move, PLAYER_O, rem)
            if val > best_val:
                best_val = val
                best_move = move
        return best_move

    def minimax(self, d, is_max, alpha, beta, max_d):
        if self.check_winner(PLAYER_O): return 1000 - d
        if self.check_winner(PLAYER_X): return -1000 + d
        if d >= max_d: return 0
        
        moves = self.get_valid_moves()
        if not moves: return 0

        if is_max:
            max_eval = -math.inf
            for move in moves:
                rem = self.make_move(move, PLAYER_O)
                eval = self.minimax(d+1, False, alpha, beta, max_d)
                self.undo_move(move, PLAYER_O, rem)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha: break
            return max_eval
        else:
            min_eval = math.inf
            for move in moves:
                rem = self.make_move(move, PLAYER_X)
                eval = self.minimax(d+1, True, alpha, beta, max_d)
                self.undo_move(move, PLAYER_X, rem)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha: break
            return min_eval

# ==========================================
# 2. MAIN APP (GUI + Flow Control)
# ==========================================
class AllInOneApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ultimate Tic-Tac-Toe (2D Only)")
        self.root.geometry("500x600")
        
        # --- State Variables ---
        self.mode = None       # 'OFFLINE' or 'ONLINE'
        self.game = None
        self.socket = None
        self.is_host = False   # True if Host
        self.my_role = PLAYER_X # Default
        self.p1_name = "Player 1"
        self.p2_name = "Player 2"
        self.turn_lock = False # For online turns
        self.n = 3
        
        # --- UI Frames ---
        # Note: 'Off_Dim' removed
        self.frames = {}
        for f in ["MainMenu", "Off_Size", "Off_Mode", "NameEntry", "Online_Menu", "Online_Wait", "Game"]:
            self.frames[f] = tk.Frame(root)
            
        self.show_frame("MainMenu")
        self.setup_main_menu()

    def hide_all(self):
        for f in self.frames.values():
            f.pack_forget()

    def show_frame(self, name):
        self.hide_all()
        self.frames[name].pack(fill='both', expand=True)

    # ==========================
    # SCREEN 1: MAIN MENU
    # ==========================
    def setup_main_menu(self):
        f = self.frames["MainMenu"]
        for w in f.winfo_children(): w.destroy()
        
        tk.Label(f, text="Tic-Tac-Toe Master\n(FIFO Mode)", font=("Arial", 24, "bold")).pack(pady=40)
        tk.Button(f, text="Play Offline", font=("Arial", 16), width=20, 
                  command=self.start_offline_flow).pack(pady=10)
        tk.Button(f, text="Play Online", font=("Arial", 16), width=20, 
                  command=self.start_online_flow).pack(pady=10)

    # ==========================
    # OFFLINE FLOW
    # ==========================
    def start_offline_flow(self):
        self.mode = 'OFFLINE'
        # Skip Dimension, go straight to Size
        self.setup_off_size()
        self.show_frame("Off_Size")

    def setup_off_size(self):
        f = self.frames["Off_Size"]
        for w in f.winfo_children(): w.destroy()
        tk.Label(f, text="Select Grid Size", font=("Arial", 20)).pack(pady=30)
        for i in [3, 4, 5]:
            tk.Button(f, text=f"{i}x{i}", width=15, font=("Arial", 14), 
                      command=lambda x=i: self.select_size_offline(x)).pack(pady=5)
        
        if self.mode == 'OFFLINE':
            tk.Button(f, text="Back", command=lambda: self.show_frame("MainMenu")).pack(pady=20)

    def select_size_offline(self, size):
        self.n = size
        self.setup_off_mode()
        self.show_frame("Off_Mode")

    def setup_off_mode(self):
        f = self.frames["Off_Mode"]
        for w in f.winfo_children(): w.destroy()
        tk.Label(f, text="Select Opponent", font=("Arial", 20)).pack(pady=30)
        tk.Button(f, text="Vs AI (Computer)", width=20, font=("Arial", 14), 
                  command=lambda: self.prep_names('AI')).pack(pady=10)
        tk.Button(f, text="2 Player (Local)", width=20, font=("Arial", 14), 
                  command=lambda: self.prep_names('PvP')).pack(pady=10)
        tk.Button(f, text="Back", command=lambda: self.show_frame("Off_Size")).pack(pady=20)

    def prep_names(self, submode):
        self.off_submode = submode
        self.setup_name_screen()
        self.show_frame("NameEntry")

    # ==========================
    # ONLINE FLOW
    # ==========================
    def start_online_flow(self):
        self.mode = 'ONLINE'
        self.setup_online_menu()
        self.show_frame("Online_Menu")

    def setup_online_menu(self):
        f = self.frames["Online_Menu"]
        for w in f.winfo_children(): w.destroy()
        tk.Label(f, text="Online Multiplayer", font=("Arial", 20)).pack(pady=30)
        tk.Button(f, text="Host Game", width=15, font=("Arial", 14), command=self.host_game).pack(pady=10)
        tk.Button(f, text="Join Game", width=15, font=("Arial", 14), command=self.join_game).pack(pady=10)
        tk.Button(f, text="Back", command=lambda: self.show_frame("MainMenu")).pack(pady=20)

    def host_game(self):
        self.is_host = True
        self.my_role = PLAYER_X
        ip = socket.gethostbyname(socket.gethostname())
        self.show_wait_screen(f"Hosting on IP:\n{ip}\n\nWaiting for Joiner...")
        threading.Thread(target=self.server_thread, daemon=True).start()

    def join_game(self):
        self.is_host = False
        self.my_role = PLAYER_O
        ip = simpledialog.askstring("Connect", "Enter Host IP Address:")
        if ip:
            self.show_wait_screen(f"Connecting to {ip}...")
            threading.Thread(target=self.client_thread, args=(ip,), daemon=True).start()

    def show_wait_screen(self, msg):
        f = self.frames["Online_Wait"]
        for w in f.winfo_children(): w.destroy()
        tk.Label(f, text=msg, font=("Arial", 16)).pack(pady=100)
        self.show_frame("Online_Wait")

    # --- Networking ---
    def server_thread(self):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.bind(('0.0.0.0', 9999))
            srv.listen(1)
            conn, _ = srv.accept()
            self.socket = conn
            self.socket.send("CONNECTED".encode())
            self.root.after(0, lambda: self.prep_names('ONLINE'))
            self.listen_thread()
        except Exception as e:
            print(e)

    def client_thread(self, ip):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((ip, 9999))
            msg = self.socket.recv(1024).decode()
            if msg == "CONNECTED":
                self.root.after(0, lambda: self.prep_names('ONLINE'))
                self.listen_thread()
        except:
            self.root.after(0, lambda: messagebox.showerror("Error", "Connection Failed"))
            self.root.after(0, lambda: self.show_frame("Online_Menu"))

    def listen_thread(self):
        t = threading.Thread(target=self.network_listener, daemon=True)
        t.start()

    def network_listener(self):
        while True:
            try:
                data = self.socket.recv(1024).decode()
                if not data: break
                for msg in data.split(';'):
                    if msg: self.handle_network_msg(msg)
            except:
                break

    def handle_network_msg(self, msg):
        parts = msg.split(',')
        cmd = parts[0]
        
        if cmd == "NAME":
            self.p2_name = parts[1]
            if self.is_host:
                # Host now chooses Size
                self.root.after(0, self.setup_off_size)
                self.root.after(0, lambda: self.show_frame("Off_Size"))
                self.root.after(0, self.override_size_buttons_for_online)
            else:
                self.root.after(0, lambda: self.show_wait_screen("Waiting for Host to select size..."))

        elif cmd == "SIZE":
            self.n = int(parts[1])
            self.root.after(0, self.start_game)

        elif cmd == "MOVE":
            idx = int(parts[1])
            self.root.after(0, lambda: self.apply_remote_move(idx))

        elif cmd == "WIN":
            self.root.after(0, lambda: self.game_over_remote())

    def override_size_buttons_for_online(self):
        f = self.frames["Off_Size"]
        # Hide back button in online setup
        for w in f.winfo_children():
            if w['text'] == "Back": w.pack_forget()
            
        # Hijack size buttons
        for widget in f.winfo_children():
            if isinstance(widget, tk.Button) and "x" in widget['text']:
                size = int(widget['text'][0])
                widget.config(command=lambda s=size: self.send_size_config(s))

    def send_size_config(self, size):
        self.n = size
        self.socket.send(f"SIZE,{size};".encode())
        self.start_game()

    # ==========================
    # NAME ENTRY SCREEN
    # ==========================
    def setup_name_screen(self):
        f = self.frames["NameEntry"]
        for w in f.winfo_children(): w.destroy()
        
        tk.Label(f, text="Enter Name", font=("Arial", 18)).pack(pady=20)
        tk.Label(f, text="Your Name:").pack()
        e1 = tk.Entry(f); e1.pack(pady=5); e1.insert(0, "Player 1")
        
        e2 = None
        if self.mode == 'OFFLINE' and self.off_submode == 'PvP':
            tk.Label(f, text="Player 2 Name:").pack()
            e2 = tk.Entry(f); e2.pack(pady=5); e2.insert(0, "Player 2")
            
        tk.Button(f, text="Start Game" if self.mode=='OFFLINE' else "Ready", 
                  font=("Arial", 14), bg="#cfc",
                  command=lambda: self.submit_names(e1.get(), e2.get() if e2 else None)).pack(pady=20)

    def submit_names(self, n1, n2):
        self.p1_name = n1
        
        if self.mode == 'OFFLINE':
            if self.off_submode == 'PvP': self.p2_name = n2
            else: self.p2_name = "Computer AI"
            self.start_game()
        else:
            self.p1_name = n1 # Visuals only
            self.socket.send(f"NAME,{n1};".encode())
            self.show_wait_screen("Waiting for Opponent Name...")

    # ==========================
    # GAMEPLAY
    # ==========================
    def start_game(self):
        self.game = GameLogic(self.n)
        self.curr_player = PLAYER_X
        self.game_running = True
        
        if self.mode == 'ONLINE' and not self.is_host:
            self.turn_lock = True
        else:
            self.turn_lock = False

        self.setup_game_board()
        self.show_frame("Game")
        self.update_status()

    def setup_game_board(self):
        f = self.frames["Game"]
        for w in f.winfo_children(): w.destroy()
        
        info = f"{self.p1_name} (Me)" if self.mode=='ONLINE' else f"{self.p1_name} vs {self.p2_name}"
        tk.Label(f, text=info, font=("Arial", 12)).pack(pady=5)
        self.lbl_status = tk.Label(f, text="Game Start", font=("Arial", 14, "bold"))
        self.lbl_status.pack(pady=5)

        container = tk.Frame(f); container.pack(pady=10)
        self.btns = []

        for i in range(self.n * self.n):
            b = self.make_btn(container, i)
            b.grid(row=i//self.n, column=i%self.n, padx=2, pady=2)
            self.btns.append(b)
        
        tk.Button(f, text="Main Menu", command=lambda: self.show_frame("MainMenu")).pack(pady=10)
        tk.Label(f, text=f"FIFO Rule: Max {self.n} pieces allowed.\nOldest removed on next move.", fg="gray").pack()

    def make_btn(self, parent, idx):
        return tk.Button(parent, text=EMPTY, font=('Arial', 18, 'bold'), width=4, height=2,
                         command=lambda: self.on_click(idx))

    def on_click(self, idx):
        if not self.game_running: return
        if self.mode == 'ONLINE' and self.turn_lock: return
        if self.mode == 'OFFLINE' and self.off_submode == 'AI' and self.curr_player == PLAYER_O: return
        if self.game.board[idx] != EMPTY: return

        # Apply Move Locally
        self.game.make_move(idx, self.curr_player)
        self.update_ui()
        
        if self.mode == 'ONLINE':
            self.socket.send(f"MOVE,{idx};".encode())
            self.turn_lock = True

        if self.game.check_winner(self.curr_player):
            self.game_over_local(True)
            if self.mode == 'ONLINE': self.socket.send(f"WIN,{self.curr_player};".encode())
            return

        self.switch_turn()
        
        if self.mode == 'OFFLINE' and self.off_submode == 'AI' and self.curr_player == PLAYER_O:
            threading.Thread(target=self.ai_move, daemon=True).start()

    def apply_remote_move(self, idx):
        opp = PLAYER_O if self.my_role == PLAYER_X else PLAYER_X
        self.game.make_move(idx, opp)
        self.update_ui()
        self.switch_turn()
        self.turn_lock = False

    def switch_turn(self):
        self.curr_player = PLAYER_O if self.curr_player == PLAYER_X else PLAYER_X
        self.update_status()

    def update_status(self):
        if not self.game_running: return
        if self.mode == 'ONLINE':
            txt = "YOUR TURN" if not self.turn_lock else "OPPONENT'S TURN"
            col = "green" if not self.turn_lock else "red"
        else:
            p = self.p1_name if self.curr_player == PLAYER_X else self.p2_name
            txt = f"{p}'s Turn ({self.curr_player})"
            col = "blue" if self.curr_player == PLAYER_X else "red"
        self.lbl_status.config(text=txt, fg=col)

    def update_ui(self):
        for i, val in enumerate(self.game.board):
            self.btns[i].config(text=val, bg="#f0f0f0")
            if val == PLAYER_X: self.btns[i].config(fg="blue")
            elif val == PLAYER_O: self.btns[i].config(fg="red")
        
        q = self.game.move_queues[self.curr_player]
        if len(q) == self.n:
            self.btns[q[0]].config(bg="#ffcccb")

    def ai_move(self):
        time.sleep(0.5)
        move = self.game.best_move_ai()
        if move is not None:
            self.root.after(0, lambda: self.finalize_ai(move))

    def finalize_ai(self, move):
        self.game.make_move(move, PLAYER_O)
        self.update_ui()
        if self.game.check_winner(PLAYER_O):
            self.game_over_local(False)
            return
        self.switch_turn()

    def game_over_local(self, i_won):
        self.game_running = False
        msg = "You Won!" if i_won else "You Lost!"
        if self.mode == 'OFFLINE': 
             w = self.p1_name if self.curr_player == PLAYER_X else self.p2_name
             msg = f"{w} Wins!"
        
        self.lbl_status.config(text=msg, fg="purple")
        messagebox.showinfo("Game Over", msg)

    def game_over_remote(self):
        self.game_running = False
        self.lbl_status.config(text="You Lost!", fg="red")
        messagebox.showinfo("Game Over", "Opponent Won!")

if __name__ == "__main__":
    root = tk.Tk()
    app = AllInOneApp(root)
    root.mainloop()
    