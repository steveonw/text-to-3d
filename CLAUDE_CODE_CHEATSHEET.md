# Claude Code Cheat Sheet

A handoff document for picking up the build of this skill in Claude Code.

**If you are Claude Code, reading this for the first time: start at "First session" below. Do not start coding yet.**

**If you are the human, reading this for the first time:** this is what Claude Code should do when you open the project. You can paste sections of this as prompts, or just point Claude Code at this file and say "read this and let's begin."

---

## TL;DR

The placement and verification halves of the skill are working. The authoring half — the part that lets Claude supply geometry per piece in context, rather than using baked-in geometry — is not built. Your job is to build it, in a specific order, without drifting toward a template-library approach.

Read `SKILL.md` and `references/philosophy.md` before writing any code. The philosophy is load-bearing and easy to violate accidentally.

---

## First session (orientation, no code changes yet)

The goal of session one is to get oriented and verify the existing machinery works, **not** to start building. Resist the urge to jump in.

### Step 1: Read the critical docs

In order:

1. `README.md` — project overview
2. `SKILL.md` — the teaching document and workflow
3. `references/philosophy.md` — the toddler-with-blocks principle
4. `CHECKLIST.md` — what's done and what's stubbed
5. This file (you're reading it)

Do not skim. These are short and load-bearing.

### Step 2: Confirm git is initialized

```bash
git status
```

If not a repo yet:

```bash
git init
git add .
git commit -m "initial skill snapshot from merge"
```

Every change from here gets committed. Tests passing → commit. Design decision made → commit. This is your undo button.

### Step 3: Verify the existing machinery works

Run the tests:

```bash
pytest tests/
```

Some tests may fail due to the reorganization (files moved into subfolders, imports may not resolve). If they fail, your **first real task** is fixing imports, not building new features. Fix them, commit, move on.

Then try the placement engine end-to-end:

```bash
python scripts/dropgrid_run.py --list
python scripts/dropgrid_run.py --example shrine --ascii-only
```

You should see an ASCII map of ~46 pieces. If you don't, something is broken in the core engine and needs fixing before any new work.

Then generate an HTML:

```bash
python scripts/dropgrid_run.py --example shrine --output /tmp/shrine.html
```

Open the file in a browser. Confirm it renders. (Walk mode may or may not be wired depending on which scaffold path the script uses — that's okay, we'll fix it.)

### Step 4: Report back

At this point, tell the human:

- What tests passed / failed
- Whether placement ran cleanly
- Whether the HTML rendered
- Any surprises

**Don't make changes yet.** Session one ends here. Fresh session starts on the first actual build task, with this report as context.

---

## The build order

These are the missing pieces, in the order they should be built. Each one is roughly one focused session in Claude Code. Do NOT try to do more than one per session.

### Task 1: Fix any test failures from reorganization

- **Goal:** all existing tests pass.
- **Scope:** import paths, moved files, nothing else.
- **Don't:** add new tests, refactor, "improve" anything you notice along the way. Just get green.
- **Done when:** `pytest tests/` passes cleanly. Commit.

### Task 2: Context exporter

- **Goal:** build `scripts/authoring/context_exporter.py` per the spec in `scripts/authoring/README.md`.
- **Scope:** a module that takes the solver's `SceneResult` and returns a per-piece context packet (neighbors, distances, edge/interior status, facing direction).
- **Tests:** at least one test file at `tests/test_context_exporter.py`. Cover: packet for an interior piece, packet for an edge piece, packet for a piece near a path.
- **Don't:** try to use this packet for anything yet. That's the next task. Just produce it and prove it's shaped right.
- **Done when:** module exists, tests pass, you can run it on the shrine example and get back readable per-piece context. Commit.

### Task 3: Geometry authoring protocol

This is the hardest design task. Before writing any code, **have a design conversation with the human.** Open questions (from `scripts/authoring/README.md`):

1. Coordinate frame — footprint-local with y-up floor origin, or piece-center origin?
2. Material vocabulary — full PBR or simpler?
3. Primitive hierarchy — flat list or grouped?
4. Validation — strict schema enforcement or lenient?
5. Fallback when Claude doesn't author a piece — baked geometry, placeholder cube, or hard error?
6. Batching — author all at once or piece-by-piece?

**Don't make these decisions alone.** Propose options, trade-offs, and a recommendation. Let the human choose. Then implement.

- **Goal:** `scripts/authoring/geometry_receiver.py` + a `scripts/authoring/schema.md` describing the packet format.
- **Tests:** validate malformed packets fail cleanly; valid packets round-trip correctly.
- **Done when:** module exists, schema is documented, tests pass. Commit.

### Task 4: Renderer rewiring

- **Goal:** modify `scripts/scaffold/scaffold_v4_walkmode.py` so it can consume LLM-authored geometry packets (from task 3) and produce HTML where each piece's geometry comes from the packet rather than from baked-in per-type geometry.
- **Preserve:** the walk mode, HUD, orbit controls. Don't lose working features.
- **Backwards compat:** if a piece has no authored geometry, fall back to baked (per task 3's design decision). Don't break existing behavior.
- **Tests:** render a scene with all-authored pieces; render a scene with partial authoring; render with no authoring (falls back).
- **Done when:** you can feed the scaffold a solver result + a dict of authored packets and get back an HTML file where every authored piece looks like what the packet said. Commit.

### Task 5: Full-loop worked example

- **Goal:** `references/worked_examples/full_loop_example.md` — a complete trace from a user prompt through decomposition, DSL, solver, per-piece authoring (with context!), verification, and final HTML.
- **Style:** match the existing worked examples (`gate_torches`, `topology_rect_demo`) in format, but covering the whole pipeline.
- **Content:** pick a small scene (~15-20 pieces). Show *actual* authored geometry packets with context-driven variation — e.g. two trees that look different because one is on the path edge.
- **Done when:** a fresh Claude session reading this example could replicate the workflow on a different scene. Commit.

### Task 6: Authoring guide reference

- **Goal:** `references/authoring_guide.md` — teach Claude the *craft* of context-aware geometry.
- **See:** the TODO stub at `references/authoring_guide.md.TODO` for the topic list.
- **Style:** prose, not code. Principles and patterns. Use the worked example from task 5 as a reference.
- **Done when:** document reads as a standalone craft guide, and a fresh Claude session reading it produces noticeably more varied, context-aware geometry than without it. Commit.

### Task 7: SKILL.md iteration

- **Goal:** tighten `SKILL.md` based on behavioral observation.
- **Method:** run 2-3 test prompts in fresh Claude sessions with the skill loaded. See where Claude falls back to template-library thinking. Note the specific failure modes. Rewrite the relevant sections of `SKILL.md` to preempt them.
- **Expect:** this is iterative. Probably 3-5 rounds before the skill consistently produces handcrafted output.
- **Done when:** across several test prompts, Claude reliably authors each piece fresh without reaching for reuse. Commit after each iteration.

---

## The rules

### Don't add a template library

No matter how tempting, no matter how much effort it would save, no matter how reasonable it sounds. The absence of a template library is the whole point of this skill. If you find yourself thinking "I'll just cache a few common objects," stop and re-read `references/philosophy.md`.

Specific telltales:

- A file named `templates.py`, `library.py`, `objects.json`, or similar
- A `__init__.py` that loads pre-defined geometries
- A function called `get_tree()` or `make_chair()` that returns a fixed structure
- A caching layer anywhere near the authoring code

If you notice yourself writing any of these, delete them and re-read the philosophy.

### One task per session

The build order above is deliberately linear. Each task builds on the previous one. Do not try to skip ahead. Do not try to do two tasks at once. Claude Code works best when scope is tight.

When a task finishes: tests pass, commit, end session, start a fresh session for the next one. The fresh context is a feature, not a bug — it prevents scope creep.

### Read before writing

Every session, before making changes to a file, read it. Not just the function you're editing — the whole file. The skill's design only stays coherent if changes respect what's already there.

### Ask the human for design decisions

Tasks 3, 7, and anything not fully specified above should trigger a design conversation, not unilateral decisions. The human has been thinking about this for longer than you have. They know things the code doesn't.

Specifically, always ask before:

- Changing the DSL syntax
- Modifying the solver's behavior
- Picking material/coordinate/schema conventions
- Deciding fallback behavior
- Adding any dependency

### Commit after every passing step

Not at the end of a session. Not "when it's done." Every time tests pass, commit. If you break something, you want a recent green to revert to.

---

## Useful commands

```bash
# Verify engine works
python scripts/dropgrid_run.py --example shrine --ascii-only

# Render a scene
python scripts/dropgrid_run.py --example shrine --output /tmp/out.html

# List available examples
python scripts/dropgrid_run.py --list

# Run tests
pytest tests/

# Run a specific test file
pytest tests/test_layout_dsl_v1_2.py -v

# Check for TODO files (things still to build)
find . -name "*.TODO" -o -name "*.TODO.*"

# See what changed since last commit
git status
git diff
```

---

## When you're stuck

If a task is harder than the estimate suggests, stop and talk to the human. Don't push through. Often "harder than expected" means the design assumption was wrong, and continuing makes the code worse.

If a test is failing mysteriously, read the test carefully and read the code carefully. Don't modify the test to make it pass. Make the code meet the test's expectation, or explain to the human why the test is wrong and propose an alternative.

If the philosophy and the pragmatic choice seem to conflict, surface it. Sometimes the philosophy wins (the skill exists for a reason). Sometimes the pragmatic choice wins (ship something usable now, purify later). Don't decide alone.

---

## Signs you're on the right track

- Each session produces one commit with one clear improvement.
- Tests stay green.
- The skill can do more after your session than before.
- The code and the philosophy still agree.
- You asked the human at least one real design question.

## Signs you're drifting

- You're three tasks ahead of where you should be.
- Tests have been failing for more than one session.
- You added a file called something like `common.py` or `utils.py` with a bunch of stuff in it.
- You're about to define a geometry that will be used more than once.
- You haven't read the philosophy doc this session.

If any of these show up, pause and re-ground.

---

## Final note

The skill is 70% built. The 30% that's missing is the part that makes it interesting. Don't treat the build like a chore — treat it like authoring a tool that didn't exist before. It's small enough that care shows.

Good luck.
