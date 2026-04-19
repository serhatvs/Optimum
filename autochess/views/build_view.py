from __future__ import annotations

import random

import arcade
from arcade.types.color import Color

from autochess.models import Character, Item, MatchState, Modifier, Player
from autochess.systems.build_phase import (
    BUILD_SLOT_KEYS,
    apply_build_selection_to_character,
    clone_character_for_build,
    get_build_recommendation,
    roll_build_offers,
)
from autochess.views.game_view import GameView


RARITY_COLORS = {
    "common": Color(144, 186, 160, 255),
    "rare": Color(112, 170, 222, 255),
    "epic": Color(220, 154, 106, 255),
    "legendary": Color(236, 208, 112, 255),
}

SLOT_COLORS = {
    "legs": Color(208, 154, 108, 255),
    "arms": Color(118, 214, 180, 255),
    "eyes": Color(128, 196, 234, 255),
    "body": Color(180, 186, 224, 255),
    "heart": Color(226, 124, 124, 255),
    "brain": Color(194, 150, 228, 255),
}

SLOT_GRID = (
    ("legs", "arms"),
    ("eyes", "body"),
    ("heart", "brain"),
)

INVENTORY_ROW_HEIGHT = 34.0
INVENTORY_ROW_GAP = 8.0
INVENTORY_DETAIL_BASE = 42.0
DRAG_THRESHOLD = 6.0


