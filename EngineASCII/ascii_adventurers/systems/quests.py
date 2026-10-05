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
             mosquitoes swarm whoever is lighting it);
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
    lit: set = field(default_factory=set)       # light quests: spot indices lit
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
        return [s.npc for s in self.states.values()]

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
                light = s.spec.kind == "light"
                label = "BRAZIER" if light else config.ENEMIES[s.spec.target].name.split()[-1].upper()
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
            if s.stage == "hunt" and s.spec.kind == "light":
                self._tend_braziers(s, players, dt)
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
        """A hunt's targets go out at the camp's spots when the run starts."""
        sp = self.scene.spawner
        if sp is not None and s.spec.kind == "hunt":
            for i, (x, y) in enumerate(s.camp.spots):
                sp.place((QUEST_SID, s.qid, i, 0), s.spec.target, x, y)

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
        if s.spec.kind == "light" and hasattr(self.world, "set_tile"):
            for x, y in s.camp.spots:
                self.world.set_tile(math.floor(x), math.floor(y), tiles.BRAZIER_LIT)
        s.stage = "awake"
        sp = self.scene.spawner
        if sp is not None:
            for i in range(len(s.camp.spots)):
                sid = (QUEST_SID, s.qid, i, 0)
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
