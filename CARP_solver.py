#!/usr/bin/env python3
import sys
import argparse

INF = 0x3f3f3f3f

class Edge:
    def __init__(self, x, y, z, c):
        self.x = x
        self.y = y
        self.z = z
        self.c = c

def main():
    # 1) parse command line: first positional is your .dat file,
    #    then optional -t <termination> and -s <seed>
    parser = argparse.ArgumentParser(description="CARP solver")
    parser.add_argument('instance_file',
                        help='path to the .dat input file')
    parser.add_argument('-t', '--termination', type=float,
                        help='termination time (unused by solver)')
    parser.add_argument('-s', '--seed', type=int,
                        help='random seed (unused by solver)')
    args = parser.parse_args()

    # 2) re‑wire stdin to read from that file:
    sys.stdin = open(args.instance_file, 'r')

    # 3) if you want to use the seed, you can do:
    if args.seed is not None:
        import random
        random.seed(args.seed)

    # ——— below this line everything is exactly as before ———
    _      = sys.stdin.readline().split()          # NAME : XXX
    parts  = sys.stdin.readline().split(); n  = int(parts[2])
    parts  = sys.stdin.readline().split(); st = int(parts[2])
    parts  = sys.stdin.readline().split(); m1 = int(parts[3])
    parts  = sys.stdin.readline().split(); m2 = int(parts[3])
    parts  = sys.stdin.readline().split(); T  = int(parts[2])
    parts  = sys.stdin.readline().split(); Q  = int(parts[2])
    parts  = sys.stdin.readline().split(); B  = int(parts[6])
    _      = sys.stdin.readline()                  # NODES COST DEMAND

    m = m1 + m2

    g = [[INF] * (n+1) for _ in range(n+1)]
    for i in range(1, n+1):
        g[i][i] = 0

    e = []
    for _ in range(m):
        x, y, z, c = map(int, sys.stdin.readline().split())
        if c > 0:
            e.append(Edge(x, y, z, c))
        g[x][y] = g[y][x] = z

    _ = sys.stdin.readline()  # END

    # Floyd–Warshall
    for k in range(1, n+1):
        for i in range(1, n+1):
            for j in range(1, n+1):
                if g[i][j] > g[i][k] + g[k][j]:
                    g[i][j] = g[i][k] + g[k][j]

    ans = []
    val = 0

    while e:
        p = st
        q = Q
        res = []
        while e:
            e.sort(key=lambda ed: min(g[p][ed.x], g[p][ed.y]))
            idx = next((i for i, ed in enumerate(e) if ed.c <= q), -1)
            if idx < 0:
                break
            ed = e.pop(idx)
            if g[p][ed.x] > g[p][ed.y]:
                ed.x, ed.y = ed.y, ed.x
            val += g[p][ed.x] + ed.z
            res.append(ed)
            q -= ed.c
            p = ed.y
        if res:
            val += g[p][st]
            ans.append(res)

    # output goes to stdout as usual
    print("s ", end="")
    for i, route in enumerate(ans):
        print("0,", end="")
        for ed in route:
            print(f"({ed.x},{ed.y}),", end="")
        if i == len(ans) - 1:
            print("0")
        else:
            print("0,", end="")
    print(f"q {val}")

if __name__ == "__main__":
    main()
