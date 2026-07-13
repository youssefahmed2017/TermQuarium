"""Fish/Decoration inspector panels, the Daily Summary, and Settings --
small Box-building functions with no shared state between them."""

from cozy_tui import Style, clipboard
from cozy_tui.widgets import Box, Button, Checkbox, Label

from .fish import Fish, occupants_of
from .relationships import relationship_state
from .styles import HEART_STYLE, MUTED
from .tank_objects import Decoration


def _build_inspector(app, f: Fish, on_rename, on_sell) -> Box:
    """A read-only stat card for one Fish (name/species/age+growth/health/
    hunger/personality/favorite spot/sell value) with Rename and Sell
    buttons. A snapshot at open-time, not live-refreshing -- matching the
    Shop's own money label, which likewise only updates on explicit actions.
    Sell asks for confirmation first (app.confirm(), stacked on top of this
    modal exactly like Rename's prompt already does) since it's the one
    irreversible action here.

    "Home tonight" (only shown while actually housed) is deliberately
    separate from "Favorite spot": the favorite spot is a permanent daytime
    hangout picked once at birth, while a home is re-claimed fresh every
    night (see Fish._claim_home()) and isn't always the favorite spot --
    a fish can have one of each, or neither.

    The relationship section (Step 8) never shows the raw score -- just
    its state (relationship_state()) and its most recent reasons, straight
    from that pair's shared memory log."""
    spot = (
        f.favorite_decoration.kind if f.favorite_decoration is not None else "none yet"
    )
    box = Box(0, 0, "380x340", title=f.display_name, border="rounded", style=app.style)
    box.add(Label(2, 1, f"Species: {f.species_name}"))
    box.add(Label(2, 2, f"Age: {f.age_days:.1f} days ({f.growth_stage})"))
    box.add(Label(2, 3, f"Health: {f.health:.0f}%"))
    box.add(Label(2, 4, f"Hunger: {f.hunger:.0f}%"))
    personality_line = f"Personality: {f.personality}"
    if f.is_sleepy:
        personality_line += " (also Sleepy 😴)"
    box.add(Label(2, 5, personality_line))
    box.add(Label(2, 6, f"Favorite spot: {spot}"))
    y = 7
    if f.sleeping_in is not None:
        box.add(Label(2, y, f"Home tonight: {f.sleeping_in.kind} 😴"))
        y += 1

    def _add_bond(other, style):
        nonlocal y
        label, emoji = relationship_state(f.relationships[other].score)
        box.add(Label(2, y, f"{label}: {other.display_name} {emoji}", style))
        y += 1
        for reason in f.relationships[other].memories[-2:]:
            box.add(Label(4, y, f"- {reason}", MUTED))
            y += 1

    if f.friend is not None:
        _add_bond(f.friend, HEART_STYLE)
    if f.rival is not None:
        _add_bond(f.rival, Style(fg="bright_red"))

    box.add(Label(2, y, f"Sell value: ${f.sell_value}"))
    y += 2

    def _on_sell(_widget):
        app.confirm(
            f"Sell {f.display_name} for ${f.sell_value}?",
            on_yes=lambda: (on_sell(f), app.close_overlay(box)),
        )

    box.add(Button(2, y, "Rename").on_click(lambda _w: on_rename(f)))
    box.add(Button(14, y, "Sell").on_click(_on_sell))
    box.add(Button(24, y, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def _build_decoration_inspector(app, d: Decoration, fish, on_sell) -> Box:
    """Decorations are sellable too -- an emergency option (per the user's
    own framing: "instead of game over, I guess the castle has to go...")
    rather than just cosmetic. Sell asks for confirmation first, same
    pattern as the Fish Inspector's Sell button.

    Containers (capacity > 0, e.g. the Castle) also show who's sleeping
    inside right now -- clicking one at night is the "enter the decoration"
    moment: the fish tucked inside are invisible in the tank itself (see
    Fish.draw()'s early return once _entered), so this is the only place to
    actually see them until morning."""
    box = Box(0, 0, "340x220", title=d.kind, border="rounded", style=app.style)
    y = 1
    if d.is_container:
        occupants = occupants_of(d, fish)
        box.add(Label(2, y, f"Capacity: {len(occupants)}/{d.capacity}"))
        y += 1
        if occupants:
            for guest in occupants:
                box.add(Label(2, y, f"😴 {guest.display_name}", MUTED))
                y += 1
        else:
            box.add(Label(2, y, "(nobody home right now)", MUTED))
            y += 1
        y += 1
    box.add(Label(2, y, f"Sell value: ${d.sell_value}"))
    y += 2

    def _on_sell(_widget):
        app.confirm(
            f"Sell this {d.kind} for ${d.sell_value}?",
            on_yes=lambda: (on_sell(d), app.close_overlay(box)),
        )

    box.add(Button(2, y, "Sell").on_click(_on_sell))
    box.add(Button(12, y, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def _build_daily_summary(
    style,
    day: int,
    visitors: int,
    ticket_sales: int,
    donations: int,
    grant: int,
    food_expense: int,
    net: int,
) -> Box:
    """The end-of-day report -- non-modal and auto-dismissing (see main()),
    since it's a periodic ceremony, not something that should interrupt
    whatever the player's doing every couple of minutes."""
    green, red = Style(fg="bright_green"), Style(fg="bright_red")
    box = Box(0, 0, "380x220", title=f"Day {day}", border="rounded", style=style)
    box.add(Label(2, 1, f"Visitors: {visitors}"))
    box.add(Label(2, 2, f"Ticket Sales: +${ticket_sales}", green))
    box.add(Label(2, 3, f"Donations Today: +${donations}", green))
    box.add(Label(2, 4, f"Maintenance Grant: +${grant}", green))
    box.add(Label(2, 5, f"Food Expenses: -${food_expense}", red))
    sign = (
        "+" if net >= 0 else "-"
    )  # goes before the $, not net's own minus (avoids "$-20")
    box.add(
        Label(
            2,
            7,
            f"Net Profit: {sign}${abs(net)}",
            Style(fg=green.fg if net >= 0 else red.fg, styles=["bold"]),
        )
    )
    return box


def _build_settings(
    app,
    state,
    cloud_key,
    on_setup_cloud,
    on_change_key,
    on_forget_key,
    on_restore,
) -> Box:
    """Gameplay (Emergency Aquarium Welfare), Display (ambient bubbles), and
    Cloud Saves. Checked state lives directly in `state`, the same dict
    everything else in this economy reads/writes. `cloud_key` is a snapshot
    at open-time (None if cloud saves has never been set up on this
    machine); the four callbacks are aquarium.py's actual network/storage
    actions -- this function only builds the box and closes itself before
    handing off, so it doesn't need to know how any of them work."""
    box = Box(0, 0, "440x340", title="Settings", border="rounded", style=app.style)
    box.add(Label(2, 1, "Gameplay", Style(styles=["bold"])))

    welfare_cb = Checkbox(
        2, 3, "Emergency Aquarium Welfare", checked=state.get("welfare_enabled", True)
    )
    welfare_cb.on_change(lambda checked: state.update(welfare_enabled=checked))
    box.add(welfare_cb)

    box.add(Label(2, 5, "If enabled, a bankrupt tank (no money, no food,", MUTED))
    box.add(Label(2, 6, "no fish) gets a small fresh start instead of", MUTED))
    box.add(Label(2, 7, "staying empty forever. Turn it off for hardcore mode.", MUTED))

    box.add(Label(2, 9, "Display", Style(styles=["bold"])))

    bubbles_cb = Checkbox(
        2, 11, "Ambient Bubbles", checked=state.get("bubbles_enabled", True)
    )
    bubbles_cb.on_change(lambda checked: state.update(bubbles_enabled=checked))
    box.add(bubbles_cb)

    box.add(Label(2, 13, "Purely cosmetic rising bubbles. Turn off if you", MUTED))
    box.add(Label(2, 14, "find them distracting.", MUTED))

    box.add(Label(2, 16, "Cloud Saves", Style(styles=["bold"])))

    def _run_and_close(callback):
        # Every cloud action needs this Settings box gone before it runs --
        # setup/restore reopen a fresh Settings once they're done (so the
        # key/key-less state shown here stays honest), and none of them
        # should have to know this box exists to close it themselves.
        def _handler(_w=None):
            app.close_overlay(box)
            callback()

        return _handler

    if cloud_key:
        box.add(Label(2, 18, f"Key: {cloud_key}", MUTED))

        def _copy(_w=None):
            clipboard.copy(cloud_key)
            app.toast("Cloud Key copied.", level="success")

        box.add(Button(2, 20, "Copy Key").on_click(_copy))
        box.add(Button(16, 20, "Use a Different Key").on_click(_run_and_close(on_change_key)))
        box.add(Button(2, 22, "Restore My Saves").on_click(_run_and_close(on_restore)))
        box.add(Button(22, 22, "Forget Key").on_click(_run_and_close(on_forget_key)))
    else:
        box.add(Label(2, 18, "Not set up yet -- saves stay local only.", MUTED))
        box.add(Button(2, 20, "Set Up Cloud Saves").on_click(_run_and_close(on_setup_cloud)))

    box.add(Button(2, 24, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box
