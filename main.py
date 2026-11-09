import json
import random
from difflib import SequenceMatcher
from pathlib import Path

def is_similar(user_input, correct_answer):
    user_input = user_input.replace(" ", "").lower()
    correct_answer = correct_answer.replace(" ", "").lower()
    if user_input == correct_answer:
        return True
    ratio = SequenceMatcher(None, user_input, correct_answer).ratio()
    return ratio >= 0.6

def load_quizzes():
    with Path(__file__).resolve().with_name('state.json').open(encoding='utf-8') as f:
        data = json.load(f)
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
    return quizzes

def play_game():
    try:
        quizzes = load_quizzes()
    except (OSError, UnicodeError, ValueError) as error:
        print(f'퀴즈 데이터를 불러올 수 없습니다: {error}')
        return
    
    # 문제를 무작위로 섞습니다.
    random.shuffle(quizzes)
    
    score = 0
    
    print("✨ 부모님을 위한 따뜻한 성경 퀴즈 ✨")
    print("--------------------------------")

    for i, q in enumerate(quizzes, 1):
        print(f"\n문제 {i}: {q['question']}")
        user_answer = input("정답을 입력하세요: ").strip()

        if is_similar(user_answer, q['answer']):
            print("✅ 정답입니다! 정말 잘하시네요! ❤️")
            score += 1
        else:
            print(f"❌ 아쉽습니다. 정답은 '{q['answer']}'입니다.")

    print("\n--------------------------------")
    print(f"게임 종료! 총 {len(quizzes)}문제 중 {score}문제를 맞히셨습니다.")
    print("부모님, 오늘도 정말 고생 많으셨어요! 사랑합니다. 🥰")
    return score, len(quizzes)


def add_quiz():
    try:
        quizzes = load_quizzes()
        question = input("추가할 문제를 입력하세요: ").strip()
        answer = input("정답을 입력하세요: ").strip()
        if not question or not answer:
            print("문제와 정답은 비워 둘 수 없습니다. 추가하지 않았습니다.")
            return

        # 기존 문제 번호와 겹치지 않는 번호를 부여합니다.
        ids = [q.get('id') for q in quizzes if type(q.get('id')) is int]
        quizzes.append({'id': max(ids, default=0) + 1,
                        'question': question, 'answer': answer})
        path = Path(__file__).resolve().with_name('state.json')
        with path.open(encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            data['quizzes'] = quizzes
        else:
            data = quizzes
        # 쓰기가 끝난 뒤 원본을 교체합니다.
        temporary_path = path.with_suffix('.json.tmp')
        try:
            with temporary_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.write('\n')
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)
        print("퀴즈를 추가했습니다.")
    except (OSError, UnicodeError, ValueError) as error:
        print(f'퀴즈를 추가할 수 없습니다: {error}')


def list_quizzes():
    try:
        quizzes = load_quizzes()
    except (OSError, UnicodeError, ValueError) as error:
        print(f'퀴즈 데이터를 불러올 수 없습니다: {error}')
        return
    print(f"\n퀴즈 목록 (총 {len(quizzes)}문제)")
    for index, quiz in enumerate(quizzes, 1):
        print(f"{index}. {quiz['question']}")
        print(f"   정답: {quiz['answer']}")


def show_scores(scores):
    print("\n이번 실행의 점수 기록")
    if not scores:
        print("아직 완료한 게임이 없습니다. 먼저 퀴즈를 풀어 주세요.")
        return
    for index, (score, total) in enumerate(scores, 1):
        print(f"{index}회: 총 {total}문제 중 {score}문제 정답")

def main():
    scores = []
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
            result = play_game()
            if result is not None:
                scores.append(result)
        elif choice == "2":
            add_quiz()
        elif choice == "3":
            list_quizzes()
        elif choice == "4":
            show_scores(scores)
        elif choice == "5":
            print("성경 퀴즈를 종료합니다. 다음에 또 만나요! ❤️")
            break
        else:
            print("잘못된 입력입니다. 1부터 5 사이의 번호를 입력해 주세요.")


if __name__ == "__main__":
    main()
