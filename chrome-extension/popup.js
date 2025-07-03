document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("startCapture");
  btn.addEventListener("click", async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) {
        console.error("No active tab found");
        return;
      }

      chrome.tabCapture.capture({ audio: true, video: false }, (stream) => {
        if (!stream) {
          console.error("⚠️ Failed to capture tab audio.");
          return;
        }

        const audioContext = new AudioContext();
        console.log("AudioContext sampleRate:", audioContext.sampleRate); // <--- Add here
        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        const ws = new WebSocket("ws://localhost:7000");

        source.connect(audioContext.destination); // play audio

        ws.onopen = () => {
          source.connect(processor);
          processor.connect(audioContext.destination);

          processor.onaudioprocess = (e) => {
            const inputData = e.inputBuffer.getChannelData(0);
            const int16Buffer = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
              int16Buffer[i] = inputData[i] * 32767;
            }
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(int16Buffer.buffer);
            }
          };
        };
      });
    } catch (err) {
      console.error("Capture initiation error:", err);
    }
  });
});