from __future__ import annotations

from pathlib import Path

import arcade

from autochess.views.menu_view import MenuView


SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Pixel FFA Auto-Chess"


def main() -> None:
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    data_dir = Path(__file__).parent / "data"
    window.show_view(MenuView(data_dir=data_dir))
    arcade.run()


if __name__ == "__main__":
    main()
