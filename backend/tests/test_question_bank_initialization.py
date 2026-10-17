def test_multiple_databases_do_not_mutate_shared_question_lists():
    from modules.interview.question_database_v2 import QuestionDatabase
    from modules.interview.question_bulk_data import BULK_CODING, BULK_SYSTEM_DESIGN

    original_coding = list(BULK_CODING)
    original_system_design = list(BULK_SYSTEM_DESIGN)
    first = QuestionDatabase()
    second = QuestionDatabase()
    assert BULK_CODING == original_coding
    assert BULK_SYSTEM_DESIGN == original_system_design
    assert first._questions.keys() == second._questions.keys()
    assert first._by_category == second._by_category
    assert first._by_topic == second._by_topic
