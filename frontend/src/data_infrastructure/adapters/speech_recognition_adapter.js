// Browser-owned speech integration; audio never passes through Mosa's backend.
export function recognizeSpeech({onResult,onError,onEnd,onStart}) {
  const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!Speech) {
    onError('Trình duyệt chưa hỗ trợ giọng nói. Hãy nhập từ khoá hoặc chọn danh mục.');
    return null;
  }
  const speech=new Speech();
  speech.lang='vi-VN';
  speech.interimResults=false;
  speech.onresult=e=>onResult(e.results[0][0].transcript);
  speech.onerror=()=>onError('Không nhận được giọng nói hoặc quyền micro bị từ chối. Thử lại hoặc nhập từ khoá.');
  speech.onend=onEnd;
  try {
    onStart('Âm thanh có thể được dịch vụ của trình duyệt xử lý. Cho phép micro để bắt đầu.');
    speech.start();
  } catch {
    onError('Không mở được micro. Hãy dùng từ khoá.');
  }
  return speech;
}
