"""Exercise the route's actual optional-import block without starting servers."""
import ast
from pathlib import Path


def test_interview_route_loads_package_relative_question_library():
    route = Path(__file__).parents[1] / 'routes' / 'interview.py'
    tree = ast.parse(route.read_text())
    block = next(node for node in tree.body if isinstance(node, ast.Try)
                 and any(isinstance(child, ast.ImportFrom)
                         and (child.module or '').endswith('question_library_integration')
                         for child in node.body))
    import logging
    scope = {'logger': logging.getLogger('test.unified-library')}
    exec(compile(ast.Module(body=[block], type_ignores=[]), str(route), 'exec'), scope)
    assert scope['UNIFIED_LIBRARY_AVAILABLE'] is True
    questions = scope['get_unified_questions'](category='behavioral', limit=2)
    assert questions and len(questions) <= 2
    companies = scope['unified_library'].get_companies()
    assert companies
    assert scope['get_unified_company_questions'](companies[0], limit=1)
