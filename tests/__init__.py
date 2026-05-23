import sys

if sys.platform == "win32":
    import asyncio

    # Use the selector loop on Windows for async DB and HTTP client test stability.
    event_loop_policy_setter = "set_event_loop_policy"
    set_event_loop_policy = getattr(asyncio, event_loop_policy_setter)
    set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
