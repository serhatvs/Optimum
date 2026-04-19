from __future__ import annotations

from pathlib import Path

import arcade

from autochess.models import MatchState
from autochess.systems.match import get_winner, run_match_round


class GameView(arcade.View):
    def __init__(self, match_state: MatchState):
        super().__init__()
        self.match_state = match_state
        self.last_events: list[str] = []
        self.character_texture = self._load_character_texture()

    def _load_character_texture(self) -> arcade.Texture | None:
        texture_path = Path(__file__).resolve().parents[2] / "player.png"
        if texture_path.exists():
            return arcade.load_texture(str(texture_path))
        return None

    def _draw_health_bar(self, x: float, y: float, width: float, ratio: float) -> None:
        ratio = max(0.0, min(1.0, ratio))
        arcade.draw_lrbt_rectangle_filled(
            x,
            x + width,
            y - 8,
            y,
            (60, 40, 40),
        )
        arcade.draw_lrbt_rectangle_filled(
            x,
            x + (width * ratio),
            y - 8,
            y,
            (90, 210, 120),
        )
        arcade.draw_lrbt_rectangle_outline(
            x,
            x + width,
            y - 8,
            y,
            arcade.color.BLACK,
            1,
        )

    def on_draw(self) -> None:
        self.clear((24, 30, 34))
        title = f"Round {self.match_state.round_number}"
        arcade.Text(title, 30, self.window.height - 50, arcade.color.WHITE, 20).draw()

        y = self.window.height - 95
        for player in self.match_state.players:
            status = "ELIM" if player.eliminated else f"HP {player.hp}"
            if self.character_texture:
                arcade.draw_texture_rect(
                    self.character_texture,
                    arcade.LBWH(30, y - 18, 32, 32),
                    pixelated=True,
                )
            else:
                arcade.draw_rectangle_filled(46, y - 2, 32, 32, arcade.color.SLATE_GRAY)

            label = f"{player.name:12} | {player.character.archetype:8} | {status}"
            arcade.Text(label, 70, y + 8, arcade.color.LIGHT_GRAY, 14).draw()

            health_ratio = player.hp / 100.0
            self._draw_health_bar(70, y - 2, 240, health_ratio)
            y -= 50

        y = 200
        for line in self.last_events[-6:]:
            arcade.Text(line, 30, y, arcade.color.ASH_GREY, 13).draw()
            y -= 20

        winner = get_winner(self.match_state)
        if winner:
            arcade.Text(
                f"Winner: {winner.name}",
                self.window.width / 2,
                60,
                arcade.color.GOLD,
                22,
                anchor_x="center",
            ).draw()
        else:
            arcade.Text(
                "Press SPACE for next round",
                self.window.width / 2,
                40,
                arcade.color.LIGHT_GRAY,
                14,
                anchor_x="center",
            ).draw()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.SPACE and not get_winner(self.match_state):
            self.last_events = run_match_round(self.match_state)
