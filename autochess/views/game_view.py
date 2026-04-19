from __future__ import annotations

from pathlib import Path

import arcade
from arcade.types.color import Color

from autochess.models import MatchState
from autochess.systems.arena import ArenaSimulation
from autochess.systems.match import (
    apply_arena_result,
    create_arena_for_round,
    get_winner,
)


class GameView(arcade.View):
    def __init__(self, match_state: MatchState):
        super().__init__()
        self.match_state = match_state
        self.last_events: list[str] = []
        self.character_texture = self._load_character_texture()
        self.arena: ArenaSimulation | None = None
        self.round_committed = False

    def on_show_view(self) -> None:
        self._start_round_arena()

    def _start_round_arena(self) -> None:
        self.arena = create_arena_for_round(
            self.match_state,
            left=340,
            right=self.window.width - 40,
            bottom=90,
            top=self.window.height - 70,
        )
        self.round_committed = False
        self.last_events = [f"Round {self.match_state.round_number} started"]

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
                arcade.draw_rect_filled(
                    arcade.XYWH(46, y - 2, 32, 32), arcade.color.SLATE_GRAY
                )

            # Player Info Row
            label = f"[ {player.name} ] HP: {player.character.current_hp} | ATK: {player.character.core_stats.atk} | DEF: {player.character.core_stats.def_stat}"
            arcade.Text(label, 70, y + 8, arcade.color.LIGHT_GRAY, 14).draw()

            # Items Row
            item_labels = []
            for slot, item in player.character.item_slots.items():
                if item:
                    # Simplify effect for display: just first modifier stat/value
                    mod = item.modifiers[0]
                    mod_str = (
                        f"{mod.stat} {'+' if mod.value > 0 else ''}{mod.value:.2f}"
                    )
                    item_labels.append(f"[{item.name} - {mod_str}]")
                else:
                    item_labels.append("[ Empty ]")

            items_text = "ITEMS: " + " ".join(item_labels)
            arcade.Text(items_text, 70, y - 10, arcade.color.LIGHT_GRAY, 10).draw()
            y -= 50

        self._draw_arena()

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
                "Arena fights automatically. Press SPACE to skip round.",
                self.window.width / 2,
                40,
                arcade.color.LIGHT_GRAY,
                14,
                anchor_x="center",
            ).draw()

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
            if not unit.alive:
                tint = Color(90, 90, 90, 160)
            elif unit.flash_timer > 0:
                tint = Color(255, 130, 130, 255)
            else:
                tint = Color(255, 255, 255, 255)

            if self.character_texture:
                arcade.draw_texture_rect(
                    self.character_texture,
                    arcade.LBWH(unit.x - 16, unit.y - 16, 32, 32),
                    color=tint,
                    pixelated=True,
                )
            else:
                color = (
                    arcade.color.DARK_SPRING_GREEN
                    if unit.alive
                    else arcade.color.DARK_SLATE_GRAY
                )
                arcade.draw_circle_filled(unit.x, unit.y, 13, color)

            hp_ratio = unit.hp / max(1, unit.max_hp)
            self._draw_health_bar(unit.x - 18, unit.y + 24, 36, hp_ratio)

    def on_update(self, delta_time: float) -> None:
        if get_winner(self.match_state):
            return
        if not self.arena:
            return

        events = self.arena.step(delta_time)
        if events:
            self.last_events.extend(events[-3:])
            self.last_events = self.last_events[-12:]

        if self.arena.finished and not self.round_committed and self.arena.winner_id:
            round_events = apply_arena_result(self.match_state, self.arena.winner_id)
            self.last_events.extend(round_events)
            self.last_events = self.last_events[-12:]
            self.round_committed = True

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.SPACE and not get_winner(self.match_state):
            if self.arena and not self.arena.finished:
                while not self.arena.finished:
                    self.arena.step(0.2)
            if self.arena and self.arena.winner_id and not self.round_committed:
                round_events = apply_arena_result(
                    self.match_state, self.arena.winner_id
                )
                self.last_events.extend(round_events)
                self.last_events = self.last_events[-12:]
                self.round_committed = True
            if not get_winner(self.match_state):
                self._start_round_arena()
