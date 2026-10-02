"""
systems/quests.py -- the run's quests (M17, design/BOSSES.md).

Each ring biome's quest for this run (one of its pool in config.QUESTS,
picked by the seed: world/landmarks.pick_quests) whose camp and lair could
be placed on this island gets a QuestState, going through these stages:

  "offered"  the giver waits at their camp (pinned on the maps from the
             start); talking to them (E / gamepad A within TALK_RADIUS)
             starts the quest;
  "hunt"     the quest's targets are out at the camp's spots, scattered
             over the biome -- a few more of them than the quest needs --
             and pinned on the maps once you're near one (they wake,
             sleep and stay dead like any enemy, systems/spawner.place);
             every one that dies counts, whoever killed it;
  "awake"    all found: the boss waits in its lair (now pinned too);
  "fight"    a player went LAIR_SEAL_DEPTH tiles into the arena: the gate
             fills with thorns (each tile as soon as nobody stands in it),
             the boss rises with its name across the screen, and the
             arena's chunks stay loaded wherever the players are in it;
  "cleared"  the boss fell: the gate opens, and every player gets the
             reward (loot, a rare+ card offer; the achievement and the
             bestiary pages go to the Guild). One more guardian down for
             the main quest, "Gain Adventurer's Glory".

What the giver says depends on the stage (QuestSpec.lines); their words
hang over their head a line at a time. The main quest counts guardians
(cleared quests) toward config.GUARDIANS.

All of it runs inside the simulation step, from the players' inputs and
the game state only (deterministic).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .. import config
from ..entities.effects import Effect
from ..world import biomes, tiles
from ..world.rng import hash_coords
from .collision import hull_hits_solid

# Spawn ids of quest enemies: (QUEST_SID, biome id, i, 0) -- four ints, so
# they never clash with a chunk roster's (cx, cy, k).
QUEST_SID = 0x51E57


@dataclass
class Npc:
    """Someone to talk to at a landmark."""

    name: str
    sprite: str
    x: float
    y: float
    biome: str
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
    spec: object                       # specs.QuestSpec
    camp: object                       # world/landmarks.Landmark
    lair: object
    npc: Npc
    stage: str = "offered"
    found: int = 0                     # hunt: targets dead so far
    boss: object = None
    pending: list = field(default_factory=list)   # gate tiles still to seal
    fight_time: float = 0.0
    damage_taken: float = 0.0          # by the players during the fight (dev report)

    @property
    def biome(self) -> str:
        return self.spec.biome


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
        self.states: dict[str, QuestState] = {}
        if layout is not None:
            from ..world.landmarks import pick_quests
            for spec in (config.QUESTS[k] for k in pick_quests(layout.seed).values()):
                camp, lair = layout.landmark(spec.camp), layout.landmark(spec.lair)
                if camp is None or lair is None or camp.npc is None:
                    continue
                npc = Npc(spec.giver, spec.giver_sprite, *camp.npc, spec.biome)
                self.states[spec.biome] = QuestState(spec, camp, lair, npc)
        self.banner: Banner | None = None

    # --- Queries --------------------------------------------------------------------

    @property
    def npcs(self) -> list[Npc]:
        return [s.npc for s in self.states.values()]

    @property
    def guardians(self) -> int:
        return sum(1 for s in self.states.values() if s.stage == "cleared")

    @property
    def fight(self) -> QuestState | None:
        return next((s for s in self.states.values() if s.stage == "fight"), None)

    def npc_near(self, hero) -> Npc | None:
        best, best_d = None, config.TALK_RADIUS
        for npc in self.npcs:
            d = math.hypot(npc.x - hero.x, npc.y - hero.y)
            if d <= best_d:
                best, best_d = npc, d
        return best

    def stream_views(self) -> list[tuple[float, float, float, float]]:
        """Extra areas to keep loaded: the arena of a fight in progress (its
        boss roams all of it, often far from the players' screens)."""
        s = self.fight
        if s is None:
            return []
        a, b = s.lair.radii
        return [(s.lair.cx, s.lair.cy, a + config.LAIR_WALL, b + config.LAIR_WALL)]

    def log(self) -> list[tuple[str, str, bool]]:
        """The quest log: (label, text, done) lines, main quest first."""
        out = [("GLORY", f"guardians {self.guardians}/{config.GUARDIANS}", False)]
        for s in self.states.values():
            spec = s.spec
            boss = config.BOSSES[spec.boss].name
            text = {
                "offered": f"talk to the {spec.giver}",
                "hunt": spec.goal.format(n=s.found, count=spec.count),
                "awake": f"go to {s.lair.name.title()}",
                "fight": f"defeat {boss}",
                "cleared": f"{boss} beaten",
            }[s.stage]
            out.append((s.biome.upper(), text, s.stage == "cleared"))
        return out

    def pins(self, near: tuple[float, float] | None = None) -> list[tuple[float, float, str, str]]:
        """Map pins: (x, y, kind, label); kind "quest" | "lair" | "target" |
        "done". A hunt's targets (still alive) are pinned only within
        QUEST_TARGET_PIN_RADIUS tiles of `near` (the viewing player; None:
        all of them): you roam the biome until you're close, then the pin
        leads you in."""
        out = []
        sp = self.scene.spawner
        for s in self.states.values():
            giver_done = s.stage == "cleared"
            out.append((s.npc.x, s.npc.y, "done" if giver_done else "quest", s.spec.giver.upper()))
            if s.stage == "hunt":
                bid = biomes.BY_NAME[s.biome].id
                label = config.ENEMIES[s.spec.target].name.split()[-1].upper()
                for i, (x, y) in enumerate(s.camp.spots):
                    if near is not None and math.hypot(x - near[0], y - near[1]) \
                            > config.QUEST_TARGET_PIN_RADIUS:
                        continue
                    if sp is None or (QUEST_SID, bid, i, 0) not in sp.dead:
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
            if s.stage == "awake":
                self._maybe_start_fight(s, players)
            elif s.stage == "fight":
                s.fight_time += dt
                self._seal(s)
        if self.banner is not None:
            self.banner.t += dt
            if self.banner.t >= self.banner.duration:
                self.banner = None

    def talk(self, npc: Npc, p) -> None:
        s = self.states[npc.biome]
        spec = s.spec
        if s.stage == "offered":
            npc.say(spec.say("offer"))
            self._start_hunt(s)
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

    def _start_hunt(self, s: QuestState) -> None:
        s.stage = "hunt"
        sp = self.scene.spawner
        bid = biomes.BY_NAME[s.biome].id
        if sp is not None:
            for i, (x, y) in enumerate(s.camp.spots):
                sp.place((QUEST_SID, bid, i, 0), s.spec.target, x, y)

    def is_target(self, s: QuestState, enemy) -> bool:
        sid = getattr(enemy, "spawn_id", None)
        return (isinstance(sid, tuple) and len(sid) == 4 and sid[0] == QUEST_SID
                and sid[1] == biomes.BY_NAME[s.biome].id)

    def on_death(self, enemy, killer) -> None:
        """An enemy died (`killer`: the player who killed it, or None)."""
        for s in self.states.values():
            if s.stage == "hunt" and self.is_target(s, enemy):
                s.found += 1
                hero = killer.hero if killer is not None else enemy
                if s.found >= s.spec.count:
                    s.stage = "awake"
                    self.banner = Banner("SOMETHING STIRS...",
                                         f"{s.lair.name.title()} is marked on your map")
                    self.scene._sounds.append("chime")
                else:
                    self.scene.effects.append(Effect(
                        "toast", hero.x, hero.y - 1,
                        label=s.spec.goal.format(n=s.found, count=s.spec.count).upper()))
                    self.scene._sounds.append("chime")
            elif s.stage == "fight" and enemy is s.boss:
                self._win(s, killer)

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
        rng = random.Random(hash_coords(getattr(self.world, "seed", 0) or 0, 0xB055,
                                        biomes.BY_NAME[s.biome].id))
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
                self.world.set_tile(tx, ty, tiles.MUD)

    def _win(self, s: QuestState, killer) -> None:
        s.stage = "cleared"
        self._open_gate(s)
        boss = s.boss
        spec = config.BOSSES[s.spec.boss]
        scene = self.scene
        self.banner = Banner(f"{boss.espec.name.upper()} IS DEFEATED",
                             f"guardians {self.guardians}/{config.GUARDIANS}")
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
        scene.app.save_guild()
        if scene.app.dev:
            print(f"[dev] {boss.espec.name}: beaten in {s.fight_time:.1f} s, "
                  f"max hp {boss.max_hp}, level {boss.level}")

    # --- Developer mode ---------------------------------------------------------------

    def dev_finish_hunt(self) -> bool:
        """Dev: the first quest still hunting (or not started) is done."""
        for s in self.states.values():
            if s.stage in ("offered", "hunt"):
                if s.stage == "offered":
                    self._start_hunt(s)
                s.found = s.spec.count
                s.stage = "awake"
                sp = self.scene.spawner
                if sp is not None:
                    bid = biomes.BY_NAME[s.biome].id
                    for i in range(len(s.camp.spots)):
                        sid = (QUEST_SID, bid, i, 0)
                        sp.dead.add(sid)
                        e = sp.awake.pop(sid, None)
                        if e is not None:
                            e.hp = 0.0
                            e.last_hit_by = None
                self.banner = Banner("SOMETHING STIRS...", "(dev) hunt finished")
                return True
        return False

    def dev_spot(self, which: str) -> tuple[float, float] | None:
        """Dev: somewhere to teleport -- next to the first quest's giver, or
        just outside its lair's gate."""
        for s in self.states.values():
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
