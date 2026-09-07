"""
Modul Logika Karnaugh Map untuk Sistem Parkir Cerdas.

Persamaan Boolean yang disederhanakan dari K-Map:
    M = D + W       (Cluster Merah: Dekan atau Wakil Dekan)
    O = D + W + S   (Cluster Orange: Dekan, Wakil Dekan, atau Dosen)

Ini adalah SINGLE SOURCE OF TRUTH untuk penentuan hak akses cluster.
Tidak boleh ada logika penentuan cluster di tempat lain.
"""

from typing import Optional, List, Dict, Union


def compute_cluster(jabatan: Optional[str]) -> Optional[str]:
    """Menentukan cluster parkir berdasarkan persamaan Karnaugh Map."""
    if jabatan is None or not isinstance(jabatan, str):
        return None

    jabatan = jabatan.strip().upper()
    D = 1 if jabatan == "D" else 0
    W = 1 if jabatan == "W" else 0
    S = 1 if jabatan == "S" else 0

    M = D or W
    O = D or W or S

    if M:
        return "Merah"
    elif O:
        return "Orange"
    return None


def validate_cluster_access(
    jabatan: Optional[str],
    slot_cluster: Optional[str],
    allow_merah_to_orange_fallback: bool = True,
) -> bool:
    """Validasi akses cluster dengan fallback Merah -> Orange yang dapat dikonfigurasi."""
    if slot_cluster is None or not isinstance(slot_cluster, str):
        return False

    slot_cluster = slot_cluster.strip()
    if slot_cluster not in ["Merah", "Orange"]:
        return False

    allowed_cluster = compute_cluster(jabatan)
    if allowed_cluster is None:
        return False

    if allowed_cluster == "Merah":
        return slot_cluster == "Merah" or (
            slot_cluster == "Orange" and allow_merah_to_orange_fallback
        )

    return slot_cluster == "Orange"


def get_truth_table() -> List[Dict[str, Union[int, bool, str, None]]]:
    """Mengembalikan tabel kebenaran lengkap Karnaugh Map."""
    table = []
    for D in [0, 1]:
        for W in [0, 1]:
            for S in [0, 1]:
                M = D or W
                O = D or W or S

                if D:
                    jabatan = "D"
                elif W:
                    jabatan = "W"
                elif S:
                    jabatan = "S"
                else:
                    jabatan = None

                table.append({
                    "D": D, "W": W, "S": S,
                    "M_Merah": M, "O_Orange": O,
                    "jabatan": jabatan,
                    "cluster": compute_cluster(jabatan)
                })
    return table


def print_truth_table() -> None:
    """Print tabel kebenaran Karnaugh Map."""
    table = get_truth_table()
    print("=" * 70)
    print("TABEL KEBENARAN KARNAUGH MAP - SISTEM PARKIR CERDAS")
    print("=" * 70)
    print(f"{'D':^3} | {'W':^3} | {'S':^3} | {'M(Merah)':^9} | {'O(Orange)':^10} | {'Cluster':^10}")
    print("-" * 70)
    for row in table:
        m = "Aktif" if row["M_Merah"] else "-"
        o = "Aktif" if row["O_Orange"] else "-"
        c = row["cluster"] if row["cluster"] else "Tidak Berhak"
        print(f"{row['D']:^3} | {row['W']:^3} | {row['S']:^3} | {m:^9} | {o:^10} | {c:^10}")
    print("=" * 70)


if __name__ == "__main__":
    print_truth_table()
