import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quiz_game import QuizGame, is_similar, quiz_write_lock


class QuizGameTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'state.json'
        original = Path(__file__).resolve().parents[1] / 'state.json'
        self.data = json.loads(original.read_text(encoding='utf-8'))
        self.path.write_text(json.dumps(self.data), encoding='utf-8')
        self.game = QuizGame(self.path)

    def run_menu(self, inputs):
        output = io.StringIO()
        with patch('builtins.input', side_effect=inputs), contextlib.redirect_stdout(output):
            self.game.run()
        return output.getvalue()

    def test_order_scoring_retry_and_second_game(self):
        quizzes = self.data['quizzes']
        answers = [str(q['answer_number']) for q in quizzes]
        wrong = [str(q['answer_number'] % 4 + 1) for q in quizzes]
        text = self.run_menu(['bad', '1', '', '5', 'abc'] + answers + ['1'] + wrong + ['4', '5'])
        self.assertEqual(self.game.scores, [(10, 10), (0, 10)])
        positions = [text.index(q['question']) for q in quizzes]
        self.assertEqual(positions, sorted(positions))
        for number, q in enumerate(quizzes, 1):
            self.assertEqual(text.count(q['question']), 2)
            self.assertEqual(text.count(f'문제 {number}/10'), 2)
        self.assertIn('현재 점수: 10점', text)
        self.assertIn('1회: 총 10문제 중 10문제 정답', text)
        self.assertIn('2회: 총 10문제 중 0문제 정답', text)

    def test_add_preserves_existing_data_and_can_play_new_question(self):
        self.data['high_score'] = 99
        self.data['other'] = {'keep': True}
        self.path.write_text(json.dumps(self.data), encoding='utf-8')
        answers = [str(q['answer_number']) for q in self.data['quizzes']]
        text = self.run_menu(['2', '테스트 문제', 'A', 'B', 'C', 'D', '0', '2', '',
                              '3', '1'] + answers + ['2', '4', '5'])
        saved = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(saved['quizzes'][:-1], self.data['quizzes'])
        self.assertEqual(saved['high_score'], 99)
        self.assertEqual(saved['other'], {'keep': True})
        self.assertEqual(saved['quizzes'][-1]['answer'], 'B')
        self.assertIn('총 11문제 중 11문제', text)

    def test_missing_corrupt_and_invalid_files_return_to_menu(self):
        invalid = copy.deepcopy(self.data)
        invalid['quizzes'][0]['answer_number'] = 0
        mismatch = copy.deepcopy(self.data)
        mismatch['quizzes'][0]['answer'] = '다른 답'
        for payload in (None, b'{', b'\xff', b'{}', b'[]', b'{"quizzes":[null]}',
                        json.dumps(invalid).encode(), json.dumps(mismatch).encode()):
            with self.subTest(payload=payload):
                if payload is None:
                    self.path.unlink(missing_ok=True)
                else:
                    self.path.write_bytes(payload)
                text = self.run_menu(['1', '2', '3', '4', '5'])
                self.assertIn('불러올 수 없습니다', text)
                self.assertIn('추가할 수 없습니다', text)
                self.assertIn('종료합니다', text)
                self.assertEqual(self.game.scores, [])
                if payload is not None:
                    self.assertEqual(self.path.read_bytes(), payload)

    def test_blank_choice_does_not_save(self):
        original = self.path.read_bytes()
        text = self.run_menu(['2', '문제', 'A', '', 'C', 'D', '1', '', '5'])
        self.assertIn('추가할 수 없습니다', text)
        self.assertEqual(self.path.read_bytes(), original)

    def test_save_failure_keeps_original(self):
        original = self.path.read_bytes()
        with patch.object(Path, 'replace', side_effect=OSError('저장 실패')):
            text = self.run_menu(['2', '문제', 'A', 'B', 'C', 'D', '1', '', '5'])
        self.assertIn('추가할 수 없습니다', text)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])
        self.assertFalse(self.path.with_name('state.json.lock').exists())

    def test_interrupted_input_does_not_record_or_save(self):
        for exception in (EOFError(), KeyboardInterrupt()):
            for prefix in ([], ['1'], ['2', '문제']):
                original = self.path.read_bytes()
                text = self.run_menu(prefix + [exception])
                self.assertIn('입력이 중단', text)
                self.assertEqual(self.game.scores, [])
                self.assertEqual(self.path.read_bytes(), original)

    def test_hint_retries_same_question_without_changing_score(self):
        self.data['quizzes'] = self.data['quizzes'][:1]
        self.path.write_text(json.dumps(self.data), encoding='utf-8')
        q = self.data['quizzes'][0]
        text = self.run_menu(['1', '?', '?', str(q['answer_number']), '5'])
        self.assertEqual(text.count('힌트: ' + q['hint']), 2)
        self.assertEqual(self.game.scores, [(1, 1)])

    def test_subjective_requires_full_answer_and_supports_hint(self):
        self.assertFalse(is_similar('엘리사', '엘리야'))
        self.assertFalse(is_similar('창세', '창세기'))
        self.assertTrue(is_similar('  Holy\t SPIRIT ', 'holy spirit'))
        self.path.write_text(json.dumps([{'question': '누구?', 'answer': '엘리야',
                                         'hint': '선지자입니다.'}]), encoding='utf-8')
        text = self.run_menu(['1', '?', '엘리사', '1', '엘 리 야', '5'])
        self.assertIn('힌트: 선지자입니다.', text)
        self.assertEqual(self.game.scores, [(0, 1), (1, 1)])

    def test_add_preserves_changes_made_while_waiting_for_input(self):
        responses = iter(['새 문제', 'A', 'B', 'C', 'D', '1', ''])
        def answer(prompt):
            if prompt.startswith('추가할'):
                updated = copy.deepcopy(self.data)
                updated['quizzes'].append(dict(updated['quizzes'][0], id=100,
                                               question='다른 실행의 문제'))
                updated['other'] = '최신 값'
                self.path.write_text(json.dumps(updated), encoding='utf-8')
            return next(responses)
        with patch('builtins.input', side_effect=answer), contextlib.redirect_stdout(io.StringIO()):
            self.game.add_quiz()
        saved = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(saved['quizzes'][-2]['question'], '다른 실행의 문제')
        self.assertEqual(saved['quizzes'][-1]['id'], 101)
        self.assertEqual(saved['other'], '최신 값')

    def test_overlapping_save_is_rejected_without_modifying_file(self):
        original = self.path.read_bytes()
        with quiz_write_lock(self.path):
            text = self.run_menu(['2', '문제', 'A', 'B', 'C', 'D', '1', '', '5'])
        self.assertIn('다른 실행에서 저장 중', text)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.path.with_name('state.json.lock').exists())

    def test_list_format_can_add_quiz(self):
        self.path.write_text(json.dumps(self.data['quizzes']), encoding='utf-8')
        self.run_menu(['2', '문제', 'A', 'B', 'C', 'D', '1', '', '5'])
        saved = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertIsInstance(saved, list)
        self.assertEqual(len(saved), 11)


if __name__ == '__main__':
    unittest.main()
