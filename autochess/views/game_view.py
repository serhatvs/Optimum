from __future__ import annotations

import random
from pathlib import Path

import arcade
from arcade.types.color import Color

from autochess.models import MatchState
from autochess.systems.arena import (
    CORPSE_FADE_DURATION,
    ArenaSimulation,
)
from autochess.systems.match import (
    apply_arena_result,
    create_arena_for_round,
    get_human_player,
    get_winner,
    is_match_over,
    player_was_eliminated,
)


class GameView(arcade.View):
    def __init__(self, match_state: MatchState):
        super().__init__()
        self.match_state = match_state
        self.last_events: list[str] = []
        self._textures = self._load_character_textures()
        self.character_texture = self._textures[0] if self._textures else None
        self._assign_textures()
        self.arena: ArenaSimulation | None = None
        # Default layout to avoid KeyErrors before on_show_view
        from typing import Any

        self.layout: dict[str, Any] = {
            "margin": 10.0,
            "title_y": 700.0,
            "footer_y": 20.0,
            "footer_heading_y": 40.0,
            "sidebar": {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0},
            "arena": {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0},
            "event_log": {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0},
        }
        self.round_committed = False

    def on_show_view(self) -> None:
        self._refresh_layout(self.window.width, self.window.height)
        self._start_round_arena()

    def _start_round_arena(self) -> None:
        # Access nested dicts with type casting for safety
        def get_frame(key: str) -> dict[str, float]:
            return self.layout[key]  # type: ignore

        arena_frame = get_frame("arena")
        self.arena = create_arena_for_round(
            self.match_state,
            left=arena_frame["left"],
            right=arena_frame["right"],
            bottom=arena_frame["bottom"],
            top=arena_frame["top"],
        )
        self.round_committed = False
        self.last_events = [f"Round {self.match_state.round_number} started"]

    def _load_character_textures(self) -> list[arcade.Texture]:
        atlas_path = Path(__file__).resolve().parents[2] / "player_atlas.png"
        textures = []
        if atlas_path.exists():
            for y in range(0, 128, 32):
                for x in range(0, 128, 32):
                    textures.append(
                        arcade.load_texture(
                            str(atlas_path),
                        ).crop(x, y, 32, 32)
                    )
        return textures

    def _assign_textures(self) -> None:
        if not self._textures:
            return

        rng = random.Random(self.match_state.seed)
        for player in self.match_state.players:
            player.character.texture_index = rng.randrange(len(self._textures))

    def _get_player_texture(self, player) -> arcade.Texture | None:
        idx = getattr(player.character, "texture_index", 0)
        if idx < len(self._textures):
            return self._textures[idx]
        return self.character_texture

    def _load_character_texture(self) -> arcade.Texture | None:
        return self.character_texture  # Kept for compatibility if used elsewhere

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _refresh_layout(self, width: float, height: float) -> None:
        margin = self._clamp(width * 0.018, 10.0, 22.0)
        gap = self._clamp(width * 0.014, 10.0, 22.0)
        title_y = height - margin - 18.0

        min_arena_width = 280.0
        sidebar_width = self._clamp(width * 0.26, 180.0, 320.0)
        max_sidebar_width = max(
            160.0,
            width - (margin * 2) - gap - min_arena_width,
        )
        sidebar_width = min(sidebar_width, max_sidebar_width)

        sidebar_left = margin
        sidebar_right = sidebar_left + sidebar_width
        sidebar_bottom = max(16.0, height * 0.11)
        sidebar_top = height - margin - 28.0

        arena_left = sidebar_right + gap
        arena_right = width - margin
        arena_bottom = max(18.0, height * 0.12)
        arena_top = height - margin - 30.0

        event_log_width = self._clamp(
            (arena_right - arena_left) * 0.34,
            220.0,
            360.0,
        )
        event_log_height = self._clamp(
            (arena_top - arena_bottom) * 0.24,
            90.0,
            126.0,
        )
        event_log_left = arena_left + 14.0
        event_log_bottom = arena_bottom + 14.0

        self.layout = {
            "margin": margin,
            "title_y": title_y,
            "footer_y": margin + 16.0,
            "footer_heading_y": margin + 36.0,
            "sidebar": {
                "left": sidebar_left,
                "right": sidebar_right,
                "bottom": sidebar_bottom,
                "top": sidebar_top,
            },
            "arena": {
                "left": arena_left,
                "right": arena_right,
                "bottom": arena_bottom,
                "top": arena_top,
            },
            "event_log": {
                "left": event_log_left,
                "right": min(event_log_left + event_log_width, arena_right - 14.0),
                "bottom": event_log_bottom,
                "top": min(event_log_bottom + event_log_height, arena_top - 14.0),
            },
        }

    def _resize_arena_to_layout(
        self,
        old_arena_frame: dict[str, float],
        new_arena_frame: dict[str, float],
    ) -> None:
        if not self.arena:
            return

        old_width = max(1.0, old_arena_frame["right"] - old_arena_frame["left"])
        old_height = max(1.0, old_arena_frame["top"] - old_arena_frame["bottom"])
        new_width = max(1.0, new_arena_frame["right"] - new_arena_frame["left"])
        new_height = max(1.0, new_arena_frame["top"] - new_arena_frame["bottom"])

        for unit in self.arena.units.values():
            x_ratio = (unit.x - old_arena_frame["left"]) / old_width
            y_ratio = (unit.y - old_arena_frame["bottom"]) / old_height
            unit.x = new_arena_frame["left"] + (x_ratio * new_width)
            unit.y = new_arena_frame["bottom"] + (y_ratio * new_height)
            unit.x = min(
                new_arena_frame["right"] - 16, max(new_arena_frame["left"] + 16, unit.x)
            )
            unit.y = min(
                new_arena_frame["top"] - 16, max(new_arena_frame["bottom"] + 16, unit.y)
            )

        self.arena.left = new_arena_frame["left"]
        self.arena.right = new_arena_frame["right"]
        self.arena.bottom = new_arena_frame["bottom"]
        self.arena.top = new_arena_frame["top"]

    def _draw_health_bar(
        self,
        x: float,
        y: float,
        width: float,
        ratio: float,
        *,
        height: float = 8,
        fill_color: tuple[int, int, int] = (90, 210, 120),
        empty_color: tuple[int, int, int] = (60, 40, 40),
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        arcade.draw_lrbt_rectangle_filled(
            x,
            x + width,
            y - height,
            y,
            empty_color,
        )
        arcade.draw_lrbt_rectangle_filled(
            x,
            x + (width * ratio),
            y - height,
            y,
            fill_color,
        )
        arcade.draw_lrbt_rectangle_outline(
            x,
            x + width,
            y - height,
            y,
            arcade.color.BLACK,
            1,
        )

    def _truncate_text(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return f"{text[: max_chars - 3]}..."

    def _player_arena_unit(self, player):
        if not self.arena:
            return None
        return self.arena.units.get(player.player_id)

    def _player_hp_label(self, player) -> str:
        arena_unit = self._player_arena_unit(player)
        if arena_unit:
            return f"{arena_unit.hp}/{arena_unit.max_hp}"
        if player.infinite_health:
            return "INF"
        if player.eliminated:
            return "ELIM"
        return str(player.hp)

    def _player_bounty_label(self, player) -> str:
        arena_unit = self._player_arena_unit(player)
        if arena_unit:
            return str(arena_unit.bounty)
        return str(player.bounty)

    def _player_health_ratio(self, player) -> float:
        arena_unit = self._player_arena_unit(player)
        if arena_unit:
            return arena_unit.hp / max(1, arena_unit.max_hp)
        if player.eliminated:
            return 0.0
        if player.infinite_health:
            return 1.0
        return player.hp / 100.0

    def _player_health_bar_fill(self, player) -> tuple[int, int, int]:
        if player.eliminated:
            return (120, 82, 82)
        if player.infinite_health:
            return (92, 214, 196)
        return (90, 210, 120)

    def _draw_player_card(
        self,
        *,
        player,
        left: float,
        right: float,
        bottom: float,
        top: float,
    ) -> None:
        arena_unit = self.arena.units.get(player.player_id) if self.arena else None
        is_dead = player.eliminated or (arena_unit and not arena_unit.alive)
        if is_dead:
            fill = (45, 42, 46)
            border = (120, 82, 82)
            title_color = arcade.color.LIGHT_GRAY
        elif player.is_human:
            fill = (28, 50, 56)
            border = (90, 190, 180)
            title_color = arcade.color.WHITE
        else:
            fill = (36, 42, 50)
            border = (88, 96, 108)
            title_color = arcade.color.WHITE_SMOKE

        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, fill)
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, border, 1)

        icon_left = left + 8
        icon_bottom = bottom + 10
        texture = self._get_player_texture(player)
        if texture:
            tint = (
                Color(255, 255, 255, 255)
                if not is_dead
                else Color(120, 120, 120, 190)
            )
            arcade.draw_texture_rect(
                texture,
                arcade.LBWH(icon_left, icon_bottom, 28, 28),
                color=tint,
                pixelated=True,
            )
        else:
            arcade.draw_rect_filled(
                arcade.XYWH(icon_left + 14, icon_bottom + 14, 28, 28),
                arcade.color.SLATE_GRAY,
            )

        card_x = left + 46
        status = "YOU" if player.is_human else ("OUT" if player.eliminated else "BOT")
        status_color = (
            Color(92, 214, 196, 255)
            if player.is_human and not player.eliminated
            else Color(170, 170, 170, 255)
            if player.eliminated
            else Color(140, 160, 192, 255)
        )
        arcade.Text(
            self._truncate_text(player.name, 16),
            card_x,
            top - 16,
            title_color,
            12,
        ).draw()
        arcade.Text(
            status,
            right - 44,
            top - 16,
            status_color,
            11,
        ).draw()

        stats_line = (
            f"{player.character.archetype}  HP {self._player_hp_label(player)}"
            f"  ATK {player.character.core_stats.atk}"
            f"  DEF {player.character.core_stats.def_stat}"
        )
        arcade.Text(
            self._truncate_text(stats_line, 34),
            card_x,
            bottom + 24,
            arcade.color.LIGHT_GRAY,
            9,
        ).draw()
        arcade.Text(
            f"Gold {player.gold}  Bounty {self._player_bounty_label(player)}",
            card_x,
            bottom + 16,
            arcade.color.GRAY,
            9,
        ).draw()

        self._draw_health_bar(
            card_x,
            bottom + 11,
            right - card_x - 10,
            self._player_health_ratio(player),
            height=5,
            fill_color=self._player_health_bar_fill(player),
            empty_color=(44, 34, 38) if player.eliminated else (42, 32, 32),
        )

    def _draw_sidebar(self) -> None:
        # Access nested dicts with type casting for safety
        def get_frame(key: str) -> dict[str, float]:
            return self.layout[key]  # type: ignore

        panel_frame = get_frame("sidebar")
        panel_left = panel_frame["left"]
        panel_right = panel_frame["right"]
        panel_bottom = panel_frame["bottom"]
        panel_top = panel_frame["top"]
        arcade.draw_lrbt_rectangle_filled(
            panel_left,
            panel_right,
            panel_bottom,
            panel_top,
            (20, 24, 30),
        )
        arcade.draw_lrbt_rectangle_outline(
            panel_left,
            panel_right,
            panel_bottom,
            panel_top,
            (66, 74, 88),
            2,
        )
        arcade.Text(
            "Roster",
            panel_left + 14,
            panel_top - 24,
            arcade.color.WHITE,
            18,
        ).draw()

        card_top = panel_top - 40
        player_count = max(1, len(self.match_state.players))
        available_height = max(120.0, card_top - panel_bottom - 8.0)
        card_gap = self._clamp(available_height / (player_count * 10), 4.0, 8.0)
        card_height = self._clamp(
            (available_height - (card_gap * (player_count - 1))) / player_count,
            42.0,
            64.0,
        )
        for player in sorted(
            self.match_state.players,
            key=lambda p: (
                -int(not p.eliminated),
                - (self.arena.units[p.player_id].bounty if self.arena and p.player_id in self.arena.units else p.bounty)
            )
        ):
            card_bottom = card_top - card_height
            self._draw_player_card(
                player=player,
                left=panel_left + 8,
                right=panel_right - 8,
                bottom=card_bottom,
                top=card_top,
            )
            card_top = card_bottom - card_gap

    def _draw_event_log(self) -> None:
        # Access nested dicts with type casting for safety
        def get_frame(key: str) -> dict[str, float]:
            return self.layout[key]  # type: ignore

        log_frame = get_frame("event_log")
        left = log_frame["left"]
        right = log_frame["right"]
        bottom = log_frame["bottom"]
        top = log_frame["top"]

        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, (12, 14, 18, 210))
        arcade.draw_lrbt_rectangle_outline(
            left,
            right,
            bottom,
            top,
            (74, 84, 96),
            1,
        )
        arcade.Text(
            "Combat Feed",
            left + 12,
            top - 22,
            arcade.color.WHITE_SMOKE,
            12,
        ).draw()

        line_y = top - 42
        for line in self.last_events[-5:]:
            arcade.Text(
                self._truncate_text(line, 42),
                left + 12,
                line_y,
                arcade.color.ASH_GREY,
                11,
            ).draw()
            line_y -= 18

    def _player_name(self, player_id: str | None) -> str:
        if not player_id:
            return "Unknown"
        for player in self.match_state.players:
            if player.player_id == player_id:
                return player.name
        return player_id

    def _has_active_human_player(self) -> bool:
        human_player = get_human_player(self.match_state)
        return human_player is not None and not human_player.eliminated

    def _status_text(self) -> str:
        if get_winner(self.match_state):
            return "Match complete."
        if player_was_eliminated(self.match_state):
            if self.arena and self.arena.finished and self.round_committed:
                return "You are out. Press SPACE to spectate the next round."
            return "You are out. Spectating the remaining lobby. Press SPACE to skip round."
        if self.arena and self.arena.finished and self.round_committed:
            if self._has_active_human_player():
                return "Round complete. Press SPACE for the market."
            return "Round complete. Press SPACE for the next round."
        return "Arena fights automatically. Press SPACE to skip round."

    def _draw_result_overlay(self) -> None:
        if not self.arena or not self.arena.finished or not self.round_committed:
            return

        winner = get_winner(self.match_state)
        last_round = self.match_state.round_number - 1
        if winner:
            title = "Match Finished"
            subtitle = f"Champion: {winner.name}"
            color = arcade.color.GOLD
        else:
            title = f"Round {last_round} Complete"
            subtitle = f"Arena winner: {self._player_name(self.arena.winner_id)}"
            color = arcade.color.LIGHT_CYAN

        arena_width = self.arena.right - self.arena.left
        arena_height = self.arena.top - self.arena.bottom
        pad_x = self._clamp(arena_width * 0.12, 40.0, 110.0)
        pad_y = self._clamp(arena_height * 0.18, 54.0, 120.0)
        overlay_left = self.arena.left + pad_x
        overlay_right = self.arena.right - pad_x
        overlay_bottom = self.arena.bottom + pad_y
        overlay_top = self.arena.top - pad_y
        arcade.draw_lrbt_rectangle_filled(
            overlay_left,
            overlay_right,
            overlay_bottom,
            overlay_top,
            (8, 12, 18, 230),
        )
        arcade.draw_lrbt_rectangle_outline(
            overlay_left,
            overlay_right,
            overlay_bottom,
            overlay_top,
            arcade.color.WHITE_SMOKE,
            2,
        )
        center_x = (overlay_left + overlay_right) / 2
        center_y = (overlay_bottom + overlay_top) / 2
        arcade.Text(
            title,
            center_x,
            center_y + 32,
            color,
            28,
            anchor_x="center",
        ).draw()
        arcade.Text(
            subtitle,
            center_x,
            center_y - 4,
            arcade.color.WHITE_SMOKE,
            18,
            anchor_x="center",
        ).draw()
        arcade.Text(
            self._status_text(),
            center_x,
            center_y - 36,
            arcade.color.LIGHT_GRAY,
            14,
            anchor_x="center",
        ).draw()

    def on_draw(self) -> None:
        self.clear((24, 30, 34))
        title = f"Round {self.match_state.round_number}"
        arcade.Text(
            title,
            self.layout["margin"],
            self.layout["title_y"],
            arcade.color.WHITE,
            20,
        ).draw()

        self._draw_sidebar()
        self._draw_arena()
        self._draw_event_log()

        winner = get_winner(self.match_state)
        if winner:
            arcade.Text(
                f"Winner: {winner.name}",
                self.window.width / 2,
                self.layout["footer_heading_y"],
                arcade.color.GOLD,
                22,
                anchor_x="center",
            ).draw()
        else:
            arcade.Text(
                self._status_text(),
                self.window.width / 2,
                self.layout["footer_y"],
                arcade.color.LIGHT_GRAY,
                14,
                anchor_x="center",
            ).draw()

        self._draw_result_overlay()

    def _draw_arena(self) -> None:
        if not self.arena:
            return
        arcade.draw_lrbt_rectangle_filled(
            self.arena.left,
            self.arena.right,
            self.arena.bottom,
            self.arena.top,
            (18, 18, 22),
        )
        arcade.draw_lrbt_rectangle_outline(
            self.arena.left,
            self.arena.right,
            self.arena.bottom,
            self.arena.top,
            arcade.color.DIM_GRAY,
            2,
        )

        for unit in self.arena.alive_units():
            if unit.target_id:
                target = self.arena.units.get(unit.target_id)
                if target and target.alive:
                    arcade.draw_line(
                        unit.x,
                        unit.y,
                        target.x,
                        target.y,
                        (160, 50, 50, 70),
                        1,
                    )

        for unit in self.arena.units.values():
            if not unit.alive and unit.corpse_timer <= 0:
                continue

            if not unit.alive:
                alpha = int(180 * (unit.corpse_timer / CORPSE_FADE_DURATION))
                tint = Color(90, 90, 90, alpha)
            elif unit.flash_timer > 0:
                tint = Color(255, 130, 130, 255)
            else:
                tint = Color(255, 255, 255, 255)

            # Find the player for this unit
            player = next((p for p in self.match_state.players if p.player_id == unit.player_id), None)
            texture = self._get_player_texture(player) if player else self.character_texture

            if texture:
                arcade.draw_texture_rect(
                    texture,
                    arcade.LBWH(unit.x - 16, unit.y - 16, 32, 32),
                    color=tint,
                    pixelated=True,
                )
            else:
                color = (
                    arcade.color.DARK_SPRING_GREEN
                    if unit.alive
                    else Color(90, 90, 90, tint.a)
                )
                arcade.draw_circle_filled(unit.x, unit.y, 13, color)

            if unit.alive:
                hp_ratio = unit.hp / max(1, unit.max_hp)
                self._draw_health_bar(unit.x - 18, unit.y + 24, 36, hp_ratio)

    def on_update(self, delta_time: float) -> None:
        if not self.arena:
            return

        events = self.arena.step(delta_time)
        if events:
            self.last_events.extend(events[-3:])
            self.last_events = self.last_events[-12:]

        if self.arena.finished and not self.round_committed and self.arena.winner_id:
            round_events = apply_arena_result(self.match_state, self.arena)
            self.last_events.extend(round_events)
            self.last_events = self.last_events[-12:]
            self.round_committed = True

        if get_winner(self.match_state):
            return

    def on_resize(self, width: int, height: int) -> None:
        if hasattr(super(), "on_resize"):
            super().on_resize(width, height)

        old_arena_frame = None
        if self.layout:
            old_arena_frame = self.layout["arena"]

        self._refresh_layout(width, height)

        if self.arena and old_arena_frame:
            self._resize_arena_to_layout(old_arena_frame, self.layout["arena"])

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.SPACE and not is_match_over(self.match_state):
            if self.arena and not self.arena.finished:
                while not self.arena.finished:
                    self.arena.step(0.2)
            if self.arena and self.arena.winner_id and not self.round_committed:
                round_events = apply_arena_result(self.match_state, self.arena)
                self.last_events.extend(round_events)
                self.last_events = self.last_events[-12:]
                self.round_committed = True
            if not is_match_over(self.match_state):
                if self._has_active_human_player():
                    from autochess.views.market_view import MarketView

                    self.window.show_view(MarketView(self.match_state))
                else:
                    self._start_round_arena()
