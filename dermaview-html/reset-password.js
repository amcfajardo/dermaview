document
  .getElementById("resetPasswordForm")
  .addEventListener("submit", async function (e) {

    e.preventDefault();

    const username =
      localStorage.getItem(
        "reset_username"
      );

    const password =
      e.target.password.value;

    const formData = new FormData();

    formData.append(
      "username",
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
        "reset_username"
      );

      window.location.href =
        "login.html";

    }

});