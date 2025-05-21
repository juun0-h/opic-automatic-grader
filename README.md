# 모의 오픽(OPIc) 자동 평가 시스템

이 프로젝트는 음성 녹음, STT(Speech-to-Text), 자동 채점 및 피드백 제공 기능을 갖춘 영어 말하기 평가 시스템입니다.

## 기능

- 학생 로그인 및 기본 정보 입력
- 사용자별 맞춤형 질문 생성을 위한 설문 조사
- 음성 녹음 및 저장
- Whisper를 이용한 음성 인식(STT)
- 사전 훈련된 모델을 사용한 자동 채점
- LLM을 활용한 개인화된 피드백 제공

## 데이터베이스 구조

이 애플리케이션은 MySQL 데이터베이스를 사용하며, 다음과 같은 테이블로 구성됩니다:

1. `question` - 질문 데이터를 저장
   - `property`: 질문 속성 (직업, 거주방식, 취미 등)
   - `link`: 연결 인덱스
   - `question_text`: 질문 내용

2. `answer` - 학생 응답 저장
   - `studentID`: 학생 ID
   - `name`: 학생 이름
   - `question_number`: 질문 번호
   - `question_text`: 질문 내용
   - `answer_text`: 응답 내용
   - `score`: 점수

3. `grade` - 최종 평가 저장
   - `studentID`: 학생 ID
   - `name`: 학생 이름
   - `grade`: 최종 등급 (NO, IL, IM, IH, AL)

## 모델 디렉토리 구조

```
model/
  ├── Task_Completion/
  ├── Accuracy/
  └── Appropriateness/
```