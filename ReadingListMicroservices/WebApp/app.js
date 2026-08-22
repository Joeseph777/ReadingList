// ══════════════════════════════════════════════════════════════════════
//  State
// ══════════════════════════════════════════════════════════════════════
let state = {
  token: localStorage.getItem("rl_token") || null,
  username: localStorage.getItem("rl_username") || null,
  userId: localStorage.getItem("rl_user_id") ? parseInt(localStorage.getItem("rl_user_id"), 10) : null,
  isAdmin: localStorage.getItem("rl_is_admin") === "true",
  books: [],
  users: [],
  friendSearch: "",
  friendSearchResults: [],
  friends: { friends: [], incoming_requests: [], outgoing_requests: [] },
  friendsTab: "list",       // 'list' | 'requests' | 'find'
  viewingFriend: null,      // { id, username } when looking at a friend's shelf
  friendBooks: [],
  view: "books",         // 'books' | 'users' | 'friends'
  filter: "all",         // 'all' | 'unread' | 'progress' | 'completed'
  search: "",
  sort: "title",
};

// ══════════════════════════════════════════════════════════════════════
//  API helpers
// ══════════════════════════════════════════════════════════════════════
async function apiRequest(base, path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && state.token) headers["Authorization"] = `Bearer ${state.token}`;

  let resp;
  try {
    resp = await fetch(base + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new Error(
      `Couldn't reach ${base}. Is the service running and reachable from your browser?`
    );
  }

  let data = null;
  const text = await resp.text();
  if (text) {
    try { data = JSON.parse(text); } catch { /* non-JSON response */ }
  }

  if (!resp.ok) {
    const detail = data && data.detail;
    let msg = "Something went wrong.";
    if (typeof detail === "string") msg = detail;
    else if (Array.isArray(detail) && detail[0]) msg = detail[0].msg || msg;
    else if (resp.status === 401) msg = "Session expired — please log in again.";
    if (resp.status === 401 && auth) doLogout(false);
    throw new Error(msg);
  }
  return data;
}

const AuthAPI = {
  register: (payload) => apiRequest(AUTH_API, "/auth/register", { method: "POST", body: payload, auth: false }),
  login: (payload) => apiRequest(AUTH_API, "/auth/login", { method: "POST", body: payload, auth: false }),
  profile: () => apiRequest(AUTH_API, "/auth/profile"),
  users: () => apiRequest(AUTH_API, "/auth/users"),
  searchUsers: (q) => apiRequest(AUTH_API, `/auth/search?q=${encodeURIComponent(q || "")}`),
  deleteUser: (userId) => apiRequest(AUTH_API, `/auth/users/${userId}`, { method: "DELETE" }),
  friends: () => apiRequest(AUTH_API, "/auth/friends"),
  sendFriendRequest: (username) => apiRequest(AUTH_API, `/auth/friends/request/${encodeURIComponent(username)}`, { method: "POST" }),
  respondFriendRequest: (friendshipId, action) => apiRequest(AUTH_API, `/auth/friends/${friendshipId}/respond`, { method: "POST", body: { action } }),
  removeFriendship: (friendshipId) => apiRequest(AUTH_API, `/auth/friends/${friendshipId}`, { method: "DELETE" }),
};

const LibraryAPI = {
  list: () => apiRequest(LIBRARY_API, "/books/"),
  create: (payload) => apiRequest(LIBRARY_API, "/books/", { method: "POST", body: payload }),
  update: (id, payload) => apiRequest(LIBRARY_API, `/books/${id}`, { method: "PUT", body: payload }),
  remove: (id) => apiRequest(LIBRARY_API, `/books/${id}`, { method: "DELETE" }),
  progress: (id, pages_read) => apiRequest(LIBRARY_API, `/books/${id}/progress`, { method: "PATCH", body: { pages_read } }),
  rating: (id, rating) => apiRequest(LIBRARY_API, `/books/${id}/rating`, { method: "PATCH", body: { rating } }),
  comments: (id, comments) => apiRequest(LIBRARY_API, `/books/${id}/comments`, { method: "PATCH", body: { comments } }),
  friendBooks: (friendId) => apiRequest(LIBRARY_API, `/books/friend/${friendId}`),
};

// ══════════════════════════════════════════════════════════════════════
//  Toast
// ══════════════════════════════════════════════════════════════════════
let toastTimer = null;
function toast(msg) {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.style.display = "none"; }, 2800);
}

// ══════════════════════════════════════════════════════════════════════
//  Modal
// ══════════════════════════════════════════════════════════════════════
function openModal(innerHtml, extraClass = "") {
  closeModal();
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "modalOverlay";
  overlay.innerHTML = `<div class="modal ${extraClass}">${innerHtml}</div>`;
  overlay.addEventListener("click", (e) => { if (e.target === overlay) closeModal(); });
  document.body.appendChild(overlay);
}
function closeModal() {
  const el = document.getElementById("modalOverlay");
  if (el) el.remove();
}

