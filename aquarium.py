"""Aquarium -- a cozy stress-test/showcase app.

Step 1: a tank full of independently-swimming fish, each its own Widget
instance (not one big custom-drawn Widget like examples/snake/snake.py) --
continuous motion via app.tick_interval, bouncing off the tank walls, drawn
by simple diff-rendering just like everything else in this library.

Step 2: click inside the tank to drop food; fish steer toward the nearest
food instead of just random-walking, eating it on contact. Each fish also
carries hunger/health that decays on its own clock (app.every), separate
from the per-frame movement update.

Step 3: a real economy. Money/Food counters replace Step 1's placeholders --
feeding spends food, buying spends money -- and a Shop overlay (a plain
Box + Button rows, opened with the "Open Shop" button or the S key) sells
more fish. The Shark is a deliberately different kind of fish: a predator
that hunts other fish instead of food, using the exact same steer-toward-
target/eat-on-contact mechanics Step 2 built for food.

Step 4: fixed Decoration widgets (a Plant, a Rock, a Castle) sit on the tank
floor. Fish steering gains a third blend term -- a repulsion push away from
whichever decoration they're nearest to, once inside its avoidance radius --
so they visibly curve around the furniture instead of swimming through it.
This is deliberately cheap steering-based avoidance, not real pathfinding: a
fish beelining for food directly behind a decoration will still get nudged
off course reactively rather than routing all the way around it. Decorations
are added before any fish, so (relying on plain z-order/draw-order layering,
not a real depth sort) fish always draw on top of them.

Step 5 (replacing the originally-planned settings panel -- skipped by
request): fish personality, naming, an Inspector panel, ASCII-art decorations,
food in the Shop, and starvation. Every Fish gets one of six named
personalities (Friendly/Explorer/Shy/Greedy/Lazy/Playful -- a single choice,
not independent traits) that changes its steering, turn cadence, and/or speed.
Mouse position is tracked via the same app.on_mouse() hook already used for
click-to-feed, extended to also record MouseMove; personality steering reuses
steer_toward_food/avoid_decorations exactly like food-seeking and decoration-
avoidance do, just aimed at a different target, with a fixed per-frame
priority: fleeing beats eating beats personality-driven steering beats plain
wandering. Clicking a fish opens an Inspector (name, species, age, health,
hunger, personality) with a Rename button (app.prompt()); hovering one shows a
quick live tooltip instead, via a custom on_enter/on_leave wiring rather than
App.set_tooltip() itself -- the tooltip text needs to stay live (hunger keeps
changing), and re-calling set_tooltip() to "refresh" it would silently
orphan any tooltip that happened to be open at that moment (single-slot
on_enter/on_leave, same as on_click). Decorations are real multi-row ASCII
art (Plant/Driftwood/Rock/Castle), not emoji -- an emoji glyph is drawn by the
terminal's own emoji font and mostly ignores our Style color. The Shop now
also sells a Fish Food restock. And a fish whose health reaches 0 (prolonged
starvation) dies -- removed from the tank with a toast.

Phase 2 (per the user's own roadmap): each fish randomly picks one Decoration
as its favorite spot at birth, shown in the Inspector ("Favorite spot: Rock").
On its own periodic clock (independent of the movement/hunger clocks), it has
a chance to swim over and relax there for a while -- gently damping its own
velocity once it arrives, rather than continuing to actively steer, so it
visibly settles down instead of just orbiting the spot. This sits at the
bottom of the existing steering priority (fleeing beats eating beats
personality-driven steering beats relaxing beats plain wandering): a
relaxing fish still drops everything to flee or eat, exactly like a
Friendly fish already drops its mouse-following the instant food shows up.

Phase 3: a real economy. Fish grow up (Baby -> Juvenile -> Adult, a real
glyph change, not just a number) and both fish and decorations can be sold
back for money (a fraction of their Shop price) via their Inspector panels,
each behind a confirmation. The Shop also sells decorations now. A daily
tick (app.every(AGE_SECONDS_PER_DAY, ...), the same "day" fish age by) pays
out a Maintenance Grant plus Visitor Donations -- attractiveness from fish,
decorations, and tank cleanliness drives a visitor count, each paying a
ticket price plus a random donation -- and shows a non-modal, auto-dismissing
Daily Summary. Settings (G key) holds one Gameplay toggle so far: Emergency
Aquarium Welfare, which gives a totally bankrupt tank (money = food = fish =
0) a small fresh start instead of leaving it empty forever.

Phase 4: relationships. Any newly-introduced fish (starter, bought, or born)
has a chance to bond with an existing one -- a mutual Friend (they drift
toward each other when neither has anything more urgent going on) or a
Rival (the disliked fish flees the moment its rival gets close, regardless
of personality, on top of Shy's existing mouse-fleeing; having a rival also
gives a fish's own food-seeking a modest "competitive" speed boost -- it's
racing its rival for food, not just hunger). Friend pairs where both are
grown-up, non-predator fish have a chance each day of a baby -- inheriting
one parent's species, born at their midpoint, and immediately eligible for
its own relationships and favorite spot like any other fish. Selling/losing
a fish clears any dangling friend/rival references pointing at it, the same
care already taken for a sold favorite Decoration.

Phase 5: world. A continuous day/night cycle (Night/Morning/Day, threshold-
based off one elapsed-time fraction) drives both the tank's background tint
and its water temperature (warmest at midday, coolest at midnight) off the
same underlying curve, so they stay in sync for free (see termquarium/
world.py). Temperature affects gameplay -- cold water slows fish down, hot
water speeds up hunger -- and Night puts every fish (hungry ones excepted --
see SLEEP_HUNGER_THRESHOLD) to sleep: a hard stop, not just slower, with
friends drifting to sleep close together and rivals as far apart as the
tank allows.

Phase 6: polish + stress test. A dev/debug key (Z) mass-spawns free starter
fish up to a 50-fish cap, proving the diff-renderer stays smooth with a lot
of independently-moving Fish widgets at once -- the whole point of this
example. Ambient bubbles (purely decorative, toggleable in Settings) rise
from the tank floor for a little extra life. Schooling: same-species,
non-predator fish within SCHOOL_RADIUS drift into loose groups via a
lightweight boids-style blend (cohesion + alignment + separation) once
nothing more urgent (fleeing/eating/personality steering/friend-following/
relaxing) is happening -- a species-level trait, not a personality one like
Friendly's own group pull, so it applies underneath everything else in the
priority chain, just above plain wandering.

Save/Load management: the Load menu's Rename/Duplicate/Delete (each mirroring
the Fish Inspector's own Rename/Sell pattern -- a prompt or confirm dialog,
then the actual save.py mutation once submitted/confirmed) sit alongside
Load on every card. Save (P) itself only prompts for a name the very first
time in a fresh session; once attached to a save (by loading one, or by
that first manual save), it writes straight back into the same file from
then on, so a normal session doesn't pile up one save per day.

Phase 7: container decorations. `capacity` (Rock=2, Castle=4; everything
else 0) is the one number that turns a decoration into a home a sleeping
fish can claim overnight -- no separate class, so any future decoration
becomes one just by giving it a nonzero capacity. Each night, a fish picks
a container via Fish._claim_home(), priority: its favorite spot (if that's
a container with room) -> a friend's already-claimed container (if it has
room, so best friends end up sleeping in the *same* home) -> the nearest
container with any room -> the tank floor (the original friend-close/
rival-far/settle behavior, unchanged, for whoever finds no room). Once
inside, a fish is frozen and invisible in the tank itself -- clicking the
decoration (the existing Decoration Inspector) is the only way to peek in
and see who's home. Waking clears the claim and drops the fish right back
at the door. A lighthearted one-line toast at the Night -> Morning
transition (see choose_morning_vignette()) picks a Friend pair for a bit of
narrative texture -- cosmetic only, since every fish still wakes together
mechanically; it isn't simulating individual wake times. Personality biases
which container (if any) a fish claims -- see Fish._claim_home()'s
docstring for Lazy/Shy/Friendly/Explorer's exact reordering of the baseline
priority.

Phase 8: Pause menu. Esc (which used to instantly quit) opens it instead --
every Fish/BubbleField checks the same shared `paused` flag this menu
flips, freezing solid (frozen in place and still drawn, unlike a housed
fish which stays invisible) rather than just showing a menu over a
simulation that keeps quietly running behind it. Quit lives behind its own
confirmation now, since Esc no longer doubles as instant, unconfirmed exit.

Sleepy: an independent yes/no trait rolled once at birth (roll_is_sleepy()),
stackable with a fish's regular personality rather than replacing it --
a Greedy fish can also be Sleepy. It only matters for the morning vignette
(choose_morning_vignette()): a Sleepy sleeper practically never gets the
"wake" flavor, resisting a normal boop almost every time (*boop* ... *...zzz*
instead of *awake*) rather than actually waking.

Phase 9: relationship scores, replacing the old one-time Friend/Rival dice
roll (see relationships.py's module docstring for the full model). Every
pair of fish shares exactly one continuous score in [-100, 100] -- nudged
by real interactions (record_wake_up/record_slept_together/
record_gave_up_home, the only three from the original design with an
actual mechanic to hook into today; the rest -- sharing/stealing food,
protecting from a shark, playing, fighting -- are natural follow-ups once
those mechanics exist), decaying slowly back toward 0 if left alone
(decay_relationships(), once a day), and never shown to the player as a
raw number -- only a state (relationship_state(): Rival/Dislikes/Neutral/
Friend/Best Friend) plus its most recent reasons. Fish.friend/Fish.rival
are now read-only properties derived from whichever relationship is
currently strongest/weakest (relationships.best_bond()/worst_bond()), so
all of Fish's existing friend-following/rival-fleeing/sleep-together/
container-priority steering keeps working unchanged. A brand new fish
(starter, bought, or born) starts with no relationships at all -- they're
earned, not rolled.

Everything reusable/testable -- pure steering/economy/relationship math, the
Fish/Decoration/Food/BubbleField widgets, and the modal-builder functions --
lives in the termquarium/ package next to this file; aquarium.py itself is
just main(), which wires all of it into one running App. See
tests/test_aquarium.py, which imports this file directly (not the package)
so every one of these re-exported names stays reachable as aq.<name>.
"""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui._width import text_width
from cozy_tui.events import Key, MouseClick, MouseMove
from cozy_tui.motion import lerp_color
from cozy_tui.widgets import Button, Label

