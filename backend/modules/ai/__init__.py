"""
AI Modules - Analytics, Cognitive Processing, ML

Uses try/except for each import because some modules depend on heavy
ML packages (sentence-transformers, spacy, neo4j) that may not be
installed in lightweight CI environments.
"""

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
    pass

try:
    from . import cache_manager
except ImportError:
    pass

try:
    from . import cognitive_graph
except ImportError:
    pass

try:
    from . import entity_extraction
except ImportError:
    pass

try:
    from . import performance_analyzer
except ImportError:
    pass

try:
    from . import predictive_interview
except ImportError:
    pass

try:
    from . import realtime_suggestions
except ImportError:
    pass

try:
    from . import study_plan_generator
except ImportError:
    pass