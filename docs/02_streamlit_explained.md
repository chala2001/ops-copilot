# 02 — Streamlit: How the App Runs as a Server

> Why Streamlit? What is it? How does it turn Python code into a website?

---

## What Is Streamlit?

Streamlit is a Python library that turns a regular Python script into an interactive web application — without writing any HTML, CSS, or JavaScript.

**Analogy:** Imagine you had a magic wand. Every time you write `st.write("Hello")` in Python, Streamlit waves the wand and puts "Hello" on a webpage for you. You never touch the actual webpage code.

Traditional web development:
```
Python (backend) → HTML + CSS + JavaScript (frontend) → Browser
```

With Streamlit:
```
Python only → Browser
```

---

## Does app.py Run as a Server?

**Yes, completely.** When you run:

```bash
streamlit run app.py
```

Streamlit does three things:
1. Starts a Python HTTP server on port 8501
2. Serves a web interface at `http://localhost:8501` (or `https://` with our TLS setup)
3. Keeps the server running, waiting for browser connections

Your browser connects to that server. Every time you click a button, type a message, or submit a form, the browser sends a message to the Streamlit server. The server runs your Python script again from top to bottom.

---

## The Most Important Concept: Streamlit Reruns the Entire Script

This is the most surprising thing about Streamlit for new users. **Every user interaction triggers a complete re-execution of app.py from line 1.**

```
User clicks "Send"
       │
       ▼
Streamlit server receives the click event
       │
       ▼
Python runs app.py from line 1 to line 313 (the entire file)
       │
       ▼
New HTML is sent to the browser
       │
       ▼
Browser updates what the user sees
```

This means:
- Any variable you define in app.py only exists for ONE rerun
- If you store data in a regular variable like `x = 5`, it's gone on the next rerun
- To keep data between reruns (like the chat history), you must use `st.session_state`

---

## What Is st.session_state?

`st.session_state` is a special dictionary that Streamlit preserves between reruns for the same browser tab.

```python
# This gets RESET every rerun:
messages = []  # always empty

# This PERSISTS between reruns:
if 'messages' not in st.session_state:
    st.session_state.messages = []   # only set on first visit
```

In our app, session_state stores:
- `st.session_state.authenticated` — True/False (is the user logged in?)
- `st.session_state.user_info` — dict with username, role, display name
- `st.session_state.messages` — the entire chat history
- `st.session_state.last_activity` — timestamp of last page interaction
- `st.session_state.session_start` — timestamp of login

---

## How app.py Controls Page Flow

Our app.py uses a "gate" pattern. At the top of the file, before any content is shown, it checks authentication:

```python
# Line 31-59: THE LOGIN GATE
if not st.session_state.authenticated:
    # show login form
    # if login fails, st.stop() halts the script here
    # nothing below this block is ever reached
    st.stop()

# Line 67-80: THE SESSION TIMEOUT CHECK
session_valid, timeout_message = check_session_timeout()
if not session_valid:
    # log out and stop
    st.stop()

# ── If we reach here, the user is authenticated and their session is valid ──
# Now we show the sidebar, chat interface, etc.
```

`st.stop()` is Streamlit's way of saying "stop executing this script right now." It's like an early return, but for the entire page.

---

## Streamlit's Multi-Page Feature

Streamlit automatically turns files in the `pages/` folder into separate pages in the left sidebar:

```
pages/
  2_Evaluation_Dashboard.py   →  "Evaluation Dashboard" in sidebar
  3_Ingestion_Log.py          →  "Ingestion Log" in sidebar
  4_Usage_Dashboard.py        →  "Usage Dashboard" in sidebar
  5_Admin_Panel.py            →  "Admin Panel" in sidebar
```

The number prefix (2_, 3_, etc.) controls the order they appear in the sidebar. Streamlit strips the number and underscore from the display name.

Each page file is its own independent Python script. When a user navigates to a page, Streamlit runs that page's script. Because `st.session_state` is shared across all pages in the same browser session, the authentication state set in `app.py` is visible in every page file — that's how `auth/auth_guard.py` can check if the user is logged in even on a different page.

---

## Key Streamlit Commands Used in This App

### Layout Commands

| Command | What It Does | Where Used |
|---------|-------------|------------|
| `st.set_page_config(...)` | Sets browser tab title, icon, layout | Top of every page file |
| `st.columns([1,2,1])` | Splits the page into 3 columns (widths 1:2:1) | Login form centering |
| `with st.sidebar:` | Everything inside shows in the left panel | Sidebar |
| `st.divider()` | Draws a horizontal line | Between sidebar sections |

