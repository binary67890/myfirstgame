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

if __name__ == "__main__":
    play_game()
