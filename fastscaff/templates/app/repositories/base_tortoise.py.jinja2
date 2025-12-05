from typing import Any, Generic, List, Optional, Tuple, Type, TypeVar

from tortoise.models import Model
from tortoise.queryset import QuerySet

from app.schemas.base import Pager
from app.utils.sort_helper import parse_order_string

ModelType = TypeVar("ModelType", bound=Model)


class BaseRepository(Generic[ModelType]):
    model: Type[ModelType]

    async def get_by_id(self, entity_id: int) -> Optional[ModelType]:
        return await self.model.filter(id=entity_id).first()

    async def get_all(
        self,
        pager: Optional[Pager] = None,
        order_by: Optional[str] = None,
    ) -> Tuple[List[ModelType], int]:
        query = self.model.all()
        return await self._paginate(query, pager, order_by)

    async def create(self, **kwargs: Any) -> ModelType:
        return await self.model.create(**kwargs)

    async def update(self, entity_id: int, **kwargs: Any) -> Optional[ModelType]:
        await self.model.filter(id=entity_id).update(**kwargs)
        return await self.get_by_id(entity_id)

    async def delete(self, entity_id: int) -> bool:
        deleted = await self.model.filter(id=entity_id).delete()
        return deleted > 0

    async def count(self, query: Optional[QuerySet[ModelType]] = None) -> int:
        target = query if query is not None else self.model.all()
        return await target.count()

    async def _paginate(
        self,
        query: QuerySet,
        pager: Optional[Pager] = None,
        order_by: Optional[str] = None,
    ) -> Tuple[List[ModelType], int]:
        """Execute query with pagination and sorting."""
        total = await query.count()
        if not total:
            return [], 0

        if order_by:
            parsed_order = parse_order_string(order_by, self.model)
            if parsed_order:
                query = query.order_by(parsed_order)

        if pager:
            query = query.offset(pager.offset).limit(pager.limit)

        items = await query.all()
        return items, total
