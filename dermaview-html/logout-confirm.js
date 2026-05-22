(function () {
  document.addEventListener("click", function (event) {
    const logoutLink = event.target.closest("a.logout-btn, a[href$='logout.php']");

    if (!logoutLink) {
      return;
    }

    const shouldLogout = window.confirm("Are you sure you want to log out of DermaView?");

    if (!shouldLogout) {
      event.preventDefault();
    }
  });
})();
