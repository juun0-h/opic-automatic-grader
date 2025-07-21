# 모의 오픽(OPIc) 자동 평가 시스템

이 프로젝트는 음성 녹음, STT(Speech-to-Text), 자동 채점 및 피드백 제공 기능을 갖춘 영어 말하기 평가 시스템입니다. FastAPI와 계층형 아키텍처를 기반으로 구축되었습니다.

## 주요 기능

- 학생 인증 및 기본 정보 관리
- 사용자별 맞춤형 질문 생성을 위한 설문 조사
- 실시간 음성 녹음 및 저장
- Whisper 기반 음성 인식(STT)
- ML 모델을 활용한 자동 채점
- LLM 기반 개인화된 피드백 제공

## 기술 스택

- **백엔드**: FastAPI, Python 3.8+
- **데이터베이스**: MySQL with SQLAlchemy ORM
- **ML/AI**: PyTorch, Transformers, Hugging Face
- **인증**: JWT (JSON Web Tokens)
- **비동기 처리**: Redis, Celery
- **배경 작업**: Async/Await pattern

## 프로젝트 구조

```
opic-automatic-grader/
├── main.py              # FastAPI 애플리케이션 엔트리포인트
├── app.py              # 레거시 애플리케이션 (마이그레이션 중)
├── requirements.txt    # Python 의존성
│
├── api/               # API 라우터 및 엔드포인트
│   ├── auth.py       # 인증 관련 API
│   └── deps.py       # 의존성 주입
│
├── config/            # 설정 관리
│   ├── database.py   # 데이터베이스 설정
│   └── settings.py   # 애플리케이션 설정
│
├── models/            # 데이터 모델
│   ├── database.py   # SQLAlchemy 모델
│   ├── ml_models.py  # ML 모델 팩토리
│   └── schemas.py    # Pydantic 스키마
│
├── repositories/      # 데이터 접근 계층
│   ├── base.py       # 기본 리포지토리
│   ├── answer_repo.py
│   ├── grade_repo.py
│   ├── question_repo.py
│   └── survey_repo.py
│
├── services/          # 비즈니스 로직 계층
│   ├── audio_service.py
│   ├── feedback_service.py
│   ├── scoring_service.py
│   └── survey_service.py
│
├── static/            # 정적 파일 (CSS, JS)
├── templates/         # HTML 템플릿
└── tests/            # 테스트 코드
```

## 설치 및 실행

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 데이터베이스 설정

MySQL 데이터베이스를 생성하고 환경 변수를 설정합니다:

```bash
# .env 파일 생성
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/database_name
SECRET_KEY=your-secret-key
UPLOAD_FOLDER=./records
```

### 3. 애플리케이션 실행

```bash
# 개발 모드
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 또는
python main.py
```

## 데이터베이스 스키마

### Tables

1. **question** - 질문 데이터
   - `property`: 질문 속성 (직업, 거주방식, 취미 등)
   - `link`: 연결 인덱스
   - `question_text`: 질문 내용

2. **answer** - 학생 응답 데이터
   - `studentID`: 학생 ID
   - `name`: 학생 이름
   - `question_number`: 질문 번호
   - `question_text`: 질문 내용
   - `answer_text`: 응답 내용
   - `score`: 점수

3. **grade** - 최종 평가 데이터
   - `studentID`: 학생 ID
   - `name`: 학생 이름
   - `grade`: 최종 등급 (NO, IL, IM, IH, AL)

## 아키텍처 패턴

이 프로젝트는 다음과 같은 아키텍처 패턴을 사용합니다:

- **계층형 아키텍처**: API → Service → Repository → Database
- **의존성 주입**: FastAPI의 Depends를 활용한 DI 패턴
- **리포지토리 패턴**: 데이터 접근 로직 추상화
- **서비스 패턴**: 비즈니스 로직 분리
- **팩토리 패턴**: ML 모델 관리

## API 엔드포인트

- `GET /`: 메인 페이지
- `POST /auth/login`: 사용자 로그인
- `GET /survey`: 설문 조사 페이지
- `POST /survey/submit`: 설문 제출
- `GET /questions`: 질문 페이지
- `POST /audio/upload`: 음성 파일 업로드
- `GET /results`: 결과 확인

## 개발 및 테스트

```bash
# 테스트 실행
pytest

# 비동기 테스트
pytest -v tests/
```

## ML 모델 구조

```
models/
├── Task_Completion/   # 과제 완성도 평가 모델
├── Accuracy/         # 정확성 평가 모델  
└── Appropriateness/  # 적절성 평가 모델
```