#!/usr/bin/env python3
# ------------------------------------------------------------
#  CARP solver – nearest-feasible greedy + intensify + 8-way parallel
# ------------------------------------------------------------
import sys, argparse, time, random, os, queue
from multiprocessing import get_context, Queue
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple, TypeVar
INF = 0x3f3f3f3f

# Route and Edge type aliases
EdgeT = Tuple[int,int,int,int]   # (u, v, cost, demand)
Route = List[Tuple[int,int]]

# ----------------------------------------------------------------
#  Nearest-feasible greedy builder
# ----------------------------------------------------------------
def build_routes(edges: List[EdgeT], dist, depot: int, cap: int):
    edges = edges[:]  # local copy
    routes, total = [], 0
    while edges:
        head, q = depot, cap
        rt: Route = []
        while edges:
            row = dist[head]
            best_i, best_key = -1, INF
            for i, (u, v, cost, dem) in enumerate(edges):
                if dem > q:
                    continue
                key = row[u] if row[u] < row[v] else row[v]
                if key < best_key:
                    best_key, best_i = key, i
            if best_i < 0:
                break
            u, v, z, d = edges.pop(best_i)
            if dist[head][u] > dist[head][v]:
                u, v = v, u
            total += dist[head][u] + z
            q -= d
            head = v
            rt.append((u, v))
        total += dist[head][depot]
        if rt:
            routes.append(rt)
    return routes, total

# ---------------------------------------------------------------- intensify function
def intensify(routes: List[Route],
              dist, depot: int, cap: int,
              demand_map, cost_map,
              attempts: int=150000) -> Tuple[List[Route], int]:
    curr = [list(rt) for rt in routes]
    best = curr
    def route_cost(rt: Route):
        tot, cur = 0, depot
        for u,v in rt:
            tot += dist[cur][u] + cost_map[(u,v)]
            cur = v
        tot += dist[cur][depot]
        return tot
    def route_demand(rt: Route):
        return sum(demand_map[(u,v)] for u,v in rt)
    curr_val = sum(route_cost(rt) for rt in curr)
    best_val = curr_val
    positions = [(ri, pi)
                 for ri, rt in enumerate(curr)
                 for pi in range(len(rt))]
    rng = random.Random()
    for _ in range(attempts):
        r1,p1 = rng.choice(positions)
        r2,p2 = rng.choice(positions)
        if (r1,p1)==(r2,p2): continue
        new = [list(rt) for rt in curr]
        new[r1][p1], new[r2][p2] = new[r2][p2], new[r1][p1]
        if r1!=r2:
            if route_demand(new[r1])>cap or route_demand(new[r2])>cap:
                continue
        nv = sum(route_cost(rt) for rt in new)
        if nv < curr_val:
            curr, curr_val = new, nv
            if nv < best_val:
                best, best_val = new, nv
    return best, best_val

# ---------------------------------------------------------------- SA worker replaced by shuffle+intensify
def sa_worker(pid: int,
              edges_data: List[EdgeT],
              dist, depot: int, cap: int,
              time_budget: float,
              seed: int,
              out_q: Queue):
    rng = random.Random(seed)
    original = edges_data[:]

    # prepare maps once
    demand_map = {(u,v):d for u,v,_,d in original}
    demand_map.update({(v,u):d for u,v,_,d in original})
    cost_map   = {(u,v):c for u,v,c,_ in original}
    cost_map.update({(v,u):c for u,v,c,_ in original})

    best_val = INF
    best_routes: List[Route] = []
    deadline = time.time() + time_budget

    while time.time() < deadline:
        rng.shuffle(original)
        routes, val = build_routes(original, dist, depot, cap)

        imp_routes, imp_val = intensify(routes, dist, depot, cap,
                                        demand_map, cost_map,
                                        attempts=150000)
        if imp_val < val:
            routes, val = imp_routes, imp_val

        if val < best_val:
            best_val, best_routes = val, routes
            out_q.put((best_val, best_routes))

    out_q.put((best_val, best_routes))

# ---------------------------------------------------------------- Floyd-Warshall
def floyd(n: int, dist):
    for k in range(1, n+1):
        row_k = dist[k]
        for i in range(1, n+1):
            ik = dist[i][k]
            if ik == INF: continue
            row_i = dist[i]
            for j in range(1, n+1):
                alt = ik + row_k[j]
                if alt < row_i[j]:
                    row_i[j] = alt

# ---------------------------------------------------------------- read instance
def read_instance(path: str):
    with open(path) as f:
        _  = f.readline()
        n  = int(f.readline().split()[2])
        depot = int(f.readline().split()[2])
        m1 = int(f.readline().split()[3])
        m2 = int(f.readline().split()[3])
        _T = int(f.readline().split()[2])
        cap= int(f.readline().split()[2])
        _  = f.readline(); _ = f.readline()
        m = m1 + m2

        dist = [[INF]*(n+1) for _ in range(n+1)]
        for i in range(1, n+1): dist[i][i] = 0
        edges: List[EdgeT] = []
        for _ in range(m):
            u,v,z,d = map(int, f.readline().split())
            if d>0:
                edges.append((u,v,z,d))
            if z < dist[u][v]:
                dist[u][v] = dist[v][u] = z
        _ = f.readline()
    floyd(n, dist)
    return n, depot, cap, dist, edges

# ---------------------------------------------------------------- print answer
def output(routes: List[Route], val: int):
    print("s ", end="")
    for i, rt in enumerate(routes):
        print("0,", end="")
        for u, v in rt:
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
    n, depot, cap, dist, edges = read_instance(args.instance_file)

    workers = min(8, os.cpu_count() or 1)
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
            pool.submit(sa_worker, i, edges, dist, depot, cap,
                        per_worker, args.seed + 10007*i, q)

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
        best_routes, best_val = build_routes(edges, dist, depot, cap)

    output(best_routes, best_val)

if __name__ == "__main__":
    main()
