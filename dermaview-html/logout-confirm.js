(function () {
  document.addEventListener("click", async function (event) {
    const logoutLink = event.target.closest("a.logout-btn, a[href$='logout.php']");

    if (!logoutLink) {
      return;
    }

    event.preventDefault();

    const shouldLogout = await DermaViewDialog.confirm("Are you sure you want to log out of DermaView?", {
      title: "Log Out",
      okText: "Log Out"
    });

    if (shouldLogout) {
      window.location.href = logoutLink.href;
    }
  });
})();
