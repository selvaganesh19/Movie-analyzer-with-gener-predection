import streamlit as st
import requests
import os
import re
from dotenv import load_dotenv
import time

# ================== Load environment variables ==================
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Check if API keys are loaded
if not OPENROUTER_API_KEY:
    st.error("❌ OPENROUTER_API_KEY not found in environment variables")
if not TMDB_API_KEY:
    st.error("❌ TMDB_API_KEY not found in environment variables")

# ================== Genre Mapping ==================
GENRE_MAP = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35,
    "crime": 80, "documentary": 99, "drama": 18, "family": 10751,
    "fantasy": 14, "history": 36, "horror": 27, "music": 10402,
    "mystery": 9648, "romance": 10749, "science fiction": 878, "sci-fi": 878,
    "thriller": 53, "war": 10752, "western": 37
}

# ================== Natural Language Genre Detection ==================
def detect_genre_from_text(text: str):
    """Detect genre from natural language input using AI"""
    if not OPENROUTER_API_KEY:
        return None
        
    prompt = f"""
    Based on this user request, identify the most suitable movie genre from this list:
    {list(GENRE_MAP.keys())}
    
    User request: "{text}"
    
    Return only the genre name from the list above, nothing else.
    """
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "AI Movie Recommender"
    }

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a genre classification expert. Return only the genre name."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 20
    }

    try:
        resp = requests.post("https://openrouter.ai/api/v1/chat/completions",
                             headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
        
        # Check if the returned content matches any genre
        for genre in GENRE_MAP.keys():
            if genre in content:
                return genre
        return None
        
    except Exception as e:
        st.error(f"❌ Error detecting genre: {e}")
        return None

# ================== AI Plot Scoring ==================
def score_plot_coherence(movie_title: str, plot: str, genre: str):
    """Score plot coherence using OpenRouter AI"""
    if not OPENROUTER_API_KEY or not plot or plot == "No summary available.":
        return "N/A"

    prompt = f"""
    Rate the plot coherence of this movie on a scale of 1–10.
    Title: {movie_title}
    Genre: {genre}
    Plot: {plot}
    Return only a single number (1–10) with no extra text.
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "AI Movie Recommender"
    }

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a concise movie analysis expert who only outputs numbers."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 8
    }

    try:
        resp = requests.post("https://openrouter.ai/api/v1/chat/completions",
                             headers=headers, json=payload, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

        # Extract only digits (handle artifacts like "<|begin...|>")
        cleaned = re.sub(r"[^0-9.]", "", content)
        if cleaned:
            try:
                val = float(cleaned)
                if 1 <= val <= 10:
                    return f"{val:.1f}/10"
            except ValueError:
                pass
        return "N/A"

    except Exception as e:
        st.error(f"❌ Error scoring coherence: {e}")
        return "N/A"


# ================== TMDB Movie Fetch ==================
def get_tmdb_recommendations(genre: str, num_movies: int = 10, retry_count: int = 3):
    """Fetch movie recommendations from TMDB based on selected genre with retry logic"""
    for attempt in range(retry_count):
        try:
            genre_id = GENRE_MAP.get(genre.lower(), 18)  # Default to drama
            params = {
                "api_key": TMDB_API_KEY,
                "with_genres": genre_id,
                "sort_by": "popularity.desc",
                "page": 1,
                "language": "en"
            }

            # Increased timeout and added retry logic
            resp = requests.get("https://api.themoviedb.org/3/discover/movie", 
                              params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            movies = []
            for movie in data.get("results", [])[:num_movies]:
                movies.append({
                    "title": movie.get("title"),
                    "overview": movie.get("overview"),
                    "release_date": movie.get("release_date"),
                    "vote_average": movie.get("vote_average"),
                    "poster_path": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}"
                    if movie.get('poster_path') else None,
                    "popularity": movie.get("popularity", 0)
                })
            return movies

        except requests.exceptions.ConnectTimeout:
            if attempt < retry_count - 1:
                st.warning(f"⏳ Connection timeout. Retrying... (Attempt {attempt + 2}/{retry_count})")
                time.sleep(2)  # Wait 2 seconds before retry
                continue
            else:
                st.error("❌ Connection timeout after multiple attempts. Please check your internet connection.")
                return []
        except requests.exceptions.RequestException as e:
            if attempt < retry_count - 1:
                st.warning(f"⏳ Request failed. Retrying... (Attempt {attempt + 2}/{retry_count})")
                time.sleep(2)
                continue
            else:
                st.error(f"❌ Error fetching TMDB recommendations after {retry_count} attempts: {e}")
                return []
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")
            return []
    
    return []


# ================== Streamlit UI ==================
st.set_page_config(page_title="🎬 AI Movie Recommender", layout="wide")

# Enhanced CSS Styling for better visibility
st.markdown("""
<style>
.main-header { 
    text-align: center; 
    padding: 2rem 0; 
}
.movie-card {
    border: 2px solid var(--secondary-background-color, #ddd); 
    border-radius: 15px; 
    padding: 1.5rem;
    margin: 1.5rem 0; 
    background: var(--background-color, white); 
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    transition: all 0.3s ease;
}
.movie-card:hover {
    border-color: var(--primary-color, #ff6b6b);
    box-shadow: 0 6px 12px rgba(0,0,0,0.2);
}
.movie-title {
    font-size: 1.4rem;
    font-weight: bold;
    color: var(--text-color, #333);
    margin-bottom: 0.5rem;
}
.movie-info {
    background: var(--secondary-background-color, #f0f2f6);
    border-radius: 10px;
    padding: 1rem;
    margin: 1rem 0;
}
.plot-text {
    background: var(--background-color, white);
    border-left: 4px solid var(--primary-color, #ff6b6b);
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0 8px 8px 0;
}
.metric-container {
    display: flex;
    justify-content: space-around;
    margin: 1rem 0;
}
.metric-item {
    text-align: center;
    padding: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ================== Header ==================
st.markdown(
    '<div class="main-header">'
    '<h1>🎬 AI Movie Recommender</h1>'
    '<h3>🤖 TMDB Recommendations + OpenRouter AI Plot Scoring</h3>'
    '</div>',
    unsafe_allow_html=True
)

# ================== API Key Status ==================
if OPENROUTER_API_KEY and TMDB_API_KEY:
    st.success("✅ API keys loaded successfully!")
else:
    st.warning("⚠️ Please check your .env file and ensure both API keys are set")

# ================== User Input ==================
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("### 🎯 Choose Your Movie Preference")
    
    # Tab selection for input method
    tab1, tab2 = st.tabs(["📋 Select Genre", "💬 Describe What You Want"])
    
    with tab1:
        genre = st.selectbox(
            "Select a Genre:",
            list(GENRE_MAP.keys()),
            index=list(GENRE_MAP.keys()).index("drama")
        )
        selected_genre = genre
        
    with tab2:
        user_request = st.text_input(
            "Describe what kind of movies you want:",
            placeholder="e.g., 'I want something funny and light-hearted' or 'Show me some scary movies'"
        )
        if user_request:
            with st.spinner("🤖 Understanding your request..."):
                detected_genre = detect_genre_from_text(user_request)
                if detected_genre:
                    st.success(f"✅ Detected genre: **{detected_genre.title()}**")
                    selected_genre = detected_genre
                else:
                    st.warning("❓ Couldn't detect genre. Using default 'drama'.")
                    selected_genre = "drama"
        else:
            selected_genre = "drama"
    
    num_movies = st.slider("Number of Movies:", min_value=3, max_value=15, value=8)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🎬 Recommend Movies", type="primary", use_container_width=True):
        if OPENROUTER_API_KEY and TMDB_API_KEY:
            st.session_state['get_recommendations'] = True
            st.session_state['genre'] = selected_genre
            st.session_state['num_movies'] = num_movies
        else:
            st.error("❌ Cannot proceed without API keys. Please check your .env file.")

# ================== Info Section ==================
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("### 🔧 How it works:")
    st.markdown("""
    1. 🎭 **Choose Input Method** - Select genre directly or describe what you want
    2. 🤖 **AI Genre Detection** - AI understands your natural language request
    3. 🎬 **TMDB Fetch** - Fetches top-rated movies from TMDB based on the genre
    4. 🧠 **AI Scoring** - Scores the plot coherence of each movie using OpenRouter AI
    5. 📊 **Results** - Displays the movies with their details and AI scores
    """)

# ================== Results Display (Fully Visible) ==================
if 'get_recommendations' in st.session_state and st.session_state['get_recommendations']:
    st.markdown("---")
    st.markdown(f"## 🍿 Recommended {st.session_state['genre'].title()} Movies")
    
    with st.spinner("🎬 Fetching movie recommendations..."):
        movies = get_tmdb_recommendations(st.session_state['genre'], st.session_state['num_movies'])

    if movies:
        # Display each movie in a fully visible card format
        for idx, movie in enumerate(movies, 1):
            st.markdown('<div class="movie-card">', unsafe_allow_html=True)
            
            # Movie Title Header
            st.markdown(f'<div class="movie-title">#{idx} 🎬 {movie["title"]}</div>', 
                       unsafe_allow_html=True)
            
            # Create columns for poster and details
            poster_col, details_col = st.columns([1, 3])
            
            with poster_col:
                if movie["poster_path"]:
                    try:
                        st.image(movie["poster_path"], width=200, caption="Movie Poster")
                    except Exception:
                        st.write("🖼️ **Poster unavailable**")
                else:
                    st.write("🖼️ **No poster available**")
            
            with details_col:
                # Movie information in a styled container
                st.markdown('<div class="movie-info">', unsafe_allow_html=True)
                
                # Metrics in columns
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                with metric_col1:
                    st.metric("🗓️ Release Date", movie['release_date'][:4] if movie['release_date'] else 'Unknown')
                with metric_col2:
                    st.metric("⭐ TMDB Rating", f"{movie['vote_average']}/10")
                with metric_col3:
                    st.metric("🔥 Popularity", f"{movie['popularity']:.0f}")
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Plot overview in a styled container
                if movie["overview"]:
                    st.markdown('<div class="plot-text">', unsafe_allow_html=True)
                    st.markdown("**📖 Plot Summary:**")
                    st.write(movie["overview"])
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("📝 No plot summary available")
                
                # AI Plot Scoring Button
                col_button, col_score = st.columns([1, 2])
                with col_button:
                    if st.button(f"🤖 Get AI Score", key=f"score_{idx}_{movie['title']}", 
                               help="Click to get AI plot coherence score"):
                        with st.spinner("🧠 AI is analyzing the plot..."):
                            score = score_plot_coherence(movie["title"], movie["overview"], st.session_state['genre'])
                            st.session_state[f'score_{idx}'] = score
                
                with col_score:
                    if f'score_{idx}' in st.session_state:
                        score_value = st.session_state[f'score_{idx}']
                        if score_value != "N/A":
                            st.success(f"🎯 **AI Plot Coherence Score: {score_value}**")
                        else:
                            st.warning("❓ **AI Score: Not Available**")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")  # Separator between movies
        
        # Action buttons at the bottom
        st.markdown("### 🎛️ Actions")
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🔄 Try Another Search", use_container_width=True):
                # Clear all stored scores
                for key in list(st.session_state.keys()):
                    if key.startswith('score_'):
                        del st.session_state[key]
                st.session_state['get_recommendations'] = False
                st.rerun()
        
        with col2:
            if st.button("🧠 Score All Plots", use_container_width=True):
                with st.spinner("🤖 Getting AI scores for all movies..."):
                    for idx, movie in enumerate(movies, 1):
                        if f'score_{idx}' not in st.session_state:
                            score = score_plot_coherence(movie["title"], movie["overview"], st.session_state['genre'])
                            st.session_state[f'score_{idx}'] = score
                st.success("✅ All AI scores have been calculated!")
                st.rerun()
        
        with col3:
            if st.button("📊 Show Summary", use_container_width=True):
                st.markdown("### 📈 Summary Statistics")
                total_movies = len(movies)
                avg_rating = sum(movie['vote_average'] for movie in movies) / total_movies
                highest_rated = max(movies, key=lambda x: x['vote_average'])
                
                summary_col1, summary_col2, summary_col3 = st.columns(3)
                with summary_col1:
                    st.metric("🎬 Total Movies", total_movies)
                with summary_col2:
                    st.metric("⭐ Average Rating", f"{avg_rating:.1f}/10")
                with summary_col3:
                    st.metric("🏆 Highest Rated", f"{highest_rated['title']}")
    
    else:
        st.error("🚫 No movies found for the selected genre and criteria. Try a different genre or check your internet connection.")