import tkinter as tk
from tkinter import messagebox
import math
import threading
import time

# --- Constants ---
PLAYER_X = 'X'
PLAYER_O = 'O'
EMPTY = ' '
WIN_SCORE = 1000
LOSE_SCORE = -1000

# ==========================================
# GAME LOGIC CLASS (Dynamic Size N x N)
# ==========================================
class TicTacToeFIFO:
    def __init__(self, n):
        self.n = n  # Grid size (3, 4, or 5)
        self.board = [EMPTY] * (n * n)
        # Track moves: [oldest, ..., newest]
        self.move_queues = {PLAYER_X: [], PLAYER_O: []}

    def check_winner(self, player):
        n = self.n
        b = self.board
        
        # Check Rows
        for r in range(n):
            if all(b[r * n + c] == player for c in range(n)): return True
        
        # Check Columns
        for c in range(n):
            if all(b[r * n + c] == player for r in range(n)): return True
            
        # Check Diagonals
        if all(b[i * n + i] == player for i in range(n)): return True
        if all(b[i * n + (n - 1 - i)] == player for i in range(n)): return True
        
        return False

    def evaluate(self):
        if self.check_winner(PLAYER_O): return WIN_SCORE
        if self.check_winner(PLAYER_X): return LOSE_SCORE
        return 0

    def get_possible_moves(self):
        return [i for i, x in enumerate(self.board) if x == EMPTY]

    def make_move(self, pos, player):
        removed_pos = None
        self.board[pos] = player
        self.move_queues[player].append(pos)
        
        # FIFO Logic: Limit is N (e.g., 3 for 3x3, 4 for 4x4)
        if len(self.move_queues[player]) > self.n:
            removed_pos = self.move_queues[player].pop(0)
            self.board[removed_pos] = EMPTY
            
        return removed_pos

    def undo_move(self, pos, player, removed_pos):
        self.board[pos] = EMPTY
        self.move_queues[player].pop()
        
        if removed_pos is not None:
            self.board[removed_pos] = player
            self.move_queues[player].insert(0, removed_pos)

    def minimax(self, depth, is_maximizing, alpha, beta, max_depth):
        score = self.evaluate()
        if score == WIN_SCORE: return score - depth
        if score == LOSE_SCORE: return score + depth
        if depth >= max_depth: return score

        moves = self.get_possible_moves()
        if not moves: return 0

        if is_maximizing:
            best_val = -math.inf
            for move in moves:
                removed_pos = self.make_move(move, PLAYER_O)
                val = self.minimax(depth + 1, False, alpha, beta, max_depth)
                self.undo_move(move, PLAYER_O, removed_pos)
                best_val = max(best_val, val)
                alpha = max(alpha, best_val)
                if beta <= alpha: break
            return best_val
        else:
            best_val = math.inf
            for move in moves:
                removed_pos = self.make_move(move, PLAYER_X)
                val = self.minimax(depth + 1, True, alpha, beta, max_depth)
                self.undo_move(move, PLAYER_X, removed_pos)
                best_val = min(best_val, val)
                beta = min(beta, best_val)
                if beta <= alpha: break
            return best_val

    def find_best_move(self):
        best_val = -math.inf
        best_move = None
        moves = self.get_possible_moves()
        
        # Adjust depth based on board size to prevent lag
        # 3x3 -> Depth 5, 4x4 -> Depth 3, 5x5 -> Depth 2
        dynamic_depth = 5 if self.n == 3 else (3 if self.n == 4 else 2)
        
        for move in moves:
            removed_pos = self.make_move(move, PLAYER_O)
            move_val = self.minimax(0, False, -math.inf, math.inf, dynamic_depth)
            self.undo_move(move, PLAYER_O, removed_pos)
            
            if move_val > best_val:
                best_val = move_val
                best_move = move
        return best_move

