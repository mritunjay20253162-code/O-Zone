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
MAX_DEPTH = 5 # Depth limit to prevent infinite loops during movement phase

# ==========================================
# GAME LOGIC CLASS (Backend)
# ==========================================
class TicTacToeVariantLogic:
    def __init__(self):
        self.board = [EMPTY] * 9
        
    def check_winner(self, player):
        win_conditions = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)
        ]
        return any(self.board[a] == self.board[b] == self.board[c] == player 
                   for a, b, c in win_conditions)

    def count_pieces(self, player):
        return self.board.count(player)

    def evaluate(self):
        if self.check_winner(AI): return WIN_SCORE
        if self.check_winner(HUMAN): return LOSE_SCORE
        
        score = 0
        # Heuristic: Slightly favor center
        if self.board[4] == AI: score += 10
        elif self.board[4] == HUMAN: score -= 10
        return score

    def get_possible_moves(self, player):
        pieces_on_board = self.count_pieces(player)
        empty_spots = [i for i, x in enumerate(self.board) if x == EMPTY]

        if pieces_on_board < 3:
            return empty_spots # Drop phase: return list of indices
        else:
            current_positions = [i for i, x in enumerate(self.board) if x == player]
            moves = []
            for start in current_positions:
                for end in empty_spots:
                    moves.append((start, end)) # Move phase: return list of (start, end) tuples
            return moves

    def make_move(self, move, player):
        if isinstance(move, int): self.board[move] = player
        else:
            self.board[move[0]] = EMPTY
            self.board[move[1]] = player

    def undo_move(self, move, player):
        if isinstance(move, int): self.board[move] = EMPTY
        else:
            self.board[move[1]] = EMPTY
            self.board[move[0]] = player

    def minimax(self, depth, is_maximizing, alpha, beta):
        score = self.evaluate()
        if score == WIN_SCORE: return score - depth
        if score == LOSE_SCORE: return score + depth
        if depth >= MAX_DEPTH: return score

        current_player = AI if is_maximizing else HUMAN
        moves = self.get_possible_moves(current_player)
        if not moves: return 0

        if is_maximizing:
            best_val = -math.inf
            for move in moves:
                self.make_move(move, AI)
                val = self.minimax(depth + 1, False, alpha, beta)
                self.undo_move(move, AI)
                best_val = max(best_val, val)
                alpha = max(alpha, best_val)
                if beta <= alpha: break
            return best_val
        else:
            best_val = math.inf
            for move in moves:
                self.make_move(move, HUMAN)
                val = self.minimax(depth + 1, True, alpha, beta)
                self.undo_move(move, HUMAN)
                best_val = min(best_val, val)
                beta = min(beta, best_val)
                if beta <= alpha: break
            return best_val

    def find_best_move(self):
        best_val = -math.inf
        best_move = None
        moves = self.get_possible_moves(AI)
        for move in moves:
            self.make_move(move, AI)
            # Slightly deeper search for the root move
            move_val = self.minimax(0, False, -math.inf, math.inf)
            self.undo_move(move, AI)
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
        self.root.title("3-Piece Tic-Tac-Toe Variant")
        self.game = TicTacToeVariantLogic()
        
        self.current_turn = HUMAN
        self.game_over = False
        # Used during movement phase to track the piece being moved
        self.selected_source_index = None 
        
        self.buttons = []
        self.setup_gui()
        self.update_status("Your Turn (Place a piece)")

    def setup_gui(self):
        # Main frame for board
        board_frame = tk.Frame(self.root)
        board_frame.pack(pady=10)

        # Create 3x3 grid of buttons
        for i in range(9):
            btn = tk.Button(board_frame, text=EMPTY, font=('Arial', 24, 'bold'), 
                            width=5, height=2,
                            command=lambda idx=i: self.handle_click(idx))
            row = i // 3
            col = i % 3
            btn.grid(row=row, column=col, padx=5, pady=5)
            self.buttons.append(btn)

        # Status Label
        self.status_label = tk.Label(self.root, text="", font=('Arial', 14))
        self.status_label.pack(pady=5)

        # Reset Button
        reset_btn = tk.Button(self.root, text="Restart Game", command=self.reset_game)
        reset_btn.pack(pady=10)

    def update_status(self, message):
        self.status_label.config(text=message)

    def reset_button_colors(self):
        for btn in self.buttons:
            btn.config(bg='SystemButtonFace') # Default color

    def handle_click(self, index):
        if self.game_over or self.current_turn != HUMAN:
            return

        human_pieces = self.game.count_pieces(HUMAN)

        # --- Phase 1: Placement (< 3 pieces) ---
        if human_pieces < 3:
            if self.game.board[index] == EMPTY:
                self.execute_human_move(index)
            else:
                messagebox.showwarning("Invalid Move", "Spot isn't empty!")

        # --- Phase 2: Movement (== 3 pieces) ---
        else:
            # Sub-phase 2a: Selecting source piece
            if self.selected_source_index is None:
                if self.game.board[index] == HUMAN:
                    self.selected_source_index = index
                    self.buttons[index].config(bg="yellow")
                    self.update_status("Select an empty spot to move to.")
                else:
                     messagebox.showwarning("Selection", "Select one of your 'X' pieces to move.")
            
            # Sub-phase 2b: Selecting destination
            else:
                move_tuple = (self.selected_source_index, index)
                possible_moves = self.game.get_possible_moves(HUMAN)

                if move_tuple in possible_moves:
                    self.execute_human_move(move_tuple)
                elif self.game.board[index] == HUMAN:
                    # Change selection to a different piece
                    self.reset_button_colors()
                    self.selected_source_index = index
                    self.buttons[index].config(bg="yellow")
                else:
                     # Cancel selection
                     self.reset_button_colors()
                     self.selected_source_index = None
                     self.update_status("Move cancelled. Select an 'X' to move.")

    def execute_human_move(self, move):
        self.game.make_move(move, HUMAN)
        self.update_gui_board()
        self.reset_button_colors()
        self.selected_source_index = None

        if self.check_game_end(HUMAN):
            return

        self.current_turn = AI
        self.update_status("AI is thinking...")
        # Start AI thread so GUI doesn't freeze
        threading.Thread(target=self.ai_turn_thread, daemon=True).start()

    def ai_turn_thread(self):
        # Small delay so it doesn't feel instantaneous
        time.sleep(0.5) 
        best_move = self.game.find_best_move()
        
        # Schedule the GUI update on the main thread
        self.root.after(0, lambda: self.execute_ai_move(best_move))

    def execute_ai_move(self, move):
        if move is not None:
            self.game.make_move(move, AI)
            self.update_gui_board()
            
            # Highlight AI's last move for clarity
            self.reset_button_colors()
            dest_idx = move if isinstance(move, int) else move[1]
            self.buttons[dest_idx].config(bg="lightblue")

            if self.check_game_end(AI):
                return
        
        self.current_turn = HUMAN
        phase_text = "Place a piece" if self.game.count_pieces(HUMAN) < 3 else "Select piece to move"
        self.update_status(f"Your Turn ({phase_text})")

    def update_gui_board(self):
        for i, mark in enumerate(self.game.board):
            self.buttons[i].config(text=mark)
            if mark == HUMAN:
                 self.buttons[i].config(fg="blue")
            elif mark == AI:
                 self.buttons[i].config(fg="red")

    def check_game_end(self, player):
        if self.game.check_winner(player):
            self.game_over = True
            msg = "You Win!" if player == HUMAN else "AI Wins!"
            self.update_status(msg)
            messagebox.showinfo("Game Over", msg)
            return True
        return False

    def reset_game(self):
        self.game = TicTacToeVariantLogic()
        self.current_turn = HUMAN
        self.game_over = False
        self.selected_source_index = None
        self.reset_button_colors()
        self.update_gui_board()
        self.update_status("Your Turn (Place a piece)")
        for btn in self.buttons:
            btn.config(fg="black") # Reset text color

if __name__ == "__main__":
    root = tk.Tk()
    gui = TicTacToeGUI(root)
    # Center the window roughly
    root.geometry("400x450")
    root.mainloop()