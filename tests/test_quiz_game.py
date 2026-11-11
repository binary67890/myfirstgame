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
        self.data['quizzes'] = self.data['quizzes'][:10]
        self.data.pop('scores', None)
        self.data.pop('scores_version', None)
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
        self.assertEqual(self.game.scores, [(100, 10), (0, 10)])
        positions = [text.index(q['question']) for q in quizzes]
        self.assertEqual(positions, sorted(positions))
        for number, q in enumerate(quizzes, 1):
            self.assertEqual(text.count(q['question']), 2)
            self.assertEqual(text.count(f'문제 {number}/10'), 2)
        self.assertIn('현재 점수: 100점', text)
        self.assertIn('1회: 100점 / 100점 만점 (전체 10문제)', text)
        self.assertIn('2회: 0점 / 100점 만점 (전체 10문제)', text)

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
        self.assertIn('최종 점수: 110점 / 110점 만점 (전체 11문제)', text)

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

    def test_hints_keep_question_order_and_scoring(self):
        quizzes = self.data['quizzes']
        original = self.path.read_bytes()
        inputs = ['1']
        for index, quiz in enumerate(quizzes):
            answer = quiz['answer_number'] if index % 2 == 0 else quiz['answer_number'] % 4 + 1
            inputs.extend(['?', ' ? ', 'invalid', str(answer)])
        text = self.run_menu(inputs + ['5'])
        self.assertEqual(self.game.scores, [(25, 10)])
        positions = [text.index(quiz['question']) for quiz in quizzes]
        self.assertEqual(positions, sorted(positions))
        for number, quiz in enumerate(quizzes, 1):
            self.assertEqual(text.count(quiz['question']), 1)
            self.assertEqual(text.count(f'문제 {number}/10'), 1)
            self.assertEqual(text.count(f"힌트: {quiz['hint']}"), 2)
        self.assertEqual(json.loads(self.path.read_text())['quizzes'], self.data['quizzes'])

    def test_missing_and_null_hints_allow_answer_retry(self):
        quizzes = self.data['quizzes']
        quizzes[0].pop('hint', None)
        quizzes[1]['hint'] = None
        self.path.write_text(json.dumps(self.data), encoding='utf-8')
        answers = [str(quiz['answer_number']) for quiz in quizzes]
        text = self.run_menu(['1', '?', answers[0], '?', answers[1]] + answers[2:] + ['5'])
        self.assertEqual(text.count('이 문제에는 힌트가 없습니다.'), 2)
        self.assertEqual(self.game.scores, [(100, 10)])

    def test_add_quiz_does_not_accept_hint_request_as_answer(self):
        text = self.run_menu(['2', '새 문제', 'A', 'B', 'C', 'D', '?', '2', '', '5'])
        saved = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertIn('1부터 4 사이의 번호를 입력해 주세요.', text)
        self.assertNotIn('이 문제에는 힌트가 없습니다.', text)
        self.assertEqual(saved['quizzes'][:-1], self.data['quizzes'])
        self.assertEqual(saved['quizzes'][-1]['answer_number'], 2)
        self.assertEqual(saved['quizzes'][-1]['answer'], 'B')
        self.assertIsNone(saved['quizzes'][-1]['hint'])

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

    def test_repeated_hint_makes_correct_answer_worth_five(self):
        self.data['quizzes'] = self.data['quizzes'][:1]
        self.path.write_text(json.dumps(self.data), encoding='utf-8')
        q = self.data['quizzes'][0]
        text = self.run_menu(['1', '?', '?', str(q['answer_number']), '5'])
        self.assertEqual(text.count('힌트: ' + q['hint']), 2)
        self.assertEqual(self.game.scores, [(5, 1)])
        self.assertIn('힌트를 사용하여 이번 문제는 5점', text)

    def test_subjective_requires_full_answer_and_supports_hint(self):
        self.assertFalse(is_similar('엘리사', '엘리야'))
        self.assertFalse(is_similar('창세', '창세기'))
        self.assertTrue(is_similar('  Holy\t SPIRIT ', 'holy spirit'))
        self.path.write_text(json.dumps([{'question': '누구?', 'answer': '엘리야',
                                         'hint': '선지자입니다.'}]), encoding='utf-8')
        text = self.run_menu(['1', '?', '엘리사', '1', '엘 리 야', '5'])
        self.assertIn('힌트: 선지자입니다.', text)
        self.assertEqual(self.game.scores, [(0, 1), (10, 1)])

    def test_subjective_missing_and_null_hints_keep_order_and_score(self):
        quizzes = [
            {'question': '첫 번째 주관식', 'answer': 'Holy Spirit'},
            {'question': '두 번째 주관식', 'answer': '창세기', 'hint': None},
        ]
        self.path.write_text(json.dumps(quizzes), encoding='utf-8')
        original = self.path.read_bytes()
        text = self.run_menu(['1', '?', ' ? ', ' HOLY\tSPIRIT ', '?', '창세', '5'])
        self.assertEqual(text.count('이 문제에는 힌트가 없습니다.'), 3)
        self.assertEqual(self.game.scores, [(10, 2)])
        self.assertLess(text.index(quizzes[0]['question']), text.index(quizzes[1]['question']))
        for number, quiz in enumerate(quizzes, 1):
            self.assertEqual(text.count(quiz['question']), 1)
            self.assertEqual(text.count(f'문제 {number}/2'), 1)
        self.assertEqual(json.loads(self.path.read_text())['quizzes'], quizzes)

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


    def test_hint_scoring_matrix_for_choice_and_subjective_questions(self):
        for multiple_choice in (True, False):
            for use_hint in (True, False):
                for correct in (True, False):
                    with self.subTest(multiple_choice=multiple_choice,
                                      use_hint=use_hint, correct=correct):
                        question = {'question': '테스트 문제', 'answer': 'A', 'hint': '도움말'}
                        if multiple_choice:
                            question.update(choices=['A', 'B', 'C', 'D'], answer_number=1)
                        # 두 번째 문제는 힌트 없이 풀어 상태 초기화도 검증합니다.
                        self.path.write_text(json.dumps({'quizzes': [question, question]}), encoding='utf-8')
                        self.game = QuizGame(self.path)
                        answer = ('1' if correct else '2') if multiple_choice else ('A' if correct else 'B')
                        inputs = ['1'] + (['?', '?'] if use_hint else [])
                        inputs += [answer, '1' if multiple_choice else 'A', '4', '5']
                        text = self.run_menu(inputs)
                        expected = 10 + ((5 if use_hint else 10) if correct else 0)
                        self.assertEqual(self.game.scores, [(expected, 2)])
                        self.assertIn(f'최종 점수: {expected}점 / 20점 만점 (전체 2문제)', text)
                        self.assertIn(f'최고 점수: {expected}점', text)
                        self.assertEqual('힌트를 사용하여 이번 문제는 5점' in text,
                                         use_hint and correct)
                        self.assertEqual(QuizGame(self.path).scores, [(expected, 2)])
                        saved = json.loads(self.path.read_text(encoding='utf-8'))
                        self.assertEqual(saved['quizzes'], [question, question])
                        self.assertEqual(saved['scores'], [[expected, 2]])

    def test_scores_persist_and_highest_is_shown_after_restart(self):
        self.data['other'] = {'keep': True}
        self.data['scores'] = [[2, 10]]
        self.path.write_text(json.dumps(self.data), encoding='utf-8')
        answers = [str(q['answer_number']) for q in self.data['quizzes']]
        self.run_menu(['1'] + answers + ['5'])
        saved = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(saved['quizzes'], self.data['quizzes'])
        self.assertEqual(saved['other'], {'keep': True})
        self.assertEqual(saved['scores'], [[20, 10], [100, 10]])
        self.game = QuizGame(self.path)
        self.assertEqual(self.game.scores, [(20, 10), (100, 10)])
        text = self.run_menu(['4', '5'])
        self.assertIn('최고 점수: 100점 / 100점 만점 (총 10문제)', text)
        self.assertIn('1회: 20점 / 100점 만점 (전체 10문제)', text)

    def test_full_score_uses_actual_question_count(self):
        for count in (5, 10):
            with self.subTest(count=count):
                data = dict(self.data, quizzes=self.data['quizzes'][:count])
                self.path.write_text(json.dumps(data), encoding='utf-8')
                self.game = QuizGame(self.path)
                answers = [str(q['answer_number']) for q in data['quizzes']]
                text = self.run_menu(['1'] + answers + ['4', '5'])
                self.assertIn(f'최종 점수: {count * 10}점 / {count * 10}점 만점', text)
                self.assertIn(f'최고 점수: {count * 10}점 / {count * 10}점 만점', text)
                self.assertEqual(QuizGame(self.path).scores, [(count * 10, count)])

    def test_legacy_migration_is_applied_once_and_preserves_data(self):
        for version in (None, 1):
            with self.subTest(version=version):
                data = dict(self.data, scores=[[0, 10], [7, 10]], other={'keep': True})
                if version is not None:
                    data['scores_version'] = version
                self.path.write_text(json.dumps(data), encoding='utf-8')
                original = self.path.read_bytes()
                self.game = QuizGame(self.path)
                self.assertEqual(self.game.scores, [(0, 10), (70, 10)])
                self.assertEqual(self.path.read_bytes(), original)
                text = self.run_menu(['4', '5'])
                self.assertIn('최고 점수: 70점 / 100점 만점', text)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.game._record_score(5, 1)
                saved = json.loads(self.path.read_text())
                self.assertEqual(saved['scores_version'], 2)
                self.assertEqual(saved['scores'], [[0, 10], [70, 10], [5, 1]])
                self.assertEqual(saved['quizzes'], data['quizzes'])
                self.assertEqual(saved['other'], data['other'])
                self.game = QuizGame(self.path)
                self.assertEqual(self.game.scores, [(0, 10), (70, 10), (5, 1)])
                with contextlib.redirect_stdout(io.StringIO()):
                    self.game._record_score(10, 1)
                self.assertEqual(QuizGame(self.path).scores,
                                 [(0, 10), (70, 10), (5, 1), (10, 1)])

    def test_new_score_version_validates_against_ten_points_per_question(self):
        data = {'scores_version': 2,
                'scores': [[5, 1], [100, 10], [51, 5], [-5, 1], [True, 1], [5, 0]]}
        self.assertEqual(QuizGame._read_scores(data), [(5, 1), (100, 10)])

    def test_unknown_score_version_is_not_overwritten(self):
        data = dict(self.data, scores_version=99, scores=[[50, 10]])
        self.path.write_text(json.dumps(data), encoding='utf-8')
        original = self.path.read_bytes()
        self.game = QuizGame(self.path)
        self.assertEqual(self.game.scores, [])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.game._record_score(10, 1)
        self.assertIn('지원하지 않는 점수 기록 버전', output.getvalue())
        self.assertEqual(self.path.read_bytes(), original)

    def test_score_loading_tolerates_missing_corrupt_and_invalid_records(self):
        for payload in (None, b'{', b'\xff', b'null', b'[]',
                        b'{"scores": null}',
                        b'{"scores": [[1, 2], [-1, 2], [3, 2], [0, 0],'
                        b' [true, 2], [1.5, 2], null, "bad", [1]]}'):
            with self.subTest(payload=payload):
                if payload is None:
                    self.path.unlink(missing_ok=True)
                else:
                    self.path.write_bytes(payload)
                game = QuizGame(self.path)
                expected = [(10, 2)] if payload and b'[1, 2]' in payload else []
                self.assertEqual(game.scores, expected)
                with contextlib.redirect_stdout(io.StringIO()):
                    game.show_scores()
                if payload is not None:
                    self.assertEqual(self.path.read_bytes(), payload)

    def test_score_save_failure_preserves_file_and_current_result(self):
        original = self.path.read_bytes()
        answers = [str(q['answer_number']) for q in self.data['quizzes']]
        with patch.object(Path, 'replace', side_effect=OSError('저장 실패')):
            text = self.run_menu(['1'] + answers + ['4', '5'])
        self.assertIn('점수 기록을 저장할 수 없습니다', text)
        self.assertIn('최고 점수: 100점', text)
        self.assertEqual(self.game.scores, [(100, 10)])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])
        self.assertFalse(self.path.with_name('state.json.lock').exists())

    def test_score_save_preserves_latest_data_and_handles_list_format(self):
        quizzes = self.data['quizzes']
        self.path.write_text(json.dumps(quizzes), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            self.game._record_score(0, 10)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved, {'quizzes': quizzes, 'scores': [[0, 10]], 'scores_version': 2})
        other = QuizGame(self.path)
        saved['other'] = '최신 값'
        self.path.write_text(json.dumps(saved), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            self.game._record_score(5, 10)
            other._record_score(7, 10)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['scores'], [[0, 10], [5, 10], [7, 10]])
        self.assertEqual(saved['other'], '최신 값')
        self.assertEqual(saved['quizzes'], quizzes)

    def test_failed_score_is_retried_on_next_completed_game(self):
        with contextlib.redirect_stdout(io.StringIO()):
            with patch.object(Path, 'replace', side_effect=OSError('저장 실패')):
                self.game._record_score(3, 10)
            self.game._record_score(4, 10)
        self.assertEqual(QuizGame(self.path).scores, [(3, 10), (4, 10)])
        self.assertEqual(self.game.scores, [(3, 10), (4, 10)])

    def test_corruption_during_game_does_not_overwrite_file(self):
        def answer(prompt):
            self.path.write_bytes(b'{broken')
            return str(self.data['quizzes'][0]['answer_number'])
        self.data['quizzes'] = self.data['quizzes'][:1]
        self.path.write_text(json.dumps(self.data), encoding='utf-8')
        with patch('builtins.input', side_effect=answer), contextlib.redirect_stdout(io.StringIO()) as output:
            self.game.play_game()
        self.assertIn('점수 기록을 저장할 수 없습니다', output.getvalue())
        self.assertEqual(self.path.read_bytes(), b'{broken')
        self.assertEqual(self.game.scores, [(10, 1)])


if __name__ == '__main__':
    unittest.main()
