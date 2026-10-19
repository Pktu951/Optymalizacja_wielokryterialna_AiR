"""Python equivalent of Lab1.m: three algorithms for finding nondominated points."""

import matplotlib.pyplot as plt
import numpy as np


X = np.array(
    [
        [5, 5], [3, 6], [4, 4], [5, 3], [3, 3], [1, 8],
        [3, 4], [4, 5], [3, 10], [6, 6], [4, 1], [3, 5],
    ],
    dtype=float,
)


def no_filter(points):
    """Algorithm 1: compare points without filtering the input array."""
    n, dimensions = points.shape
    result = []
    active = np.ones(n, dtype=bool)
    point_comparisons = coordinate_comparisons = 0

    for i in range(n):
        if not active[i]:
            continue
        candidate = points[i].copy()
        changed_candidate = False

        for j in range(i + 1, n):
            if not active[j]:
                continue
            outcome, count = compare(candidate, points[j])
            point_comparisons += 1
            coordinate_comparisons += count
            if outcome == 1:
                active[j] = False
            elif outcome == -1:
                active[i] = False
                candidate = points[j].copy()
                changed_candidate = True

        if not any(np.array_equal(candidate, row) for row in result):
            result.append(candidate)
        if not changed_candidate:
            active[i] = False

    return np.asarray(result, dtype=float).reshape(-1, dimensions), {
        "porPkt": point_comparisons,
        "porWsp": coordinate_comparisons,
    }


def filter_alg(points):
    """Algorithm 2: remove dominated points from the working set."""
    remaining = [row.copy() for row in points]
    result = []
    point_comparisons = coordinate_comparisons = 0

    while remaining:
        candidate = remaining.pop(0)
        j = 0
        while j < len(remaining):
            outcome, count = compare(candidate, remaining[j])
            point_comparisons += 1
            coordinate_comparisons += count
            if outcome == 1:
                remaining.pop(j)
            elif outcome == -1:
                candidate = remaining.pop(j)
                j = 0
            elif np.array_equal(candidate, remaining[j]):
                remaining.pop(j)
            else:
                j += 1

        result.append(candidate)
        k = 0
        while k < len(remaining):
            outcome, count = compare(candidate, remaining[k])
            point_comparisons += 1
            coordinate_comparisons += count
            if outcome == 1:
                remaining.pop(k)
            else:
                k += 1

    return np.asarray(result, dtype=float).reshape(-1, points.shape[1]), {
        "porPkt": point_comparisons,
        "porWsp": coordinate_comparisons,
    }


def ideal_point_algorithm(points):
    """Algorithm 3: order points by distance from the ideal point."""
    n = points.shape[0]
    point_comparisons = coordinate_comparisons = 0
    ideal = np.min(points, axis=0)
    distances = np.sum((points - ideal) ** 2, axis=1)
    _, order, sort_comparisons = merge_sort_count(distances)

    active = np.ones(n, dtype=bool)
    indices = []
    for point_index in order:
        if not active[point_index]:
            continue
        indices.append(point_index)
        active[point_index] = False
        for other_index in np.flatnonzero(active):
            dominated, count = dominates(points[point_index], points[other_index])
            point_comparisons += 1
            coordinate_comparisons += count
            if dominated:
                active[other_index] = False
        if not np.any(active):
            break

    indices_array = np.asarray(indices, dtype=int)
    result = points[indices_array]
    estimated_sorted_point_comparisons = (
        sort_comparisons * point_comparisons / coordinate_comparisons
        if coordinate_comparisons > 0 else 0
    )
    stats = {
        "porPkt": point_comparisons,
        "porWsp": coordinate_comparisons,
        "porSort": sort_comparisons,
        "porPktSort": estimated_sorted_point_comparisons,
        "porPktRazem": point_comparisons + estimated_sorted_point_comparisons,
    }
    # Match MATLAB's one-based indices in the displayed result.
    return result, indices_array + 1, stats


def compare(y, x):
    """Return 1 if y dominates x, -1 if x dominates y, otherwise 0."""
    better = worse = False
    comparisons = 0
    for y_value, x_value in zip(y, x):
        comparisons += 1
        if y_value < x_value:
            better = True
        elif y_value > x_value:
            worse = True
        if better and worse:
            break
    if better and not worse:
        return 1, comparisons
    if worse and not better:
        return -1, comparisons
    return 0, comparisons


