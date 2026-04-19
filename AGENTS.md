# Agent Slot Architecture

The game uses a fixed 6-slot equipment system for all characters. Items can only be equipped in the slot corresponding to their `slot_type`.

## Equipment Slots
- **legs**: Footwear and leg-based equipment.
- **arms**: Hand-held items, bracers, and gloves.
- **eyes**: Helmets, headgear, and eye-enhancing accessories.
- **body**: Chest armor, cloaks, and body coverings.
- **heart**: Core accessories, amulets, and heart-augmenting items.
- **brain**: Magical accessories, books, and items enhancing cognitive/magical stats.

## Inventory
- Each character has an `inventory` (bag) to hold unequipped items.
- Players move items from the bag to the correct slot in the **Build Phase**.
- Duplicate items are allowed and tracked by unique instance IDs.
