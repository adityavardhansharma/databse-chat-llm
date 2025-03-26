document.addEventListener("DOMContentLoaded", function () {
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const messagesContainer = document.getElementById("messages-container");
  const themeToggle = document.getElementById("theme-toggle");
  const clearChat = document.getElementById("clear-chat");
  const suggestionChips = document.querySelectorAll(".suggestion-chip");

  // Theme toggle functionality
  themeToggle.addEventListener("click", function() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute("data-theme") || "light";
    const newTheme = currentTheme === "light" ? "dark" : "light";

    html.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);

    // Update icon
    const icon = themeToggle.querySelector("i");
    if (newTheme === "dark") {
      icon.classList.remove("fa-moon");
      icon.classList.add("fa-sun");
    } else {
      icon.classList.remove("fa-sun");
      icon.classList.add("fa-moon");
    }
  });

  // Apply saved theme or system preference
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme) {
    document.documentElement.setAttribute("data-theme", savedTheme);
    if (savedTheme === "dark") {
      themeToggle.querySelector("i").classList.replace("fa-moon", "fa-sun");
    }
  } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    document.documentElement.setAttribute("data-theme", "dark");
    themeToggle.querySelector("i").classList.replace("fa-moon", "fa-sun");
  }

  // Configure marked.js for proper markdown rendering
  marked.setOptions({
    gfm: true,
    breaks: true,
    smartLists: true,
    highlight: function(code, lang) {
      if (window.hljs && lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return code;
    }
  });

  // Function to safely render markdown
  function renderMarkdown(content) {
    const rawHtml = marked.parse(content);
    return DOMPurify.sanitize(rawHtml);
  }

  // Auto-resize textarea as user types
  userInput.addEventListener("input", function() {
    this.style.height = "auto";
    const newHeight = Math.min(this.scrollHeight, 120);
    this.style.height = newHeight + "px";
  });

  // Function to add a message to the chat
  function addMessage(content, type) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${type}-message`;
    messageDiv.id = type === "thinking" ? "thinking-message" : null;

    const messageContent = document.createElement("div");
    messageContent.className = "message-content";

    if (type === "thinking") {
      messageContent.innerHTML = `
        <div class="dots-container">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
        <span>Processing query...</span>
      `;
    } else if (type === "assistant") {
      messageContent.innerHTML = renderMarkdown(content);

      // Apply syntax highlighting to code blocks
      messageContent.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
      });
    } else {
      messageContent.textContent = content;
    }

    messageDiv.appendChild(messageContent);
    messagesContainer.appendChild(messageDiv);

    // Scroll to the bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return messageDiv;
  }

  // Function to send message to backend
  async function sendMessage(message) {
    try {
      // Show thinking message
      const thinkingMessage = addMessage("", "thinking");

      const response = await fetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: message }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Remove thinking message
      thinkingMessage.remove();

      if (data.error) {
        addMessage(
          `I couldn't process that query. Error: ${data.error}`,
          "system"
        );
      } else {
        // Add the response message
        addMessage(data.response, "assistant");
      }
    } catch (error) {
      console.error("Error:", error);

      // Remove thinking message if it exists
      const thinkingMessage = document.getElementById("thinking-message");
      if (thinkingMessage) {
        thinkingMessage.remove();
      }

      addMessage(
        "I encountered an error processing your request. Please try again.",
        "system"
      );
    }
  }

  // Handle form submission
  chatForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const message = userInput.value.trim();
    if (message === "") return;

    // Add user message to chat
    addMessage(message, "user");

    // Clear input field and reset height
    userInput.value = "";
    userInput.style.height = "";
    userInput.focus();

    // Send message to backend
    sendMessage(message);
  });

  // Handle suggestion chips
  suggestionChips.forEach(chip => {
    chip.addEventListener("click", function() {
      const query = this.getAttribute("data-query");
      userInput.value = query;

      // Manually dispatch submit event
      chatForm.dispatchEvent(new Event("submit"));
    });
  });

  // Clear chat functionality
  clearChat.addEventListener("click", function() {
    // Keep only the first welcome message
    while (messagesContainer.children.length > 1) {
      messagesContainer.removeChild(messagesContainer.lastChild);
    }
  });

  // Submit with Enter (allow Shift+Enter for new lines)
  userInput.addEventListener("keydown", function(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  // Focus input field on load
  userInput.focus();
});
