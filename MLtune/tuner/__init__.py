"""
FRC Shooter Bayesian Tuner

MLtune
Copyright (C) 2025 Ruthie-FRC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

------------------------------------------------------

A Driver Station-only Bayesian optimization tuner for the FiringSolutionSolver.
Automatically tunes shooting coefficients based on shot hit/miss feedback.

Usage:
    from bayesopt.tuner import run_tuner
    
    # Run with default config
    run_tuner()
    
    # Or with custom server IP
    run_tuner(server_ip="10.12.34.2")
"""

__version__ = "1.0.0"

from .config import TunerConfig, CoefficientConfig
from .tuner import BayesianTunerCoordinator, run_tuner
from .nt_interface import NetworkTablesInterface, ShotData
from .optimizer import BayesianOptimizer, CoefficientTuner
from .logger import TunerLogger, setup_logging

__all__ = [
    'TunerConfig',
    'CoefficientConfig',
    'BayesianTunerCoordinator',
    'run_tuner',
    'NetworkTablesInterface',
    'ShotData',
    'BayesianOptimizer',
    'CoefficientTuner',
    'TunerLogger',
    'setup_logging',
]