def dominates(y, x):
    """Dominance check used by algorithm 3, matching the MATLAB implementation."""
    comparisons = 0
    for y_value, x_value in zip(y, x):
        comparisons += 1
        if y_value > x_value:
            return False, comparisons
    return True, comparisons


def merge_sort_count(values):
    """Merge sort that counts value comparisons."""
    values = np.asarray(values, dtype=float).reshape(-1)
    if len(values) <= 1:
        return values.copy(), list(range(len(values))), 0

    middle = len(values) // 2
    left, left_indices, left_count = merge_sort_count(values[:middle])
    right, right_indices, right_count = merge_sort_count(values[middle:])
    right_indices = [index + middle for index in right_indices]

    merged, merged_indices = [], []
    i = j = 0
    comparisons = left_count + right_count
    while i < len(left) and j < len(right):
        comparisons += 1
        if left[i] <= right[j]:
            merged.append(left[i])
            merged_indices.append(left_indices[i])
            i += 1
        else:
            merged.append(right[j])
            merged_indices.append(right_indices[j])
            j += 1
    merged.extend(left[i:])
    merged_indices.extend(left_indices[i:])
    merged.extend(right[j:])
    merged_indices.extend(right_indices[j:])
    return np.asarray(merged), merged_indices, comparisons


def print_points(points):
    """Print a point matrix in a MATLAB-like layout."""
    print("[]" if len(points) == 0 else
          np.array2string(points, precision=6, suppress_small=True))


def main():
    p1, stats1 = no_filter(X)
    p2, stats2 = filter_alg(X)
    p3, indices_p, stats3 = ideal_point_algorithm(X)

    print("\nALGORYTM 1 - BEZ FILTRACJI")
    print("Punkty niezdominowane:")
    print_points(p1)
    print(f"Porownania punktow: {stats1['porPkt']}")
    print(f"Porownania wspolrzednych: {stats1['porWsp']}")

    print("\nALGORYTM 2 - Z FILTRACJA")
    print("Punkty niezdominowane:")
    print_points(p2)
    print(f"Porownania punktow: {stats2['porPkt']}")
    print(f"Porownania wspolrzednych: {stats2['porWsp']}")

    print("\nALGORYTM 3 - PUNKT IDEALNY")
    print("Punkty niezdominowane:")
    print_points(p3)
    print("Indeksy punktow w X:")
    print(indices_p)
    print("Punkt idealny:")
    print(np.min(X, axis=0))
    print(f"Porownania punktow (faza 2): {stats3['porPkt']}")
    print(f"Porownania wspolrzednych (faza 2): {stats3['porWsp']}")
    print(f"Porownania przy sortowaniu: {stats3['porSort']}")
    print(f"Szacowane porownania punktow lacznie: {stats3['porPktRazem']:.2f}")

    if X.shape[1] >= 2:
        if X.shape[1] > 2:
            print("Uwaga: wykresy punktow pokazuja tylko pierwsze dwa kryteria.")
        point_sets = [p1, p2, p3]
        names = ["1. Bez filtracji", "2. Z filtracja", "3. Punkt idealny"]
        figure, axes = plt.subplots(1, 3, num="Punkty niezdominowane")
        for index, axis in enumerate(axes):
            axis.grid(True)
            axis.plot(X[:, 0], X[:, 1], "bo", markersize=8)
            axis.plot(point_sets[index][:, 0], point_sets[index][:, 1],
                      "rd", markersize=9, markerfacecolor="red")
            if index == 2:
                ideal = np.min(X, axis=0)
                axis.plot(ideal[0], ideal[1], "k*", markersize=12)
                axis.legend(["Zbior X", "P(X)", "Punkt idealny"], loc="best")
            else:
                axis.legend(["Zbior X", "P(X)"], loc="best")
            axis.set_xlabel("Kryterium 1 (min)")
            axis.set_ylabel("Kryterium 2 (min)")
            axis.set_title(names[index])
        figure.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()

