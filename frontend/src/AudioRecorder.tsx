import { useEffect, useRef, useState } from "react";
import { CirclePause, CirclePlay, Download, Mic, Square, Upload, WandSparkles } from "lucide-react";
import { api } from "./api";

interface Props { onTranscript:(text:string) => void; onError:(message:string) => void; fileBaseName?:string; meetingId?:number; }

export default function AudioRecorder({ onTranscript, onError, fileBaseName="회의녹음", meetingId }: Props) {
  const [status, setStatus] = useState<"idle" | "recording" | "paused" | "ready" | "transcribing" | "complete">("idle");
  const [transcriptionStep,setTranscriptionStep]=useState(0);
  const [processError,setProcessError]=useState("");
  const [seconds, setSeconds] = useState(0);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    if (status !== "recording") return;
    const timer = window.setInterval(() => setSeconds(value => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [status]);

  useEffect(() => () => {
    stream.current?.getTracks().forEach(track => track.stop());
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  async function start() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      onError("이 브라우저는 마이크 녹음을 지원하지 않습니다."); return;
    }
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio:{ echoCancellation:true, noiseSuppression:true, autoGainControl:true } });
      const candidates = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"];
      const mimeType = candidates.find(type => MediaRecorder.isTypeSupported(type));
      recorder.current = new MediaRecorder(stream.current, mimeType ? { mimeType } : undefined);
      chunks.current = [];
      setSeconds(0); setAudioFile(null); setTranscriptionStep(0); setProcessError("");
      recorder.current.ondataavailable = event => { if (event.data.size) chunks.current.push(event.data); };
      recorder.current.onstop = () => {
        const type = recorder.current?.mimeType || "audio/webm";
        const ext = type.includes("mp4") ? "m4a" : "webm";
        const file = new File(chunks.current, `decisionflow-${Date.now()}.${ext}`, { type });
        setAudioFile(file);
        setPreviewUrl(current => { if (current) URL.revokeObjectURL(current); return URL.createObjectURL(file); });
        stream.current?.getTracks().forEach(track => track.stop());
        setStatus("ready");
      };
      recorder.current.start(1000);
      setStatus("recording"); onError("");
    } catch (error) {
      onError(error instanceof DOMException && error.name === "NotAllowedError" ? "마이크 권한을 허용해 주세요." : "마이크를 시작하지 못했습니다.");
    }
  }

  function pause() {
    if (recorder.current?.state === "recording") { recorder.current.pause(); setStatus("paused"); }
    else if (recorder.current?.state === "paused") { recorder.current.resume(); setStatus("recording"); }
  }

  function stop() { if (["recording", "paused"].includes(recorder.current?.state || "")) recorder.current?.stop(); }

  function saveAudio() {
    if (!audioFile) return;
    const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const extension = audioFile.name.split(".").pop() || (audioFile.type.includes("mp4") ? "m4a" : "webm");
    const safeName = (fileBaseName.trim() || "회의녹음").replace(/[\\/:*?"<>|]/g, "-");
    const link = document.createElement("a");
    link.href = previewUrl || URL.createObjectURL(audioFile);
    link.download = `${safeName}-${stamp}.${extension}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  function selectFile(file:File|null) {
    setAudioFile(file);
    setSeconds(0);
    setPreviewUrl(current => {
      if (current) URL.revokeObjectURL(current);
      return file ? URL.createObjectURL(file) : "";
    });
    setStatus(file ? "ready" : "idle");
    setTranscriptionStep(0);
    setProcessError("");
    onError("");
    if (file) void transcribe(file);
  }

  async function transcribe(selectedFile?:File) {
    const file=selectedFile||audioFile;
    if (!file) { onError("녹음하거나 음성 파일을 선택해 주세요."); return; }
    if (file.size > 250 * 1024 * 1024) { const message="음성 파일은 최대 250MB까지 가능합니다.";setProcessError(message);onError(message);return; }
    setStatus("transcribing"); setTranscriptionStep(1); setProcessError(""); onError("");
    try {
      await new Promise(resolve=>window.setTimeout(resolve,350));
      setTranscriptionStep(2);
      const body = new FormData(); body.append("file", file);
      if (meetingId) {
        const job=await api<{id:number}>(`/meetings/${meetingId}/input/file?recording=true`,{method:"POST",body});
        for (;;) {
          await new Promise(resolve=>window.setTimeout(resolve,1500));
          const jobs=await api<{id:number;status:string;error:string|null}[]>(`/meetings/${meetingId}/input/jobs`);
          const current=jobs.find(value=>value.id===job.id);
          if(current?.status==="FAILED")throw new Error(current.error||"전사 실패");
          if(current?.status==="TRANSCRIBED")break;
        }
        const meeting=await api<{transcript:string}>(`/meetings/${meetingId}`);
        onTranscript(meeting.transcript);
      } else {
        const result = await api<{text:string}>("/transcriptions", { method:"POST", body });
        onTranscript(result.text);
      }
      onError(""); setTranscriptionStep(3); setStatus("complete");
    } catch (error) { const message=error instanceof Error ? error.message : "음성 전사에 실패했습니다.";setProcessError(message);onError(message);setStatus("ready"); }
  }

  const time = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  return <div className="recorder-box">
    <div className="recorder-status"><span className={`record-dot ${status}`} /><strong>{status === "recording" ? "녹음 중" : status === "paused" ? "일시정지" : status === "ready" ? "전사 준비됨" : status === "transcribing" ? "전사 처리 중" : status === "complete" ? "전사 완료" : "녹음 대기"}</strong><time>{time}</time></div>
    <div className="recorder-controls">
      <button type="button" className="button soft" onClick={start} disabled={["recording","paused","transcribing"].includes(status)}><Mic size={16}/>녹음</button>
      <button type="button" className="icon-control" onClick={pause} disabled={!(["recording","paused"].includes(status))} title={status === "paused" ? "계속 녹음" : "일시정지"}>{status === "paused" ? <CirclePlay/> : <CirclePause/>}</button>
      <button type="button" className="icon-control" onClick={stop} disabled={!(["recording","paused"].includes(status))} title="정지"><Square/></button>
      <label className={`button ghost file-button ${status==="transcribing"?"disabled":""}`}><Upload size={16}/>파일<input disabled={status==="transcribing"} type="file" accept=".flac,.mp3,.mp4,.mpeg,.mpga,.m4a,.ogg,.wav,.webm" onChange={event=>{selectFile(event.target.files?.[0]||null);event.currentTarget.value="";}}/></label>
      <button type="button" className="button ghost" onClick={saveAudio} disabled={!audioFile} title="음성 원본 저장"><Download size={16}/>저장</button>
      <button type="button" className="button primary" onClick={()=>void transcribe()} disabled={!audioFile || status === "transcribing"}><WandSparkles size={16}/>{status === "transcribing" ? "처리 중" : status === "complete" ? "다시 전사" : "전사"}</button>
    </div>
    {previewUrl && <audio className="audio-preview" controls src={previewUrl}/>} 
    <small>{audioFile ? `${audioFile.name} · ${(audioFile.size / 1024 / 1024).toFixed(1)}MB` : "마이크 녹음 또는 최대 250MB 음성 파일"}</small>
    {transcriptionStep>0&&<div className="transcription-progress" aria-live="polite"><div className={`progress-track ${status==="transcribing"?"running":""}`}><i style={{width:transcriptionStep===1?"20%":transcriptionStep===2?"68%":"100%"}}/></div><ol><li className={transcriptionStep>=1?"done":""}>파일 확인</li><li className={transcriptionStep===2&&status==="transcribing"?"active":transcriptionStep>2?"done":""}>분할 및 AI 전사</li><li className={transcriptionStep===3?"done":""}>원문 반영</li></ol>{processError&&<p>{processError}</p>}</div>}
  </div>;
}
