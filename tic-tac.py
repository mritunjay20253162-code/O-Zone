import tkinter as tk
from tkinter import messagebox, simpledialog
import socket
import threading
import time
import math
import random

PLAYER_X = 'X'
PLAYER_O = 'O'
EMPTY = ' '
PORT = 9999

# --- COLOR PALETTE (Dracula/Modern Dark) ---
COLORS = {
    'bg': '#1e1e2e',
    'fg': '#cdd6f4',
    'btn_bg': '#313244',
    'btn_hover': '#45475a',
    'btn_text': '#ffffff',
    'accent_x': '#89b4fa',  # Blue
    'accent_o': '#f38ba8',  # Red/Pink
    'accent_1': '#a6e3a1',  # Green
    'accent_2': '#fab387',  # Orange
    'fifo_fade': '#585b70',
    'overlay_bg': '#282a36',
    'win_gold': '#f1c40f'
}

FONTS = {
    'header': ("Segoe UI", 24, "bold"),
    'title_huge': ("Segoe UI", 36, "bold"),
    'sub': ("Segoe UI", 14),
    'rules': ("Segoe UI", 11),
    'btn': ("Segoe UI", 12, "bold"),
    'game': ("Segoe UI", 20, "bold")
}

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

    def best_move_ai(self, difficulty):
        valid_moves = self.get_valid_moves()
        if not valid_moves: return None

        if difficulty == 'EASY':
            return random.choice(valid_moves)

        best_val = -math.inf
        best_move = None
        
        if difficulty == 'MEDIUM':
            depth_limit = 2
        else: 
            depth_limit = 6 if self.n == 3 else (4 if self.n == 4 else 3)
        
        center = self.total_cells // 2
        valid_moves.sort(key=lambda x: abs(x - center))

        for move in valid_moves:
            self.board[move] = PLAYER_O
            val = self.minimax(0, False, -math.inf, math.inf, depth_limit)
            self.board[move] = EMPTY
            if val > best_val:
                best_val = val
                best_move = move
        return best_move

    def minimax(self, d, is_max, alpha, beta, max_d):
        if self.check_winner(PLAYER_O): return 1000 - d
        if self.check_winner(PLAYER_X): return -1000 + d
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
        return score

class HoverButton(tk.Button):
    def __init__(self, master, **kw):
        self.default_bg = kw.get('bg', COLORS['btn_bg'])
        self.hover_bg = kw.pop('hover_bg', COLORS['btn_hover'])
        
        kw.setdefault('activebackground', self.hover_bg)
        kw.setdefault('activeforeground', COLORS['fg'])
        kw.setdefault('bg', self.default_bg)
        kw.setdefault('fg', COLORS['btn_text'])
        kw.setdefault('font', FONTS['btn'])
        kw.setdefault('relief', tk.FLAT)
        kw.setdefault('bd', 0)
        kw.setdefault('cursor', 'hand2')
        
        super().__init__(master, **kw)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['bg'] = self.hover_bg

    def on_leave(self, e):
        self['bg'] = self.default_bg

class ModernApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FIFO Tic-Tac-Toe | MNNIT Project")
        self.root.geometry("600x750")
        self.root.configure(bg=COLORS['bg'])
        
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
        self.ai_difficulty = 'HARD'
        
        # Sync Flags
        self.name_submitted = False
        self.opponent_name_received = False
        
        self.animating = False
        self.particles = []

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.frames = {}
        frame_list = ["Welcome", "MainMenu", "Off_Size", "Off_Mode", 
                      "Off_Diff", "NameEntry", "Online_Menu", "Online_Wait", "Game"]
        
        for f_name in frame_list:
            frame = tk.Frame(root, bg=COLORS['bg'])
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[f_name] = frame
        self.current_frame_name = None
        
        self.show_frame("Welcome")

    def show_frame(self, name):
        if self.current_frame_name == name: return
        
        if name != "Welcome": self.animating = False

        if name == "Welcome": self.setup_welcome_screen()
        elif name == "MainMenu": self.setup_main_menu()
        
        screen_order = [
            "Welcome", "MainMenu", "Off_Size", "Off_Mode", 
            "Off_Diff", "NameEntry", "Online_Menu", "Online_Wait", "Game"
        ]
        
        effect = "left" 
        
        if self.current_frame_name is None:
            self.frames[name].tkraise()
            self.current_frame_name = name
            if name == "Welcome": self.setup_welcome_screen()
            return

        try:
            old_idx = screen_order.index(self.current_frame_name)
            new_idx = screen_order.index(name)
        except ValueError:
            old_idx, new_idx = 0, 0

        if name == "Game":
            effect = "up"
        elif name == "Welcome":
            effect = "down"
        elif new_idx > old_idx:
            effect = "left"
        elif new_idx < old_idx:
            effect = "right"

        prev_frame = self.frames[self.current_frame_name]
        next_frame = self.frames[name]
        self.animate_switch(prev_frame, next_frame, name, effect)

    def animate_switch(self, prev_frame, next_frame, next_name, effect):
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        if effect == "left":
            next_frame.place(x=width, y=0, width=width, height=height)
        elif effect == "right":
            next_frame.place(x=-width, y=0, width=width, height=height)
        elif effect == "up":
            next_frame.place(x=0, y=height, width=width, height=height)
        elif effect == "down":
            next_frame.place(x=0, y=-height, width=width, height=height)
            
        prev_frame.place(x=0, y=0, width=width, height=height)
        next_frame.tkraise()

        def slide(step=0):
            speed = 45 
            
            offset = step * speed
            
            finished = False
            
            if effect == "left":
                new_prev_x = -offset
                new_next_x = width - offset
                if new_next_x <= 0: finished = True
                else:
                    prev_frame.place(x=new_prev_x, y=0)
                    next_frame.place(x=new_next_x, y=0)

            elif effect == "right":
                new_prev_x = offset
                new_next_x = -width + offset
                if new_next_x >= 0: finished = True
                else:
                    prev_frame.place(x=new_prev_x, y=0)
                    next_frame.place(x=new_next_x, y=0)

            elif effect == "up":
                new_prev_y = -offset
                new_next_y = height - offset
                if new_next_y <= 0: finished = True
                else:
                    prev_frame.place(x=0, y=new_prev_y)
                    next_frame.place(x=0, y=new_next_y)

            elif effect == "down":
                new_prev_y = offset
                new_next_y = -height + offset
                if new_next_y >= 0: finished = True
                else:
                    prev_frame.place(x=0, y=new_prev_y)
                    next_frame.place(x=0, y=new_next_y)

            if finished:
                prev_frame.place_forget()
                next_frame.place(x=0, y=0, width=width, height=height)
                
                next_frame.grid(row=0, column=0, sticky="nsew")
                
                self.current_frame_name = next_name
                
                if next_name == "Welcome":
                    self.animating = True
                    self.animate_background()
            else:
                self.root.after(10, lambda: slide(step+1))

        slide()
    def clear_frame(self, frame_name):
        for widget in self.frames[frame_name].winfo_children():
            widget.destroy()
        return self.frames[frame_name]

    def setup_welcome_screen(self):
        f = self.clear_frame("Welcome")
        
        self.bg_canvas = tk.Canvas(f, bg=COLORS['bg'], highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True)
        
        self.particles = []
        for _ in range(30):
            self.particles.append(self.create_particle())
            
        self.animating = True
        self.animate_background()

        overlay = tk.Frame(f, bg=COLORS['overlay_bg'], padx=40, pady=40, bd=2, relief=tk.GROOVE)
        overlay.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(overlay, text="FIFO\nTIC-TAC-TOE", font=FONTS['title_huge'], 
                 bg=COLORS['overlay_bg'], fg=COLORS['accent_x'], justify="center").pack(pady=(0, 10))
        
        tk.Label(overlay, text="MNNIT Project Edition", font=("Segoe UI", 12, "italic"), 
                 bg=COLORS['overlay_bg'], fg=COLORS['accent_o']).pack(pady=(0, 30))

        rules_frame = tk.Frame(overlay, bg=COLORS['overlay_bg'])
        rules_frame.pack(fill="x", pady=20)
        
        tk.Label(rules_frame, text="GAME RULES:", font=FONTS['btn'], 
                 bg=COLORS['overlay_bg'], fg=COLORS['accent_1'], anchor="w").pack(fill="x")
        
        rules = [
            "• Objective: Get N symbols in a row/col/diag.",
            f"• FIFO Rule: Max N pieces per player allowed.",
            "• Placing the (N+1)th piece removes your oldest.",
            "• Strategy: Trap opponent while saving your pieces!"
        ]
        for rule in rules:
            tk.Label(rules_frame, text=rule, font=FONTS['rules'], 
                     bg=COLORS['overlay_bg'], fg=COLORS['fg'], anchor="w", justify="left").pack(fill="x", pady=2)

        HoverButton(overlay, text="ENTER GAME >>>", width=20, pady=10, 
                    bg=COLORS['accent_1'], fg=COLORS['bg'], hover_bg="#89e389", 
                    font=("Segoe UI", 14, "bold"),
                    command=lambda: self.show_frame("MainMenu")).pack(pady=(40, 10))

    def create_particle(self):
        text = random.choice(['X', 'O'])
        color = COLORS['accent_x'] if text == 'X' else COLORS['accent_o']
        size = random.randint(20, 60)
        font = ("Arial", size, "bold")
        
        side = random.choice(['top', 'bottom', 'left', 'right'])
        w = self.root.winfo_width() or 600
        h = self.root.winfo_height() or 750
        
        if side == 'top': 
            x, y = random.randint(0, w), -50
            dx, dy = random.uniform(-1, 1), random.uniform(1, 4)
        elif side == 'bottom': 
            x, y = random.randint(0, w), h+50
            dx, dy = random.uniform(-1, 1), random.uniform(-4, -1)
        elif side == 'left': 
            x, y = -50, random.randint(0, h)
            dx, dy = random.uniform(1, 4), random.uniform(-1, 1)
        else:
            x, y = w+50, random.randint(0, h)
            dx, dy = random.uniform(-4, -1), random.uniform(-1, 1)

        item = self.bg_canvas.create_text(x, y, text=text, font=font, fill=color, tag="particle")
        return {'item': item, 'dx': dx, 'dy': dy}

    def animate_background(self):
        if not self.animating: return
        
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        
        particles_to_remove = []
        for p in self.particles:
            self.bg_canvas.move(p['item'], p['dx'], p['dy'])
            pos = self.bg_canvas.coords(p['item'])
            
            if (pos[0] < -100 or pos[0] > w + 100 or 
                pos[1] < -100 or pos[1] > h + 100):
                particles_to_remove.append(p)
                
        for p in particles_to_remove:
            self.bg_canvas.delete(p['item'])
            self.particles.remove(p)
            self.particles.append(self.create_particle())

        self.root.after(30, self.animate_background)

    def setup_main_menu(self):
        f = self.clear_frame("MainMenu")
        
        tk.Label(f, text="MAIN MENU", font=FONTS['header'], 
                 bg=COLORS['bg'], fg=COLORS['accent_1']).pack(pady=(80, 40))
        
        HoverButton(f, text="PLAY OFFLINE", width=25, pady=12, font=FONTS['btn'],
                    command=self.start_offline_flow).pack(pady=15)
        
        HoverButton(f, text="LAN MULTIPLAYER", width=25, pady=12, font=FONTS['btn'],
                    command=self.start_online_flow).pack(pady=15)
        
        HoverButton(f, text="← Back to Welcome", width=20, bg="#45475a",
                    command=lambda: self.show_frame("Welcome")).pack(pady=50)


    def start_offline_flow(self):
        self.mode = 'OFFLINE'
        self.setup_off_size()
        self.show_frame("Off_Size")

    def setup_off_size(self):
        f = self.clear_frame("Off_Size")
        tk.Label(f, text="SELECT GRID SIZE", font=FONTS['header'], 
                 bg=COLORS['bg'], fg=COLORS['fg']).pack(pady=50)
        
        for i in [3, 4, 5]:
            HoverButton(f, text=f"{i} x {i}", width=15, pady=5, 
                        command=lambda x=i: self.select_size_offline(x)).pack(pady=10)
        
        HoverButton(f, text="← Back", width=10, bg="#45475a", 
                    command=lambda: self.show_frame("MainMenu")).pack(pady=30)

    def select_size_offline(self, size):
        self.n = size
        self.setup_off_mode()
        self.show_frame("Off_Mode")

    def setup_off_mode(self):
        f = self.clear_frame("Off_Mode")
        tk.Label(f, text="CHOOSE OPPONENT", font=FONTS['header'], 
                 bg=COLORS['bg'], fg=COLORS['fg']).pack(pady=50)
        
        HoverButton(f, text="VS AI (Computer)", width=20, pady=10, 
                    command=self.goto_difficulty_select).pack(pady=10)
        
        HoverButton(f, text="VS FRIEND (Local)", width=20, pady=10, 
                    command=lambda: self.prep_names('PvP')).pack(pady=10)
        
        HoverButton(f, text="← Back", width=10, bg="#45475a", 
                    command=lambda: self.show_frame("Off_Size")).pack(pady=30)

    def goto_difficulty_select(self):
        self.off_submode = 'AI'
        self.setup_off_diff()
        self.show_frame("Off_Diff")

    def setup_off_diff(self):
        f = self.clear_frame("Off_Diff")
        tk.Label(f, text="AI DIFFICULTY", font=FONTS['header'], 
                 bg=COLORS['bg'], fg=COLORS['fg']).pack(pady=50)
        
        HoverButton(f, text="EASY (Random)", width=20, hover_bg=COLORS['accent_1'], 
                    command=lambda: self.set_difficulty('EASY')).pack(pady=10)
        
        HoverButton(f, text="MEDIUM (Smart)", width=20, hover_bg=COLORS['accent_2'], 
                    command=lambda: self.set_difficulty('MEDIUM')).pack(pady=10)
        
        HoverButton(f, text="HARD (Unbeatable)", width=20, hover_bg=COLORS['accent_o'], 
                    command=lambda: self.set_difficulty('HARD')).pack(pady=10)
        
        HoverButton(f, text="← Back", width=10, bg="#45475a", 
                    command=lambda: self.show_frame("Off_Mode")).pack(pady=30)

    def set_difficulty(self, diff):
        self.ai_difficulty = diff
        self.prep_names('AI')

    def prep_names(self, submode):
        self.off_submode = submode
        self.name_submitted = False
        self.opponent_name_received = False
        self.setup_name_screen()
        self.show_frame("NameEntry")

    def start_online_flow(self):
        self.mode = 'ONLINE'
        self.setup_online_menu()
        self.show_frame("Online_Menu")

    def setup_online_menu(self):
        f = self.clear_frame("Online_Menu")
        tk.Label(f, text="LAN MULTIPLAYER", font=FONTS['header'], 
                 bg=COLORS['bg'], fg=COLORS['accent_x']).pack(pady=50)
        
        HoverButton(f, text="HOST GAME", width=20, pady=10, 
                    command=self.host_game).pack(pady=10)
        
        HoverButton(f, text="JOIN GAME", width=20, pady=10, 
                    command=self.join_game).pack(pady=10)
        
        HoverButton(f, text="← Back", width=10, bg="#45475a", 
                    command=lambda: self.show_frame("MainMenu")).pack(pady=30)

    def host_game(self):
        self.is_host = True
        self.my_role = PLAYER_X
        threading.Thread(target=self.server_thread, daemon=True).start()
        
        try: 
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except: 
            local_ip = "Unknown"
            
        self.show_wait_screen(f"HOSTING ON IP:\n{local_ip}\n\nWaiting for player...")

    def join_game(self):
        self.is_host = False
        self.my_role = PLAYER_O
        
        ip_info = self.custom_input_popup("CONNECTION SETUP", "Enter Host IP Address:")
        
        if not ip_info: return
        
        self.show_wait_screen(f"Connecting to {ip_info}...")
        threading.Thread(target=self.client_thread, args=(ip_info,), daemon=True).start()

    def custom_input_popup(self, title, prompt):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry("400x250")
        popup.configure(bg=COLORS['overlay_bg'])
        popup.resizable(False, False)
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 125
        popup.geometry(f"+{x}+{y}")

        result_var = tk.StringVar()
        self.popup_result = None

        tk.Label(popup, text=title, font=("Segoe UI", 16, "bold"), 
                 bg=COLORS['overlay_bg'], fg=COLORS['accent_x']).pack(pady=(20, 10))
        
        tk.Label(popup, text=prompt, font=("Segoe UI", 11), 
                 bg=COLORS['overlay_bg'], fg=COLORS['fg']).pack(pady=5)

        entry = tk.Entry(popup, font=("Segoe UI", 14), justify='center', 
                         bg=COLORS['btn_bg'], fg="white", insertbackground='white',
                         bd=2, relief=tk.FLAT)
        entry.pack(pady=10, ipadx=10, ipady=5)
        entry.focus_set()

        def on_confirm():
            self.popup_result = entry.get()
            popup.destroy()

        def on_cancel():
            self.popup_result = None
            popup.destroy()

        popup.bind('<Return>', lambda event: on_confirm())

        btn_frame = tk.Frame(popup, bg=COLORS['overlay_bg'])
        btn_frame.pack(pady=20)

        HoverButton(btn_frame, text="CONNECT", width=12, bg=COLORS['accent_1'], fg="#1e1e2e",
                    command=on_confirm).pack(side=tk.LEFT, padx=10)
        
        HoverButton(btn_frame, text="CANCEL", width=12, bg=COLORS['btn_bg'], 
                    command=on_cancel).pack(side=tk.LEFT, padx=10)

        popup.transient(self.root)
        popup.grab_set()
        self.root.wait_window(popup)
        
        return self.popup_result
    
    def show_custom_error(self, title, message):
        popup = tk.Toplevel(self.root)
        popup.title("ERROR")
        popup.geometry("380x220")
        popup.configure(bg=COLORS['overlay_bg'])
        popup.resizable(False, False)
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 190
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 110
        popup.geometry(f"+{x}+{y}")

        tk.Label(popup, text="⚠", font=("Segoe UI", 40), 
                 bg=COLORS['overlay_bg'], fg="#ff5555").pack(pady=(10, 0))
        
        tk.Label(popup, text=title, font=("Segoe UI", 14, "bold"), 
                 bg=COLORS['overlay_bg'], fg="#ff5555").pack()

        tk.Label(popup, text=message, font=("Segoe UI", 11), wraplength=350,
                 bg=COLORS['overlay_bg'], fg=COLORS['fg']).pack(pady=10)

        def on_close():
            popup.destroy()
            
        btn_frame = tk.Frame(popup, bg=COLORS['overlay_bg'])
        btn_frame.pack(pady=10)
        
        HoverButton(btn_frame, text="OK", width=10, bg="#ff5555", fg="white", hover_bg="#ff7777",
                    command=on_close).pack()

        popup.transient(self.root)
        popup.grab_set()
        self.root.wait_window(popup)
    
    # --- NEW STYLISH CONFIRMATION DIALOG (Replaces MessageBox) ---
    def show_styled_confirm_popup(self, title, message):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry("380x200")
        popup.configure(bg=COLORS['overlay_bg'])
        popup.resizable(False, False)
        
        # Center the popup
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 190
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 100
        popup.geometry(f"+{x}+{y}")

        self.confirm_result = False

        tk.Label(popup, text="❓", font=("Segoe UI", 30), 
                 bg=COLORS['overlay_bg'], fg=COLORS['accent_2']).pack(pady=(15, 0))
        
        tk.Label(popup, text=message, font=("Segoe UI", 14), 
                 bg=COLORS['overlay_bg'], fg=COLORS['fg']).pack(pady=10)

        def on_yes():
            self.confirm_result = True
            popup.destroy()
            
        def on_no():
            self.confirm_result = False
            popup.destroy()
            
        btn_frame = tk.Frame(popup, bg=COLORS['overlay_bg'])
        btn_frame.pack(pady=15)
        
        HoverButton(btn_frame, text="YES", width=10, bg=COLORS['accent_1'], fg="#1e1e2e", 
                    command=on_yes).pack(side=tk.LEFT, padx=15)
        
        HoverButton(btn_frame, text="NO", width=10, bg="#ff5555", fg="white", hover_bg="#ff7777",
                    command=on_no).pack(side=tk.LEFT, padx=15)

        popup.transient(self.root)
        popup.grab_set()
        self.root.wait_window(popup)
        
        return self.confirm_result

    # --- NEW ANIMATED WIN SCREEN (With Confetti) ---
    def show_win_popup(self, winner_name, can_rematch):
        popup = tk.Toplevel(self.root)
        popup.title("VICTORY!")
        popup.geometry("450x350")
        popup.configure(bg=COLORS['overlay_bg'])
        popup.resizable(False, False)
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 175
        popup.geometry(f"+{x}+{y}")

        # Canvas for Confetti
        canvas = tk.Canvas(popup, bg=COLORS['overlay_bg'], highlightthickness=0)
        canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Confetti Logic
        confetti = []
        colors = [COLORS['accent_x'], COLORS['accent_o'], COLORS['accent_1'], COLORS['accent_2'], '#f1c40f']
        
        for _ in range(50):
            cx = random.randint(0, 450)
            cy = random.randint(-200, 0)
            c_size = random.randint(5, 10)
            color = random.choice(colors)
            item = canvas.create_oval(cx, cy, cx+c_size, cy+c_size, fill=color, outline="")
            confetti.append({'id': item, 'speed': random.randint(2, 6)})

        def animate_confetti():
            try:
                for c in confetti:
                    canvas.move(c['id'], 0, c['speed'])
                    pos = canvas.coords(c['id'])
                    if pos[1] > 350:
                        canvas.move(c['id'], 0, -360)
                popup.after(30, animate_confetti)
            except: pass # Popup closed

        animate_confetti()

        # UI Overlay on top of canvas
        content_frame = tk.Frame(popup, bg=COLORS['overlay_bg'])
        content_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(content_frame, text="🏆", font=("Segoe UI", 60), 
                 bg=COLORS['overlay_bg'], fg=COLORS['win_gold']).pack(pady=(10, 0))
        
        tk.Label(content_frame, text="VICTORY!", font=("Segoe UI", 14, "bold", "italic"), 
                 bg=COLORS['overlay_bg'], fg=COLORS['win_gold']).pack()

        tk.Label(content_frame, text=f"{winner_name} Wins!", font=("Segoe UI", 24, "bold"), 
                 bg=COLORS['overlay_bg'], fg="#ffffff").pack(pady=(5, 20))

        self.win_choice = False 

        def on_restart():
            self.win_choice = True
            popup.destroy()

        def on_menu():
            self.win_choice = False
            popup.destroy()

        btn_frame = tk.Frame(content_frame, bg=COLORS['overlay_bg'])
        btn_frame.pack(pady=10)

        if can_rematch:
            HoverButton(btn_frame, text="↻ PLAY AGAIN", width=14, 
                        bg=COLORS['accent_1'], fg="#1e1e2e", hover_bg="#89e389",
                        command=on_restart).pack(side=tk.LEFT, padx=10)
            
            HoverButton(btn_frame, text="MENU", width=10, 
                        bg=COLORS['btn_bg'], command=on_menu).pack(side=tk.LEFT, padx=10)
        else:
            HoverButton(btn_frame, text="OK", width=15, 
                        bg=COLORS['accent_1'], fg="#1e1e2e",
                        command=on_menu).pack()

        popup.transient(self.root)
        popup.grab_set()
        self.root.wait_window(popup)
        
        return self.win_choice

    def show_wait_screen(self, msg):
        f = self.clear_frame("Online_Wait")
        tk.Label(f, text=msg, font=FONTS['sub'], 
                 bg=COLORS['bg'], fg=COLORS['accent_2']).pack(pady=100)
        
        tk.Label(f, text="●  ●  ●", font=("Arial", 20), 
                 bg=COLORS['bg'], fg=COLORS['fg']).pack(pady=10)
        
        HoverButton(f, text="Cancel", width=15, bg="#45475a", 
                    command=self.cancel_online_wait).pack(pady=50)
        self.show_frame("Online_Wait")

    def cancel_online_wait(self):
        if self.socket:
            try: self.socket.close()
            except: pass
            self.socket = None
        self.show_frame("Online_Menu")

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
            self.socket.settimeout(5) 
            self.socket.connect((ip, PORT))
            self.socket.settimeout(None)
            
            msg = self.socket.recv(1024).decode()
            if msg == "CONNECTED":
                self.root.after(0, lambda: self.prep_names('ONLINE'))
                self.listen_thread()
        except:
            self.root.after(0, lambda: self.show_custom_error("CONNECTION FAILED", f"Could not connect to host at:\n{ip}\n\nCheck IP address or try again."))
            self.root.after(0, lambda: self.show_frame("Online_Menu"))

    def listen_thread(self):
        threading.Thread(target=self.network_listener, daemon=True).start()

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
            self.opponent_name_received = True
            
            if self.is_host:
                if self.name_submitted:
                    self.root.after(0, self.setup_off_size)
                    self.root.after(0, lambda: self.show_frame("Off_Size"))
                    self.root.after(0, self.override_size_buttons_for_online)
                else:
                    pass
            else:
                if self.name_submitted:
                    self.root.after(0, lambda: self.show_wait_screen("Waiting for Host to pick size..."))
                else:
                    pass

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
            if isinstance(w, HoverButton) and "Back" in w['text']: w.pack_forget()
        
        for widget in f.winfo_children():
            if isinstance(widget, HoverButton) and "x" in widget['text']:
                size = int(widget['text'][0])
                widget.config(command=lambda s=size: self.send_size_config(s))

    def send_size_config(self, size):
        self.n = size
        self.socket.send(f"SIZE,{size};".encode())
        self.start_game()

    def setup_name_screen(self):
        f = self.clear_frame("NameEntry")
        tk.Label(f, text="PLAYER NAMES", font=FONTS['header'], 
                 bg=COLORS['bg'], fg=COLORS['fg']).pack(pady=40)
        
        tk.Label(f, text="Your Name:", bg=COLORS['bg'], fg=COLORS['fg']).pack()
        e1 = tk.Entry(f, font=("Segoe UI", 12), justify='center', 
                      bg="#45475a", fg="white", insertbackground='white')
        e1.pack(pady=5, ipadx=10, ipady=5); e1.insert(0, "Player 1")
        
        e2 = None
        if self.mode == 'OFFLINE' and self.off_submode == 'PvP':
            tk.Label(f, text="Opponent Name:", bg=COLORS['bg'], fg=COLORS['fg']).pack(pady=(20,0))
            e2 = tk.Entry(f, font=("Segoe UI", 12), justify='center', 
                          bg="#45475a", fg="white", insertbackground='white')
            e2.pack(pady=5, ipadx=10, ipady=5); e2.insert(0, "Player 2")
            
        HoverButton(f, text="START GAME", width=20, bg=COLORS['accent_1'], 
                    fg="#1e1e2e", hover_bg="#a6e3a1",
                    command=lambda: self.submit_names(e1.get(), e2.get() if e2 else None)).pack(pady=40)
        
        HoverButton(f, text="← Back", width=10, bg="#45475a", 
                    command=self.go_back_from_names).pack(pady=10)

    def go_back_from_names(self):
        if self.mode == 'OFFLINE':
            if self.off_submode == 'AI': self.show_frame("Off_Diff")
            else: self.show_frame("Off_Mode")
        else:
            if self.socket:
                try: self.socket.close()
                except: pass
                self.socket = None
            self.show_frame("Online_Menu")

    def submit_names(self, n1, n2):
        self.p1_name = n1
        self.name_submitted = True
        
        if self.mode == 'OFFLINE':
            if self.off_submode == 'AI':
                self.p2_name = f"AI ({self.ai_difficulty})"
            else:
                self.p2_name = n2
            self.start_game()
        else:
            self.socket.send(f"NAME,{n1};".encode())
            
            if self.is_host:
                if self.opponent_name_received:
                    self.setup_off_size()
                    self.show_frame("Off_Size")
                    self.override_size_buttons_for_online()
                else:
                    self.show_wait_screen("Waiting for Opponent...")
            else:
                if self.opponent_name_received:
                    self.show_wait_screen("Waiting for Host to pick size...")
                else:
                    self.show_wait_screen("Waiting for Opponent...")

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
        f = self.clear_frame("Game")
        
        score_frame = tk.Frame(f, bg=COLORS['bg'])
        score_frame.pack(pady=20, fill='x')
        
        if self.mode == 'ONLINE' and not self.is_host:
            name_left = self.p2_name
            name_right = self.p1_name
        else:
            name_left = self.p1_name
            name_right = self.p2_name

        f_p1 = tk.Frame(score_frame, bg=COLORS['bg'])
        f_p1.pack(side=tk.LEFT, padx=20, expand=True)
        tk.Label(f_p1, text=name_left, font=("Segoe UI", 12), fg=COLORS['accent_x'], bg=COLORS['bg']).pack()
        self.lbl_score_x = tk.Label(f_p1, text=str(self.score_x), font=("Segoe UI", 24, "bold"), fg=COLORS['accent_x'], bg=COLORS['bg'])
        self.lbl_score_x.pack()
        
        tk.Label(score_frame, text="VS", font=("Segoe UI", 14), fg="#585b70", bg=COLORS['bg']).pack(side=tk.LEFT)
        
        f_p2 = tk.Frame(score_frame, bg=COLORS['bg'])
        f_p2.pack(side=tk.RIGHT, padx=20, expand=True)
        tk.Label(f_p2, text=name_right, font=("Segoe UI", 12), fg=COLORS['accent_o'], bg=COLORS['bg']).pack()
        self.lbl_score_o = tk.Label(f_p2, text=str(self.score_o), font=("Segoe UI", 24, "bold"), fg=COLORS['accent_o'], bg=COLORS['bg'])
        self.lbl_score_o.pack()

        self.lbl_status = tk.Label(f, text="Game Start", font=("Segoe UI", 16), bg=COLORS['bg'], fg=COLORS['fg'])
        self.lbl_status.pack(pady=5)
        
        grid_frame = tk.Frame(f, bg=COLORS['bg'])
        grid_frame.pack(pady=10)
        
        self.btns = []
        for i in range(self.n * self.n):
            b = tk.Button(grid_frame, text=EMPTY, font=FONTS['game'], width=4, height=2,
                          bg=COLORS['btn_bg'], fg=COLORS['btn_text'],
                          relief=tk.FLAT, bd=0, activebackground=COLORS['btn_hover'],
                          command=lambda idx=i: self.on_click(idx))
            b.grid(row=i//self.n, column=i%self.n, padx=3, pady=3)
            self.btns.append(b)
        
        footer = tk.Frame(f, bg=COLORS['bg'])
        footer.pack(side=tk.BOTTOM, pady=20)
        
        tk.Label(footer, text=f"FIFO RULE: Only {self.n} pieces allowed.", 
                 font=("Segoe UI", 10, "italic"), fg="#6c7086", bg=COLORS['bg']).pack(pady=5)
        
        h_btn_frame = tk.Frame(footer, bg=COLORS['bg'])
        h_btn_frame.pack()
        
        HoverButton(h_btn_frame, text="Restart", width=12, bg=COLORS['btn_bg'], 
                    command=self.trigger_restart_confirm).pack(side=tk.LEFT, padx=5)
        HoverButton(h_btn_frame, text="Menu", width=12, bg="#f38ba8", fg="#1e1e2e", hover_bg="#eba0ac", 
                    command=self.quit_to_menu).pack(side=tk.LEFT, padx=5)

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
            if not self.turn_lock:
                txt = "YOUR TURN"
                col = COLORS['accent_1']
            else:
                txt = "OPPONENT'S TURN"
                col = COLORS['accent_2']
        else:
            p = self.p1_name if self.curr_player == PLAYER_X else self.p2_name
            txt = f"{p}'s Turn ({self.curr_player})"
            col = COLORS['accent_x'] if self.curr_player == PLAYER_X else COLORS['accent_o']
        self.lbl_status.config(text=txt, fg=col)

    def update_ui(self):
        for i, val in enumerate(self.game.board):
            btn = self.btns[i]
            btn.config(text=val)
            if val == PLAYER_X:
                btn.config(fg=COLORS['accent_x'], bg=COLORS['btn_bg'])
            elif val == PLAYER_O:
                btn.config(fg=COLORS['accent_o'], bg=COLORS['btn_bg'])
            else:
                btn.config(fg=COLORS['fg'], bg=COLORS['btn_bg'])
        
        q = self.game.move_queues[self.curr_player]
        if len(q) == self.n:
            self.btns[q[0]].config(bg=COLORS['fifo_fade'], fg="#ffffff")

    def ai_move(self):
        time.sleep(0.5)
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
        self.update_scores()
        
        if self.mode == 'ONLINE' and not self.is_host:
             if winner_char == PLAYER_X: winner_name = self.p2_name 
             else: winner_name = self.p1_name 
        else:
             winner_name = self.p1_name if winner_char == PLAYER_X else self.p2_name

        self.lbl_status.config(text=f"{winner_name} Wins!", fg=COLORS['accent_1'])
        
        # New: Uses the fancy popup with confetti
        play_again = self.show_win_popup(winner_name, can_rematch=True)
        
        if play_again:
            self.trigger_restart()
        else:
            self.quit_to_menu()

    def game_over_remote(self, winner_char):
        self.game_running = False
        if winner_char == PLAYER_X: self.score_x += 1
        else: self.score_o += 1
        self.update_scores()
        
        if self.mode == 'ONLINE' and not self.is_host:
             if winner_char == PLAYER_X: winner_name = self.p2_name
             else: winner_name = self.p1_name
        else:
             winner_name = self.p1_name if winner_char == PLAYER_X else self.p2_name

        self.lbl_status.config(text=f"{winner_name} Won!", fg=COLORS['accent_o'])
        
        # New: Uses the fancy popup with confetti
        self.show_win_popup(winner_name, can_rematch=False)

    def update_scores(self):
        self.lbl_score_x.config(text=str(self.score_x))
        self.lbl_score_o.config(text=str(self.score_o))

    def trigger_restart_confirm(self):
        # New: Replaces standard messagebox with dark theme styled popup
        if self.show_styled_confirm_popup("RESTART", "Are you sure you want to restart?"):
            self.trigger_restart()

    def trigger_restart(self):
        self.reset_match()
        if self.mode == 'ONLINE':
            self.socket.send("RESTART;".encode())

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernApp(root)
    root.mainloop()