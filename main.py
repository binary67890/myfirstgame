import json

def load_quizzes():
    # state.json 파일을 읽어옵니다.
    with open('state.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['quizzes']

def play_game():
    quizzes = load_quizzes()
    score = 0
    
    print("✨ 부모님을 위한 성경 퀴즈 게임 ✨")
    print("--------------------------------")

    for q in quizzes:
        print(f"\n문제 {q['id']}: {q['question']}")
        user_answer = input("정답을 입력하세요 (힌트를 보려면 '힌트' 입력): ")

        if user_answer == "힌트":
            print(f"💡 힌트: {q['hint']}")
            user_answer = input("정답을 입력하세요: ")

        if user_answer == q['answer']:
            print("✅ 정답입니다! 정말 대단하세요!")
            score += 1
        else:
            print(f"❌ 아쉽습니다. 정답은 '{q['answer']}'입니다.")

    print("\n--------------------------------")
    print(f"게임 종료! 총 {len(quizzes)}문제 중 {score}문제를 맞히셨습니다.")
    print("오늘도 멋진 하루 보내세요! ❤️")

if __name__ == "__main__":
    play_game()