"""
Generalized Klotski solver - Lab 4

The puzzle is cast as "searching for a path" in the state space:
  - state      : where every piece is on the board
  - actions    : slide one piece by one cell (up/down/left/right) into empty cells
  - result     : the board after that slide
  - goal test  : the target piece covers the exit cells on the bottom edge
  - path cost  : number of moves (every move costs 1)

All strategies share the same generic search loop; they differ only
in the priority function used for the frontier.
"""

import heapq
import itertools
import sys
import time
from collections import namedtuple

DIRECTIONS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}

Piece = namedtuple("Piece", "name h w")

def parse_problems(path):
    """Read klotski_problems.txt and return {id: problem dict}."""
    problems, cur, board, in_board = {}, None, [], False
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if line == "=========":
                if in_board:  # closing line: board finished
                    cur["grid"] = board
                    problems[cur["id"]] = cur
                    board = []
                in_board = not in_board
                continue
            if in_board:
                board.append(line.split())
            elif not line or line.startswith("#"):
                continue
            else:
                key, *vals = line.split()
                if key == "problem":
                    cur = {"id": vals[0]}
                elif key == "size":
                    cur["rows"], cur["cols"] = int(vals[0]), int(vals[1])
                elif key == "exit":  # "exit bottom 1 2"
                    cur["exit_cols"] = [int(v) for v in vals[1:]]
                elif key == "target":
                    cur["target"] = vals[0]
    return problems


class Klotski:
    """Static description of one instance: board size, pieces, exit."""

    def __init__(self, prob):
        self.id = prob["id"]
        self.R, self.C = prob["rows"], prob["cols"]
        grid = prob["grid"]
        assert len(grid) == self.R and all(len(r) == self.C for r in grid), "bad board size"

        # Collect the cells of each named piece
        cells = {}
        for r in range(self.R):
            for c in range(self.C):
                t = grid[r][c]
                if t != ".":
                    cells.setdefault(t, []).append((r, c))

        # Every piece must be a filled rectangle
        pieces, start = [], []
        for name, cs in cells.items():
            r0, c0 = min(r for r, _ in cs), min(c for _, c in cs)
            h = max(r for r, _ in cs) - r0 + 1
            w = max(c for _, c in cs) - c0 + 1
            assert len(cs) == h * w, f"piece {name} is not a rectangle"
            pieces.append(Piece(name, h, w))
            start.append((r0, c0))

        # Put the target first, then the other pieces grouped by shape.
        # Pieces with the same shape are interchangeable: two boards that differ
        # only by swapping two identical 1x1 blocks are the SAME state.
        order = sorted(range(len(pieces)),
                       key=lambda i: (pieces[i].name != prob["target"], pieces[i].h, pieces[i].w))
        self.pieces = [pieces[i] for i in order]
        self.start_pos = [start[i] for i in order]
        tgt = self.pieces[0]
        assert tgt.name == prob["target"]

        # Groups of interchangeable pieces (target is always alone in group 0)
        self.groups = [[0]]
        for i in range(1, len(self.pieces)):
            p, q = self.pieces[i], self.pieces[i - 1]
            if i > 1 and (p.h, p.w) == (q.h, q.w):
                self.groups[-1].append(i)
            else:
                self.groups.append([i])

        # Goal position of the target: bottom row, under the exit columns
        exit_cols = prob["exit_cols"]
        assert len(exit_cols) == tgt.w and exit_cols == list(range(exit_cols[0], exit_cols[0] + tgt.w)), \
            "exit width must match the target width"
        self.goal_pos = (self.R - tgt.h, exit_cols[0])
        self.goal_cells = {(self.goal_pos[0] + dr, self.goal_pos[1] + dc)
                           for dr in range(tgt.h) for dc in range(tgt.w)}

        # Sanity check from the slides: N*M = sum(r*c*n_rc) + e, with e >= 2
        self.empty = self.R * self.C - sum(p.h * p.w for p in self.pieces)
        self.start = self.canonical(self.start_pos)

    def canonical(self, positions):
        """Sort positions inside each group of identical pieces -> one key per state."""
        out = []
        for g in self.groups:
            out.extend(sorted(positions[i] for i in g))
        return tuple(out)

    def cells_of(self, i, pos):
        (r, c), p = pos, self.pieces[i]
        return [(r + dr, c + dc) for dr in range(p.h) for dc in range(p.w)]

    def occupancy(self, state):
        occ = [[-1] * self.C for _ in range(self.R)]
        for i, pos in enumerate(state):
            for r, c in self.cells_of(i, pos):
                occ[r][c] = i
        return occ

    def goal_test(self, state):
        return state[0] == self.goal_pos

    def successors(self, state):
        """Yield (action, new_state). action = (piece_index, direction, old_pos)."""
        occ = self.occupancy(state)
        for i, (r, c) in enumerate(state):
            for d, (dr, dc) in DIRECTIONS.items():
                nr, nc = r + dr, c + dc
                ok = True
                for (x, y) in self.cells_of(i, (nr, nc)):
                    if not (0 <= x < self.R and 0 <= y < self.C) or occ[x][y] not in (-1, i):
                        ok = False
                        break
                if ok:
                    new = list(state)
                    new[i] = (nr, nc)
                    yield (i, d, (r, c)), self.canonical(new)

    def h(self, state):
        """
        Relaxed problem: pretend the target could slide through other pieces.
          * it still needs |dr| + |dc| moves  (Manhattan distance)
          * every OTHER piece sitting on the goal cells must move at least once
        Each move moves only one piece by one cell, so h never overestimates
        (admissible) and changes by at most 1 per move (consistent).
        """
        (r, c), (gr, gc) = state[0], self.goal_pos
        dist = abs(r - gr) + abs(c - gc)
        if dist == 0:
            return 0
        occ = self.occupancy(state)
        blockers = {occ[x][y] for (x, y) in self.goal_cells} - {-1, 0}
        return dist + len(blockers)

    def render(self, positions):
        """Draw a board from a list of positions in self.pieces order."""
        g = [["."] * self.C for _ in range(self.R)]
        for i, pos in enumerate(positions):
            for r, c in self.cells_of(i, pos):
                g[r][c] = self.pieces[i].name
        width = max(len(p.name) for p in self.pieces)
        return "\n".join(" ".join(t.rjust(width) for t in row) for row in g)


