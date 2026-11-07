import unittest
from rag.generation import validation_result, UNAVAILABLE
from rag.numeric_grounding import quantities, numeric_failures
from rag.context_selection import focus_sources


class NumericGroundingTests(unittest.TestCase):
    def check(self, answer, evidence, ok=True):
        final, reason = validation_result(answer, [{'text': evidence}])
        self.assertEqual(final != UNAVAILABLE, ok, (answer, evidence, reason))

    def test_equivalent_forms(self):
        for answer in ['Minimum technical RAG score is 15/30 [1].',
                       'Minimum technical RAG score is ١٥ من ٣٠ [1].',
                       'Minimum technical RAG score is fifteen out of thirty [1].',
                       'Minimum technical RAG score is 50% [1].',
                       'Minimum technical RAG score is one half [1].',
                       'الحد الأدنى في RAG التقني خمسون بالمئة [1].']:
            with self.subTest(answer=answer):
                self.check(answer, 'شرط الاستحقاق في RAG التقني: 15 علامة على الأقل من 30.')

    def test_percent_scalar_not_interchangeable(self):
        self.check('Bonus is 50 points [1].', 'Bonus is 50%.', False)
        self.check('Bonus is ٥٠٪ [1].', 'Bonus is fifty percent.')
        self.check('Bonus is 25% [1].', 'Bonus is 50%.', False)

    def test_decimals_grouping_and_written_numbers(self):
        self.check('Cost is ١٬٥٠٠٫٥ [1].', 'Cost is 1,500.5.')
        self.check('Cost is 1.5 [1].', 'Cost is 15.', False)
        self.check('Bonus is twenty-five points [1].', 'Bonus is 25 points.')
        self.check('Bonus is one hundred points [1].', 'Bonus is 100 points.')
        self.check('البونص خمسة عشر علامة [1].', 'البونص 15 علامة.')

    def test_fractions_compare_whole_ratio(self):
        self.check('RAG threshold is 15/30 [1].', 'RAG threshold is 30/15.', False)
        self.check('RAG threshold is 1/2 [1].', 'RAG threshold is 15/30.')
        self.check('RAG threshold is 15/0 [1].', 'RAG threshold is 15/30.', False)

    def test_citation_is_local_to_claim(self):
        sources = [{'text': 'Bonus is 10 points.'}, {'text': 'Cost is 99 dollars.'}]
        self.assertTrue(numeric_failures('Bonus is 99 points [1]. Cost is 99 dollars [2].', sources))
        self.assertTrue(numeric_failures('Bonus is 99 points [2].', sources))
        self.assertTrue(numeric_failures('Bonus is 99 points [1][2].', sources))

    def test_same_chunk_unrelated_sentence_cannot_support_claim(self):
        self.check('Bonus is 99 points [1].', 'Bonus is 10 points. Cost is 99 dollars.', False)
        self.check('Bonus is 15 points [1].', 'Bonus is 10 points and deadline is 15 days.', False)
        self.check('Minimum RAG score is 15 [1].', 'Maximum RAG score is 15.', False)
        self.check('Cost is -15 [1].', 'Cost is 15.', False)
        self.check('Bonus is one million points [1].', 'Bonus is 10 points.', False)

    def test_numbered_list_markers_are_not_claims(self):
        self.check('1. Bonus is ten points [1].\n2. Bonus requires 15/30 in RAG [1].',
                   'Bonus is 10 points. Bonus requires 15/30 in RAG.')

    def test_wrong_and_missing_citation_rejected(self):
        self.check('Bonus requires 15/30 [9].', 'Bonus requires 15/30.', False)
        self.check('Bonus requires 15/30. Bonus is ten points [1].', 'Bonus requires 15/30. Bonus is 10 points.', False)

    def test_focus_has_safe_fallback_and_no_answer_values(self):
        sources = [{'text': 'Unrelated marketing costs.'}, {'text': 'شروط استحقاق البونص'}]
        self.assertEqual(focus_sources('What are the conditions for earning bonus points?', sources), [sources[1]])
        self.assertEqual(focus_sources('Unrecognized query', sources), sources)

    def test_reproduced_bad_citation_must_stay_rejected(self):
        sources = [{'text': 'Unrelated grading scale.'}, {'text': 'Marketing costs.'},
                   {'text': 'Presentation topics.'},
                   {'text': 'شرط استحقاق البونص : 15 علامة على الأقل من 30 في معيار RAG التقني.'}]
        draft = 'A team must achieve at least 15 out of 30 points in the technical RAG metric.\n[3]'
        self.assertTrue(numeric_failures(draft, sources))
        self.assertFalse(numeric_failures(draft.replace('[3]', '[4]'), sources))
        self.assertFalse(numeric_failures(draft.replace('[3]', '[4]').replace('.\n', '.  \n'), sources))
