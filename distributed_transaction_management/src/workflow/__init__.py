"""Workflow package initializer

This file makes the `src/workflow` directory a Python package so it can be
imported as `workflow` (e.g. `from workflow.manager import ...`).
"""

from .manager import SagaWorkflowManager, Activity  # re-export common symbols

__all__ = ["SagaWorkflowManager", "Activity"]