# --------------------------------------------------------------------------- #
#  2. Generic search: one loop, different priority functions                  #
# --------------------------------------------------------------------------- #
def search(problem, priority, max_expansions=5_000_000):
    """
    Graph search: remembers visited states (slide 24, avoids exponential blow-up).
    priority(g, state) -> number; the frontier pops the smallest value first.
    Returns (list_of_actions or None, number_of_expanded_nodes).
    """
    tie = itertools.count()          # FIFO tie-breaking among equal priorities
    start = problem.start
    cost = {start: 0}                # best known g(n) for every generated state
    parent = {start: None}           # to rebuild the path at the end
    frontier = [(priority(0, start), next(tie), start)]
    closed = set()
    expanded = 0

    while frontier:
        _, _, state = heapq.heappop(frontier)
        if state in closed:          # stale entry (a cheaper copy was already expanded)
            continue
        if problem.goal_test(state):  # goal tested when the node is extracted (slide 28)
            return rebuild(parent, state), expanded
        closed.add(state)
        expanded += 1
        if expanded > max_expansions:
            break
        g = cost[state]
        for action, new_state in problem.successors(state):
            new_g = g + 1            # every move costs 1
            if new_state in closed:
                continue
            if new_state not in cost or new_g < cost[new_state]:
                cost[new_state] = new_g          # new node, or a cheaper path to it
                parent[new_state] = (state, action)
                heapq.heappush(frontier, (priority(new_g, new_state), next(tie), new_state))
    return None, expanded


def rebuild(parent, state):
    actions = []
    while parent[state] is not None:
        state, action = parent[state]
        actions.append(action)
    return actions[::-1]


# The strategies of the lecture, expressed only as priority functions
def strategies(p):
    return {
        "Breadth-first": lambda g, s: g,             # = uniform cost (unit costs)
        "Depth-first":   lambda g, s: -g,            # deepest node first
        "Greedy best-1st": lambda g, s: p.h(s),      # only the estimate
        "A*":            lambda g, s: g + p.h(s),    # f(n) = g(n) + h(n)
    }


# --------------------------------------------------------------------------- #
#  3. Replaying a solution with the real piece names                          #
# --------------------------------------------------------------------------- #
def replay(problem, actions):
    """Canonical states forget piece names; replay the moves on a named board."""
    pos = list(problem.start_pos)
    boards, steps = [problem.render(pos)], []
    for i, d, old in actions:
        # find which named piece of that shape sits at 'old'
        group = next(g for g in problem.groups if i in g)
        j = next(k for k in group if pos[k] == old)
        dr, dc = DIRECTIONS[d]
        pos[j] = (old[0] + dr, old[1] + dc)
        steps.append(f"{problem.pieces[j].name} {d}")
        boards.append(problem.render(pos))
    return steps, boards


def main(path="klotski_problems.txt", show_boards=False):
    problems = parse_problems(path)
    for pid, prob in problems.items():
        p = Klotski(prob)
        print("=" * 64)
        print(f"{pid}: {p.R}x{p.C} board, {len(p.pieces)} pieces, {p.empty} empty cells, "
              f"target {p.pieces[0].name} -> top-left at {p.goal_pos}")
        print(p.render(p.start_pos))
        best = None
        for name, prio in strategies(p).items():
            t0 = time.perf_counter()
            sol, expanded = search(p, prio)
            dt = time.perf_counter() - t0
            length = len(sol) if sol is not None else "no solution"
            print(f"  {name:16s} moves={length!s:>5}  expanded={expanded:>8}  time={dt:6.2f}s")
            if name == "A*":
                best = sol
        if best is None:
            print("  -> unsolvable")
            continue
        steps, boards = replay(p, best)
        print(f"  Optimal solution ({len(steps)} moves): " + ", ".join(steps))
        if show_boards:
            for k, b in enumerate(boards):
                print(f"\n  step {k}:\n" + b)


if __name__ == "__main__":
    file = sys.argv[1] if len(sys.argv) > 1 else "klotski_problems.txt"
    main(file, show_boards="--boards" in sys.argv)