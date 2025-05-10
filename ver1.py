#!/usr/bin/env python3
import sys, argparse, time, random

INF = 0x3f3f3f3f

class Edge:
    __slots__ = ("x", "y", "z", "c")
    def __init__(self, x, y, z, c):
        self.x, self.y, self.z, self.c = x, y, z, c

# ------------- helper ---------------------------------------------------------
def build_routes(edges, g, st, Q):
    """
    Greedy route builder identical to the original logic, but working
    on *its own* copy of edges and returning (routes,cost).
    """
    edges = edges[:]                         # copy we can mutate
    routes, total = [], 0

    while edges:
        p, q = st, Q
        route = []
        while edges:
            # choose edge whose nearer endpoint is closest to p
            idx = min(
                range(len(edges)),
                key=lambda i: min(g[p][edges[i].x], g[p][edges[i].y])
            )
            ed = edges[idx]
            if ed.c > q:                     # can't take, stop this vehicle
                break
            # orient so p → ed.x
            if g[p][ed.x] > g[p][ed.y]:
                ed.x, ed.y = ed.y, ed.x
            total += g[p][ed.x] + ed.z
            route.append((ed.x, ed.y, ed.z, ed.c))
            q -= ed.c
            p = ed.y
            edges.pop(idx)
        total += g[p][st]                    # return to depot
        if route:
            routes.append(route)
    return routes, total

# ------------- main -----------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="CARP solver")
    parser.add_argument('instance_file')
    parser.add_argument('-t', '--termination', type=float, default=1.0)
    parser.add_argument('-s', '--seed', type=int)
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # ---------------------------------------------------------------- read data
    with open(args.instance_file) as f:
        _      = f.readline().split()                # NAME :
        n       = int(f.readline().split()[2])       # VERTICES :
        st      = int(f.readline().split()[2])       # DEPOT :
        m1      = int(f.readline().split()[3])       # REQUIRED EDGES :
        m2      = int(f.readline().split()[3])       # NON‑REQUIRED :
        T       = int(f.readline().split()[2])       # VEHICLES :
        Q       = int(f.readline().split()[2])       # CAPACITY :
        B       = int(f.readline().split()[6])       # TOTAL COST :
        _       = f.readline()                       # NODES COST DEMAND

        m = m1 + m2
        g = [[INF]*(n+1) for _ in range(n+1)]
        for i in range(1, n+1):
            g[i][i] = 0

        original_edges = []
        for _ in range(m):
            x, y, z, c = map(int, f.readline().split())
            if c:                                     # only required edges
                original_edges.append(Edge(x, y, z, c))
            g[x][y] = g[y][x] = z
        _ = f.readline()                              # END

    # ------------------------------------------------------- Floyd–Warshall
    for k in range(1, n+1):
        for i in range(1, n+1):
            ik = g[i][k]
            if ik == INF: continue
            row_i, row_k = g[i], g[k]
            for j in range(1, n+1):
                if row_i[j] > ik + row_k[j]:
                    row_i[j] = ik + row_k[j]

    # ------------------------------------------------ initial greedy solution
    best_routes, best_val = build_routes(
        [Edge(e.x, e.y, e.z, e.c) for e in original_edges], g, st, Q
    )

    # ------------------------------------------------ timed improvement loop
    time_limit = args.termination
    start = time.time()
    DEADLINE = start + time_limit - 0.05              # 50 ms safety margin
    while time.time() < DEADLINE:
        # simple perturbation: random shuffle of edges then greedy
        random_edges = original_edges[:]
        random.shuffle(random_edges)
        routes, val = build_routes(
            [Edge(e.x, e.y, e.z, e.c) for e in random_edges],
            g, st, Q
        )
        if val < best_val:
            best_routes, best_val = routes, val

    # ------------------------------------------------------------ print answer
    print("s ", end="")
    for i, rt in enumerate(best_routes):
        print("0,", end="")
        for x, y, *_ in rt:
            print(f"({x},{y}),", end="")
        if i == len(best_routes)-1:
            print("0")
        else:
            print("0,", end="")
    print(f"q {best_val}")

if __name__ == '__main__':
    main()
