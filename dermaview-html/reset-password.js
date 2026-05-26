document
  .getElementById("resetPasswordForm")
  .addEventListener("submit", async function (e) {

    e.preventDefault();

    const username = localStorage.getItem("reset_employee");
    const password = e.target.password.value;
    const confirm = e.target.confirm_password ? e.target.confirm_password.value : null;

    if (confirm !== null && password !== confirm) {
      alert("Passwords do not match");
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

    const response = await fetch(
      "reset-password.php",
      {
        method: "POST",
        body: formData
      }
    );

    const result =
      await response.text();

    alert(result);

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