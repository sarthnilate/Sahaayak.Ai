from typing import Generic, List, Optional, Type, TypeVar

from backend.app.models.all_models import Base
from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, model_class: Type[T], db: Session):
        self.model_class = model_class
        self.db = db

    def get_by_id(self, id: str) -> Optional[T]:
        return self.db.get(self.model_class, id)

    def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        stmt = select(self.model_class).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def add(self, entity: T) -> T:
        self.db.add(entity)
        return entity

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, entity: T) -> T:
        self.db.refresh(entity)
        return entity
