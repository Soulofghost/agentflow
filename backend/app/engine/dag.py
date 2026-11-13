from typing import List, Dict, Set

class CyclicDependencyError(Exception):
    pass

class InvalidNodeDependencyError(Exception):
    pass

class DagEngine:
    @staticmethod
    def validate_and_sort(nodes: List[Dict[str, any]]) -> List[List[Dict[str, any]]]:
        """
        Validates the DAG structure and returns execution tiers (parallel batches)
        in topological order. Raises exception if cycles or invalid dependencies are detected.
        """
        node_map = {n["id"]: n for n in nodes}
        in_degree = {n["id"]: 0 for n in nodes}
        adj = {n["id"]: [] for n in nodes}

        # Check for unknown dependencies and populate graph
        for n in nodes:
            for dep in n.get("dependencies", []):
                if dep not in node_map:
                    raise InvalidNodeDependencyError(f"Node '{n['id']}' references non-existent dependency '{dep}'")
                adj[dep].append(n["id"])
                in_degree[n["id"]] += 1

        # Kahn's Algorithm with Tier Grouping
        current_tier = [n_id for n_id, deg in in_degree.items() if deg == 0]
        tiers = []
        visited_count = 0

        while current_tier:
            tiers.append([node_map[n_id] for n_id in current_tier])
            visited_count += len(current_tier)
            next_tier = []

            for n_id in current_tier:
                for neighbor in adj[n_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_tier.append(neighbor)

            current_tier = next_tier

        if visited_count != len(nodes):
            raise CyclicDependencyError("Cyclic dependency detected in agent workflow graph.")

        return tiers
