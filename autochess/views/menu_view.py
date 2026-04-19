from __future__ import annotations

from pathlib import Path

import arcade

from autochess.bootstrap import build_match
from autochess.views.build_view import BuildView


class MenuView(arcade.View):
    def __init__(self, data_dir: Path):
        super().__init__()
        self.data_dir = data_dir

    def on_draw(self) -> None:
        self.clear((18, 22, 28))
        arcade.Text(
            "Pixel FFA Auto-Chess",
            self.window.width / 2,
            self.window.height / 2 + 40,
            arcade.color.ANTIQUE_WHITE,
            28,
            anchor_x="center",
        ).draw()
        arcade.Text(
            "Press ENTER to start",
            self.window.width / 2,
            self.window.height / 2 - 10,
            arcade.color.LIGHT_GRAY,
            16,
            anchor_x="center",
        ).draw()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.ENTER:
            match_state = build_match(seed=1337, data_dir=self.data_dir)
            self.window.show_view(BuildView(match_state))
