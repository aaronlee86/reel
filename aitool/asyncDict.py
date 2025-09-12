import asyncio
import json
import importlib
from typing import Any, Dict, List, Optional, Union, Callable
import sys
import signal
import ast

try:
    import aiofiles
except ImportError:
    aiofiles = None

class Status:
    LOADING = "Loading..."
    READY = "ready"

class AsyncDictionaryManager:
    def __init__(
        self,
        refill_func: Callable[[str], Any],
        threshold: int = 1
    ):
        """
        Initialize the Async Dictionary Manager

        :param json_path: Path to the JSON file storing the dictionary
        :param refill_func: Async function or string path to the function (module.submodule.function)
        :param threshold: Minimum number of items in array before refilling
        """
        self._refill_func = refill_func
        self._threshold = threshold
        self._data: Dict[str, List[Any]] = {}
        self._lock = asyncio.Lock()
        self._json_path = "_func_cache/" + refill_func.__name__ + ".json"
        self._refilling: Dict[str, bool] = {}  # Track refilling status per key
        self._flush_event = asyncio.Event()

        # Load initial data from JSON
        self._load_from_json()

        # Set up exit handlers
        self._setup_exit_handlers()

    def _load_from_json(self):
        """Load dictionary from JSON file synchronously during initialization"""
        try:
            with open(self._json_path, 'r') as f:
                self._data = json.load(f)
        except FileNotFoundError:
            self._data = {}
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {self._json_path}. Starting with empty dictionary.")
            self._data = {}

    def _setup_exit_handlers(self):
        """
        Set up handlers to ensure data is flushed on program exit
        """
        # For normal Python exit
        import atexit
        atexit.register(self._sync_final_flush)

        # For asyncio event loop
        try:
            loop = asyncio.get_event_loop()

            # Add signal handlers for graceful shutdown
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._async_final_flush(s))
                )
        except Exception as e:
            print(f"Error setting up exit handlers: {e}")

    async def get(self, *args) -> List[Any]:
        """
        Get an item from the dictionary

        :param key: Key to retrieve
        :return: Dictionary with value and status, or None
        """
        async with self._lock:
            # If key doesn't exist or array is empty, trigger background refill
            key = str(args)
            if len(self._data.get(key, [])) == 0:
                if not self._refilling.get(key, False):
                    print(f"Triggering background refill for key: {key}")
                    self._refilling[key] = True
                    asyncio.create_task(self._refill(key))

                return {"status": Status.LOADING}

            # Pop the first item from the array
            value = self._data[key].pop(0)

            # Check if we need to refill
            if len(self._data[key]) < self._threshold:
                if not self._refilling.get(key, False):
                    print(f"Threshold reached for key: {key}. Triggering background refill.")
                    self._refilling[key] = True
                    asyncio.create_task(self._refill(key))

            return {
                "status": Status.READY,
                "value": value
            }

    async def _refill(self, key: str):
        """
        Refill the dictionary for a specific key in the background

        :param key: Key to refill
        """
        try:
            # Call the user-provided refill function
            new_values = await asyncio.to_thread(self._refill_func, *ast.literal_eval(key))

            # If new values are returned, add them to the dictionary
            async with self._lock:
                if new_values:
                    if key not in self._data:
                        self._data[key] = []

                    # Extend the existing list
                    self._data[key].extend(new_values)

        except Exception as e:
            print(f"Refill failed for key {key}: {e}")
        finally:
            async with self._lock:
                self._refilling[key] = False

    def _sync_final_flush(self):
        """
        Synchronous final flush method for atexit
        """
        try:
            with open(self._json_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            print(f"Final sync flush to {self._json_path}")
        except Exception as e:
            print(f"Error in final sync flush: {e}")

    async def _async_final_flush(self, sig=None):
        """
        Async final flush method for signal handling
        """
        try:
            async with self._lock:
                # Prefer aiofiles for non-blocking file I/O if available
                if aiofiles:
                    async with aiofiles.open(self._json_path, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(self._data, indent=2, ensure_ascii=False))
                else:
                    # Fallback to standard library method
                    with open(self._json_path, 'w', encoding='utf-8') as f:
                        json.dump(self._data, f, indent=2, ensure_ascii=False)

                print(f"Final async flush to {self._json_path}")

                # Signal flush completion
                self._flush_event.set()
        except Exception as e:
            print(f"Error in final async flush: {e}")

        # If called due to signal, exit the program
        if sig is not None:
            sys.exit(0)

def load_refill_func(refill_func: str) -> Callable[[str], Any]:
        """
        Load refill function dynamically if a string path is provided

        :param refill_func: Function or string path to the function
        :return: Callable refill function
        """

        try:
            # Split the string into module path and function name
            module_path, func_name = refill_func.rsplit('.', 1)

            # Import the module
            module = importlib.import_module(module_path)

            # Get the function from the module
            func = getattr(module, func_name)

            return func
        except (ImportError, AttributeError, ValueError) as e:
            raise ValueError(f"Could not load refill function {refill_func}: {e}")

async def main():
    func1 = load_refill_func('module1.is_prime')
    manager = AsyncDictionaryManager(
        refill_func=func1,
        threshold=4
    )

    # Simulate concurrent gets
    print("Starting concurrent gets")

    key1 = 0
    key2 = 1
    count = 0
    while True:
        result = await manager.get(0)
        if count % 1000 == 0:
            print(f"count={count}")
        count += 1

        if result["status"] == Status.LOADING:
            print("key1 loading")
        else:
            assert(result['value']==key1)
            key1+=1
            if key1 == 10:
                key1 = 0

        result = await manager.get(1)
        if result["status"] == Status.LOADING:
            print("key2 loading")
        else:
            assert(result['value']==key2)
            key2+=1
            if key2 == 11:
                key2 = 1
        await asyncio.sleep(0.000000001)


if __name__ == '__main__':
    asyncio.run(main())