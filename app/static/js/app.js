function printdropUI() {
  return {
    sidebarOpen: false,
    confirmTitle: "Confirm action",
    confirmMessage: "Are you sure you want to continue?",
    pendingConfirm: null,
    askConfirm(title, message, callback) {
      this.confirmTitle = title;
      this.confirmMessage = message;
      this.pendingConfirm = callback;
      this.$refs.confirmDialog.showModal();
    },
    resetConfirm() {
      this.pendingConfirm = null;
    },
    confirmAction() {
      if (typeof this.pendingConfirm === "function") {
        this.pendingConfirm();
      }
      this.$refs.confirmDialog.close();
    },
  };
}

document.body.addEventListener("htmx:afterSwap", () => {
  // Ensure freshly swapped forms stay keyboard-navigable with consistent focus outlines.
  const firstAutofocus = document.querySelector("[autofocus]");
  if (firstAutofocus && document.activeElement === document.body) {
    firstAutofocus.focus();
  }
});
