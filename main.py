from __future__ import annotations

from pathlib import Path

import arcade

SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Pixel FFA Auto-Chess"


def main() -> None:
    import autochess

    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)
    font_path = Path(__file__).parent / "ui" / "PixelSplitter.ttf"
    try:
        arcade.load_font(str(font_path))
        autochess.PIXEL_FONT = "PixelSplitter"
    except FileNotFoundError:
        autochess.PIXEL_FONT = "Arial"

    from autochess.views.menu_view import MenuView

    data_dir = Path(__file__).parent / "data"
    window.show_view(MenuView(data_dir=data_dir))
    arcade.run()


if __name__ == "__main__":
    main()
