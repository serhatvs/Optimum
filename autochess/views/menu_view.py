from __future__ import annotations

from pathlib import Path
from typing import Callable

import arcade
from arcade.types.color import Color

from autochess.bootstrap import build_match
from autochess.views.build_view import BuildView


class MenuView(arcade.View):
    def __init__(self, data_dir: Path):
        super().__init__()
        self.data_dir = data_dir
        self.menu_items = ("Start", "Options", "Exit")
        self.selected_index = 0
        self.hovered_index: int | None = None
        self.options_message: str | None = None

    def _button_layout(self) -> list[dict[str, float | str | int]]:
        button_width = min(320.0, self.window.width * 0.34)
        button_height = 54.0
        gap = 16.0
        left = (self.window.width - button_width) / 2
        top = self.window.height / 2 + 18.0
        layout: list[dict[str, float | str | int]] = []

        for index, label in enumerate(self.menu_items):
            button_top = top - (index * (button_height + gap))
            layout.append(
                {
                    "label": label,
                    "index": index,
                    "left": left,
                    "right": left + button_width,
                    "top": button_top,
                    "bottom": button_top - button_height,
                }
            )
        return layout

    def _button_at_position(self, x: float, y: float) -> int | None:
        for button in self._button_layout():
            if (
                button["left"] <= x <= button["right"]
                and button["bottom"] <= y <= button["top"]
            ):
                return int(button["index"])
        return None

    def _start_game(self) -> None:
        match_state = build_match(seed=1337, data_dir=self.data_dir)
        self.window.show_view(BuildView(match_state))

    def _open_options(self) -> None:
        self.options_message = "Options screen is not wired yet."

    def _exit_game(self) -> None:
        self.window.close()

    def _activate_selection(self, index: int) -> None:
        actions: dict[int, Callable[[], None]] = {
            0: self._start_game,
            1: self._open_options,
            2: self._exit_game,
        }
        self.selected_index = index
        action = actions.get(index)
        if action:
            action()

    def on_draw(self) -> None:
        self.clear((18, 22, 28))
        arcade.draw_lrbt_rectangle_filled(
            0,
            self.window.width,
            0,
            self.window.height,
            (18, 22, 28),
        )
        arcade.draw_circle_filled(
            self.window.width * 0.18,
            self.window.height * 0.84,
            140,
            Color(54, 92, 88, 60),
        )
        arcade.draw_circle_filled(
            self.window.width * 0.84,
            self.window.height * 0.22,
            180,
            Color(120, 82, 62, 40),
        )
        arcade.Text(
            "Pixel FFA Auto-Chess",
            self.window.width / 2,
            self.window.height / 2 + 140,
            arcade.color.ANTIQUE_WHITE,
            30,
            anchor_x="center",
        ).draw()
        arcade.Text(
            "Deterministic arena battles with one survivor.",
            self.window.width / 2,
            self.window.height / 2 + 104,
            arcade.color.LIGHT_GRAY,
            13,
            anchor_x="center",
        ).draw()

        for button in self._button_layout():
            index = int(button["index"])
            is_selected = index == self.selected_index
            is_hovered = index == self.hovered_index

            if is_selected or is_hovered:
                fill = (54, 78, 82)
                border = Color(104, 220, 198, 255)
                text_color = arcade.color.WHITE
            else:
                fill = (34, 40, 48)
                border = Color(90, 96, 110, 255)
                text_color = arcade.color.LIGHT_GRAY

            arcade.draw_lrbt_rectangle_filled(
                button["left"],
                button["right"],
                button["bottom"],
                button["top"],
                fill,
            )
            arcade.draw_lrbt_rectangle_outline(
                button["left"],
                button["right"],
                button["bottom"],
                button["top"],
                border,
                2,
            )
            arcade.Text(
                str(button["label"]),
                (float(button["left"]) + float(button["right"])) / 2,
                (float(button["bottom"]) + float(button["top"])) / 2 - 10,
                text_color,
                18,
                anchor_x="center",
            ).draw()

        footer_text = self.options_message or "Use mouse or arrow keys, then press ENTER."
        arcade.Text(
            footer_text,
            self.window.width / 2,
            self.window.height / 2 - 190,
            arcade.color.GRAY,
            12,
            anchor_x="center",
        ).draw()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol in (arcade.key.UP, arcade.key.W):
            self.selected_index = (self.selected_index - 1) % len(self.menu_items)
            self.options_message = None
        elif symbol in (arcade.key.DOWN, arcade.key.S):
            self.selected_index = (self.selected_index + 1) % len(self.menu_items)
            self.options_message = None
        elif symbol == arcade.key.ESCAPE:
            self._exit_game()
        if symbol == arcade.key.ENTER:
            self._activate_selection(self.selected_index)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        self.hovered_index = self._button_at_position(x, y)
        if self.hovered_index is not None:
            self.selected_index = self.hovered_index

    def on_mouse_press(
        self, x: int, y: int, button: int, modifiers: int
    ) -> None:
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        target_index = self._button_at_position(x, y)
        if target_index is not None:
            self._activate_selection(target_index)
