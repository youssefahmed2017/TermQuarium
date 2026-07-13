"""The Fish widget: steering, hunger/growth, personality, relationships, and
sleep, all in its own draw() -- plus the small helpers built around it."""

import math
import random
import time

from cozy_tui import Style
from cozy_tui._width import text_width
from cozy_tui.widget import Widget

from .constants import (
    AVOID_MARGIN,
    AVOID_STEER_RATE,
    EXPLORER_HOME_SHUFFLE_CHANCE,
    FLEE_STEER_RATE,
    FOLLOW_MOUSE_RATE,
    FOOD_STEER_RATE,
    FRIEND_STEER_RATE,
    GREEDY_RATE_MULT,
    GREEDY_SPEED_MULT,
    GROWTH_STAGES,
    HEART_RADIUS,
    HOME_ARRIVE_MARGIN,
    HOME_STEER_RATE,
    IDLE_DAMPING,
    LAZY_HOME_RADIUS,
    LAZY_SPEED_MULT,
    BABY_LEFT,
    BABY_RIGHT,
    COLD_SPEED_MULT,
    COLD_TEMP_THRESHOLD,
    EXPLORER_TURN_DIV,
    LAZY_TURN_MULT,
    MAX_SPEED,
    MIN_SPEED,
    MIN_TURN_DELAY,
    MAX_TURN_DELAY,
    PLAYFUL_SPEED_VARIANCE,
    PLAYFUL_TURN_DIV,
    RELAX_ARRIVE_MARGIN,
    RELAX_CHANCE,
    RELAX_CHECK_MAX,
    RELAX_CHECK_MIN,
    RELAX_DURATION_MAX,
    RELAX_DURATION_MIN,
    RELAX_STEER_RATE,
    RIVAL_FLEE_RADIUS,
    RIVAL_FOOD_BOOST,
    SCHOOL_ALIGNMENT_WEIGHT,
    SCHOOL_COHESION_WEIGHT,
    SCHOOL_RADIUS,
    SCHOOL_SEPARATION_DISTANCE,
    SCHOOL_SEPARATION_WEIGHT,
    SCHOOL_STEER_RATE,
    SHY_FLEE_RADIUS,
    SLEEP_CLOSE_DISTANCE,
    SLEEP_FAR_DISTANCE,
    SLEEP_HUNGER_THRESHOLD,
    SLEEP_STEER_RATE,
    SOCIAL_STEER_RATE,
    AGE_SECONDS_PER_DAY,
    Species,
)
from .economy import feed
from .relationships import (
    best_bond,
    random_personality,
    relationship_state,
    roll_is_sleepy,
    worst_bond,
)
from .steering import (
    avoid_decorations,
    nearest_index,
    random_velocity,
    school_velocity,
    steer,
    steer_away_from,
    steer_toward_food,
)
from .styles import HEART_STYLE, MUTED


