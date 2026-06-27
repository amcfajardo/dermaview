document
  .getElementById("resetPasswordForm")
  .addEventListener("submit", async function (e) {

    e.preventDefault();

    const username = localStorage.getItem("reset_employee");
    const password = e.target.password.value;
    const confirm = e.target.confirm_password ? e.target.confirm_password.value : null;

    if (confirm !== null && password !== confirm) {
      await DermaViewDialog.alert("Passwords do not match", { title: "Reset Password" });
      return;
    }

    if (window.isPasswordComplexEnough && !window.isPasswordComplexEnough(password)) {
      await DermaViewDialog.alert(window.passwordPolicyMessage, { title: "Password Requirement" });
      return;
    }

    const formData = new FormData();

    formData.append(
      "employee_number",
      username
    );

    formData.append(
      "password",
      password
    );
    formData.append(
      "confirm_password",
      confirm
    );

    const response = await fetch(
      "reset-password.php",
      {
        method: "POST",
        body: formData
      }
    );

    const result =
      await response.text();

    await DermaViewDialog.alert(result, { title: "Reset Password" });

    if (
      result ===
      "Password updated"
    ) {

      localStorage.removeItem(
        "reset_employee"
      );

      window.location.href =
        "index.html";

    }

});
