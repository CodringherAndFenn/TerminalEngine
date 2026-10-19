"""
entities/character.py -- a walking body with a weapon: the hero, and the
enemies that shoot (goblin archer, warlock, ogre, spell tower).

Movement is free in 8 directions: the input (or the AI) gives a direction,
and the velocity eases toward direction * max_speed at `accel` (or down to
zero at `brake` when there's no input). Collision is a square box of
`size_px` against the tile grid, resolved one axis at a time so walking
diagonally into a wall slides along it (systems/collision.py).

Aiming is separate from walking: `aim_angle` is where the weapon points
(the hero: straight at the mouse; enemies turn it at `aim_turn_speed`).
Characters face left or right toward their aim -- that's how the sprite is
drawn.

Heroes can dodge-roll (M18, systems/roll.py): while `roll_t` runs the body
slides along `roll_dir` at the roll's speed instead of walking, and it
can't be hit at all (not hittable, so shots, blasts and bodies pass
through).

Angles are in radians in WORLD space, measured with atan2(dy, dx) where +y
points DOWN the screen. So 0 = east, +pi/2 = south, -pi/2 = north.
"""

from __future__ import annotations

import math
import random

from .. import config
from ..specs import CharacterSpec
from ..systems.collision import TileSource, WaterWalk, move_hull
from .actor import Actor
from .weapon import Weapon

# A hit counts as "on the front" when it comes from within this angle of
# where the character faces (its aim) -- used for front_armor (the ogre).
FRONT_ARC = math.radians(55)

TAU = 2 * math.pi


def wrap_angle(a: float) -> float:
    """Wrap an angle to (-pi, pi]."""
    a = math.fmod(a + math.pi, TAU)
    if a <= 0:
        a += TAU
    return a - math.pi


def rotate_toward(current: float, target: float, max_step: float) -> float:
    """Turn `current` toward `target` by at most `max_step`, the short way."""
    err = wrap_angle(target - current)
    if abs(err) <= max_step:
        return target
    return current + math.copysign(max_step, err)


def _approach(v: float, target: float, rate: float) -> float:
    if abs(target - v) <= rate:
        return target
    return v + math.copysign(rate, target - v)


