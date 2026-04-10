"""
AI Modules - Analytics, Cognitive Processing, ML

Uses try/except for each import because some modules depend on heavy
ML packages (sentence-transformers, spacy, neo4j) that may not be
installed in lightweight CI environments.
"""

try:
    from .analytics_engine import *
except ImportError:
    pass

try:
    from .cache_manager import *
except ImportError:
    pass

try:
    from .cognitive_graph import *
except ImportError:
    pass

try:
    from .entity_extraction import *
except ImportError:
    pass

try:
    from .performance_analyzer import *
except ImportError:
    pass

try:
    from .predictive_interview import *
except ImportError:
    pass

try:
    from .realtime_suggestions import *
except ImportError:
    pass

try:
    from .study_plan_generator import *
except ImportError:
    pass