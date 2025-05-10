import numpy as np
import re

def parse_instance(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    info = {}
    edges = []
    for line in lines:
        if ':' in line:
            key, val = line.split(':', 1)
            info[key.strip()] = val.strip()
        elif line.strip().startswith('END'):
            break
        elif line.strip() and line[0].isdigit():
            u, v, cost, demand = map(int, line.split())
            edges.append({'u': u, 'v': v, 'cost': cost, 'demand': demand})
    return {
        'V': int(info['VERTICES']),
        'depot': int(info['DEPOT']),
        'vehicles': int(info['VEHICLES']),
        'capacity': int(info['CAPACITY']),
        'required': {(min(e['u'],e['v']),max(e['u'],e['v'])) for e in edges if e['demand']>0},
        'edges': edges
    }

def build_graph(instance):
    V = instance['V']
    INF = 10**9
    cost = np.full((V+1, V+1), INF, dtype=int)
    for e in instance['edges']:
        u, v, c = e['u'], e['v'], e['cost']
        cost[u,v] = cost[v,u] = min(cost[u,v], c)
    for i in range(1, V+1):
        cost[i,i] = 0
    for k in range(1, V+1):
        for i in range(1, V+1):
            for j in range(1, V+1):
                if cost[i,j] > cost[i,k] + cost[k,j]:
                    cost[i,j] = cost[i,k] + cost[k,j]
    return cost

def parse_solution(filename):
    with open(filename) as f:
        lines = [l.strip() for l in f if l.strip()]
    s_lines = [l for l in lines if l.startswith('s ')]
    q_lines = [l for l in lines if l.startswith('q ')]
    if len(s_lines) != 1 or len(q_lines) != 1:
        raise ValueError('Require exactly one s‑line and one q‑line')
    q_val = int(q_lines[0].split()[1])
    raw = s_lines[0][2:]      # drop leading 's '
    tokens = re.findall(r'\(\d+,\d+\)|0', raw)
    routes = []
    curr = []
    for t in tokens:
        if t == '0':
            if curr:
                routes.append(curr)
                curr = []
        else:
            u, v = map(int, re.findall(r'\d+', t))
            curr.append((u, v))
    if curr:
        routes.append(curr)
    return routes, q_val

def calc_total_cost(routes, instance, cost):
    edge_cost = {}
    for e in instance['edges']:
        edge_cost[(e['u'],e['v'])] = edge_cost[(e['v'],e['u'])] = e['cost']
    depot = instance['depot']
    total = 0
    served = set()
    for route in routes:
        load = 0
        curr = depot
        for u, v in route:
            total += cost[curr, u]                 # deadheading
            total += edge_cost[(u, v)]            # service
            load += next(e['demand'] for e in instance['edges']
                         if {e['u'], e['v']} == {u, v})
            served.add((min(u, v), max(u, v)))
            curr = v
        total += cost[curr, depot]
        if load > instance['capacity']:
            raise ValueError(f'Route load {load} exceeds capacity')
    if len(routes) > instance['vehicles']:
        raise ValueError(f'Using {len(routes)} routes > available {instance["vehicles"]}')
    if served != instance['required']:
        miss = instance['required'] - served
        dup  = served - instance['required']
        raise ValueError(f'Missing tasks {miss}, extra {dup}')
    return total

def main():
    inst_file = r'E:\U\Assignment\CS311\Project2\egl-s1-A.dat'
    sol_file  = r'E:\U\Assignment\CS311\Project2\sample.txt'

    inst   = parse_instance(inst_file)
    cost   = build_graph(inst)
    routes, q_given = parse_solution(sol_file)
    q_calc = calc_total_cost(routes, inst, cost)

    if q_calc != q_given:
        print(f'q mismatch: computed {q_calc} vs given {q_given}')
    else:
        print("Legal solution")
        print(f"Routes used: {len(routes)}, Total cost: {q_calc}")

if __name__ == '__main__':
    main()
