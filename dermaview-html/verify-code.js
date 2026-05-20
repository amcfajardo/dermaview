document
  .getElementById("verifyCodeForm")
  .addEventListener("submit", async function (e) {

    e.preventDefault();

    const code =
      e.target.code.value;

    const username =
      localStorage.getItem(
        "reset_username"
      );

    const formData = new FormData();

    formData.append(
      "username",
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

    alert(result);

    if (result === "Code verified") {

      window.location.href =
        "reset-password.html";

    }

});