### Content Commands

| Command | What It Does |
|---------|-------------|
| `st.title("text")` | Big heading |
| `st.header("text")` | Medium heading |
| `st.subheader("text")` | Small heading |
| `st.caption("text")` | Small grey text |
| `st.write("text")` | Write text (also works with dataframes, charts) |
| `st.info("text")` | Blue info box |
| `st.success("text")` | Green success box |
| `st.warning("text")` | Yellow warning box |
| `st.error("text")` | Red error box |
| `st.metric("label", value)` | Big number with label (used in dashboards) |

### Interactive Commands

| Command | What It Does |
|---------|-------------|
| `st.text_input("label")` | Single-line text field |
| `st.text_input("label", type="password")` | Password field (hides input) |
| `st.button("label")` | Clickable button, returns True when clicked |
| `st.form("key")` | Groups inputs; only triggers rerun when submitted |
| `st.form_submit_button("label")` | Submit button inside a form |
| `st.selectbox("label", options)` | Dropdown menu |
| `st.checkbox("label")` | Checkbox, returns True/False |

### Chat Commands (Special to This App)

| Command | What It Does |
|---------|-------------|
| `st.chat_input("placeholder")` | Fixed input bar at the bottom of the page |
| `st.chat_message("user")` | Blue chat bubble with user avatar |
| `st.chat_message("assistant")` | Grey chat bubble with robot avatar |
| `st.write_stream(generator)` | Streams text word-by-word from a generator |

### Data Commands (Dashboards)

| Command | What It Does |
|---------|-------------|
| `st.dataframe(df)` | Interactive, sortable table |
| `st.bar_chart(data)` | Bar chart (auto from a pandas Series) |
| `st.expander("label")` | Collapsible section |
| `st.spinner("message")` | Loading spinner while an operation runs |

### Control Commands

| Command | What It Does |
|---------|-------------|
| `st.stop()` | Stop executing this script immediately |
| `st.rerun()` | Trigger a full rerun right now |

---

## How Streaming Works (st.write_stream)

When the user asks a question, the answer appears word by word — just like ChatGPT. This is done using Python generators.

A generator is a function that uses `yield` instead of `return`. Each `yield` gives back one piece of data, then pauses, then continues when asked for the next piece.

```python
# In core/rag.py — ask_stream is a generator
def ask_stream(question, customer_scope):
    # ... retrieve chunks, build prompt ...
    
    response = client.models.generate_content_stream(...)
    
    for chunk in response:          # Gemini sends tokens one by one
        if chunk.text:
            yield chunk.text        # yield each token to the caller
    
    yield sources                   # at the very end, yield the sources list

# In app.py — st.write_stream consumes the generator
full_answer = st.write_stream(text_only_stream())
```

`st.write_stream()` calls `next()` on the generator repeatedly and updates the browser display as each chunk arrives. The user sees text appearing progressively.

---

## Why Streamlit Instead of Flask or Django?

| Criteria | Streamlit | Flask / Django |
|----------|-----------|----------------|
| Lines of code for a chat UI | ~50 lines | ~300-500 lines |
| Needs HTML/CSS knowledge | No | Yes |
| Built-in session state | Yes | Manual setup |
| Built-in charts and tables | Yes | Third-party libraries |
| Authentication built-in | No (we built it) | Partial |
| Good for data/AI apps | Excellent | Medium |
| Good for public APIs | No | Yes |
| Production scalability | Medium | High |

For an internal SRE tool that needs to be built quickly and shown to a team, Streamlit is the right choice. We get a professional-looking UI in days, not weeks.

---

## How the HTTPS Transport Works

By default, Streamlit runs on plain HTTP. We configured TLS (HTTPS) by passing certificate files at startup:

```bash
streamlit run app.py \
  --server.sslCertFile=certs/cert.pem \
  --server.sslKeyFile=certs/key.pem \
  --server.port=8501
```

The `certs/cert.pem` and `certs/key.pem` files in the project are TLS certificates. When a browser connects:

1. Browser: "I want to connect to your server"
2. Server: "Here is my certificate proving I am who I say I am" (cert.pem)
3. Browser: "OK, let's encrypt our communication" (using key.pem on server side)
4. All data flows encrypted — no one in between can read your questions or answers

Without HTTPS, every question a user types would be visible to anyone on the same network (like a Wi-Fi sniffer). With HTTPS, it's encrypted.
