"""
systems/quests.py -- the run's quests (M17, design/BOSSES.md).

Every quest in config.QUESTS whose camp and lair could be placed on this
island gets a QuestState (M22.5: all of a biome's bosses, every run). The
quests are HIDDEN: nothing about them shows until their boss wakes, unless
a player takes one from its giver. Stages:

  "hunt"     from the start of the run: the quest's targets are out at
             the camp's spots, scattered over the biome -- a few more of
             them than the quest needs (they wake, sleep and stay dead like
             any enemy, systems/spawner.place); every one that dies counts,
             whoever killed it, quest taken or not;
             (a "light" quest, M22.2: the spots hold braziers instead;
             one catches after a hero stands by it for a while, and
             mosquitoes swarm whoever is lighting it; a "collect" quest,
             M23.2: the spots hold bundles of cargo, each guarded by a few
             of the quest's enemies -- once they're dead, walk up to the
             bundle to take it; a "survive" quest, M23.3: the spots hold
             sealed star circles -- stand in one long enough to break its
             seal, while the quest's enemies rise round you in waves; an
             "escort" quest, M24.1: the giver herself follows whoever took
             the quest and plants a beacon at each spot she's led to, while
             waves of the quest's enemies come for the players -- she can't
             be hurt; it needs her, so it can't be done without her; a
             "rescue" quest, M24.2: the spots hold captives frozen in ice
             blocks -- shatter one, then stay close while they thaw, with
             the quest's enemies trying to re-freeze them; a "fetch" quest,
             M24.3: guarded pieces to carry back to the giver -- and then,
             sewn whole, Mr. Buttons the bear, carried into the fight and
             given back to Fragile after it);
             the giver (unpinned: you find their camp) tells you what to
             do; talking to them TAKES the quest (`taken`): it gets a
             counter in the quest log, and its living targets are pinned
             once you're near one;
  "awake"    all found: "SOMETHING STIRS...", and the boss waits in its
             lair, now pinned on the maps;
  "fight"    a player went LAIR_SEAL_DEPTH tiles into the arena: the gate
             fills with thorns (each tile as soon as nobody stands in it),
             the boss rises with its name across the screen, and the
             arena's chunks stay loaded wherever the players are in it;
  "cleared"  the boss fell: the gate opens, and every player gets the
             reward (loot, a rare+ card offer; the achievement and the
             bestiary pages go to the Guild). The first boss beaten in a
             biome is one more guardian down for the main quest, "Gain
             Adventurer's Glory"; the biome's others are optional.

Several fights can be on at once (co-op players in different arenas).
What the giver says depends on the stage (QuestSpec.lines); their words
hang over their head a line at a time. The main quest counts guardians
(biomes with a cleared quest) toward config.GUARDIANS.

All of it runs inside the simulation step, from the players' inputs and
the game state only (deterministic).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .. import config
from ..entities.effects import Effect
from ..world import tiles
from ..world.rng import hash_coords
from .collision import hull_hits_solid

# Spawn ids of quest enemies: (QUEST_SID, quest id, i, 0) -- four ints, so
# they never clash with a chunk roster's (cx, cy, k). A quest's id is its
# place in config.QUESTS, from 1.
QUEST_SID = 0x51E57


def quest_id(key: str) -> int:
    return list(config.QUESTS).index(key) + 1


def place_name(name: str) -> str:
    """A map name ("FROGGY'S POND") in a sentence: "Froggy's Pond"
    (str.title would give "Froggy'S")."""
    return " ".join(w.capitalize() for w in name.split())


@dataclass
class Npc:
    """Someone to talk to at a landmark."""

    name: str
    sprite: str
    x: float
    y: float
    biome: str
    quest: str = ""                # the config.QUESTS key they give
    speech: tuple = ()
    speech_t: float = 0.0

    def say(self, lines) -> None:
        self.speech = tuple(lines)
        self.speech_t = 0.0

    def update(self, dt: float) -> None:
        if self.speech:
            self.speech_t += dt
            if self.speech_t >= len(self.speech) * config.SPEECH_LINE_TIME:
                self.speech = ()

    @property
    def line(self) -> str | None:
        if not self.speech:
            return None
        return self.speech[min(len(self.speech) - 1,
                               int(self.speech_t / config.SPEECH_LINE_TIME))]


@dataclass
class QuestState:
    key: str                           # its config.QUESTS key
    spec: object                       # specs.QuestSpec
    camp: object                       # world/landmarks.Landmark
    lair: object
    npc: Npc
    stage: str = "hunt"
    taken: bool = False                # a player talked to the giver
    found: int = 0                     # hunt: targets dead so far
    boss: object = None
    pending: list = field(default_factory=list)   # gate tiles still to seal
    fight_time: float = 0.0
    damage_taken: float = 0.0          # by the players during the fight (dev report)
    lit: set = field(default_factory=set)       # light / collect / survive / escort: spots done
    stuck: float = 0.0                 # escort: s the giver has been blocked following
    opened: set = field(default_factory=set)    # rescue: captives whose block is shattered
    wraiths: dict = field(default_factory=dict) # rescue: spot -> the enemies sent at it
    carry: dict = field(default_factory=dict)   # fetch: player index -> pieces carried
    bear: int | None = None            # fetch: the player carrying the finished bear
    drops: list = field(default_factory=list)   # fetch: [x, y, "piece" | "bear"] on the ground
    crying: object = None              # fetch: Fragile, beaten, crying (an Npc)
    gifted: bool = False               # fetch: the bear's been given back
    heat: dict = field(default_factory=dict)    # light quests: spot index -> s of heat
    swarmed: set = field(default_factory=set)   # light quests: (spot, wave) already sent

    @property
    def biome(self) -> str:
        return self.spec.biome

    @property
    def qid(self) -> int:
        return quest_id(self.key)


@dataclass
class Banner:
    """Big text across the middle of the screen for a while."""

    title: str
    sub: str
    t: float = 0.0
    duration: float = config.BOSS_BANNER_TIME


class Quests:
    def __init__(self, scene) -> None:
        self.scene = scene
        self.world = scene.world
        layout = getattr(self.world, "layout", None)
        self.states: dict[str, QuestState] = {}     # config.QUESTS key -> its state
        if layout is not None:
            from ..world.landmarks import quest_marks
            for key, spec in config.QUESTS.items():
                camp, lair = quest_marks(layout, key)
                if camp is None or lair is None or camp.npc is None:
                    continue
                npc = Npc(spec.giver, spec.giver_sprite, *camp.npc, spec.biome, quest=key)
                s = self.states[key] = QuestState(key, spec, camp, lair, npc)
                self._place_targets(s)
        self.banner: Banner | None = None

    # --- Queries --------------------------------------------------------------------

    @property
    def npcs(self) -> list[Npc]:
        return [s.npc for s in self.states.values()] + \
            [s.crying for s in self.states.values() if s.crying is not None]

    @property
    def guardians(self) -> int:
        """Ring biomes with a boss beaten (one per biome counts)."""
        return len({s.biome for s in self.states.values() if s.stage == "cleared"})

    @property
    def fights(self) -> list[QuestState]:
        return [s for s in self.states.values() if s.stage == "fight"]

    @property
    def fight(self) -> QuestState | None:
        """A fight in progress (the first; see fight_for)."""
        return next(iter(self.fights), None)

    def fight_for(self, hero) -> QuestState | None:
        """The fight this hero is in (inside its arena), else the nearest one
        going on (for the boss bar and the off-screen pointer)."""
        fights = self.fights
        for s in fights:
            if s.lair.inside(hero.x, hero.y):
                return s
        return min(fights, key=lambda s: math.hypot(s.lair.cx - hero.x, s.lair.cy - hero.y),
                   default=None)

    def npc_near(self, hero) -> Npc | None:
        best, best_d = None, config.TALK_RADIUS
        for npc in self.npcs:
            d = math.hypot(npc.x - hero.x, npc.y - hero.y)
            if d <= best_d:
                best, best_d = npc, d
        return best

    def stream_views(self) -> list[tuple[float, float, float, float]]:
        """Extra areas to keep loaded: the arenas of fights in progress (a
        boss roams all of its arena, often far from the players' screens)."""
        out = []
        for s in self.fights:
            a, b = s.lair.radii
            out.append((s.lair.cx, s.lair.cy, a + config.LAIR_WALL, b + config.LAIR_WALL))
        return out

    def log(self) -> list[tuple[str, str, bool]]:
        """The quest log: (label, text, done) lines -- the main quest, then
        a counter for each quest taken from its giver until its boss falls.
        Quests nobody took stay hidden (M22.5)."""
        out = [("GLORY", f"guardians {self.guardians}/{config.GUARDIANS}", False)]
        for s in self.states.values():
            if s.crying is not None and not s.gifted:            # (M24.3)
                out.append((s.biome.upper(), "give Fragile her bear", False))
                continue
            if not s.taken or s.stage == "cleared":
                continue
            spec = s.spec
            boss = config.BOSSES[spec.boss].name
            text = {
                "hunt": spec.goal.format(n=s.found, count=spec.count),
                "awake": f"go to {place_name(s.lair.name)}",
                "fight": f"defeat {boss}",
            }[s.stage]
            out.append((s.biome.upper(), text, False))
        return out

    def pins(self, near: tuple[float, float] | None = None) -> list[tuple[float, float, str, str]]:
        """Map pins: (x, y, kind, label); kind "lair" | "target" | "done".
        Givers and lairs are found, not pinned (M22.5); a lair is pinned
        once its boss wakes. A taken quest's targets (still alive) are
        pinned only within QUEST_TARGET_PIN_RADIUS tiles of `near` (the
        viewing player; None: all of them): you roam the biome until you're
        close, then the pin leads you in."""
        out = []
        sp = self.scene.spawner
        for s in self.states.values():
            giver_done = s.stage == "cleared"
            if s.stage == "hunt" and s.taken:
                qid = s.qid
                light = s.spec.kind in ("light", "collect", "survive", "escort", "rescue",
                                        "fetch")
                label = {"light": "BRAZIER", "collect": "CARGO", "survive": "SEAL",
                         "escort": "BEACON", "rescue": "CAPTIVE",
                         "fetch": "PIECE"}.get(s.spec.kind) \
                    or config.ENEMIES[s.spec.target].name.split()[-1].upper()
                for i, (x, y) in enumerate(s.camp.spots):
                    if near is not None and math.hypot(x - near[0], y - near[1]) \
                            > config.QUEST_TARGET_PIN_RADIUS:
                        continue
                    if light:
                        if i not in s.lit:
                            out.append((x, y, "target", label))
                    elif sp is None or (QUEST_SID, qid, i, 0) not in sp.dead:
                        out.append((x, y, "target", label))
            if s.stage in ("awake", "fight", "cleared"):
                out.append((s.lair.cx, s.lair.cy, "done" if giver_done else "lair", s.lair.name))
            for x, y, what in s.drops:          # (M24.3: dropped pieces / the bear)
                out.append((x, y, "bear", "MR. BUTTONS" if what == "bear" else "PIECE"))
            marks = getattr(s.boss, "map_marks", None) if s.stage == "fight" else None
            if marks is not None:
                out.extend(marks())             # (M24.1: the fight's fixtures)
        return out

    # --- Simulation step -------------------------------------------------------------

    def step(self, dt: float, players, inputs) -> None:
        """Talk to givers (players who pressed interact), tick speech, and
        run each quest's stage."""
        for npc in self.npcs:
            npc.update(dt)
        for e in self.scene.enemies:
            if getattr(e, "fresh", False):          # a quest enemy appearing
                e.fresh = False
                self.scene.effects.append(Effect("nova", e.x, e.y, size=2.0))
        for p in players:
            inp = inputs.get(p.index)
            if inp is not None and inp.interact and p.alive and not p.ghost:
                npc = self.npc_near(p.hero)
                if npc is not None:
                    self.talk(npc, p)
        for s in self.states.values():
            if s.spec.kind == "fetch" and not s.gifted:   # (every stage: the pieces, the bear)
                self._fetch(s, players, dt)
            if s.stage == "hunt" and s.spec.kind == "light":
                self._tend_braziers(s, players, dt)
            elif s.stage == "hunt" and s.spec.kind == "collect":
                self._collect(s, players)
            elif s.stage == "hunt" and s.spec.kind == "survive":
                self._hold_seals(s, players, dt)
            elif s.stage == "hunt" and s.spec.kind == "escort":
                self._escort(s, players, dt)
            elif s.stage == "hunt" and s.spec.kind == "rescue":
                self._rescue(s, players, dt)
            elif s.stage == "awake":
                self._maybe_start_fight(s, players)
            elif s.stage == "fight":
                s.fight_time += dt
                self._seal(s)
        if self.banner is not None:
            self.banner.t += dt
            if self.banner.t >= self.banner.duration:
                self.banner = None

    def talk(self, npc: Npc, p) -> None:
        s = self.states[npc.quest]
        if npc is s.crying:
            self._gift(s, p)
            return
        spec = s.spec
        first = not s.taken
        s.taken = True
        if s.stage == "hunt" and first:
            npc.say(spec.say("offer"))
        elif s.stage == "hunt":
            left = spec.count - s.found
            npc.say(line.format(left=left) for line in spec.say("progress"))
        elif s.stage == "awake":
            npc.say(spec.say("done"))
        elif s.stage == "fight":
            npc.say(spec.say("fight"))
        else:
            npc.say(spec.say("cleared"))
        if p.local:
            self.scene._sounds.append("ui")

    def _place_targets(self, s: QuestState) -> None:
        """A hunt's targets go out at the camp's spots when the run starts
        (spawn id (QUEST_SID, quest, spot, 0)); a collect quest's guards
        round each bundle (..., spot, 1..CARGO_GUARDS)."""
        sp = self.scene.spawner
        if sp is None:
            return
        if s.spec.kind == "hunt":
            for i, (x, y) in enumerate(s.camp.spots):
                sp.place((QUEST_SID, s.qid, i, 0), s.spec.target, x, y)
        elif s.spec.kind in ("collect", "fetch"):
            n = config.CARGO_GUARDS
            for i, (x, y) in enumerate(s.camp.spots):
                for k in range(n):
                    a = (i * 1.3 + k * math.tau / n)
                    r = config.CARGO_GUARD_RING
                    sp.place((QUEST_SID, s.qid, i, k + 1), s.spec.target,
                             x + math.cos(a) * r, y + math.sin(a) * r * 0.7)

    def guards_left(self, s: QuestState, i: int) -> int:
        """Collect quests: the guards still alive round bundle i."""
        sp = self.scene.spawner
        if sp is None:
            return 0
        return sum(1 for k in range(config.CARGO_GUARDS)
                   if (QUEST_SID, s.qid, i, k + 1) not in sp.dead)

    def is_target(self, s: QuestState, enemy) -> bool:
        sid = getattr(enemy, "spawn_id", None)
        return (isinstance(sid, tuple) and len(sid) == 4 and sid[0] == QUEST_SID
                and sid[1] == s.qid)

    def on_death(self, enemy, killer) -> None:
        """An enemy died (`killer`: the player who killed it, or None)."""
        for s in self.states.values():
            if s.stage == "hunt" and s.spec.kind == "hunt" and self.is_target(s, enemy):
                self._found(s, killer.hero if killer is not None else enemy)
            elif s.stage == "fight" and enemy is s.boss:
                self._win(s, killer)

    def _found(self, s: QuestState, at) -> None:
        """One more target done (a hunt's kill, a brazier lit): a toast over
        `at` if the quest was taken (otherwise it counts silently), or, the
        last one, the boss wakes whether or not anyone took the quest."""
        s.found += 1
        if s.found >= s.spec.count:
            s.stage = "awake"
            self.banner = Banner("SOMETHING STIRS...",
                                 f"{place_name(s.lair.name)} is marked on your map")
            self.scene._sounds.append("chime")
        elif s.taken:
            self.scene.effects.append(Effect(
                "toast", at.x, at.y - 1,
                label=s.spec.goal.format(n=s.found, count=s.spec.count).upper()))
            self.scene._sounds.append("chime")

    # --- Collect quests (M23.2) ---------------------------------------------------------

    def _collect(self, s: QuestState, players) -> None:
        """A hero by a bundle takes it once its guards are dead (until then,
        a reminder over the bundle, once each time someone walks up)."""
        heroes = [p.hero for p in players if p.alive and not p.ghost]
        for i, (x, y) in enumerate(s.camp.spots):
            if i in s.lit:
                continue
            by = [h for h in heroes if math.hypot(h.x - x, h.y - y) <= config.CARGO_RADIUS + 1.0]
            if not by:
                s.heat.pop(i, None)
                continue
            if self.guards_left(s, i):
                if i not in s.heat:              # (s.heat: warned since they walked up)
                    s.heat[i] = 1.0
                    self.scene.effects.append(Effect("toast", x, y - 1.5,
                                                     label="THE CAMELS WON'T BUDGE!"))
                continue
            s.lit.add(i)
            s.heat.pop(i, None)
            if hasattr(self.world, "set_tile"):
                self.world.set_tile(math.floor(x), math.floor(y),
                                    tiles.SAND if s.biome == "desert" else tiles.MUD)
            self.scene.effects.append(Effect("nova", x, y, size=2.0))
            self._found(s, by[0])
            if s.stage != "hunt":
                return

    # --- Survive quests (M23.3) ---------------------------------------------------------

    def _hold_seals(self, s: QuestState, players, dt: float) -> None:
        """A star circle with a hero inside wears its seal down (s.heat: s of
        it); with nobody inside it heals back SEAL_HEAL x as fast. Each
        SEAL_WAVE s of wear, a wave of the quest's enemies rises round it
        (each wave once). SEAL_TIME s and the seal breaks."""
        heroes = [p.hero for p in players if p.alive and not p.ghost]
        full = config.SEAL_TIME
        for i, (x, y) in enumerate(s.camp.spots):
            if i in s.lit:
                continue
            inside = [h for h in heroes if math.hypot(h.x - x, h.y - y) <= config.SEAL_RADIUS]
            worn = s.heat.get(i, 0.0)
            if not inside:
                if worn > 0:
                    s.heat[i] = max(0.0, worn - dt * config.SEAL_HEAL)
                continue
            wave = int(worn // config.SEAL_WAVE)
            if (i, wave) not in s.swarmed:
                s.swarmed.add((i, wave))
                self._rise(s, i, wave, x, y)
            worn += dt
            s.heat[i] = worn
            if worn >= full:
                s.lit.add(i)
                s.heat.pop(i, None)
                if hasattr(self.world, "set_tile"):
                    self.world.set_tile(math.floor(x), math.floor(y), tiles.SEAL_BROKEN)
                self.scene.effects.append(Effect("nova", x, y, size=config.SEAL_RADIUS))
                self.scene.effects.append(Effect("toast", x, y - 2, label="THE SEAL BREAKS!"))
                self._found(s, inside[0])
                if s.stage != "hunt":
                    return

    def _rise(self, s: QuestState, i: int, wave: int, x: float, y: float) -> None:
        """A wave of the quest's enemies rising out of the sand round a star
        circle (dice from the seed, the spot and the wave)."""
        sp = self.scene.spawner
        if sp is None:
            return
        rng = random.Random(hash_coords(getattr(self.world, "seed", 0) or 0, 0x5EA1, s.qid, i,
                                        wave))
        lo, hi = config.SEAL_WAVE_RANGE
        for _ in range(rng.randint(*config.SEAL_WAVE_SIZE)):
            a = rng.uniform(0, math.tau)
            r = rng.uniform(lo, hi)
            ex, ey = free_spot(self.world, x + math.cos(a) * r, y + math.sin(a) * r, 11.0)
            e = sp.wake(s.spec.target, ex, ey, None, random.Random(rng.random()))
            e.alert = True
            self.scene.enemies.append(e)
            self.scene.effects.append(Effect("eruption", ex, ey))

    # --- Escort quests (M24.1) ----------------------------------------------------------

    def _escort(self, s: QuestState, players, dt: float) -> None:
        """Once taken, the giver follows the nearest player within
        ESCORT_RANGE; within ESCORT_SITE of a spot without a beacon she stops
        and plants one over ESCORT_SETUP s (s.heat), a wave of the quest's
        enemies coming at each ESCORT_WAVES mark -- for the players: she
        can't be hurt."""
        if not s.taken:
            return
        npc = s.npc
        for i, (x, y) in enumerate(s.camp.spots):
            if i in s.lit or math.hypot(npc.x - x, npc.y - y) > config.ESCORT_SITE:
                continue
            done = s.heat.get(i, 0.0)
            for wave, at in enumerate(config.ESCORT_WAVES):
                if done >= at and (i, wave) not in s.swarmed:
                    s.swarmed.add((i, wave))
                    self._ambush(s, i, wave, x, y)
            done += dt
            s.heat[i] = done
            if done >= config.ESCORT_SETUP:
                s.lit.add(i)
                s.heat.pop(i, None)
                if hasattr(self.world, "set_tile"):
                    self.world.set_tile(math.floor(x), math.floor(y), tiles.BEACON)
                self.scene.effects.append(Effect("nova", x, y, size=3.0))
                self.scene.effects.append(Effect("toast", x, y - 2, label="BEACON PLANTED!"))
                self._found(s, npc)
            return                                  # (planting: she stays put)
        heroes = [p.hero for p in players if p.alive and not p.ghost]
        near = [h for h in heroes if math.hypot(h.x - npc.x, h.y - npc.y) <= config.ESCORT_RANGE]
        if not near:
            return
        lead = min(near, key=lambda h: math.hypot(h.x - npc.x, h.y - npc.y))
        dx, dy = lead.x - npc.x, lead.y - npc.y
        d = math.hypot(dx, dy)
        if d <= config.ESCORT_GAP:
            s.stuck = 0.0
            return
        step = min(d - config.ESCORT_GAP, config.ESCORT_SPEED * dt)
        ux, uy = dx / d, dy / d
        # (She starts on her post, a solid tile: from there any step goes.)
        stuck_in = hull_hits_solid(self.world, npc.x, npc.y, 0.0, 9.0, 9.0)
        for mx, my in ((ux, uy), (ux, 0.0), (0.0, uy)):
            nx, ny = npc.x + mx * step, npc.y + my * step
            if (mx or my) and (stuck_in or not hull_hits_solid(self.world, nx, ny, 0.0, 9.0, 9.0)):
                npc.x, npc.y = nx, ny
                s.stuck = 0.0
                break
        else:
            s.stuck += dt
            if s.stuck > 1.5:                       # caught on something: she catches up
                npc.x, npc.y = free_spot(self.world, lead.x - ux * config.ESCORT_GAP,
                                         lead.y - uy * config.ESCORT_GAP, 9.0)
                s.stuck = 0.0
                self.scene.effects.append(Effect("burrow", npc.x, npc.y))

    def _ambush(self, s: QuestState, i: int, wave: int, x: float, y: float) -> None:
        """A wave of the quest's enemies coming for the players at a site."""
        sp = self.scene.spawner
        if sp is None:
            return
        rng = random.Random(hash_coords(getattr(self.world, "seed", 0) or 0, 0xE5C0, s.qid, i,
                                        wave))
        lo, hi = config.ESCORT_WAVE_RANGE
        for _ in range(config.ESCORT_WAVE_SIZE):
            a = rng.uniform(0, math.tau)
            r = rng.uniform(lo, hi)
            ex, ey = free_spot(self.world, x + math.cos(a) * r, y + math.sin(a) * r, 9.0)
            e = sp.wake(s.spec.target, ex, ey, None, random.Random(rng.random()))
            e.alert = True
            self.scene.enemies.append(e)
            self.scene.effects.append(Effect("eruption", ex, ey))

    # --- Rescue quests (M24.2) ----------------------------------------------------------

    def _rescue(self, s: QuestState, players, dt: float) -> None:
        """A captive whose ice block is shattered (the tile isn't ICE_BLOCK
        any more) thaws while a hero is within RESCUE_WARM tiles (s.heat);
        waves of the quest's enemies come at RESCUE_WAVES marks, drifting at
        the captive, and one that touches them knocks the thaw back. Thawed:
        freed. (Only spots near a hero are looked at: far ones may not be
        loaded.)"""
        heroes = [p.hero for p in players if p.alive and not p.ghost]
        for i, (x, y) in enumerate(s.camp.spots):
            if i in s.lit or not any(math.hypot(h.x - x, h.y - y) < 40 for h in heroes):
                continue
            if i not in s.opened:
                if self.world.tile_at(math.floor(x), math.floor(y)) is tiles.ICE_BLOCK:
                    continue
                s.opened.add(i)
                self.scene.effects.append(Effect("toast", x, y - 2, label="STAY CLOSE! KEEP THEM WARM!"))
            for w in s.wraiths.get(i, []):
                if w.alive and getattr(w, "touched", False):
                    w.touched = False
                    w.hp = 0.0
                    w.last_hit_by = None
                    s.heat[i] = max(0.0, s.heat.get(i, 0.0) - config.RESCUE_REFREEZE * config.RESCUE_THAW)
                    self.scene.effects.append(Effect("toast", x, y - 2, label="RE-FROZEN!"))
            if not any(math.hypot(h.x - x, h.y - y) <= config.RESCUE_WARM for h in heroes):
                continue
            done = s.heat.get(i, 0.0)
            for wave, at in enumerate(config.RESCUE_WAVES):
                if done >= at and (i, wave) not in s.swarmed:
                    s.swarmed.add((i, wave))
                    self._send_wraiths(s, i, wave, x, y)
            done += dt
            s.heat[i] = done
            if done >= config.RESCUE_THAW:
                s.lit.add(i)
                s.heat.pop(i, None)
                for w in s.wraiths.pop(i, []):
                    w.goal_pos = None               # (they turn on the players)
                self.scene.effects.append(Effect("nova", x, y, size=3.0))
                self.scene.effects.append(Effect("toast", x, y - 2, label="FREED! THANK YOU!"))
                self._found(s, heroes[0])
                if s.stage != "hunt":
                    return

    def _send_wraiths(self, s: QuestState, i: int, wave: int, x: float, y: float) -> None:
        sp = self.scene.spawner
        if sp is None:
            return
        rng = random.Random(hash_coords(getattr(self.world, "seed", 0) or 0, 0xF205, s.qid, i,
                                        wave))
        lo, hi = config.RESCUE_WAVE_RANGE
        for _ in range(config.RESCUE_WAVE_SIZE):
            a = rng.uniform(0, math.tau)
            r = rng.uniform(lo, hi)
            e = sp.wake(s.spec.target, x + math.cos(a) * r, y + math.sin(a) * r, None,
                        random.Random(rng.random()))
            e.alert = True
            e.goal_pos = (x, y)
            s.wraiths.setdefault(i, []).append(e)
            self.scene.enemies.append(e)
            self.scene.effects.append(Effect("burrow", e.x, e.y))

    # --- Fetch quests (M24.3) -----------------------------------------------------------

    def _fetch(self, s: QuestState, players, dt: float) -> None:
        """Pieces: taken (guards dead) and carried (s.carry); delivered to the
        giver one by one. The last sews Mr. Buttons whole -- he goes with
        whoever brought it (s.bear). A downed carrier drops what they have
        (s.drops); anyone walking over it picks it up."""
        for p in players:                         # a fallen carrier drops it all
            if p.alive:
                continue
            n = s.carry.pop(p.index, 0)
            for _ in range(n):
                s.drops.append([p.hero.x, p.hero.y, "piece"])
            if s.bear == p.index:
                s.bear = None
                s.drops.append([p.hero.x, p.hero.y, "bear"])
        living = [p for p in players if p.alive and not p.ghost]
        for d in list(s.drops):
            p = next((p for p in living
                      if math.hypot(p.hero.x - d[0], p.hero.y - d[1]) <= config.FETCH_PICKUP), None)
            if p is None:
                continue
            s.drops.remove(d)
            if d[2] == "bear":
                s.bear = p.index
                self.scene.effects.append(Effect("toast", d[0], d[1] - 1.5, label="MR. BUTTONS!"))
            else:
                s.carry[p.index] = s.carry.get(p.index, 0) + 1
        if s.stage != "hunt":
            return
        for i, (x, y) in enumerate(s.camp.spots):
            if i in s.lit:
                continue
            near = [p for p in living
                    if math.hypot(p.hero.x - x, p.hero.y - y) <= config.CARGO_RADIUS + 1.0]
            if not near:
                s.heat.pop(i, None)
                continue
            if self.guards_left(s, i):
                if i not in s.heat:
                    s.heat[i] = 1.0
                    self.scene.effects.append(Effect("toast", x, y - 1.5,
                                                     label="THE BATS WON'T LET YOU!"))
                continue
            s.lit.add(i)
            s.heat.pop(i, None)
            p = near[0]
            s.carry[p.index] = s.carry.get(p.index, 0) + 1
            if hasattr(self.world, "set_tile"):
                self.world.set_tile(math.floor(x), math.floor(y),
                                    tiles.CONCRETE if s.biome == "ruins" else tiles.SAND)
            self.scene.effects.append(Effect("toast", x, y - 1.5, label="A PIECE OF MR. BUTTONS!"))
            self.scene._sounds.append("chime")
        npc = s.npc
        for p in living:
            n = s.carry.get(p.index, 0)
            if n <= 0 or math.hypot(p.hero.x - npc.x, p.hero.y - npc.y) > config.FETCH_DELIVER:
                continue
            s.carry.pop(p.index)
            s.taken = True
            for _ in range(n):
                if s.stage == "hunt":
                    self._found(s, p.hero)
            if s.stage != "hunt":
                s.bear = p.index
                npc.say(s.spec.say("done"))
                self.scene.effects.append(Effect("toast", p.hero.x, p.hero.y - 2,
                                                 label="MR. BUTTONS IS WHOLE! TAKE HIM!"))
                return
            npc.say(line.format(left=s.spec.count - s.found) for line in s.spec.say("progress"))

    def _gift(self, s: QuestState, p) -> None:
        """Talking to Fragile, beaten and crying: whoever has Mr. Buttons
        gives him back -- FRAGILE_GIFT_LEVELS levels for every player."""
        cry = s.crying
        if s.gifted:
            cry.say(("Thank you... I'll take good care of him.",))
            return
        if s.bear != p.index:
            cry.say(("*sniff* ...Mr. Buttons... where is he?",
                     "They took him. They always take everything."))
            return
        s.bear = None
        s.gifted = True
        cry.say(("...Mr. Buttons? You... brought him back?",
                 "Nobody ever brings anything back. Thank you.",
                 "I'm... sorry. About the ballroom. And everything."))
        scene = self.scene
        for q in scene.players:
            if q.ghost:
                continue
            for _ in range(config.FRAGILE_GIFT_LEVELS):
                scene._gain_xp(q, q.progress.needed - q.progress.xp)
        scene.effects.append(Effect("toast", cry.x, cry.y - 3,
                                    label=f"+{config.FRAGILE_GIFT_LEVELS} LEVELS!"))
        scene._sounds.append("chime")

    def pointers(self, p) -> list[tuple[float, float, str]]:
        """Edge-of-screen arrows for this player's quest errands: the giver's
        stall while carrying pieces; Fragile, crying, while holding her bear."""
        out = []
        for s in self.states.values():
            if s.spec.kind != "fetch":
                continue
            if s.carry.get(p.index, 0) > 0:
                out.append((s.npc.x, s.npc.y, "STALL"))
            if s.bear == p.index and s.crying is not None and not s.gifted:
                out.append((s.crying.x, s.crying.y, "FRAGILE"))
        return out

    # --- Light quests (M22.2) -----------------------------------------------------------

    def _tend_braziers(self, s: QuestState, players, dt: float) -> None:
        """Every unlit brazier with a hero by it heats up (and calls in the
        mosquitoes as it passes each BRAZIER_SWARMS fraction); with nobody
        there it cools. One that's hot enough catches: it smokes for good."""
        heroes = [p.hero for p in players if p.alive]
        full = config.BRAZIER_LIGHT_TIME
        for i, (x, y) in enumerate(s.camp.spots):
            if i in s.lit:
                continue
            by = [h for h in heroes if math.hypot(h.x - x, h.y - y) <= config.BRAZIER_RADIUS]
            heat = s.heat.get(i, 0.0)
            if not by:
                if heat > 0:
                    s.heat[i] = max(0.0, heat - dt * config.BRAZIER_COOL)
                continue
            for wave, at in enumerate(config.BRAZIER_SWARMS):
                if heat >= at * full and (i, wave) not in s.swarmed:
                    s.swarmed.add((i, wave))
                    self._swarm(s, i, wave, x, y)
            heat += dt
            s.heat[i] = heat
            if heat >= full:
                s.lit.add(i)
                s.heat.pop(i, None)
                if hasattr(self.world, "set_tile"):
                    self.world.set_tile(math.floor(x), math.floor(y), tiles.BRAZIER_LIT)
                self.scene.effects.append(Effect("nova", x, y, size=2.5))
                self._found(s, by[0])
                if s.stage != "hunt":
                    return

    def _swarm(self, s: QuestState, i: int, wave: int, x: float, y: float) -> None:
        """BRAZIER_SWARM_SIZE mosquitoes buzzing in at the brazier (dice
        from the seed, the spot and the wave: deterministic)."""
        sp = self.scene.spawner
        if sp is None:
            return
        rng = random.Random(hash_coords(getattr(self.world, "seed", 0) or 0, 0xB4A2, s.qid, i,
                                        wave))
        lo, hi = config.BRAZIER_SWARM_RANGE
        for _ in range(config.BRAZIER_SWARM_SIZE):
            a = rng.uniform(0, math.tau)
            r = rng.uniform(lo, hi)
            e = sp.wake("mosquito", x + math.cos(a) * r, y + math.sin(a) * r, None,
                        random.Random(rng.random()))
            e.alert = True
            self.scene.enemies.append(e)

    # --- The fight ------------------------------------------------------------------

    def _maybe_start_fight(self, s: QuestState, players) -> None:
        lair = s.lair
        if not any(p.alive and lair.inside(p.hero.x, p.hero.y, config.LAIR_SEAL_DEPTH)
                   for p in players):
            return
        s.stage = "fight"
        s.fight_time = 0.0
        s.pending = list(lair.gate)
        sp = self.scene.spawner
        x, y = lair.spots[0] if lair.spots else (lair.cx, lair.cy)
        rng = random.Random(hash_coords(getattr(self.world, "seed", 0) or 0, 0xB055, s.qid))
        if sp is not None:
            boss = sp.wake(s.spec.boss, x, y, None, rng)
        else:
            from ..ai import make_enemy
            boss = make_enemy(s.spec.boss, x, y, rng)
        humans = sum(1 for p in players if not p.ghost)
        boss.scale_for(humans)
        boss.lair = lair
        boss.recruit = self._recruiter(rng)
        s.boss = boss
        self.scene.enemies.append(boss)
        # A swarm boss (M22) fights with many bodies: they join the enemies.
        self.scene.enemies.extend(getattr(boss, "parts", ()))
        self.banner = Banner(boss.espec.name.upper(), "guardian of the " + s.biome)
        self.scene.effects.append(Effect("explosion", x, y))
        self.scene._sounds.append("boulder")
        self._seal(s)

    def _recruiter(self, rng: random.Random):
        """What a boss calls to bring in adds (they join the fight now)."""
        scene = self.scene

        def recruit(key: str, x: float, y: float):
            sp = scene.spawner
            if sp is None:
                return None
            e = sp.wake(key, x, y, None, random.Random(rng.random()))
            scene.enemies.append(e)
            return e
        return recruit

    def _seal(self, s: QuestState) -> None:
        """Thorns fill the gate, tile by tile, as soon as nobody stands there."""
        if not s.pending or not hasattr(self.world, "set_tile"):
            return
        heroes = [p.hero for p in self.scene.players if p.alive]
        still = []
        for tx, ty in s.pending:
            if any(abs(h.x - (tx + 0.5)) < 1.5 and abs(h.y - (ty + 0.5)) < 1.5 for h in heroes):
                still.append((tx, ty))
                continue
            self.world.set_tile(tx, ty, tiles.THORN_GATE)
        s.pending = still

    def _open_gate(self, s: QuestState) -> None:
        s.pending = []
        if hasattr(self.world, "set_tile"):
            for tx, ty in s.lair.gate:
                self.world.set_tile(tx, ty, s.lair.floor or tiles.MUD)

    def _win(self, s: QuestState, killer) -> None:
        first = s.biome not in {o.biome for o in self.states.values() if o.stage == "cleared"}
        s.stage = "cleared"
        self._open_gate(s)
        boss = s.boss
        if s.spec.kind == "fetch":                 # (M24.3: she sits there crying)
            s.crying = Npc(config.ENEMIES[s.spec.boss].name.split(",")[0], "fragile_crying",
                           boss.x, boss.y, s.biome, quest=s.key)
            s.crying.say(("*sob*",))
        spec = config.BOSSES[s.spec.boss]
        scene = self.scene
        self.banner = Banner(f"{boss.espec.name.upper()} IS DEFEATED",
                             f"guardians {self.guardians}/{config.GUARDIANS}" if first
                             else f"the {s.biome}'s guardian already fell: a bonus kill")
        scene._sounds.append("chime")
        guild = scene.app.guild
        for p in scene.players:
            if p.ghost:
                continue
            p.stats.loot += spec.loot
            scene.effects.append(Effect("loot", boss.x, boss.y, target=p.hero, value=spec.loot))
            prog = p.progress
            prog.picks += 1
            rarities = config.RARITIES
            want = config.BOSS_CARD_RARITY
            if prog.decree is None or rarities.index(prog.decree) < rarities.index(want):
                prog.decree = want
            scene.rules.award(p, spec.achievement)
            if p.hero.bestiary is not None:
                p.hero.bestiary.update(spec.pages)
        guild.pages.update(spec.pages)
        guild.record_quest(s.key, [p.stats.hero for p in scene.players if not p.ghost],
                           s.fight_time)
        scene.app.save_guild()
        if scene.app.dev:
            print(f"[dev] {boss.espec.name}: beaten in {s.fight_time:.1f} s, "
                  f"max hp {boss.max_hp}, level {boss.level}")

    # --- Developer mode ---------------------------------------------------------------

    def dev_quest(self) -> QuestState | None:
        """Dev: the quest the dev keys act on -- config.QUEST_FOCUS (run.py
        --boss), else the first one not beaten yet."""
        s = self.states.get(config.QUEST_FOCUS) if config.QUEST_FOCUS else None
        if s is not None:
            return s
        return next((s for s in self.states.values() if s.stage != "cleared"), None)

    def dev_finish_hunt(self) -> bool:
        """Dev: the dev quest's hunt is done (its boss wakes)."""
        s = self.dev_quest()
        if s is None or s.stage != "hunt":
            return False
        s.taken = True
        s.found = s.spec.count
        s.lit = set(range(len(s.camp.spots)))
        done = {"light": tiles.BRAZIER_LIT, "collect": tiles.SAND,
                "survive": tiles.SEAL_BROKEN, "escort": tiles.BEACON,
                "rescue": tiles.SLUSH, "fetch": tiles.CONCRETE}.get(s.spec.kind)
        if s.spec.kind == "fetch":
            s.bear = self.scene.me.index           # (dev: the bear's yours)
        if done is not None and hasattr(self.world, "set_tile"):
            for x, y in s.camp.spots:
                self.world.set_tile(math.floor(x), math.floor(y), done)
        s.stage = "awake"
        sp = self.scene.spawner
        if sp is not None:
            for i in range(len(s.camp.spots)):
                for k in range(config.CARGO_GUARDS + 1):
                    sid = (QUEST_SID, s.qid, i, k)
                    if k and s.spec.kind not in ("collect", "fetch"):
                        break
                    sp.dead.add(sid)
                    e = sp.awake.pop(sid, None)
                    if e is not None:
                        e.hp = 0.0
                        e.last_hit_by = None
        self.banner = Banner("SOMETHING STIRS...", "(dev) hunt finished")
        return True

    def dev_spot(self, which: str) -> tuple[float, float] | None:
        """Dev: somewhere to teleport -- next to the dev quest's giver, or
        just outside its lair's gate."""
        s = self.dev_quest()
        if s is not None:
            if which == "giver":
                return s.npc.x, s.npc.y         # (free_spot finds room beside them)
            gx = sum(t[0] for t in s.lair.gate) / max(1, len(s.lair.gate))
            gy = sum(t[1] for t in s.lair.gate) / max(1, len(s.lair.gate))
            dx, dy = gx - s.lair.cx, gy - s.lair.cy
            d = math.hypot(dx, dy) or 1.0
            return gx + dx / d * 8.0, gy + dy / d * 8.0
        return None


def free_spot(world, x: float, y: float, half: float) -> tuple[float, float]:
    """The nearest spot to (x, y) where a body of half-size `half` px fits."""
    for r in range(0, 16):
        for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r), (r, r), (-r, -r), (r, -r), (-r, r)):
            if not hull_hits_solid(world, x + dx, y + dy, 0.0, half, half):
                return x + dx, y + dy
    return x, y
