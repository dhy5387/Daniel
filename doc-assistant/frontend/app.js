const API = "";  // 같은 origin

// DOM refs
const btnRecord = document.getElementById("btn-record");
const micLabel = document.getElementById("mic-label");
const recordingIndicator = document.getElementById("recording-indicator");
const transcriptBox = document.getElementById("transcript-box");
const btnFill = document.getElementById("btn-fill");
const btnReset = document.getElementById("btn-reset");
const sectionForm = document.getElementById("section-form");
const formFieldsList = document.getElementById("form-fields-list");
const issuesBanner = document.getElementById("issues-banner");
const btnCorrection = document.getElementById("btn-correction");
const btnSubmit = document.getElementById("btn-submit");
const sectionMessage = document.getElementById("section-message");
const correctionMessageBox = document.getElementById("correction-message-box");
const phoneMissingNotice = document.getElementById("phone-missing-notice");
const btnSendManual = document.getElementById("btn-send-manual");
const ocrUpload = document.getElementById("ocr-upload");
const ocrPreviewArea = document.getElementById("ocr-preview-area");
const ocrPreviewImg = document.getElementById("ocr-preview-img");
const ocrResult = document.getElementById("ocr-result");
const toast = document.getElementById("toast");
const loadingOverlay = document.getElementById("loading-overlay");
const loadingText = document.getElementById("loading-text");

// State
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let lastIssues = null;

// ─── Utilities ───────────────────────────────────────────────────────────────

function showToast(msg, duration = 2800) {
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), duration);
}

function setLoading(visible, text = "처리 중...") {
  loadingText.textContent = text;
  loadingOverlay.classList.toggle("hidden", !visible);
}

async function postJSON(url, body) {
  const res = await fetch(API + url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "요청 실패");
  }
  return res.json();
}

async function postFormData(url, formData) {
  const res = await fetch(API + url, { method: "POST", body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "요청 실패");
  }
  return res.json();
}

// ─── Recording ───────────────────────────────────────────────────────────────

btnRecord.addEventListener("click", async () => {
  if (isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
});

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    audioChunks = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(audioChunks, { type: "audio/webm" });
      await sendAudio(blob);
    };

    mediaRecorder.start(200);
    isRecording = true;
    btnRecord.classList.add("recording");
    micLabel.textContent = "녹음 중... 다시 누르면 완료";
    recordingIndicator.classList.remove("hidden");
  } catch (err) {
    showToast("마이크 접근 권한이 필요합니다: " + err.message);
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    isRecording = false;
    btnRecord.classList.remove("recording");
    micLabel.textContent = "마이크 버튼을 누르고 말씀해주세요";
    recordingIndicator.classList.add("hidden");
  }
}

async function sendAudio(blob) {
  setLoading(true, "음성 인식 중 (Whisper)...");
  try {
    const fd = new FormData();
    fd.append("audio", blob, "recording.webm");
    const data = await postFormData("/api/transcribe", fd);
    transcriptBox.value = data.transcript;
    btnFill.disabled = false;
    showToast("음성 인식 완료!");
  } catch (err) {
    showToast("음성 인식 실패: " + err.message);
  } finally {
    setLoading(false);
  }
}

// ─── Form Fill ───────────────────────────────────────────────────────────────

transcriptBox.addEventListener("input", () => {
  btnFill.disabled = transcriptBox.value.trim().length === 0;
});

btnFill.addEventListener("click", async () => {
  const transcript = transcriptBox.value.trim();
  if (!transcript) return;

  setLoading(true, "신청서 자동 기입 중 (GPT-4o)...");
  try {
    const data = await postJSON("/api/fill-form", { transcript });
    renderFormFields(data.fields);
    lastIssues = data.issues;

    sectionForm.classList.remove("hidden");
    sectionForm.scrollIntoView({ behavior: "smooth", block: "start" });

    if (data.has_issues) {
      const missingCount = data.issues.missing.length;
      const errorCount = data.issues.errors.length;
      const parts = [];
      if (missingCount) parts.push(`누락 ${missingCount}건`);
      if (errorCount) parts.push(`오류 ${errorCount}건`);
      issuesBanner.textContent = `⚠️ 검토 필요: ${parts.join(", ")} 발견되었습니다.`;
      issuesBanner.classList.remove("hidden");
      btnCorrection.classList.remove("hidden");
      btnSubmit.classList.add("hidden");
    } else {
      issuesBanner.classList.add("hidden");
      btnCorrection.classList.add("hidden");
      btnSubmit.classList.remove("hidden");
      showToast("모든 항목이 정상적으로 기입되었습니다!");
    }
  } catch (err) {
    showToast("폼 기입 실패: " + err.message);
  } finally {
    setLoading(false);
  }
});