class Fish(Widget):
    def __init__(
        self,
        x: float,
        y: float,
        bounds,
        foods,
        fish_list,
        on_eat_food,
        on_eat_fish,
        right_glyph,
        left_glyph,
        color,
        is_predator: bool = False,
        decorations=None,
        species_name: str = "Fish",
        mouse_pos=None,
        price: int = 0,
        environment=None,
        paused=None,
    ):
        super().__init__(round(x), round(y), Style(fg=color), name="Fish")
        self.fx, self.fy = float(x), float(y)
        self.bounds = bounds
        self.foods = foods
        self.fish_list = fish_list
        self.on_eat_food = on_eat_food
        self.on_eat_fish = on_eat_fish
        self.right_glyph = right_glyph
        self.left_glyph = left_glyph
        self.is_predator = is_predator
        self.decorations = decorations if decorations is not None else []
        # Shared {"phase": "Day"/"Morning"/"Night", "temperature": float}
        # dict, updated once a second by main()'s _per_second_tick -- the
        # same shared-mutable-dict pattern mouse_pos already uses.
        self.environment = environment
        # Shared {"value": bool} dict, or None -- main()'s Pause menu. Checked
        # first thing in draw(): everything (movement, hunger-independent
        # timers, sleep/home logic) freezes solid while paused, see draw().
        self.paused = paused
        self.species_name = species_name
        self.display_name = species_name  # renameable -- see _rename_fish() in main()
        self.price = price  # this species' Shop price -- sell_value scales off it by growth stage
        self.mouse_pos = mouse_pos  # shared {"x":.., "y":..} dict, or None
        self.personality = random_personality()
        # Independent of (and stackable with) personality -- see
        # roll_is_sleepy()'s docstring. A Greedy fish can also be Sleepy.
        self.is_sleepy = roll_is_sleepy()
        # Chosen once at birth, like a real pet's favorite spot -- never
        # re-rolled later, unlike everything else personality-related.
        self.favorite_decoration = (
            random.choice(self.decorations) if self.decorations else None
        )
        # Every pairwise relationship this fish currently has, keyed by the
        # other Fish -- starts empty (a new fish, starter/bought/born alike,
        # has no relationships yet; they're earned through interactions,
        # see relationships.py). `friend`/`rival` below are read-only views
        # derived from whichever relationship is currently strongest/
        # weakest, not fixed pointers set once at birth.
        self.relationships: dict["Fish", object] = {}
        # Which container Decoration (capacity > 0) this fish has claimed
        # for tonight, if any -- re-rolled fresh every time it falls asleep
        # (see _claim_home()), not a permanent "home" like favorite_decoration
        # is a permanent favorite. `_entered` is True once it's actually
        # arrived inside (not just still swimming toward it) -- see draw().
        self.sleeping_in = None
        self._entered = False
        self.speed = random.uniform(MIN_SPEED, MAX_SPEED)
        self.vx, self.vy = random_velocity(self._effective_speed())
        self.hunger = 0.0  # 0 = full, 100 = starving
        self.health = 100.0
        self.birth_time = time.monotonic()
        self._last = time.monotonic()
        self._next_turn = self._last + random.uniform(MIN_TURN_DELAY, MAX_TURN_DELAY)
        self._relaxing_until = 0.0
        self._next_relax_check = self._last + random.uniform(
            RELAX_CHECK_MIN, RELAX_CHECK_MAX
        )

    @property
    def age_days(self) -> float:
        return (time.monotonic() - self.birth_time) / AGE_SECONDS_PER_DAY

    @property
    def friend(self):
        """The other fish this one gets along with best, if that's at
        least Friend-level (relationships.RELATIONSHIP_FRIEND_THRESHOLD),
        else None. Read-only and live -- derived from the current
        relationship scores (see relationships.best_bond()), not a fixed
        pointer set once at birth."""
        return best_bond(self)

    @property
    def rival(self):
        """The other fish this one gets along with least, if that's
        Rival-level (relationships.RELATIONSHIP_RIVAL_THRESHOLD), else
        None -- the same read-only, score-derived shape as `friend`."""
        return worst_bond(self)

    def _growth_stage_index(self) -> int:
        idx = 0
        for i, (_name, min_age, _mult) in enumerate(GROWTH_STAGES):
            if self.age_days >= min_age:
                idx = i
        return idx

    @property
    def growth_stage(self) -> str:
        return GROWTH_STAGES[self._growth_stage_index()][0]

    @property
    def sell_value(self) -> int:
        return round(self.price * GROWTH_STAGES[self._growth_stage_index()][2])

    def _effective_speed(self) -> float:
        # Checked fresh every use (like every other personality effect),
        # rather than baked permanently into self.speed at construction --
        # otherwise a Lazy fish would move like a normal one everywhere
        # this file (or a test) sets .personality after construction, since
        # nothing else here treats personality as fixed-at-birth.
        # Night no longer lives here -- a sleeping fish is a hard stop
        # (see draw()), not just slower, so there's nothing left to blend.
        mult = LAZY_SPEED_MULT if self.personality == "Lazy" else 1.0
        if self.environment is not None:
            temperature = self.environment.get("temperature")
            if temperature is not None and temperature < COLD_TEMP_THRESHOLD:
                mult *= COLD_SPEED_MULT  # cold-blooded and sluggish
        return self.speed * mult

    def _nearest_food(self):
        i = nearest_index(self.fx, self.fy, [(f.fx, f.fy) for f in self.foods])
        return self.foods[i] if i is not None else None

    def _nearest_prey(self):
        # Sharks hunt ordinary fish, never each other.
        prey = [f for f in self.fish_list if f is not self and not f.is_predator]
        i = nearest_index(self.fx, self.fy, [(f.fx, f.fy) for f in prey])
        return prey[i] if i is not None else None

    def _group_centroid(self):
        """Average (x, y) of every other fish sharing this tank, or None if
        there are none -- Friendly's fallback when there's no mouse to
        follow. None (not e.g. (0, 0)) matters: it's what lets a solitary
        Friendly fish correctly fall through to relaxing/wandering instead
        of silently doing nothing while still "claiming" this frame's
        personality-steering priority slot."""
        others = [(o.fx, o.fy) for o in self.fish_list if o is not self]
        if not others:
            return None
        return sum(p[0] for p in others) / len(others), sum(p[1] for p in others) / len(
            others
        )

    def _schoolmates(self):
        """(x, y, vx, vy) for same-species, non-predator fish within
        SCHOOL_RADIUS -- schooling is a species trait (real fish shoal with
        their own kind), not a personality one like Friendly's group pull,
        and predators (Sharks) hunt alone rather than schooling."""
        if self.is_predator:
            return []
        return [
            (o.fx, o.fy, o.vx, o.vy)
            for o in self.fish_list
            if o is not self
            and not o.is_predator
            and o.species_name == self.species_name
            and math.hypot(o.fx - self.fx, o.fy - self.fy) <= SCHOOL_RADIUS
        ]

    def _home_occupancy(self, decoration) -> int:
        return sum(
            1 for f in self.fish_list if f is not self and f.sleeping_in is decoration
        )

    def _claim_home(self):
        """Pick a container Decoration to sleep inside tonight, or None for
        the tank floor. Baseline priority: the favorite spot, if it happens
        to be a container with room -> a friend's already-claimed container,
        if it has room (so best friends end up sleeping in the same home,
        not just near each other) -> the nearest container with any room ->
        None. Only called while asleep and not yet housed (see draw()), so a
        fish that finds nothing simply retries next frame -- cheap, and
        means a spot freed up mid-night (a tankmate waking early) can still
        be claimed later.

        Personality reorders this baseline rather than replacing it:
          - Lazy won't travel for a container, but won't turn one down
            either -- only takes one already within LAZY_HOME_RADIUS,
            otherwise the floor. Matches its low-effort theme everywhere
            else (LAZY_SPEED_MULT, turn cadence) without making it *refuse*
            a home that happens to already be right there.
          - Shy weights *any* nearby shelter over specifically bunking with
            a friend -- Shy already hides behind decorations from the mouse
            while awake, so safety beats company at night too.
          - Friendly weights sleeping with a friend over even its own
            favorite spot -- being with friends is already Friendly's
            defining trait (mouse-follow, group drift) while awake.
          - Explorer occasionally shuffles to a different container than
            its usual (nearest) pick, echoing its constant-patrol restlessness.
        """
        favorite = self.favorite_decoration
        favorite_ok = (
            favorite is not None
            and favorite.is_container
            and self._home_occupancy(favorite) < favorite.capacity
        )
        friend_home = self.friend.sleeping_in if self.friend is not None else None
        friend_ok = (
            friend_home is not None
            and self._home_occupancy(friend_home) < friend_home.capacity
        )
        containers = sorted(
            (d for d in self.decorations if d.is_container),
            key=lambda d: math.hypot(d.fx - self.fx, d.fy - self.fy),
        )
        nearest = next(
            (d for d in containers if self._home_occupancy(d) < d.capacity), None
        )

        if self.personality == "Lazy":
            if (
                nearest is not None
                and math.hypot(nearest.fx - self.fx, nearest.fy - self.fy)
                <= LAZY_HOME_RADIUS
            ):
                return nearest
            return None
        if self.personality == "Friendly" and friend_ok:
            return friend_home
        if favorite_ok:
            return favorite
        if self.personality == "Shy" and nearest is not None:
            return nearest
        if friend_ok:
            return friend_home
        if (
            self.personality == "Explorer"
            and random.random() < EXPLORER_HOME_SHUFFLE_CHANCE
        ):
            available = [d for d in containers if self._home_occupancy(d) < d.capacity]
            if available:
                return random.choice(available)
        return nearest

    def _glyph(self) -> str:
        # A Baby hasn't grown into its species' real shape yet -- growing up
        # is something you can actually see, not just an Inspector number.
        if self.growth_stage == "Baby":
            return BABY_RIGHT if self.vx >= 0 else BABY_LEFT
        return self.right_glyph if self.vx >= 0 else self.left_glyph

    def natural_width(self, scale) -> int:
        return text_width(self._glyph())

    def natural_height(self, scale) -> int:
        return 1

    def _mouse_point(self):
        if self.mouse_pos and self.mouse_pos.get("x") is not None:
            return (self.mouse_pos["x"], self.mouse_pos["y"])
        return None

    def draw(self, canvas) -> None:
        now = time.monotonic()
        dt = now - self._last
        self._last = now  # updated every frame, paused or not (see below)

        if self.paused is not None and self.paused.get("value"):
            # Frozen solid -- no movement, no hunger-independent timers, no
            # steering of any kind. _last still just got updated above, so
            # there's no dt jump the instant the game resumes. A housed fish
            # stays invisible even while paused, same as normal.
            if not self._entered:
                canvas.write(self.abs_x, self.abs_y, self._glyph(), self.style)
            return

        speed = self._effective_speed()
        mouse_pos = self._mouse_point()
        # Fully asleep -- not just slower. A sleeping fish doesn't wander,
        # chase food, flee, or relax; it just settles into position (see
        # below) and stops, same as the turn/relax timers not advancing
        # while asleep (so it picks a fresh direction/relax roll the moment
        # it wakes, rather than acting on a stale decision from before it
        # fell asleep). A fish hungry enough to actually be in danger stays
        # up instead -- sleeping through your own starvation isn't cozy,
        # it's just a bug wearing a nightcap.
        sleeping = (
            self.environment is not None
            and self.environment.get("phase") == "Night"
            and self.hunger <= SLEEP_HUNGER_THRESHOLD
        )

        if sleeping:
            if self.sleeping_in is None:
                self.sleeping_in = self._claim_home()
            if self.sleeping_in is not None:
                home = self.sleeping_in
                arrive_radius = home.radius + AVOID_MARGIN + HOME_ARRIVE_MARGIN
                if math.hypot(self.fx - home.fx, self.fy - home.fy) > arrive_radius:
                    blend = min(1.0, HOME_STEER_RATE * dt)
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx,
                        self.vy,
                        self.fx,
                        self.fy,
                        (home.fx, home.fy),
                        speed,
                        blend,
                    )
                else:
                    # Arrived -- tucked inside, invisible from the tank view
                    # until the player clicks the decoration (see draw()'s
                    # early return below and _build_decoration_inspector()).
                    self.vx *= IDLE_DAMPING
                    self.vy *= IDLE_DAMPING
                    self._entered = True
            else:
                # No container claimed tonight -- the original floor
                # behavior: friends sleep close together, rivals sleep as
                # far apart as the tank allows, otherwise just settle
                # wherever night caught it.
                settle_blend = min(1.0, SLEEP_STEER_RATE * dt)
                if self.friend is not None:
                    close_enough = (
                        math.hypot(self.fx - self.friend.fx, self.fy - self.friend.fy)
                        <= SLEEP_CLOSE_DISTANCE
                    )
                    if close_enough:
                        self.vx *= IDLE_DAMPING
                        self.vy *= IDLE_DAMPING
                    else:
                        self.vx, self.vy, _ = steer_toward_food(
                            self.vx,
                            self.vy,
                            self.fx,
                            self.fy,
                            (self.friend.fx, self.friend.fy),
                            speed,
                            settle_blend,
                        )
                elif self.rival is not None:
                    far_enough = (
                        math.hypot(self.fx - self.rival.fx, self.fy - self.rival.fy)
                        >= SLEEP_FAR_DISTANCE
                    )
                    if far_enough:
                        self.vx *= IDLE_DAMPING
                        self.vy *= IDLE_DAMPING
                    else:
                        self.vx, self.vy = steer_away_from(
                            self.vx,
                            self.vy,
                            self.fx,
                            self.fy,
                            (self.rival.fx, self.rival.fy),
                            speed,
                            settle_blend,
                        )
                else:
                    self.vx *= IDLE_DAMPING
                    self.vy *= IDLE_DAMPING
        else:
            if self.sleeping_in is not None:
                # Waking up -- reappear right at the home's doorstep and
                # resume normal movement/visibility from there.
                self.fx, self.fy = self.sleeping_in.fx, self.sleeping_in.fy
                self.sleeping_in = None
                self._entered = False
            if now >= self._next_turn:
                lo, hi = MIN_TURN_DELAY, MAX_TURN_DELAY
                turn_speed = speed
                if self.personality == "Explorer":
                    lo, hi = lo / EXPLORER_TURN_DIV, hi / EXPLORER_TURN_DIV
                elif self.personality == "Lazy":
                    lo, hi = lo * LAZY_TURN_MULT, hi * LAZY_TURN_MULT
                elif self.personality == "Playful":
                    lo, hi = lo / PLAYFUL_TURN_DIV, hi / PLAYFUL_TURN_DIV
                    turn_speed = speed * random.uniform(*PLAYFUL_SPEED_VARIANCE)
                self.vx, self.vy = random_velocity(turn_speed)
                self._next_turn = now + random.uniform(lo, hi)

            if self.favorite_decoration is not None and now >= self._next_relax_check:
                self._next_relax_check = now + random.uniform(
                    RELAX_CHECK_MIN, RELAX_CHECK_MAX
                )
                if random.random() < RELAX_CHANCE:
                    self._relaxing_until = now + random.uniform(
                        RELAX_DURATION_MIN, RELAX_DURATION_MAX
                    )
            relaxing = (
                self.favorite_decoration is not None and now < self._relaxing_until
            )

            mouse_scare = (
                self.personality == "Shy"
                and mouse_pos is not None
                and math.hypot(self.fx - mouse_pos[0], self.fy - mouse_pos[1])
                < SHY_FLEE_RADIUS
            )
            rival_pos = (
                (self.rival.fx, self.rival.fy) if self.rival is not None else None
            )
            rival_scare = (
                rival_pos is not None
                and math.hypot(self.fx - rival_pos[0], self.fy - rival_pos[1])
                < RIVAL_FLEE_RADIUS
            )
            fleeing = mouse_scare or rival_scare
            # A Rival scares regardless of personality (Goldie swims away from
            # Kevin whether or not she's Shy) -- Shy's mouse-fear takes priority
            # if somehow both are true at once, since it's already the more
            # dramatic threat this fish is built to react to.
            threat_pos = mouse_pos if mouse_scare else rival_pos

            # Per-frame priority: fleeing (fear) beats eating (hunger) beats
            # personality-driven steering (affection/socializing toward the
            # cursor or the group) beats friend-following beats relaxing at the
            # favorite spot beats plain wandering -- exactly one of these blends
            # velocity per frame.
            seeking_food = False
            if fleeing:
                # Only Shy's mouse-fear hides behind a decoration. A Rival
                # never does: two mutual rivals both fleeing toward "my
                # nearest decoration" can converge on the *same* spot if
                # it's nearest to both of them, which looks like they're
                # frozen huddling together right where the user doesn't
                # want them -- the opposite of "put distance between us".
                # Fleeing a Rival always steers straight away instead, with
                # no distance cap, so they keep separating.
                hide_pos = None
                if mouse_scare and self.decorations:
                    i = nearest_index(
                        self.fx, self.fy, [(d.fx, d.fy) for d in self.decorations]
                    )
                    if i is not None:
                        hide_pos = (self.decorations[i].fx, self.decorations[i].fy)
                blend = min(1.0, FLEE_STEER_RATE * dt)
                if hide_pos is not None:
                    # Aimed at a Decoration, not food -- the "ate" flag this
                    # returns is meaningless here and deliberately discarded;
                    # avoid_decorations() below still keeps it from actually
                    # overlapping the decoration it's hiding behind.
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx, self.vy, self.fx, self.fy, hide_pos, speed, blend
                    )
                else:
                    self.vx, self.vy = steer_away_from(
                        self.vx, self.vy, self.fx, self.fy, threat_pos, speed, blend
                    )
            else:
                target = (
                    self._nearest_prey() if self.is_predator else self._nearest_food()
                )
                target_pos = (target.fx, target.fy) if target is not None else None
                if target_pos is not None:
                    # Actively pursuing food/prey overrides the unconditional
                    # avoid_decorations() call below entirely (see seeking_food),
                    # not just the priority chain above -- otherwise food sitting
                    # inside a decoration's avoidance radius (but outside
                    # EAT_RADIUS) could never actually be reached: every frame
                    # avoid_decorations() would shove the fish back out before it
                    # arrived, a real "stuck near the furniture, starving" bug.
                    seeking_food = True
                    greedy = self.personality == "Greedy"
                    has_rival = self.rival is not None
                    food_speed = speed * (
                        (GREEDY_SPEED_MULT if greedy else 1.0)
                        * (RIVAL_FOOD_BOOST if has_rival else 1.0)
                    )
                    rate = FOOD_STEER_RATE * (
                        (GREEDY_RATE_MULT if greedy else 1.0)
                        * (RIVAL_FOOD_BOOST if has_rival else 1.0)
                    )
                    blend = min(1.0, rate * dt)
                    self.vx, self.vy, caught = steer_toward_food(
                        self.vx,
                        self.vy,
                        self.fx,
                        self.fy,
                        target_pos,
                        food_speed,
                        blend,
                    )
                    if caught:
                        if self.is_predator:
                            self.fish_list.remove(target)
                            self.on_eat_fish(target)
                        else:
                            self.foods.remove(target)
                            self.on_eat_food(target)
                        self.hunger, self.health = feed(self.hunger, self.health)
                elif self.personality == "Friendly" and mouse_pos is not None:
                    blend = min(1.0, FOLLOW_MOUSE_RATE * dt)
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx, self.vy, self.fx, self.fy, mouse_pos, speed, blend
                    )
                elif (
                    self.personality == "Friendly"
                    and self._group_centroid() is not None
                ):
                    # No mouse to follow -- drift gently toward the group instead.
                    cx, cy = self._group_centroid()
                    blend = min(1.0, SOCIAL_STEER_RATE * dt)
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx, self.vy, self.fx, self.fy, (cx, cy), speed, blend
                    )
                elif self.friend is not None:
                    # "They often swim together" -- unlike Friendly's group pull,
                    # this is a specific bond, not personality-gated, and applies
                    # to any fish with a Friend once nothing more urgent (food,
                    # fleeing, its own personality-steering) claims this frame.
                    blend = min(1.0, FRIEND_STEER_RATE * dt)
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx,
                        self.vy,
                        self.fx,
                        self.fy,
                        (self.friend.fx, self.friend.fy),
                        speed,
                        blend,
                    )
                elif relaxing:
                    spot = self.favorite_decoration
                    arrive_radius = spot.radius + AVOID_MARGIN + RELAX_ARRIVE_MARGIN
                    if math.hypot(self.fx - spot.fx, self.fy - spot.fy) > arrive_radius:
                        blend = min(1.0, RELAX_STEER_RATE * dt)
                        self.vx, self.vy, _ = steer_toward_food(
                            self.vx,
                            self.vy,
                            self.fx,
                            self.fy,
                            (spot.fx, spot.fy),
                            speed,
                            blend,
                        )
                    else:
                        # Arrived -- settle down instead of continuing to steer,
                        # so it visibly relaxes rather than endlessly orbiting the
                        # spot. avoid_decorations() below still keeps it from
                        # actually overlapping the decoration it's next to.
                        self.vx *= IDLE_DAMPING
                        self.vy *= IDLE_DAMPING
                else:
                    # Schooling: the bottom of the priority chain, just above
                    # plain wandering -- a species-level ambient behavior
                    # (unlike Friendly's personality-gated group pull above),
                    # so it applies to whichever fish reach here with nothing
                    # more urgent going on. No schoolmates in range simply
                    # leaves this frame's turn-timer velocity untouched.
                    schoolmates = self._schoolmates()
                    if schoolmates:
                        blend = min(1.0, SCHOOL_STEER_RATE * dt)
                        self.vx, self.vy = school_velocity(
                            self.fx,
                            self.fy,
                            self.vx,
                            self.vy,
                            schoolmates,
                            speed,
                            blend,
                            SCHOOL_COHESION_WEIGHT,
                            SCHOOL_ALIGNMENT_WEIGHT,
                            SCHOOL_SEPARATION_WEIGHT,
                            SCHOOL_SEPARATION_DISTANCE,
                        )

            if self.decorations and not seeking_food:
                avoid_blend = min(1.0, AVOID_STEER_RATE * dt)
                self.vx, self.vy = avoid_decorations(
                    self.vx,
                    self.vy,
                    self.fx,
                    self.fy,
                    [(d.fx, d.fy, d.radius) for d in self.decorations],
                    speed,
                    avoid_blend,
                )

        if self._entered:
            # Tucked inside a container -- frozen in place and invisible
            # from the tank view, same as the player physically not being
            # able to see through the Castle's walls. See
            # _build_decoration_inspector() for how to peek inside.
            return

        self.fx, self.fy, self.vx, self.vy = steer(
            self.fx, self.fy, self.vx, self.vy, self.bounds, dt
        )
        self.x, self.y = round(self.fx), round(self.fy)
        canvas.write(self.abs_x, self.abs_y, self._glyph(), self.style)

        if sleeping:
            # Sleep takes visual priority over a Friendly heart -- a fish
            # fast asleep isn't also mooning over the cursor.
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "😴", MUTED)
        elif self.personality == "Friendly" and mouse_pos is not None:
            close = (
                math.hypot(self.fx - mouse_pos[0], self.fy - mouse_pos[1])
                < HEART_RADIUS
            )
            if close:
                canvas.write(self.abs_x, max(0, self.abs_y - 1), "💕", HEART_STYLE)


