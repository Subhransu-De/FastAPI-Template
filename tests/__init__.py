import sys

if sys.platform == "win32":
    import asyncio

    # Use the selector loop on Windows for async DB and HTTP client test stability.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
