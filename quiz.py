"""객관식 문제 한 개를 관리합니다. 실행하면 예제 문제를 풀 수 있습니다."""


class Quiz:
    """선택지 네 개와 정답 번호(1~4)를 가진 성경 퀴즈입니다."""

    def __init__(
        self,
        question: str,
        choices: list[str],
        answer: int,
        hint: str | None = None,
    ) -> None:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("문제는 비어 있지 않은 문자열이어야 합니다.")
        if not isinstance(choices, list) or len(choices) != 4:
            raise ValueError("선택지는 목록으로 정확히 4개를 입력해야 합니다.")
        if any(not isinstance(choice, str) or not choice.strip() for choice in choices):
            raise ValueError("각 선택지는 비어 있지 않은 문자열이어야 합니다.")
        if type(answer) is not int or not 1 <= answer <= 4:
            raise ValueError("정답은 1부터 4 사이의 정수여야 합니다.")
        if hint is not None and (not isinstance(hint, str) or not hint.strip()):
            raise ValueError("힌트는 비어 있지 않은 문자열 또는 None이어야 합니다.")

        self.question = question.strip()
        # 전달받은 목록을 복사하여 외부 목록의 변경에 영향을 받지 않게 합니다.
        self.choices = [choice.strip() for choice in choices]
        self.answer = answer
        self.hint = hint.strip() if hint is not None else None

    def display_question(self) -> None:
        """문제와 1~4번 선택지를 출력합니다. 정답은 표시하지 않습니다."""
        print(self.question)
        for number, choice in enumerate(self.choices, 1):
            print(f"{number}. {choice}")

    def check_answer(self, user_answer: str | int) -> bool:
        """정답이면 True, 오답이나 잘못된 입력이면 False를 반환합니다."""
        # input()의 반환값인 문자열과 직접 전달한 정수를 모두 지원합니다.
        if isinstance(user_answer, str):
            value = user_answer.strip()
            if value not in ("1", "2", "3", "4"):
                return False
            user_answer = int(value)
        if type(user_answer) is not int:
            return False
        return user_answer == self.answer


if __name__ == "__main__":
    quiz = Quiz(
        question="성경의 첫 번째 책은 무엇인가요?",
        choices=["출애굽기", "창세기", "시편", "마태복음"],
        answer=2,
        hint="천지 창조 이야기가 나오는 책입니다.",
    )
    quiz.display_question()
    print(f"힌트: {quiz.hint}")
    user_answer = input("정답 번호를 입력하세요 (1~4): ")
    if quiz.check_answer(user_answer):
        print("정답입니다!")
    else:
        print(f"오답 또는 잘못된 입력입니다. 정답은 {quiz.answer}번입니다.")
