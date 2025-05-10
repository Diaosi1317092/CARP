#!/usr/bin/env python3
# ------------------------------------------------------------
#  CARP solver – greedy multi-start + 8-way parallel +
#                 local-search intensification per shuffle
# ------------------------------------------------------------
import sys, argparse, time, random, os, queue
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
    """Greedy builder (original). Returns (routes, total_cost)."""
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

# ----------------------------------------------------------------
#  intensify: random 2‐edge swaps + 1‐edge orientation tweaks
# ----------------------------------------------------------------
def intensify(routes: List[List[Tuple[int,int]]],
              g, st: int, Q: int,
              demand_map, cost_map,
              attempts: int=150000) -> Tuple[List[List[Tuple[int,int]]], int]:
    curr = [list(rt) for rt in routes]
    best = curr
    def route_cost(rt):
        tot, cur = 0, st
        for u,v in rt:
            tot += g[cur][u] + cost_map[(u,v)]
            cur = v
        tot += g[cur][st]
        return tot
    def route_demand(rt):
        return sum(demand_map[(u,v)] for u,v in rt)

    curr_val = sum(route_cost(rt) for rt in curr)
    best_val = curr_val

    # precompute “unchanged” cost contributions by route index
    def total_except(r_indices):
        return sum(route_cost(curr[i]) for i in range(len(curr)) if i not in r_indices)

    # flatten positions
    positions = [(ri, pi)
                 for ri, rt in enumerate(curr)
                 for pi in range(len(rt))]

    rng = random.Random()

    for _ in range(attempts):
        if rng.random() < 0.5:
            # --- two‐edge swap as before ---
            r1,p1 = rng.choice(positions)
            r2,p2 = rng.choice(positions)
            if (r1,p1)==(r2,p2): continue

            base = [list(rt) for rt in curr]
            e1 = base[r2][p2]
            e2 = base[r1][p1]
            base[r1][p1], base[r2][p2] = e1, e2

            const_cost = total_except({r1, r2})

            best_local, best_local_val = None, INF
            for flip1 in (False, True):
                for flip2 in (False, True):
                    new = [list(rt) for rt in base]
                    u1,v1 = (e1 if not flip1 else (e1[1], e1[0]))
                    u2,v2 = (e2 if not flip2 else (e2[1], e2[0]))
                    new[r1][p1] = (u1,v1)
                    new[r2][p2] = (u2,v2)
                    # capacity check
                    if r1!=r2 and (route_demand(new[r1])>Q or route_demand(new[r2])>Q):
                        continue
                    val = const_cost + route_cost(new[r1]) + route_cost(new[r2])
                    if val < best_local_val:
                        best_local_val = val
                        best_local = new
            if best_local is None:
                continue
            new, nv = best_local, best_local_val

        else:
            # --- single-edge orientation tweak ---
            r, p = rng.choice(positions)
            e = curr[r][p]
            # try both orientations
            best_local, best_local_val = None, INF
            const_cost = total_except({r})
            for flip in (False, True):
                new = [list(rt) for rt in curr]
                u,v = (e if not flip else (e[1], e[0]))
                new[r][p] = (u,v)
                if route_demand(new[r]) > Q:
                    continue
                val = const_cost + route_cost(new[r])
                if val < best_local_val:
                    best_local_val = val
                    best_local = new
            if best_local is None:
                continue
            new, nv = best_local, best_local_val

        # accept strictly improving moves
        if nv < curr_val:
            curr, curr_val = new, nv
            if nv < best_val:
                best, best_val = new, nv

    return best, best_val

# ---------------------------------------------------------------- SA worker replaced by shuffle+intensify
def sa_worker(pid: int,
              edges_data: List[Tuple[int,int,int,int]],
              g, st: int, Q: int,
              time_budget: float,
              seed: int,
              out_q: Queue):
    rng = random.Random(seed)
    original_edges = [Edge(*t) for t in edges_data]

    # prepare maps once
    demand_map = {(e.x,e.y):e.c for e in original_edges}
    demand_map.update({(e.y,e.x):e.c for e in original_edges})
    cost_map   = {(e.x,e.y):e.z for e in original_edges}
    cost_map.update({(e.y,e.x):e.z for e in original_edges})

    best_val = INF
    best_routes: List[List[Tuple[int,int]]] = []
    deadline = time.time() + time_budget

    while time.time() < deadline:
        # 1) random shuffle + greedy
        rng.shuffle(original_edges)
        routes, val = build_routes(
            [Edge(e.x,e.y,e.z,e.c) for e in original_edges],
            g, st, Q)

        # 2) intensify via 150k random swaps
        imp_routes, imp_val = intensify(routes, g, st, Q,
                                        demand_map, cost_map,
                                        attempts=150000)

        # 3) accept improvement
        if imp_val < val:
            routes, val = imp_routes, imp_val

        # 4) record global best
        if val < best_val:
            best_val, best_routes = val, routes
            out_q.put((best_val, best_routes))

    # ensure at least one result
    out_q.put((best_val, best_routes))

# ---------------------------------------------------------------- Floyd-Warshall
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

    edges_data = [(e.x,e.y,e.z,e.c) for e in edges]

    workers = min(20, os.cpu_count() or 1)
    if args.termination < 1.5:
        workers = 1
    per_worker = args.termination - 0.3
    if per_worker <= 0.1:
        workers, per_worker = 1, args.termination - 0.05

    ctx = get_context("spawn")
    q: Queue = ctx.Manager().Queue()

    start = time.time()
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        for i in range(workers):
            pool.submit(sa_worker, i, edges_data, g, st, Q,
                        per_worker, args.seed + 10007 * i, q)

        best_val, best_routes = INF, []
        deadline = start + args.termination - 0.05
        while time.time() < deadline:
            try:
                val, routes = q.get(timeout=0.02)
                if val < best_val:
                    best_val, best_routes = val, routes
            except queue.Empty:
                pass

    if best_val == INF:
        best_routes, best_val = build_routes(edges, g, st, Q)

    output(best_routes, best_val)

if __name__ == "__main__":
    main()
