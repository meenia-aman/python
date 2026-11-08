"""PostgreSQL integration tests, using a fresh disposable schema for every test.

Run with MODULE_V3_TEST_DATABASE_URL=postgresql+asyncpg://... then:
    .venv/bin/python -m unittest discover -s src/module_v3/tests -v

The application's DATABASE_URL is never used for test queries.
"""

import asyncio
import json
import os
import unittest
from typing import Annotated
from unittest.mock import patch
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.module_v3 import db
from src.module_v3.email.model import Email, EmailStatus
from src.module_v3.email.service import EmailService
from src.module_v3.order.model import Order
from src.module_v3.order.route import get_order_service
from src.module_v3.order.service import OrderService
from src.module_v3.products.model import Product, ProductCategory
from src.module_v3.products.repository import SqlAlchemyProductRepository
from src.module_v3.products.service import ProductService
from src.module_v3.router import api_router
from src.module_v3.user.model import User
from src.module_v3.user.repository import SqlAlchemyUserRepository


@unittest.skipUnless(
    os.environ.get("MODULE_V3_TEST_DATABASE_URL"),
    "Set MODULE_V3_TEST_DATABASE_URL to a disposable PostgreSQL database",
)
class TransactionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        test_url = os.environ["MODULE_V3_TEST_DATABASE_URL"]
        if not test_url.startswith("postgresql+asyncpg://"):
            raise ValueError("Tests require a postgresql+asyncpg URL")
        self.schema = "uow_test_" + uuid4().hex
        self.engine = create_async_engine(
            test_url,
            connect_args={"server_settings": {"search_path": self.schema}},
        )
        self.addAsyncCleanup(self.engine.dispose)
        async with self.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addAsyncCleanup(self.drop_schema)
        async with self.engine.begin() as connection:
            await connection.run_sync(db.Base.metadata.create_all)

        self.events = []
        lifecycle = self.events

        class TrackedSession(AsyncSession):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                event.listen(self.sync_session, "after_commit", lambda _: lifecycle.append("commit"))
                event.listen(self.sync_session, "after_rollback", lambda _: lifecycle.append("rollback"))

            async def close(self):
                await super().close()
                lifecycle.append("close")

        self.factory = async_sessionmaker(
            self.engine,
            class_=TrackedSession,
            expire_on_commit=False,
            autoflush=False,
            autobegin=False,
        )
        self.factory_patch = patch.object(db, "AsyncSessionLocal", self.factory)
        self.factory_patch.start()
        self.addCleanup(self.factory_patch.stop)
        self.app = FastAPI()
        self.app.include_router(api_router)

        async with self.factory.begin() as session:
            self.user = User(name="Example", email="example@example.com")
            self.product = Product(category=ProductCategory.CLOTHING, price=100, stock_count=5)
            session.add_all([self.user, self.product])
        self.events.clear()

    async def drop_schema(self):
        async with self.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))

    async def request(self, method, path, data=None, *, allow_error=False):
        """Exercise the real ASGI app without adding an HTTP-client dependency."""
        body = json.dumps(data).encode() if data is not None else b""
        messages = []
        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": path,
            "raw_path": path.encode(), "query_string": b"", "root_path": "",
            "headers": [(b"content-type", b"application/json")],
            "client": ("127.0.0.1", 1), "server": ("test", 80),
        }

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            if message["type"] == "http.response.start":
                self.events.append("response:" + str(message["status"]))
            messages.append(message)

        try:
            await self.app(scope, receive, send)
        except Exception:
            if not allow_error:
                raise
        status = next(m["status"] for m in messages if m["type"] == "http.response.start")
        payload = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        return status, json.loads(payload) if payload.startswith((b"{", b"[")) else payload.decode()

    def order_data(self, count=2):
        return {"user_id": str(self.user.id), "product_id": str(self.product.id), "count": count}

    async def state(self):
        async with self.factory.begin() as session:
            product = await session.get(Product, self.product.id)
            orders = await session.scalar(select(func.count()).select_from(Order))
            emails = await session.scalar(select(func.count()).select_from(Email))
            return product.stock_count, orders, emails

    async def test_order_commits_once_and_closes_before_response(self):
        status, order = await self.request("POST", "/v3/orders", self.order_data())
        self.assertEqual(status, 201)
        self.assertEqual(order["total_amount"], 200)
        self.assertEqual(self.events, ["commit", "close", "response:201"])
        self.assertEqual(await self.state(), (3, 1, 1))
        self.assertEqual(self.engine.pool.checkedout(), 0)

    async def test_all_dependencies_share_one_active_session(self):
        @self.app.get("/session")
        async def check(session: db.SessionDep, service: Annotated[OrderService, Depends(get_order_service)]):
            repositories = [service.order_repo, service.user_service.user_repo,
                            service.product_service.product_repo, service.email_service.email_repo]
            return {"shared": all(repo.session is session for repo in repositories),
                    "active": session.in_transaction()}

        status, result = await self.request("GET", "/session")
        self.assertEqual((status, result), (200, {"shared": True, "active": True}))
        self.assertEqual(self.events, ["commit", "close", "response:200"])

    async def test_failure_after_email_flush_rolls_back_everything(self):
        original = EmailService.send_email

        async def fail(service, data):
            await original(service, data)
            raise RuntimeError("Failure after every write was flushed")

        with patch.object(EmailService, "send_email", fail):
            status, _ = await self.request("POST", "/v3/orders", self.order_data(), allow_error=True)
        self.assertEqual(status, 500)
        self.assertEqual(self.events, ["rollback", "close", "response:500"])
        self.assertEqual(await self.state(), (5, 0, 0))

    async def test_database_flush_failure_rolls_back_stock_and_order(self):
        async def invalid_email(service, data):
            return await service.email_repo.add(Email(user_id=data.user_id, order_id=uuid4()))

        with patch.object(EmailService, "send_email", invalid_email):
            with self.assertRaises(IntegrityError):
                await self.request("POST", "/v3/orders", self.order_data())
        self.assertEqual(await self.state(), (5, 0, 0))
        self.assertEqual((await self.request("POST", "/v3/orders", self.order_data()))[0], 201)

    async def test_commit_failure_never_sends_success(self):
        original = EmailService.send_email

        async def inject_commit_failure(service, data):
            email = await original(service, data)

            def fail(_):
                raise RuntimeError("Injected before commit")

            event.listen(service.email_repo.session.sync_session, "before_commit", fail, once=True)
            return email

        with patch.object(EmailService, "send_email", inject_commit_failure):
            status, _ = await self.request("POST", "/v3/orders", self.order_data(), allow_error=True)
        self.assertEqual(status, 500)
        self.assertEqual(self.events, ["rollback", "close", "response:500"])
        self.assertEqual(await self.state(), (5, 0, 0))

    async def test_cancellation_rolls_back_and_closes(self):
        original = EmailService.send_email

        async def cancel(service, data):
            await original(service, data)
            raise asyncio.CancelledError()

        with patch.object(EmailService, "send_email", cancel):
            with self.assertRaises(asyncio.CancelledError):
                await self.request("POST", "/v3/orders", self.order_data())
        self.assertEqual(self.events, ["rollback", "close"])
        self.assertEqual(await self.state(), (5, 0, 0))

    async def test_concurrent_orders_cannot_buy_the_same_last_item(self):
        async with self.factory.begin() as session:
            product = await session.get(Product, self.product.id)
            product.stock_count = 1
        results = await asyncio.wait_for(asyncio.gather(
            self.request("POST", "/v3/orders", self.order_data(1)),
            self.request("POST", "/v3/orders", self.order_data(1)),
        ), timeout=10)
        self.assertEqual(sorted(status for status, _ in results), [201, 400])
        self.assertEqual(await self.state(), (0, 1, 1))

    async def test_locked_read_refreshes_a_previously_loaded_product(self):
        async with self.factory.begin() as first:
            stale = await first.get(Product, self.product.id)
            self.assertEqual(stale.stock_count, 5)
            async with self.factory.begin() as second:
                await ProductService(SqlAlchemyProductRepository(second)).reserve_stock(self.product.id, 1)
            await ProductService(SqlAlchemyProductRepository(first)).reserve_stock(self.product.id, 1)
        self.assertEqual(await self.state(), (3, 0, 0))

    async def test_repeated_reservations_preserve_unflushed_changes(self):
        async with self.factory.begin() as session:
            service = ProductService(SqlAlchemyProductRepository(session))
            await service.reserve_stock(self.product.id, 1)
            await service.reserve_stock(self.product.id, 1)
        self.assertEqual(await self.state(), (3, 0, 0))

    async def test_nonpositive_service_quantity_is_rejected(self):
        for count in (0, -1):
            with self.subTest(count=count):
                async with self.factory.begin() as session:
                    service = ProductService(SqlAlchemyProductRepository(session))
                    with self.assertRaises(HTTPException) as error:
                        await service.reserve_stock(self.product.id, count)
                    self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(await self.state(), (5, 0, 0))

    async def test_no_implicit_transaction_outside_boundary(self):
        async with self.factory() as session:
            with self.assertRaises(InvalidRequestError):
                await session.get(Product, self.product.id)

    async def test_standalone_write_routes_commit(self):
        status, user = await self.request("POST", "/v3/users", {"name": "Another", "email": "another@example.com"})
        self.assertEqual(status, 201)
        self.assertEqual((await self.request("GET", "/v3/users/" + user["id"]))[0], 200)
        status, product = await self.request("POST", "/v3/products", {"category": "CLOTHING", "price": 50, "stock_count": 4})
        self.assertEqual(status, 201)
        self.assertEqual((await self.request("GET", "/v3/products/" + product["id"]))[0], 200)
        _, order = await self.request("POST", "/v3/orders", self.order_data())
        status, email = await self.request("POST", "/v3/emails", {"user_id": str(self.user.id), "order_id": order["id"]})
        self.assertEqual((status, email["status"]), (201, EmailStatus.PENDING.value))
        self.assertEqual(await self.state(), (3, 1, 2))

    async def test_concurrent_duplicate_email_returns_conflict(self):
        barrier = asyncio.Barrier(2)
        original = SqlAlchemyUserRepository.get_by_email

        async def simultaneous_check(repository, email):
            result = await original(repository, email)
            await barrier.wait()
            return result

        data = {"name": "Duplicate", "email": "duplicate@example.com"}
        with patch.object(SqlAlchemyUserRepository, "get_by_email", simultaneous_check):
            results = await asyncio.wait_for(asyncio.gather(
                self.request("POST", "/v3/users", data),
                self.request("POST", "/v3/users", data),
            ), timeout=10)
        self.assertEqual(sorted(status for status, _ in results), [201, 409])
        async with self.factory.begin() as session:
            count = await session.scalar(select(func.count()).select_from(User).where(User.email == data["email"]))
            self.assertEqual(count, 1)

    async def test_missing_order_returns_404(self):
        status, _ = await self.request("GET", "/v3/orders/" + str(uuid4()))
        self.assertEqual(status, 404)
        self.assertEqual(self.events, ["rollback", "close", "response:404"])
