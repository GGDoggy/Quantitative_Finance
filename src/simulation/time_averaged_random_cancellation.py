"""Public interface for the time-averaged random-cancellation simulation algorithm."""

from ._simulation_core import simulate_virtual_best_orders


ALGORITHM_NAME = "time_averaged_random_cancellation"

__all__ = ["ALGORITHM_NAME", "simulate_virtual_best_orders"]