from examples.aquarium.termquarium.bubbles import BubbleField, _Bubble, rise_bubble
from examples.aquarium.termquarium.constants import *
from examples.aquarium.termquarium.economy import (
    compute_attractiveness,
    compute_visitor_income,
    decay_hunger,
    feed,
    roll_visitor_donation,
    should_grant_welfare,
    should_warn_hungry,
)
from examples.aquarium.termquarium.fish import (
    Fish,
    _make_fish,
    describe_fish,
    fish_at,
    occupants_of,
)
from examples.aquarium.termquarium.inspectors import (
    _build_castle_interior,
    _build_daily_summary,
    _build_decoration_inspector,
    _build_inspector,
    _build_settings,
)
from examples.aquarium.termquarium.relationships import (
    all_relationship_pairs,
    choose_baby_species_name,
    choose_morning_vignette,
    clear_relationships,
    decay_relationships,
    find_breeding_pairs,
    find_eligible_waker,
    find_mutual_friend_pairs,
    get_relationship,
    random_personality,
    record_gave_up_home,
    record_slept_together,
    record_wake_up,
    relationship_state,
    remember,
    resolve_wake_attempt,
    roll_is_sleepy,
    roll_wake_threshold,
    set_relationship,
)
from examples.aquarium.termquarium.cloud import (
    delete_cloud_save,
    download_save as download_cloud_save,
    generate_cloud_key,
    list_cloud_saves,
    upload_save as upload_cloud_save,
)
from examples.aquarium.termquarium.save import (
    delete_save,
    duplicate_save,
    list_saves,
    load_cloud_key,
    read_save,
    rename_save,
    store_cloud_key,
    write_save,
)
from examples.aquarium.termquarium.shop import build_shop as _build_shop
from examples.aquarium.termquarium.steering import (
    avoid_decorations,
    nearest_index,
    random_velocity,
    school_velocity,
    steer,
    steer_toward_food,
)
from examples.aquarium.termquarium.styles import (
    STATS,
    TITLE,
    VIGNETTE_STYLE,
    WATER_LINE,
)
from examples.aquarium.termquarium.tank_objects import Decoration, Food, decoration_at
from examples.aquarium.termquarium.ui import (
    build_help_menu,
    build_pause_menu,
    build_restore_menu,
    build_save_menu,
    build_start_menu,
)
from examples.aquarium.termquarium.vignettes import MorningVignette
from examples.aquarium.termquarium.world import (
    compute_time_of_day,
    compute_water_temperature,
    get_day_phase,
    night_blend,
)

import math


