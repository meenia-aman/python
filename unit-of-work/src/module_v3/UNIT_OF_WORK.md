# Module 3: unit of work, explained from the actual code

## Recommendation

Use the revised module 3 as the starting point for this FastAPI + SQLAlchemy
application. Its transaction rule is small enough to understand and verify:

**The API operation owns one transaction. All participating services and
repositories use the same session. They can flush, but never commit or roll back.**

SQLAlchemy already implements the persistence unit of work: it tracks new, dirty,
and deleted objects, flushes their SQL, and coordinates a transaction. A custom
class named `UnitOfWork` is an optional application abstraction over that behavior.
Its presence alone does not make an application safer.

This guide focuses on transaction behavior. It does not teach the repository,
service, or model patterns.

## How the three implementations differ

| Question | Module 1 (`src/module`) | Module 2 (`src/module_v2`) | Original module 3 | Revised module 3 |
| --- | --- | --- | --- | --- |
| Transaction owner | Service enters a module-specific UoW and explicitly commits | Outermost entry into a shared, re-entrant UoW | Services commit by default; callers pass `commit=False` when composing | One function-scoped API dependency; workers open their own explicit boundary |
| Session creation | UoW creates a session on entry | Shared UoW creates a session at depth zero | Cached `get_db` supplies one session per operation | Cached `get_db` supplies one session and transaction per operation |
| Successful exit | No automatic commit; service must call `commit()` | Outermost exit automatically commits | Depends on flags and manual commits | SQLAlchemy's transaction context automatically commits |
| Failed exit | UoW rolls back and closes; close also releases unfinished transactions | Marks rollback-only, outer exit rolls back, then closes | Order service and dependency perform manual rollback | SQLAlchemy's transaction context rolls back; session context closes |
| Composition | Order UoW exposes all needed repositories; separately entered UoWs do not automatically share a transaction | Nested services join the same UoW | Correct only if nested services use the same session and suppress their commits | Services always participate; no commit flags to remember |
| Caught inner exceptions | No custom rollback-only state | Outer success still raises `UnexpectedRollback` if an inner UoW failed | No custom rollback-only state | No custom rollback-only state; required-step errors must escape the boundary |
| Savepoints | Not exposed by this implementation | Explicit `uow.savepoint()` helper | Not exposed by the service API | SQLAlchemy `session.begin_nested()` is available when actually needed |
| Inventory protection | Order reads stock without a row lock | `SELECT FOR UPDATE` | `SELECT FOR UPDATE` | Row lock plus refresh of previously loaded stock |
| Complexity | Repeated UoW subclasses and repository wiring | Depth counter, rollback-only state, owner task, backend hooks, lazy composition root, ports | Small, but commit/rollback responsibility is distributed | Small, with one visible transaction policy |

Module 1 is a valid pattern, but this implementation needs concurrency hardening
and must not compose independently entered UoWs as though they shared a session.
Its commit methods also silently do nothing if no session exists. Its order code
uses the request's `amount` for the total, whereas modules 2 and 3 use the stored
product price.

Module 2's extra code has a purpose: it supplies Spring-like transaction
propagation, including rollback-only behavior and an explicit savepoint API. Use
that approach if those semantics are a real application requirement, and test the
state machine thoroughly. It is not automatically more production-ready merely
because it has more abstractions. Its protocols also do not turn a later HTTP call
to another microservice into part of the local PostgreSQL transaction.

Original module 3 already worked for the current order path when every
`commit=False` was correct. Its failure mode was maintenance: forgetting a flag
would permanently reduce stock before a later order/email failure. Rolling back
after that early commit cannot undo the completed transaction.

Revised module 3 chooses caller-owned transactions instead of re-entrant
transaction propagation. This is an architectural choice, not a universal ranking
of UoW patterns. A large application can also use a simple explicit UoW abstraction
without adopting module 2's full propagation machinery.

## Changes made, all inside `src/module_v3`

- `db.py`: one transaction around each operation, function-scoped dependency,
  explicit transaction requirement, and context-managed cleanup.
- All service/route wiring: removed `commit` flags and direct commit/rollback calls.
  Services receive repositories rather than an additional session used to commit.
- Product locked reads: flush pending changes and refresh the session's existing
  product instance from the locked row.
- Product reservation: reject nonpositive quantities for direct service callers.
- User creation: translate the PostgreSQL `users_email_key` uniqueness race into
  HTTP 409; unrelated integrity errors still propagate.
