from __future__ import annotations

import random
from dataclasses import dataclass

import arcade

from autochess.models import (
    AUX_STATS,
    AuxStats,
    Character,
    CoreStats,
    MatchState,
)
from autochess.views.game_view import GameView


@dataclass
class SliderConfig:
    label: str
    min_val: float
    max_val: float
    step: float
    format_str: str


class Slider:
    def __init__(self, config: SliderConfig, x: float, y: float, width: float):
        self.config = config
        self.x = x
        self.y = y
        self.width = width
        self.height = 12
        self.value = (config.min_val + config.max_val) / 2

    @property
    def normalized(self) -> float:
        range_size = self.config.max_val - self.config.min_val
        if range_size == 0:
            return 0.0
        return (self.value - self.config.min_val) / range_size

    def set_from_normalized(self, norm: float) -> None:
        range_size = self.config.max_val - self.config.min_val
        self.value = self.config.min_val + (norm * range_size)
        self.snap_to_step()

    def snap_to_step(self) -> None:
        step = self.config.step
        if step > 0:
            self.value = round(self.value / step) * step
        self.value = max(self.config.min_val, min(self.config.max_val, self.value))

    def hit_test(self, px: float, py: float) -> bool:
        return (
            self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height
        )

    def drag_to(self, px: float) -> None:
        ratio = max(0.0, min(1.0, (px - self.x) / self.width))
        self.set_from_normalized(ratio)

    def draw(self, selected: bool = False) -> None:
        bg_color = (50, 56, 64) if not selected else (70, 80, 96)
        fill_color = (90, 190, 180) if not selected else (120, 220, 200)

        arcade.draw_lrbt_rectangle_filled(
            self.x, self.x + self.width, self.y, self.y + self.height, bg_color
        )

        fill_width = self.width * self.normalized
        if fill_width > 0:
            arcade.draw_lrbt_rectangle_filled(
                self.x,
                self.x + fill_width,
                self.y,
                self.y + self.height,
                fill_color,
            )

        thumb_x = self.x + fill_width
        thumb_color = (255, 255, 255) if not selected else (255, 255, 200)
        arcade.draw_circle_filled(thumb_x, self.y + self.height / 2, 6, thumb_color)
        arcade.draw_circle_outline(
            thumb_x, self.y + self.height / 2, 6, (120, 130, 140), 1
        )


