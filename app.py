from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import mysql.connector
import random
import os
import torch
from transformers import (
    AutomaticSpeechRecognitionPipeline,
    WhisperForConditionalGeneration,
    WhisperTokenizer,
    WhisperProcessor,
    AutoModelForSpeechSeq2Seq,
    AutoProcessor,
    pipeline
)
import threading
from transformers import RobertaForSequenceClassification, RobertaTokenizer
from queue import Queue

# from dataclasses import dataclass
from typing import Dict, Optional
from huggingface_hub import login

from langchain_community.llms import HuggingFaceHub
from langchain.schema import (
    HumanMessage,
    SystemMessage,
)
from langchain_community.chat_models.huggingface import ChatHuggingFace


from dotenv import load_dotenv
import os

load_dotenv()

# ================== Flask App ==================

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

app.config['UPLOAD_FOLDER'] = './records'

device = "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
model_id = "openai/whisper-large-v3"
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
)
model.to(device).float()
processor = AutoProcessor.from_pretrained(model_id)

whisper_pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    max_new_tokens=256,
    chunk_length_s=30,
    batch_size=16,
    return_timestamps=True,
    torch_dtype=torch_dtype,
    device=device,
)

connection = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_DATABASE')
)

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
login(token=HUGGINGFACE_API_TOKEN)

task_queue = Queue() # Queue containing question_page_number to be transcribed 
transcript_list = {}
for i in range(1, 16):
    transcript_list[i] = 'Hello'
selected_options = {}  # 각 분야별 선택 옵션 저장 딕셔너리
question_list = [0 for i in range(15)]

# 설문지 내용
# 1 = '종사 분야' 
# 2 = '거주 방식' 
# 3 = '여가 및 취미'
survey_questions = {
    1: "현재 귀하는 어느 분야에 종사하고 계십니까?",
    2: "현재 귀하는 어디에 살고 계십니까?",
    3: "귀하는 여가 및 취미활동으로 주로 무엇을 하십니까? (두 개 이상 선택)",
}

survey_options = {
    1: ["사업자/직장인", "학생", "취업준비생"],
    2: ["개인주택이나 아파트에 홀로 거주", "친구나 룸메이트와 함께 주택이나 아파트에 거주", "가족과 함께 주택이나 아파트에 거주"],
    3: ["운동", "게임", "SNS", "문화생활", "여행", "자기관리", "예술활동", "자기개발"],
}

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    studentID = request.form['studentID']
    name = request.form['name']
    session['studentID'] = studentID
    session['name'] = name
    return render_template('start_page.html')

@app.route('/survey', methods=['GET', 'POST'])
def survey():
    global selected_options
    next_page = 1

    if request.method == 'POST':
        survey_page = int(request.form.get('survey-page'))
        next_page_direction = request.form.get('next-page-direction')

        if next_page_direction == 'next':
            next_page = survey_page + 1
        else: # next_page_direction == 'back'
            next_page = survey_page - 1

        if survey_page == 3:
            selected_options[survey_page] = request.form.getlist('option')
        else:
            selected_options[survey_page] = request.form.get('option')

        if next_page == 4:
            global question_list
            print(selected_options)

            cursor = connection.cursor()
            index = 0
            question_list[index] = "Can you introduce yourself in as much detail as possible?"
            index += 1

            query = "SELECT question_text FROM question WHERE property = %s AND link = %s"
            option_value = selected_options.get(1) # 종사 분야
            for i in range(3):
                cursor.execute(query, (option_value, i))
                question_list[index] = cursor.fetchone()[0]
                index += 1

            option_value = selected_options.get(2) # 거주 방식
            for i in range(3):
                cursor.execute(query, (option_value, i))
                question_list[index] = cursor.fetchone()[0]
                index += 1

            option_value = random.choice(selected_options.get(3)) # 여가 및 취미
            for i in range(3):
                cursor.execute(query, (option_value, i))
                question_list[index] = cursor.fetchone()[0]
                index += 1

            option_value = random.choice(['롤플레이1', '롤플레이2', '롤플레이3', '롤플레이4'])
            for i in range(3):
                cursor.execute(query, (option_value, i))
                question_list[index] = cursor.fetchone()[0]
                index += 1

            option_value = random.choice(['돌발질문:코로나', '돌발질문:코인', '돌발질문:출산율'])
            for i in range(2):
                cursor.execute(query, (option_value, i))
                question_list[index] = cursor.fetchone()[0]
                index += 1
            for question in question_list:
                print(question)
            return redirect(url_for('background_start'))

    return render_template('survey_page.html', 
                           survey_page=next_page, 
                           question=survey_questions[next_page], 
                           options=survey_options[next_page], 
                           selected_option=selected_options.get(next_page)
                           )

