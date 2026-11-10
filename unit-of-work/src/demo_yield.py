import logging
from typing import Annotated, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger("yield_demo")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] [YIELD-DEMO] %(message)s"
)

demo_router = APIRouter(prefix="/demo-yield", tags=["Yield Dependencies Demo"])


# -------------------------------------------------------------------------
# 2. FUNCTION-SCOPED DEPENDENCY (scope="function")
# -------------------------------------------------------------------------
async def get_db_function_scope() -> AsyncGenerator[str, None]:
    logger.info("👉 [1. FUNC-SCOPE] BEFORE yield: Opening database session S1...")
    session = "Session-Func-Scope-101"
    try:
        # Code yields session to the route handler
        yield session
        # TEARDOWN: Runs immediately after route returns, BEFORE response is sent!
        logger.info(
            "👉 [4. FUNC-SCOPE] AFTER yield: Committing transaction on S1 (Runs BEFORE response delivery)..."
        )
    except Exception as exc:
        logger.error(f"❌ [FUNC-SCOPE] Exception occurred: {exc}. Rolling back S1...")
        raise
    finally:
        logger.info("👉 [5. FUNC-SCOPE] FINALLY: Closing database session S1.")


# -------------------------------------------------------------------------
# 2. REQUEST-SCOPED DEPENDENCY (scope="request" or default)
# -------------------------------------------------------------------------
async def get_db_request_scope() -> AsyncGenerator[str, None]:
    logger.info("👉 [1. REQ-SCOPE] BEFORE yield: Opening database session S2...")
    session = "Session-Req-Scope-202"
    try:
        # Code yields session to the route handler
        yield session
        # TEARDOWN: Runs AFTER response has ALREADY been sent to client!
        logger.info(
            "👉 [4. REQ-SCOPE] AFTER yield: Committing transaction on S2 (Runs AFTER response was sent!)..."
        )
    except Exception as exc:
        logger.error(f"❌ [REQ-SCOPE] Exception occurred: {exc}. Rolling back S2...")
        raise
    finally:
        logger.info("👉 [5. REQ-SCOPE] FINALLY: Closing database session S2.")


# -------------------------------------------------------------------------
# 3. FAILING FUNCTION-SCOPED (to show client gets HTTP 500)
# -------------------------------------------------------------------------
async def get_db_func_fail() -> AsyncGenerator[str, None]:
    logger.info("👉 [FUNC-FAIL] BEFORE yield: Opening session...")
    try:
        yield "Session-Func-Fail"
        logger.info("👉 [FUNC-FAIL] AFTER yield: Database commit starting...")
        raise RuntimeError("IntegrityError: Unique constraint violated on commit!")
    except Exception as exc:
        logger.error(f"❌ [FUNC-FAIL] Database commit failed: {exc}. Rolling back...")
        raise
    finally:
        logger.info("👉 [FUNC-FAIL] FINALLY: Session closed.")


# -------------------------------------------------------------------------
# 4. FAILING REQUEST-SCOPED (to show client falsely gets HTTP 200)
# -------------------------------------------------------------------------
async def get_db_req_fail() -> AsyncGenerator[str, None]:
    logger.info("👉 [REQ-FAIL] BEFORE yield: Opening session...")
    try:
        yield "Session-Req-Fail"
        logger.info(
            "👉 [REQ-FAIL] AFTER yield: Database commit starting (CLIENT ALREADY GOT 200 OK!)..."
        )
        raise RuntimeError("IntegrityError: Unique constraint violated on commit!")
    except Exception as exc:
        logger.error(f"❌ [REQ-FAIL] Database commit failed: {exc}. Rolling back...")
        raise
    finally:
        logger.info("👉 [REQ-FAIL] FINALLY: Session closed.")


# ENDPOINTS
@demo_router.get("/function-scope")
async def demo_function_scope(
    session: Annotated[str, Depends(get_db_function_scope, scope="function")],
):
    logger.info(f"⚡ [2. ROUTE] Executing route logic using {session}")
    logger.info("⚡ [3. ROUTE] Route finished; returning response dict.")
    return {
        "scope": "function",
        "session": session,
        "note": "Commit & Close executed BEFORE response was sent to client.",
    }


@demo_router.get("/request-scope")
async def demo_request_scope(
    session: Annotated[str, Depends(get_db_request_scope, scope="request")],
):
    logger.info(f"⚡ [2. ROUTE] Executing route logic using {session}")
    logger.info("⚡ [3. ROUTE] Route finished; returning response dict.")
    return {
        "scope": "request",
        "session": session,
        "note": "Response was sent to client BEFORE commit & close executed!",
    }


@demo_router.get("/fail-function-scope")
async def demo_fail_function_scope(
    session: Annotated[str, Depends(get_db_func_fail, scope="function")],
):
    logger.info("⚡ [ROUTE] Route finished successfully.")
    return {
        "message": "You will never see this because commit fails in function scope!"
    }


@demo_router.get("/fail-request-scope")
async def demo_fail_request_scope(
    session: Annotated[str, Depends(get_db_req_fail, scope="request")],
):
    logger.info(
        "⚡ [ROUTE] Route finished successfully. Client receives this 200 OK even though DB commit fails after!"
    )
    return {
        "warning": "Client received 200 OK, but check terminal logs: DB commit crashed afterwards!"
    }
