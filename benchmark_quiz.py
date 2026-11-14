"""임시 성경 퀴즈 데이터로 실제 읽기·저장 경로를 측정합니다 (표준 라이브러리)."""

import gc
import hashlib
import json
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

from quiz_game import QuizGame, quiz_write_lock


def make_data(count):
    examples = [
        ('성경의 첫 번째 책은 무엇인가요?', ['창세기', '출애굽기', '레위기', '민수기'],
         '천지 창조 이야기가 나옵니다.'),
        ('노아가 만든 것은 무엇인가요?', ['방주', '성전', '우물', '성벽'],
         '홍수를 대비해 만들었습니다.'),
        ('예수님께서 태어나신 곳은 어디인가요?', ['베들레헴', '나사렛', '여리고', '가나'],
         '동방박사들이 찾아간 곳입니다.'),
    ]
    quizzes = []
    for index in range(count):
        question, choices, hint = examples[index % len(examples)]
        quizzes.append(dict(id=index + 1, question=f'{index + 1}번: {question}',
                            choices=list(choices), answer=choices[0], answer_number=1,
                            hint=hint))
    return dict(quizzes=quizzes, scores=[[10, 1]], scores_version=2)


def measure(operation, repeats=7):
    operation()  # 워밍업은 통계에서 제외합니다.
    elapsed = []
    for _ in range(repeats):
        gc.collect()  # 수집 자체는 시간 측정에서 제외합니다.
        start = time.perf_counter()
        operation()
        elapsed.append((time.perf_counter() - start) * 1000)
    gc.collect()
    tracemalloc.start()  # 시간 측정과 분리하여 한 번 더 측정합니다.
    operation()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return dict(median_ms=round(statistics.median(elapsed), 3),
                min_ms=round(min(elapsed), 3), max_ms=round(max(elapsed), 3),
                peak_mib=round(peak / 1024**2, 3))


def main():
    original = Path(__file__).resolve().with_name('state.json')
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    results = []
    with tempfile.TemporaryDirectory(prefix='quiz-benchmark-') as directory:
        for count in (1000, 10000):
            path = Path(directory) / f'quizzes-{count}.json'
            QuizGame._write_data(path, make_data(count))
            game = QuizGame(path)  # 초기화는 측정 대상에서 제외합니다.

            def save():
                # 저장 직전 재읽기·검증, 잠금, 전체 파일 교체를 포함합니다.
                with quiz_write_lock(path):
                    data, _ = game._load_data()
                    game._write_data(path, data)

            results.append(dict(count=count, file_bytes=path.stat().st_size,
                                read=measure(game.load_quizzes), save=measure(save)))
    after = hashlib.sha256(original.read_bytes()).hexdigest()
    if before != after:
        raise RuntimeError('측정 중 실제 state.json의 내용이 변경되었습니다.')
    print(json.dumps(dict(python=sys.version, platform=platform.platform(),
                          machine=platform.machine(), temporary_root=tempfile.gettempdir(),
                          repeats=7, state_sha256_before=before, state_sha256_after=after,
                          results=results), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
