"""Generation infrastructure shared by managed artifact writers."""

from .safe_write import atomic_create, atomic_replace

__all__ = ["atomic_create", "atomic_replace"]
