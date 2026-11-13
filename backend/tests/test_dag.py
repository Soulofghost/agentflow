import pytest
from app.engine.dag import DagEngine, CyclicDependencyError, InvalidNodeDependencyError

def test_topological_sort_linear():
    nodes = [
        {"id": "c", "dependencies": ["b"]},
        {"id": "a", "dependencies": []},
        {"id": "b", "dependencies": ["a"]}
    ]
    tiers = DagEngine.validate_and_sort(nodes)
    assert len(tiers) == 3
    assert tiers[0][0]["id"] == "a"
    assert tiers[1][0]["id"] == "b"
    assert tiers[2][0]["id"] == "c"

def test_topological_sort_parallel_branches():
    nodes = [
        {"id": "start", "dependencies": []},
        {"id": "worker1", "dependencies": ["start"]},
        {"id": "worker2", "dependencies": ["start"]},
        {"id": "join", "dependencies": ["worker1", "worker2"]}
    ]
    tiers = DagEngine.validate_and_sort(nodes)
    assert len(tiers) == 3
    assert len(tiers[0]) == 1 # start
    assert len(tiers[1]) == 2 # worker1 and worker2 can run in parallel
    assert len(tiers[2]) == 1 # join

def test_cycle_detection():
    # a -> b -> c -> a (cycle)
    nodes = [
        {"id": "a", "dependencies": ["c"]},
        {"id": "b", "dependencies": ["a"]},
        {"id": "c", "dependencies": ["b"]}
    ]
    with pytest.raises(CyclicDependencyError):
        DagEngine.validate_and_sort(nodes)

def test_missing_dependency():
    nodes = [
        {"id": "a", "dependencies": ["non_existent_node"]}
    ]
    with pytest.raises(InvalidNodeDependencyError):
        DagEngine.validate_and_sort(nodes)
