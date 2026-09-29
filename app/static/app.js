const state = { projects: [], meetings: [], actions: [], decisions: [], view: "dashboard" };
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const labels = { dashboard:"대시보드", projects:"프로젝트", meetings:"회의", actions:"Action Items", decisions:"결정사항", todo:"할 일", in_progress:"진행 중", done:"완료", cancelled:"취소", low:"낮음", medium:"보통", high:"높음", draft:"초안", confirmed:"확정" };

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, { headers:{ "Content-Type":"application/json" }, ...options });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error?.message || body.detail || "요청을 처리하지 못했습니다.");
  }
  return response.status === 204 ? null : response.json();
}

const esc = (value = "") => String(value).replace(/[&<>'"]/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", "'":"&#39;", '"':"&quot;" }[c]));
const projectName = id => state.projects.find(project => project.id === id)?.name || "프로젝트 없음";
const fmtDate = value => value ? new Intl.DateTimeFormat("ko-KR", { month:"short", day:"numeric" }).format(new Date(`${value.slice(0, 10)}T00:00:00`)) : "기한 없음";
const empty = text => `<div class="empty">${esc(text)}</div>`;
const badge = value => `<span class="badge ${value}">${labels[value] || value}</span>`;
const controls = (type, id) => `<span class="row-actions"><button class="action-button" data-edit="${type}" data-id="${id}" title="수정">수정</button><button class="action-button danger" data-delete="${type}" data-id="${id}" title="삭제">삭제</button></span>`;

async function loadData() {
  try {
    const [projects, meetings, actions] = await Promise.all([api("/projects"), api("/meetings"), api("/action-items")]);
    state.projects = projects;
    state.meetings = meetings;
    state.actions = actions;
    const decisionSets = await Promise.all(projects.map(project => api(`/projects/${project.id}/decisions`)));
    state.decisions = decisionSets.flat().sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
    render();
  } catch (error) { toast(error.message); }
}

function render() {
  renderFilters();
  renderDashboard();
  renderProjects();
  renderMeetings();
  renderActions();
  renderDecisions();
}

function renderDashboard() {
  const open = state.actions.filter(item => !["done", "cancelled"].includes(item.status));
  const high = open.filter(item => item.risk_level === "high");
  const thisWeek = state.meetings.filter(meeting => {
    const days = (Date.now() - new Date(`${meeting.meeting_date}T00:00:00`)) / 86400000;
    return days >= 0 && days <= 7;
  }).length;
  const metrics = [["프로젝트", state.projects.length, "진행 중인 업무 공간"], ["회의", state.meetings.length, `최근 7일 ${thisWeek}건`], ["미완료 업무", open.length, "확인이 필요한 항목"], ["고위험 업무", high.length, "우선 조치 권장"]];
  $("#metrics").innerHTML = metrics.map(item => `<article class="metric"><small>${item[0]}</small><strong>${item[1]}</strong><small>${item[2]}</small></article>`).join("");
  $("#recent-meetings").innerHTML = state.meetings.slice(0, 5).map(meetingRow).join("") || empty("등록된 회의가 없습니다.");
  $("#risk-items").innerHTML = state.actions.filter(item => item.risk_level !== "low" && item.status !== "done").slice(0, 5).map(item => `<div class="list-row"><div><strong>${esc(item.task)}</strong><span class="meta">${esc(projectName(item.project_id))} · ${esc(item.assignee || "미지정")}</span></div>${badge(item.risk_level)}</div>`).join("") || empty("주의할 업무가 없습니다.");
  $("#recent-decisions").innerHTML = state.decisions.slice(0, 3).map(decisionCard).join("") || empty("등록된 결정사항이 없습니다.");
}

function renderProjects() {
  $("#projects-list").innerHTML = state.projects.map(project => {
    const meetingCount = state.meetings.filter(meeting => meeting.project_id === project.id).length;
    const openCount = state.actions.filter(item => item.project_id === project.id && !["done", "cancelled"].includes(item.status)).length;
    return `<article class="project-card"><div class="section-head"><p class="eyebrow">PROJECT ${project.id}</p>${controls("projects", project.id)}</div><h3>${esc(project.name)}</h3><p>${esc(project.description || "설명이 없습니다.")}</p><div class="card-foot"><span class="meta">회의 ${meetingCount} · 미완료 ${openCount}</span><button class="text-button" data-open-project="${project.id}">회의 보기 →</button></div></article>`;
  }).join("") || empty("첫 프로젝트를 만들어 보세요.");
}

function meetingRow(meeting) {
  const synced = meeting.notion_sync_status === "SYNCED";
  return `<div class="list-row"><div><strong>${esc(meeting.title)}</strong><span class="meta">${esc(projectName(meeting.project_id))} · ${esc((meeting.participants || []).join(", ") || "참석자 없음")}</span></div><div class="row-end"><span class="date-box">${fmtDate(meeting.meeting_date)}</span><button class="action-button notion-button ${synced ? "synced" : ""}" data-notion-sync="${meeting.id}" title="Notion으로 보내기">${synced ? "Notion 완료" : "Notion 전송"}</button>${controls("meetings", meeting.id)}</div></div>`;
}

function renderMeetings() {
  const query = $("#meeting-search").value.toLowerCase();
  const projectId = Number($("#meeting-project-filter").value);
  const rows = state.meetings.filter(meeting => (!projectId || meeting.project_id === projectId) && (!query || meeting.title.toLowerCase().includes(query) || (meeting.summary || "").toLowerCase().includes(query)));
  $("#meetings-list").innerHTML = rows.map(meetingRow).join("") || empty("조건에 맞는 회의가 없습니다.");
}

function renderActions() {
  const projectId = Number($("#action-project-filter").value);
  const status = $("#action-status-filter").value;
  const risk = $("#action-risk-filter").value;
  const rows = state.actions.filter(item => (!projectId || item.project_id === projectId) && (!status || item.status === status) && (!risk || item.risk_level === risk));
  $("#actions-list").innerHTML = rows.map(item => `<tr><td>${esc(item.task)}</td><td>${esc(projectName(item.project_id))}</td><td>${esc(item.assignee || "-")}</td><td>${fmtDate(item.due_date)}</td><td>${badge(item.status)}</td><td>${badge(item.risk_level)} <span class="meta">${item.risk_score}</span></td><td>${controls("actions", item.id)}</td></tr>`).join("") || `<tr><td colspan="7">${empty("조건에 맞는 업무가 없습니다.")}</td></tr>`;
}

function decisionCard(decision) {
  return `<article class="decision-card"><div class="section-head"><p class="eyebrow">${esc(projectName(decision.project_id))}</p>${controls("decisions", decision.id)}</div><h3>${esc(decision.topic)}</h3><p>${esc(decision.value)}</p><div class="card-foot">${badge(decision.status)}<span class="meta">${fmtDate(decision.updated_at)}</span></div></article>`;
}

function renderDecisions() {
  const projectId = Number($("#decision-project-filter").value);
  const rows = state.decisions.filter(decision => !projectId || decision.project_id === projectId);
  $("#decisions-list").innerHTML = rows.map(decisionCard).join("") || empty("등록된 결정사항이 없습니다.");
}

function renderFilters() {
  const options = state.projects.map(project => `<option value="${project.id}">${esc(project.name)}</option>`).join("");
  ["meeting-project-filter", "action-project-filter", "decision-project-filter"].forEach(id => {
    const element = $(`#${id}`);
    const value = element.value;
    element.innerHTML = `<option value="">모든 프로젝트</option>${options}`;
    element.value = value;
  });
}

function projectOptions(selected = "") {
  return `<option value="">선택하세요</option>${state.projects.map(project => `<option value="${project.id}" ${Number(selected) === project.id ? "selected" : ""}>${esc(project.name)}</option>`).join("")}`;
}

const forms = {
  projects: {
    singular:"프로젝트", endpoint:"/projects",
    fields:item => `<div class="field"><label>프로젝트명</label><input name="name" required value="${esc(item?.name || "")}" placeholder="예: FastAPI Portfolio"></div><div class="field"><label>설명</label><textarea name="description" placeholder="프로젝트의 목표를 입력하세요.">${esc(item?.description || "")}</textarea></div>`,
    payload:data => data
  },
  meetings: {
    singular:"회의", endpoint:"/meetings",
    fields:item => `<div class="field"><label>프로젝트</label><select name="project_id" required ${item ? "disabled" : ""}>${projectOptions(item?.project_id)}</select></div><div class="field"><label>회의 제목</label><input name="title" required value="${esc(item?.title || "")}"></div><div class="field"><label>회의 날짜</label><input name="meeting_date" type="date" required value="${item?.meeting_date || new Date().toISOString().slice(0, 10)}"></div><div class="field"><label>참석자</label><input name="participants" value="${esc((item?.participants || []).join(", "))}" placeholder="쉼표로 구분"></div><div class="field recorder-field"><label>실시간 회의 녹음</label><div class="recorder"><div class="record-status"><span id="record-dot"></span><strong id="record-state">녹음 대기</strong><time id="record-time">00:00</time></div><div class="record-actions"><button id="record-start" class="audio-button" type="button">녹음 시작</button><button id="record-pause" class="secondary" type="button" disabled>일시정지</button><button id="record-stop" class="secondary" type="button" disabled>정지</button></div><audio id="record-preview" controls hidden></audio></div><small>마이크 권한이 필요합니다. 녹음을 마친 뒤 음성 전사를 실행하세요.</small></div><div class="field audio-field"><label>녹음 파일 또는 기존 음성 파일</label><div class="file-row"><input id="audio-file" type="file" accept=".mp3,.mp4,.mpeg,.mpga,.m4a,.wav,.webm,audio/*"><button id="transcribe-btn" class="audio-button" type="button">음성 전사</button></div><small id="audio-source-label">MP3, M4A, WAV, WEBM 등 · 최대 25MB</small></div><div class="field"><label>회의 원문</label><textarea name="transcript" required placeholder="직접 입력하거나 녹음한 음성을 전사하세요.">${esc(item?.transcript || "")}</textarea></div>`,
    payload:(data, editing) => ({ ...(editing ? {} : { project_id:Number(data.project_id) }), title:data.title, meeting_date:data.meeting_date, participants:data.participants.split(",").map(value => value.trim()).filter(Boolean), transcript:data.transcript })
  },
  actions: {
    singular:"Action Item", endpoint:"/action-items",
    fields:item => `<div class="field"><label>프로젝트</label><select name="project_id" required ${item ? "disabled" : ""}>${projectOptions(item?.project_id)}</select></div><div class="field"><label>업무</label><input name="task" required value="${esc(item?.task || "")}"></div><div class="field"><label>담당자</label><input name="assignee" value="${esc(item?.assignee || "")}"></div><div class="field"><label>기한</label><input name="due_date" type="date" value="${item?.due_date || ""}"></div><div class="field"><label>상태</label><select name="status">${["todo","in_progress","done","cancelled"].map(value => `<option value="${value}" ${item?.status === value ? "selected" : ""}>${labels[value]}</option>`).join("")}</select></div><div class="field"><label>우선순위</label><select name="priority">${["low","medium","high"].map(value => `<option value="${value}" ${(item?.priority || "medium") === value ? "selected" : ""}>${labels[value]}</option>`).join("")}</select></div>`,
    payload:(data, editing) => ({ ...(editing ? {} : { project_id:Number(data.project_id) }), task:data.task, assignee:data.assignee || null, due_date:data.due_date || null, status:data.status, priority:data.priority })
  },
  decisions: {
    singular:"결정사항", endpoint:"/decisions",
    fields:item => `<div class="field"><label>프로젝트</label><select name="project_id" required ${item ? "disabled" : ""}>${projectOptions(item?.project_id)}</select></div><div class="field"><label>주제</label><input name="topic" required value="${esc(item?.topic || "")}"></div><div class="field"><label>결정 내용</label><textarea name="value" required>${esc(item?.value || "")}</textarea></div><div class="field"><label>상태</label><select name="status">${["draft","confirmed"].map(value => `<option value="${value}" ${(item?.status || "draft") === value ? "selected" : ""}>${labels[value]}</option>`).join("")}</select></div>`,
    payload:(data, editing) => ({ ...(editing ? {} : { project_id:Number(data.project_id) }), topic:data.topic, value:data.value, status:data.status })
  }
};

function showView(view) {
  state.view = view;
  $$(".view").forEach(element => element.classList.toggle("active", element.id === `${view}-view`));
  $$(".nav-item").forEach(element => element.classList.toggle("active", element.dataset.view === view));
  $("#page-title").textContent = labels[view];
  const createLabels = { dashboard:"+ 새 프로젝트", projects:"+ 새 프로젝트", meetings:"+ 새 회의", actions:"+ 새 업무", decisions:"+ 새 결정" };
  $("#create-btn").textContent = createLabels[view];
}

function openDialog(type, item = null, focusAudio = false) {
  if (type !== "projects" && !state.projects.length) { toast("프로젝트를 먼저 만들어 주세요."); showView("projects"); return; }
  const config = forms[type];
  $("#dialog-title").textContent = `${item ? "수정" : "새"} ${config.singular}`;
  $("#form-fields").innerHTML = config.fields(item);
  $("#form-error").textContent = "";
  $("#create-form").dataset.type = type;
  $("#create-form").dataset.id = item?.id || "";
  if (type === "meetings") resetRecorder();
  $("#create-dialog").showModal();
  if (focusAudio) setTimeout(() => $("#audio-file")?.click(), 100);
}

async function openEditor(type, id) {
  try {
    let item = state[type].find(value => value.id === id);
    if (type === "meetings") item = await api(`/meetings/${id}`);
    openDialog(type, item);
  } catch (error) { toast(error.message); }
}

async function removeItem(type, id) {
  const item = state[type].find(value => value.id === id);
  const name = item?.name || item?.title || item?.task || item?.topic || "이 항목";
  if (!window.confirm(`'${name}'을(를) 삭제할까요?`)) return;
  try {
    await api(`${forms[type].endpoint}/${id}`, { method:"DELETE" });
    toast("삭제했습니다.");
    await loadData();
  } catch (error) { toast(error.message); }
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("show");
  setTimeout(() => element.classList.remove("show"), 2600);
}

let mediaRecorder = null;
let microphoneStream = null;
let recordedAudio = null;
let recordedAudioUrl = null;
let recordStartedAt = 0;
let pausedAt = 0;
let pausedDuration = 0;
let recordTimer = null;

function resetRecorder() {
  if (mediaRecorder?.state === "recording" || mediaRecorder?.state === "paused") mediaRecorder.stop();
  microphoneStream?.getTracks().forEach(track => track.stop());
  if (recordedAudioUrl) URL.revokeObjectURL(recordedAudioUrl);
  mediaRecorder = null;
  microphoneStream = null;
  recordedAudio = null;
  recordedAudioUrl = null;
  clearInterval(recordTimer);
}

function closeDialog() {
  resetRecorder();
  $("#create-dialog").close();
}

function updateRecordTime() {
  const pausedNow = mediaRecorder?.state === "paused" ? Date.now() - pausedAt : 0;
  const elapsed = Math.max(0, Date.now() - recordStartedAt - pausedDuration - pausedNow);
  const seconds = Math.floor(elapsed / 1000);
  const time = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  if ($("#record-time")) $("#record-time").textContent = time;
}

function setRecorderUi(stateName) {
  const stateLabel = $("#record-state");
  const dot = $("#record-dot");
  if (!stateLabel || !dot) return;
  const labels = { idle:"녹음 대기", recording:"녹음 중", paused:"일시정지", ready:"녹음 완료" };
  stateLabel.textContent = labels[stateName];
  dot.className = stateName;
  $("#record-start").disabled = stateName === "recording" || stateName === "paused";
  $("#record-pause").disabled = !["recording", "paused"].includes(stateName);
  $("#record-pause").textContent = stateName === "paused" ? "계속 녹음" : "일시정지";
  $("#record-stop").disabled = !["recording", "paused"].includes(stateName);
}

async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    $("#form-error").textContent = "이 브라우저는 마이크 녹음을 지원하지 않습니다.";
    return;
  }
  try {
    resetRecorder();
    microphoneStream = await navigator.mediaDevices.getUserMedia({ audio:{ echoCancellation:true, noiseSuppression:true, autoGainControl:true } });
    const mimeCandidates = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"];
    const mimeType = mimeCandidates.find(type => MediaRecorder.isTypeSupported(type));
    mediaRecorder = new MediaRecorder(microphoneStream, mimeType ? { mimeType } : undefined);
    const chunks = [];
    mediaRecorder.addEventListener("dataavailable", event => { if (event.data.size) chunks.push(event.data); });
    mediaRecorder.addEventListener("stop", () => {
      const type = mediaRecorder.mimeType || "audio/webm";
      const extension = type.includes("mp4") ? "m4a" : "webm";
      recordedAudio = new File([new Blob(chunks, { type })], `decisionflow-recording-${Date.now()}.${extension}`, { type });
      recordedAudioUrl = URL.createObjectURL(recordedAudio);
      const preview = $("#record-preview");
      preview.src = recordedAudioUrl;
      preview.hidden = false;
      $("#audio-source-label").textContent = `녹음 완료 · ${(recordedAudio.size / 1024 / 1024).toFixed(1)}MB · 전사 준비됨`;
      microphoneStream?.getTracks().forEach(track => track.stop());
      clearInterval(recordTimer);
      setRecorderUi("ready");
    });
    mediaRecorder.start(1000);
    recordStartedAt = Date.now();
    pausedDuration = 0;
    recordTimer = setInterval(updateRecordTime, 500);
    updateRecordTime();
    setRecorderUi("recording");
    $("#form-error").textContent = "";
  } catch (error) {
    $("#form-error").textContent = error.name === "NotAllowedError" ? "브라우저에서 마이크 권한을 허용해 주세요." : "마이크를 시작하지 못했습니다.";
  }
}

