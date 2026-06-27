document
  .getElementById("forgotPasswordForm")
  .addEventListener("submit", async function (e) {

    e.preventDefault();

    const formData = new FormData(e.target);

    const response = await fetch(
      "forgot-password.php",
      {
        method: "POST",
        body: formData
      }
    );

    const result = await response.text();

    await DermaViewDialog.alert(result, { title: "Password Reset" });

    if (result === "Code sent") {

      const employee = e.target.employee_number.value;

      localStorage.setItem("reset_employee", employee);
      // store timestamp (ms) when code was sent
      localStorage.setItem("reset_sent_at", Date.now().toString());

      window.location.href = "verify-code.html";
    }

});
