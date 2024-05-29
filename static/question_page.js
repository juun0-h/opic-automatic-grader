const questionListenButton = document.getElementById('questionListen');
const startRecordingButton = document.getElementById('startRecording');
const stopRecordingButton = document.getElementById('stopRecording');

let recorder;
let audioChunks = [];
let clickCount = 0;
const maxClicks = 2;

questionListenButton.addEventListener('click', questionListen);
startRecordingButton.addEventListener('click', startRecording);
stopRecordingButton.addEventListener('click', stopRecording);

function questionListen() {
    if (clickCount < maxClicks) {
        clickCount++;
        fetch('/get_question')  // Flask 서버에 '/get_text' 엔드포인트로 GET 요청을 보냄
        .then(response => response.json())  // 서버에서의 응답을 JSON 형태로 파싱
        .then(data => {
            // 서버에서 받은 데이터를 text 변수에 할당하여 TTS 실행
            const text = data.text;
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "en-US";
            utterance.rate = 0.8;

            window.speechSynthesis.speak(utterance);
        })
        .catch(error => {
            console.error('Error fetching text:', error);
        });
    } else {
        alert('최대 2번까지 들을 수 있습니다.');
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recorder = new MediaRecorder(stream);
        recorder.ondataavailable = (e) => {
            audioChunks.push(e.data);
        };
        recorder.onstop = () => {
            saveRecording();
        };
        recorder.start();
        const audioContext = new AudioContext();
        const analyser = audioContext.createAnalyser();
        const microphone = audioContext.createMediaStreamSource(stream);
        const javascriptNode = audioContext.createScriptProcessor(2048, 1, 1);
        
        analyser.smoothingTimeConstant = 0.8;
        analyser.fftSize = 1024;

        microphone.connect(analyser);
        analyser.connect(javascriptNode);
        javascriptNode.connect(audioContext.destination);

        javascriptNode.onaudioprocess = () => {
            const array = new Uint8Array(analyser.frequencyBinCount);
            analyser.getByteFrequencyData(array);
            const average = array.reduce((a, b) => a + b, 0) / array.length;
            const volume = Math.round(average);
            document.getElementById('volumeValue').style.height = `${volume * 3}px`;
        };
    } catch (err) {
        console.error('Error starting recording:', err);
    }
}

function stopRecording() {
    if (recorder && recorder.state !== 'inactive') {
        recorder.stop();
    }
}

function saveRecording() {
    const blob = new Blob(audioChunks, { type: 'audio/wav' });
    const formData = new FormData();
    formData.append("audio_file", blob);

    fetch('/save_recording', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to save recording');
        }
        console.log('Recording saved successfully!');
        // `/save_recording` 성공 후 `/transcript` 요청
        return fetch('/transcript');

        // window.location.href = '/transcript';
        // window.location.href = '/question_page_next';
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to save recording');
        }
        console.log('Transcript informaition send successfully!');
        // /transcript 성공 후 /question_page_next로 이동
        window.location.href = '/question_page';
    })
    .catch(error => {
        console.error('Error saving recording:', error);
    });
}