class BuildView(arcade.View):
    CORE_SLIDERS = [
        SliderConfig("Max HP", 400, 1800, 10, "%d"),
        SliderConfig("Attack", 30, 160, 5, "%d"),
        SliderConfig("Defense", 10, 100, 5, "%d"),
    ]

    AUX_SLIDERS = [
        SliderConfig("Attack Speed", 0.2, 5.0, 0.1, "%.1f"),
        SliderConfig("Agility", 0, 300, 5, "%.0f"),
        SliderConfig("Crit Chance", 0.0, 0.75, 0.01, "%.0f%%"),
        SliderConfig("Mana Gain", 0.0, 3.0, 0.1, "%.1f"),
        SliderConfig("Lifesteal", 0.0, 0.4, 0.01, "%.0f%%"),
    ]

    def __init__(self, match_state: MatchState):
        super().__init__()
        self.match_state = match_state
        self.sliders: list[Slider] = []
        self.selected_index = -1
        self.dragging = False
        self.layout: dict[str, float] = {}
        self._init_from_character()

    def _init_from_character(self) -> None:
        human_player = None
        for player in self.match_state.players:
            if player.is_human:
                human_player = player
                break

        if not human_player or not human_player.character:
            return

        char = human_player.character
        self.sliders = []

        self.sliders.append(
            Slider(
                self.CORE_SLIDERS[0],
                0,
                0,
                200,
            )
        )
        self.sliders[-1].value = float(char.core_stats.max_hp)
        self.sliders[-1].snap_to_step()

        self.sliders.append(
            Slider(
                self.CORE_SLIDERS[1],
                0,
                0,
                200,
            )
        )
        self.sliders[-1].value = float(char.core_stats.atk)
        self.sliders[-1].snap_to_step()

        self.sliders.append(
            Slider(
                self.CORE_SLIDERS[2],
                0,
                0,
                200,
            )
        )
        self.sliders[-1].value = float(char.core_stats.def_stat)
        self.sliders[-1].snap_to_step()

        aux = char.aux_stats
        for i, cfg in enumerate(self.AUX_SLIDERS):
            self.sliders.append(Slider(cfg, 0, 0, 200))
            if i == 0:
                self.sliders[-1].value = aux.attack_speed
            elif i == 1:
                self.sliders[-1].value = aux.agility
            elif i == 2:
                self.sliders[-1].value = aux.crit_chance
            elif i == 3:
                self.sliders[-1].value = aux.mana_gain
            elif i == 4:
                self.sliders[-1].value = aux.lifesteal
            self.sliders[-1].snap_to_step()

    def on_show_view(self) -> None:
        self._refresh_layout(self.window.width, self.window.height)
        self._position_sliders()

    def _refresh_layout(self, width: float, height: float) -> None:
        margin = 30
        slider_width = 260
        label_width = 130
        col_gap = 120

        content_width = (
            label_width + slider_width + col_gap + label_width + slider_width
        )
        content_left = (width - content_width) / 2

        self.layout = {
            "margin": margin,
            "content_left": content_left,
            "slider_width": slider_width,
            "label_width": label_width,
            "col_gap": col_gap,
            "title_y": height - margin - 30,
        }

    def _position_sliders(self) -> None:
        left = self.layout["content_left"]
        col2_left = (
            left
            + self.layout["label_width"]
            + self.layout["slider_width"]
            + self.layout["col_gap"]
        )
        width = self.layout["slider_width"]

        y = self.layout["title_y"] - 90
        gap = 52

        for i, slider in enumerate(self.sliders[:3]):
            slider.x = left + self.layout["label_width"] + 12
            slider.y = y - i * gap
            slider.width = width

        for i, slider in enumerate(self.sliders[3:]):
            slider.x = col2_left + self.layout["label_width"] + 12
            slider.y = y - i * gap
            slider.width = width

    def _apply_to_character(self) -> None:
        for player in self.match_state.players:
            if player.is_human and player.character:
                char = player.character
                char.core_stats.max_hp = int(self.sliders[0].value)
                char.core_stats.atk = int(self.sliders[1].value)
                char.core_stats.def_stat = int(self.sliders[2].value)

                char.base_aux_stats = AuxStats(
                    attack_speed=self.sliders[3].value,
                    agility=self.sliders[4].value,
                    crit_chance=self.sliders[5].value,
                    mana_gain=self.sliders[6].value,
                    lifesteal=self.sliders[7].value,
                )
                char.aux_stats = AuxStats.from_dict(char.base_aux_stats.as_dict())
                char.current_hp = char.core_stats.max_hp

    def _randomize(self) -> None:
        rng = random.Random()
        for slider in self.sliders:
            slider.value = rng.uniform(slider.config.min_val, slider.config.max_val)
            slider.snap_to_step()

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        if button == arcade.MOUSE_BUTTON_LEFT:
            for i, slider in enumerate(self.sliders):
                if slider.hit_test(x, y):
                    self.selected_index = i
                    self.dragging = True
                    slider.drag_to(x)
                    return

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        if self.dragging and self.selected_index >= 0:
            self.sliders[self.selected_index].drag_to(x)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.dragging = False

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.ENTER:
            self._apply_to_character()
            self.window.show_view(GameView(self.match_state))
        elif symbol == arcade.key.R:
            self._randomize()
        elif symbol == arcade.key.TAB:
            self.selected_index = (self.selected_index + 1) % len(self.sliders)
        elif symbol in (arcade.key.UP, arcade.key.RIGHT):
            if 0 <= self.selected_index < len(self.sliders):
                step = self.sliders[self.selected_index].config.step
                self.sliders[self.selected_index].value += step
                self.sliders[self.selected_index].snap_to_step()
        elif symbol in (arcade.key.DOWN, arcade.key.LEFT):
            if 0 <= self.selected_index < len(self.sliders):
                step = self.sliders[self.selected_index].config.step
                self.sliders[self.selected_index].value -= step
                self.sliders[self.selected_index].snap_to_step()

    def on_text_input(self, text: str) -> None:
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(self.sliders):
                self.selected_index = idx

    def on_resize(self, width: float, height: float) -> None:
        super().on_resize(int(width), int(height))
        self._refresh_layout(width, height)
        self._position_sliders()

    def _draw_stat_value(self, value: float, config: SliderConfig) -> str:
        if "%%" in config.format_str:
            pct = int(value * 100)
            return config.format_str.replace("%%", str(pct))
        return config.format_str % value

    def on_draw(self) -> None:
        self.clear((30, 24, 20))

        arcade.Text(
            "Build Phase",
            self.window.width / 2,
            self.layout["title_y"] + 30,
            arcade.color.LIGHT_CYAN,
            28,
            anchor_x="center",
        ).draw()

        arcade.Text(
            "Customize your character",
            self.window.width / 2,
            self.layout["title_y"] - 10,
            arcade.color.LIGHT_GRAY,
            14,
            anchor_x="center",
        ).draw()

        left = self.layout["content_left"]
        core_y = self.layout["title_y"] - 75

        arcade.Text(
            "Core Stats",
            left + self.layout["label_width"] / 2,
            core_y + 36,
            arcade.color.WHITE,
            14,
            anchor_x="center",
        ).draw()

        arcade.Text(
            "Customize your character",
            self.window.width / 2,
            self.layout["title_y"] - 10,
            arcade.color.LIGHT_GRAY,
            14,
            anchor_x="center",
        ).draw()

        left = self.layout["content_left"]
        core_y = self.layout["title_y"] - 75

        arcade.Text(
            "Core Stats",
            left + self.layout["label_width"] / 2,
            core_y + 36,
            arcade.color.WHITE,
            14,
            anchor_x="center",
        ).draw()

        for i, cfg in enumerate(self.CORE_SLIDERS):
            slider = self.sliders[i]
            arcade.Text(
                cfg.label,
                left + self.layout["label_width"],
                slider.y + 2,
                arcade.color.WHITE,
                12,
                anchor_x="right",
                anchor_y="center",

            ).draw()
            slider.draw(selected=(i == self.selected_index))
            arcade.Text(
                self._draw_stat_value(slider.value, cfg),
                slider.x + slider.width + 18,
                slider.y + 2,
                arcade.color.LIGHT_CYAN,
                12,
                anchor_x="left",
                anchor_y="center",

            ).draw()

        aux_start = len(self.CORE_SLIDERS)
        col2_left = (
            left
            + self.layout["label_width"]
            + self.layout["slider_width"]
            + self.layout["col_gap"]
        )

        arcade.Text(
            "Auxiliary Stats",
            col2_left + self.layout["label_width"] / 2,
            core_y + 36,
            arcade.color.WHITE,
            14,
            anchor_x="center",
        ).draw()

        for i, cfg in enumerate(self.AUX_SLIDERS):
            slider = self.sliders[aux_start + i]
            arcade.Text(
                cfg.label,
                col2_left + self.layout["label_width"],
                slider.y + 2,
                arcade.color.WHITE,
                12,
                anchor_x="right",
                anchor_y="center",

            ).draw()
            slider.draw(selected=(aux_start + i == self.selected_index))
            arcade.Text(
                self._draw_stat_value(slider.value, cfg),
                slider.x + slider.width + 18,
                slider.y + 2,
                arcade.color.LIGHT_CYAN,
                12,
                anchor_x="left",
                anchor_y="center",

            ).draw()

        footer_y = self.layout["margin"] + 40

        btn_width = 100
        btn_height = 28
        btn_gap = 20

        random_x = self.window.width / 2 - btn_width - btn_gap / 2
        confirm_x = self.window.width / 2 + btn_gap / 2

        arcade.draw_lrbt_rectangle_filled(
            random_x,
            random_x + btn_width,
            footer_y,
            footer_y + btn_height,
            (50, 56, 64),
        )
        arcade.draw_lrbt_rectangle_outline(
            random_x,
            random_x + btn_width,
            footer_y,
            footer_y + btn_height,
            (90, 190, 180),
            1,
        )
        arcade.Text(
            "Random",
            random_x + btn_width / 2,
            footer_y + btn_height / 2,
            arcade.color.WHITE,
            12,
            anchor_x="center",
            anchor_y="center",
        ).draw()

        arcade.draw_lrbt_rectangle_filled(
            confirm_x,
            confirm_x + btn_width,
            footer_y,
            footer_y + btn_height,
            (40, 80, 70),
        )
        arcade.draw_lrbt_rectangle_outline(
            confirm_x,
            confirm_x + btn_width,
            footer_y,
            footer_y + btn_height,
            arcade.color.GOLD,
            1,
        )
        arcade.Text(
            "Confirm",
            confirm_x + btn_width / 2,
            footer_y + btn_height / 2,
            arcade.color.GOLD,
            12,
            anchor_x="center",
            anchor_y="center",
        ).draw()

        help_y = footer_y - 30
        arcade.Text(
            "Controls: Click/drag sliders | Arrow keys adjust selected | Tab select | 1-8 quick select | R randomize | Enter confirm",
            self.window.width / 2,
            help_y,
            arcade.color.GRAY,
            10,
            anchor_x="center",
        ).draw()
