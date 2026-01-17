import tkinter as tk
from tkinter import messagebox
import math
import threading
import time

# --- Constants ---
HUMAN = 'X'
AI = 'O'
EMPTY = ' '
WIN_SCORE = 1000
LOSE_SCORE = -1000
MAX_DEPTH = 5 

# ==========================================
# GAME LOGIC CLASS (Backend)
# ==========================================
class TicTacToeFIFO:
    def __init__(self):
        self.board = [EMPTY] * 9
        # Track the order of moves for each player: [oldest, middle, newest]
        self.move_queues = {HUMAN: [], AI: []}

    def check_winner(self, player):
        win_conditions = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)
        ]
        return any(self.board[a] == self.board[b] == self.board[c] == player 
                   for a, b, c in win_conditions)

    def evaluate(self):
        if self.check_winner(AI): return WIN_SCORE
        if self.check_winner(HUMAN): return LOSE_SCORE
        
        score = 0
        # Simple Heuristic: Center is valuable
        if self.board[4] == AI: score += 5
        elif self.board[4] == HUMAN: score -= 5
        return score

    def get_possible_moves(self):
        # In FIFO mode, you can always play in any currently empty spot.
        # You cannot play on your own piece even if it's about to be removed.
        return [i for i, x in enumerate(self.board) if x == EMPTY]

    def make_move(self, pos, player):
        """
        Places a piece. If > 3 pieces, removes the oldest.
        Returns the index of the removed piece (or None) to allow undoing.
        """
        removed_pos = None
        
        # 1. Place new piece
        self.board[pos] = player
        self.move_queues[player].append(pos)
        
        # 2. Check limit (FIFO removal)
        if len(self.move_queues[player]) > 3:
            removed_pos = self.move_queues[player].pop(0) # Remove oldest
            self.board[removed_pos] = EMPTY
            
        return removed_pos

    def undo_move(self, pos, player, removed_pos):
        """
        Reverses a move. Requires knowing which piece was auto-removed.
        """
        # 1. Remove the piece that was just added
        self.board[pos] = EMPTY
        self.move_queues[player].pop() # Remove newest
        
        # 2. Restore the piece that was auto-removed (if any)
        if removed_pos is not None:
            self.board[removed_pos] = player
            self.move_queues[player].insert(0, removed_pos) # Put back at start of queue

    def minimax(self, depth, is_maximizing, alpha, beta):
        score = self.evaluate()
        if score == WIN_SCORE: return score - depth
        if score == LOSE_SCORE: return score + depth
        if depth >= MAX_DEPTH: return score

        moves = self.get_possible_moves()
        
        # If board is somehow full (unlikely in FIFO but possible in standard), draw
        if not moves: return 0

        if is_maximizing:
            best_val = -math.inf
            for move in moves:
                # Store removed_pos so we can undo correctly
                removed_pos = self.make_move(move, AI)
                
                val = self.minimax(depth + 1, False, alpha, beta)
                
                self.undo_move(move, AI, removed_pos)
                
                best_val = max(best_val, val)
                alpha = max(alpha, best_val)
                if beta <= alpha: break
            return best_val
        else:
            best_val = math.inf
            for move in moves:
                removed_pos = self.make_move(move, HUMAN)
                
                val = self.minimax(depth + 1, True, alpha, beta)
                
                self.undo_move(move, HUMAN, removed_pos)
                
                best_val = min(best_val, val)
                beta = min(beta, best_val)
                if beta <= alpha: break
            return best_val

    def find_best_move(self):
        best_val = -math.inf
        best_move = None
        moves = self.get_possible_moves()
        
        for move in moves:
            removed_pos = self.make_move(move, AI)
            move_val = self.minimax(0, False, -math.inf, math.inf)
            self.undo_move(move, AI, removed_pos)
            
            if move_val > best_val:
                best_val = move_val
                best_move = move
        return best_move

# ==========================================
# GUI CLASS (Frontend)
# ==========================================
class TicTacToeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FIFO Tic-Tac-Toe (Auto-Remove Oldest)")
        self.game = TicTacToeFIFO()
        
        self.current_turn = HUMAN
        self.game_over = False
        self.buttons = []
        
        self.setup_gui()

    def setup_gui(self):
        board_frame = tk.Frame(self.root)
        board_frame.pack(pady=20)

        for i in range(9):
            btn = tk.Button(board_frame, text=EMPTY, font=('Arial', 24, 'bold'), 
                            width=5, height=2,
                            command=lambda idx=i: self.handle_click(idx))
            row = i // 3
            col = i % 3
            btn.grid(row=row, column=col, padx=5, pady=5)
            self.buttons.append(btn)

        self.status_label = tk.Label(self.root, text="Your Turn (X)", font=('Arial', 14))
        self.status_label.pack(pady=10)

        reset_btn = tk.Button(self.root, text="Restart Game", command=self.reset_game)
        reset_btn.pack(pady=5)
        
        instructions = tk.Label(self.root, text="Note: When you place a 4th piece,\nyour oldest piece is automatically removed.", fg="gray")
        instructions.pack(pady=10)

    def update_gui_board(self):
        # Update text and colors
        for i, mark in enumerate(self.game.board):
            self.buttons[i].config(text=mark, bg="SystemButtonFace") # Reset bg
            if mark == HUMAN:
                self.buttons[i].config(fg="blue")
            elif mark == AI:
                self.buttons[i].config(fg="red")
            else:
                self.buttons[i].config(fg="black")

        # Highlight the oldest piece (the one about to die) if 3 exist
        if len(self.game.move_queues[HUMAN]) == 3:
            oldest = self.game.move_queues[HUMAN][0]
            self.buttons[oldest].config(bg="#ffcccb") # Light red warning

    def handle_click(self, index):
        if self.game_over or self.current_turn != HUMAN: return
        
        # In FIFO, you can only click empty spots
        if self.game.board[index] != EMPTY:
            messagebox.showwarning("Invalid Move", "You must click an empty spot.")
            return

        # Execute Human Move
        self.game.make_move(index, HUMAN)
        self.update_gui_board()
        
        if self.check_end_condition(HUMAN): return

        # Trigger AI
        self.current_turn = AI
        self.status_label.config(text="AI is thinking...")
        threading.Thread(target=self.ai_turn_thread, daemon=True).start()

    def ai_turn_thread(self):
        time.sleep(0.6) # UX delay
        best_move = self.game.find_best_move()
        self.root.after(0, lambda: self.execute_ai_move(best_move))

    def execute_ai_move(self, move):
        if move is not None:
            self.game.make_move(move, AI)
            self.update_gui_board()
            if self.check_end_condition(AI): return
        
        self.current_turn = HUMAN
        self.status_label.config(text="Your Turn (X)")

    def check_end_condition(self, player):
        if self.game.check_winner(player):
            self.game_over = True
            winner = "You Win!" if player == HUMAN else "AI Wins!"
            self.status_label.config(text=winner)
            messagebox.showinfo("Game Over", winner)
            return True
        return False

    def reset_game(self):
        self.game = TicTacToeFIFO()
        self.current_turn = HUMAN
        self.game_over = False
        self.update_gui_board()
        self.status_label.config(text="Your Turn (X)")

if __name__ == "__main__":
    root = tk.Tk()
    gui = TicTacToeGUI(root)
    root.geometry("400x500")
    root.mainloop()