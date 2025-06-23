from __future__ import annotations
import os
import multiprocessing as mp
from typing import Callable, Iterable, Any


def run_parallel(
    func: Callable,
    inputs: Iterable[Any],
    use_multiprocessing: bool = True,
    processes: int = None,
    start_method: str = "spawn",
    mode: str = "default"  # "default", "unpack_args", or "kwargs"
) -> list:
    """
    Runs a function in parallel or serial mode.

    Args:
        func: The function to run (must be top-level, pickleable).
        inputs: List of inputs to pass to func.
        use_multiprocessing: Whether to use multiprocessing.
        processes: Number of worker processes.
        start_method: Multiprocessing start method ('spawn', 'fork', 'forkserver').
        mode: 'default' (single arg), 'unpack_args' (tuple -> *args), 'kwargs' (dict -> **kwargs).

    Returns:
        List of results.
    """

    if mode not in {"default", "unpack_args", "kwargs"}:
        raise ValueError("Invalid mode. Use 'default', 'unpack_args', or 'kwargs'.")

    if use_multiprocessing:
        processes = resolve_num_processes(processes)
        ctx = mp.get_context(start_method)
        with ctx.Pool(processes=processes) as pool:
            if mode == "unpack_args":
                return pool.map(_wrapper_unpack_args, [(func, args) for args in inputs])
            elif mode == "kwargs":
                return pool.map(_wrapper_kwargs, [(func, kwargs) for kwargs in inputs])
            else:
                return pool.map(func, inputs)
    else:
        if mode == "unpack_args":
            return [func(*args) for args in inputs]
        elif mode == "kwargs":
            return [func(**kwargs) for kwargs in inputs]
        else:
            return [func(arg) for arg in inputs]

def _wrapper_unpack_args(args: tuple) -> Any:
    func, func_args = args
    return func(*func_args)

def _wrapper_kwargs(args: tuple) -> Any:
    func, func_kwargs = args
    return func(**func_kwargs)

def resolve_num_processes(requested: int | None) -> int: # For python > 3.9
    cpu_total = os.cpu_count() or 1  # Fallback in case cpu_count() returns None

    if requested is None or requested == 0:
        return cpu_total
    elif requested < 0:
        return max(1, cpu_total + requested)
    else:
        return max(1, requested)
# import multiprocessing as mp

# from utils.logger import logger
# from typing import Callable, Dict, Iterable, Any
# 
# def default_wrapper(fn: Callable, kwargs: Dict) -> Any:
#     return fn(**kwargs)
# 
# def run_parallel(
#     func: Callable,
#     inputs: Iterable[Any],
#     use_multiprocessing: bool = True,
#     processes: int = None,
#     start_method: str = 'spawn',
#     wrap_kwargs: bool = False,
#     unpack_args: bool = False,
# ):
#     if unpack_args and wrap_kwargs:
#         raise ValueError("Cannot use both unpack_args and wrap_kwargs")
# 
#     if wrap_kwargs:
#         def wrapped_func(kwargs): return func(**kwargs)
#     elif unpack_args:
#         def wrapped_func(args): return func(*args)
#     else:
#         wrapped_func = func
#     
#     if use_multiprocessing:
#         ctx = mp.get_context(start_method)
#         with ctx.Pool(processes=processes) as pool:
#             return pool.map(wrapped_func, inputs)
#     else:
#         return [wrapped_func(inp) for inp in inputs]