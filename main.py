import json
import random
from difflib import SequenceMatcher

def is_similar(user_input, correct_answer):
    user_input = user_input.replace(" ", "").lower()
    correct_answer = correct_answer.replace(" ", "").lower()
    if user_input == correct_answer:
        return True
    ratio = SequenceMatcher(None, user_input, correct_answer).ratio()
    return ratio >= 0.6

def load_quizzes():
    with open('state.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        # 데이터 구조가 사전형태면 'quizzes' 키의 값을, 아니면 데이터 전체를 리스트로 반환
        if isinstance(data, dict) and 'quizzes' in data:
            return data['quizzes']
        return data

def play_game():
    quizzes = load_quizzes()
    
    # 문제를 무작위로 섞습니다.
    random.shuffle(quizzes)
    
    score = 0
    
    print("✨ 부모님을 위한 따뜻한 성경 퀴즈 ✨")
    print("--------------------------------")

    for i, q in enumerate(quizzes, 1):
        # q가 사전(dict) 형태여야 q['question']이 작동합니다.
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