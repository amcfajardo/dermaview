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

    alert(result);

    if (result === "Code sent") {

      const username =
        e.target.username.value;

      localStorage.setItem(
        "reset_username",
        username
      );

      window.location.href =
        "verify-code.html";
    }

});