"""
entities/projectile.py -- shots in flight (bolts, arrows, rocks...).

A shot flies in a straight line along the aim angle at its ShellSpec speed,
until it hits an actor or something that blocks shots, or has travelled its
max range. Hit detection lives in systems/combat.py. A returning shot (the
dwarf's axe) then turns and flies back to its owner.
"""

from __future__ import annotations

import math

from ..specs import ShellSpec


class Projectile:
    def __init__(
        self, x: float, y: float, angle: float, spec: ShellSpec,
        owner=None, damage: float | None = None,
    ) -> None:
        self.x = x
        self.y = y
        self.angle = angle            # world radians
        self.spec = spec
        self.owner = owner            # the Actor that fired it (never hits itself)
        self.damage = spec.damage if damage is None else damage
        self.dir_x = math.cos(angle)  # unit direction, world tiles
        self.dir_y = math.sin(angle)
        self.travelled = 0.0          # tiles
        self.alive = True
        self.pierce_left = spec.pierce  # enemies it may still pass through
        self.hit: set[int] = set()    # ids of actors already hit (pierce)
        self.variant = 0              # which of a spread's pellets (its color)
        self.tags: tuple[str, ...] = ()   # the weapon's damage tags (bucket T)
        self.mult = 1.0               # per-shot damage multiplier (Grand Finale, Twin Lanes...)
        self.extra_chain = 0          # per-shot extra lightning jumps
        self.sure_crit = False        # its hit always crits (Riposte)
        # Homing (M20, spec.seek_turn): the world point it looks for a
        # target around, the target once picked (False: looked, found none),
        # its turn rate (the spec's, x cards), and how often an Orbiting
        # Darts miss has swung round to try again.
        self.seek_point: tuple[float, float] | None = None
        self.seek = None
        self.seek_turn = spec.seek_turn
        self.orbits = 0
        # Cards (M16): how far it may fly (Deadeye doubles it), its hit radius
        # bonus (Bright Colors), the colors of its shot (Prism), wall bounces
        # (Ricochet), whether it split off another shot (can't split again),
        # whether a summon fired it (no crits / statuses unless Pack
        # Leader), and a status it carries ((name, stacks): Fire Wand).
        self.max_range = spec.max_range
        self.size = 0.0
        self.group: dict | None = None
        self.bounces = 0
        self.child = False
        self.summon = False
        self.inflicts: tuple[str, int] | None = None
        self.returning = False        # boomerangs: on the way back to the owner
        # P4 cards. Hang Time: seconds left hovering at the end of the throw,
        # whether it has hovered, the countdown to its next round of hits,
        # and extra spin while it hovers (drawing). Tether: the countdown to
        # the chain's next cut. Splitting Axe: already split. Converge: how
        # fast it turns (rad per tile flown) and how much turn is left.
        self.hang = 0.0
        self.hung = False
        self.hang_tick = 0.0
        self.spin = 0.0
        self.tether_t = 0.0
        self.halved = False
        self.curve = 0.0
        self.curve_left = 0.0
        # M17 (bosses): the aim a weaving shot (spec.wobble) weaves around,
        # and seconds it waits in place before flying (harmless meanwhile:
        # a contracting ring shows where it'll close first). `tint` picks a
        # color from a look's palette (psychedelic shots).
        self.base_angle = angle
        self.hold = 0.0
        self.tint = 0
        # M23.3: how fast it flies right now (the Nameless Magus's time
        # zones set it: slower or faster inside one).
        self.time_scale = 1.0
        # Lobbed shells: where it comes down, and how far that is (full range
        # straight ahead unless combat.fire aims it at a point).
        self.flight = spec.max_range
        # M28.2a (gear tricks): cuts the first enemy shot it touches (Compass
        # Orb), grows with distance (Nautilus Shell), drifts sideways (tiles
        # per tile flown, and how far it may go; Twinned Quiver), the twin
        # pair it belongs to (who each twin hit), how many splits deep it is
        # and the shot family it came from (Pepperbox), and whether an Echo
        # fired it (Canyon Horn).
        self.cancels = False
        self.grow = False
        self.drift = 0.0
        self.drift_left = 0.0
        self.twin: dict | None = None
        self.gen = 0
        self.family: dict | None = None
        self.echo = False
        # M28.2f, the trinkets' tricks: a Chainbolt Charm bolt (Grounding,
        # Eternal arc), a Firefly Lantern bolt that lights up what it hits
        # (Glow) / leaves a wisp where it stops (Will-o'-wisps).
        self.charm = False
        self.glow = False
        self.wisp = False
        # M28.2g, the wizard's main hand: the path a Thunderball rolls
        # along (Crackle Staff +9); it went through a wall (Haunt); hits
        # made hunting on (Endless hunt); enemies passed on a swing
        # (Planets); it lost a target (Persistence).
        self.ball: list | None = None
        self.haunted = False
        self.hunts = 0
        self.passed: set[int] = set()
        self.persisted = False
        # M28.2h, the dwarf's and the huntress's main hands: an axe glanced
        # off a big enemy (Pinball); hits while hovering (Saw) and s held
        # up (Hold it there); swinging round on its chain (Flail: radians
        # left, radius, angle); the enemy it drags (Shackle); rethrows
        # (Gale force); the pieces of one split axe (Reunite) and where a
        # piece aims first (Crossing). Arrows: enemies pierced, came back
        # (Run-through), a Deadeye crit (Follow-through).
        self.pinballed = False
        self.saws = 0
        self.held = 0.0
        self.flail = 0.0
        self.flail_r = 0.0
        self.flail_a = 0.0
        self.flailed = False
        self.shackle: tuple | None = None
        self.shackled = False
        self.spins = 0
        self.pieces: list | None = None
        self.reunited = False
        self.cross: tuple | None = None
        self.pierced = 0
        self.came_back = False
        self.deadeye = False
        self.followed = False
        # M28.2b: x its speed (Blazecrown +6, Heat haze: a burning enemy's
        # shots), and whether it shocks what it hits (Galvanic Mask +6).
        self.pace = 1.0
        self.shocks = False
        # M28.2c: fired by a riposte (Fencer's Boots), thrown back by a
        # roll (plain damage, Hairsbreadth), makes what it hits aim off
        # (Dancing Slippers), and x its crit chance (Tumbler Boots).
        self.riposte = False
        self.plain = False
        self.dizzy = False
        self.crit_x = 1.0
        # M28.2i: the princess's and the bard's main hands. One beam of
        # every color (Spyglass +9); the middle color (Lens); Converge's
        # middle line, where the fan left, where it crosses, the enemy it
        # follows (Lockstep) and crossings still to come (Second crossing);
        # how many times a piece has split again (Infinite mirror); a
        # note's way round walls and its target (Birdsong).
        self.beam = False
        self.middle = False
        self.mid: float | None = None
        self.origin: tuple[float, float] | None = None
        self.focal: list | None = None
        self.lock = None
        self.crossings = 0
        self.refracted = 0
        self.path: list | None = None
        self.bird = None
        self.target: tuple[float, float] | None = (
            (x + self.dir_x * spec.max_range, y + self.dir_y * spec.max_range) if spec.lob else None)
