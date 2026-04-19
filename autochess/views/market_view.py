from __future__ import annotations

import random

import arcade
from arcade.types.color import Color

from autochess.models import Item, MatchState, Modifier
from autochess.systems.market import (
    MARKET_OFFER_COUNT,
    MARKET_REFRESH_COST,
    get_market_price,
    purchase_market_item,
    roll_market_offers,
)
from autochess.systems.match import get_human_player


class MarketView(arcade.View):
    def __init__(self, match_state: MatchState):
        super().__init__()
        self.match_state = match_state
        self.human_player = get_human_player(match_state)
        self.rng = random.Random(match_state.seed + match_state.round_number * 2029)
        self.offers: list[Item | None] = []
        self.selected_index = 0
        self.hovered_index: int | None = None
        self.message = "Pick an upgrade, reroll, or continue to the next round."
        self.layout: dict[str, float] = {}
        self._roll_offers(spend_gold=False)

    def on_show_view(self) -> None:
        self._refresh_layout(self.window.width, self.window.height)

    def _refresh_layout(self, width: float, height: float) -> None:
        self.layout = {
            "margin": 28.0,
            "title_y": height - 58.0,
            "footer_y": 34.0,
        }

    def _roll_offers(self, *, spend_gold: bool) -> None:
        if not self.human_player:
            self.offers = []
            return

        if spend_gold:
            if self.human_player.gold < MARKET_REFRESH_COST:
                self.message = f"Need {MARKET_REFRESH_COST} gold to reroll."
                return
            self.human_player.gold -= MARKET_REFRESH_COST
            self.match_state.history.append(
                f"{self.human_player.name} rerolled the market for {MARKET_REFRESH_COST} gold"
            )

        self.offers = roll_market_offers(self.rng, self.match_state.item_catalog)
        if not self.offers:
            self.message = "No market items available. Press SPACE to continue."
        self.selected_index = 0

    def _offer_cards(self) -> list[dict[str, float]]:
        margin = self.layout["margin"]
        gap = 18.0
        card_width = min(280.0, (self.window.width - margin * 2 - gap * 2) / 3)
        total_width = card_width * MARKET_OFFER_COUNT + gap * (MARKET_OFFER_COUNT - 1)
        left = (self.window.width - total_width) / 2
        top = self.window.height - 150.0
        bottom = 170.0
        cards: list[dict[str, float]] = []
        for index in range(MARKET_OFFER_COUNT):
            card_left = left + index * (card_width + gap)
            cards.append(
                {
                    "left": card_left,
                    "right": card_left + card_width,
                    "top": top,
                    "bottom": bottom,
                }
            )
        return cards

    def _button_rects(self) -> dict[str, dict[str, float]]:
        footer_y = self.layout["footer_y"] + 20.0
        button_width = 140.0
        button_height = 40.0
        gap = 20.0
        center_x = self.window.width / 2
        refresh_left = center_x - button_width - gap / 2
        continue_left = center_x + gap / 2
        return {
            "refresh": {
                "left": refresh_left,
                "right": refresh_left + button_width,
                "bottom": footer_y,
                "top": footer_y + button_height,
            },
            "continue": {
                "left": continue_left,
                "right": continue_left + button_width,
                "bottom": footer_y,
                "top": footer_y + button_height,
            },
        }

    def _rect_contains(self, rect: dict[str, float], x: float, y: float) -> bool:
        return rect["left"] <= x <= rect["right"] and rect["bottom"] <= y <= rect["top"]

    def _item_color(self, item: Item | None) -> Color:
        if item is None:
            return Color(110, 110, 110, 255)
        palette = {
            "common": Color(134, 174, 152, 255),
            "rare": Color(110, 170, 220, 255),
            "epic": Color(210, 150, 110, 255),
            "legendary": Color(240, 208, 108, 255),
        }
        return palette.get(item.rarity, arcade.color.WHITE_SMOKE)

    def _modifier_label(self, modifier: Modifier) -> str:
        sign = "+" if modifier.value >= 0 else ""
        if modifier.mode == "percent":
            value = f"{sign}{modifier.value * 100:.0f}%"
        elif modifier.stat in {"crit_chance", "lifesteal"}:
            value = f"{sign}{modifier.value * 100:.0f}%"
        else:
            value = f"{sign}{modifier.value:.2f}".rstrip("0").rstrip(".")
        stat = modifier.stat.replace("_", " ").title()
        return f"{value} {stat}"

    def _buy_offer(self, index: int) -> None:
        if not self.human_player:
            self.message = "No human player found for the market."
            return
        if index >= len(self.offers) or self.offers[index] is None:
            self.message = "That offer is already gone."
            return

        item = self.offers[index]
        assert item is not None

        try:
            replaced_item = purchase_market_item(
                player=self.human_player,
                item=item,
                aux_caps=self.match_state.aux_caps,
            )
        except ValueError:
            self.message = f"Not enough gold for {item.name}."
            return

        replaced_text = ""
        if replaced_item is not None:
            replaced_text = f", replacing {replaced_item.name}"
        self.message = (
            f"Bought {item.name} for {get_market_price(item)} gold{replaced_text}."
        )
        self.match_state.history.append(
            f"{self.human_player.name} bought {item.name} for {get_market_price(item)} gold"
        )
        self.offers[index] = None

    def _continue_to_next_round(self) -> None:
        from autochess.views.game_view import GameView

        self.window.show_view(GameView(self.match_state))

    def on_draw(self) -> None:
        self.clear((18, 20, 24))
        arcade.draw_circle_filled(
            self.window.width * 0.16,
            self.window.height * 0.78,
            120,
            Color(58, 80, 72, 54),
        )
        arcade.draw_circle_filled(
            self.window.width * 0.84,
            self.window.height * 0.26,
            160,
            Color(112, 88, 62, 44),
        )

        arcade.Text(
            f"Round {self.match_state.round_number - 1} Market",
            self.window.width / 2,
            self.layout["title_y"],
            arcade.color.ANTIQUE_WHITE,
            28,
            anchor_x="center",
        ).draw()
        gold_total = self.human_player.gold if self.human_player else 0
        arcade.Text(
            f"Gold: {gold_total}",
            self.window.width / 2,
            self.layout["title_y"] - 34,
            arcade.color.GOLD,
            18,
            anchor_x="center",
        ).draw()

        cards = self._offer_cards()
        for index, rect in enumerate(cards):
            item = self.offers[index] if index < len(self.offers) else None
            is_selected = index == self.selected_index
            is_hovered = index == self.hovered_index
            if item is None:
                fill = (34, 36, 40)
                border = Color(84, 86, 92, 255)
            elif is_selected or is_hovered:
                fill = (46, 58, 68)
                border = Color(118, 224, 198, 255)
            else:
                fill = (34, 40, 48)
                border = Color(90, 96, 108, 255)

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

            label = "Sold Out"
            rarity_color = arcade.color.LIGHT_GRAY
            price_text = ""
            slot_text = ""
            modifiers: list[str] = []
            replace_text = ""
            if item is not None:
                label = item.name
                rarity_color = self._item_color(item)
                price_text = f"{item.rarity.title()}  {get_market_price(item)}g"
                slot_text = f"Slot: {item.slot_type.title()}"
                modifiers = [self._modifier_label(modifier) for modifier in item.modifiers[:3]]
                equipped = (
                    self.human_player.character.item_slots.get(item.slot_type)
                    if self.human_player
                    else None
                )
                replace_text = (
                    f"Equipped: {equipped.name}" if equipped is not None else "Equipped: Empty"
                )

            arcade.Text(
                f"{index + 1}. {label}",
                rect["left"] + 14,
                rect["top"] - 30,
                rarity_color,
                15,
            ).draw()
            arcade.Text(
                price_text,
                rect["left"] + 14,
                rect["top"] - 58,
                arcade.color.LIGHT_GRAY,
                11,
            ).draw()
            arcade.Text(
                slot_text,
                rect["left"] + 14,
                rect["top"] - 82,
                arcade.color.GRAY,
                11,
            ).draw()
            arcade.Text(
                replace_text,
                rect["left"] + 14,
                rect["top"] - 106,
                arcade.color.GRAY_BLUE,
                10,
            ).draw()

            line_y = rect["top"] - 146
            for line in modifiers:
                arcade.Text(
                    line,
                    rect["left"] + 14,
                    line_y,
                    arcade.color.WHITE_SMOKE,
                    11,
                ).draw()
                line_y -= 24

        buttons = self._button_rects()
        for label, rect in buttons.items():
            if label == "refresh":
                fill = (48, 58, 66)
                border = Color(108, 186, 180, 255)
                text = f"Reroll (-{MARKET_REFRESH_COST}g)"
            else:
                fill = (70, 84, 66)
                border = Color(198, 210, 124, 255)
                text = "Continue"

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
                text,
                (rect["left"] + rect["right"]) / 2,
                (rect["bottom"] + rect["top"]) / 2 - 8,
                arcade.color.WHITE,
                14,
                anchor_x="center",
            ).draw()

        arcade.Text(
            self.message,
            self.window.width / 2,
            110,
            arcade.color.LIGHT_GRAY,
            12,
            anchor_x="center",
        ).draw()
        arcade.Text(
            "Use 1-3 to buy, R to reroll, and SPACE to continue.",
            self.window.width / 2,
            82,
            arcade.color.GRAY,
            11,
            anchor_x="center",
        ).draw()

    def on_resize(self, width: int, height: int) -> None:
        if hasattr(super(), "on_resize"):
            super().on_resize(width, height)
        self._refresh_layout(width, height)

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        key_to_offer = {
            arcade.key.KEY_1: 0,
            arcade.key.KEY_2: 1,
            arcade.key.KEY_3: 2,
            arcade.key.NUM_1: 0,
            arcade.key.NUM_2: 1,
            arcade.key.NUM_3: 2,
        }
        if symbol in key_to_offer:
            self._buy_offer(key_to_offer[symbol])
            return
        if symbol in (arcade.key.LEFT, arcade.key.A):
            self.selected_index = (self.selected_index - 1) % MARKET_OFFER_COUNT
            return
        if symbol in (arcade.key.RIGHT, arcade.key.D):
            self.selected_index = (self.selected_index + 1) % MARKET_OFFER_COUNT
            return
        if symbol == arcade.key.ENTER:
            self._buy_offer(self.selected_index)
            return
        if symbol == arcade.key.R:
            self._roll_offers(spend_gold=True)
            return
        if symbol in (arcade.key.SPACE, arcade.key.ESCAPE):
            self._continue_to_next_round()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        self.hovered_index = None
        for index, rect in enumerate(self._offer_cards()):
            if self._rect_contains(rect, x, y):
                self.hovered_index = index
                self.selected_index = index
                return

    def on_mouse_press(
        self,
        x: int,
        y: int,
        button: int,
        modifiers: int,
    ) -> None:
        if button != arcade.MOUSE_BUTTON_LEFT:
            return

        for index, rect in enumerate(self._offer_cards()):
            if self._rect_contains(rect, x, y):
                self._buy_offer(index)
                return

        buttons = self._button_rects()
        if self._rect_contains(buttons["refresh"], x, y):
            self._roll_offers(spend_gold=True)
            return
        if self._rect_contains(buttons["continue"], x, y):
            self._continue_to_next_round()
