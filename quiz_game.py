"""메뉴와 문제 파일, 게임 진행을 관리하는 모듈입니다."""

import json
from contextlib import contextmanager
import tempfile
from pathlib import Path

from quiz import Quiz

def is_similar(user_input: str, correct_answer: str) -> bool:
    """공백과 대소문자를 제외한 전체 답이 같을 때만 정답입니다."""
    return ''.join(user_input.split()).casefold() == ''.join(correct_answer.split()).casefold()


@contextmanager
def quiz_write_lock(path: Path):
    """별도 잠금 폴더로 동시에 저장하는 실행 간 충돌을 막습니다."""
    lock_path = path.with_name(path.name + '.lock')
    try:
        lock_path.mkdir()
    except FileExistsError:
        raise ValueError('다른 실행에서 저장 중입니다. 잠시 후 다시 추가해 주세요.') from None
    try:
        yield
    finally:
        lock_path.rmdir()


class QuizGame:
    """문제 파일, 게임 진행과 메뉴, 이번 실행의 점수 기록을 관리합니다."""

    def __init__(self, state_path: str | Path | None = None) -> None:
        self.state_path = (Path(state_path) if state_path is not None
                           else Path(__file__).resolve().with_name('state.json'))
        self.scores: list[tuple[int, int]] = []

    @staticmethod
    def read_answer_number(hint: str | None = None) -> str:
        """유효한 번호를 입력할 때까지 현재 문제에서 기다립니다."""
        while True:
            prompt = "정답 번호를 입력하세요 (1~4, 힌트: ?): " if hint else "정답 번호를 입력하세요 (1~4): "
            value = input(prompt).strip()
            if hint and value == '?':
                print(f"힌트: {hint}")
                continue
            if value in ('1', '2', '3', '4'):
                return value
            print("1부터 4 사이의 번호를 입력해 주세요.")

    def run(self) -> None:
        """메뉴를 실행하며 입력 종료나 Ctrl+C도 안전하게 처리합니다."""
        try:
            self._run_menu()
        except (EOFError, KeyboardInterrupt):
            print("\n입력이 중단되어 게임을 종료합니다. 완료하지 않은 게임은 기록하지 않습니다.")

    def load_quizzes(self):
        return self._load_data()[1]

    def _load_data(self):
        """파일 전체를 읽고 검사합니다. 실패하면 호출한 메뉴에서 안내합니다."""
        with self.state_path.open(encoding='utf-8') as f:
            data = json.load(f)
        return data, self._validate_quizzes(data)

    @staticmethod
    def _validate_quizzes(data):
        quizzes = data.get('quizzes') if isinstance(data, dict) else data
        if not isinstance(quizzes, list) or not quizzes:
            raise ValueError('퀴즈 데이터는 하나 이상의 문제가 있는 목록이어야 합니다.')
        for index, quiz in enumerate(quizzes, 1):
            if not isinstance(quiz, dict):
                raise ValueError(f'{index}번 문제는 객체 형식이어야 합니다.')
            for field in ('question', 'answer'):
                value = quiz.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f'{index}번 문제의 {field}는 비어 있지 않은 문자열이어야 합니다.')
            hint = quiz.get('hint')
            if hint is not None and (not isinstance(hint, str) or not hint.strip()):
                raise ValueError(f'{index}번 문제의 힌트는 비어 있지 않은 문자열이어야 합니다.')
            if 'choices' in quiz or 'answer_number' in quiz:
                item = Quiz(quiz['question'], quiz.get('choices'),
                            quiz.get('answer_number'), quiz.get('hint'))
                if item.choices[item.answer - 1] != quiz['answer'].strip():
                    raise ValueError(f'{index}번 문제의 정답 번호와 정답 내용이 다릅니다.')
        return quizzes

    def play_game(self):
        """문제를 순서대로 한 번씩 출제하고 완료한 점수를 기록합니다."""
        try:
            quizzes = self.load_quizzes()
        except (OSError, UnicodeError, ValueError) as error:
            print(f'퀴즈 데이터를 불러올 수 없습니다: {error}')
            return

        score = 0

        print("✨ 부모님을 위한 따뜻한 성경 퀴즈 ✨")
        print("--------------------------------")

        for i, q in enumerate(quizzes, 1):
            print(f"\n문제 {i}/{len(quizzes)} | 현재 점수: {score}점")
            if 'choices' in q:
                quiz = Quiz(q['question'], q['choices'], q['answer_number'], q.get('hint'))
                quiz.display_question()
                user_answer = self.read_answer_number(quiz.hint)
                correct = quiz.check_answer(user_answer)
            else:
                print(q['question'])
                hint = q.get('hint')
                while True:
                    prompt = "정답을 입력하세요 (힌트: ?): " if hint else "정답을 입력하세요: "
                    user_answer = input(prompt).strip()
                    if hint and user_answer == '?':
                        print(f"힌트: {hint}")
                        continue
                    break
                correct = is_similar(user_answer, q['answer'])

            if correct:
                print("✅ 정답입니다! 정말 잘하시네요! ❤️")
                score += 1
            else:
                print(f"❌ 아쉽습니다. 정답은 '{q['answer']}'입니다.")
            print(f"현재 점수: {score}점 / 전체 {len(quizzes)}문제")

        print("\n--------------------------------")
        print(f"게임 종료! 총 {len(quizzes)}문제 중 {score}문제를 맞히셨습니다.")
        print("부모님, 오늘도 정말 고생 많으셨어요! 사랑합니다. 🥰")
        self.scores.append((score, len(quizzes)))
        return score, len(quizzes)


    def add_quiz(self):
        """객관식 문제를 추가하며 JSON의 다른 항목을 보존합니다."""
        try:
            self.load_quizzes()
            question = input("추가할 문제를 입력하세요: ").strip()
            choices = [input(f"선택지 {number}: ").strip() for number in range(1, 5)]
            answer_number = self.read_answer_number()
            hint = input("힌트 (생략하려면 Enter): ").strip() or None
            quiz = Quiz(question, choices, int(answer_number), hint)
            answer = quiz.choices[quiz.answer - 1]
            path = self.state_path.resolve()
            with quiz_write_lock(path):
                # 입력 중 다른 실행에서 추가한 문제와 메타데이터도 다시 읽습니다.
                data, quizzes = self._load_data()
                ids = [q.get('id') for q in quizzes if type(q.get('id')) is int]
                quizzes.append({'id': max(ids, default=0) + 1,
                                'question': quiz.question, 'answer': answer,
                                'choices': quiz.choices, 'answer_number': quiz.answer,
                                'hint': quiz.hint})
                temporary_path = None
                try:
                    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                                     dir=path.parent, prefix=path.name + '.',
                                                     suffix='.tmp', delete=False) as f:
                        temporary_path = Path(f.name)
                        json.dump(data, f, ensure_ascii=False, indent=4)
                        f.write('\n')
                    temporary_path.replace(path)
                finally:
                    if temporary_path is not None:
                        temporary_path.unlink(missing_ok=True)
            print("퀴즈를 추가했습니다.")
        except (OSError, UnicodeError, ValueError) as error:
            print(f'퀴즈를 추가할 수 없습니다: {error}')


    def list_quizzes(self):
        try:
            quizzes = self.load_quizzes()
        except (OSError, UnicodeError, ValueError) as error:
            print(f'퀴즈 데이터를 불러올 수 없습니다: {error}')
            return
        print(f"\n퀴즈 목록 (총 {len(quizzes)}문제)")
        for index, quiz in enumerate(quizzes, 1):
            print(f"{index}. {quiz['question']}")
            print(f"   정답: {quiz['answer']}")


    def show_scores(self):
        print("\n이번 실행의 점수 기록")
        if not self.scores:
            print("아직 완료한 게임이 없습니다. 먼저 퀴즈를 풀어 주세요.")
            return
        for index, (score, total) in enumerate(self.scores, 1):
            print(f"{index}회: 총 {total}문제 중 {score}문제 정답")

    def _run_menu(self):
        while True:
            print("\n============================")
            print("    기억 속의 은혜")
            print("    성경 퀴즈 게임")
            print("============================")
            print("\n1. 퀴즈 풀기")
            print("2. 퀴즈 추가")
            print("3. 퀴즈 목록")
            print("4. 점수 확인")
            print("5. 종료")
            choice = input("\n번호를 선택하세요: ").strip()

            if choice == "1":
                self.play_game()
            elif choice == "2":
                self.add_quiz()
            elif choice == "3":
                self.list_quizzes()
            elif choice == "4":
                self.show_scores()
            elif choice == "5":
                print("성경 퀴즈를 종료합니다. 다음에 또 만나요! ❤️")
                break
            else:
                print("잘못된 입력입니다. 1부터 5 사이의 번호를 입력해 주세요.")
