# 🐠 TermQuarium

A cozy aquarium simulator that runs entirely in your terminal — built as a showcase/stress-test example for [cozy_tui](../../README.md). Every fish is its own independently-moving widget, decorations are real ASCII art, and the whole tank keeps living (day/night, hunger, friendships, sleep) whether you're clicking around or just watching.

```
  Money: $141   Food: 15   Fish: 6   🌙 Night, 21°C

  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                                 <o
        o>    <o                                      o>
                                                                /^\ /^\
      )                                                        | | | |
     (            ___                                         _|_|_|_|_
      )   ~~~~~~ /   \                                        |       |
     ==   \____/ \___/                                        |_______|
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

## Running it

```bash
python examples/aquarium/aquarium.py
# or
cozy-tui run examples/aquarium/aquarium.py
```

No extra dependencies beyond `cozy_tui` itself.

## Controls

| Key | Action |
|---|---|
| Click open water | Drop a pinch of food |
| Click a fish or decoration | Inspect it |
| `S` | Open the Shop |
| `G` | Settings |
| `P` | Save |
| `L` | Load |
| `H` | Help |
| `Esc` | Pause |
| `Z` | Stress test — mass-spawn fish up to the cap (debug) |

## What's in the tank

- **Fish** — Goldfish, Angelfish, Betta, and the Shark (a predator that hunts other fish instead of food). Each one gets a personality — Friendly, Explorer, Shy, Greedy, Lazy, or Playful — that shapes its steering, and can independently also be **Sleepy** (harder to wake up at night, stacks with any personality). Fish grow from Baby → Juvenile → Adult, get hungry, and can be sold from their Inspector panel.
- **Decorations** — Plant, Driftwood, Rock, and Castle. Rock and Castle are *containers*: fish can claim one to sleep inside overnight (priority: favorite spot → a bonded tankmate's container → nearest one with room → the floor), disappearing from view until they wake — click the decoration to peek in and see who's home.
- **Relationships** — every pair of fish quietly tracks a continuous bond score, nudged by real events (waking a friend up, sleeping together, giving up a home so someone else could have it) and slowly decaying if left alone. You never see the number — just a state (Rival/Dislikes/Neutral/Friend/Best Friend) and a short list of why, in each fish's Inspector. Bonds are earned, not rolled at birth.
- **Day/night cycle** — water temperature and the tank's background tint drift together over one continuous curve; Night puts non-hungry fish to sleep (a hard stop, not just slower). Mornings occasionally get a lighthearted vignette when a Friend pair wakes up together.
- **Economy** — a Shop for more fish/food/decorations, daily visitor income based on how attractive the tank looks, an Emergency Aquarium Welfare safety net for a totally bankrupt tank, and a Pause menu (`Esc`) that actually freezes the simulation, not just the screen.
- **Save/Load** — name a save once and `P` keeps saving into it; the Load menu can Rename, Duplicate, or Delete any save.

## Building a standalone Windows executable

The `TermQuarium.spec` (PyInstaller) and `TermQuarium.iss` (Inno Setup) files in this directory package the game as a double-clickable `.exe` and installer. Run both from inside `examples/aquarium/`:

```bash
pyinstaller TermQuarium.spec        # -> dist/TermQuarium.exe
iscc TermQuarium.iss                # -> Output/TermQuarium-Setup.exe (needs Inno Setup)
```

## Tests

The game's pure logic (steering, hunger, economy, relationships, save format) is unit-tested independently of any real terminal:

```bash
python -m pytest tests/test_aquarium.py tests/test_termquarium_save.py tests/test_termquarium_world.py -q
```

## Project layout

```
aquarium.py              # main() only -- wires everything into one running App
termquarium/
  constants.py           # every tuning constant, species/decoration catalogs
  steering.py            # pure movement math (steer, avoid, school, ...)
  economy.py             # hunger, feeding, attractiveness, visitor income
  relationships.py       # personality, Sleepy, the relationship-score system
  fish.py                # the Fish widget + its steering/sleep/home logic
  tank_objects.py        # Food, Decoration
  bubbles.py             # ambient bubble particles
  vignettes.py           # the morning "*boop*" in-tank caption
  world.py               # day/night cycle, water temperature
  save.py                # versioned JSON save/load
  shop.py, ui.py, inspectors.py   # Shop, menus, and Inspector panel builders
```
