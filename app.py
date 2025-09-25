import streamlit as st
import requests
import os
import json
from dotenv import load_dotenv

# Load env
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Language map
LANGUAGE_MAP = {
    "english": "en", "hindi": "hi", "tamil": "ta", "telugu": "te",
    "french": "fr", "german": "de", "korean": "ko",
    "japanese": "ja", "spanish": "es", "italian": "it",
    "chinese": "zh", "all": "all"
}

# Genre mapping for TMDB
GENRE_MAP = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35,
    "crime": 80, "documentary": 99, "drama": 18, "family": 10751,
    "fantasy": 14, "history": 36, "horror": 27, "music": 10402,
    "mystery": 9648, "romance": 10749, "science fiction": 878,
    "thriller": 53, "war": 10752, "western": 37
}

# --- OpenRouter API calls
def predict_genre_from_mood(mood: str):
    """Use AI to predict movie genre from user's mood"""
    if not OPENROUTER_API_KEY:
        return "drama"  # Default fallback
    
    prompt = f"""
    Based on the mood '{mood}', predict the most suitable movie genre.
    Choose from: action, adventure, animation, comedy, crime, documentary, drama, 
    family, fantasy, history, horror, music, mystery, romance, science fiction, 
    thriller, war, western.
    
    Return only the genre name in lowercase, nothing else.
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Movie Recommender App"
    }

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a mood-to-genre prediction assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 50
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        response_data = resp.json()
        
        if "choices" in response_data and response_data["choices"]:
            genre = response_data["choices"][0]["message"]["content"].strip().lower()
            return genre if genre in GENRE_MAP else "drama"
        return "drama"
        
    except Exception as e:
        print(f"❌ Error predicting genre: {e}")
        return "drama"

def score_plot_coherence(movie_title: str, plot: str, genre: str):
    """Score plot coherence using AI"""
    if not OPENROUTER_API_KEY or not plot or plot == "No summary available.":
        return "N/A"
    
    prompt = f"""
    Rate the plot coherence of this movie on a scale of 1-10:
    
    Title: {movie_title}
    Genre: {genre}
    Plot: {plot}
    
    Consider:
    - Does the plot make logical sense?
    - Is it well-structured?
    - Does it match the genre?
    
    Return only a number between 1-10, nothing else.
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Movie Recommender App"
    }

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a movie plot analysis expert."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 10
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        response_data = resp.json()
        
        if "choices" in response_data and response_data["choices"]:
            score = response_data["choices"][0]["message"]["content"].strip()
            # Extract number from response
            try:
                score_num = float(score.split()[0])
                return f"{score_num}/10" if 1 <= score_num <= 10 else "N/A"
            except:
                return "N/A"
        return "N/A"
        
    except Exception as e:
        print(f"❌ Error scoring plot coherence: {e}")
        return "N/A"

# --- TMDB API calls
def get_tmdb_recommendations(genre: str, language: str, num_movies: int = 10):
    """Get movie recommendations from TMDB based on genre"""
    try:
        genre_id = GENRE_MAP.get(genre.lower(), 18)  # Default to drama
        lang_code = LANGUAGE_MAP.get(language.lower(), "en")
        
        params = {
            "api_key": TMDB_API_KEY,
            "with_genres": genre_id,
            "sort_by": "popularity.desc",
            "page": 1,
            "language": lang_code if lang_code != "all" else "en"
        }
        
        resp = requests.get("https://api.themoviedb.org/3/discover/movie", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        movies = []
        for movie in data.get("results", [])[:num_movies]:
            movies.append({
                "title": movie.get("title"),
                "overview": movie.get("overview"),
                "release_date": movie.get("release_date"),
                "vote_average": movie.get("vote_average"),
                "poster_path": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None,
                "genre_ids": movie.get("genre_ids", []),
                "popularity": movie.get("popularity", 0)
            })
        
        return movies
        
    except Exception as e:
        print(f"❌ Error fetching TMDB recommendations: {e}")
        return []

def get_tmdb_movie_details(movie_id: int):
    """Get detailed movie information from TMDB"""
    try:
        params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "credits"
        }
        
        resp = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Get director and cast
        credits = data.get("credits", {})
        director = next((crew["name"] for crew in credits.get("crew", []) if crew["job"] == "Director"), "Unknown")
        cast = [actor["name"] for actor in credits.get("cast", [])[:5]]  # Top 5 actors
        
        return {
            "director": director,
            "cast": ", ".join(cast) if cast else "Unknown",
            "runtime": data.get("runtime", "Unknown"),
            "budget": data.get("budget", 0),
            "revenue": data.get("revenue", 0),
            "imdb_id": data.get("imdb_id", "")
        }
        
    except Exception as e:
        print(f"❌ Error fetching movie details: {e}")
        return None