// ══════════════════════════════════════════════════════════════════════
//  Auth screen
// ══════════════════════════════════════════════════════════════════════
// Mirrors AuthService's check_password_strength() so the hint never contradicts
// the server. The server is still the real gate — this is just live feedback.
const SPECIAL_CHARS = new Set('$@#%_-/\\!&*+=?.,;:'.split(''));
function updatePasswordHint(pw) {
  const el = document.getElementById("pwHint");
  if (!el) return;
  const rules = [
    [pw.length >= 8 && pw.length <= 64, "8–64 characters"],
    [/[0-9]/.test(pw), "a digit"],
    [/[A-Z]/.test(pw), "an uppercase letter"],
    [/[a-z]/.test(pw), "a lowercase letter"],
    [[...pw].some((c) => SPECIAL_CHARS.has(c)), "a special character"],
  ];
  const allMet = rules.every(([met]) => met);
  el.style.color = allMet ? "var(--buttons)" : "var(--text-mute)";
  el.innerHTML = rules
    .map(([met, label]) => `<span style="opacity:${met ? "1" : "0.5"}">${met ? "✓" : "○"} ${label}</span>`)
    .join(" &nbsp; ");
}

function setAuthTab(tab) {
  document.getElementById("loginTab").classList.toggle("active", tab === "login");
  document.getElementById("registerTab").classList.toggle("active", tab === "register");
  document.getElementById("loginForm").classList.toggle("hidden", tab !== "login");
  document.getElementById("registerForm").classList.toggle("hidden", tab !== "register");
  document.getElementById("authError").textContent = "";
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value;
  const errEl = document.getElementById("authError");
  errEl.textContent = "";
  try {
    const data = await AuthAPI.login({ username, password });
    state.token = data.access_token;
    state.username = username;
    localStorage.setItem("rl_token", state.token);
    localStorage.setItem("rl_username", state.username);
    try {
      const profile = await AuthAPI.profile();
      state.userId = profile.id;
      state.isAdmin = !!profile.is_admin;
      localStorage.setItem("rl_user_id", String(profile.id));
      localStorage.setItem("rl_is_admin", String(state.isAdmin));
    } catch { /* non-fatal — friends "find people" will just not exclude self by id */ }
    await showApp();
  } catch (err) {
    errEl.textContent = err.message;
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const username = document.getElementById("regUsername").value.trim();
  const email = document.getElementById("regEmail").value.trim();
  const password = document.getElementById("regPassword").value;
  const admin_code = document.getElementById("regAdminCode").value.trim();
  const errEl = document.getElementById("authError");
  errEl.textContent = "";
  try {
    await AuthAPI.register({ username, email, password, admin_code: admin_code || null });
    toast(`Account created for ${username} — log in below.`);
    setAuthTab("login");
    document.getElementById("loginUsername").value = username;
  } catch (err) {
    errEl.textContent = err.message;
  }
}

function doLogout(redraw = true) {
  state.token = null;
  state.username = null;
  state.userId = null;
  state.isAdmin = false;
  localStorage.removeItem("rl_token");
  localStorage.removeItem("rl_username");
  localStorage.removeItem("rl_user_id");
  localStorage.removeItem("rl_is_admin");
  if (redraw) render();
}

// ══════════════════════════════════════════════════════════════════════
//  Data loading
// ══════════════════════════════════════════════════════════════════════
async function showApp() {
  render();
  await refreshBooks();
}

async function refreshBooks() {
  try {
    state.books = await LibraryAPI.list();
    renderBooksView();
    renderStats();
  } catch (err) {
    toast(err.message);
  }
}

async function refreshUsers() {
  try {
    state.users = await AuthAPI.users();
    renderUsersView();
  } catch (err) {
    toast(err.message);
  }
}

async function deleteUser(userId, username) {
  if (!confirm(`Permanently delete "${username}"? This removes their account, friendships, and books.`)) return;
  try {
    await AuthAPI.deleteUser(userId);
    toast(`Deleted ${username}`);
    await refreshUsers();
  } catch (err) {
    toast(err.message);
  }
}

async function refreshFriends() {
  try {
    state.friends = await AuthAPI.friends();
    renderFriendsView();
  } catch (err) {
    toast(err.message);
  }
}

let friendSearchDebounce = null;
async function runFriendSearch(q) {
  state.friendSearch = q;
  try {
    state.friendSearchResults = await AuthAPI.searchUsers(q);
  } catch (err) {
    toast(err.message);
    state.friendSearchResults = [];
  }
  renderFriendSearchResults();
}
function onFriendSearchInput(value) {
  clearTimeout(friendSearchDebounce);
  friendSearchDebounce = setTimeout(() => runFriendSearch(value), 300);
}

// ══════════════════════════════════════════════════════════════════════
//  Book actions
// ══════════════════════════════════════════════════════════════════════
function statusOf(book) {
  if (book.pages_read >= book.pages) return "completed";
  if (book.pages_read > 0) return "progress";
  return "unread";
}

function openAddBookModal() {
  openModal(`
    <h2>Add a book</h2>
    <form id="bookForm">
      <div class="field"><label>Title</label><input id="f_title" required></div>
      <div class="field"><label>Author</label><input id="f_author" required></div>
      <div class="field"><label>Year</label><input id="f_year" type="number" required></div>
      <div class="field"><label>Pages</label><input id="f_pages" type="number" min="1" required></div>
      <div class="field"><label>Language</label><input id="f_language" value="Unknown"></div>
      <div class="error-text" id="formError"></div>
      <div class="modal-actions">
        <button type="button" class="btn ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn">Save book</button>
      </div>
    </form>
  `);
  document.getElementById("bookForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      title: document.getElementById("f_title").value.trim(),
      author: document.getElementById("f_author").value.trim(),
      year: parseInt(document.getElementById("f_year").value, 10),
      pages: parseInt(document.getElementById("f_pages").value, 10),
      language: document.getElementById("f_language").value.trim() || "Unknown",
    };
    try {
      await LibraryAPI.create(payload);
      closeModal();
      toast(`Added "${payload.title}"`);
      await refreshBooks();
    } catch (err) {
      document.getElementById("formError").textContent = err.message;
    }
  });
}

