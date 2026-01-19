import tkinter as tk
from tkinter import messagebox, simpledialog
import socket
import threading
import time
import math
import random

# --- Constants ---
PLAYER_X = 'X'
PLAYER_O = 'O'
EMPTY = ' '
PORT = 9999  # Fixed Port for LAN

# ==========================================
# 1. GAME LOGIC (Brain)
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
        for r in range(n):
            if all(b[r*n + c] == player for c in range(n)): return True
        for c in range(n):
            if all(b[r*n + c] == player for r in range(n)): return True
        if all(b[i*n + i] == player for i in range(n)): return True
        if all(b[i*n + (n-1-i)] == player for i in range(n)): return True
        return False

    def make_move(self, pos, player):
        self.board[pos] = player
        self.move_queues[player].append(pos)
        removed = None
        if len(self.move_queues[player]) > self.n:
            removed = self.move_queues[player].pop(0)
            self.board[removed] = EMPTY
        return removed

    def get_valid_moves(self):
        return [i for i, x in enumerate(self.board) if x == EMPTY]

    # --- AI with Difficulty Levels ---
    def best_move_ai(self, difficulty):
        valid_moves = self.get_valid_moves()
        if not valid_moves: return None

        # --- LEVEL 1: EASY (Random) ---
        if difficulty == 'EASY':
            return random.choice(valid_moves)

        # --- LEVEL 2 & 3: MEDIUM & HARD (Minimax) ---
        best_val = -math.inf
        best_move = None
        
        # MEDIUM: Look only 2 moves ahead (Immediate threats/wins only)
        # HARD:   Look deep (Strategic)
        if difficulty == 'MEDIUM':
            depth_limit = 2
        else: # HARD
            depth_limit = 6 if self.n == 3 else (4 if self.n == 4 else 3)
        
        # Optimization: Sort moves to check Center first (Prunes the tree faster)
        center = self.total_cells // 2
        valid_moves.sort(key=lambda x: abs(x - center))

        for move in valid_moves:
            self.board[move] = PLAYER_O
            # Start Minimax
            val = self.minimax(0, False, -math.inf, math.inf, depth_limit)
            self.board[move] = EMPTY
            
            if val > best_val:
                best_val = val
                best_move = move
                
        return best_move

    def minimax(self, d, is_max, alpha, beta, max_d):
        if self.check_winner(PLAYER_O): return 1000 - d
        if self.check_winner(PLAYER_X): return -1000 + d
        
        # Heuristic check when depth limit reached
        if d >= max_d or not self.get_valid_moves():
            return self.evaluate_board()

        moves = self.get_valid_moves()
        
        if is_max:
            max_eval = -math.inf
            for move in moves:
                self.board[move] = PLAYER_O
                eval = self.minimax(d+1, False, alpha, beta, max_d)
                self.board[move] = EMPTY
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha: break
            return max_eval
        else:
            min_eval = math.inf
            for move in moves:
                self.board[move] = PLAYER_X
                eval = self.minimax(d+1, True, alpha, beta, max_d)
                self.board[move] = EMPTY
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha: break
            return min_eval

    def evaluate_board(self):
        score = 0
        center = self.n // 2
        center_idx = center * self.n + center
        if self.board[center_idx] == PLAYER_O: score += 15
        elif self.board[center_idx] == PLAYER_X: score -= 15

        lines = []
        for i in range(self.n):
            row = [self.board[i*self.n + c] for c in range(self.n)]
            col = [self.board[r*self.n + i] for r in range(self.n)]
            lines.extend([row, col])
        diag1 = [self.board[i*self.n + i] for i in range(self.n)]
        diag2 = [self.board[i*self.n + (self.n-1-i)] for i in range(self.n)]
        lines.extend([diag1, diag2])

        for line in lines:
            o_count = line.count(PLAYER_O)
            x_count = line.count(PLAYER_X)
            empty_count = line.count(EMPTY)

            if o_count == self.n - 1 and empty_count == 1: score += 50
            elif x_count == self.n - 1 and empty_count == 1: score -= 50
            
            if o_count == 1 and x_count == 0: score += 5
            elif x_count == 1 and o_count == 0: score -= 5

        return score

