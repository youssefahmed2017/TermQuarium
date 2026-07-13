"""Small reusable UI pieces for TermQuarium."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from cozy_tui import Style
from cozy_tui.widgets import Box, Button, Label

from .save import format_relative_time

MAX_CARDS_SHOWN = 4  # keeps the menu on one screen; no scrolling yet


def build_save_menu(
    app,
    cards: list[tuple[Path, dict]],
    on_load: Callable[[Path], None],
    on_rename: Callable[[Path, str, str], None],
    on_duplicate: Callable[[Path, str], None],
    on_delete: Callable[[Path, str], None],
) -> Box:
    """Render the save list from metadata, not simulation widgets -- cheap
    to draw since it never touches a save's full fish/decoration data. Each
    card shows exactly what the user asked for: enough at a glance to know
    which aquarium to load without opening any of them. Rename/Duplicate
    each open their own app.prompt() for a new name (same pattern as the
    Fish Inspector's Rename); Delete opens an app.confirm() first, same
    pattern as Sell -- all three call back into the caller (main()'s
    _open_load_menu()) only once confirmed/submitted, which does the actual
    save.py mutation and refreshes this menu."""
    muted = Style(fg="bright_black")
    box = Box(0, 0, "520x440", title="Load Aquarium", border="rounded", style=app.style)
    if not cards:
        box.add(Label(2, 2, "No saves yet. Press P to create one.", muted))
    y = 2
    for path, meta in cards[:MAX_CARDS_SHOWN]:
        name = str(meta.get("name", path.stem))
        box.add(Label(2, y, name, Style(styles=["bold"])))
        y += 1

        def _rename_prompt(_widget, path=path, name=name):
            app.prompt(
                f"Rename '{name}' to",
                initial=name,
                on_submit=lambda new_name: on_rename(path, name, new_name),
            )

        def _duplicate_prompt(_widget, path=path, name=name):
            app.prompt(
                f"Duplicate '{name}' as",
                initial=f"{name} copy",
                on_submit=lambda new_name: on_duplicate(path, new_name),
            )

        def _delete_confirm(_widget, path=path, name=name):
            app.confirm(
                f"Delete '{name}'? This can't be undone.",
                on_yes=lambda: on_delete(path, name),
            )

        box.add(Button(2, y, "Load").on_click(lambda _widget, path=path: on_load(path)))
        box.add(Button(11, y, "Rename").on_click(_rename_prompt))
        box.add(Button(22, y, "Duplicate").on_click(_duplicate_prompt))
        box.add(Button(36, y, "Delete").on_click(_delete_confirm))
        y += 1
        box.add(Label(2, y, "─" * 30, muted))
        y += 1
        box.add(Label(2, y, f"🐠 {meta.get('fish', 0)} Fish"))
        y += 1
        box.add(Label(2, y, f"💰 ${meta.get('money', 0)}"))
        y += 1
        box.add(Label(2, y, f"🍽️ {meta.get('food', 0)} Food"))
        y += 1
        box.add(Label(2, y, f"📅 Day {meta.get('day', 0)}"))
        y += 1
        played = format_relative_time(meta.get("last_played", ""))
        box.add(Label(2, y, f"🕒 Played {played}", muted))
        y += 2
    box.add(Button(2, y, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def build_restore_menu(
    app, cloud_saves: list[dict], on_download: Callable[[str], None]
) -> Box:
    """Cloud Saves' "Restore My Saves" list -- deliberately simpler than
    build_save_menu()'s cards (no rename/duplicate/delete: those already
    exist for local saves once a cloud save is downloaded and shows up in
    the normal Load menu). Each entry is `{"name": ..., "metadata": ...}`
    from cloud.list_cloud_saves(), the same metadata shape write_save()
    already produces locally."""
    muted = Style(fg="bright_black")
    box = Box(0, 0, "460x360", title="Restore My Saves", border="rounded", style=app.style)
    if not cloud_saves:
        box.add(Label(2, 2, "No cloud saves found for this key.", muted))
    y = 2
    for entry in cloud_saves[:MAX_CARDS_SHOWN]:
        name = entry.get("name", "Untitled Aquarium")
        meta = entry.get("metadata", {})
        box.add(Label(2, y, name, Style(styles=["bold"])))
        y += 1
        box.add(
            Button(2, y, "Download").on_click(
                lambda _w, name=name: on_download(name)
            )
        )
        y += 1
        played = format_relative_time(meta.get("last_played", ""))
        box.add(
            Label(2, y, f"🐠 {meta.get('fish', 0)} Fish · Day {meta.get('day', 0)} · {played}", muted)
        )
        y += 2
    box.add(Button(2, y, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def build_help_menu(app) -> Box:
    """A compact in-game controls reference, reachable from the start menu."""
    muted = Style(fg="bright_black")
    box = Box(0, 0, "500x270", title="How to Play", border="rounded", style=app.style)
    lines = [
        "Click open water to drop food for your fish.",
        "Click a fish or decoration to inspect it.",
        "S  Shop       G  Settings       P  Save       L  Load",
        "Fish grow, make friends or rivals, and may have babies.",
        "Keep food stocked: starving fish lose health over time.",
        "Daily visitors and maintenance grants keep the aquarium going.",
    ]
    for row, line in enumerate(lines, start=2):
        box.add(Label(2, row, line, muted if row not in (2, 4) else None))
    box.add(Button(2, 10, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def build_start_menu(
    app,
    on_new: Callable[[], None],
    on_load: Callable[[], None],
    on_settings: Callable[[], None],
    on_help: Callable[[], None],
) -> Box:
    """The first screen shown for every session."""
    box = Box(0, 0, "360x260", title="TermQuarium", border="rounded", style=app.style)
    box.add(
        Label(
            2,
            2,
            "A cozy aquarium, one fish at a time.",
            Style(fg="bright_cyan", styles=["bold"]),
        )
    )
    box.add(Button(2, 5, "New Aquarium").on_click(lambda _w: on_new()))
    box.add(Button(2, 7, "Load Save").on_click(lambda _w: on_load()))
    box.add(Button(2, 9, "Settings").on_click(lambda _w: on_settings()))
    box.add(Button(2, 11, "Help").on_click(lambda _w: on_help()))
    box.add(Button(2, 14, "Quit").on_click(lambda _w: app.quit()))
    return box


def build_pause_menu(
    app,
    on_resume: Callable[[], None],
    on_save: Callable[[], None],
    on_settings: Callable[[], None],
    on_help: Callable[[], None],
    on_quit: Callable[[], None],
) -> Box:
    """Esc opens this (see main()) instead of instantly quitting -- the
    game genuinely freezes while it's open (every Fish/BubbleField checks
    the same shared `paused` flag this menu flips), and Quit here asks for
    confirmation first instead of a single accidental keypress destroying
    an unsaved session."""
    box = Box(0, 0, "320x260", title="Paused", border="rounded", style=app.style)
    box.add(
        Label(
            2,
            2,
            "Game paused -- nothing is moving.",
            Style(fg="bright_cyan", styles=["bold"]),
        )
    )
    box.add(Button(2, 5, "Resume").on_click(lambda _w: on_resume()))
    box.add(Button(2, 7, "Save").on_click(lambda _w: on_save()))
    box.add(Button(2, 9, "Settings").on_click(lambda _w: on_settings()))
    box.add(Button(2, 11, "Help").on_click(lambda _w: on_help()))
    box.add(Button(2, 14, "Quit").on_click(lambda _w: on_quit()))
    return box
