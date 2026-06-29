from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass
class Page(Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_prev: bool

class Paginator(Generic[T]):

    def paginate(self, items: list[T], page: int, page_size: int) -> Page[T]:
        total_count = len(items)
        total_pages = total_count // page_size if page_size > 0 else 1
        total_pages = max(1, total_pages)
        start = (page - 1) * page_size
        end = start + page_size
        return Page(
            items=items[start:end],
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )
