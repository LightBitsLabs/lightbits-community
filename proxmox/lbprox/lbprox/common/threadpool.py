import concurrent.futures
import time
import logging



def run_with_threadpool(func, args, desc, max_workers=10):
    start = time.time()
    logging.info("starting concurrent job: %s", desc)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, *arg): arg for arg in args}

        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
    elapsed = time.time() - start
    logging.info("done concurrent job: %s - [took: %s]", desc, elapsed)
    return results