function toggleRecordingPause() {
  if (mediaRecorder?.state === "recording") {
    mediaRecorder.pause();
    pausedAt = Date.now();
    setRecorderUi("paused");
  } else if (mediaRecorder?.state === "paused") {
    pausedDuration += Date.now() - pausedAt;
    mediaRecorder.resume();
    setRecorderUi("recording");
  }
}

function stopRecording() {
  if (["recording", "paused"].includes(mediaRecorder?.state)) mediaRecorder.stop();
}

$$('.nav-item').forEach(button => button.addEventListener('click', () => showView(button.dataset.view)));
$$('[data-go]').forEach(button => button.addEventListener('click', () => showView(button.dataset.go)));
$("#create-btn").addEventListener("click", () => openDialog(state.view === "dashboard" ? "projects" : state.view));
$("#global-audio-btn").addEventListener("click", () => openDialog("meetings", null, true));
$("#audio-meeting-btn").addEventListener("click", () => openDialog("meetings", null, true));
$("#refresh-btn").addEventListener("click", loadData);
["close-dialog", "cancel-dialog"].forEach(id => $("#" + id).addEventListener("click", closeDialog));

document.addEventListener("click", event => {
  const edit = event.target.closest("[data-edit]");
  const remove = event.target.closest("[data-delete]");
  const project = event.target.closest("[data-open-project]");
  const notionSync = event.target.closest("[data-notion-sync]");
  if (edit) openEditor(edit.dataset.edit, Number(edit.dataset.id));
  if (remove) removeItem(remove.dataset.delete, Number(remove.dataset.id));
  if (project) { showView("meetings"); $("#meeting-project-filter").value = project.dataset.openProject; renderMeetings(); }
  if (notionSync) syncToNotion(Number(notionSync.dataset.notionSync), notionSync);
});