class Character(Actor):
    faction = "player"

    def __init__(self, spec: CharacterSpec, x: float, y: float, max_hp: int | None = None) -> None:
        # Hit circle: a bit bigger than half the box, in tiles.
        super().__init__(max_hp if max_hp is not None else spec.max_hp,
                         spec.size_px / 2 / config.TILE_PX_W + 0.15)
        self.spec = spec
        self.x, self.y = x, y
        self.vx = self.vy = 0.0          # tiles/s (enemies lead their shots with this)
        self.aim_angle = 0.0
        self.aim_point: tuple[float, float] | None = None   # the world point aimed at
        self.heading = 0.0               # direction of the last movement
        self.walked = 0.0                # tiles walked in total (walk animation)
        self.last_blocked = False
        self.half = spec.size_px / 2     # collision half-size, px
        self.weapon = Weapon(config.WEAPONS[spec.weapon])
        # Heroes (M14): their card stats (players/stats.HeroStats; None for
        # enemies), the dice for crits / evasions / status rolls (the game
        # seeds it per player so runs replay), Hunter's Mark's target,
        # attacks made (Overload) and hits evaded (for the "evade" pop-up).
        self.stats = None
        self.rng = random.Random(0)
        self.marked = None
        self.attacks = 0
        self.evaded = 0
        # More hero card state (M16), kept up by the game scene: shield HP and
        # seconds since last hurt, a hit that wants Retaliation, Crescendo's
        # streak, Bloodlust's kill timers, the hero's level / run loot / run
        # clock, whether the last strike crit, bestiary kinds known.
        self.shield = 0.0
        self.since_hit = 0.0
        self.retaliate = False
        self.streak = 0
        self.bloodlust: list[float] = []
        self.level = 1
        self.run_loot = 0.0
        self.time = 0.0
        self.last_crit = False
        self.bestiary: set[str] = set()
        self.idle = 0.0                   # seconds since the last attack (Capacitor)
        # The dodge roll (systems/roll.py): seconds of roll left and its
        # direction (unit vector) and speed (tiles/s; 0 for Blink, which has
        # already arrived), charges ready and seconds toward the next one,
        # plus what roll cards keep: Riposte's and Slipstream's timers,
        # enemy shots already rolled through (Close Call) / shouldered aside
        # this roll, distance to the next trail patch, steps rolled.
        self.roll_t = 0.0
        self.roll_dir = (1.0, 0.0)
        self.roll_speed = 0.0
        self.roll_charges = config.ROLL_CHARGES
        self.roll_recharge = 0.0
        self.riposte = 0.0
        self.slipstream = 0.0
        self.roll_passed: set[int] = set()
        self.roll_trail = 0.0
        self.roll_steps = 0
        self.speed_mult = 1.0             # Slipstream
        # P8: slowed (a web, a wendigo's howl, a phantom's touch): x this
        # speed for this many s more (the strongest slow wins).
        self.slow_mult = 1.0
        self.slow_t = 0.0
        # M28.2a: hits taken (the Sunwheel's +6 counts them), and Unshaken
        # (the War Drum's +6, set by systems/run_rules while in a frenzy):
        # slows and roots don't hold.
        self.hits_taken = 0
        self.unshaken = False
        # M28.2b: Kindle's count (the enemy, hits in a row on it), and
        # Battery's charges and whether this attack shocks (Galvanic Mask).
        self.kindle: tuple = (None, 0)
        self.battery = 0
        self.shocking = False
        # M28.2c, the feet's tricks: sure crits left after a roll and whether
        # this attack is one (Fencer's Boots); s left untouchable and shots
        # rolled through this roll (Hairsbreadth); rolls so far (Ashwalkers'
        # patches know their roll); s walked without stopping, a charged
        # attack, and the distance of the next hoofbeat (Gallopers); the s
        # left on each Quickstep (Wingheel); blinks left in a storm and s to
        # use them (Phasewalkers); tiles the charge was carried (Ramhorn);
        # s of fast shooting left (Tumbler); enemies passed (Stompers); the
        # amps on the ground and the images left behind.
        self.riposte_left = 0
        self.riposte_now = False
        self.riposting = False
        self.spectral = False         # (Ghostwood Staff +6: a dart's hit, through fronts)
        # M28.2h: the attack held this step (Hoverhead +6); catches' attack
        # speed (Homesick +6); s still toward the next fast arrow and when
        # last steady (Stillwater +3, +9); marks besides the main one, each
        # (enemy, until) (Bloodhound +3, +9).
        self.trigger = False
        self.welcome: list[float] = []
        self.breath = 0.0
        self.calm = 0.0
        self.marks: list[tuple] = []
        # M28.2i: the duelist (Duelist's Wand +6); HP a beat couldn't heal,
        # for the next (Cradlesong +6); when a beat last hit something
        # (Showstopper +3), the last Curtain call and whether HP was below
        # its line (+6); during a beat, its hits don't wake (Cradlesong +3).
        self.duelist = None
        self.unspent = 0.0
        self.beat_hit = -math.inf
        self.curtain_t = -math.inf
        self.low = False
        self.lulling = False
        self.untouchable = 0.0
        self.roll_grazes = 0
        self.rolls = 0
        self.walk_t = 0.0
        self.charged = False
        self.hoof = config.HOOFBEATS[0]
        self.quick: list[float] = []
        self.storm_blinks = 0
        self.storm_t = 0.0
        self.rampage = 0.0
        self.aerial = 0.0
        self.surfed: set[int] = set()
        self.amps: list[list[float]] = []
        self.images: list = []
        # M28.2d, the chest's tricks: s standing still (Overgrowth, Anvil
        # stance); Tempered's armor (s left on each point); what this
        # step's hits leave for systems/run_rules (Grudge Mail: how many,
        # the biggest, where from; a shield that broke and its size; thorn
        # hits for Wild hedge); hits blocked (Prism skin); Clean getaway's
        # s; Last stand's s and its cooldown; Grudge Mail's built-up grudge;
        # whether you were above 90% HP; the clocks of the auras and the
        # second ward; next to a wall (Garrison).
        # M28.2e, the rings' tricks: Golden armor's armor; Slow fade's
        # clock; Deluge's crits (when each runs out); who your wolves rush
        # (The pack: the attacker, until when).
        self.hoard_armor = 0
        self.fade_t = 0.0
        self.deluge: list[float] = []
        self.rush: tuple | None = None
        # M28.2f, the trinkets' tricks: the enemy you hit last (Scent), the
        # enemy that hit you last (Thunderhead), where your last kill fell
        # (Ossuary).
        self.scent = None
        self.struck_by = None
        self.kill_spot: tuple[float, float] | None = None
        self.still_t = 0.0
        self.temper: list[float] = []
        self.retaliate_hits = 0
        self.retaliate_big = 0.0
        self.retaliate_from: tuple[float, float] | None = None
        self.shield_broke = 0.0
        self.hedge: list = []
        self.blocked = 0
        self.getaway = 0.0
        self.last_stand = 0.0
        self.stand_cd = 0.0
        self.grudge = 0.0
        self.above90 = True
        self.bramble_t = 0.0
        self.tremor_t = 0.0
        self.radiant_t = 0.0
        self.ward_full_t = 0.0
        self.near_wall = False
        self.petrified = 0.0              # P9: s left turned to stone (a basilisk's gaze)
        # P6 riding (systems/mount.py): the mount ridden ("" on foot), s left
        # until a called one arrives, s before it can be called again, the
        # speed it gives, and since_hit when last looked (a drop: a hit).
        self.mount = ""
        self.mount_call = 0.0
        self.mount_cd = 0.0
        self.mount_mult = 1.0
        self.mount_seen = 0.0
        self.mount_left = False           # the mount faces where it's going (left?)
        # M23.3: the Nameless Magus's time zones and quicksand (walking
        # only: a roll is never slowed). He sets it each step he's fighting.
        self.time_mult = 1.0
        # M24.1: the Fallout King's rads (0..RADS_FULL) and seconds left
        # irradiated (no regen, a slower roll recharge; he does the burn).
        self.rads = 0.0
        self.irradiated = 0.0
        # M24.2: the Snow King's black ice (how fast you speed up and stop,
        # x), his chill (0..CHILL_FULL), and seconds left encased in ice
        # (can't move or attack; rolls pressed meanwhile count toward
        # breaking out).
        self.traction = 1.0
        self.chill = 0.0
        self.encased = 0.0
        self.encase_breaks = 0
        # M25.1: seconds left shrunk by Nettle's dust (faster, half damage,
        # knocked about; a growcap grows you back sooner).
        self.shrunk = 0.0
        self.water_walk = False           # M27: Adventurer's Glory -- water is ground
        self.spiral = 0                   # Spiral: how far round its extra shot has turned

    @property
    def rolling(self) -> bool:
        return self.roll_t > 0

    @property
    def hittable(self) -> bool:
        """Mid-roll (and Untouchable after one), nothing can touch a hero."""
        return self.alive and self.roll_t <= 0 and self.untouchable <= 0

    @property
    def facing_left(self) -> bool:
        return math.cos(self.aim_angle) < 0

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    def petrify(self, seconds: float) -> None:
        """Turned to stone (P9, a basilisk): can't move or attack."""
        self.petrified = max(self.petrified, seconds)

    def slowed(self, mult: float, seconds: float) -> None:
        """Slow to x `mult` for `seconds` (P8). A weaker slow doesn't
        replace a stronger one still running."""
        if self.slow_t > 0 and self.slow_mult < mult:
            return                                    # a stronger slow is on
        if self.slow_t > 0 and self.slow_mult == mult:
            self.slow_t = max(self.slow_t, seconds)   # the same one again: the longer
        else:
            self.slow_mult, self.slow_t = mult, seconds

    # --- Damage ------------------------------------------------------------------------

    def take_damage(self, amount, source, from_angle):
        """Armor: a hit coming from the side the character faces (its aim)
        is scaled by the spec's front_armor. A hero's evasion may make
        the hit miss outright, and armor `a` scales it by 1 - a / (|a| + ARMOR_K)
        (40 armor halves it; negative armor makes hits hurt more)."""
        if from_angle is not None and self.spec.front_armor != 1.0 \
                and not getattr(source, "spectral", False):
            came_from = from_angle + math.pi     # a hit comes *from* opposite its travel
            if abs(wrap_angle(came_from - self.aim_angle)) < FRONT_ARC:
                amount *= self.spec.front_armor
        st = self.stats
        if self.roll_t > 0 or self.untouchable > 0:     # i-frames (Hairsbreadth +9 too)
            return 0.0
        if st is not None and source is not None and getattr(source, "disarmed", 0) > 0:
            source.disarmed = 0.0                       # (Fencer's Boots +3: it fizzles)
            return 0.0
        if st is None or not self.alive or self.invulnerable:
            return super().take_damage(amount, source, from_angle)
        howled = getattr(source, "howled", None)
        if howled is not None and howled[0].time < howled[1]:
            amount *= config.HOWL[2]                    # (Wolfcall Whistle +6: Howl)
        if source is not None and source is self.duelist and st.has("point_blank+6"):
            amount *= config.DUEL[1]                    # (Duelist's Wand +6: Duel)
        if st.has("glass_cannon+6") and self.since_hit >= config.PRISM_SKIN:
            self.since_hit = 0.0                        # (Shattercoat +6: Prism skin)
            self.blocked += 1
            return 0.0
        if st.evasion > 0 and self.rng.random() < st.evasion:
            self.evaded += 1
            return 0.0
        armor = st.armor + len(self.temper) + self.hoard_armor   # (Tempered, Golden armor)
        if armor:
            amount *= 1 - armor / (abs(armor) + config.ARMOR_K)
        if st.has("berserker+3") and self.hp < self.max_hp * config.THICK_FUR[0]:
            amount *= config.THICK_FUR[1]               # (Wolfpelt +3: Thick fur)
        if st.has("hit_cap"):                           # Heavy Plate
            stance = st.has("heavy_plate+9") and self.still_t >= config.ANVIL_STANCE[0]
            cap = self.max_hp * (config.ANVIL_STANCE[1] if stance else 0.10)
            if amount > cap:
                amount = cap
                if st.has("heavy_plate+3"):
                    per, seconds, most = config.TEMPERED
                    self.temper = (self.temper + [seconds])[-most:]
        self.since_hit = 0.0
        self.hits_taken += 1
        if source is not None and source is not self \
                and getattr(source, "faction", None) == "enemy" and source.alive:
            self.struck_by = source                     # (Stormjar +6: Thunderhead)
        if st.has("pack_leader+9") and source is not None and source is not self \
                and getattr(source, "faction", None) == "enemy" and source.alive:
            self.rush = (source, self.time + config.PACK_RUSH)   # (Packmaster +9: The pack)
        if st.has("venom+6") and source is not None and source is not self \
                and getattr(source, "faction", None) == "enemy" and source.alive:
            from ..systems.statuses import inflict         # Viper Mask +6 (Toxic blood)
            inflict(source, "poison", self, config.TOXIC_BLOOD)
        if self.shield > 0:                             # Ward Charm, Aegis
            before = self.shield
            absorbed = min(self.shield, amount)
            self.shield -= absorbed
            amount -= absorbed
            if self.shield <= 1e-9:
                self.shield = 0.0
                self.shield_broke = max(self.shield_broke, before)   # (run_rules: M28.2d)
        if st.has("retaliation"):
            self.retaliate = True
            self.retaliate_hits += 1
            self.retaliate_big = max(self.retaliate_big, amount)
            if source is not None and source is not self:
                self.retaliate_from = (source.x, source.y)
        flat, share = st.thorns                         # Thorn Mail
        if (flat or share) and source is not None and source is not self \
                and source.faction != "player" and source.alive:
            dealt = source.take_damage(flat + share * amount, self, None)
            if dealt > 0 and st.has("thorn_mail+3") and source.alive:
                from ..systems.statuses import inflict     # Brambleguard +3 (Barbs)
                inflict(source, "bleed", self, config.BARBS)
            if dealt > 0 and st.has("thorn_mail+9"):
                self.hedge.append((source, dealt))          # (Wild hedge: run_rules)
        if amount <= 0:
            self.hurt_flash = 0.12
            return 0.0
        if self.last_stand > 0 or (st.has("berserker+9")
                                   and self.hp - amount < self.max_hp * config.LAST_STAND[0]):
            amount = self._last_stand(amount)               # Wolfpelt +9 (Last stand)
        return super().take_damage(amount, source, from_angle)

    def _last_stand(self, amount: float) -> float:
        """Wolfpelt +9: dropping below LAST_STAND[0] of max HP starts it (if
        it's ready); while it runs, HP can't go under 1."""
        st = self.stats
        if self.last_stand <= 0 and self.stand_cd <= 0 and st is not None \
                and st.has("berserker+9"):
            self.last_stand = config.LAST_STAND[1]
            self.stand_cd = config.LAST_STAND[2]
        if self.last_stand > 0:
            amount = min(amount, max(0.0, self.hp - 1.0))
        return amount

    def heal(self, amount: float) -> float:
        """Aegis (a card): healing past full HP becomes shield, up to
        AEGIS_MAX of max HP."""
        if not self.alive or amount <= 0:
            return 0.0
        room = self.max_hp - self.hp
        healed = super().heal(amount)
        st = self.stats
        if st is not None and st.has("aegis") and amount > room:
            cap = max(self.shield, self.max_hp * config.AEGIS_MAX)
            self.shield = min(cap, self.shield + amount - room)
        return healed

    # --- Moving -------------------------------------------------------------------------

    def move(self, ax: float, ay: float, dt: float, world: TileSource) -> None:
        """One frame of walking toward direction (ax, ay) (any length; zero
        = stop), with collision."""
        self.last_blocked = False
        spec = self.spec
        if spec.max_speed <= 0:
            return   # towers don't walk
        if self.roll_t > 0:
            self._roll_move(dt, world)
            return
        if self.encased > 0:                  # (frozen solid, M24.2)
            self.vx = self.vy = 0.0
            return
        if self.petrified > 0:                # (P9: stone, for a moment)
            self.petrified -= dt
            self.vx = self.vy = 0.0
            return
        n = math.hypot(ax, ay)
        time_mult = max(1.0, self.time_mult) if self.unshaken else self.time_mult
        top = spec.max_speed * self.speed_mult * time_mult * self.mount_mult
        if self.slow_t > 0:                   # (P8: webs, howls, a phantom's touch)
            self.slow_t -= dt
            if not self.unshaken:             # (M28.2a: the War Drum's Unshaken)
                top *= self.slow_mult
        if self.shrunk > 0:                   # (tiny: quicker on your feet, M25.1)
            top *= config.SHRINK[1]
        if n > 0:
            tx, ty = ax / n * top, ay / n * top
            rate = spec.accel * dt * self.traction
        else:
            tx = ty = 0.0
            rate = spec.brake * dt * self.traction
        self.vx = _approach(self.vx, tx, rate)
        self.vy = _approach(self.vy, ty, rate)
        if self.vx == 0.0 and self.vy == 0.0:
            return
        dx, dy = self.vx * dt, self.vy * dt
        x0, y0 = self.x, self.y
        if self.water_walk:                   # (M27: Adventurer's Glory)
            world = WaterWalk(world)
        self.x, self.y, bx, by = move_hull(world, self.x, self.y, 0.0, self.half, self.half, dx, dy)
        if bx:
            self.vx = 0.0
        if by:
            self.vy = 0.0
        self.last_blocked = bx or by
        moved = math.hypot(self.x - x0, self.y - y0)
        if moved > 1e-9:
            self.heading = math.atan2(self.y - y0, self.x - x0)
            self.walked += moved

    def _roll_move(self, dt: float, world: TileSource) -> None:
        """One step of a roll: a straight slide at the roll's speed, stopped
        by walls like walking. It comes out of the roll at walking speed
        the same way, so the hero doesn't stop dead."""
        step = min(dt, self.roll_t)
        self.roll_t -= dt
        dx, dy = self.roll_dir
        if self.roll_speed > 0:
            if self.water_walk:
                world = WaterWalk(world)
            x0, y0 = self.x, self.y
            self.x, self.y, bx, by = move_hull(world, self.x, self.y, 0.0, self.half, self.half,
                                               dx * self.roll_speed * step,
                                               dy * self.roll_speed * step)
            self.last_blocked = bx or by
            moved = math.hypot(self.x - x0, self.y - y0)
            if moved > 1e-9:
                self.heading = math.atan2(self.y - y0, self.x - x0)
                self.walked += moved
        top = self.spec.max_speed * self.speed_mult
        self.vx, self.vy = dx * top, dy * top
        if self.roll_t <= 1e-9:                      # (float leftovers of n steps)
            self.roll_t = 0.0

    # --- Aiming ---------------------------------------------------------------------------

    def aim_at(self, wx: float, wy: float, dt: float) -> None:
        """Point the weapon at world point (wx, wy): the true angle, so shots
        travel exactly through it."""
        self.aim_point = (wx, wy)
        if wx == self.x and wy == self.y:
            return
        self.aim_angle_toward(math.atan2(wy - self.y, wx - self.x), dt)

    def aim_angle_toward(self, target: float, dt: float) -> None:
        """Turn the aim toward a world angle at the spec's speed (instantly
        if it's 0, as for the player)."""
        speed = self.spec.aim_turn_speed
        if speed <= 0:
            self.aim_angle = target
        else:
            self.aim_angle = wrap_angle(rotate_toward(self.aim_angle, target, speed * dt))

    def aim_on_target(self, target: float, tolerance: float) -> bool:
        return abs(wrap_angle(target - self.aim_angle)) <= tolerance
