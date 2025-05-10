#!/usr/bin/env python3
# ------------------------------------------------------------
#  CARP solver – greedy + simulated annealing + 8‑way parallel
# ------------------------------------------------------------
import sys, argparse, time, random, math, os, queue
from multiprocessing import get_context, Queue
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple
INF = 0x3f3f3f3f

# ---------------------------------------------------------------- Edge / helpers
class Edge:
    __slots__ = ("x", "y", "z", "c")
    def __init__(self, x: int, y: int, z: int, c: int):
        self.x, self.y, self.z, self.c = x, y, z, c

def build_routes(edges: List[Edge], g, st: int, Q: int):
    """Greedy builder (原版).  Returns (routes, total_cost)."""
    edges = edges[:]           # copy
    routes, total = [], 0
    while edges:
        p, q = st, Q
        route = []
        while edges:
            idx = min(range(len(edges)),
                      key=lambda i: min(g[p][edges[i].x], g[p][edges[i].y]))
            ed = edges[idx]
            if ed.c > q:
                break
            if g[p][ed.x] > g[p][ed.y]:     # orient
                ed.x, ed.y = ed.y, ed.x
            total += g[p][ed.x] + ed.z
            route.append((ed.x, ed.y))
            q -= ed.c
            p = ed.y
            edges.pop(idx)
        total += g[p][st]                   # back to depot
        if route:
            routes.append(route)
    return routes, total

# ---------------------------------------------------------------- SA worker
def sa_worker(pid: int,
              edges_data: List[Tuple[int,int,int,int]],
              g, st: int, Q: int,
              time_budget: float,
              seed: int,
              out_q: Queue):
    rng = random.Random(seed)
    # rebuild Edge objects locally (faster than pickling large objects many times)
    original_edges = [Edge(*t) for t in edges_data]

    # initial state: random shuffle
    curr_order = original_edges[:]
    rng.shuffle(curr_order)
    curr_routes, curr_val = build_routes([Edge(e.x,e.y,e.z,e.c) for e in curr_order],
                                         g, st, Q)
    best_routes, best_val = curr_routes, curr_val

    T0 = 600.0                             # initial temperature
    Tend = 1e-2
    steps = 0
    deadline = time.time() + time_budget
    while time.time() < deadline:
        steps += 1
        # linear cooling
        frac = (deadline - time.time()) / time_budget
        T = T0 * max(frac, 0)**2 + Tend
        # propose: swap two positions
        i, j = rng.sample(range(len(curr_order)), 2)
        curr_order[i], curr_order[j] = curr_order[j], curr_order[i]
        # evaluate
        routes, val = build_routes([Edge(e.x,e.y,e.z,e.c) for e in curr_order],
                                   g, st, Q)
        delta = val - curr_val
        if delta < 0 or rng.random() < math.exp(-delta / T):
            # accept
            curr_routes, curr_val = routes, val
            if val < best_val:
                best_routes, best_val = routes, val
                out_q.put((best_val, best_routes))
        else:
            # revert swap
            curr_order[i], curr_order[j] = curr_order[j], curr_order[i]
    # ensure at least one result sent
    out_q.put((best_val, best_routes))

# ---------------------------------------------------------------- Floyd‑Warshall
def floyd(n: int, g):
    for k in range(1, n+1):
        row_k = g[k]
        for i in range(1, n+1):
            ik = g[i][k]
            if ik == INF: continue
            row_i = g[i]
            for j in range(1, n+1):
                alt = ik + row_k[j]
                if alt < row_i[j]:
                    row_i[j] = alt

# ---------------------------------------------------------------- read instance
def read_instance(path: str):
    with open(path) as f:
        _  = f.readline()
        n  = int(f.readline().split()[2])
        st = int(f.readline().split()[2])
        m1 = int(f.readline().split()[3])
        m2 = int(f.readline().split()[3])
        _T = int(f.readline().split()[2])
        Q  = int(f.readline().split()[2])
        _  = f.readline(); _ = f.readline()
        m = m1 + m2

        g = [[INF]*(n+1) for _ in range(n+1)]
        for i in range(1, n+1): g[i][i] = 0
        edges = []
        for _ in range(m):
            x,y,z,c = map(int, f.readline().split())
            if c: edges.append(Edge(x,y,z,c))
            if z < g[x][y]: g[x][y] = g[y][x] = z
        _ = f.readline()
    floyd(n, g)
    return n, st, Q, g, edges

# ---------------------------------------------------------------- print answer
def output(routes, val):
    print("s ", end="")
    for i, rt in enumerate(routes):
        print("0,", end="")
        for u,v in rt:
            print(f"({u},{v}),", end="")
        print("0" if i==len(routes)-1 else "0,", end="")
    print(f"\nq {val}")

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_file")
    ap.add_argument("-t","--termination", type=float, default=30.0)
    ap.add_argument("-s","--seed", type=int, default=1)
    args = ap.parse_args()

    random.seed(args.seed)
    n, st, Q, g, edges = read_instance(args.instance_file)

    # Pack edges into tuples for easy pickle
    edges_data = [(e.x,e.y,e.z,e.c) for e in edges]

    workers = min(8, os.cpu_count() or 1)
    if args.termination < 1.5:        # tiny limit → single process safer
        workers = 1
    per_worker = args.termination - 0.3
    if per_worker <= 0.1:
        workers, per_worker = 1, args.termination - 0.05

    ctx = get_context("spawn")
    q: Queue = ctx.Manager().Queue()

    start = time.time()
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        for i in range(workers):
            seed_i = args.seed + 10007 * i
            pool.submit(sa_worker, i, edges_data, g, st, Q,
                        per_worker, seed_i, q)

        best_val, best_routes = INF, []
        deadline = start + args.termination - 0.05
        while time.time() < deadline:
            try:
                val, routes = q.get(timeout=0.02)
                if val < best_val:
                    best_val, best_routes = val, routes
            except queue.Empty:
                pass

    # fallback if nothing received
    if best_val == INF:
        best_routes, best_val = build_routes(edges, g, st, Q)

    output(best_routes, best_val)

if __name__ == "__main__":
    main()