function openEditBookModal(id) {
  const book = state.books.find((b) => b.id === id);
  if (!book) return;
  openModal(`
    <h2>Edit book</h2>
    <form id="bookForm">
      <div class="field"><label>Title</label><input id="f_title" value="${escapeAttr(book.title)}" required></div>
      <div class="field"><label>Author</label><input id="f_author" value="${escapeAttr(book.author)}" required></div>
      <div class="field"><label>Year</label><input id="f_year" type="number" value="${book.year}" required></div>
      <div class="field"><label>Pages</label><input id="f_pages" type="number" min="1" value="${book.pages}" required></div>
      <div class="field"><label>Language</label><input id="f_language" value="${escapeAttr(book.language)}"></div>
      <div class="error-text" id="formError"></div>
      <div class="modal-actions">
        <button type="button" class="btn ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn">Save changes</button>
      </div>
    </form>
  `);
  document.getElementById("bookForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      title: document.getElementById("f_title").value.trim(),
      author: document.getElementById("f_author").value.trim(),
      year: parseInt(document.getElementById("f_year").value, 10),
      pages: parseInt(document.getElementById("f_pages").value, 10),
      language: document.getElementById("f_language").value.trim() || "Unknown",
    };
    try {
      await LibraryAPI.update(id, payload);
      closeModal();
      toast(`Updated "${payload.title}"`);
      await refreshBooks();
    } catch (err) {
      document.getElementById("formError").textContent = err.message;
    }
  });
}

function openProgressModal(id) {
  const book = state.books.find((b) => b.id === id);
  if (!book) return;
  openModal(`
    <h2>Update progress — ${escapeHtml(book.title)}</h2>
    <div class="field">
      <label>Pages read (of ${book.pages})</label>
      <input id="f_pages_read" type="number" min="0" max="${book.pages}" value="${book.pages_read}">
    </div>
    <div class="error-text" id="formError"></div>
    <div class="modal-actions">
      <button type="button" class="btn ghost" onclick="closeModal()">Cancel</button>
      <button type="button" class="btn" id="saveProgressBtn">Save</button>
    </div>
  `);
  document.getElementById("saveProgressBtn").addEventListener("click", async () => {
    const val = parseInt(document.getElementById("f_pages_read").value, 10);
    if (isNaN(val) || val < 0 || val > book.pages) {
      document.getElementById("formError").textContent = `Enter a number between 0 and ${book.pages}.`;
      return;
    }
    try {
      await LibraryAPI.progress(id, val);
      closeModal();
      toast(val >= book.pages ? `Finished "${book.title}"! 🎉` : "Progress updated");
      await refreshBooks();
    } catch (err) {
      document.getElementById("formError").textContent = err.message;
    }
  });
}

function openRatingModal(id) {
  const book = state.books.find((b) => b.id === id);
  if (!book) return;
  openModal(`
    <h2>Rate — ${escapeHtml(book.title)}</h2>
    <div class="field">
      <label>Rating (0–10)</label>
      <input id="f_rating" type="number" min="0" max="10" step="0.5" value="${book.rating}">
    </div>
    <div class="error-text" id="formError"></div>
    <div class="modal-actions">
      <button type="button" class="btn ghost" onclick="closeModal()">Cancel</button>
      <button type="button" class="btn" id="saveRatingBtn">Save</button>
    </div>
  `);
  document.getElementById("saveRatingBtn").addEventListener("click", async () => {
    const val = parseFloat(document.getElementById("f_rating").value);
    if (isNaN(val) || val < 0 || val > 10) {
      document.getElementById("formError").textContent = "Enter a rating between 0 and 10.";
      return;
    }
    try {
      await LibraryAPI.rating(id, val);
      closeModal();
      toast(`Rated "${book.title}" — ${val}/10`);
      await refreshBooks();
    } catch (err) {
      document.getElementById("formError").textContent = err.message;
    }
  });
}

function openCommentsModal(id) {
  const book = state.books.find((b) => b.id === id);
  if (!book) return;
  openModal(`
    <h2>Notes — ${escapeHtml(book.title)}</h2>
    <div class="field">
      <label>Comments</label>
      <textarea id="f_comments" rows="14" maxlength="50000" style="min-height:320px; resize:vertical;">${escapeHtml(book.comments || "")}</textarea>
    </div>
    <div class="error-text" id="formError"></div>
    <div class="modal-actions">
      <button type="button" class="btn ghost" onclick="closeModal()">Cancel</button>
      <button type="button" class="btn" id="saveCommentsBtn">Save</button>
    </div>
  `, "modal-notes");
  document.getElementById("saveCommentsBtn").addEventListener("click", async () => {
    const val = document.getElementById("f_comments").value;
    try {
      await LibraryAPI.comments(id, val);
      closeModal();
      toast("Notes saved");
      await refreshBooks();
    } catch (err) {
      document.getElementById("formError").textContent = err.message;
    }
  });
}

function openReadOnlyCommentsModal(book) {
  openModal(`
    <h2>Notes — ${escapeHtml(book.title)}</h2>
    <div class="field">
      <label>Comments</label>
      <div style="white-space:pre-wrap; color:var(--text-main); font-size:14px; line-height:1.6; min-height:320px;">
        ${book.comments ? escapeHtml(book.comments) : `<span style="color:var(--text-mute)">No notes yet.</span>`}
      </div>
    </div>
    <div class="modal-actions">
      <button type="button" class="btn ghost" onclick="closeModal()">Close</button>
    </div>
  `, "modal-notes");
}

