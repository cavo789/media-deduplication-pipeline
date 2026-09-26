"""Link items two by two, then read the connected sets (disjoint-set forest)."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class UnionFind[T]:
    """Connected sets of items, built by linking pairs of items."""

    def __init__(self, items: Sequence[T]) -> None:
        """Start with every item alone.

        Args:
            items: The items, referred to by their position.
        """
        self._items = items
        self._parent = list(range(len(items)))

    def link(self, first: int, second: int) -> None:
        """Put two items in the same set.

        Args:
            first: Position of an item.
            second: Position of another item.
        """
        self._parent[self._root(first)] = self._root(second)

    def sets(self) -> list[list[T]]:
        """Return the sets of two items or more, in the order of their first item.

        Returns:
            The linked sets.
        """
        grouped: defaultdict[int, list[T]] = defaultdict(list)
        for index, item in enumerate(self._items):
            grouped[self._root(index)].append(item)
        return [members for members in grouped.values() if len(members) > 1]

    def _root(self, index: int) -> int:
        """Find the representative of an item's set, shortening the path to it.

        Args:
            index: Position of an item.

        Returns:
            Position of the representative.
        """
        while self._parent[index] != index:
            self._parent[index] = self._parent[self._parent[index]]
            index = self._parent[index]
        return index
