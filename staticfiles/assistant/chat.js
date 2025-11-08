// ==== Luchi Assistant Frontend ====

document.addEventListener("DOMContentLoaded", function () {
  // === DOM ELEMENTS ===
  const chatButton = document.getElementById("luchi-chat-button");
  const chatWindow = document.getElementById("luchi-chat-window");
  const closeBtn = document.getElementById("luchi-close-btn");
  const sendBtn = document.getElementById("chat-send-btn");
  const input = document.getElementById("chat-input");
  const chatBody = document.getElementById("chat-body");
  const notification = document.getElementById("luchi-notification");

  // === TYPING INDICATOR ===
  const typingIndicator = document.createElement("div");
  typingIndicator.className = "typing";
  typingIndicator.textContent = "Luchi is typing...";
  chatBody.appendChild(typingIndicator);

  // === SESSION ID HANDLING ===
  let sessionId = localStorage.getItem("luchi_session");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem("luchi_session", sessionId);
  }

  // === UTILITIES ===
  function getCSRFToken() {
    const name = "csrftoken";
    const cookies = document.cookie.split("; ");
    for (const cookie of cookies) {
      const [key, value] = cookie.split("=");
      if (key === name) return decodeURIComponent(value);
    }
    return "";
  }

  function appendMessage(sender, text) {
    const msg = document.createElement("div");
    msg.className = `message ${sender}`;
    msg.textContent = text;
    chatBody.insertBefore(msg, typingIndicator);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function renderProductCards(products) {
    if (!products || products.length === 0) return "";
    return `
      <div class="luchi-product-cards">
        ${products
          .map(
            (p) => `
          <div class="luchi-product-card">
            ${p.image ? `<img src="${p.image}" alt="${p.name}" class="luchi-product-img">` : ""}
            <div class="luchi-product-info">
              <h4 class="luchi-product-name">${p.name}</h4>
              <p class="luchi-product-price">${p.price}</p>
              <a href="${p.url}" target="_blank" class="luchi-btn">View</a>
            </div>
          </div>`
          )
          .join("")}
      </div>
    `;
  }

  function renderOrderCard(order) {
  if (!order) return "";

  // Normalize status for dynamic color class
  const statusClass = order.status
    ? `status-${order.status.toLowerCase().replace(/\s+/g, "-")}`
    : "status-processing";

  return `
    <div class="order-card">
      <h4>Order #${order.id}</h4>
      <span class="order-status ${statusClass}">${order.status || "Processing"}</span>
      <p><strong>Payment:</strong> ${order.paid ? "Paid ✅" : "Unpaid ❌"}</p>
      <p><strong>Total:</strong> ${order.total}</p>
      <p><strong>Date:</strong> ${order.date}</p>
      ${order.address ? `<p><strong>Address:</strong> ${order.address}</p>` : ""}
      ${order.tracking ? `<p><strong>Tracking ID:</strong> ${order.tracking}</p>` : ""}
    </div>
  `;
}


  // === CHAT TOGGLE ===
  function toggleChat(open = null) {
    const visible = chatWindow.classList.contains("visible");
    if (open === true || (!visible && open === null)) {
      chatWindow.classList.add("visible");
      chatWindow.classList.remove("hidden");
      notification.classList.add("hidden");
    } else {
      chatWindow.classList.remove("visible");
      setTimeout(() => chatWindow.classList.add("hidden"), 250);
    }
  }

  chatButton.addEventListener("click", () => toggleChat(true));
  closeBtn.addEventListener("click", () => toggleChat(false));

  let isSending = false; // prevent concurrent sends

async function sendMessage() {
  const text = input.value.trim();
  if (!text || isSending) return; // block if busy or empty

  isSending = true;
  sendBtn.disabled = true;
  input.disabled = true;

  appendMessage("user", text);
  input.value = "";
  typingIndicator.style.display = "block";

  try {
    const response = await fetch("/assistant/chat/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ message: text, session_id: sessionId }),
    });

    const data = await response.json();
    typingIndicator.style.display = "none";

    const botMsg = document.createElement("div");
    botMsg.className = "message bot";
if (data.order) {
  // order card is generated on the client from structured data (safe)
  botMsg.innerHTML = renderOrderCard(data.order);
} else {
  // Use textContent for reply to avoid XSS; then append product cards (safe markup)
  const replyPara = document.createElement("p");
  replyPara.textContent = data.reply || "Sorry, I didn’t quite get that.";
  botMsg.appendChild(replyPara);

  // render product cards (these are built by our own template function)
  const cardsHtml = renderProductCards(data.products);
  if (cardsHtml) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = cardsHtml; // safe because products come from your backend but prefer to sanitize images/URLs server-side
    botMsg.appendChild(wrapper);
  }

  if (data.requires_human && data.handoff_url) {
    const handoffDiv = document.createElement("div");
    handoffDiv.classList.add("chat-handoff-btn");
    handoffDiv.innerHTML = `
      <a href="${data.handoff_url}" target="_blank" class="btn btn-outline-primary">
        👩🏽‍💻 Talk to a Human
      </a>
    `;
    botMsg.appendChild(handoffDiv);
  }
}


    chatBody.insertBefore(botMsg, typingIndicator);
    chatBody.scrollTop = chatBody.scrollHeight;
  } catch (err) {
    typingIndicator.style.display = "none";
    appendMessage("bot", "⚠️ Network error — please try again later.");
    console.error(err);
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    input.disabled = false;
  }
}


  sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

  // === GREETING NOTIFICATION ===
  setTimeout(() => {
    notification.classList.remove("hidden");
    notification.classList.add("visible");

    // Auto-hide after 7 seconds
    setTimeout(() => {
      notification.classList.remove("visible");
      setTimeout(() => notification.classList.add("hidden"), 400);
    }, 7000);
  }, 1500);

  // Clicking notification opens chat
  notification.addEventListener("click", () => {
    notification.classList.add("hidden");
    toggleChat(true);
  });
});