def main() -> None:
    app = App(full=True, style=Style(fg="white", bg="black"), title="TermQuarium")
    app.tick_interval = 0.05  # continuous redraws; each Fish gates its own dt

    app.add(
        Label(
            2,
            0,
            "TermQuarium -- click to feed, S: shop, G: settings, P: save, L: load, "
            "Z: stress test, Esc: pause",
            TITLE,
        )
    )
    stats = Label(2, 1, "", STATS)
    app.add(stats)

    tank_x, tank_y = 2, 3
    tank_w = min(70, max(20, app.cols - 6))
    tank_h = min(20, max(8, app.rows - 8))

    app.add(Label(tank_x, tank_y, "~" * tank_w, WATER_LINE))
    app.add(Label(tank_x, tank_y + tank_h + 1, "~" * tank_w, WATER_LINE))

    bounds = (
        float(tank_x),
        float(tank_y + 1),
        float(tank_x + tank_w - 1),
        float(tank_y + tank_h),
    )
    foods = []
    fish = []
    state = {
        "money": 120,
        "food": 15,
        "food_spent_today": 0,
        "donations_today": 0,
        "welfare_enabled": True,
        "bubbles_enabled": True,
        "treats": {},
    }
    hungry_warning_active = {"value": False}
    day_count = {"n": 0}
    # None until Cloud Saves is set up (or restored via an existing key) on
    # this machine -- see _open_settings()'s Cloud Saves section. Kept
    # separate from `state`/save snapshots deliberately: the key lives with
    # the *machine*, not with any one aquarium's save file.
    cloud = {"key": load_cloud_key()}
    # Name of the save this session is currently "attached to" -- None until
    # the player has either loaded or manually saved once. Once set, Save
    # (P) writes straight back into that same save instead of prompting for
    # a new name every time, so a normal play session doesn't pile up one
    # file per day (see _save_game()).
    current_save = {"name": None}
    # Shared with every Fish/BubbleField -- the Pause menu (Esc) flips this
    # and everything freezes solid; see _open_pause_menu().
    paused = {"value": False}
    mouse_pos = {
        "x": None,
        "y": None,
    }  # shared with every Fish -- see personality steering
    # Day/night fraction is elapsed-time-since-start, modulo a day -- offset
    # so a fresh session (and a loaded save, which doesn't itself store a
    # time of day) always starts at midday (fraction 0.5), not fraction 0
    # (which get_day_phase() defines as Night).
    session_start = time.monotonic() - AGE_SECONDS_PER_DAY * 0.5
    environment = {
        "phase": "Day",
        "temperature": BASE_WATER_TEMP,
    }  # shared with every Fish -- see world.py

    # Decorations sit on the tank floor and are added before any fish, so
    # (plain add-order z-layering, see the module docstring) fish always
    # draw on top of them. Built from DECORATION_CATALOG (the same source
    # the Shop sells from) so a starting Castle sells for the same value as
    # a bought one.
    floor_y = tank_y + tank_h

    # Ambient bubbles, added before decorations so (plain add-order
    # z-layering, same convention as decorations-before-fish) they always
    # drift behind the furniture and fish rather than over them.
    app.add(
        BubbleField(bounds, lambda: state["bubbles_enabled"], lambda: paused["value"])
    )

    def _make_starting_decoration(kind: str, x) -> Decoration:
        item = DECORATION_CATALOG[kind]
        return Decoration(
            x,
            floor_y - len(item.art) + 1,
            item.art,
            item.colors,
            kind=kind,
            price=item.price,
            capacity=item.capacity,
        )

    # Seeded by _seed_starter_aquarium() (defined below, once _add_fish
    # exists) -- called once at the bottom of main() for the initial boot,
    # and again from _return_to_main_menu()'s "New Aquarium" for a real
    # mid-session reset.
    decorations = []

    PHASE_ICON = {"Day": "☀️", "Morning": "🌅", "Night": "🌙"}

    def _refresh_stats():
        icon = PHASE_ICON.get(environment["phase"], "☀️")
        stats.text = (
            f"Money: ${state['money']}   Food: {state['food']}   Fish: {len(fish)}"
            f"   {icon} {environment['phase']}, {environment['temperature']:.0f}°C"
        )

    def _wire_tooltip(f: Fish) -> None:
        # Not app.set_tooltip(f, fixed_text): that captures `text` once at
        # registration time, but a fish's hunger (and display_name, after a
        # rename) changes over its life. Wiring on_enter/on_leave directly,
        # once, and computing describe_fish(f) lazily inside _open() (i.e.
        # at the moment the tooltip actually opens, not when this function
        # ran) keeps it live without ever needing to re-register the
        # handlers -- re-calling set_tooltip later to "refresh" the text
        # would replace on_enter/on_leave (single-callback-slot, like
        # on_click) out from under a tooltip that's *currently* open,
        # orphaning it: nothing would ever close it again.
        state = {"timer": None, "tip": None}

        def _hide(_w=None):
            if state["timer"] is not None:
                app.cancel(state["timer"])
                state["timer"] = None
            if state["tip"] is not None:
                app.close_overlay(state["tip"])
                state["tip"] = None

        def _open():
            from cozy_tui.widgets.display.tooltip import Tooltip

            state["timer"] = None
            tip = Tooltip(f, describe_fish(f))
            state["tip"] = tip
            app.open_overlay(
                tip, modal=False, dim=False, center=False, close_on_escape=False
            )

        def _show(_w):
            _hide()
            state["timer"] = app.after(0.4, _open)

        f.on_enter(_show)
        f.on_leave(_hide)

    def _rename_fish(f: Fish) -> None:
        app.prompt(
            f"Rename your {f.species_name}",
            initial=f.display_name,
            on_submit=lambda new_name: setattr(
                f, "display_name", new_name.strip() or f.display_name
            ),
        )

    def _sell_fish(f: Fish) -> None:
        fish.remove(f)
        app.widgets.remove(f)
        clear_relationships(f, fish)
        state["money"] += f.sell_value
        _refresh_stats()
        app.toast(f"Sold {f.display_name} for ${f.sell_value}.", level="success")

    def _open_inspector(f: Fish) -> None:
        app.open_overlay(
            _build_inspector(app, f, _rename_fish, _sell_fish, state["treats"], _feed_treat),
            close_on_click_outside=True,
        )

    def _sell_decoration(d: Decoration) -> None:
        decorations.remove(d)
        app.widgets.remove(d)
        # A fish whose favorite spot just got sold adopts a new one, rather
        # than being left pining after a decoration that no longer exists.
        for f in fish:
            if f.favorite_decoration is d:
                f.favorite_decoration = (
                    random.choice(decorations) if decorations else None
                )
        state["money"] += d.sell_value
        _refresh_stats()
        app.toast(f"Sold the {d.kind} for ${d.sell_value}.", level="success")

    def _open_decoration_inspector(d: Decoration) -> None:
        app.open_overlay(
            _build_decoration_inspector(
                app, d, fish, _sell_decoration, _enter_decoration
            ),
            close_on_click_outside=True,
        )

    def _enter_decoration(d: Decoration) -> None:
        # A lightweight poll rather than hooking every individual event
        # that can change who's home (the nightly wake transition, or the
        # rarer case of a housed fish starving) -- see _build_castle_interior's
        # docstring. on_close fires no matter how the overlay is dismissed
        # (Leave, click-outside, Esc), which is also true of _refresh()'s
        # own close-then-reopen when occupants change -- `rebuilding` tells
        # on_close apart from an actual "the player left" close, so the
        # poll only ever stops on the latter.
        interior = {"box": None, "occupants": None, "rebuilding": False}

        def _on_close(_widget):
            if interior["rebuilding"]:
                interior["rebuilding"] = False
                return
            app.cancel(timer)

        def _signature():
            # Identity, mood, *and* boop-flash state -- a fish waking but
            # lingering (still occupants_of()-eligible, see fish.py's
            # _awake_in_home) or mid-attempt (_just_booped_until) needs to
            # trigger a redraw too, not just someone actually arriving or
            # leaving.
            now = time.monotonic()
            return [
                (
                    o,
                    o._awake_in_home,
                    o._just_booped_until is not None and now < o._just_booped_until,
                )
                for o in occupants_of(d, fish)
            ]

        def _show():
            interior["occupants"] = _signature()
            interior["box"] = app.open_overlay(
                _build_castle_interior(app, d, fish),
                close_on_click_outside=True,
                on_close=_on_close,
            )

        def _refresh():
            if _signature() != interior["occupants"]:
                interior["rebuilding"] = True
                app.close_overlay(interior["box"])
                _show()

        timer = app.every(1.0, _refresh)
        _show()

    def _on_eat_food(food):
        app.widgets.remove(food)

    def _on_eat_fish(eaten):
        app.widgets.remove(eaten)
        clear_relationships(eaten, fish)
        app.toast(f"The shark ate {eaten.display_name}!", level="warning", icon="🦈")
        _refresh_stats()

    def _add_fish(species: Species) -> Fish:
        f = _make_fish(
            bounds,
            foods,
            fish,
            _on_eat_food,
            _on_eat_fish,
            species,
            decorations,
            mouse_pos,
            environment,
            paused,
        )
        fish.append(f)
        app.add(f)
        _wire_tooltip(f)
        return f

    def _seed_starter_aquarium() -> None:
        """Everything a brand-new aquarium starts with -- the same starter
        decorations/fish boot has always created, factored out so
        _return_to_main_menu()'s "New Aquarium" can genuinely start over
        mid-session instead of only being meaningful at launch."""
        for kind, x in (
            ("Plant", tank_x + 3),
            ("Driftwood", tank_x + tank_w // 3),
            ("Rock", tank_x + tank_w // 2),
            ("Castle", tank_x + max(tank_w - 10, tank_w * 4 // 5)),
        ):
            d = _make_starting_decoration(kind, x)
            decorations.append(d)
            app.add(d)
        for _ in range(3):
            _add_fish(random.choice(STARTER_SPECIES))
        _refresh_stats()

    _seed_starter_aquarium()

    def _spawn_fish(species: Species):
        # Only for purchases (see the Shop below) -- unlike the starter fish
        # above, a bought fish gets a confirmation toast and a naming prompt.
        f = _add_fish(species)
        _refresh_stats()
        if species.predator:
            app.toast(f"Bought a {species.name}! Watch out, fish...", level="warning")
        else:
            app.toast(f"Bought a {species.name}!", level="success")
        _rename_fish(f)

    def _stress_test():
        # Free, no rename prompt -- this is a dev/debug key for proving the
        # diff-renderer stays smooth with a lot of independently-moving
        # Fish widgets at once (see the module docstring), not a normal
        # gameplay action.
        added = 0
        while len(fish) < STRESS_TEST_TARGET:
            _add_fish(random.choice(STARTER_SPECIES))
            added += 1
        _refresh_stats()
        if added:
            app.toast(
                f"Stress test: spawned {added} more fish ({len(fish)} total).",
                level="info",
            )
        else:
            app.toast(
                f"Already at the stress-test cap ({STRESS_TEST_TARGET} fish).",
                level="info",
            )

    def _buy_food():
        state["food"] += FOOD_PACK_SIZE
        state["food_spent_today"] += FOOD_PACK_PRICE
        _refresh_stats()
        app.toast(f"Bought {FOOD_PACK_SIZE} fish food!", level="success")

    def _buy_treat(item) -> None:
        state["treats"][item.kind] = state["treats"].get(item.kind, 0) + item.pack_size
        unit = "" if item.pack_size == 1 else f" x{item.pack_size}"
        app.toast(f"Bought {item.kind}{unit}.", level="success")

    def _feed_treat(f: Fish, kind: str) -> None:
        state["treats"][kind] -= 1
        f.hunger, f.health = feed(f.hunger, f.health)
        if kind == "Pizza":
            # Universal delight, regardless of species or favorite --
            # matching Pizza's flavor text (see constants.TREAT_SHOP_ITEMS):
            # nobody has it as a declared favorite, everyone loves it anyway.
            app.toast(
                f"{f.display_name} devoured an entire {kind}. Nobody knows why.",
                level="success",
                icon="🍕",
            )
        elif kind in f.favorite_foods:
            # Flavor only -- same feed() relief as any other treat above,
            # just a nicer reaction. Personality, not a better stat stick.
            item = next(i for i in TREAT_SHOP_ITEMS if i.kind == kind)
            app.toast(
                f"{f.display_name} lights up at the {kind}! Favorite food.",
                level="success",
                icon=item.emoji,
            )
        else:
            app.toast(f"Fed {f.display_name} some {kind}.", level="success")
        _refresh_stats()

    def _add_decoration(item: DecorationItem) -> None:
        width = max(text_width(line) for line in item.art)
        x = random.uniform(tank_x + 1, max(tank_x + 1, tank_x + tank_w - 1 - width))
        d = Decoration(
            x,
            floor_y - len(item.art) + 1,
            item.art,
            item.colors,
            kind=item.kind,
            price=item.price,
            capacity=item.capacity,
        )
        decorations.append(d)
        # Insert right after the last existing Decoration (not app.add(),
        # which would append it *after* every already-added Fish -- new
        # decorations still need to draw behind all fish, matching every
        # decoration already in the tank; see the module docstring).
        insert_at = 0
        for i, w in enumerate(app.widgets):
            if isinstance(w, Decoration):
                insert_at = i + 1
        app.widgets.insert(insert_at, d)
        app.toast(f"Bought a {item.kind}!", level="success")

    def _snapshot() -> dict:
        """Convert live Widgets to plain JSON-friendly state."""
        fish_index = {id(f): i for i, f in enumerate(fish)}
        decoration_index = {id(d): i for i, d in enumerate(decorations)}
        return {
            "state": dict(state),
            "day": day_count["n"],
            "foods": [{"x": food.fx, "y": food.fy} for food in foods],
            "decorations": [
                {"kind": d.kind, "x": d.fx, "y": d.fy, "price": d.price}
                for d in decorations
            ],
            "fish": [
                {
                    "species": f.species_name,
                    "name": f.display_name,
                    "x": f.fx,
                    "y": f.fy,
                    "vx": f.vx,
                    "vy": f.vy,
                    "speed": f.speed,
                    "hunger": f.hunger,
                    "health": f.health,
                    "personality": f.personality,
                    "is_sleepy": f.is_sleepy,
                    "age_seconds": max(0.0, time.monotonic() - f.birth_time),
                    "favorite": decoration_index.get(id(f.favorite_decoration)),
                }
                for f in fish
            ],
            "relationships": [
                {
                    "a": fish_index[id(a)],
                    "b": fish_index[id(b)],
                    "score": rel.score,
                    "memories": list(rel.memories),
                }
                for a, b, rel in all_relationship_pairs(fish)
            ],
        }

    def _clear_tank() -> None:
        """Removes every fish/food/decoration widget and resets `state`/
        `day_count`/`current_save` back to defaults -- the common first
        half of both loading a save (_load_snapshot) and starting fresh
        mid-session (_return_to_main_menu()'s "New Aquarium")."""
        for widget in [*foods, *fish, *decorations]:
            if widget in app.widgets:
                app.widgets.remove(widget)
        foods.clear()
        fish.clear()
        decorations.clear()
        state.clear()
        state.update(
            {
                "money": 100,
                "food": 15,
                "food_spent_today": 0,
                "donations_today": 0,
                "welfare_enabled": True,
                "bubbles_enabled": True,
                "treats": {},
            }
        )
        day_count["n"] = 0
        current_save["name"] = None

    def _load_snapshot(snapshot: dict) -> None:
        """Replace the tank from a validated save while retaining the UI."""
        _clear_tank()
        state.update(snapshot.get("state", {}))
        day_count["n"] = int(snapshot.get("day", 0))
        for saved in snapshot.get("decorations", []):
            item = DECORATION_CATALOG.get(saved.get("kind"))
            if item is None:
                continue
            d = Decoration(
                saved.get("x", tank_x + 1),
                saved.get("y", floor_y),
                item.art,
                item.colors,
                kind=item.kind,
                price=item.price,
                capacity=item.capacity,
            )
            decorations.append(d)
            app.add(d)
        for saved in snapshot.get("fish", []):
            species = next(
                (s for s in SHOP_ITEMS if s.name == saved.get("species")),
                STARTER_SPECIES[0],
            )
            f = Fish(
                saved.get("x", tank_x + 1),
                saved.get("y", tank_y + 1),
                bounds,
                foods,
                fish,
                _on_eat_food,
                _on_eat_fish,
                species.right,
                species.left,
                species.color,
                is_predator=species.predator,
                decorations=decorations,
                species_name=species.name,
                mouse_pos=mouse_pos,
                price=species.price,
                environment=environment,
                paused=paused,
            )
            f.display_name = saved.get("name", species.name)
            for attr in (
                "vx",
                "vy",
                "speed",
                "hunger",
                "health",
                "personality",
                "is_sleepy",
            ):
                if attr in saved:
                    setattr(f, attr, saved[attr])
            f.birth_time = time.monotonic() - max(0.0, saved.get("age_seconds", 0.0))
            fish.append(f)
            app.add(f)
            _wire_tooltip(f)
        for f, saved in zip(fish, snapshot.get("fish", [])):
            favorite = saved.get("favorite")
            f.favorite_decoration = (
                decorations[favorite]
                if isinstance(favorite, int) and 0 <= favorite < len(decorations)
                else None
            )
        for saved in snapshot.get("relationships", []):
            a_idx, b_idx = saved.get("a"), saved.get("b")
            if (
                not isinstance(a_idx, int)
                or not isinstance(b_idx, int)
                or not (0 <= a_idx < len(fish))
                or not (0 <= b_idx < len(fish))
            ):
                continue
            rel = set_relationship(fish[a_idx], fish[b_idx], saved.get("score", 0.0))
            rel.memories.extend(saved.get("memories", []))
        for saved in snapshot.get("foods", []):
            food = Food(saved.get("x", tank_x + 1), saved.get("y", tank_y + 1))
            foods.append(food)
            app.add(food)
        _refresh_stats()

    def _save_game() -> None:
        # Once attached to a save (loaded, or saved manually once already
        # this session), Save just writes back into it -- no prompt, no new
        # file every day. Only the very first save of a fresh session (never
        # loaded, never saved) asks for a name.
        if current_save["name"] is not None:
            _write_named_save(current_save["name"])
            return
        default_name = f"Aquarium Day {day_count['n']}"
        app.prompt(
            "Save aquarium as",
            initial=default_name,
            on_submit=lambda name: _write_named_save(name),
        )

    def _write_named_save(name: str) -> None:
        payload_path = write_save(name, _snapshot())
        current_save["name"] = name
        app.toast(f"Saved {payload_path.stem}.", level="success")
        if cloud["key"] is not None:
            # Fire-and-forget: the local save above already succeeded and
            # is what Load reads from, so a slow/failed cloud sync should
            # never block or roll back the (already-real) local save.
            app.run_worker(
                upload_cloud_save,
                cloud["key"],
                name,
                read_save(payload_path),
                on_result=lambda _r: app.toast("Synced to cloud.", level="success"),
                on_error=lambda _e: app.toast(
                    "Cloud sync failed -- saved locally only.", level="warning"
                ),
            )

    def _open_load_menu(on_loaded=None) -> None:
        cards = list_saves()

        def _load(path):
            try:
                payload = read_save(path)
                _load_snapshot(payload["aquarium"])
                current_save["name"] = payload["metadata"].get("name", path.stem)
                app.close_overlay(box)
                if on_loaded is not None:
                    on_loaded()
                app.toast(f"Loaded {path.stem}.", level="success")
            except (OSError, ValueError) as error:
                app.toast(f"Couldn't load save: {error}", level="error")

        def _rename(path, old_name, new_name):
            try:
                rename_save(path, new_name)
                if current_save["name"] == old_name:
                    current_save["name"] = new_name
                app.toast(f"Renamed to {new_name}.", level="success")
            except (OSError, ValueError) as error:
                app.toast(f"Couldn't rename: {error}", level="error")
            app.close_overlay(box)
            _open_load_menu(on_loaded)

        def _duplicate(path, new_name):
            try:
                duplicate_save(path, new_name)
                app.toast(f"Duplicated as {new_name}.", level="success")
            except (OSError, ValueError) as error:
                app.toast(f"Couldn't duplicate: {error}", level="error")
            app.close_overlay(box)
            _open_load_menu(on_loaded)

        def _delete(path, name):
            delete_save(path)
            if current_save["name"] == name:
                # The save this session was attached to is gone -- the next
                # Save should ask for a fresh name rather than silently
                # recreating the exact file just deleted.
                current_save["name"] = None
            app.toast(f"Deleted {name}.", level="success")
            app.close_overlay(box)
            _open_load_menu(on_loaded)

        box = build_save_menu(app, cards, _load, _rename, _duplicate, _delete)
        app.open_overlay(box, close_on_click_outside=True)

    def _open_shop():
        app.open_overlay(
            _build_shop(app, state, _spawn_fish, _buy_food, _add_decoration, _buy_treat),
            close_on_click_outside=True,
        )

    def _open_settings():
        def _setup_cloud():
            key = generate_cloud_key()
            cloud["key"] = key
            store_cloud_key(key)
            app.toast(
                f"Cloud Saves set up. Your key: {key} -- write it down, it's "
                "the only way to get your saves back on a new PC.",
                level="info",
                duration=8.0,
            )
            _open_settings()

        def _change_key():
            def _use_key(entered: str):
                entered = entered.strip()
                if not entered:
                    return
                cloud["key"] = entered
                store_cloud_key(entered)
                app.toast("Cloud Key updated.", level="success")
                _open_settings()

            app.prompt("Enter an existing Cloud Key", on_submit=_use_key)

        def _forget_key():
            def _yes():
                cloud["key"] = None
                store_cloud_key(None)
                app.toast(
                    "Cloud Key forgotten -- saves stay local only now.", level="info"
                )
                _open_settings()

            app.confirm(
                "Forget this Cloud Key? Local saves are untouched, but this "
                "machine won't sync to the cloud until you set one up again.",
                on_yes=_yes,
            )

        def _restore():
            key = cloud["key"]
            if key is None:
                return

            def _download(name: str) -> None:
                def _on_downloaded(payload):
                    write_save(name, payload["aquarium"])
                    app.toast(f"Downloaded {name} -- find it in Load.", level="success")

                app.run_worker(
                    download_cloud_save,
                    key,
                    name,
                    on_result=_on_downloaded,
                    on_error=lambda error: app.toast(
                        f"Couldn't download: {error}", level="error"
                    ),
                )

            def _on_listed(cloud_saves):
                app.open_overlay(
                    build_restore_menu(app, cloud_saves, _download),
                    close_on_click_outside=True,
                )

            app.run_worker(
                list_cloud_saves,
                key,
                on_result=_on_listed,
                on_error=lambda error: app.toast(
                    f"Couldn't reach the cloud: {error}", level="error"
                ),
            )

        app.open_overlay(
            _build_settings(
                app,
                state,
                cloud["key"],
                _setup_cloud,
                _change_key,
                _forget_key,
                _restore,
            ),
            close_on_click_outside=True,
        )

    def _open_help():
        app.open_overlay(build_help_menu(app), close_on_click_outside=True)

    def _open_start_menu(on_resume=None):
        # `on_resume` is only ever passed by _return_to_main_menu() (a real
        # mid-session reset is now possible -- see _new_aquarium below);
        # boot's own call leaves it None, exactly as before this existed.
        menu = None

        def _new_aquarium():
            _clear_tank()
            _seed_starter_aquarium()
            app.close_overlay(menu)

        def _load_save():
            _open_load_menu(lambda: app.close_overlay(menu))

        def _settings():
            _open_settings()

        def _help():
            _open_help()

        # Boot's call (on_resume=None) keeps today's exact behavior: no
        # Resume button, Esc/click-outside do nothing. Reached mid-session
        # via Ctrl+C, both dismiss it too -- on_close (fires no matter
        # which of Resume/Esc/click-outside/New/Load is what closes it)
        # is what actually unpauses, so all of them resume correctly.
        resumable = on_resume is not None
        menu = build_start_menu(
            app, _new_aquarium, _load_save, _settings, _help, on_resume
        )
        app.open_overlay(
            menu,
            close_on_escape=resumable,
            close_on_click_outside=resumable,
            on_close=(lambda _w: paused.update(value=False)) if resumable else None,
        )

    def _confirm_quit():
        app.confirm(
            "Quit without saving? Progress since your last save will be lost.",
            on_yes=lambda: app.quit(),
        )

    def _open_pause_menu():
        # Esc used to instantly quit the whole app -- a single accidental
        # keypress destroying an unsaved session. Now it pauses instead:
        # every Fish/BubbleField freezes solid (see their own `paused`
        # checks), and Quit lives behind this menu's own confirmation.
        paused["value"] = True
        box = None

        def _resume():
            app.close_overlay(box)

        box = build_pause_menu(
            app,
            on_resume=_resume,
            on_save=_save_game,
            on_settings=_open_settings,
            on_help=_open_help,
            on_quit=_confirm_quit,
        )
        app.open_overlay(
            box,
            close_on_click_outside=True,
            on_close=lambda _w: paused.update(value=False),
        )

    app.add(Button(2, 2, "Open Shop").on_click(lambda _w: _open_shop()))
    app.add(Button(16, 2, "Settings").on_click(lambda _w: _open_settings()))
    app.add(Button(29, 2, "Save").on_click(lambda _w: _save_game()))
    app.add(Button(39, 2, "Load").on_click(lambda _w: _open_load_menu()))
    app.add(Button(49, 2, "Pause").on_click(lambda _w: _open_pause_menu()))
    app.on_key("s", lambda: _open_shop())
    app.on_key("S", lambda: _open_shop())
    app.on_key("g", lambda: _open_settings())
    app.on_key("G", lambda: _open_settings())
    app.on_key("p", lambda: _save_game())
    app.on_key("P", lambda: _save_game())
    app.on_key("l", lambda: _open_load_menu())
    app.on_key("L", lambda: _open_load_menu())
    app.on_key("h", lambda: _open_help())
    app.on_key("H", lambda: _open_help())
    app.on_key("z", lambda: _stress_test())
    app.on_key("Z", lambda: _stress_test())

    def _on_mouse(event):
        if isinstance(event, MouseMove):
            mouse_pos["x"], mouse_pos["y"] = float(event.col), float(event.row)
            return False  # not consumed -- normal hover dispatch still runs (tooltips)
        if any(e.modal for e in app._overlays):
            return False  # a modal (Shop/Inspector/prompt) is open -- let it handle its own clicks
        if isinstance(event, MouseClick) and event.btn == 0:
            clicked = fish_at(fish, event.col, event.row)
            if clicked is not None:
                _open_inspector(clicked)
                return True
            clicked_dec = decoration_at(decorations, event.col, event.row)
            if clicked_dec is not None:
                _open_decoration_inspector(clicked_dec)
                return True
            x0, y0, x1, y1 = bounds
            if x0 <= event.col <= x1 and y0 <= event.row <= y1:
                if state["food"] <= 0:
                    app.toast("Out of food -- visit the shop!", level="warning")
                    return True
                state["food"] -= 1
                food = Food(event.col, event.row)
                foods.append(food)
                app.add(food)
                _refresh_stats()
                return True
        return False

    app.on_mouse(_on_mouse)

    def _check_emergency_welfare():
        if not should_grant_welfare(
            state["money"], state["food"], len(fish), state.get("welfare_enabled", True)
        ):
            return
        # A gift, not a purchase -- _add_fish() directly, skipping
        # _spawn_fish()'s "Bought a ..." toast and forced rename prompt,
        # so this reads as one clear message instead of a noisy pile-up.
        state["money"] += WELFARE_MONEY_GRANT
        state["food"] += WELFARE_FOOD_GRANT
        _add_fish(random.choice(STARTER_SPECIES))
        _refresh_stats()
        app.toast(
            "Aquarium Welfare: your aquarium fell on hard times -- here's a "
            f"fresh start. +1 Fish, +{WELFARE_FOOD_GRANT} Food, +${WELFARE_MONEY_GRANT}. Good luck.",
            level="info",
            icon="❤️",
            duration=6.0,
        )

    def _fire_morning_vignette():
        # A one-line Night -> Morning flavor toast for a Friend pair -- see
        # choose_morning_vignette()'s docstring for why this is cosmetic
        # texture, not a real per-fish wake-time simulation. "wake"/"resist"
        # also get a short in-tank caption right where the pair actually
        # are -- the toast is the headline, this is the cute moment.
        result = choose_morning_vignette(find_mutual_friend_pairs(fish))
        if result is None:
            return
        waker, sleeper, flavor = result

        def _add_vignette(wakes: bool) -> None:
            vignette = MorningVignette(
                (waker.fx + sleeper.fx) / 2,
                min(waker.fy, sleeper.fy) - 2,
                waker._glyph(),
                sleeper._glyph(),
                VIGNETTE_STYLE,
                wakes=wakes,
            )
            app.add(vignette)
            app.after(
                vignette.total_seconds,
                lambda: (
                    app.widgets.remove(vignette) if vignette in app.widgets else None
                ),
            )

        if flavor == "wake":
            app.toast(
                f"{waker.display_name} notices {sleeper.display_name} is still "
                f"asleep... *boop*... {sleeper.display_name} woke up!",
                level="info",
            )
            record_wake_up(waker, sleeper)
            _add_vignette(wakes=True)
        elif flavor == "resist":
            app.toast(
                f"{waker.display_name} tries to boop {sleeper.display_name} awake... "
                f"but {sleeper.display_name} is too sleepy to notice!",
                level="info",
            )
            _add_vignette(wakes=False)
        else:
            app.toast(
                f"{waker.display_name} notices {sleeper.display_name} is still "
                f"asleep. {waker.display_name} leaves without them.",
                level="info",
            )

    def _check_night_events():
        # Two lightweight relationship-building checks run once at the
        # Night -> Morning transition, alongside the vignette: pairs who
        # ended up sleeping together (a shared container, or just close on
        # the floor), and a homeless fish whose nearest housed tankmate
        # benefits from the spot it didn't get. Both are real,
        # currently-triggerable events -- see relationships.py's module
        # docstring for which interactions from the original design aren't
        # wired up yet (no mechanic exists for them today).
        counted_together = set()
        for a in fish:
            for b in fish:
                if a is b:
                    continue
                key = frozenset((id(a), id(b)))
                if key in counted_together:
                    continue
                together = (
                    a.sleeping_in is not None and a.sleeping_in is b.sleeping_in
                ) or (
                    a.sleeping_in is None
                    and b.sleeping_in is None
                    and math.hypot(a.fx - b.fx, a.fy - b.fy) <= SLEEP_CLOSE_DISTANCE
                )
                if together:
                    counted_together.add(key)
                    record_slept_together(a, b)

        counted_gave_up = set()
        for f in fish:
            if f.sleeping_in is not None:
                continue
            housed_nearby = [
                o
                for o in fish
                if o is not f
                and o.sleeping_in is not None
                and math.hypot(o.fx - f.fx, o.fy - f.fy) <= RELATIONSHIP_NEARBY_RADIUS
            ]
            if not housed_nearby:
                continue
            beneficiary = min(
                housed_nearby, key=lambda o: math.hypot(o.fx - f.fx, o.fy - f.fy)
            )
            key = frozenset((id(f), id(beneficiary)))
            if key in counted_gave_up:
                continue
            counted_gave_up.add(key)
            record_gave_up_home(f, beneficiary)

    def _start_sleepy_holds():
        # Must run in this exact spot -- right at the Night->Morning
        # transition, before any fish's own draw() has processed the new
        # phase -- because a non-Sleepy tankmate's `sleeping_in` reverts to
        # None the instant its own next frame sees the phase change. One
        # tick later (_process_sleepy_holds, on the ordinary 1-second
        # timer) would already be too late to find who was actually
        # sleeping alongside a Sleepy fish overnight.
        for f in fish:
            if not f.is_sleepy or f.sleeping_in is None:
                continue
            f._holding_asleep = True
            f._held_since = time.monotonic()
            tankmates = [
                o for o in fish if o is not f and o.sleeping_in is f.sleeping_in
            ]
            waker, tier = find_eligible_waker(f, tankmates)
            if waker is not None:
                f._wake_waker = waker
                f._wake_threshold = roll_wake_threshold(tier)
                f._wake_next_attempt = time.monotonic() + WAKE_ATTEMPT_INTERVAL_SECONDS

    def _process_sleepy_holds():
        # The ongoing half, on the ordinary per-second tick: resolve an
        # attempt once its cooldown has passed, or force a wake once
        # SLEEPY_HOLD_MAX_SECONDS has passed regardless -- the fallback
        # that keeps "never permanently impossible" true even when
        # _start_sleepy_holds() found nobody eligible to try at all.
        now = time.monotonic()
        for f in fish:
            if not f._holding_asleep:
                continue
            if now - f._held_since >= SLEEPY_HOLD_MAX_SECONDS:
                f._holding_asleep = False
                continue
            waker = f._wake_waker
            if waker is None or waker not in fish or now < f._wake_next_attempt:
                continue
            # Every attempt actually happens visibly -- see BOOP_FLASH_SECONDS
            # -- resisted or not, not just the one that finally succeeds.
            waker._just_booped_until = now + BOOP_FLASH_SECONDS
            if resolve_wake_attempt(f._wake_attempts_used, f._wake_threshold):
                record_wake_up(waker, f)
                app.toast(
                    f"{waker.display_name} notices {f.display_name} is still "
                    f"asleep... *boop*... {f.display_name} woke up!",
                    level="info",
                )
                f._holding_asleep = False
            else:
                f._wake_attempts_used += 1
                f._wake_next_attempt = now + WAKE_ATTEMPT_INTERVAL_SECONDS

    def _update_environment():
        previous_phase = environment["phase"]
        fraction = compute_time_of_day(
            time.monotonic() - session_start, AGE_SECONDS_PER_DAY
        )
        environment["phase"] = get_day_phase(fraction)
        environment["temperature"] = compute_water_temperature(fraction)
        app.style.bg = lerp_color(DAY_BG, NIGHT_BG, night_blend(fraction))
        if previous_phase == "Night" and environment["phase"] == "Morning":
            _check_night_events()
            _fire_morning_vignette()
            _start_sleepy_holds()

    def _hunger_step() -> float:
        # Night: sleeping fish get hungry slower. Heat: a stressed fish
        # burns through energy faster. Both are independent of each other
        # and of Lazy/Greedy/etc, which act on speed, not hunger.
        step = HUNGER_STEP
        if environment["phase"] == "Night":
            step *= NIGHT_HUNGER_MULT
        if environment["temperature"] > HOT_TEMP_THRESHOLD:
            step *= HOT_HUNGER_MULT
        return step

    def _per_second_tick():
        if paused["value"]:
            return  # environment/hunger/breeding all frozen while paused
        _update_environment()
        hunger_step = _hunger_step()
        dead = []
        for f in fish:
            f.hunger, f.health = decay_hunger(
                f.hunger, f.health, hunger_step=hunger_step
            )
            if f.health <= 0:
                dead.append(f)
        for f in dead:
            fish.remove(f)
            app.widgets.remove(f)
            clear_relationships(f, fish)
            app.toast(f"{f.display_name} starved to death...", level="error", icon="💀")
        _refresh_stats()
        hungry_levels = [f.hunger for f in fish]
        if should_warn_hungry(hungry_levels, hungry_warning_active["value"]):
            hungry_warning_active["value"] = True
            hungry_names = [
                f.display_name for f in fish if f.hunger > HUNGER_WARNING_THRESHOLD
            ]
            message = (
                f"{hungry_names[0]} is getting hungry!"
                if len(hungry_names) == 1
                else f"{len(hungry_names)} fish are getting hungry!"
            )
            app.toast(message, level="warning", icon="⚠️", duration=5.0)
        elif not any(level > HUNGER_WARNING_THRESHOLD for level in hungry_levels):
            # Back under the threshold -- rearm the one-shot warning so it
            # can fire again next time hunger climbs, instead of staying
            # permanently latched from the first warning of the session.
            hungry_warning_active["value"] = False
        _check_emergency_welfare()
        _process_sleepy_holds()

        # Visitor donations pay out the moment they happen instead of being
        # bundled into the once-a-day summary -- see roll_visitor_donation()
        # for why this fires at roughly the same daily rate as before.
        attractiveness = compute_attractiveness(fish, decorations, foods)
        visitors = attractiveness // VISITORS_PER_ATTRACTIVENESS
        donation = roll_visitor_donation(visitors)
        if donation:
            state["money"] += donation
            state["donations_today"] += donation
            _refresh_stats()
            app.toast(f"A visitor donated ${donation}!", level="info")

    def _try_breeding():
        if len(fish) >= MAX_FISH_FOR_BREEDING:
            return
        for parent_a, parent_b in find_breeding_pairs(fish):
            if len(fish) >= MAX_FISH_FOR_BREEDING:
                break
            if random.random() >= BREED_CHANCE:
                continue
            species_name = choose_baby_species_name(parent_a, parent_b)
            species = next(s for s in SHOP_ITEMS if s.name == species_name)
            baby_x = (parent_a.fx + parent_b.fx) / 2
            baby_y = (parent_a.fy + parent_b.fy) / 2
            baby = Fish(
                baby_x,
                baby_y,
                bounds,
                foods,
                fish,
                _on_eat_food,
                _on_eat_fish,
                species.right,
                species.left,
                species.color,
                is_predator=species.predator,
                decorations=decorations,
                species_name=species.name,
                mouse_pos=mouse_pos,
                price=species.price,
                environment=environment,
                paused=paused,
            )
            fish.append(baby)
            app.add(baby)
            _wire_tooltip(baby)
            app.toast(
                f"{parent_a.display_name} and {parent_b.display_name} had a baby! "
                f"Welcome, {baby.display_name}.",
                level="success",
                icon="👶",
            )
        _refresh_stats()

    def _daily_tick():
        if paused["value"]:
            return
        day_count["n"] += 1
        decay_relationships(fish)
        _try_breeding()
        attractiveness = compute_attractiveness(fish, decorations, foods)
        # Donations were already paid out (and toasted) second by second in
        # _per_second_tick as they happened -- only ticket sales and the
        # maintenance grant are new money here. `donations` is still read
        # from state for the summary below, then reset for the next day.
        visitors, ticket_sales, _donations = compute_visitor_income(attractiveness)
        grant = MAINTENANCE_GRANT
        food_expense = state["food_spent_today"]
        donations = state["donations_today"]
        state["food_spent_today"] = 0
        state["donations_today"] = 0
        state["money"] += ticket_sales + grant
        net = ticket_sales + donations + grant - food_expense
        _refresh_stats()

        box = _build_daily_summary(
            app.style,
            day_count["n"],
            visitors,
            ticket_sales,
            donations,
            grant,
            food_expense,
            net,
        )
        app.open_overlay(
            box, modal=False, dim=False, center=True, close_on_escape=False
        )
        app.after(6.0, lambda: app.close_overlay(box))

    app.every(1.0, _per_second_tick)
    app.every(AGE_SECONDS_PER_DAY, _daily_tick)

    def _return_to_main_menu():
        # Ctrl+C reaches here even through a modal (see cozy_tui's
        # App._handle_ctrl_c()) -- close whatever's currently stacked
        # first (there's no public "close everything", so this loops the
        # ordinary "close the topmost" call), same as the Pause Menu,
        # pause the simulation so nothing keeps aging/starving behind the
        # menu, and unpause via open_overlay's own on_close hook so
        # Resume, Esc, and click-outside all correctly resume regardless
        # of which one is used.
        while app._overlays:
            app.close_overlay()
        paused["value"] = True
        # The menu is the only overlay open at this point, so closing
        # "the topmost" (no widget arg needed) always means this one.
        _open_start_menu(on_resume=lambda: app.close_overlay())

    app.on_key(Key.ESC, lambda: _open_pause_menu())
    app.on_key(Key.CTRL_C, _return_to_main_menu)
    _open_start_menu()
    app.run()


if __name__ == "__main__":
    main()