async function deleteBook(id) {
  const book = state.books.find((b) => b.id === id);
  if (!book) return;
  if (!confirm(`Remove "${book.title}" from your list?`)) return;
  try {
    await LibraryAPI.remove(id);
    toast(`Removed "${book.title}"`);
    await refreshBooks();
  } catch (err) {
    toast(err.message);
  }
}

// ══════════════════════════════════════════════════════════════════════
//  JSON import (from the desktop app's reading_list.json)
// ══════════════════════════════════════════════════════════════════════
async function handleImportFile(e) {
  const file = e.target.files[0];
  if (!file) return;

  let data;
  try {
    data = JSON.parse(await file.text());
  } catch {
    toast("That file isn't valid JSON.");
    e.target.value = "";
    return;
  }
  if (!Array.isArray(data)) {
    toast('Expected a JSON array of books (like the desktop app\'s reading_list.json).');
    e.target.value = "";
    return;
  }

  // Make sure we're comparing against the latest list before deciding create vs update.
  await refreshBooks();

  let created = 0, updated = 0, skipped = 0;
  for (const raw of data) {
    const title = String(raw.title ?? "").trim();
    const author = String(raw.author ?? "").trim();
    const pages = parseInt(raw.nb_pages, 10);
    if (!title || !author || !pages || pages <= 0) { skipped++; continue; }

    const year = parseInt(raw.year, 10) || 0;
    const language = (raw.OriginalLanguage || "Unknown").toString();
    const readingLevelPct = typeof raw.ReadingLevel === "number" ? raw.ReadingLevel : 0;
    const pagesRead = Math.max(0, Math.min(pages, Math.round((readingLevelPct / 100) * pages)));
    const rating = typeof raw.Rating === "number" ? raw.Rating : 0;
    const comments = (raw.Comments || "").toString();

    const existing = state.books.find(
      (b) => b.title.toLowerCase() === title.toLowerCase() && b.author.toLowerCase() === author.toLowerCase()
    );

    try {
      let book;
      if (existing) {
        book = await LibraryAPI.update(existing.id, { title, author, year, pages, language });
        updated++;
      } else {
        book = await LibraryAPI.create({ title, author, year, pages, language });
        created++;
      }
      if (pagesRead > 0) await LibraryAPI.progress(book.id, pagesRead);
      if (rating > 0) await LibraryAPI.rating(book.id, rating);
      if (comments) await LibraryAPI.comments(book.id, comments);
    } catch {
      skipped++;
    }
  }

  e.target.value = "";
  toast(`Import complete — ${created} added, ${updated} updated${skipped ? `, ${skipped} skipped` : ""}.`);
  await refreshBooks();
}

// ══════════════════════════════════════════════════════════════════════
//  Export (JSON — round-trips with the desktop app; PDF — readable report)
// ══════════════════════════════════════════════════════════════════════
function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function dateStamp() {
  return new Date().toISOString().slice(0, 10);
}

function exportJSON() {
  if (state.books.length === 0) {
    toast("Your list is empty — nothing to export.");
    return;
  }
  // Mirrors the desktop app's reading_list.json format exactly (same field
  // names handleImportFile() reads), so this file can be opened directly by
  // ReadingList.py / ReadingListGUI.py, or re-imported here later.
  const data = state.books.map((b) => ({
    title: b.title,
    author: b.author,
    year: b.year,
    nb_pages: b.pages,
    OriginalLanguage: b.language,
    ReadingLevel: b.reading_level,
    Rating: b.rating,
    Comments: b.comments || "",
  }));
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  triggerDownload(blob, `reading_list_${dateStamp()}.json`);
  toast(`Exported ${data.length} book(s) as JSON`);
}

function exportPDF() {
  if (state.books.length === 0) {
    toast("Your list is empty — nothing to export.");
    return;
  }
  if (typeof window.jspdf === "undefined") {
    toast("PDF export isn't available right now — try reloading the page.");
    return;
  }
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const books = getFilteredSortedBooks();

  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("Reading List", 40, 46);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(120);
  doc.text(`${state.username} · exported ${new Date().toLocaleDateString()} · ${books.length} book(s)`, 40, 64);
  doc.setTextColor(0);

  doc.autoTable({
    startY: 84,
    head: [["Title", "Author", "Year", "Pages", "Progress", "Rating"]],
    body: books.map((b) => [
      b.title,
      b.author,
      String(b.year),
      `${b.pages_read}/${b.pages}`,
      `${b.reading_level.toFixed(0)}%`,
      b.rating > 0 ? b.rating.toFixed(1) : "—",
    ]),
    styles: { fontSize: 9, cellPadding: 6 },
    headStyles: { fillColor: [2, 195, 167], textColor: [13, 27, 42] },
    margin: { left: 40, right: 40 },
  });

  const withNotes = books.filter((b) => b.comments && b.comments.trim());
  if (withNotes.length > 0) {
    let y = doc.lastAutoTable.finalY + 30;
    const pageHeight = doc.internal.pageSize.getHeight();
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    if (y > pageHeight - 60) { doc.addPage(); y = 50; }
    doc.text("Notes", 40, y);
    y += 20;

    for (const book of withNotes) {
      doc.setFont("helvetica", "bold");
      doc.setFontSize(10);
      if (y > pageHeight - 60) { doc.addPage(); y = 50; }
      doc.text(`${book.title} — ${book.author}`, 40, y);
      y += 14;

      doc.setFont("helvetica", "normal");
      doc.setFontSize(9);
      const lines = doc.splitTextToSize(book.comments, 515);
      for (const line of lines) {
        if (y > pageHeight - 40) { doc.addPage(); y = 50; }
        doc.text(line, 40, y);
        y += 12;
      }
      y += 12;
    }
  }

  doc.save(`reading_list_${dateStamp()}.pdf`);
  toast(`Exported ${books.length} book(s) as PDF`);
}