- Order lookup: return HTTP 404 instead of returning `None` to a required response
  model and causing response validation to fail.
- `main.py`: v3-only application with engine disposal on shutdown.
- `tests/test_transactions.py`: PostgreSQL integration tests using disposable
  schemas. No test framework or HTTP-client dependency was added.

No table definition was changed, so these edits require no new database migration.

## `db.py`, line by line

Line numbers below refer to the final code accompanying this guide.

### Imports and base, lines 1–16

- **1, `Annotated`**: lets one type carry FastAPI dependency metadata. It will let
  repositories request a session using the short name `SessionDep`.
- **1, `Any`**: types SQLAlchemy mapper configuration values.
- **1, `AsyncGenerator`**: describes a dependency that yields a session and later
  resumes for cleanup. It does not create a database transaction by itself.
- **3, `Depends`**: tells FastAPI how to resolve and cache the dependency.
- **4–9**: import the engine type, session type, session factory, and engine factory.
  Importing their names does not open a database connection.
- **10, `DeclarativeBase`**: supplies the ORM mapping base used by this variant.
- **12**: imports the configured database URL. It comes from the shared settings.
- **15**: gives v3 its own ORM metadata, allowing these demo variants to map the
  same table names without redefining tables inside one metadata object.
- **16, `eager_defaults=True`**: asks SQLAlchemy to load generated defaults eagerly
  during persistence. PostgreSQL `RETURNING` can supply generated timestamps
  without requiring later implicit async I/O. This is about available object
  attributes, not transaction durability.

### Engine, lines 19–23

```python
engine: AsyncEngine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)
```

- **19** creates the process-level engine and connection pool configuration.
  The engine is shared; an individual session is not. Engine construction is
  normally lazy about opening actual database connections.
- **20** chooses the database and async driver from configuration.
- **21** disables SQL echo output. This avoids printing every SQL statement and
  its parameters during ordinary operation.
- **22** checks pooled connections when checked out so stale idle connections can
  be replaced. It cannot recover a transaction interrupted halfway through.
- **23** closes the factory call; no transaction has been opened by this line.

### Session factory, lines 25–31

```python
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autobegin=False,
    expire_on_commit=False,
)
```

- **25** creates a reusable factory, not a singleton session. Calling this factory
  later creates a fresh session for one operation.
- **26** associates each created session with this engine.
- **27** selects SQLAlchemy's async session implementation.
- **28, `autoflush=False`** prevents many query-triggered automatic flushes.
  Explicit `flush()` calls still work, and commit still flushes pending changes.
  A database query might not see new in-memory objects until an explicit flush.
- **29, `autobegin=False`** requires a deliberate transaction boundary. Database
  work outside `session.begin()` raises rather than silently opening another
  transaction. This makes forgotten boundaries in scripts/workers easier to catch.
- **30, `expire_on_commit=False`** keeps loaded attributes available after commit.
  It does not reload the object, keep it fresh forever, or make unloaded
  relationships safe after close. Rollback has different expiration behavior.
- **31** finishes factory configuration.

