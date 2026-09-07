from logic.karnaugh import compute_cluster, validate_cluster_access, get_truth_table


def test_compute_cluster_mapping():
    assert compute_cluster("D") == "Merah"
    assert compute_cluster("W") == "Merah"
    assert compute_cluster("S") == "Orange"


def test_compute_cluster_normalizes_input():
    assert compute_cluster(" d ") == "Merah"
    assert compute_cluster("s") == "Orange"
    assert compute_cluster(None) is None
    assert compute_cluster("X") is None


def test_validate_cluster_access_preserves_default_fallback():
    assert validate_cluster_access("D", "Merah") is True
    assert validate_cluster_access("D", "Orange") is True
    assert validate_cluster_access("S", "Merah") is False
    assert validate_cluster_access("S", "Orange") is True


def test_validate_cluster_access_can_disable_fallback():
    assert validate_cluster_access("D", "Orange", allow_merah_to_orange_fallback=False) is False
    assert validate_cluster_access("D", "Merah", allow_merah_to_orange_fallback=False) is True


def test_truth_table_has_all_combinations():
    table = get_truth_table()
    assert len(table) == 8
    assert {row["cluster"] for row in table} == {None, "Merah", "Orange"}
