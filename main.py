import json
from difflib import SequenceMatcher # 유사도 측정을 위한 라이브러리

def is_similar(user_input, correct_answer):
    # 1. 공백 제거 및 소문자 변환 (기본적인 전처리)
    user_input = user_input.replace(" ", "").lower()
    correct_answer = correct_answer.replace(" ", "").lower()
    
    # 2. 완전히 같으면 바로 True
    if user_input == correct_answer:
        return True
    
    # 3. 유사도 계산 (0.0 ~ 1.0 사이의 값)
    # 0.6(60%) 이상 비슷하면 정답으로 인정해줍니다.
    ratio = SequenceMatcher(None, user_input, correct_answer).ratio()
    return ratio >= 0.6

def load_quizzes():
    with open('state.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['quizzes']

def play_game():
    quizzes = load_quizzes()
    score = 0
    
    print("✨ 부모님을 위한 따뜻한 성경 퀴즈 ✨")
    print("--------------------------------")

    for q in quizzes:
        print(f"\n문제 {q['id']}: {q['question']}")
        user_answer = input("정답을 입력하세요: ")

        # 유연한 정답 체크 함수 사용
        if is_similar(user_answer, q['answer']):
            print("✅ 정답입니다! 정말 잘하시네요! ❤️")
            score += 1
        else:
            print(f"❌ 아쉽습니다. 정답은 '{q['answer']}'입니다. (입력하신 값: {user_answer})")

    print("\n--------------------------------")
    print(f"게임 종료! 총 {len(quizzes)}문제 중 {score}문제를 맞히셨습니다.")
    print("부모님, 오늘도 정말 고생 많으셨어요! 사랑합니다. 🥰")

if __name__ == "__main__":
    play_game()