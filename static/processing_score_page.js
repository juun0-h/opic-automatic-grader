document.addEventListener("DOMContentLoaded", function() {
    var checkTranscriptListInterval = setInterval(function() {
        fetch('/get_transcriptListLength')  
        .then(response => response.json())  // 서버에서의 응답을 JSON 형태로 파싱
        .then(data => {
            const len = data.len;
            if (len == 15) {
                clearInterval(checkTranscriptListInterval); // interval 종료
                window.location.href = '/grading';
            }
        })
        .catch(error => {
            console.error('Error fetching text:', error);
        });
    }, 1000); // 1초마다 transcriptList의 길이를 확인합니다.
});