# ==========================================
# GUI CLASS
# ==========================================
class TicTacToeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Tic-Tac-Toe")
        
        # State Variables
        self.n = 3             # Default Grid Size
        self.game_mode = 'AI'  # Default Mode
        self.game = None
        self.current_turn = PLAYER_X
        self.game_over = False
        self.buttons = []

        # Frames
        self.size_frame = tk.Frame(self.root)
        self.mode_frame = tk.Frame(self.root)
        self.game_frame = tk.Frame(self.root)

        # Start Flow
        self.setup_size_screen()
        self.setup_mode_screen()
        # Game board is setup dynamically later
        
        self.show_size_screen()

    # --- SCREEN 1: SIZE SELECTION ---
    def setup_size_screen(self):
        lbl = tk.Label(self.size_frame, text="Select Grid Size", font=('Arial', 20, 'bold'))
        lbl.pack(pady=30)
        
        sizes = [3, 4, 5]
        for s in sizes:
            btn = tk.Button(self.size_frame, text=f"{s} x {s}", font=('Arial', 14), width=20,
                            command=lambda val=s: self.select_size(val))
            btn.pack(pady=10)

    def select_size(self, size):
        self.n = size
        self.size_frame.pack_forget()
        self.mode_frame.pack(fill='both', expand=True)
        # Update window size based on grid
        dims = {3: "400x500", 4: "500x600", 5: "600x700"}
        self.root.geometry(dims.get(size, "400x500"))

    # --- SCREEN 2: MODE SELECTION ---
    def setup_mode_screen(self):
        lbl = tk.Label(self.mode_frame, text="Select Game Mode", font=('Arial', 20, 'bold'))
        lbl.pack(pady=30)
        
        btn_ai = tk.Button(self.mode_frame, text="Play vs AI", font=('Arial', 14), width=20,
                           command=lambda: self.start_game('AI'))
        btn_ai.pack(pady=10)
        
        btn_pvp = tk.Button(self.mode_frame, text="2 Player (PvP)", font=('Arial', 14), width=20,
                            command=lambda: self.start_game('PvP'))
        btn_pvp.pack(pady=10)
        
        btn_back = tk.Button(self.mode_frame, text="Back", command=self.show_size_screen)
        btn_back.pack(pady=20)

    def show_size_screen(self):
        self.mode_frame.pack_forget()
        self.game_frame.pack_forget()
        self.size_frame.pack(fill='both', expand=True)
        self.root.geometry("400x450")

    # --- SCREEN 3: GAME BOARD ---
    def start_game(self, mode):
        self.game_mode = mode
        self.mode_frame.pack_forget()
        self.game_frame.pack(fill='both', expand=True)
        
        # Initialize Logic
        self.game = TicTacToeFIFO(self.n)
        self.current_turn = PLAYER_X
        self.game_over = False
        
        # Build UI
        for widget in self.game_frame.winfo_children():
            widget.destroy()
            
        self.build_game_ui()
        self.update_status_text()

    def build_game_ui(self):
        top_lbl = tk.Label(self.game_frame, text=f"Match: {self.n}x{self.n} ({self.game_mode})", font=('Arial', 12))
        top_lbl.pack(pady=10)

        grid_frame = tk.Frame(self.game_frame)
        grid_frame.pack(pady=10)
        
        self.buttons = []
        for i in range(self.n * self.n):
            btn = tk.Button(grid_frame, text=EMPTY, font=('Arial', 18, 'bold'), 
                            width=4, height=2,
                            command=lambda idx=i: self.handle_click(idx))
            row = i // self.n
            col = i % self.n
            btn.grid(row=row, column=col, padx=3, pady=3)
            self.buttons.append(btn)

        self.status_label = tk.Label(self.game_frame, text="", font=('Arial', 14))
        self.status_label.pack(pady=10)

        # Bottom Controls
        btn_frame = tk.Frame(self.game_frame)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Restart", command=lambda: self.start_game(self.game_mode)).pack(side='left', padx=10)
        tk.Button(btn_frame, text="Main Menu", command=self.show_size_screen).pack(side='left', padx=10)
        
        rule_lbl = tk.Label(self.game_frame, text=f"Note: Max {self.n} pieces allowed per player.\nOldest removes on {self.n+1}th move.", fg="gray")
        rule_lbl.pack(pady=5)

    def update_gui_board(self):
        for i, mark in enumerate(self.game.board):
            self.buttons[i].config(text=mark, bg="SystemButtonFace")
            if mark == PLAYER_X: self.buttons[i].config(fg="blue")
            elif mark == PLAYER_O: self.buttons[i].config(fg="red")
            else: self.buttons[i].config(fg="black")

        # Highlight oldest piece
        current_queue = self.game.move_queues[self.current_turn]
        if len(current_queue) == self.n and not self.game_over:
            oldest = current_queue[0]
            self.buttons[oldest].config(bg="#ffcccb")

    def update_status_text(self):
        if self.game_over: return
        if self.game_mode == 'AI' and self.current_turn == PLAYER_O:
            self.status_label.config(text="AI is thinking...")
        else:
            p_name = "Player 1 (X)" if self.current_turn == PLAYER_X else "Player 2 (O)"
            self.status_label.config(text=f"{p_name}'s Turn")

    def handle_click(self, index):
        if self.game_over: return
        if self.game_mode == 'AI' and self.current_turn == PLAYER_O: return
        
        if self.game.board[index] != EMPTY:
            messagebox.showwarning("Invalid", "Spot taken!")
            return

        self.execute_move(index, self.current_turn)

        if self.check_win(self.current_turn): return
        
        self.toggle_turn()
        self.update_gui_board()
        self.update_status_text()

        if self.game_mode == 'AI' and self.current_turn == PLAYER_O:
            threading.Thread(target=self.ai_move_thread, daemon=True).start()

    def ai_move_thread(self):
        time.sleep(0.5)
        best_move = self.game.find_best_move()
        self.root.after(0, lambda: self.finish_ai_move(best_move))

    def finish_ai_move(self, move):
        if move is not None:
            self.execute_move(move, PLAYER_O)
            if self.check_win(PLAYER_O): return
            
        self.toggle_turn()
        self.update_gui_board()
        self.update_status_text()

    def execute_move(self, index, player):
        self.game.make_move(index, player)
        self.update_gui_board()

    def toggle_turn(self):
        self.current_turn = PLAYER_O if self.current_turn == PLAYER_X else PLAYER_X

    def check_win(self, player):
        if self.game.check_winner(player):
            self.game_over = True
            msg = "You Win!" if player == PLAYER_X and self.game_mode == 'AI' else \
                  ("AI Wins!" if player == PLAYER_O and self.game_mode == 'AI' else \
                  (f"{player} Wins!"))
            self.status_label.config(text=msg)
            messagebox.showinfo("Game Over", msg)
            return True
        return False

if __name__ == "__main__":
    root = tk.Tk()
    app = TicTacToeGUI(root)
    root.mainloop()