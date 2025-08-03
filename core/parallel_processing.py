import concurrent.futures
from typing import Dict, List, Callable
from config.settings import Settings
from utilities.error_handler import log_error

class ParallelProcessor:
    """Handles parallel execution with resource monitoring"""
    
    def __init__(self):
        self.max_workers = Settings.PARALLEL_WORKERS
        
    def process_batch(
        self,
        tasks: List[Dict],
        process_func: Callable,
        timeout: int = 300
    ) -> Dict:
        """
        Process tasks in parallel with:
        - Timeout protection
        - Error isolation
        - Resource monitoring
        """
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            future_to_id = {
                executor.submit(
                    self._safe_execute,
                    process_func,
                    task
                ): task.get('id') 
                for task in tasks
            }
            
            for future in concurrent.futures.as_completed(
                future_to_id,
                timeout=timeout
            ):
                task_id = future_to_id[future]
                try:
                    results[task_id] = future.result()
                except Exception as e:
                    results[task_id] = None
                    log_error(f"Parallel task failed: {str(e)}")
                    
        return results
    
    def _safe_execute(self, func, task):
        """Wrapper with resource limits"""
        import resource
        # Set 1GB memory limit (Linux/Mac only)
        resource.setrlimit(
            resource.RLIMIT_AS,
            (Settings.MAX_MEMORY, resource.RLIM_INFINITY)
        )
        return func(task)