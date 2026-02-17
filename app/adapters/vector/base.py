from abc import ABC, abstractmethod

class VectorStore(ABC):
    @abstractmethod
    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]): ...
    @abstractmethod
    def search(self, vector: list[float], top_k: int, filter: dict | None = None) -> list[dict]: ...
