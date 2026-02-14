# Implementation Plan: Remove Slots + Add Bonus + Line Animation

## Status: READY TO IMPLEMENT (Offline Work)

### 1. Line Clear Animation ✅ STARTED
**What's Done:**
- Modified `Grid.clear_lines()` to return `completed_line_indices`
- Tracks which rows are complete for highlighting

**Next Steps:**
- Update calls at lines 2822 and 3631 to handle returned indices
- Add animation state: `self.clearing_lines = []`, `self.clear_animation_timer = 0`
- Flash completed lines (white/yellow) for 0.5 seconds before removing
- Play satisfying sound effect

**Code Pattern:**
```python
cleared, events, line_indices = self.grid.clear_lines()
if cleared > 0:
    self.clearing_lines = line_indices
    self.clear_animation_timer = 0.5  # 500ms animation
    # Don't apply score until animation completes
```

---

### 2. Remove Slot Machine
**Files to Modify:**
- Line 18: Remove `from src.slot_machine import SlotMachine`
- Line 2109: Remove `self.slot_machine = SlotMachine(...)`
- Find all `game_state == 'SLOT_MACHINE'` checks and remove
- Remove slot drawing code
- Remove slot trigger on stomp combos

**Replacement:** End-of-level bonus calculation

---

### 3. End-of-Level Bonus Screen
**New Feature:** When level completes, show bonus screen

**Bonus Formula:**
```
Bonus Coins = Stomps Collected × Lines Cleared
```

**Implementation:**
```python
# At level completion:
self.level_stomps_collected = self.turtles_stomped  # Track per level
self.level_lines_cleared = self.lines_this_level

bonus = self.level_stomps_collected * self.level_lines_cleared
self.coins += bonus

# Show bonus screen
self.game_state = 'LEVEL_BONUS'
self.bonus_display_timer = 3.0
```

**Bonus Screen Display:**
```
LEVEL COMPLETE!

Stomps: 12
Lines: 25
─────────
BONUS: 300 COINS!

(Auto-continues to next level)
```

---

## Testing Checklist
- [ ] Lines flash white/yellow before clearing
- [ ] No slot machine appears
- [ ] End-of-level bonus shows correct calculation
- [ ] Bonus coins added to total
- [ ] Continues system still works (from v24)
- [ ] Mobile touch controls work

---

## Branch Status
- **Current Branch:** `remove-slots-add-bonus`
- **Safe Fallback:** `mobile-touch-working` (v19)
- **Latest Features:** `mario-tetris-focus` (v24 with continues)

**Ready to implement when Pygbag CDN is back online!**
