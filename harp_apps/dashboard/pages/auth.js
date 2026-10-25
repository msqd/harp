"use strict";

// Sign-in and setup pages. The setup secret travels in the fragment of the URL, which the browser never sends: it is
// read here and posted in the body.
const page = document.body.dataset.page;
const form = document.querySelector("form");
const problem = document.querySelector("[data-error]");
const button = form.querySelector("button");

function show(message) {
  problem.textContent = message;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  show("");
  const data = new FormData(form);
  const body = { username: data.get("username"), password: data.get("password") };
  if (page === "setup") {
    if (body.password !== data.get("confirm")) {
      show("The two passwords differ.");
      return;
    }
    body.secret = decodeURIComponent(window.location.hash.slice(1));
    if (!body.secret) {
      show("Open the setup link HARP wrote in its logs: this page needs its secret.");
      return;
    }
  }
  button.disabled = true;
  try {
    const response = await fetch(page === "setup" ? "/api/auth/setup" : "/api/auth/signin", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (response.ok) {
      window.location.replace("/");
      return;
    }
    const answer = await response.json().catch(() => ({}));
    show(answer.message || "Something went wrong (" + response.status + ").");
  } catch (error) {
    show("The server could not be reached.");
  } finally {
    button.disabled = false;
  }
});
