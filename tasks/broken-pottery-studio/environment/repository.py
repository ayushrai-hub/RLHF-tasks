from __future__ import annotations
import math
from data import Page

class EntityNotFound(Exception):
    pass

class Repository:

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def save(self, entity: object) -> object:
        entity_id = self._get_id(entity)
        self._store[entity_id] = entity
        return entity

    def get(self, entity_id: str) -> object:
        if entity_id not in self._store:
            raise EntityNotFound(f"Entity '{entity_id}' not found")
        return self._store[entity_id]

    def delete(self, entity_id: str) -> None:
        if entity_id not in self._store:
            raise EntityNotFound(f"Entity '{entity_id}' not found")
        del self._store[entity_id]

    def find(self, filters: dict[str, object]) -> list[object]:
        return [e for e in self._store.values() if self._matches(e, filters)]

    def count(self, filters: dict[str, object]) -> int:
        return len(self.find(filters))

    def find_paginated(self, filters: dict[str, object], page: int, page_size: int) -> Page:
        all_items = self.find(filters)
        total_count = len(all_items)
        total_pages = max(1, math.ceil(total_count / page_size)) if page_size > 0 else 1
        start = (page - 1) * page_size
        end = start + page_size
        items = all_items[start:end]
        return Page(
            items=items,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    @staticmethod
    def _get_id(entity: object) -> str:
        for attr in ("id", "reservation_id", "student_id", "class_session_id", "studio_id"):
            val = getattr(entity, attr, None)
            if val is not None:
                return str(val)
        raise ValueError(f"Cannot determine ID for entity: {entity!r}")

    @staticmethod
    def _matches(entity: object, filters: dict[str, object]) -> bool:
        return all(getattr(entity, k, None) == v for k, v in filters.items())
