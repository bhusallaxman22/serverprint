function printdropUI() {
  const storedCollapsed = (() => {
    try {
      return localStorage.getItem("printdrop.sidebarCollapsed") === "1";
    } catch (_err) {
      return false;
    }
  })();

  return {
    sidebarOpen: false,
    sidebarCollapsed: storedCollapsed,
    liveToasts: [],
    confirmTitle: "Confirm action",
    confirmMessage: "Are you sure you want to continue?",
    pendingConfirm: null,
    createUserOpen: false,
    init() {
      const onToast = (event) => {
        const detail = event.detail;
        if (Array.isArray(detail)) {
          detail.forEach((flash) => this.pushToast(flash.level || "info", flash.message || ""));
          return;
        }
        if (detail && detail.message) {
          this.pushToast(detail.level || "info", detail.message);
        }
      };
      document.body.addEventListener("printdrop:toast", onToast);
      document.body.addEventListener("printdrop:close-create-user", () => {
        this.closeCreateUser();
      });
    },
    openSidebar() {
      this.sidebarOpen = true;
    },
    closeSidebar() {
      this.sidebarOpen = false;
    },
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen;
    },
    toggleCollapsed() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
      try {
        localStorage.setItem("printdrop.sidebarCollapsed", this.sidebarCollapsed ? "1" : "0");
      } catch (_err) {
        /* ignore quota / private mode */
      }
    },
    toggleNav() {
      if (window.matchMedia("(min-width: 1024px)").matches) {
        this.toggleCollapsed();
      } else {
        this.toggleSidebar();
      }
    },
    pushToast(level, message) {
      if (!message) return;
      const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      this.liveToasts.push({ id, level, message });
      setTimeout(() => {
        this.liveToasts = this.liveToasts.filter((toast) => toast.id !== id);
      }, 4200);
    },
    openCreateUser() {
      this.createUserOpen = true;
    },
    closeCreateUser() {
      this.createUserOpen = false;
    },
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
  const firstAutofocus = document.querySelector("[autofocus]");
  if (firstAutofocus && document.activeElement === document.body) {
    firstAutofocus.focus();
  }
});
