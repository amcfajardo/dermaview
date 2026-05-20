document
  .getElementById("loginForm")
  .addEventListener("submit", async function (e) {

    e.preventDefault();

    const form = e.target;

    const formData = new FormData(form);

    try {

      const response = await fetch("login.php", {
        method: "POST",
        body: formData,
      });

      const result = await response.text();

      alert(result);

      if (result === "Login successful") {

        window.location.href = "index.html";

      }

    } catch (error) {

      console.error(error);

      alert("Something went wrong");

    }

});