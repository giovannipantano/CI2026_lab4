# Lab 4 – Generalized Klotski solved by search

## 🎥 Video presentation

**[Watch the video](https://drive.google.com/file/d/1ru3EyYcV-N3S6JI8bysWKsekhY_18R-j/view?usp=sharing)** (about 10 minutes)

The video explains the problem, the code and the results.

## The problem

Generalized Klotski is a sliding-block puzzle on an N×M board with rectangular pieces and at least two empty cells.
One move slides one piece by one cell. The goal is to bring the target piece onto the exit at the bottom edge.
The six benchmark puzzles are in [`klotski_problems.txt`](klotski_problems.txt), from a 3×3 warm-up (p01) to the classic Klotski (p04).

## Approach

The puzzle is solved as a **search for a path**, following the lecture *C3 – Searching for a Path*.

| Lecture | In this solution |
|---|---|
| State *s* | the board, as a tuple of rows (`.` = empty cell) |
| Actions A(s) / Result R(s, a) | slide one piece by one cell into empty cells |
| Goal test G(s) | the target covers the exit cells |
| Path cost C(P) | number of moves (each move costs 1) |

- **Graph search**: every board already reached is remembered, so no board is expanded twice.
- **Identical pieces are interchangeable**: before checking "seen before?", each piece name is replaced by its shape (`1x1`, `2x1`, `1x2`). On p02 this cuts the search from 1,033,088 boards to 256.
- **One generic search, four strategies**: the same loop with a different priority for the frontier.

| Strategy | Priority |
|---|---|
| BFS (breadth-first) | g (moves so far) |
| DFS (depth-first) | −g |
| Greedy best-first | h |
| A* | g + h |

The heuristic **h** relaxes the rules: the target's Manhattan distance to the exit, plus one move for each piece sitting on the exit cells.
It never overestimates (admissible) and changes by at most 1 per move (consistent), so A* returns optimal solutions.

## Results

Solution length in moves (boards expanded in brackets):

| Puzzle | BFS | A* | Greedy | DFS |
|---|---|---|---|---|
| p01 | 8 (107) | 8 (62) | 8 (9) | 51 (58) |
| p02 | 18 (256) | 18 (195) | 18 (55) | 62 (75) |
| p03 | 45 (2,125) | 45 (2,051) | 49 (1,124) | 615 (1,421) |
| p04 | 116 (24,029) | 116 (23,742) | 196 (8,029) | 1,101 (2,367) |
| p05 | 179 (40,114) | 179 (37,304) | 308 (27,739) | 6,305 (23,979) |
| p06 | no solution (833) | no solution (833) | no solution (833) | no solution (833) |

- BFS and A* are optimal and agree on every puzzle; 116 is the known optimum of classic Klotski with one-cell moves.
- A* saves little over BFS: most moves clear the way for the target, which the heuristic cannot see.
- Greedy and DFS expand fewer boards on the larger puzzles but return much longer solutions.
- p06 is unsolvable: all 833 reachable boards were explored and none is a goal.