def _make_fish(
    bounds,
    foods,
    fish_list,
    on_eat_food,
    on_eat_fish,
    species: Species,
    decorations=None,
    mouse_pos=None,
    environment=None,
    paused=None,
) -> Fish:
    x0, y0, x1, y1 = bounds
    x = random.uniform(x0, x1)
    y = random.uniform(y0, y1)
    return Fish(
        x,
        y,
        bounds,
        foods,
        fish_list,
        on_eat_food,
        on_eat_fish,
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


def fish_at(fish_list, col: int, row: int):
    """The Fish in `fish_list` currently occupying (col, row), or None --
    used to tell "clicked a fish" (rename it) apart from "clicked open
    water" (feed) in the same left-click."""
    for f in fish_list:
        w = f.natural_width(1)
        if f.y == row and f.x <= col < f.x + w:
            return f
    return None


def occupants_of(decoration, fish_list) -> list:
    """Every Fish currently sleeping inside `decoration` tonight, in no
    particular order -- what the Decoration Inspector peeks in to show
    (see _build_decoration_inspector())."""
    return [f for f in fish_list if f.sleeping_in is decoration]


def describe_fish(f: Fish) -> str:
    """One-line tooltip text: name, species, growth stage, personality,
    hunger, and (if any) a short relationship hint -- the full detail
    (state + recent reasons) lives in the Inspector, this is just enough to
    notice a bond exists. Never shows the raw score (Step 8), only the
    state's own emoji (relationship_state())."""
    relationship = ""
    if f.friend is not None:
        _label, emoji = relationship_state(f.relationships[f.friend].score)
        relationship = f" - {emoji} {f.friend.display_name}"
    elif f.rival is not None:
        _label, emoji = relationship_state(f.relationships[f.rival].score)
        relationship = f" - {emoji} {f.rival.display_name}"
    return (
        f"{f.display_name} ({f.species_name}, {f.growth_stage}) - "
        f"{f.personality} - Hunger {f.hunger:.0f}%{relationship}"
    )