class BuildView(arcade.View):
    def __init__(self, match_state: MatchState):
        super().__init__()
        self.match_state = match_state
        self.human_player = self._get_human_player()
        self.layout: dict[str, float] = {}
        self.dragged_item: Item | None = None
        self.drag_origin_index: int | None = None
        self.drag_position = (0.0, 0.0)
        self.hovered_offer_index: int | None = None
        self.expanded_offer_index: int | None = None
        self.pressed_offer_index: int | None = None
        self.press_position: tuple[float, float] | None = None
        self.message = "Drag items from your inventory into matching slots."
        self.rng = random.Random(match_state.seed + 313)
        self.offers: list[Item] = roll_build_offers(self.rng, match_state.item_catalog)
        self.selected_items: dict[str, Item | None] = {
            slot: None for slot in BUILD_SLOT_KEYS
        }
        self._load_existing_selection()

    def _get_human_player(self) -> Player | None:
        for player in self.match_state.players:
            if player.is_human:
                return player
        return None

    def _load_existing_selection(self) -> None:
        if not self.human_player:
            return
        for slot in BUILD_SLOT_KEYS:
            self.selected_items[slot] = self.human_player.character.item_slots.get(slot)

    def on_show_view(self) -> None:
        self._refresh_layout(self.window.width, self.window.height)

    def _refresh_layout(self, width: float, height: float) -> None:
        margin = 28.0
        left_panel_width = min(420.0, width * 0.38)
        right_left = margin + left_panel_width + 26.0
        slot_gap_x = 16.0
        slot_gap_y = 18.0
        slot_width = (left_panel_width - 24.0 - slot_gap_x) / 2
        slot_height = 96.0

        self.layout = {
            "margin": margin,
            "title_y": height - 58.0,
            "left_left": margin,
            "left_right": margin + left_panel_width,
            "slot_grid_left": margin + 8.0,
            "slot_grid_top": height - 154.0,
            "slot_width": slot_width,
            "slot_height": slot_height,
            "slot_gap_x": slot_gap_x,
            "slot_gap_y": slot_gap_y,
            "stats_left": margin + 16.0,
            "stats_right": margin + left_panel_width - 16.0,
            "stats_bottom": 188.0,
            "stats_top": 320.0,
            "inventory_left": right_left,
            "inventory_right": width - margin,
            "inventory_top": height - 154.0,
            "inventory_bottom": 150.0,
            "footer_y": 42.0,
            "button_width": 142.0,
            "button_height": 40.0,
        }

    def _slot_rect(self, slot: str) -> dict[str, float]:
        for row_index, row in enumerate(SLOT_GRID):
            for col_index, row_slot in enumerate(row):
                if row_slot != slot:
                    continue
                left = self.layout["slot_grid_left"] + col_index * (
                    self.layout["slot_width"] + self.layout["slot_gap_x"]
                )
                top = self.layout["slot_grid_top"] - row_index * (
                    self.layout["slot_height"] + self.layout["slot_gap_y"]
                )
                return {
                    "left": left,
                    "right": left + self.layout["slot_width"],
                    "top": top,
                    "bottom": top - self.layout["slot_height"],
                }
        raise ValueError(f"unknown slot '{slot}'")

    def _inventory_detail_height(self, item: Item) -> float:
        modifier_count = min(len(item.modifiers), 4)
        return INVENTORY_DETAIL_BASE + modifier_count * 18.0

    def _inventory_entry_rects(
        self,
    ) -> list[tuple[dict[str, float], dict[str, float] | None]]:
        left = self.layout["inventory_left"]
        right = self.layout["inventory_right"]
        top = self.layout["inventory_top"]
        rects: list[tuple[dict[str, float], dict[str, float] | None]] = []

        for index, item in enumerate(self.offers):
            header = {
                "left": left,
                "right": right,
                "top": top,
                "bottom": top - INVENTORY_ROW_HEIGHT,
            }
            top = header["bottom"] - INVENTORY_ROW_GAP
            detail = None
            if self.expanded_offer_index == index:
                detail_height = self._inventory_detail_height(item)
                detail = {
                    "left": left + 14.0,
                    "right": right - 10.0,
                    "top": top,
                    "bottom": top - detail_height,
                }
                top = detail["bottom"] - INVENTORY_ROW_GAP
            rects.append((header, detail))
        return rects

    def _button_rect(self, name: str) -> dict[str, float]:
        total_width = self.layout["button_width"] * 3 + 48.0
        left = (self.window.width - total_width) / 2
        if name == "reroll":
            button_left = left
        elif name == "recommend":
            button_left = left + self.layout["button_width"] + 24.0
        else:
            button_left = left + self.layout["button_width"] * 2 + 48.0
        return {
            "left": button_left,
            "right": button_left + self.layout["button_width"],
            "bottom": self.layout["footer_y"],
            "top": self.layout["footer_y"] + self.layout["button_height"],
        }

    def _rect_contains(self, rect: dict[str, float], x: float, y: float) -> bool:
        return rect["left"] <= x <= rect["right"] and rect["bottom"] <= y <= rect["top"]

    def _inventory_offer_at_position(self, x: float, y: float) -> int | None:
        for index, (header, _detail) in enumerate(self._inventory_entry_rects()):
            if self._rect_contains(header, x, y):
                return index
        return None

    def _slot_at_position(self, x: float, y: float) -> str | None:
        for slot in BUILD_SLOT_KEYS:
            if self._rect_contains(self._slot_rect(slot), x, y):
                return slot
        return None

    def _merging_key(self, item_1: Item, item_2: Item) -> tuple[str, str]:
        return tuple(sorted((item_1.item_id, item_2.item_id)))

    def _merged_item(self, equipped_item: Item, incoming_item: Item) -> Item | None:
        recipe_key = self._merging_key(equipped_item, incoming_item)
        result_id = self.match_state.item_mergings.get(recipe_key)
        if result_id is None:
            return None
        return self.match_state.item_catalog.get(result_id)

    def _preview_character(self) -> Character | None:
        if not self.human_player:
            return None
        preview = clone_character_for_build(self.human_player.character)
        apply_build_selection_to_character(
            character=preview,
            selected_items=self.selected_items,
            aux_caps=self.match_state.aux_caps,
        )
        return preview

    def _reroll(self) -> None:
        self.offers = roll_build_offers(self.rng, self.match_state.item_catalog)
        self.expanded_offer_index = None
        self.message = "Inventory rerolled."

    def _recommend(self) -> None:
        if not self.human_player:
            return

        # Prepare for optimization
        # Re-use character cloning to safely pass character
        preview = self._preview_character()
        if preview is None:
            return

        recommendation = get_build_recommendation(preview, self.offers)
        # Apply recommendation (subset: only non-None)
        for slot, item in recommendation.items():
            if item:
                self.selected_items[slot] = item

        self.message = "Recommended build applied."

    def _confirm(self) -> None:
        if not self.human_player:
            return
        apply_build_selection_to_character(
            character=self.human_player.character,
            selected_items=self.selected_items,
            aux_caps=self.match_state.aux_caps,
        )
        self.human_player.character.current_hp = (
            self.human_player.character.core_stats.max_hp
        )
        self.window.show_view(GameView(self.match_state))

    def _modifier_label(self, modifier: Modifier) -> str:
        sign = "+" if modifier.value >= 0 else ""
        if modifier.mode == "percent" or modifier.stat in {"crit_chance", "lifesteal"}:
            value_text = f"{sign}{modifier.value * 100:.0f}%"
        else:
            value_text = f"{sign}{modifier.value:.2f}".rstrip("0").rstrip(".")
        stat_text = modifier.stat.replace("_", " ").title()
        return f"{value_text} {stat_text}"

    def _draw_slot_item(
        self,
        slot: str,
        rect: dict[str, float],
        item: Item | None,
    ) -> None:
        arcade.draw_lrbt_rectangle_filled(
            rect["left"],
            rect["right"],
            rect["bottom"],
            rect["top"],
            (26, 30, 36),
        )
        arcade.draw_lrbt_rectangle_outline(
            rect["left"],
            rect["right"],
            rect["bottom"],
            rect["top"],
            SLOT_COLORS[slot],
            2,
        )
        arcade.Text(
            slot.title(),
            rect["left"] + 12,
            rect["top"] - 22,
            SLOT_COLORS[slot],
            12,
        ).draw()

        if item is None:
            arcade.Text(
                "Drop matching item here",
                rect["left"] + 12,
                rect["bottom"] + 18,
                arcade.color.GRAY,
                10,
            ).draw()
            return

        rarity_color = RARITY_COLORS.get(item.rarity, arcade.color.WHITE_SMOKE)
        arcade.Text(
            item.name,
            rect["left"] + 12,
            rect["top"] - 46,
            rarity_color,
            12,
            width=int(rect["right"] - rect["left"] - 22),
            multiline=True,
        ).draw()
        arcade.Text(
            item.rarity.title(),
            rect["left"] + 12,
            rect["top"] - 68,
            arcade.color.LIGHT_GRAY,
            10,
        ).draw()

    def _draw_slot_panel(self) -> None:
        panel_left = self.layout["left_left"]
        panel_right = self.layout["left_right"]
        panel_top = self.layout["title_y"] - 42.0
        panel_bottom = 150.0

        arcade.draw_lrbt_rectangle_filled(
            panel_left,
            panel_right,
            panel_bottom,
            panel_top,
            (18, 20, 24),
        )
        arcade.draw_lrbt_rectangle_outline(
            panel_left,
            panel_right,
            panel_bottom,
            panel_top,
            (82, 90, 104),
            2,
        )

        arcade.Text(
            "Equip Slots",
            panel_left + 16,
            panel_top - 24,
            arcade.color.WHITE,
            18,
        ).draw()
        arcade.Text(
            "User now owns 6 slot types: legs, arms, eyes, body, heart, brain.",
            panel_left + 16,
            panel_top - 50,
            arcade.color.LIGHT_GRAY,
            11,
        ).draw()

        for slot in BUILD_SLOT_KEYS:
            self._draw_slot_item(
                slot, self._slot_rect(slot), self.selected_items.get(slot)
            )

    def _draw_preview_stats(self) -> None:
        rect = {
            "left": self.layout["stats_left"],
            "right": self.layout["stats_right"],
            "top": self.layout["stats_top"],
            "bottom": self.layout["stats_bottom"],
        }
        arcade.draw_lrbt_rectangle_filled(
            rect["left"],
            rect["right"],
            rect["bottom"],
            rect["top"],
            (16, 18, 22),
        )
        arcade.draw_lrbt_rectangle_outline(
            rect["left"],
            rect["right"],
            rect["bottom"],
            rect["top"],
            (70, 78, 90),
            1,
        )
        arcade.Text(
            "Preview",
            rect["left"] + 12,
            rect["top"] - 22,
            arcade.color.WHITE_SMOKE,
            15,
        ).draw()

        preview = self._preview_character()
        if preview is None:
            return

        arcade.Text(
            f"{preview.name} | {preview.archetype}",
            rect["left"] + 12,
            rect["top"] - 48,
            arcade.color.LIGHT_GRAY,
            11,
        ).draw()
        arcade.Text(
            f"HP {preview.core_stats.max_hp}  ATK {preview.core_stats.atk}  DEF {preview.core_stats.def_stat}",
            rect["left"] + 12,
            rect["top"] - 72,
            arcade.color.ANTIQUE_WHITE,
            11,
        ).draw()
        arcade.Text(
            f"AS {preview.aux_stats.attack_speed:.2f}  AGI {preview.aux_stats.agility:.0f}",
            rect["left"] + 12,
            rect["top"] - 96,
            arcade.color.LIGHT_GRAY,
            10,
        ).draw()
        arcade.Text(
            f"CRIT {preview.aux_stats.crit_chance * 100:.0f}%  MANA {preview.aux_stats.mana_gain:.2f}",
            rect["left"] + 12,
            rect["top"] - 118,
            arcade.color.LIGHT_GRAY,
            10,
        ).draw()
        arcade.Text(
            f"Lifesteal {preview.aux_stats.lifesteal * 100:.0f}%",
            rect["left"] + 12,
            rect["top"] - 140,
            arcade.color.LIGHT_GRAY,
            10,
        ).draw()

    def _draw_inventory_panel(self) -> None:
        left = self.layout["inventory_left"]
        right = self.layout["inventory_right"]
        top = self.layout["title_y"] - 42.0
        bottom = self.layout["inventory_bottom"]

        arcade.draw_lrbt_rectangle_filled(
            left,
            right,
            bottom,
            top,
            (18, 20, 24),
        )
        arcade.draw_lrbt_rectangle_outline(
            left,
            right,
            bottom,
            top,
            (82, 90, 104),
            2,
        )

        arcade.Text(
            "Inventory",
            left + 16,
            top - 24,
            arcade.color.WHITE,
            18,
        ).draw()
        arcade.Text(
            "Click a row to expand details, then drag that item into its slot.",
            left + 16,
            top - 48,
            arcade.color.LIGHT_GRAY,
            11,
        ).draw()

        for index, item in enumerate(self.offers):
            header, detail = self._inventory_entry_rects()[index]
            active = self.expanded_offer_index == index
            hovered = self.hovered_offer_index == index
            subdued = self.dragged_item is item and self.dragged_item is not None

            fill = (34, 40, 48) if not (active or hovered) else (44, 58, 66)
            text_color = arcade.color.WHITE_SMOKE if not subdued else arcade.color.GRAY
            border_color = SLOT_COLORS.get(item.slot_type, arcade.color.LIGHT_GRAY)

            arcade.draw_lrbt_rectangle_filled(
                header["left"],
                header["right"],
                header["bottom"],
                header["top"],
                fill,
            )
            arcade.draw_lrbt_rectangle_outline(
                header["left"],
                header["right"],
                header["bottom"],
                header["top"],
                border_color,
                2 if active else 1,
            )

            arcade.Text(
                item.slot_type.title(),
                header["left"] + 12,
                header["top"] - 22,
                border_color,
                11,
            ).draw()
            arcade.Text(
                item.name,
                header["left"] + 106,
                header["top"] - 22,
                text_color,
                12,
                width=int(header["right"] - header["left"] - 138),
                multiline=True,
            ).draw()
            arcade.Text(
                "v" if active else ">",
                header["right"] - 22,
                header["top"] - 22,
                arcade.color.LIGHT_GRAY,
                12,
            ).draw()

            if detail is None:
                continue

            arcade.draw_lrbt_rectangle_filled(
                detail["left"],
                detail["right"],
                detail["bottom"],
                detail["top"],
                (24, 28, 34),
            )
            arcade.draw_lrbt_rectangle_outline(
                detail["left"],
                detail["right"],
                detail["bottom"],
                detail["top"],
                (94, 102, 118),
                1,
            )

            rarity_color = RARITY_COLORS.get(item.rarity, arcade.color.WHITE_SMOKE)
            arcade.Text(
                f"Rarity: {item.rarity.title()}",
                detail["left"] + 12,
                detail["top"] - 20,
                rarity_color,
                10,
            ).draw()
            arcade.Text(
                "Modifiers",
                detail["left"] + 12,
                detail["top"] - 40,
                arcade.color.LIGHT_GRAY,
                10,
            ).draw()

            line_y = detail["top"] - 60
            for modifier in item.modifiers[:4]:
                arcade.Text(
                    self._modifier_label(modifier),
                    detail["left"] + 12,
                    line_y,
                    arcade.color.WHITE_SMOKE,
                    10,
                ).draw()
                line_y -= 18

    def _draw_buttons(self) -> None:
        for name, label in (
            ("reroll", "Reroll"),
            ("recommend", "Recommend"),
            ("confirm", "Confirm"),
        ):
            rect = self._button_rect(name)
            if name == "confirm":
                fill = (46, 86, 72)
                border = arcade.color.GOLD
                text_color = arcade.color.GOLD
            elif name == "recommend":
                fill = (52, 60, 72)
                border = arcade.color.LIGHT_BLUE
                text_color = arcade.color.LIGHT_BLUE
            else:
                fill = (38, 44, 52)
                border = Color(90, 98, 110, 255)
                text_color = arcade.color.WHITE_SMOKE

            arcade.draw_lrbt_rectangle_filled(
                rect["left"],
                rect["right"],
                rect["bottom"],
                rect["top"],
                fill,
            )
            arcade.draw_lrbt_rectangle_outline(
                rect["left"],
                rect["right"],
                rect["bottom"],
                rect["top"],
                border,
                2,
            )
            arcade.Text(
                label,
                (rect["left"] + rect["right"]) / 2,
                (rect["bottom"] + rect["top"]) / 2 - 8,
                text_color,
                13,
                anchor_x="center",
            ).draw()

    def _draw_drag_preview(self) -> None:
        if self.dragged_item is None:
            return

        rect = {
            "left": self.drag_position[0] - 120.0,
            "right": self.drag_position[0] + 120.0,
            "top": self.drag_position[1] + 22.0,
            "bottom": self.drag_position[1] - 22.0,
        }
        border_color = SLOT_COLORS.get(
            self.dragged_item.slot_type, arcade.color.LIGHT_GRAY
        )
        arcade.draw_lrbt_rectangle_filled(
            rect["left"],
            rect["right"],
            rect["bottom"],
            rect["top"],
            (42, 48, 56),
        )
        arcade.draw_lrbt_rectangle_outline(
            rect["left"],
            rect["right"],
            rect["bottom"],
            rect["top"],
            border_color,
            2,
        )
        arcade.Text(
            self.dragged_item.slot_type.title(),
            rect["left"] + 10,
            rect["top"] - 18,
            border_color,
            10,
        ).draw()
        arcade.Text(
            self.dragged_item.name,
            rect["left"] + 86,
            rect["top"] - 18,
            arcade.color.WHITE_SMOKE,
            11,
        ).draw()

    def on_draw(self) -> None:
        self.clear((24, 26, 30))
        arcade.Text(
            "Build Phase",
            self.window.width / 2,
            self.layout["title_y"] + 10,
            arcade.color.ANTIQUE_WHITE,
            30,
            anchor_x="center",
        ).draw()
        arcade.Text(
            "Inventory list active: click to inspect, drag to equip.",
            self.window.width / 2,
            self.layout["title_y"] - 18,
            arcade.color.LIGHT_GRAY,
            13,
            anchor_x="center",
        ).draw()

        self._draw_slot_panel()
        self._draw_preview_stats()
        self._draw_inventory_panel()
        self._draw_buttons()

        arcade.Text(
            self.message,
            self.window.width / 2,
            104,
            arcade.color.GRAY,
            11,
            anchor_x="center",
        ).draw()
        arcade.Text(
            "Controls: click row to expand | drag row to slot | right click slot to clear | R reroll | Enter confirm",
            self.window.width / 2,
            82,
            arcade.color.DARK_GRAY,
            10,
            anchor_x="center",
        ).draw()

        self._draw_drag_preview()

    def on_resize(self, width: float, height: float) -> None:
        super().on_resize(int(width), int(height))
        self._refresh_layout(width, height)

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        self.hovered_offer_index = self._inventory_offer_at_position(x, y)
        if self.dragged_item is not None:
            self.drag_position = (x, y)

    def on_mouse_drag(
        self,
        x: float,
        y: float,
        dx: float,
        dy: float,
        buttons: int,
        modifiers: int,
    ) -> None:
        if (
            self.dragged_item is None
            and self.pressed_offer_index is not None
            and self.press_position
        ):
            if (
                abs(x - self.press_position[0]) + abs(y - self.press_position[1])
                >= DRAG_THRESHOLD
            ):
                self.drag_origin_index = self.pressed_offer_index
                self.dragged_item = self.offers[self.pressed_offer_index]

        if self.dragged_item is not None:
            self.drag_position = (x, y)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        if button == arcade.MOUSE_BUTTON_RIGHT:
            slot = self._slot_at_position(x, y)
            if slot is not None:
                self.selected_items[slot] = None
                self.message = f"{slot.title()} slot cleared."
            return

        if button != arcade.MOUSE_BUTTON_LEFT:
            return

        for name in ("reroll", "recommend", "confirm"):
            if self._rect_contains(self._button_rect(name), x, y):
                if name == "reroll":
                    self._reroll()
                elif name == "recommend":
                    self._recommend()
                else:
                    self._confirm()
                return

        hit_index = self._inventory_offer_at_position(x, y)
        if hit_index is None:
            return

        self.pressed_offer_index = hit_index
        self.press_position = (x, y)
        self.drag_position = (x, y)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        if button != arcade.MOUSE_BUTTON_LEFT:
            return

        if self.dragged_item is not None:
            target_slot = self._slot_at_position(x, y)
            if target_slot is None:
                self.message = "Item returned to inventory."
            elif self.dragged_item.slot_type != target_slot:
                self.message = (
                    f"{self.dragged_item.name} only fits the "
                    f"{self.dragged_item.slot_type.title()} slot."
                )
            else:
                equipped_item = self.selected_items.get(target_slot)
                if equipped_item is None:
                    self.selected_items[target_slot] = self.dragged_item
                    self.message = (
                        f"{self.dragged_item.name} equipped to {target_slot.title()}."
                    )
                else:
                    merged_item = self._merged_item(equipped_item, self.dragged_item)
                    if merged_item is None:
                        self.message = f"No merge recipe for {equipped_item.name} + {self.dragged_item.name}."
                    else:
                        self.selected_items[target_slot] = merged_item
                        self.message = (
                            f"Merged {equipped_item.name} + {self.dragged_item.name} "
                            f"-> {merged_item.name}."
                        )
            self.dragged_item = None
            self.drag_origin_index = None
        elif self.pressed_offer_index is not None:
            hit_index = self._inventory_offer_at_position(x, y)
            if hit_index == self.pressed_offer_index:
                if self.expanded_offer_index == hit_index:
                    self.expanded_offer_index = None
                    self.message = "Item details closed."
                else:
                    self.expanded_offer_index = hit_index
                    self.message = f"{self.offers[hit_index].name} details opened."

        self.pressed_offer_index = None
        self.press_position = None

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.R:
            self._reroll()
        elif symbol == arcade.key.ENTER:
            self._confirm()