// ══════════════════════════════════════════════════════════════════════
//  Friend actions
// ══════════════════════════════════════════════════════════════════════
async function sendFriendRequest(username) {
  try {
    await AuthAPI.sendFriendRequest(username);
    toast(`Friend request sent to ${username}`);
    await refreshFriends();
  } catch (err) {
    toast(err.message);
  }
}

async function respondFriendRequest(friendshipId, action) {
  try {
    await AuthAPI.respondFriendRequest(friendshipId, action);
    toast(action === "accept" ? "Friend request accepted" : "Request declined");
    await refreshFriends();
  } catch (err) {
    toast(err.message);
  }
}

async function removeFriendship(friendshipId, label) {
  if (!confirm(`Remove ${label} from your friends?`)) return;
  try {
    await AuthAPI.removeFriendship(friendshipId);
    toast("Removed");
    if (state.viewingFriend) { state.viewingFriend = null; state.friendBooks = []; }
    await refreshFriends();
  } catch (err) {
    toast(err.message);
  }
}

async function viewFriendShelf(id, username) {
  state.viewingFriend = { id, username };
  renderFriendsView();
  try {
    state.friendBooks = await LibraryAPI.friendBooks(id);
    renderFriendsView();
  } catch (err) {
    toast(err.message);
    state.viewingFriend = null;
    renderFriendsView();
  }
}

function backToFriendsList() {
  state.viewingFriend = null;
  state.friendBooks = [];
  renderFriendsView();
}

// ══════════════════════════════════════════════════════════════════════
//  Rendering
// ══════════════════════════════════════════════════════════════════════
function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function escapeAttr(str) { return escapeHtml(str); }

function getFilteredSortedBooks() {
  let list = [...state.books];
  if (state.filter !== "all") {
    list = list.filter((b) => statusOf(b) === state.filter);
  }
  if (state.search.trim()) {
    const q = state.search.trim().toLowerCase();
    list = list.filter(
      (b) => b.title.toLowerCase().includes(q) || b.author.toLowerCase().includes(q)
    );
  }
  const sorters = {
    title: (a, b) => a.title.localeCompare(b.title),
    author: (a, b) => a.author.localeCompare(b.author),
    year: (a, b) => b.year - a.year,
    reading_level: (a, b) => b.reading_level - a.reading_level,
    rating: (a, b) => b.rating - a.rating,
    pages: (a, b) => a.pages - b.pages,
  };
  list.sort(sorters[state.sort] || sorters.title);
  return list;
}

function renderBookCard(book) {
  const status = statusOf(book);
  const badge = status === "completed" ? "✅" : status === "progress" ? "📖" : "⏳";
  return `
    <div class="book-card status-${status}">
      <div class="book-main" ondblclick="openCommentsModal(${book.id})" title="Double-click for notes">
        <div class="title-row">
          <span class="title">${badge} ${escapeHtml(book.title)}</span>
          <span class="year">${book.year}</span>
        </div>
        <div class="author">by ${escapeHtml(book.author)}</div>
        <div class="meta-line">
          <span>${book.pages} pages · ${escapeHtml(book.language)}</span>
        </div>
      </div>
      <div class="progress-block">
        <div class="progress-track"><div class="progress-fill" style="width:${Math.min(100, book.reading_level)}%"></div></div>
        <div class="progress-pct">${book.reading_level.toFixed(0)}% · ${book.pages_read}/${book.pages}p</div>
      </div>
      <div class="rating-badge">${book.rating > 0 ? "★ " + book.rating.toFixed(1) : "— unrated"}</div>
      <div class="card-actions">
        <button class="icon-btn" title="Update progress" onclick="openProgressModal(${book.id})">📊</button>
        <button class="icon-btn" title="Rate" onclick="openRatingModal(${book.id})">⭐</button>
        <button class="icon-btn" title="Notes" onclick="openCommentsModal(${book.id})">💬</button>
        <button class="icon-btn" title="Edit" onclick="openEditBookModal(${book.id})">✏️</button>
        <button class="icon-btn" title="Delete" onclick="deleteBook(${book.id})">🗑️</button>
      </div>
    </div>
  `;
}

