from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel
from sqlalchemy import UnaryExpression, asc, select
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


class CRUDBase[
    ModelType: DeclarativeBase,
    CreateSchemaType: BaseModel,
    UpdateSchemaType: BaseModel,
]:
    """Generic CRUD base class providing common database operations.

    This class is designed to be subclassed by service classes that require
    standard create, read, update, and delete operations against a SQLAlchemy
    model. It uses Python 3.12+ generic syntax to ensure type safety across
    model, create-schema, and update-schema types.

    Type Parameters:
        ModelType: The SQLAlchemy ORM model class.
        CreateSchemaType: The Pydantic schema used for object creation.
        UpdateSchemaType: The Pydantic schema used for object updates.

    Example:
        >>> class ItemService(CRUDBase[Item, ItemCreate, ItemUpdate]):
        ...     pass
        >>> service = ItemService(Item)
    """

    def __init__(self, model: type[ModelType]):
        """Initialize the CRUD service with a SQLAlchemy model class.

        Args:
            model: The SQLAlchemy model class to operate on.
        """
        self._model = model

    async def create(
        self,
        db_session: AsyncSession,
        create_schema: CreateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Create and persist a new model instance.

        Accepts either a Pydantic schema or a plain dictionary. Unset fields
        in the schema are excluded from the INSERT statement.

        Args:
            db_session: The active async database session.
            create_schema: Data used to populate the new record, either as a
                Pydantic model (``exclude_unset=True`` applied) or a raw dict.

        Returns:
            The newly created and refreshed ORM instance.
        """
        data = (
            create_schema
            if isinstance(create_schema, dict)
            else create_schema.model_dump(exclude_unset=True)
        )

        db_object = self._model(**data)
        db_session.add(db_object)
        await db_session.commit()
        await db_session.refresh(db_object)

        return db_object

    async def get(
        self,
        db_session: AsyncSession,
        *args,
        **kwargs,
    ) -> ModelType | None:
        """Retrieve a single model instance matching the given filters.

        Positional arguments are passed to ``.filter()`` (SQLAlchemy column
        expressions), while keyword arguments are passed to ``.filter_by()``
        (equality filters by attribute name).

        Args:
            db_session: The active async database session.
            *args: Optional SQLAlchemy column expressions for filtering.
            **kwargs: Optional keyword filters applied via ``filter_by``.

        Returns:
            The matching ORM instance, or ``None`` if no record is found.
        """
        stmt = select(self._model)

        if args:
            stmt = stmt.filter(*args)

        if kwargs:
            stmt = stmt.filter_by(**kwargs)

        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db_session: AsyncSession,
        *args,
        page: int = 1,
        per_page: int = 100,
        order_by: list[UnaryExpression] | None = None,
        **kwargs,
    ) -> Sequence[ModelType]:
        """Retrieve a paginated list of model instances.

        Applies optional column-expression filters (``*args``) and equality
        filters (``**kwargs``). Results default to ascending ``id`` order when
        the model exposes that column and no explicit ordering is provided.

        Args:
            db_session: The active async database session.
            *args: Optional SQLAlchemy column expressions for filtering.
            page: 1-based page number (default: ``1``).
            per_page: Maximum records per page (default: ``100``).
            order_by: List of SQLAlchemy unary expressions defining sort order.
                Defaults to ``[asc(model.id)]`` when the model has an ``id``
                column.
            **kwargs: Optional keyword filters applied via ``filter_by``.

        Returns:
            A sequence of ORM instances for the requested page.
        """
        query = (
            select(self._model)
            .filter(*args)
            .filter_by(**kwargs)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        if order_by is None and hasattr(self._model, "id"):
            order_by = [asc(self._model.id)]  # type: ignore[attr-defined]

        if order_by is not None:
            query = query.order_by(*order_by)

        result = await db_session.execute(query)
        return result.scalars().all()

    async def update(
        self,
        db_session: AsyncSession,
        *,
        db_object: ModelType | None,
        update_schema: UpdateSchemaType | dict[str, Any],
        exclude_none: bool = True,
        **kwargs,
    ) -> ModelType | None:
        """Update an existing model instance with the provided data.

        If ``db_object`` is ``None``, the method attempts to fetch the record
        using ``**kwargs`` before applying updates. Fields explicitly set to
        ``None`` in the update schema are skipped when ``exclude_none=True``
        (the default).

        Args:
            db_session: The active async database session.
            db_object: The ORM instance to update, or ``None`` to trigger a
                lookup via ``**kwargs``.
            update_schema: New field values as a Pydantic model or dict.
                Only fields present in ``model_dump(exclude_unset=True)`` are
                applied.
            exclude_none: When ``True`` (default), ``None`` values in the
                update payload are ignored and the existing column value is
                preserved.
            **kwargs: Filters forwarded to :meth:`get` when ``db_object`` is
                ``None``.

        Returns:
            The updated and refreshed ORM instance, or ``None`` if the record
            could not be found.
        """
        db_object = db_object or await self.get(db_session, **kwargs)

        if db_object is not None:
            data = (
                update_schema
                if isinstance(update_schema, dict)
                else update_schema.model_dump(exclude_unset=True)
            )

            if not data:
                return db_object

            for attribute, value in data.items():
                if exclude_none and value is None:
                    continue
                setattr(db_object, attribute, value)

            await db_session.commit()
            await db_session.refresh(db_object)

        return db_object

    async def delete(
        self,
        db_session: AsyncSession,
        db_object: ModelType | None,
        **kwargs,
    ) -> ModelType | None:
        """Permanently delete a model instance from the database.

        If ``db_object`` is ``None``, the method looks up the record via
        ``**kwargs`` before deleting. No error is raised when the record does
        not exist.

        Args:
            db_session: The active async database session.
            db_object: The ORM instance to delete, or ``None`` to trigger a
                lookup via ``**kwargs``.
            **kwargs: Filters forwarded to :meth:`get` when ``db_object`` is
                ``None``.

        Returns:
            The deleted ORM instance, or ``None`` if no matching record was
            found.
        """
        db_object = db_object or await self.get(db_session, **kwargs)

        if db_object:
            await db_session.delete(db_object)
            await db_session.commit()

        return db_object

    async def bulk_create(
        self,
        db_session: AsyncSession,
        create_schemas: Sequence[CreateSchemaType | dict[str, Any]],
        refresh: bool = False,
    ) -> Sequence[ModelType]:
        """Create multiple model instances in a single transaction.

        All objects are added and committed together. Optionally refreshes
        each instance from the database after the commit.

        Args:
            db_session: The active async database session.
            create_schemas: An iterable of Pydantic models or dicts describing
                the records to create.
            refresh: When ``True``, each created instance is refreshed from
                the database after the commit. Defaults to ``False``.

        Returns:
            A sequence of the newly created ORM instances.
        """
        db_objects = []

        for create_schema in create_schemas:
            data = (
                create_schema
                if isinstance(create_schema, dict)
                else create_schema.model_dump(exclude_unset=True)
            )
            db_objects.append(self._model(**data))

        db_session.add_all(db_objects)
        await db_session.commit()

        if refresh:
            for db_object in db_objects:
                await db_session.refresh(db_object)

        return db_objects

    async def bulk_update(
        self,
        db_session: AsyncSession,
        updates: Sequence[tuple[ModelType, UpdateSchemaType | dict[str, Any]]],
        refresh: bool = False,
    ) -> None:
        """Update multiple model instances in a single bulk statement.

        Builds a list of update payloads keyed by each object's ``uid``
        attribute and executes a single SQLAlchemy bulk UPDATE. Optionally
        refreshes each instance after the commit.

        Args:
            db_session: The active async database session.
            updates: A sequence of ``(db_object, update_schema)`` tuples.
                Each update schema or dict must resolve to a non-empty payload
                to be included in the bulk statement.
            refresh: When ``True``, each instance is refreshed from the
                database after the commit. Defaults to ``False``.

        Note:
            Each model instance **must** expose a ``uid`` attribute, which is
            used as the WHERE key in the bulk UPDATE statement.
        """
        data_list = []

        for db_object, update_schema in updates:
            data = (
                update_schema
                if isinstance(update_schema, dict)
                else update_schema.model_dump(exclude_unset=True)
            )
            if data:
                data["uid"] = db_object.uid  # type: ignore[attr-defined]
                data_list.append(data)

        await db_session.execute(sqlalchemy_update(self._model), data_list)
        await db_session.commit()

        if refresh:
            for db_object, _ in updates:
                await db_session.refresh(db_object)