### Transaction owner, lines 34–38

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """One session and transaction per API operation; shared by all repositories."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
```

- **34** declares FastAPI's async yield dependency. `get_db` is the factory
  callable FastAPI caches within this operation. Different requests get different
  executions and different sessions.
- **35** states its ownership contract.
- **36** creates a new session and enters its lifetime context. On exit, SQLAlchemy
  closes the session and releases its connection. We no longer duplicate that
  close in a separate `finally` block.
- **37** enters the transaction context before any repository is used. The ORM
  transaction exists at this point; database connection checkout and a physical
  database transaction occur as needed when SQL runs. On normal exit, the context
  flushes outstanding changes and commits. On an exception, it rolls back. If
  commit itself fails before completion, SQLAlchemy attempts rollback and cleanup.
- **38** hands the same session to dependency consumers and suspends this
  generator while the endpoint runs. It is not the end of the function. FastAPI
  resumes or unwinds it later, which exits the transaction and session contexts.

The nesting order matters: **finish the transaction first, then close the session**.
The context managers also handle an escaping `CancelledError`, which is a
`BaseException`, not an `Exception`. Cancellation during an in-flight commit can
still leave the client uncertain about whether the database committed; see the
retry discussion below.

### Dependency alias, lines 41–43

```python
SessionDep = Annotated[AsyncSession, Depends(get_db, scope="function")]
```

- `SessionDep` is a type alias carrying dependency metadata. It is neither a
  global session nor an extra wrapper around the session.
- `AsyncSession` is the value the receiving function gets.
- `Depends(get_db, ...)` selects this dependency callable.
- `scope="function"` makes its exit run before FastAPI sends the response. With
  the installed FastAPI version, ordinary response validation/serialization also
  happens before this dependency exits. A failure there unwinds the transaction.
- Dependency caching stays enabled by default. Every repository asking for the
  same `SessionDep` in this operation receives the same session object. Do not
  replace it with independent factories or `use_cache=False`.
- A default request-scoped yield dependency can clean up after response delivery.
  Moving commit there without selecting function scope could report success
  before learning that commit failed. The integration test checks the actual
  order: commit, close, response start.

## Where the shared session comes from

In `order/route.py`, lines 23–26:

```python
def get_order_repo(session: SessionDep) -> OrderRepository:
    return SqlAlchemyOrderRepository(session)
```

The parameter requests the already defined dependency. The constructor stores a
reference to that object; it does not copy it or create another transaction.
User, product, and email repository factories request the identical alias.

Lines 29–40 build the order service using those repository-backed services. No
service constructor opens a transaction. No depth counter is necessary because
none of the inner methods is trying to own the transaction.

Lines 43–48 validate the order request and call the service. `201` describes the
intended success response; it does not make the database durable. Even after this
endpoint returns its result, the function-scoped dependency must successfully
commit and close before the response is sent.

The resulting object references are:

```text
get_db: session S, transaction T
    order repository   -> S
    user repository    -> S
    product repository -> S
    email repository   -> S
```

Sharing an engine or database URL would not be enough: two separate sessions
normally have separate transactions.

## `OrderService.create_order`, lines 27–45

- **27** begins the application operation. Calling it does not itself begin or
  commit a transaction; the caller must supply the active boundary.
- **28** documents that contract.
- **29** verifies the user using session S. A missing user raises HTTP 404. That
  exception escapes to the boundary, which rolls back and closes.
- **30–33** calls stock reservation with the same session S. It acquires the
  product row lock and changes the tracked stock attribute. No inner commit
  releases the lock or makes the stock change permanent.
- **34–41** constructs and adds the order using the stored product price. The
  repository's `flush()` writes pending stock/order changes in transaction T and
  obtains the order ID. The generated ID is available before commit.
- **42–44** creates an email record using that order ID. Its repository flushes
  the email in transaction T. This queues intent to send an email; no email is
  transmitted by this method.
- **45** returns the order object to the endpoint. This is not a commit. The
  dependency's successful exit commits stock, order, and email together.

There is no service-level `try/except` rollback block anymore because rollback is
owned by the surrounding transaction context. Errors must propagate out of this
operation when they should abort the transaction.

## Why `flush()` does not break atomicity

For example, `order/repository.py`, lines 20–23:

```python
async def add(self, order: Order) -> Order:
    self.session.add(order)
    await self.session.flush()
    return order
```

- `add()` attaches the new object to the session. It does not immediately commit
  an SQL insert.
- `flush()` emits SQL for the session's pending changes. It is **session-wide**,
  not restricted to this one repository. The previously changed stock can be
  updated by the same flush that inserts the order.
- A successful flush checks immediate database constraints and populates values
  such as the generated primary key. Later SQL in the same transaction can use
  the inserted row.
- The data remains uncommitted. Other transactions normally cannot read these
  new values at PostgreSQL's default READ COMMITTED isolation level, though they
  may wait on locks or constraints involving the uncommitted writes.
- `return order` returns a Python object, not a committed database record.

Suppose stock is 5 and the requested quantity is 2:

| Point | This transaction | Committed outcome |
| --- | --- | --- |
| Before operation | Stock 5, no new order/email | Stock 5, no new order/email |
| After stock/order flush | Stock 3 and a new order | Previous committed values |
| After email flush | Stock 3, new order and PENDING email | Previous committed values |
| Successful commit | Transaction complete | Stock 3, order and email all saved |
| Failure before commit | Transaction rolled back | Stock 5, neither new record saved |

An ID existing in Python is not proof of a committed order. Commit can also fail
after successful flushes, for example because of deferred constraints.

## Stock locking, explained at the transaction boundary

`products/repository.py`, lines 24–34:

```python
async def get_for_update(self, product_id: UUID) -> Product | None:
    await self.session.flush()
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

- The initial flush preserves pending changes before a refresh can overwrite
  them. This matters if one operation reserves the same product twice with
  `autoflush=False`. It still does not commit.
- `select(Product)` loads the ORM row; `where(...)` selects this product.
- `with_for_update()` adds a database row lock. Competing updates/locking reads
  wait until this transaction commits or rolls back. Ordinary reads are not
  blocked just because the row is locked.
- `populate_existing=True` refreshes an already cached ORM object using the
  locked query result. Without it, SQLAlchemy's identity map can preserve old
  stock attributes even though the query acquired a lock.
- `execute()` runs this SQL through session S and transaction T.
- `scalar_one_or_none()` returns the mapped product or `None`. Merely returning
  from this method does not release the lock.

`products/service.py`, lines 33–56, rejects a nonpositive quantity, obtains the
locked product, rejects a missing product or insufficient stock, and deducts
`count` from the tracked object. The lock is held through order/email creation
until the outer transaction ends.

For two buyers and one remaining item, the first transaction locks the row and
reduces stock to zero. The second waits. Once the first commits, the second's
locked read sees zero and fails the stock check. If the first instead rolls back,
the second can still buy the item. A transaction alone, without locking or an
equivalent atomic conditional update, would not solve the read-modify-write race.

This description assumes the configured/default PostgreSQL isolation behavior.
Stricter isolation can raise serialization errors requiring a complete operation
retry. All inventory-writing paths must follow a compatible concurrency policy.

## Failure rules and how they differ from module 2

Raise required-step errors so the boundary can observe them. Do not catch an
email-queue failure and then return success if that record is required to be part
of the order.

Unlike module 2, revised v3 does not mark a transaction rollback-only because an
ordinary Python exception happened and was caught inside the operation. If such
an exception is swallowed, normal exit can commit. A database flush failure may
instead leave the transaction unusable until rollback. Do not attempt to continue
using that failed transaction as though nothing happened.

When an optional operation genuinely needs independent failure handling, use a
deliberate SQLAlchemy savepoint inside the outer transaction and catch its error
outside the savepoint block. `begin_nested()` is a SAVEPOINT, not an independent
durable commit; it can also flush pending state on entry. None of the current
order steps is optional, so no savepoint was added.

Returning a response with an error status is not the same as raising an error.
The transaction context sees exceptions, not HTTP status numbers. Raise
`HTTPException` for aborting failures, as the current services do.

Do not add `if session.in_transaction(): yield session` as a generic transaction
joining helper. An automatically started transaction is not evidence of another
application operation safely owning it. This version avoids that ambiguity by
disabling autobegin and creating the boundary explicitly.

## Using services from a background job or script

FastAPI dependency injection does not run when a worker directly calls a service.
The worker must construct all participants from the same session and open its own
boundary:

```python
from src.module_v3.db import AsyncSessionLocal
from src.module_v3.email.repository import SqlAlchemyEmailRepository
from src.module_v3.email.service import EmailService
from src.module_v3.order.repository import SqlAlchemyOrderRepository
from src.module_v3.order.service import OrderService
from src.module_v3.products.repository import SqlAlchemyProductRepository
from src.module_v3.products.service import ProductService
from src.module_v3.user.repository import SqlAlchemyUserRepository
from src.module_v3.user.service import UserService

async def place_order(data):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            service = OrderService(
                order_repo=SqlAlchemyOrderRepository(session),
                user_service=UserService(SqlAlchemyUserRepository(session)),
                product_service=ProductService(SqlAlchemyProductRepository(session)),
                email_service=EmailService(SqlAlchemyEmailRepository(session)),
            )
            order = await service.create_order(data)
        # Commit has succeeded here. The session closes on leaving the outer block.
        return order
```

Several operations inside that same `session.begin()` share its transaction.
Do not open `session.begin()` again inside a participating service; it is not a
re-entrant context. Do not use `asyncio.gather()` for these service calls on the
same session. An AsyncSession is mutable transaction state and must not be used
concurrently by different tasks. Separate independent jobs need separate sessions
and do not share an atomic transaction.

## Email delivery and production scope

`send_email()` currently persists a PENDING row. The method name does not mean
SMTP or an email-provider API was called. PostgreSQL can roll back that row; it
cannot unsend a network-delivered email. Keep actual delivery outside this
transaction, using a worker that reads committed pending intent.

The email table is a useful starting point for an outbox, but a complete worker
still needs safe claiming, retries, duplicate-delivery handling, and observability.
A process-local after-commit callback alone is insufficient: the process could
crash after commit and before the callback sends anything.

These edits harden the transaction implementation, not certify the whole demo as
a complete production application. Before deployment:

- Add authentication and authorization, including checks that an authenticated
  user may access the requested user/order/email data.
- Choose one variant. The existing `src/main.py` exposes v1 and v3 over the
  same tables. Running the unprotected v1 inventory path would undermine a
  consistent stock policy. The new v3 entry point avoids those routes.
- Align Alembic's authoritative metadata before changing v3 models. Currently
  `alembic/env.py` imports v1 metadata. These edits changed no table definitions.
- Add database check constraints for stock/quantity/price rules through the
  authoritative migration path, not only Pydantic validation. Size pool limits
  and database timeouts for the number of workers and database capacity.
- Add order idempotency and a deliberate retry policy. If PostgreSQL commits but
  the response or commit acknowledgement is lost, the caller may not know the
  outcome. Blindly retrying can create another order. A rollback cannot reverse
  a transaction that already committed.
- Keep transactions short; avoid network calls while holding inventory locks.
  Use stable row ordering if later operations lock several products to reduce
  deadlocks. Decide how lock timeouts/deadlocks are reported and retried.
- Define whether integer prices represent minor currency units, and bound
  quantities/totals to fit the actual database column types.

The unique-email translation relies on PostgreSQL's existing default constraint
name `users_email_key`, which matches the supplied migration and test schema. If
that constraint is renamed, update the translation with the migration.

The engine is disposed in the new v3 app's lifespan on shutdown. Sessions are
still closed separately after every operation. Engine disposal is pool-level
cleanup, not a substitute for per-operation transaction cleanup.

## Run and verification

With application configuration and the existing migrations applied:

```bash
uv run uvicorn src.module_v3.main:app --reload
```

`--reload` is for local development. The API routes remain under `/v3`.

For integration tests, use a disposable PostgreSQL database URL, never a
production database:

```bash
MODULE_V3_TEST_DATABASE_URL='postgresql+asyncpg://USER:PASSWORD@HOST:PORT/TEST_DB' \
  .venv/bin/python -m unittest discover -s src/module_v3/tests -v
```

The test database user needs permission to create/drop schemas. Each test creates
a randomly named schema, uses it for all test tables, and drops only that schema.
No test queries use the application's configured database URL. Fourteen tests
passed against a disposable PostgreSQL 18 container during this review:

- All repositories share one active session.
- Successful order commits once, closes, then starts the success response.
- Failure after all writes flush rolls back stock, order, and email.
- A real FK/flush error rolls back the preceding stock and order writes.
- A failure injected before commit cannot send HTTP 201.
- Escaping cancellation rolls back and closes.
- Concurrent buyers cannot both buy the last item.
- A locked query refreshes previously loaded stock.
- Repeated reservations retain pending changes.
- Direct service calls reject zero/negative quantities.
- Queries outside an explicit boundary fail instead of implicitly beginning.
- Standalone user, product, and email routes persist successfully.
- Concurrent duplicate signups produce one HTTP 201 and one HTTP 409.
- Missing order lookup returns HTTP 404.

The injected pre-commit failure test does not simulate a network-disconnected,
unknown commit outcome; order idempotency remains required for that case.

## Primary references

- [SQLAlchemy 2.1 session basics](https://docs.sqlalchemy.org/en/21/orm/session_basics.html)
  for flush, transaction boundaries, autobegin, and expiration.
- [SQLAlchemy 2.1 transactions](https://docs.sqlalchemy.org/en/21/orm/session_transaction.html)
  for transaction contexts and savepoints.
- [SQLAlchemy async sessions](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html#using-asyncsession-with-concurrent-tasks)
  for task ownership and async attribute-loading constraints.
- [FastAPI yield dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#early-exit-and-scope)
  for function-scoped teardown before response delivery.
- [PostgreSQL row locks](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-ROWS)
  for `FOR UPDATE` and lock lifetime.