function renderBooksView() {
  const container = document.getElementById("booksList");
  if (!container) return;
  const list = getFilteredSortedBooks();
  if (list.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="stamp">${state.books.length === 0 ? "shelf empty" : "no matches"}</div>
        <p>${state.books.length === 0 ? "Add your first book to get started." : "Try a different filter or search."}</p>
      </div>`;
    return;
  }
  container.innerHTML = list.map(renderBookCard).join("");
}

function renderStats() {
  const el = document.getElementById("statsStrip");
  if (!el) return;
  const books = state.books;
  const total = books.length;
  const completed = books.filter((b) => statusOf(b) === "completed").length;
  const inProgress = books.filter((b) => statusOf(b) === "progress").length;
  const unread = books.filter((b) => statusOf(b) === "unread").length;
  const rated = books.filter((b) => b.rating > 0);
  const avgRating = rated.length ? (rated.reduce((s, b) => s + b.rating, 0) / rated.length).toFixed(1) : "—";
  const totalPages = books.reduce((s, b) => s + b.pages, 0);
  const totalPagesRead = books.reduce((s, b) => s + b.pages_read, 0);

  el.innerHTML = [
    ["Total books", total],
    ["Completed", completed],
    ["In progress", inProgress],
    ["Unread", unread],
    ["Avg rating", avgRating],
    ["Pages read", `${totalPagesRead} / ${totalPages}`],
  ].map(([label, num]) => `
    <div class="stat-col">
      <div class="stat-num">${num}</div>
      <div class="stat-label">${label}</div>
    </div>
  `).join("");
}

function renderUsersView() {
  const container = document.getElementById("usersTableBody");
  if (!container) return;
  if (state.users.length === 0) {
    container.innerHTML = `<tr><td colspan="5" style="color:var(--text-mute); padding:20px 14px;">No users yet.</td></tr>`;
    return;
  }
  container.innerHTML = state.users.map((u) => `
    <tr>
      <td class="uid">#${u.id}</td>
      <td>${escapeHtml(u.username)}${u.is_admin ? ' <span style="color:var(--special); font-size:11px;">ADMIN</span>' : ""}</td>
      <td>${escapeHtml(u.email)}</td>
      <td>${new Date(u.created_at).toLocaleDateString()}</td>
      <td>${u.id === state.userId
          ? `<span style="color:var(--text-mute); font-size:12px;">that's you</span>`
          : `<button class="icon-btn" title="Delete user" onclick="deleteUser(${u.id}, '${escapeAttr(u.username)}')">🗑️</button>`}</td>
    </tr>
  `).join("");
}

function renderReadOnlyBookCard(book) {
  const status = statusOf(book);
  const badge = status === "completed" ? "✅" : status === "progress" ? "📖" : "⏳";
  return `
    <div class="book-card status-${status}">
      <div class="book-main" ondblclick="openFriendCommentsModal(${book.id})" title="Double-click for notes">
        <div class="title-row">
          <span class="title">${badge} ${escapeHtml(book.title)}</span>
          <span class="year">${book.year}</span>
        </div>
        <div class="author">by ${escapeHtml(book.author)}</div>
        <div class="meta-line">
          <span>${book.pages} pages · ${escapeHtml(book.language)}</span>
        </div>
      </div>
      <div class="progress-block">
        <div class="progress-track"><div class="progress-fill" style="width:${Math.min(100, book.reading_level)}%"></div></div>
        <div class="progress-pct">${book.reading_level.toFixed(0)}% · ${book.pages_read}/${book.pages}p</div>
      </div>
      <div class="rating-badge">${book.rating > 0 ? "★ " + book.rating.toFixed(1) : "— unrated"}</div>
      <div></div>
    </div>
  `;
}

function openFriendCommentsModal(bookId) {
  const book = state.friendBooks.find((b) => b.id === bookId);
  if (!book) return;
  openReadOnlyCommentsModal(book);
}

function renderFriendsView() {
  const container = document.getElementById("friendsContent");
  if (!container) return;

  if (state.viewingFriend) {
    const list = state.friendBooks;
    container.innerHTML = `
      <button class="btn ghost small" onclick="backToFriendsList()" style="margin-bottom:16px;">&larr; Back to friends</button>
      <h2 style="font-family:var(--font-display); margin: 0 0 16px;">${escapeHtml(state.viewingFriend.username)}'s shelf</h2>
      ${list.length === 0
        ? `<div class="empty-state"><div class="stamp">shelf empty</div><p>${escapeHtml(state.viewingFriend.username)} hasn't added any books yet.</p></div>`
        : list.map(renderReadOnlyBookCard).join("")}
    `;
    return;
  }

  const tab = state.friendsTab;
  const tabs = [
    ["list", `Friends (${state.friends.friends.length})`],
    ["requests", `Requests (${state.friends.incoming_requests.length})`],
    ["find", "Find people"],
  ];

  let body = "";
  if (tab === "list") {
    body = state.friends.friends.length === 0
      ? `<div class="empty-state"><div class="stamp">no friends yet</div><p>Send a request from "Find people" to get started.</p></div>`
      : state.friends.friends.map((f) => `
          <div class="book-card" style="grid-template-columns: 1fr auto;">
            <div class="book-main"><div class="title-row"><span class="title">${escapeHtml(f.username)}</span></div><div class="author">${escapeHtml(f.email)}</div></div>
            <div class="card-actions">
              <button class="btn small" onclick="viewFriendShelf(${f.id}, '${escapeAttr(f.username)}')">View shelf</button>
              <button class="icon-btn" title="Remove friend" onclick="removeFriendship(${f.friendship_id}, '${escapeAttr(f.username)}')">🗑️</button>
            </div>
          </div>
        `).join("");
  } else if (tab === "requests") {
    const incoming = state.friends.incoming_requests.map((f) => `
      <div class="book-card" style="grid-template-columns: 1fr auto;">
        <div class="book-main"><div class="title-row"><span class="title">${escapeHtml(f.username)}</span></div><div class="author">wants to be friends</div></div>
        <div class="card-actions">
          <button class="btn small" onclick="respondFriendRequest(${f.friendship_id}, 'accept')">Accept</button>
          <button class="btn ghost small" onclick="respondFriendRequest(${f.friendship_id}, 'decline')">Decline</button>
        </div>
      </div>
    `).join("");
    const outgoing = state.friends.outgoing_requests.map((f) => `
      <div class="book-card" style="grid-template-columns: 1fr auto;">
        <div class="book-main"><div class="title-row"><span class="title">${escapeHtml(f.username)}</span></div><div class="author">request sent — awaiting response</div></div>
        <div class="card-actions">
          <button class="icon-btn" title="Cancel request" onclick="removeFriendship(${f.friendship_id}, '${escapeAttr(f.username)}')">🗑️</button>
        </div>
      </div>
    `).join("");
    body = (incoming || outgoing)
      ? incoming + outgoing
      : `<div class="empty-state"><div class="stamp">no requests</div><p>Nothing pending right now.</p></div>`;
  } else if (tab === "find") {
    container.innerHTML = `
      <div class="filter-row">
        ${tabs.map(([key, label]) => `<button class="filter-chip ${tab === key ? "active" : ""}" onclick="setFriendsTab('${key}')">${label}</button>`).join("")}
      </div>
      <div class="search-box" style="width:280px; margin-bottom:16px;">
        <input id="friendSearchInput" placeholder="Search by username…" value="${escapeAttr(state.friendSearch)}" oninput="onFriendSearchInput(this.value)">
      </div>
      <div id="friendSearchResultsList"></div>
    `;
    renderFriendSearchResults();
    return;
  }

  container.innerHTML = `
    <div class="filter-row">
      ${tabs.map(([key, label]) => `<button class="filter-chip ${tab === key ? "active" : ""}" onclick="setFriendsTab('${key}')">${label}</button>`).join("")}
    </div>
    <div id="friendsList">${body}</div>
  `;
}

function renderFriendSearchResults() {
  const el = document.getElementById("friendSearchResultsList");
  if (!el) return;
  const takenIds = new Set([
    state.userId,
    ...state.friends.friends.map((f) => f.id),
    ...state.friends.incoming_requests.map((f) => f.id),
    ...state.friends.outgoing_requests.map((f) => f.id),
  ]);
  const candidates = state.friendSearchResults.filter((u) => !takenIds.has(u.id));
  el.innerHTML = candidates.length === 0
    ? `<div class="empty-state"><div class="stamp">${state.friendSearch ? "no matches" : "nobody left"}</div><p>${state.friendSearch ? "Try a different search." : "Everyone's already your friend or has a pending request."}</p></div>`
    : candidates.map((u) => `
        <div class="book-card" style="grid-template-columns: 1fr auto;">
          <div class="book-main"><div class="title-row"><span class="title">${escapeHtml(u.username)}</span></div><div class="author">${escapeHtml(u.email)}</div></div>
          <div class="card-actions">
            <button class="btn small" onclick="sendFriendRequest('${escapeAttr(u.username)}')">Add friend</button>
          </div>
        </div>
      `).join("");
}

function setFriendsTab(tab) {
  state.friendsTab = tab;
  if (tab === "find") {
    runFriendSearch(state.friendSearch);
  } else {
    refreshFriends();
  }
  renderFriendsView();
}

function renderPaletteSwatches() {
  const el = document.getElementById("swatches");
  if (!el) return;
  const active = currentPaletteName();
  el.innerHTML = Object.entries(PALETTES).map(([name, p]) => `
    <button class="swatch ${name === active ? "active" : ""}" title="${name}"
      style="background:${p.buttons}" onclick="handlePaletteChange('${name}')"></button>
  `).join("");
}

function handlePaletteChange(name) {
  applyPalette(name);
  renderPaletteSwatches();
}

function setView(view) {
  if (view === "users" && !state.isAdmin) return; // defense in depth; server also enforces this
  state.view = view;
  render();
  if (view === "users") refreshUsers();
  if (view === "books") refreshBooks();
  if (view === "friends") {
    state.viewingFriend = null;
    refreshFriends();
  }
}

// ══════════════════════════════════════════════════════════════════════
//  Main render — swaps between auth screen and app shell
// ══════════════════════════════════════════════════════════════════════
function render() {
  const root = document.getElementById("root");
  if (!state.token) {
    root.innerHTML = authScreenHtml();
    document.getElementById("loginForm").addEventListener("submit", handleLogin);
    document.getElementById("registerForm").addEventListener("submit", handleRegister);
    document.getElementById("regPassword").addEventListener("input", (e) => updatePasswordHint(e.target.value));
    return;
  }
  root.innerHTML = appShellHtml();
  renderPaletteSwatches();

  if (state.view === "books") {
    document.getElementById("searchInput").addEventListener("input", (e) => {
      state.search = e.target.value;
      renderBooksView();
    });
    document.getElementById("sortSelect").addEventListener("change", (e) => {
      state.sort = e.target.value;
      renderBooksView();
    });
    document.querySelectorAll(".filter-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        state.filter = chip.dataset.filter;
        document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        renderBooksView();
      });
    });
    document.getElementById("importFileInput").addEventListener("change", handleImportFile);
    renderBooksView();
    renderStats();
  }
  if (state.view === "users") renderUsersView();
  if (state.view === "friends") renderFriendsView();
}

function authScreenHtml() {
  return `
    <div id="authScreen">
      <div class="membership-card">
        <div class="card-eyebrow">Library Card</div>
        <div class="card-title">Reading List</div>
        <div class="card-sub">Track what you're reading, together.</div>
        <div class="auth-tabs">
          <button class="auth-tab active" id="loginTab" onclick="setAuthTab('login')" type="button">Log in</button>
          <button class="auth-tab" id="registerTab" onclick="setAuthTab('register')" type="button">Register</button>
        </div>
        <form id="loginForm" class="auth-form">
          <div class="field"><label>Username</label><input id="loginUsername" required></div>
          <div class="field"><label>Password</label><input id="loginPassword" type="password" required></div>
          <button class="btn" type="submit">Log in</button>
        </form>
        <form id="registerForm" class="auth-form hidden">
          <div class="field"><label>Username</label><input id="regUsername" required></div>
          <div class="field"><label>Email</label><input id="regEmail" type="email" required></div>
          <div class="field"><label>Password</label><input id="regPassword" type="password" required></div>
          <div id="pwHint" style="font-size:11px; color:var(--text-mute); margin:-8px 0 14px;">
            At least 8 characters, with an uppercase letter, a lowercase letter, a digit, and a special character.
          </div>
          <div class="field"><label>Admin code <span style="text-transform:none; font-weight:400; color:var(--text-mute);">(optional — only if you're setting up as admin)</span></label><input id="regAdminCode"></div>
          <button class="btn" type="submit">Create account</button>
        </form>
        <div class="error-text" id="authError"></div>
      </div>
    </div>
  `;
}

function appShellHtml() {
  return `
    <div id="appScreen">
      <div class="sidebar">
        <div class="sidebar-logo"><span class="mark">📚</span><span class="word">Reading List</span></div>
        <hr>
        <button class="nav-item ${state.view === "books" ? "active" : ""}" onclick="setView('books')">📖 My Books</button>
        <button class="nav-item ${state.view === "friends" ? "active" : ""}" onclick="setView('friends')">🤝 Friends</button>
        ${state.isAdmin ? `<button class="nav-item ${state.view === "users" ? "active" : ""}" onclick="setView('users')">👥 Users</button>` : ""}
        <hr>
        <div class="palette-picker">
          <div class="palette-picker-label">Theme</div>
          <div class="swatches" id="swatches"></div>
        </div>
        <div class="sidebar-footer">
          <div class="sidebar-user">Signed in as ${escapeHtml(state.username || "")}</div>
          <button class="btn ghost small" onclick="doLogout()" style="width:100%">Log out</button>
        </div>
      </div>
      <div class="main">
        <div class="topbar">
          <h1>${state.view === "users" ? "Users" : state.view === "friends" ? "Friends" : "My Books"}</h1>
          ${state.view === "books" ? `
            <div class="search-box">
              <input id="searchInput" placeholder="Search title or author…" value="${escapeAttr(state.search)}">
            </div>
          ` : state.view === "users" ? `<button class="btn ghost small" onclick="refreshUsers()">Refresh</button>` : ""}
        </div>
        ${state.view === "books" ? `<div class="stats-strip" id="statsStrip"></div>` : ""}
        <div class="content">
          ${state.view === "books" ? booksViewHtml() : state.view === "friends" ? friendsViewHtml() : usersViewHtml()}
        </div>
      </div>
    </div>
  `;
}

function booksViewHtml() {
  const filters = [
    ["all", "All"], ["unread", "Unread"], ["progress", "In progress"], ["completed", "Completed"],
  ];
  return `
    <div class="filter-row">
      ${filters.map(([key, label]) => `
        <button class="filter-chip ${state.filter === key ? "active" : ""}" data-filter="${key}">${label}</button>
      `).join("")}
      <select class="sort-select" id="sortSelect">
        <option value="title" ${state.sort === "title" ? "selected" : ""}>Sort: Title</option>
        <option value="author" ${state.sort === "author" ? "selected" : ""}>Sort: Author</option>
        <option value="year" ${state.sort === "year" ? "selected" : ""}>Sort: Year</option>
        <option value="reading_level" ${state.sort === "reading_level" ? "selected" : ""}>Sort: Progress</option>
        <option value="rating" ${state.sort === "rating" ? "selected" : ""}>Sort: Rating</option>
        <option value="pages" ${state.sort === "pages" ? "selected" : ""}>Sort: Pages</option>
      </select>
      <button class="btn ghost small" onclick="exportJSON()" title="Download as JSON — matches the desktop app's format">⇩ JSON</button>
      <button class="btn ghost small" onclick="exportPDF()" title="Download as a readable PDF">⇩ PDF</button>
      <button class="btn ghost small" onclick="document.getElementById('importFileInput').click()">⇪ Import JSON</button>
      <input type="file" id="importFileInput" accept=".json,application/json" class="hidden">
      <button class="btn small" onclick="openAddBookModal()">+ Add book</button>
    </div>
    <div id="booksList"></div>
  `;
}

function friendsViewHtml() {
  return `<div id="friendsContent"></div>`;
}

function usersViewHtml() {
  return `
    <table class="users-table">
      <thead><tr><th>ID</th><th>Username</th><th>Email</th><th>Joined</th><th></th></tr></thead>
      <tbody id="usersTableBody"><tr><td colspan="5" style="padding:20px 14px;color:var(--text-mute)">Loading…</td></tr></tbody>
    </table>
  `;
}

// ══════════════════════════════════════════════════════════════════════
//  Boot
// ══════════════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  applyPalette(currentPaletteName());
  render();
  if (state.token) {
    refreshBooks();
    AuthAPI.profile().then((p) => {
      state.userId = p.id;
      state.isAdmin = !!p.is_admin;
      localStorage.setItem("rl_user_id", String(p.id));
      localStorage.setItem("rl_is_admin", String(state.isAdmin));
      if (state.view !== "books") render(); // refresh nav visibility if admin status changed
    }).catch(() => {});
  }
});