function renderFormFields(fields) {
  formFieldsList.innerHTML = "";
  for (const f of fields) {
    const isOk = f.status === "정상";
    const row = document.createElement("div");
    row.className = `field-row status-${f.status}`;

    const icon = document.createElement("span");
    icon.className = `field-icon ${isOk ? "icon-ok" : "icon-ng"}`;
    icon.textContent = isOk ? "✓" : "✗";

    const name = document.createElement("span");
    name.className = "field-name";
    name.textContent = f.field.replace(/_/g, " ");

    const right = document.createElement("span");
    right.className = `field-right ${isOk ? "right-ok" : "right-ng"}`;
    right.textContent = isOk
      ? (f.value || "")
      : f.status + (f.reason ? ` · ${f.reason}` : "");

    row.appendChild(icon);
    row.appendChild(name);
    row.appendChild(right);
    formFieldsList.appendChild(row);
  }
}

// ─── Correction Message ───────────────────────────────────────────────────────

btnCorrection.addEventListener("click", async () => {
  if (!lastIssues) return;
  setLoading(true, "보완 요청 메시지 생성 중...");
  try {
    const data = await postJSON("/api/correction-message", lastIssues);
    correctionMessageBox.textContent = data.message;
    sectionMessage.classList.remove("hidden");
    sectionMessage.scrollIntoView({ behavior: "smooth", block: "start" });

    // 전화번호 누락 여부 확인
    const hasPhoneMissing = lastIssues.missing.some(
      (f) => f.includes("전화번호") || f.includes("연락처")
    );
    if (hasPhoneMissing) {
      phoneMissingNotice.classList.remove("hidden");
    } else {
      phoneMissingNotice.classList.add("hidden");
    }
  } catch (err) {
    showToast("메시지 생성 실패: " + err.message);
  } finally {
    setLoading(false);
  }
});

btnSubmit.addEventListener("click", () => {
  showToast("신청서가 제출되었습니다. 완료 안내 문자가 발송됩니다.");
  setTimeout(() => doReset(), 1200);
});

btnSendManual.addEventListener("click", () => {
  const phone = document.getElementById("manual-phone").value.trim();
  if (!phone) { showToast("전화번호를 입력해주세요"); return; }
  showToast(`${phone}으로 메시지가 발송되었습니다.`);
  phoneMissingNotice.classList.add("hidden");
});

function renderOcrResult(fields) {
  ocrResult.innerHTML = "";

  if (!fields || fields.length === 0) {
    ocrResult.textContent = "인식된 항목이 없습니다.";
    return;
  }

  const okCount = fields.filter(f => f.status === "정상").length;
  const ngCount = fields.filter(f => f.status === "누락").length;

  // 요약
  const summary = document.createElement("div");
  summary.className = "ocr-summary";
  summary.innerHTML =
    `총 ${fields.length}개 항목 · ` +
    `<span class="ocr-cnt good">${okCount}개 기입</span> · ` +
    `<span class="ocr-cnt low">${ngCount}개 누락</span>`;
  ocrResult.appendChild(summary);

  // 항목 목록
  for (const f of fields) {
    const isOk = f.status === "정상";
    const row = document.createElement("div");
    row.className = `ocr-item-row ${isOk ? "ocr-row-good" : "ocr-row-low"}`;

    row.innerHTML =
      `<span class="ocr-field-icon ${isOk ? "icon-ok" : "icon-ng"}">${isOk ? "✓" : "✗"}</span>` +
      `<span class="ocr-item-text">${f.field}</span>` +
      `<span class="ocr-field-status ${isOk ? "right-ok" : "right-ng"}">${isOk ? (f.value || "기입됨") : "누락"}</span>`;

    ocrResult.appendChild(row);
  }
}

// ─── Reset ────────────────────────────────────────────────────────────────────

btnReset.addEventListener("click", doReset);

function doReset() {
  transcriptBox.value = "";
  btnFill.disabled = true;
  sectionForm.classList.add("hidden");
  sectionMessage.classList.add("hidden");
  formFieldsList.innerHTML = "";
  issuesBanner.classList.add("hidden");
  btnCorrection.classList.add("hidden");
  btnSubmit.classList.add("hidden");
  lastIssues = null;
  ocrResult.classList.add("hidden");
  ocrPreviewArea.classList.add("hidden");
  ocrUpload.value = "";
}

// ─── OCR ─────────────────────────────────────────────────────────────────────

ocrUpload.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  ocrPreviewImg.src = URL.createObjectURL(file);
  ocrPreviewArea.classList.remove("hidden");

  setLoading(true, "신청서 항목 분석 중 (GPT-4o Vision)...");
  try {
    const fd = new FormData();
    fd.append("image", file, file.name);
    const data = await postFormData("/api/ocr", fd);

    renderOcrResult(data.fields || []);
    ocrResult.classList.remove("hidden");
    const missing = (data.fields || []).filter(f => f.status === "누락").length;
    showToast(`분석 완료 · 누락 ${missing}건 발견`);
  } catch (err) {
    ocrResult.innerHTML = `<div style="color:var(--danger);font-weight:600;">⚠ 분석 실패: ${err.message}</div>`;
    ocrResult.classList.remove("hidden");
    showToast("분석 실패: " + err.message, 5000);
  } finally {
    setLoading(false);
  }
});
