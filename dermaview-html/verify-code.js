document
  .getElementById("verifyCodeForm")
  .addEventListener("submit", async function (e) {

    e.preventDefault();

    const code =
      e.target.code.value;

    const username = localStorage.getItem("reset_employee");

    const formData = new FormData();

    formData.append(
      "employee_number",
      username
    );

    formData.append(
      "code",
      code
    );

    const response = await fetch(
      "verify-code.php",
      {
        method: "POST",
        body: formData
      }
    );

    const result =
      await response.text();

    await DermaViewDialog.alert(result, { title: "Verification Code" });

    if (result === "Code verified") {

      window.location.href =
        "reset-password.html";

    }

});

// Resend / cooldown logic
const resendButton = document.getElementById("resendButton");
const resendTimer = document.getElementById("resendTimer");

const COOLDOWN_MS = 30000; // 30 seconds
const COOLDOWN_S = COOLDOWN_MS / 1000;

function getSentAt() {
  const v = localStorage.getItem("reset_sent_at");
  return v ? parseInt(v, 10) : 0;
}

function setSentAt(ts) {
  localStorage.setItem("reset_sent_at", ts.toString());
}

function updateTimer() {
  const sentAt = getSentAt();
  if (!sentAt) {
    resendTimer.textContent = "";
    resendButton.disabled = false;
    return;
  }
  const elapsed = Math.floor((Date.now() - sentAt) / 1000);
  const remaining = COOLDOWN_S - elapsed;
  if (remaining > 0) {
    resendButton.disabled = true;
    resendTimer.textContent = `You can resend in ${remaining}s`;
  } else {
    resendButton.disabled = false;
    resendTimer.textContent = "You can resend the code now.";
  }
}

updateTimer();
setInterval(updateTimer, 1000);

resendButton.addEventListener("click", async function () {
  const username = localStorage.getItem("reset_employee");
  if (!username) {
    await DermaViewDialog.alert("No employee number or email to resend to.", { title: "Verification Code" });
    return;
  }

  // prevent spamming
  const sentAt = getSentAt();
  if (sentAt && Date.now() - sentAt < COOLDOWN_MS) {
    updateTimer();
    return;
  }

  const formData = new FormData();
  formData.append("employee_number", username);

  const response = await fetch("forgot-password.php", { method: "POST", body: formData });
  const result = await response.text();
  await DermaViewDialog.alert(result, { title: "Verification Code" });

  if (result === "Code sent") {
    setSentAt(Date.now());
    updateTimer();
  }

});
