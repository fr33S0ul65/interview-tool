# Interview Tool - final prototype (Section 66, lectures 379-385)
import streamlit as st
from openai import OpenAI
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Streamlit Chat", page_icon="💬")
st.title("Chatbot")

# ---------- Session state (lecture 383) ----------
if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False
if "user_message_count" not in st.session_state:
    st.session_state.user_message_count = 0
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False
if "chat_complete" not in st.session_state:
    st.session_state.chat_complete = False
if "messages" not in st.session_state:
    st.session_state.messages = []


def complete_setup():
    st.session_state.setup_complete = True


def show_feedback():
    st.session_state.feedback_shown = True


# ---------- Setup stage ----------
if not st.session_state.setup_complete:
    st.subheader("Personal Information", divider="rainbow")

    if "name" not in st.session_state:
        st.session_state["name"] = ""
    if "experience" not in st.session_state:
        st.session_state["experience"] = ""
    if "skills" not in st.session_state:
        st.session_state["skills"] = ""

    # Character limits on everything that goes into the LLM (lecture 383)
    st.session_state["name"] = st.text_input(
        label="Name", value=st.session_state["name"], placeholder="Enter your name", max_chars=40)
    st.session_state["experience"] = st.text_area(
        label="Experience", value=st.session_state["experience"],
        placeholder="Describe your experience", max_chars=200)
    st.session_state["skills"] = st.text_area(
        label="Skills", value=st.session_state["skills"], placeholder="List your skills", max_chars=200)

    st.subheader("Company and Position", divider="rainbow")

    if "level" not in st.session_state:
        st.session_state["level"] = "Junior"
    if "position" not in st.session_state:
        st.session_state["position"] = "Data Scientist"
    if "company" not in st.session_state:
        st.session_state["company"] = "Amazon"

    levels = ["Junior", "Mid-level", "Senior"]
    positions = ("Data Scientist", "Data Engineer", "ML Engineer", "BI Analyst", "Financial Analyst")
    companies = ("Amazon", "Meta", "Udemy", "365 Company", "Nestle", "LinkedIn", "Spotify")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state["level"] = st.radio(
            "Choose level", key="visibility", options=levels,
            index=levels.index(st.session_state["level"]))
    with col2:
        st.session_state["position"] = st.selectbox(
            "Choose a position", positions,
            index=positions.index(st.session_state["position"]))

    st.session_state["company"] = st.selectbox(
        "Select a Company", companies,
        index=companies.index(st.session_state["company"]))

    if st.button("Start Interview", on_click=complete_setup):
        st.write("Setup complete. Starting interview...")

# ---------- Interview stage (lecture 384) ----------
if (st.session_state.setup_complete
        and not st.session_state.feedback_shown
        and not st.session_state.chat_complete):

    st.info("Start by introducing yourself", icon="👋")

    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = "gpt-4o"

    # Empty list -> add the system prompt once
    if not st.session_state.messages:
        st.session_state.messages = [{
            "role": "system",
            "content": (f"You are an HR executive that interviews an interviewee called {st.session_state['name']} "
                        f"with experience {st.session_state['experience']} and skills {st.session_state['skills']}. "
                        f"You should interview him for the position {st.session_state['level']} "
                        f"{st.session_state['position']} at the company {st.session_state['company']}"),
        }]

    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Max 5 user messages; the assistant answers the first 4
    if st.session_state.user_message_count < 5:
        if prompt := st.chat_input("Your response", max_chars=1000):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            if st.session_state.user_message_count < 4:
                with st.chat_message("assistant"):
                    stream = client.chat.completions.create(
                        model=st.session_state["openai_model"],
                        messages=[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages
                        ],
                        stream=True,
                    )
                    response = st.write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": response})

            st.session_state.user_message_count += 1

    if st.session_state.user_message_count >= 5:
        st.session_state.chat_complete = True

# ---------- Feedback (lecture 385) ----------
if st.session_state.chat_complete and not st.session_state.feedback_shown:
    if st.button("Get Feedback", on_click=show_feedback):
        st.write("Fetching feedback...")

if st.session_state.feedback_shown:
    st.subheader("Feedback")

    conversation_history = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages)

    # Second model acting as the evaluator
    feedback_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    feedback_completion = feedback_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": """You are a helpful tool that provides feedback on an interviewee performance.
Before the Feedback give a score of 1 to 10.
Follow this format:
Overall Score: //Your score
Feedback: //Here you put your feedback
Give only the feedback do not ask any additional questions.
"""},
            {"role": "user", "content": (
                "This is the interview you need to evaluate. Keep in mind that you are only a tool. "
                f"And you shouldn't engage in any conversation: {conversation_history}")},
        ],
    )

    st.write(feedback_completion.choices[0].message.content)

    # Restart = reload the page (needs streamlit_js_eval)
    if st.button("Restart Interview", type="primary"):
        streamlit_js_eval(js_expressions="parent.window.location.reload()")
