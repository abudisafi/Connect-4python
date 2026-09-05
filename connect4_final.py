import tkinter as tk
from tkinter import messagebox
import random
import sqlite3


class Players:
    """Stores player information and assigns each player a color."""

    def __init__(self):
        self.player1 = {"player_number": 1, "turns_taken": 0, "pieces": 21}
        self.player2 = {"player_number": 2, "turns_taken": 0, "pieces": 21}
        self._assign_colors()

    def _assign_colors(self):
        colors = ["red", "yellow"]
        random.shuffle(colors)
        self.player1["color"] = colors[0]
        self.player2["color"] = colors[1]


class Board:
    """Contains the Connect 4 board and game logic."""

    ROWS = 6
    COLUMNS = 7

    def __init__(self):
        self.players = Players()
        self.current_player = self.players.player1
        self.last_played = None
        self.column_counts = [0] * self.COLUMNS
        self.grid = [[0] * self.COLUMNS for _ in range(self.ROWS)]

    def play_piece(self, column):
        if self.column_counts[column] >= self.ROWS:
            messagebox.showinfo("Column Full", "Pick another column.")
            return False

        row = self.column_counts[column]
        self.grid[row][column] = self.current_player["player_number"]
        self.last_played = (row, column)
        self.column_counts[column] += 1
        self.current_player["turns_taken"] += 1
        self.current_player["pieces"] -= 1
        return True

    def check_win(self):
        if self.last_played is None:
            return False

        row, column = self.last_played
        player = self.current_player["player_number"]

        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for row_step, col_step in directions:
            count = 1

            for direction in (1, -1):
                r, c = row, column
                while True:
                    r += row_step * direction
                    c += col_step * direction

                    if not (0 <= r < self.ROWS and 0 <= c < self.COLUMNS):
                        break
                    if self.grid[r][c] != player:
                        break

                    count += 1

            if count >= 4:
                return True

        return False

    def switch_player(self):
        if self.current_player == self.players.player1:
            self.current_player = self.players.player2
        else:
            self.current_player = self.players.player1


