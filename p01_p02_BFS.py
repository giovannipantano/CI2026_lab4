"""
Klotski - Lab 4, levels 1 and 2 only (p01, p02).

A minimal version that follows the lecture step by step:
  state        -> the board itself (tuple of rows)
  A(s), R(s,a) -> successors(): every legal one-cell slide of one piece
  G(s)         -> goal_test(): the target covers the exit cells
  C(P)         -> number of moves (each move costs 1)
  search       -> the generic search of slide 27, run as Breadth-First
"""

from collections import deque


PROBLEMS = {
    "p01": {
        "board": ["A 5 1",
                  "6 4 2",
                  "3 . ."],
        "target": "A",
        "exit_cols": [1],
    },
    "p02": {
        "board": [" A  A  4  7",
                  " A  A  6  8",
                  " 1  5  .  3",
                  "10  .  9  2"],
        "target": "A",
        "exit_cols": [1, 2],
    },
}

MOVES = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


def make_state(lines):
    """Turn the text board into a state: a tuple of tuples (hashable, so it
    can go in a set / dict key -> needed for graph search)."""
    return tuple(tuple(line.split()) for line in lines)


def goal_test(state, target, exit_cols):
    """The target piece must cover the exit cells: the bottom-most row(s)
    under the exit columns. The target's height decides how many rows."""
    rows = len(state)
    height = sum(1 for row in state if target in row)    # 1 for p01, 2 for p02
    for r in range(rows - height, rows):
        for c in exit_cols:
            if state[r][c] != target:
                return False
    return True


def successors(state):
    """Yield (action, new_state) for every legal move.
    A move = slide one whole piece by one cell into empty cells."""
    rows, cols = len(state), len(state[0])

    # Collect the cells of each piece: {"A": [(0,0),(0,1),...], "5": [(0,1)], ...}
    pieces = {}
    for r in range(rows):
        for c in range(cols):
            name = state[r][c]
            if name != ".":
                pieces.setdefault(name, []).append((r, c))

    for name, cells in pieces.items():
        for direction, (dr, dc) in MOVES.items():
            # Can the whole piece shift by (dr, dc)?
            legal = True
            for r, c in cells:
                nr, nc = r + dr, c + dc
                if not (0 <= nr < rows and 0 <= nc < cols):
                    legal = False          # would leave the board
                    break
                if state[nr][nc] not in (".", name):
                    legal = False          # cell taken by another piece
                    break
            if not legal:
                continue

            # R(s, a): build the new board
            grid = [list(row) for row in state]
            for r, c in cells:             # 1) lift the piece
                grid[r][c] = "."
            for r, c in cells:             # 2) put it down shifted
                grid[r + dr][c + dc] = name
            yield f"{name} {direction}", tuple(tuple(row) for row in grid)


def key(state, target):
    """In p01 and p02 every piece except the target is 1x1, so two boards
    that differ only by swapping two small blocks are the SAME puzzle position.
    The key hides their names ('x'), so the search sees them as one state
    ("good generators are not redundant", slide 18)."""
    return tuple(tuple(t if t in (".", target) else "x" for t in row) for row in state)


def bfs(start, target, exit_cols):
    """Frontier = FIFO queue -> shallowest node first -> fewest moves.
    'parent' doubles as the visited set (graph search, no duplicates)."""
    frontier = deque([start])
    parent = {key(start, target): None}    # key -> (previous_state, action)
    expanded = 0

    while frontier:
        state = frontier.popleft()                     # extract...
        if goal_test(state, target, exit_cols):        # ...then test (slide 28)
            return build_path(parent, state, target), expanded
        expanded += 1
        for action, new_state in successors(state):
            k = key(new_state, target)
            if k not in parent:                        # never seen -> new node
                parent[k] = (state, action)
                frontier.append(new_state)
    return None, expanded                              # space exhausted: unsolvable


def build_path(parent, state, target):
    """Walk back from the goal to the start through 'parent'."""
    path = []
    while parent[key(state, target)] is not None:
        previous, action = parent[key(state, target)]
        path.append((action, state))
        state = previous
    return path[::-1]


def show(state):
    width = max(len(t) for row in state for t in row)
    return "\n".join("   " + " ".join(t.rjust(width) for t in row) for row in state)


if __name__ == "__main__":
    for pid, prob in PROBLEMS.items():
        start = make_state(prob["board"])
        path, expanded = bfs(start, prob["target"], prob["exit_cols"])
        print("=" * 40)
        print(f"{pid}: solved in {len(path)} moves ({expanded} states expanded)")
        print("start:\n" + show(start))
        for i, (action, state) in enumerate(path, 1):
            print(f"\nmove {i}: {action}\n" + show(state))