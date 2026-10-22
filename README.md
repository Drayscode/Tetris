# Retro Arcade Tetris

A Python/Pygame Tetris game with a retro arcade-inspired interface, persistent local high scores, placement assistance, visual effects, and a separate Summary tab for game statistics.

## Features

- Classic falling-block Tetris gameplay
- Retro arcade-style framed game interface
- Level-based falling speed that increases as the player clears lines
- Persistent local high-score leaderboard
- Current score, top score, lines, and level tracking
- Summary tab with:
  - Current score
  - Top score
  - Lines cleared
  - Current level
  - Top-score leaderboard
  - Per-piece usage statistics
- Next-piece preview
- Ghost-piece landing preview
- Two placement guide lines for more accurate positioning
- Hard drop with the Space bar
- Hard-drop glow trail and landing flash
- Animated line-clear glow
- Flashing `TETRIS!` animation when four lines are cleared at once
- Confetti animation for a new top score
- Pause and restart functionality

---

Key	Action
A	Move the active piece left
D	Move the active piece right
R	Rotate the active piece clockwise
S	Soft drop; makes the piece fall faster while held
Space	Hard drop; instantly places the piece at its lowest valid position
Tab	Switch between the GAME and SUMMARY tabs
Esc	Pause or resume the game
W	Restart after game over
P	Quit the game

## Requirements

- Python 3.8 or later
- Pygame

Install Pygame with:

```bash
pip install pygame