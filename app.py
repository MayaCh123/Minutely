import os
import json, math
import random
from datetime import datetime
import streamlit as st
import time

# Import OpenAI and ElevenLabs SDKs
import openai
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from elevenlabs import save

from dotenv import load_dotenv
load_dotenv()



# === Configuration: API Keys ===
openai_api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

openai_client = OpenAI(api_key=openai_api_key)
elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)


# === Onboarding Check ===
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False

if not st.session_state.onboarded:
    st.set_page_config(page_title="Minutely", page_icon="🎙️", layout="centered")

    st.title("🎙️ Welcome to Minutely!")
    st.markdown("""
    **Learn something new—wherever you are.**  
    Minutely turns your curiosity into personalized, five-minute podcast episodes—perfect for your commute, workout, coffee break, or winding down at night.

    Let’s take a minute to show you around. This isn’t just a podcast generator—it’s a curiosity companion built just for you.

    ---

    ### 🔧 What Minutely Can Do:

    #### 🎚️ Adjustable Mood, Length and Complexity  
    Learning should match your mood. Choose *Beginner*, *Intermediate*, or *Expert* to control the level of depth and detail.

    #### 📝 Smart Suggestions  
    You don't always know what you want to learn next—and that’s okay!
    Minutely recommends fresh topics based on your previous interests. Whether you recently explored “AI ethics” or “the Renaissance,” you'll get suggestions that are relevant but not repetitive.

    #### 🕰️ Time Traveler Mode  
    Ever wondered how a Roman emperor or a future AI might explain your topic? Enable this mode to hear your episode from the perspective of another time—past or future.

    #### 🧠 Active Recall Quizzes  
    Remember more, effortlessly.
    Minutely helps you retain what you've learned by asking quick review questions based on all of your past episodes. These short quizzes are embedded into new episodes as memory boosters—perfect for spaced repetition and active learning.
    Just tick the checkbox and never forget anything.

    #### 🎲 Curiosity Roulette  
    Feeling indecisive? Let serendipity decide.
    Spin the curiosity wheel to get a fun, unexpected topic from your selected interests. It's a great way to explore ideas you might not think to ask about—like “why cats purr” or “how volcanoes shape the economy.”

    #### 📊 Minutely Wrapped 
    See your learning journey come to life.
    Your listening habits are turned into insights:
        - Total minutes learned
        - Your most explored topics
        - An AI career tip
        - Fun comparisons (like "you've learned enough to explain 10 TED talks")
        - Even a quirky AI-generated listener persona based on your interests

    ---

    👇 Let’s start by picking a few topics you're curious about!
    """)

    # === Category setup ===
    default_categories = ["Science", "History", "Art", "Technology", "AI", "Politics", "Music", "Entertainment"]

    if "verticals" not in st.session_state:
        st.session_state.verticals = default_categories.copy()

    if "selected_verticals" not in st.session_state:
        st.session_state.selected_verticals = default_categories[:4]  # preselect a few

    # Multiselect for existing popular categories
    chosen = st.multiselect("Choose from popular categories:",
                            options=st.session_state.verticals,
                            default=st.session_state.selected_verticals)

    st.session_state.selected_verticals = chosen

    # Add category input
    new_cat = st.text_input("Add another category:")
    if st.button("Add Interest", key="add_interest_btn") and new_cat:
        new_cat = new_cat.strip()
        if new_cat and new_cat not in st.session_state.verticals:
            st.session_state.verticals.append(new_cat)
        if new_cat and new_cat not in st.session_state.selected_verticals:
            st.session_state.selected_verticals.append(new_cat)
        st.rerun()

    # Display selected as pills
    if st.session_state.selected_verticals:
        st.write("**Selected Categories:**")
        st.markdown("".join(
            f"<span class='pill'>{cat}</span>" for cat in st.session_state.selected_verticals
        ), unsafe_allow_html=True)

    # Continue button
    st.markdown("""
        <style>
        .centered-button button {
            display: block;
            margin: 0 auto;
            background-color: #FF4B4B !important;
            color: white !important;
            font-size: 1.2rem !important;
            padding: 0.6em 1.5em !important;
            border-radius: 10px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="centered-button">', unsafe_allow_html=True)
    if st.button("✅ Start Exploring", key="start_exploring_btn"):
        st.session_state.onboarded = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


    # Inject pill style
    st.markdown("""
        <style>
        .pill {
            background-color: #ff4b4b !important;
            color: white;
            padding: 5px 10px;
            border-radius: 12px;
            margin: 4px;
            display: inline-block;
        }
        </style>
    """, unsafe_allow_html=True)

    st.stop()






# === App Page Configuration ===
st.set_page_config(page_title="Minutely", page_icon="🎙️", layout="centered")
st.markdown("""
    <style>
    .pill {background-color:#ff4b4b!important;color:#fff;padding:5px 10px;
           border-radius:12px;margin:4px;display:inline-block;}
    </style>""", unsafe_allow_html=True)

st.title("🎙️ Minutely")

# Initialize session state for stored topics (if not already)
if "past_topics" not in st.session_state:
    st.session_state.past_topics = []
# If a library file exists, load last few topics for suggestions (persistent across sessions)
library_file = "podcast_library.jsonl"
if os.path.exists(library_file) and not st.session_state.past_topics:
    try:
        with open(library_file, "r") as f:
            lines = f.readlines()
        # Parse last up to 5 unique topics from the end of the file
        recent_topics = []
        for line in reversed(lines):
            record = json.loads(line)
            topic = record.get("topic")
            if topic and topic not in recent_topics:
                recent_topics.append(topic)
            if len(recent_topics) >= 5:
                break
        st.session_state.past_topics = list(recent_topics)[::-1]  # reverse to original chronological order
    except Exception:
        st.session_state.past_topics = []  # If any error, start with empty list

# Predefined moods and their prompt style descriptions
mood_styles = {
    "💥 Mind-Blowing":    "with an extremely enthusiastic tone, providing astonishing facts and insights that will wow the listener",
    "☕ Chill & Curious": "in a calm, relaxed manner, as if casually exploring the topic with a sense of curiosity",
    "☁️ I’m Tired, Be Gentle": "in a gentle, soothing manner, using simple language and a slow pace for someone who is tired",
    "🔥 Hype Me Up to Learn": "in a very energetic, motivational tone that will pump up the listener and get them excited about learning",
    "🤓 Funny":           "in a humorous tone, incorporating light jokes and wit while still being informative"
}


# Create two tabs: one for generation and one for the library
tab_main, tab_library, tab_analytics,  tab_settings= st.tabs(["🎧 Home", "📚 Library", "📊 Wrapped", "⚙️ Settings"])



# ============== Generation Tab ==============
with tab_main:
    st.subheader("Create a New Minutely")
    
    # Mood selector
    mood = st.selectbox("Choose a mood/tone for the podcast:", list(mood_styles.keys()), index=1)

    # Time slider (minutes)
    minutes = st.slider("Desired audio length (minutes):", min_value=1, max_value=10, value=5)

    # Complexity slider
    complexity = st.select_slider(
        "Target Complexity Level:",
        options=["Beginner", "Intermediate", "Expert"],
        value="Intermediate"
    )

    # Load past topics from JSONL history (each line is a JSON object with a 'topic' field)
    def load_topics_history(file="topics.jsonl"):
        try:
            with open(file, "r") as f:
                return [json.loads(line)["topic"] for line in f]
        except FileNotFoundError:
            return []

    past_topics = load_topics_history()

    # After the user types a topic (or on app load), compute suggestions
    st.markdown("🎯 **Enter a topic you want to learn about:**")
    user_input = st.text_input("", key="topic_input", value=st.session_state.get("topic_input_generated", ""), label_visibility="collapsed")



    
    # -------- Related‑to‑past suggestion chips -----------------
    if st.session_state.past_topics:
        st.caption("Or pick something related to a past topic:")
        rel_titles = []

        # one GPT call per past topic – cache so it runs only once per session
        @st.cache_data(show_spinner=False)
        def related_topic(seed, exclude):
            prompt = (f"Suggest one concise learning topic that is *related* to "
                      f"'{seed}' but is **not the same** and not in {exclude}. "
                      f"Return only the title.")
            r = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8
            )
            return r.choices[0].message.content.strip()

        for seed in st.session_state.past_topics:
            rel_titles.append( related_topic(seed, st.session_state.past_topics) )

        cols = st.columns(len(rel_titles))
        for i, title in enumerate(rel_titles):
            if cols[i].button(title):
                st.session_state["topic_input_generated"] = title
                st.rerun()

    # -----------------------------------------------------------



    # ------------------ SUGGESTIONS ------------------
    suggestions = []
    if user_input:
        try:
            user_emb = openai_client.embeddings.create(
                input=user_input,
                model="text-embedding-ada-002"
            ).data[0].embedding

            # load past topics + embeddings from library
            past = []
            if os.path.exists(library_file):
                with open(library_file) as f:
                    for line in f:
                        rec = json.loads(line)
                        if "embedding" in rec:
                            past.append((rec["topic"], rec["embedding"]))

            # cosine similarity
            scored = []
            for topic, emb in past:
                if topic.lower() == user_input.lower():
                    continue
                dot = sum(u*v for u, v in zip(user_emb, emb))
                sim = dot / (math.dist(user_emb, [0]*len(user_emb)) *
                             math.dist(emb,       [0]*len(emb)))
                scored.append((sim, topic))

            scored.sort(reverse=True)
            base_topic = scored[0][1] if scored else user_input

            # ask GPT for a fresh spin on the closest topic
            prompt = (f"Suggest one fresh, fun learning topic that is *related* to "
                      f"'{base_topic}' but not the same and not already in this list: "
                      f"{[t for _, t in scored[:10]]}. Reply with only the topic title.")
            resp = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8
            )
            suggestions = [resp.choices[0].message.content.strip()]

        except Exception as e:
            st.warning(f"Suggestion engine failed: {e}")
    # -------------------------------------------------



    # Remove duplicates and limit to ~5 suggestions
    suggestions = suggestions[:5]

    # Display suggestions as buttons (only if there are suggestions)
    if suggestions:
        st.write("**You might also like:**")
        cols = st.columns(len(suggestions))
        for idx, suggestion in enumerate(suggestions):
            if cols[idx].button(suggestion, key=f"suggestion_{idx}"):
                st.session_state.topic_input = suggestion
                st.rerun()





    # Curiosity Roulette toggle (for random topic)
    if "curiosity_spun" not in st.session_state:
        st.session_state.curiosity_spun = False

    if st.button("🎲 Curiosity Roulette"):
        st.session_state.curiosity_spun = True
        spinning_placeholder = st.empty()

        # Simulate animation with fake spinning
        fake_spin_words = ["Books", "Space", "Pyramids", "Bees", "Jazz", "Fungi", "AI", "Atlantis", "Lasers"]
        for _ in range(12):
            spinning_placeholder.markdown(f"🌀 {random.choice(fake_spin_words)}")
            time.sleep(0.05)

        # Get selected interests (default to broad if none selected)
        interests = st.session_state.get("selected_verticals", ["Science", "History", "Technology"])
        interest_str = ", ".join(interests)

        # Ask GPT to generate one fun educational topic from user's selected categories
        spin_prompt = (
            f"Suggest one fun, random, creative educational podcast topic from the following interests: {interest_str}. "
            "Be specific and imaginative. Return only the title."
        )
        try:
            spin_response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": spin_prompt}],
                temperature=1.1
            )
            final_topic = spin_response.choices[0].message.content.strip()
        except Exception as e:
            final_topic = "The history of spoons (fallback)"
            st.warning(f"GPT failed: {e}")

        # Show final selected topic
        spinning_placeholder.markdown(f"🎉 Your topic: **{final_topic}**")
        st.session_state["roulette_topic"] = final_topic








    # Time Traveler mode toggle
    time_traveler_enabled = st.checkbox("🕰️ Time Traveler Mode: Past or Future Perspective")
    time_traveler_year = None
    if time_traveler_enabled:
        time_traveler_year = st.text_input("Enter a year (e.g. 3024 or 1492):", max_chars=10, label_visibility="collapsed")

    # Active recall
    recall_enabled = st.checkbox("🧠 Reinforce learning with a quick recall quiz at the end of your podcast based on your library", value=False)

    

    

    
    # Generate button triggers the AI and TTS pipeline
    # Custom styled "Generate My Minutely" button
    st.markdown("""
        <style>
        .generate-button button {
            display: block;
            margin: 2em auto;
            background-color: #4f46e5 !important;
            color: white !important;
            font-size: 1.3rem !important;
            padding: 0.75em 2em !important;
            border-radius: 12px !important;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="generate-button">', unsafe_allow_html=True)
    clicked = st.button("🎧 Generate My Minutely")
    st.markdown('</div>', unsafe_allow_html=True)

    if clicked:
        # Validate input or random selection
        
        if not user_input and not st.session_state.get("curiosity_spun", False):
            st.error("Please enter a topic or enable Curiosity Roulette for a random topic.")
        else:
            # Determine the final topic to use
            # Decide final topic properly
            if st.session_state.get("curiosity_spun", False):
                final_topic = st.session_state.get("roulette_topic", "")
            else:
                final_topic = user_input.strip()



            if not final_topic and curiosity:
                final_topic = random.choice(random_topics)
                st.session_state.topic_input = final_topic  # update input box for transparency
                st.info(f"Random topic selected: **{final_topic}**")
            if final_topic:
                # Construct the prompt for OpenAI
                tone_instruction = mood_styles.get(mood, "")
                # Approximate target word count from minutes (150 words/min avg)
                target_words = int(minutes * 150)
                # Build the messages for ChatCompletion
                system_msg = {
                    "role": "system",
                    "content": "You are a helpful assistant that generates educational podcast scripts for a text-to-speech app."
                }
                
                user_msg_content = (
                    f"Write a spoken monologue for an educational podcast episode about **{final_topic}**, "
                    f"{tone_instruction}. The episode should last around {minutes} minutes (~{target_words} words). "
                    f"Start with a natural, engaging introduction as if welcoming the listener, not with a title or sound cue. "
                    f"Then explain: (1) What it is, (2) Why it matters, (3) How it works or happened, and (4) a surprising or fun fact at the end."
                )

                if time_traveler_enabled and time_traveler_year:
                    user_msg_content += f" Tell this story from the perspective of someone living in the year {time_traveler_year}."
                elif time_traveler_enabled:
                    user_msg_content += " Tell this story from a historical or futuristic perspective."

                user_msg = {"role": "user", "content": user_msg_content}
                # Call OpenAI API for text generation (ChatCompletion)
                max_tokens = min(3000, target_words * 2)  # limit tokens for target length
                try:
                    response = openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[system_msg, user_msg],
                        max_tokens=max_tokens,
                        temperature=0.7
                        )
                except Exception as e:
                    st.error(f"Error during text generation: {e}")
                    st.stop()  # Halt further execution if text generation failed
                # Extract the generated script text
                script_text = response.choices[0].message.content.strip()

                # Active recall insertion (after script_text is available)
                if recall_enabled and st.session_state.past_topics:
                    previous_topics = [t for t in st.session_state.past_topics if t.lower() != final_topic.lower()]
                    if previous_topics:
                        quiz_topic = random.choice(previous_topics)

                        # 🔄 Try to load old script from the podcast library
                        def load_script_for_topic(search_topic):
                            try:
                                with open(library_file, "r") as f:
                                    for line in reversed(f.readlines()):
                                        record = json.loads(line)
                                        if record.get("topic", "").lower() == search_topic.lower():
                                            return record.get("script", "")
                            except Exception:
                                return ""
                            return ""

                        past_script = load_script_for_topic(quiz_topic)
                        if past_script:
                            quiz_prompt = (
                                f"You're reviewing an educational podcast. "
                                f"Based on this script, extract *one important fact*, and turn it into a quiz question and answer pair "
                                f"to reinforce learning.\n\nScript:\n{past_script}\n\n"
                                f"Return the output in this format:\n"
                                f"Question: ...\nAnswer: ..."
                            )

                            try:
                                quiz_resp = openai_client.chat.completions.create(
                                    model="gpt-3.5-turbo",
                                    messages=[{"role": "user", "content": quiz_prompt}],
                                    temperature=0.7
                                )
                                qa_text = quiz_resp.choices[0].message.content.strip()
                                quiz_text = f"\n\n🔁 **Quiz Review from \"{quiz_topic}\":**\n{qa_text}"
                                script_text += quiz_text
                            except Exception as e:
                                st.warning(f"Quiz generation failed: {e}")



                # Display the generated script text for the user
                st.write("**Generated Script:**")
                st.write(script_text)
                # Convert the script text to speech using ElevenLabs
                
                try:
                    with st.spinner("🎤 Converting text to speech with ElevenLabs..."):
                        audio = elevenlabs_client.generate(text=script_text, voice="Rachel")
                        save(audio, "output.mp3")  # Save to temporary output
                    st.success("✅ Audio generated successfully!")
                except Exception as e:
                    st.error(f"Error during audio generation: {e}")
                    st.stop()

                # Create unique filename for library
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                audio_filename = f"podcast_{timestamp}.mp3"

                # Copy output.mp3 to permanent filename
                import shutil
                shutil.copy("output.mp3", audio_filename)

                # --- Output display in Streamlit ---

                # Play from the temporary file
                st.audio("output.mp3", format="audio/mpeg")

                # Let user download the saved file
                with open(audio_filename, "rb") as audio_file:
                    st.download_button(
                        label="💾 Download MP3",
                        data=audio_file,
                        file_name=audio_filename,
                        mime="audio/mpeg"
                    )

                record = {
                    "timestamp": datetime.now().isoformat(sep=' ', timespec='seconds'),
                    "topic": final_topic,
                    "mood": mood,
                    "minutes": minutes,
                    "time_traveler": time_traveler_enabled,
                    "script": script_text,
                    "audio_file": audio_filename
                }

                # Try embedding separately
                try:
                    embedding = openai_client.embeddings.create(
                        input=final_topic,
                        model="text-embedding-ada-002"
                    ).data[0].embedding
                    record["embedding"] = embedding
                except Exception as e:
                    st.warning(f"Embedding failed: {e}")
                    record["embedding"] = None  # Or just skip this key

                # Finally save the podcast record
                try:
                    with open(library_file, "a") as f:
                        f.write(json.dumps(record) + "\n")
                except Exception as e:
                    st.error(f"⚠️ Could not save podcast to library: {e}")





                # Update past topics suggestions in session state (avoid duplicates)
                if final_topic not in st.session_state.past_topics:
                    st.session_state.past_topics.append(final_topic)
                    if len(st.session_state.past_topics) > 5:
                        # Keep only last 5 for suggestion chips
                        st.session_state.past_topics = st.session_state.past_topics[-5:]





# ============== Podcast Library Tab ==============
with tab_library:
    st.subheader("📜 Saved Podcasts Library")
    # Read and display saved podcast records
    if not os.path.exists(library_file) or os.stat(library_file).st_size == 0:
        st.info("No podcasts have been generated yet. Your creations will appear here.")
    else:
        # Load all records from the JSONL file
        with open(library_file, "r") as f:
            lines = f.readlines()
        records = [json.loads(line) for line in lines]
        records.reverse()  # show newest first
        for rec in records:
            topic = rec.get("topic", "Untitled Topic")
            timestamp = rec.get("timestamp", "")
            script = rec.get("script", "")
            audio_path = rec.get("audio_file", "")
            st.markdown(f"**Topic:** {topic}  \n*Generated:* {timestamp}*")
            # Audio player
            if audio_path and os.path.exists(audio_path):
                audio_data = open(audio_path, "rb").read()
                st.audio(audio_data, format="audio/mp3")
            else:
                st.write("_Audio file not found_")
            # Expander for script text
            if script:
                with st.expander("Show script text"):
                    st.write(script)
            st.divider()


# Settings Tab


# --- Settings Tab ---
with tab_settings:
    st.header("Settings & Categories")
    # Initialize default categories if not already in session state
    if "verticals" not in st.session_state:
        st.session_state.verticals = ["Science", "History", "Art", "Technology"]
    # Multiselect for active categories
    chosen = st.multiselect("Select categories for Curiosity Roulette:", 
                             options=st.session_state.verticals, 
                             default=st.session_state.verticals)
    st.session_state.selected_verticals = chosen
    # UI to add a new category
    new_cat = st.text_input("Add a new category:")
    if st.button("Add Category") and new_cat:
        new_cat = new_cat.strip()
        if new_cat and new_cat not in st.session_state.verticals:
            st.session_state.verticals.append(new_cat)
            st.session_state.selected_verticals.append(new_cat)
            st.success(f"Added category '{new_cat}'")
            # After adding new category
            st.markdown(f"<span style='background-color:#ff4b4b; color:white; padding:5px 10px; border-radius:12px; margin:4px; display:inline-block'>{new_cat}</span>", unsafe_allow_html=True)
            st.rerun()

    # UI to delete an existing category
    to_delete = st.selectbox("Delete a category:", options=[""] + st.session_state.verticals)
    if to_delete and st.button("Delete Category"):
        st.session_state.verticals.remove(to_delete)
        if to_delete in st.session_state.selected_verticals:
            st.session_state.selected_verticals.remove(to_delete)
        st.warning(f"Removed category '{to_delete}'")



# analytics tab
with tab_analytics:
    st.header("🎧 Minutely Wrapped")

    # Load history
    try:
        with open("podcast_library.jsonl", "r") as f:
            records = [json.loads(line) for line in f if "topic" in json.loads(line)]
    except:
        records = []

    total_sessions = len(records)
    total_minutes = sum(int(rec.get("minutes", 0)) for rec in records)
    unique_topics = len(set(rec["topic"].lower() for rec in records if "topic" in rec))

    st.metric("🎙️ Podcasts Generated", total_sessions)
    st.metric("⏱️ Minutes Listened", total_minutes)

    if total_minutes > 0:
        # Funny comparison
        prompt_cmp = f"Compare {total_minutes} minutes of listening to something fun like number of pizzas eaten, Netflix episodes watched, or miles walked."
        response_cmp = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_cmp}],
            temperature=0.8
        )
        st.write(f"🎯 Equivalent To: *{response_cmp.choices[0].message.content.strip()}*")

    if records:
        # Extract frequent themes
        from collections import Counter
        words = []
        for rec in records:
            for w in rec["topic"].lower().split():
                if w.isalpha() and len(w) > 3:
                    words.append(w)
        common_words = Counter(words).most_common(3)
        if common_words:
            top_words = [w for w, _ in common_words]
            st.write(f"**Frequent Themes:** _{', '.join(top_words)}_")
        top_topics = Counter([rec["topic"].lower() for rec in records]).most_common(3)
        top_topics = [t[0] for t in top_topics]
        st.write(f"**Favorite Topics:** {', '.join(top_topics).title()}")

        
        # AI Career Tip
        tip_prompt = (
            f"This person enjoys topics about {', '.join(top_words or top_topics)}. "
            "Give them one personalized career or life tip in the style of an AI mentor, like 'You sound like a CEO' or 'You should get a cat'."
        )
        tip_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": tip_prompt}],
            temperature=0.9
        )
        st.subheader("💡 AI Career Tip")
        st.info(tip_response.choices[0].message.content.strip())

        # Listener Persona
        prompt = (
            f"The user listens to educational podcasts mostly about: {', '.join(top_words or top_topics)}. "
            "Invent a whimsical profile with:\n"
            "• a two-word nickname\n• an imaginary job title\n• favourite book\n• how they spend a Sunday"
        )
        resp = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a playful creative writer."},
                      {"role": "user", "content": prompt}],
            temperature=0.9
        )
        st.subheader("🌟 Your Listener Persona")
        st.markdown(resp.choices[0].message.content.strip())

        

    try:
        with open("podcast_library.jsonl", "r") as f:
            history = [json.loads(line)["topic"] for line in f if "topic" in json.loads(line)]
    except:
        history = []