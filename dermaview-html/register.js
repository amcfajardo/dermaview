document
  .getElementById("registerForm")
  .addEventListener("submit", async function (e) {

    e.preventDefault();

    const form = e.target;

    const formData = new FormData(form);

    try {

      const response = await fetch("register.php", {
        method: "POST",
        body: formData,
      });

      const result = await response.text();

      alert(result);

      if (result === "Registration successful") {
        window.location.href = "index.html";
      }

    } catch (error) {

      console.error(error);

      alert("Something went wrong");

    }

});