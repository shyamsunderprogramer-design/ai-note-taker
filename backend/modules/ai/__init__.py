"""
AI Modules - Analytics, Cognitive Processing, ML

Uses try/except for each import because some modules depend on heavy
ML packages (sentence-transformers, spacy, neo4j) that may not be
installed in lightweight CI environments.
"""

import logging

logger = logging.getLogger(__name__)

__all__ = [
    "analytics_engine",
    "cache_manager",
    "cognitive_graph",
    "entity_extraction",
    "performance_analyzer",
    "predictive_interview",
    "realtime_suggestions",
    "study_plan_generator",
]

try:
    from . import analytics_engine
except ImportError:
    logger.debug("Optional AI module unavailable: analytics_engine")

try:
    from . import cache_manager
except ImportError:
    logger.debug("Optional AI module unavailable: cache_manager")

try:
    from . import cognitive_graph
except ImportError:
    logger.debug("Optional AI module unavailable: cognitive_graph")

try:
    from . import entity_extraction
except ImportError:
    logger.debug("Optional AI module unavailable: entity_extraction")

try:
    from . import performance_analyzer
except ImportError:
    logger.debug("Optional AI module unavailable: performance_analyzer")

try:
    from . import predictive_interview
except ImportError:
    logger.debug("Optional AI module unavailable: predictive_interview")

try:
    from . import realtime_suggestions
except ImportError:
    logger.debug("Optional AI module unavailable: realtime_suggestions")

try:
    from . import study_plan_generator
except ImportError:
    logger.debug("Optional AI module unavailable: study_plan_generator")