async function syncToNotion(meetingId, button) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "전송 중...";
  try {
    const result = await api(`/meetings/${meetingId}/notion-sync`, { method:"POST" });
    toast(result.status === "ALREADY_SYNCED" ? "이미 Notion에 전송된 회의입니다." : "Notion에 전송했습니다.");
    await loadData();
  } catch (error) {
    toast(error.message);
    button.disabled = false;
    button.textContent = original;
  }
}

$("#create-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const type = form.dataset.type;
  const id = form.dataset.id;
  const editing = Boolean(id);
  const data = Object.fromEntries(new FormData(form));
  try {
    const payload = forms[type].payload(data, editing);
    await api(`${forms[type].endpoint}${editing ? `/${id}` : ""}`, { method:editing ? "PATCH" : "POST", body:JSON.stringify(payload) });
    closeDialog();
    toast(editing ? "수정했습니다." : "저장했습니다.");
    await loadData();
  } catch (error) { $("#form-error").textContent = error.message; }
});

$("#form-fields").addEventListener("click", async event => {
  if (event.target.id === "record-start") { await startRecording(); return; }
  if (event.target.id === "record-pause") { toggleRecordingPause(); return; }
  if (event.target.id === "record-stop") { stopRecording(); return; }
  if (event.target.id !== "transcribe-btn") return;
  const input = $("#audio-file");
  const file = recordedAudio || input.files[0];
  const button = event.target;
  if (!file) { $("#form-error").textContent = "음성 파일을 먼저 선택해 주세요."; return; }
  if (file.size > 25 * 1024 * 1024) { $("#form-error").textContent = "음성 파일은 최대 25MB까지 가능합니다."; return; }
  const data = new FormData();
  data.append("file", file);
  button.disabled = true;
  button.textContent = "전사 중...";
  $("#form-error").textContent = "";
  try {
    const response = await fetch("/api/transcriptions", { method:"POST", body:data });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error?.message || "음성 전사에 실패했습니다.");
    $("textarea[name='transcript']").value = result.text;
    toast("음성을 회의 원문으로 변환했습니다.");
  } catch (error) { $("#form-error").textContent = error.message; }
  finally { button.disabled = false; button.textContent = "음성 전사"; }
});

$("#form-fields").addEventListener("change", event => {
  if (event.target.id !== "audio-file" || !event.target.files[0]) return;
  recordedAudio = null;
  $("#audio-source-label").textContent = `선택 파일: ${event.target.files[0].name}`;
});

$("#meeting-search").addEventListener("input", renderMeetings);
["meeting-project-filter", "action-project-filter", "action-status-filter", "action-risk-filter", "decision-project-filter"].forEach(id => $("#" + id).addEventListener("change", render));
loadData();
