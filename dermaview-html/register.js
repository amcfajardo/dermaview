(function () {
  const form = document.getElementById("registerForm");
  const otpInput = document.getElementById("registrationOtp");
  const submitButton = form ? form.querySelector(".auth-button") : null;
  let otpRequested = false;

  if (!form) return;

  function setRegistrationFieldsReadOnly(isReadOnly) {
    ["email", "first_name", "last_name", "password", "confirm_password"].forEach((name) => {
      const field = form.elements[name];
      if (field) field.readOnly = isReadOnly;
    });
  }

  function resetOtpStep() {
    otpRequested = false;
    setRegistrationFieldsReadOnly(false);
    otpInput.value = "";
    otpInput.hidden = true;
    otpInput.required = false;
    if (submitButton) submitButton.textContent = "Send OTP";
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const password = form.password.value;
    const confirmPassword = form.confirm_password.value;

    if (!otpRequested && password !== confirmPassword) {
      await DermaViewDialog.alert("Passwords do not match", { title: 'Registration' });
      form.confirm_password.focus();
      return;
    }

    if (!otpRequested && window.isPasswordComplexEnough && !window.isPasswordComplexEnough(password)) {
      await DermaViewDialog.alert(window.passwordPolicyMessage, { title: 'Password Requirement' });
      return;
    }

    if (otpRequested && !/^\d{6}$/.test(otpInput.value.trim())) {
      await DermaViewDialog.alert("Enter the 6-digit OTP sent to your email.", { title: 'OTP Required' });
      otpInput.focus();
      return;
    }

    const formData = new FormData(form);
    formData.append("action", otpRequested ? "verify_otp" : "request_otp");

    try {
      if (submitButton) submitButton.disabled = true;

      const response = await fetch("register.php", {
        method: "POST",
        body: formData,
      });

      const result = await response.text();

      if (result === "OTP sent") {
        await DermaViewDialog.alert("We sent a 6-digit OTP to your email.", { title: 'OTP Sent' });
        otpRequested = true;
        setRegistrationFieldsReadOnly(true);
        otpInput.hidden = false;
        otpInput.required = true;
        otpInput.focus();
        if (submitButton) submitButton.textContent = "Verify OTP & Create Account";
        return;
      }

      if (result === "Please request a new OTP" || result === "OTP expired. Please request a new OTP.") {
        await DermaViewDialog.alert(result, { title: 'OTP Needed' });
        resetOtpStep();
        return;
      }

      if (result === "Registration successful") {
        await DermaViewDialog.alert("Your account has been created and is waiting for admin role assignment.", { title: 'Registration Successful' });
        window.location.href = "index.html";
        return;
      }

      await DermaViewDialog.alert(result, { title: 'Registration' });
    } catch (error) {
      console.error(error);
      await DermaViewDialog.alert("Something went wrong", { title: 'Registration Error' });
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  });
})();
