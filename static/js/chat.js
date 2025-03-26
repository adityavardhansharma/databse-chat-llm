document.addEventListener("DOMContentLoaded", function () {
  // --- DOM Elements ---
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const messageStream = document.getElementById("message-stream");
  const messageStreamWrapper = document.querySelector(".message-stream-wrapper");
  const themeToggle = document.getElementById("theme-toggle"); // ID remains the same
  const clearChatBtn = document.getElementById("clear-chat"); // ID remains the same
  const suggestionPills = document.querySelectorAll(".suggestion-pill");
  const htmlElement = document.documentElement;

  // --- State ---
  let isFetching = false;

  // --- Theme Handling ---
  const applyTheme = (theme, animate = false) => {
    const oldTheme = htmlElement.getAttribute("data-theme");
    htmlElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);

    if (animate && oldTheme !== theme) {
      // Simple crossfade background animation
      const tempDiv = document.createElement("div");
      tempDiv.style.position = "fixed";
      tempDiv.style.inset = "0";
      tempDiv.style.backgroundColor =
        oldTheme === "dark" ? "var(--bg-dark)" : "var(--bg-light)"; // Use CSS vars
      tempDiv.style.zIndex = "-1";
      document.body.appendChild(tempDiv);

      gsap.to(tempDiv, {
        opacity: 0,
        duration: 0.6,
        ease: "power1.inOut",
        onComplete: () => tempDiv.remove(),
      });

      // Animate theme toggle button (optional subtle animation on the switch itself)
      gsap.fromTo(
        themeToggle, // Target the button itself
        { scale: 0.95 }, // Subtle scale
        {
          scale: 1,
          duration: 0.4, // Faster than original icon rotation
          ease: "back.out(1.7)",
        }
      );
    }
  };

  const initializeTheme = () => {
    const savedTheme = localStorage.getItem("theme");
    const prefersDark =
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(savedTheme || (prefersDark ? "dark" : "light"));
  };

  themeToggle.addEventListener("click", () => {
    const currentTheme = htmlElement.getAttribute("data-theme") || "light";
    applyTheme(currentTheme === "light" ? "dark" : "light", true); // Animate the change
  });

  // --- Markdown Rendering ---
  marked.setOptions({
    gfm: true,
    breaks: true,
    smartLists: true,
    highlight: (code) => code, // No syntax highlighting configured
  });

  const renderMarkdown = (content) => {
    const rawHtml = marked.parse(content);
    return DOMPurify.sanitize(rawHtml, { USE_PROFILES: { html: true } });
  };

  // --- Textarea Auto-Resize ---
  const autoResizeTextarea = () => {
    userInput.style.height = "auto";
    const scrollHeight = userInput.scrollHeight;
    const maxHeight = parseInt(getComputedStyle(userInput).maxHeight, 10) || 120; // Match CSS
    userInput.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
  };
  userInput.addEventListener("input", autoResizeTextarea);

  // --- Message Handling ---
  const scrollToBottom = (delay = 0) => {
    gsap.to(messageStreamWrapper, {
      scrollTop: messageStream.scrollHeight,
      duration: 0.5,
      delay: delay,
      ease: "power2.out",
    });
  };

  const addMessage = (content, type) => {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${type}-message`;
    if (type === "thinking") messageDiv.id = "thinking-message";

    const messageContent = document.createElement("div");
    messageContent.className = "message-content";

    if (type === "thinking") {
      messageContent.innerHTML = `
        <div class="pulsing-orb"></div>
        <span>Thinking...</span>
      `;
    } else if (type === "assistant") {
      messageContent.innerHTML = renderMarkdown(content);
    } else if (
      type === "system" &&
      !messageDiv.classList.contains("initial-system-message")
    ) {
      messageContent.innerHTML = `<p>${content}</p>`;
    } else if (type !== "system") {
      messageContent.textContent = content;
    } else {
      messageContent.innerHTML = content; // Assume initial system message content is safe HTML
    }

    if (!messageDiv.classList.contains("initial-system-message")) {
      messageDiv.appendChild(messageContent);
    } else {
      return document.querySelector(".initial-system-message");
    }

    const xOffset = type === "user" ? 20 : -20;
    gsap.set(messageDiv, { opacity: 0, scale: 0.95, x: xOffset, y: 15 }); // Slightly different entry

    messageStream.appendChild(messageDiv);

    gsap.to(messageDiv, {
      opacity: 1,
      scale: 1,
      x: 0,
      y: 0,
      duration: 0.6,
      ease: "elastic.out(1, 0.8)", // Slightly adjusted ease
      onComplete: () => {
        scrollToBottom(0.1);
      },
    });

    return messageDiv;
  };

  // --- API Interaction ---
  const sendMessage = async (message) => {
    if (isFetching) return;
    isFetching = true;
    let thinkingMessage;

    try {
      thinkingMessage = addMessage("", "thinking");
      scrollToBottom();

      const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: message }),
      });

      if (thinkingMessage) {
        gsap.to(thinkingMessage, {
          opacity: 0,
          scale: 0.8,
          height: 0,
          paddingTop: 0, // Animate padding
          paddingBottom: 0,
          marginTop: 0, // Animate margin
          marginBottom: 0,
          duration: 0.4,
          ease: "power1.in",
          onComplete: () => thinkingMessage.remove(),
        });
      }

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();

      if (data.error) {
        addMessage(`Error: ${data.error}`, "system");
      } else {
        addMessage(data.response, "assistant");
      }
    } catch (error) {
      console.error("Error sending message:", error);
      const currentThinking = document.getElementById("thinking-message");
      if (currentThinking) currentThinking.remove();
      addMessage("Failed to connect. Please try again.", "system");
    } finally {
      isFetching = false;
    }
  };

  // --- Event Listeners ---
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (message === "" || isFetching) return;

    addMessage(message, "user");
    userInput.value = "";
    autoResizeTextarea();
    userInput.focus();
    sendMessage(message);

    gsap.fromTo(
      ".send-button",
      { scale: 0.9 },
      { scale: 1, duration: 0.4, ease: "elastic.out(1, 0.5)" }
    );
  });

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  suggestionPills.forEach((pill) => {
    pill.addEventListener("click", function () {
      if (isFetching) return;
      const query = this.getAttribute("data-query");
      userInput.value = query;
      autoResizeTextarea();
      userInput.focus();
      gsap.fromTo(
        this,
        { scale: 0.95 },
        { scale: 1, duration: 0.3, ease: "back.out(1.7)" }
      );
    });
  });

  clearChatBtn.addEventListener("click", () => {
    const messagesToRemove = messageStream.querySelectorAll(
      ".message:not(.initial-system-message)"
    );
    if (messagesToRemove.length === 0 || isFetching) return;

    gsap.fromTo(
      clearChatBtn,
      { rotation: -360 },
      { rotation: 0, duration: 0.5, ease: "back.out(1.7)" }
    );

    gsap.to(messagesToRemove, {
      opacity: 0,
      scale: 0.85, // Less drastic scale down
      y: 25,
      duration: 0.4,
      stagger: 0.04, // Slightly faster stagger
      ease: "power2.in",
      onComplete: () => {
        messagesToRemove.forEach((msg) => msg.remove());
      },
    });
  });

  // --- Initialization ---
  initializeTheme();
  autoResizeTextarea();
  userInput.focus();

  const initialMessage = document.querySelector(".initial-system-message");
  if (initialMessage) {
    gsap.from(initialMessage, {
      opacity: 0,
      y: 30,
      scale: 0.95,
      delay: 0.3,
      duration: 0.7,
      ease: "elastic.out(1, 0.8)",
    });
  }
});