@app.route('/background_start')
def background_start():
    # thread background 작업
    def backgroundTask():
        while True:
            question_page_number_ = task_queue.get()
            audio_file = f'records/record{question_page_number_}.wav'
            result = whisper_pipe(audio_file, generate_kwargs={"language": "english"})
            transcript_list[question_page_number_] = result["text"]
            for key, value in transcript_list.items():
                print(key, value)

            if len(transcript_list) == 15:
                break
            
    def startBackgroundTask():
        thread = threading.Thread(target=backgroundTask, args=())
        thread.start()

    startBackgroundTask()
    session['question_page_number'] = 1
    return render_template("question_page.html", question_page_number = session['question_page_number'])

@app.route('/question_page', methods=['GET', 'POST'])
def question_page():
    session['question_page_number'] += 1
    if session['question_page_number'] < 16:
        return render_template("question_page.html", question_page_number = session['question_page_number'])
    else:
        return render_template("processing_score_page.html")

@app.route('/get_question')
def get_text():
    text = question_list[session['question_page_number'] - 1]
    return jsonify({'text': text})

@app.route('/get_transcriptListLength')
def get_transcriptListLength():
    transcriptListLength = len(transcript_list)
    return jsonify({'len': transcriptListLength})

@app.route('/save_recording', methods=['POST'])
def save_recording():
    try:
        file = request.files['audio_file']
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], f"record{session['question_page_number']}.wav"))

        return 'Recording saved successfully!', 200
    except Exception as e:
        return f'Error saving recording: {e}', 500
    
@app.route('/transcript')
def transcript():
    try:
        task_queue.put(session['question_page_number'])
        return jsonify({'message': 'task_queue saved successfully!'}), 200
    except Exception as e:
        return jsonify({'error': f'Error saving recording: {e}'}), 500

