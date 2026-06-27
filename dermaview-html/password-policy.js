(function () {
  const message = 'Password must be at least 8 characters and include uppercase, lowercase, number, and special character.';
  const pattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

  window.passwordPolicyMessage = message;
  window.isPasswordComplexEnough = function (password) {
    return pattern.test(password || '');
  };
})();