# ==========================================
# 2. GUI APP
# ==========================================
class AllInOneApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tic-Tac-Toe LAN Multiplayer")
        self.root.geometry("500x700") 
        
        self.mode = None
        self.game = None
        self.socket = None
        self.is_host = False
        self.my_role = PLAYER_X
        self.p1_name = "Player 1"
        self.p2_name = "Player 2"
        self.turn_lock = False
        self.n = 3
        
        self.score_x = 0
        self.score_o = 0
        
        # New variable for AI difficulty
        self.ai_difficulty = 'HARD' 
        
        self.frames = {}
        # Added "Off_Diff" to list
        frame_list = ["MainMenu", "Off_Size", "Off_Mode", "Off_Diff", "NameEntry", "Online_Menu", "Online_Wait", "Game"]
        for f in frame_list:
            self.frames[f] = tk.Frame(root)
            
        self.show_frame("MainMenu")
        self.setup_main_menu()

    def hide_all(self):
        for f in self.frames.values(): f.pack_forget()

    def show_frame(self, name):
        self.hide_all()
        self.frames[name].pack(fill='both', expand=True)

    # --- MAIN MENU ---
    def setup_main_menu(self):
        f = self.frames["MainMenu"]
        for w in f.winfo_children(): w.destroy()
        
        tk.Label(f, text="Tic-Tac-Toe\n(FIFO Mode)", font=("Arial", 24, "bold")).pack(pady=40)
        tk.Button(f, text="Play Offline", font=("Arial", 16), width=20, 
                  command=self.start_offline_flow).pack(pady=10)
        tk.Button(f, text="Play Local LAN", font=("Arial", 16), width=20, 
                  command=self.start_online_flow).pack(pady=10)

    # --- OFFLINE FLOW ---
    def start_offline_flow(self):
        self.mode = 'OFFLINE'
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
        
        # Vs AI -> Go to Difficulty Select
        tk.Button(f, text="Vs AI", width=20, font=("Arial", 14), 
                  command=self.goto_difficulty_select).pack(pady=10)
        
        # PvP -> Go straight to Names
        tk.Button(f, text="2 Player (Local)", width=20, font=("Arial", 14), 
                  command=lambda: self.prep_names('PvP')).pack(pady=10)
        
        tk.Button(f, text="Back", command=lambda: self.show_frame("Off_Size")).pack(pady=20)

    # --- NEW: DIFFICULTY SELECTION SCREEN ---
    def goto_difficulty_select(self):
        self.off_submode = 'AI'
        self.setup_off_diff()
        self.show_frame("Off_Diff")

    def setup_off_diff(self):
        f = self.frames["Off_Diff"]
        for w in f.winfo_children(): w.destroy()
        tk.Label(f, text="Select AI Difficulty", font=("Arial", 20)).pack(pady=30)
        
        tk.Button(f, text="Easy (Random)", width=20, bg="#ccffcc", font=("Arial", 14), 
                  command=lambda: self.set_difficulty('EASY')).pack(pady=10)
        
        tk.Button(f, text="Medium (Smartish)", width=20, bg="#ffffcc", font=("Arial", 14), 
                  command=lambda: self.set_difficulty('MEDIUM')).pack(pady=10)
        
        tk.Button(f, text="Hard (Unbeatable)", width=20, bg="#ffcccc", font=("Arial", 14), 
                  command=lambda: self.set_difficulty('HARD')).pack(pady=10)
        
        tk.Button(f, text="Back", command=lambda: self.show_frame("Off_Mode")).pack(pady=20)

    def set_difficulty(self, diff):
        self.ai_difficulty = diff
        self.prep_names('AI')

    def prep_names(self, submode):
        self.off_submode = submode
        self.setup_name_screen()
        self.show_frame("NameEntry")

    # --- ONLINE (LAN) FLOW ---
    def start_online_flow(self):
        self.mode = 'ONLINE'
        self.setup_online_menu()
        self.show_frame("Online_Menu")

    def setup_online_menu(self):
        f = self.frames["Online_Menu"]
        for w in f.winfo_children(): w.destroy()
        tk.Label(f, text="Local LAN Multiplayer", font=("Arial", 20)).pack(pady=30)
        tk.Button(f, text="Host Game", width=15, font=("Arial", 14), command=self.host_game).pack(pady=10)
        tk.Button(f, text="Join Game", width=15, font=("Arial", 14), command=self.join_game).pack(pady=10)
        tk.Button(f, text="Back", command=lambda: self.show_frame("MainMenu")).pack(pady=20)

    def host_game(self):
        self.is_host = True
        self.my_role = PLAYER_X
        threading.Thread(target=self.server_thread, daemon=True).start()
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "Unknown"
        self.show_wait_screen(f"Hosting on IP: {local_ip}\n\nWaiting for Player to Join...")

    def join_game(self):
        self.is_host = False
        self.my_role = PLAYER_O
        ip_info = simpledialog.askstring("Connect", "Enter Host IP Address (e.g., 192.168.1.5):")
        if not ip_info: return
        self.show_wait_screen(f"Connecting to {ip_info}...")
        threading.Thread(target=self.client_thread, args=(ip_info,), daemon=True).start()

    def show_wait_screen(self, msg):
        f = self.frames["Online_Wait"]
        for w in f.winfo_children(): w.destroy()
        tk.Label(f, text=msg, font=("Arial", 14)).pack(pady=50)
        tk.Button(f, text="Cancel / Back", command=self.cancel_online_wait).pack(pady=20)
        self.show_frame("Online_Wait")

    def cancel_online_wait(self):
        if self.socket:
            try: self.socket.close()
            except: pass
            self.socket = None
        self.show_frame("Online_Menu")

    # --- NETWORKING ---
    def server_thread(self):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.bind(('0.0.0.0', PORT))
            srv.listen(1)
            conn, _ = srv.accept()
            self.socket = conn
            self.socket.send("CONNECTED".encode())
            self.root.after(0, lambda: self.prep_names('ONLINE'))
            self.listen_thread()
        except Exception: pass

    def client_thread(self, ip):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((ip, PORT))
            msg = self.socket.recv(1024).decode()
            if msg == "CONNECTED":
                self.root.after(0, lambda: self.prep_names('ONLINE'))
                self.listen_thread()
        except:
            self.root.after(0, lambda: messagebox.showerror("Error", "Connection Failed. Check IP."))
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
            except: break

    def handle_network_msg(self, msg):
        parts = msg.split(',')
        cmd = parts[0]
        if cmd == "NAME":
            self.p2_name = parts[1]
            if self.is_host:
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
            winner_char = parts[1] 
            self.root.after(0, lambda: self.game_over_remote(winner_char))
        elif cmd == "RESTART":
            self.root.after(0, self.reset_match)

    def override_size_buttons_for_online(self):
        f = self.frames["Off_Size"]
        for w in f.winfo_children():
            if w['text'] == "Back": w.pack_forget()
        for widget in f.winfo_children():
            if isinstance(widget, tk.Button) and "x" in widget['text']:
                size = int(widget['text'][0])
                widget.config(command=lambda s=size: self.send_size_config(s))

    def send_size_config(self, size):
        self.n = size
        self.socket.send(f"SIZE,{size};".encode())
        self.start_game()

    # --- NAME SCREEN ---
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
            
        tk.Button(f, text="Start / Ready", font=("Arial", 14), bg="#cfc",
                  command=lambda: self.submit_names(e1.get(), e2.get() if e2 else None)).pack(pady=20)
        
        # Back Logic updated to return to correct screen
        tk.Button(f, text="Back", command=self.go_back_from_names).pack(pady=10)

    def go_back_from_names(self):
        if self.mode == 'OFFLINE':
            if self.off_submode == 'AI':
                self.show_frame("Off_Diff") # Go back to difficulty
            else:
                self.show_frame("Off_Mode")
        else:
            if self.socket:
                try: self.socket.close()
                except: pass
                self.socket = None
            self.show_frame("Online_Menu")

    def submit_names(self, n1, n2):
        self.p1_name = n1
        if self.mode == 'OFFLINE':
            if self.off_submode == 'AI':
                self.p2_name = f"AI ({self.ai_difficulty.capitalize()})"
            else:
                self.p2_name = n2
            self.start_game()
        else:
            self.socket.send(f"NAME,{n1};".encode())
            self.show_wait_screen("Waiting for Opponent Name...")

    # --- GAMEPLAY ---
    def start_game(self):
        if self.game is None: 
            self.score_x = 0
            self.score_o = 0
        self.reset_match()
        self.show_frame("Game")

    def reset_match(self):
        self.game = GameLogic(self.n)
        if self.mode == 'OFFLINE':
            self.curr_player = random.choice([PLAYER_X, PLAYER_O])
        else:
            self.curr_player = PLAYER_X
        
        self.game_running = True
        self.turn_lock = (self.mode == 'ONLINE' and not self.is_host)
        
        self.setup_game_board()
        self.update_status()

        if self.mode == 'OFFLINE' and self.off_submode == 'AI' and self.curr_player == PLAYER_O:
            threading.Thread(target=self.ai_move, daemon=True).start()

    def setup_game_board(self):
        f = self.frames["Game"]
        for w in f.winfo_children(): w.destroy()
        
        score_text = f"Score: {self.score_x} - {self.score_o}"
        tk.Label(f, text=score_text, font=("Arial", 20, "bold"), fg="#333").pack(pady=5)
        
        info = f"{self.p1_name} (Me)" if self.mode=='ONLINE' else f"{self.p1_name} vs {self.p2_name}"
        tk.Label(f, text=info, font=("Arial", 12)).pack(pady=2)
        
        self.lbl_status = tk.Label(f, text="Game Start", font=("Arial", 14, "bold"))
        self.lbl_status.pack(pady=5)
        
        container = tk.Frame(f); container.pack(pady=10)
        self.btns = []
        for i in range(self.n * self.n):
            b = tk.Button(container, text=EMPTY, font=('Arial', 18, 'bold'), width=4, height=2,
                          command=lambda idx=i: self.on_click(idx))
            b.grid(row=i//self.n, column=i%self.n, padx=2, pady=2)
            self.btns.append(b)
        
        tk.Button(f, text="Restart Match", command=self.trigger_restart_confirm).pack(pady=5)
        tk.Button(f, text="Main Menu", command=self.quit_to_menu).pack(pady=5)
        tk.Label(f, text=f"FIFO Rule: Max {self.n} pieces.", fg="gray").pack()

    def quit_to_menu(self):
        if self.socket:
            try: self.socket.close()
            except: pass
            self.socket = None
        self.game = None
        self.show_frame("MainMenu")

    def on_click(self, idx):
        if not self.game_running: return
        if self.mode == 'ONLINE' and self.turn_lock: return
        if self.mode == 'OFFLINE' and self.off_submode == 'AI' and self.curr_player == PLAYER_O: return
        if self.game.board[idx] != EMPTY: return

        self.game.make_move(idx, self.curr_player)
        self.update_ui()
        
        if self.mode == 'ONLINE':
            self.socket.send(f"MOVE,{idx};".encode())
            self.turn_lock = True

        if self.game.check_winner(self.curr_player):
            self.game_over_local(self.curr_player)
            if self.mode == 'ONLINE': 
                self.socket.send(f"WIN,{self.curr_player};".encode())
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
        if len(q) == self.n: self.btns[q[0]].config(bg="#ffcccb")

    def ai_move(self):
        time.sleep(0.5)
        # Pass the selected difficulty to the AI logic
        move = self.game.best_move_ai(self.ai_difficulty)
        if move is not None: self.root.after(0, lambda: self.finalize_ai(move))

    def finalize_ai(self, move):
        self.game.make_move(move, PLAYER_O)
        self.update_ui()
        if self.game.check_winner(PLAYER_O):
            self.game_over_local(PLAYER_O)
            return
        self.switch_turn()

    def game_over_local(self, winner_char):
        self.game_running = False
        if winner_char == PLAYER_X: self.score_x += 1
        else: self.score_o += 1
        msg = f"Player {winner_char} Wins!"
        self.lbl_status.config(text=msg, fg="purple")
        play_again = messagebox.askyesno("Game Over", f"{msg}\n\nPlay Again?")
        if play_again: self.trigger_restart()

    def game_over_remote(self, winner_char):
        self.game_running = False
        if winner_char == PLAYER_X: self.score_x += 1
        else: self.score_o += 1
        self.lbl_status.config(text="Game Over", fg="red")
        messagebox.showinfo("Game Over", f"Player {winner_char} Won!")

    def trigger_restart_confirm(self):
        if messagebox.askyesno("Restart", "Are you sure you want to restart?"):
            self.trigger_restart()

    def trigger_restart(self):
        self.reset_match()
        if self.mode == 'ONLINE':
            self.socket.send("RESTART;".encode())

if __name__ == "__main__":
    root = tk.Tk()
    app = AllInOneApp(root)
    root.mainloop()