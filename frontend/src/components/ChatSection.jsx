import { useState, useRef } from "react";
import axios from "axios";
import { useDispatch } from "react-redux";
import { setFormData } from "../redux/formSlice";

export default function ChatSection() {
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState([]);
  const [recording, setRecording] = useState(false);

  const dispatch = useDispatch();

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // 🧠 TEXT MESSAGE
  const sendMessage = async (text) => {
    const msg = text || message;
    if (!msg) return;

    try {
      const res = await axios.post("http://localhost:8000/chat", {
        message: msg,
      });

      dispatch(setFormData(res.data.form_data));

      setChat((prev) => [
        ...prev,
        { type: "user", text: msg },
        { type: "bot", text: res.data.message },
      ]);

      setMessage("");
    } catch (err) {
      console.error(err);
    }
  };

  // 🎤 START RECORDING
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = handleStopRecording;

      mediaRecorder.start();
      setRecording(true);
    } catch (err) {
      console.error("Mic error:", err);
    }
  };

  // ⏹ STOP RECORDING
  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  // 🎯 HANDLE AUDIO SEND
  const handleStopRecording = async () => {
    const audioBlob = new Blob(audioChunksRef.current, {
      type: "audio/webm",
    });

    const formData = new FormData();
    formData.append("file", audioBlob, "voice.webm");

    try {
      const res = await axios.post("http://localhost:8000/voice", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      dispatch(setFormData(res.data.form_data));

      setChat((prev) => [
        ...prev,
        { type: "user", text: "[Voice Message]" },
        { type: "bot", text: res.data.message },
      ]);
    } catch (err) {
      console.error("Voice error:", err);
    }
  };

  // 💾 SAVE BUTTON
  const handleSave = async () => {
    try {
      await axios.post("http://localhost:8000/save");

      setChat((prev) => [
        ...prev,
        { type: "bot", text: "✅ Interaction saved successfully" },
      ]);
    } catch (err) {
      console.error(err);
      setChat((prev) => [...prev, { type: "bot", text: "❌ Failed to save" }]);
    }
  };

  return (
    <div className="card">
      <div className="title">AI Assistant</div>

      {/* 💡 SAMPLE TEXT */}
      <div className="chat-hint">
        💡 Example: John met Dr Isaac with friend Isaac and father James to
        discuss tooth pain, shared report and gave sample medicine
      </div>

      {/* CHAT DISPLAY */}
      <div className="chat-box">
        {chat.map((c, i) => (
          <div key={i} className={`chat-msg ${c.type}`}>
            <div className="bubble">{c.text}</div>
          </div>
        ))}
      </div>

      {/* INPUT AREA */}
      <div className="chat-input">
        <input
          className="input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Describe interaction..."
        />

        <button onClick={() => sendMessage()}>Send</button>

        {/* 🎤 Voice */}
        {!recording ? (
          <button onClick={startRecording}>🎤</button>
        ) : (
          <button onClick={stopRecording}>⏹</button>
        )}
      </div>

      {/* 🔥 SAVE BUTTON */}
      <button className="save-btn" onClick={handleSave}>
        Save Interaction
      </button>
    </div>
  );
}
