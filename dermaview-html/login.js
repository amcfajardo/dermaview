document
  .getElementById("loginForm")
  .addEventListener("submit", async function (e) {

    e.preventDefault();

    const form = e.target;

    const formData = new FormData(form);

    try {
      const resp = await fetch("login.php", { method: "POST", body: formData });
      const text = await resp.text();

      // try parse JSON response
      let parsed = null;
      try {
        parsed = JSON.parse(text);
      } catch (e) {
        parsed = null;
      }

      if (parsed && parsed.status === 'ok') {
        if (parsed.redirect) {
          window.location.href = parsed.redirect;
          return;
        }

        const role = String(parsed.role || '').trim().toLowerCase().replace(/[\s_-]+/g, '');
        if (role === 'admin' || role === 'superadmin') {
          window.location.href = 'admin.html';
        } else {
          window.location.href = 'index.html';
        }
        return;
      }

      // fallback: server returned plain text (older code). If it indicates success, fetch session role.
      if (text && text.indexOf('Login successful') !== -1) {
        try {
          const s = await fetch('get-session.php');
          const session = await s.json();
          const role = String(session.role || '').trim().toLowerCase().replace(/[\s_-]+/g, '');
          if (session.status === 'ok' && (role === 'admin' || role === 'superadmin')) {
            window.location.href = 'admin.html';
            return;
          }
        } catch (e) {
          console.warn('get-session failed', e);
        }
        // default redirect
        window.location.href = 'index.html';
        return;
      }

      // show server message if available
      if (parsed && parsed.message) {
        alert(parsed.message);
      } else {
        alert(text || 'Login failed');
      }

    } catch (error) {
      console.error(error);
      alert('Something went wrong');
    }

});