# --- Streamlit UI
st.set_page_config(page_title="🎬 AI Movie Recommender", layout="wide")

# Custom CSS - removed white box styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
    }
    .center-container {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
        padding: 2rem;
        max-width: 800px;
        margin: 0 auto;
        margin-bottom: 2rem;
    }
    .results-container {
        margin-top: 3rem;
        padding-top: 2rem;
    }
    .movie-card {
        border: 1px solid #ddd; 
        border-radius: 10px; 
        padding: 1rem; 
        margin: 1rem 0;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown('<div class="main-header"><h1>🎬 AI Movie Recommender</h1><h3>🤖 TMDB Recommendations + OpenRouter AI Analysis</h3></div>', unsafe_allow_html=True)

# Centered Controls Container - removed the div wrapper
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("### 🎯 Your Preferences")
    
    mood = st.text_input(
        "Enter your mood:", 
        value="happy", 
        help="e.g., happy, sad, excited, relaxed, adventurous",
        placeholder="What's your mood today?"
    )
    
    language = st.selectbox(
        "Select Language:", 
        list(LANGUAGE_MAP.keys()), 
        index=0,
        help="Choose your preferred movie language"
    )
    
    num_movies = st.slider(
        "Number of movies:", 
        min_value=3, 
        max_value=15, 
        value=8,
        help="How many movie recommendations do you want?"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Centered button
    if st.button("🎬 Get My Movie Recommendations", type="primary", use_container_width=True):
        st.session_state['get_recommendations'] = True
        st.session_state['mood'] = mood
        st.session_state['language'] = language
        st.session_state['num_movies'] = num_movies

# How it works info (centered)
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("### 🔧 How it works:")
    st.markdown("""
    1. 🤖 **AI Genre Prediction** - AI analyzes your mood to predict the perfect movie genre
    2. 🎬 **TMDB Discovery** - Fetches high-quality movie recommendations from TMDB database  
    3. 🧠 **Plot Analysis** - AI scores each movie's plot coherence and quality
    4. 📊 **Smart Recommendations** - Combines all data for personalized movie suggestions
    """)

# Results Section
if st.session_state.get('get_recommendations', False):
    st.markdown('<div class="results-container">', unsafe_allow_html=True)
    
    with st.spinner("🤖 Analyzing your mood and finding perfect movies..."):
        # Step 1: Predict genre from mood using AI
        predicted_genre = predict_genre_from_mood(st.session_state['mood'])
        
        # Centered genre prediction result
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info(f"🎭 AI predicted genre: **{predicted_genre.title()}** based on your mood: '{st.session_state['mood']}'")
        
        # Step 2: Get TMDB recommendations
        tmdb_movies = get_tmdb_recommendations(predicted_genre, st.session_state['language'], st.session_state['num_movies'])
        
        if not tmdb_movies:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.error("⚠️ No movies found. Please check your TMDB API key or try a different mood/language.")
        else:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.success(f"🎉 Found {len(tmdb_movies)} movies perfect for you!")
            
            st.markdown("---")
            
            # Display movies in a grid
            for idx in range(0, len(tmdb_movies), 2):
                cols = st.columns(2)
                
                for i, col in enumerate(cols):
                    if idx + i < len(tmdb_movies):
                        movie = tmdb_movies[idx + i]
                        
                        with col:
                            # Movie card styling
                            st.markdown('<div class="movie-card">', unsafe_allow_html=True)
                            
                            # Movie title and year
                            title = movie["title"]
                            year = movie["release_date"][:4] if movie["release_date"] else "Unknown"
                            st.subheader(f"🎬 {title} ({year})")
                            
                            # Rating and poster
                            poster_col, info_col = st.columns([1, 2])
                            
                            with poster_col:
                                if movie["poster_path"]:
                                    st.image(movie["poster_path"], width=120)
                                else:
                                    st.write("🖼️ No poster")
                            
                            with info_col:
                                # TMDB rating
                                tmdb_rating = movie["vote_average"]
                                st.metric("TMDB Rating", f"⭐ {tmdb_rating}/10")
                                
                                # Popularity metric
                                popularity = movie.get("popularity", 0)
                                st.metric("Popularity", f"🔥 {popularity:.0f}")
                                
                                # Plot coherence scoring using AI
                                with st.spinner("🧠 Analyzing..."):
                                    coherence_score = score_plot_coherence(title, movie["overview"], predicted_genre)
                                    st.metric("AI Plot Score", f"🧠 {coherence_score}")
                            
                            # Plot/Overview
                            if movie["overview"]:
                                st.write("**Plot:**")
                                st.write(movie["overview"][:200] + "..." if len(movie["overview"]) > 200 else movie["overview"])
                            
                            st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Reset button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 Get New Recommendations", use_container_width=True):
            st.session_state['get_recommendations'] = False
            st.rerun()