class GameSave:
    """Handles persistent game statistics with SQLite."""

    def __init__(self, database_name="game_progress.db"):
        self.connection = sqlite3.connect(database_name)
        self.cursor = self.connection.cursor()
        # Start each new run of the app with a clean slate so scores
        # from a previous session don't carry over after you exit.
        self.cursor.execute("DROP TABLE IF EXISTS game_progress")
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS game_progress (
                player_1_score INTEGER,
                player_2_score INTEGER,
                winner INTEGER
            )
            """
        )
        self.connection.commit()

    def save_winner(self, board):
        winner = board.current_player["player_number"]
        values = (
            board.players.player1["turns_taken"],
            board.players.player2["turns_taken"],
            winner,
        )
        self.cursor.execute(
            "INSERT INTO game_progress VALUES (?, ?, ?)", values
        )
        self.connection.commit()

    def get_win_counts(self):
        self.cursor.execute(
            "SELECT COUNT(*) FROM game_progress WHERE winner = 1"
        )
        player1_wins = self.cursor.fetchone()[0]

        self.cursor.execute(
            "SELECT COUNT(*) FROM game_progress WHERE winner = 2"
        )
        player2_wins = self.cursor.fetchone()[0]

        return player1_wins, player2_wins

    def get_best_score(self):
        scores = []

        for winner, column in ((1, "player_1_score"), (2, "player_2_score")):
            self.cursor.execute(
                f"SELECT {column} FROM game_progress WHERE winner = ?",
                (winner,),
            )
            scores.extend(row[0] for row in self.cursor.fetchall())

        return min(scores) if scores else 0

    def close(self):
        self.connection.close()


class GameGUI:
    """Builds and updates the graphical user interface."""

    def __init__(self, game):
        self.game = game
        self.root = game.root
        self.board = Board()

        self._create_board()
        self._create_buttons()
        self._create_scoreboard()
        self.update_scoreboard()

    def _create_board(self):
        self.root.configure(bg="blue")

        self.canvas = tk.Canvas(
            self.root, width=700, height=600, bg="blue", highlightthickness=0
        )
        self.canvas.grid(row=2, column=0, columnspan=7)

        self.circles = [
            [
                self.canvas.create_oval(
                    column * 100,
                    row * 100,
                    (column + 1) * 100,
                    (row + 1) * 100,
                    fill="white",
                    outline="white",
                )
                for column in range(Board.COLUMNS)
            ]
            for row in range(Board.ROWS)
        ]

    def _create_buttons(self):
        for column in range(Board.COLUMNS):
            button = tk.Button(
                self.root,
                text=f"Column {column + 1}",
                command=lambda c=column: self.play(c),
                borderwidth=0,
            )
            button.grid(row=1, column=column)

    def _create_scoreboard(self):
        tk.Label(
            self.root, text="Player Stats", font=("Arial", 13, "bold")
        ).grid(row=3, column=0, columnspan=3)

        tk.Label(
            self.root, text="Leaderboard", font=("Arial", 13, "bold")
        ).grid(row=3, column=4, columnspan=3)

        self.player1_score = tk.Label(self.root, font=("Arial", 13))
        self.player1_score.grid(row=4, column=0, columnspan=3)

        self.player2_score = tk.Label(self.root, font=("Arial", 13))
        self.player2_score.grid(row=4, column=3, columnspan=3)

        self.best_score = tk.Label(self.root, font=("Arial", 13))
        self.best_score.grid(row=4, column=5, columnspan=2)

    def play(self, column):
        if not self.board.play_piece(column):
            return

        self.update_board()
        # Force Tk to actually repaint the canvas now, before any dialog
        # (like the "Game Over!" popup) blocks the event loop. Without this,
        # the winning piece is drawn into the canvas's internal model but
        # never gets painted to the screen until after the dialog closes.
        self.canvas.update_idletasks()

        if self.board.check_win():
            data.save_winner(self.board)
            winner = self.board.current_player["player_number"]
            self.update_scoreboard()

            play_again = messagebox.askyesno(
                "Game Over!",
                f"Player {winner} wins! Would you like to start a new game?",
            )

            if play_again:
                self.reset_board()
            else:
                self.game.exit_game()
            return

        self.board.switch_player()
        self.update_scoreboard()

    def update_board(self):
        row, column = self.board.last_played
        display_row = Board.ROWS - 1 - row
        color = self.board.current_player["color"]
        self.canvas.itemconfig(
            self.circles[display_row][column], fill=color
        )

    def reset_board(self):
        self.board = Board()
        self.canvas.delete("all")
        self._create_board()
        self.update_scoreboard()

    def update_scoreboard(self):
        player1_wins, player2_wins = data.get_win_counts()
        best = data.get_best_score()

        self.player1_score.config(text=f"Player 1 Wins: {player1_wins}")
        self.player2_score.config(text=f"Player 2 Wins: {player2_wins}")

        if best:
            self.best_score.config(text=f"Best Score: {best} moves")
        else:
            self.best_score.config(text="No high score yet")


class Game:
    """Controls the application and game lifecycle."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Connect 4")
        self.root.resizable(False, False)

        self.gui = GameGUI(self)

        self.root.protocol("WM_DELETE_WINDOW", self.exit_game)

        # Make sure the main window is fully drawn and focused BEFORE the
        # instructions dialog pops up. Calling messagebox immediately (before
        # the window has been mapped/rendered) is what caused the dialog to
        # appear "stuck" until you clicked on the board - update_idletasks()
        # forces the window to finish drawing, and scheduling the dialog with
        # after() lets the window manager finish showing the window first.
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.after(100, self.show_instructions)

    def show_instructions(self):
        messagebox.showinfo(
            "Connect 4 Instructions",
            "Take turns dropping one of your pieces onto the board.\n\n"
            "The first player to get four pieces in a row "
            "vertically, horizontally, or diagonally wins!",
        )

    def exit_game(self):
        data.close()
        self.root.destroy()


data = GameSave()
game = Game()
game.root.mainloop()