@app.route('/grading')
def grading():
    def load_model_and_tokenizer(model_path):
        model = RobertaForSequenceClassification.from_pretrained(model_path)
        tokenizer = RobertaTokenizer.from_pretrained(model_path)
        return model, tokenizer
    
    models_paths = {
        "Task_Completion": "model/Task_Completion",
        "Accuracy": "model/Accuracy",
        "Appropriateness": "model/Appropriateness"
    }

    cursor = connection.cursor()
    models_and_tokenizers = {criteria: load_model_and_tokenizer(path) for criteria, path in models_paths.items()}

    def predict(criteria, text, models_and_tokenizers):
        model, tokenizer = models_and_tokenizers[criteria]
        inputs = tokenizer(text, return_tensors="pt", max_length=512, truncation=True, padding="max_length")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            predictions = outputs.logits.squeeze().item()

        rounded_predictions = round(predictions, 2)
        return rounded_predictions

    question_num = 0
    # scores_summary = {f"Q{idx}_{criteria}": [] for idx, criteria in enumerate(models_paths.keys())}
    scores_summary = {criteria: [] for criteria in models_paths.keys()}
    sorted_transcript_list = [transcript_list[key] for key in sorted(transcript_list.keys())]
    question_average_list = []
    question_scores_list = []
    for question, transcript in zip(question_list, sorted_transcript_list):
        text = f"question : {question}  \n\n answer : {transcript}"

        question_scores = []
        question_num += 1
        for criteria in models_paths.keys():
        # for criteria in scores_summary.keys():
            score = predict(criteria, text, models_and_tokenizers)
            question_scores.append(score)
            scores_summary[criteria].append(score)
            print(f"{criteria}: {score}")

        question_scores_list.append(question_scores)
        question_average = sum(question_scores) / len(question_scores)
        question_average = round(question_average, 2)
        print(f"질문 {question}에 대한 평균 점수: {question_average}")
        question_average_list.append(question_average)
        insert_query = "INSERT INTO answer (studentID, name, question_number, question_text, answer_text, score) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (session['studentID'], session['name'], question_num, question, transcript, question_average))
    
    criteria_averages = {criteria: sum(scores) / len(scores) for criteria, scores in scores_summary.items()}
    total_average_score = sum(criteria_averages.values()) / len(criteria_averages)

    print(f"총 평균 점수: {total_average_score}")

    if total_average_score >= 4.5: 
        grade = "AL"
    elif 3.5 <= total_average_score < 4.5:
        grade = "IH"
    elif 2.5 <= total_average_score < 3.5:
        grade = "IM"
    elif 1.5 <= total_average_score < 2.5:
        grade = "IL"
    else:
        grade = "NH"

    insert_grade_query = "INSERT INTO grade (studentID, name, grade) VALUES (%s, %s, %s)"
    cursor.execute(insert_grade_query, (session['studentID'], session['name'], grade))
    connection.commit()

    # feedback 작업
    rubric = {
        "NO": "Novice-level speakers can communicate short messages on highly predictable, everyday topics that affect them directly. They do so primarily through the use of isolated words and phrases that have been encountered, memorized, and recalled. Novice-level speakers may be difficult to understand even by the most sympathetic interlocutors accustomed to non-native speech",
        "IL": "Speakers at the Intermediate Low sublevel are able to handle successfully a limited number of uncomplicated communicative tasks by creating with the language in straightforward social situations. Conversation is restricted to some of the concrete exchanges and predictable topics necessary for survival in the target-language culture. These topics relate to basic personal information; for example, self and family, some daily activities and personal preferences, and some immediate needs, such as ordering food and making simple purchases. At the Intermediate Low sublevel, speakers are primarily reactive and struggle to answer direct questions or requests for information. They are also able to ask a few appropriate questions. Intermediate Low speakers manage to sustain the functions of the Intermediate level, although just barely.",
        "IM": "Mid Speakers at the Intermediate Mid sublevel are able to handle successfully a variety of uncomplicated communicative tasks in straightforward social situations. Conversation is generally limited to those predictable and concrete exchanges necessary for survival in the target culture. These include personal information related to self, family, home, daily activities, interests and personal preferences, as well as physical and social needs, such as food, shopping, travel, and lodging. Intermediate Mid speakers tend to function reactively, for example, by responding to direct questions or requests for information. However, they are capable of asking a variety of questions when necessary to obtain simple information to satisfy basic needs, such as directions, prices, and services. When called on to perform functions or handle topics at the Advanced level, they provide some information but have difficulty linking ideas, manipulating time and aspect, and using communicative strategies, such as circumlocution. Intermediate Mid speakers are able to express personal meaning by creating with the language, in part by combining and recombining known elements and conversational input to produce responses typically consisting of sentences and strings of sentences. Their speech may contain pauses, reformulations, and self-corrections as they search for adequate vocabulary and appropriate language forms to express themselves. In spite of the limitations in their vocabulary and/or pronunciation and/or grammar and/or syntax, Intermediate Mid speakers are generally understood by sympathetic interlocutors accustomed to dealing with non-natives.",
        "IH": "Intermediate High speakers are able to converse with ease and confidence when dealing with the routine tasks and social situations of the Intermediate level. They are able to handle successfully uncomplicated tasks and social situations requiring an exchange of basic information related to their work, school, recreation, particular interests, and areas of competence. Intermediate High speakers can handle a substantial number of tasks associated with the Advanced level, but they are unable to sustain performance of all of these tasks all of the time. Intermediate High speakers can narrate and describe in all major time frames using connected discourse of paragraph length, but not all the time. Typically, when Intermediate High speakers attempt to perform Advanced-level tasks, their speech exhibits one or more features of breakdown, such as the failure to carry out fully the narration or description in the appropriate major time frame, an inability to maintain paragraph-length discourse, or a reduction in breadth and appropriateness of vocabulary. Intermediate High speakers can generally be understood by native speakers unaccustomed to dealing with non-natives, although interference from another language may be evident (e.g., use of code-switching, false cognates, literal translations), and a pattern of gaps in communication may occur.",
        "AL": "Speakers at the Advanced Low sublevel are able to handle a variety of communicative tasks. They are able to participate in most informal and some formal conversations on topics related to school, home, and leisure activities. They can also speak about some topics related to employment, current events, and matters of public and community interest. Advanced Low speakers demonstrate the ability to narrate and describe in the major time frames of past, present, and future in paragraph-length discourse with some control of aspect. In these narrations and descriptions, Advanced Low speakers combine and link sentences into connected discourse of paragraph length, although these narrations and descriptions tend to be handled separately rather than interwoven. They can handle appropriately the essential linguistic challenges presented by a complication or an unexpected turn of events. Responses produced by Advanced Low speakers are typically not longer than a single paragraph. The speaker's dominant language may be evident in the use of false cognates, literal translations, or the oral paragraph structure of that language. At times their discourse may be minimal for the level, marked by an irregular flow, and containing noticeable self-correction. More generally, the performance of Advanced Low speakers tends to be uneven. Advanced Low speech is typically marked by a certain grammatical roughness (e.g., inconsistent control of verb endings), but the overall performance of the Advanced-level tasks is sustained, albeit minimally. The vocabulary of Advanced Low speakers often lacks specificity. Nevertheless, Advanced Low speakers are able to use communicative strategies such as rephrasing and circumlocution. Advanced Low speakers contribute to the conversation with sufficient accuracy, clarity, and precision to convey their intended message without misrepresentation or confusion. Their speech can be understood by native speakers unaccustomed to dealing with non-natives, even though this may require some repetition or restatement. When attempting to perform functions or handle topics associated with the Superior level, the linguistic quality and quantity of their speech will deteriorate significantly."
    }
    repo_id = "meta-llama/Meta-Llama-3-8B-Instruct"
    llm = HuggingFaceHub(
        repo_id=repo_id,
        task="text-generation",
        model_kwargs={
            "max_new_tokens": 512,
            "top_k": 30,
            "temperature": 0.1,
            "repetition_penalty": 1.03,
            "return_full_text": False,
        },
        huggingfacehub_api_token=os.getenv("HUGGINGFACE_API_TOKEN")
    )
    feedbackOutput = []
    
    for question, transcript, question_scores in zip(question_list, sorted_transcript_list, question_scores_list):
        messages = [
            SystemMessage(content=
                        f"""
                        You're a professional English teacher.

                        Your task is to give feedback based on the given evaluation rubric, questions and answers, scores (1 to 5) according to the evaluation items, and final grade.
                        Please make sure you read and understand the instructions carefully
                        Please keep this document open while reviewing, and refer to it as needed.
                        Also, keep in mind that a few spelling errors can be included in the responses that can be scored with the maximum score(5.0) or native responses with a small portion.\n\n
                        Note that the given response is a transcribed English text and given as a pair with a question of item and please keep in mind that this is a English oral test, which means that you should evaluate the response as an oral test.

                        [Evaluation Metric]
                        {rubric}
                        
                        [Input Data]
                        Question: {question}
                        STT: {transcript}
                        Task Completion Score: {question_scores[0]}
                        Accuracy Score: {question_scores[1]}  
                        Appropriateness Score: {question_scores[2]}
                        Final Level: {grade}
                        """
                        ),
            HumanMessage(
                content="""
                [Request]
                        1. Please briefly write the overall feedback (weaknesses, directions for improvement, etc.) based on the ratings(1~5) and evaluation rubric.
                        2. Please write a detailed feedback (based on your evaluation score and rubric) for each score (up to 3).
                        3. Please write a brief specific advice for achieving the next level.
                        4. Please provide all feedback in Korean
                """
            ),
        ]

        chat_model = ChatHuggingFace(llm=llm)
        res = chat_model.invoke(messages)
        feedbackOutput.append(res.content)

    return render_template("show_score_page.html", grade = grade, scores = question_average_list, feedbackOutput = feedbackOutput)

@app.route('/feedback', methods=['POST'])
def feedback():
    feedbackOutput = request.form.getlist('feedback-output[]')
    for i in range (15):
        print(feedbackOutput[i])
    sorted_transcript_list = [transcript_list[key] for key in sorted(transcript_list.keys())]

    return render_template("feedback_page.html", feedbackOutput = feedbackOutput, questions = question_list, stt = sorted_transcript_list)

if __name__ == '__main__':
    app.run(debug=True)