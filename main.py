from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
import pyjokes
import webbrowser
import os
import time
import pyautogui
import requests
import random
import threading
from textblob import TextBlob
from googletrans import Translator
from bs4 import BeautifulSoup
import wikipediaapi
import urllib.parse
from newsapi import NewsApiClient
import aiohttp
import asyncio
from cachetools import TTLCache

app = Flask(__name__)
HISTORY_FILE = "history.txt"

# Initialize NewsAPI client (replace 'your_api_key' with a real NewsAPI key)
newsapi = NewsApiClient(api_key='your_api_key')

# Initialize in-memory cache (TTL = 10 minutes)
cache = TTLCache(maxsize=100, ttl=600)

# ============ MANUAL Q&A ============

manual_qa = {
    "what is your name": "I'm Mini, your Personal Voice assistant.",
    "who created you": "I was created by Ravindra Pal as a smart assistant.",
    "what can you do": "I can tell jokes, fetch weather, take notes, play music, schedule tasks, run quizzes, search Wikipedia, fetch the latest news, redirect to Google search, and much more!",
    "atul sir": "You can find Prof. Atul Sir in the Computer Science Engineering department. I suggest visiting there!",
    "tarunedra sir": "You can find Prof. Tarunedra Sir in the Computer Science Engineering department. I suggest visiting there!",
    "praveen sir": "You can find Prof. Praveen Sir in the Computer Science Engineering department. I suggest visiting there!",
}

# ============ QUIZ DATA ============

quiz_questions = [
    {"question": "What does HTML stand for?", "options": ["A) Hyper Text Markup Language", "B) High Text Machine Language", "C) Hyperlink Text Management Language"], "answer": "A", "correct": "Hyper Text Markup Language"},
    {"question": "Which CSS property controls text size?", "options": ["A) font-weight", "B) font-size", "C) text-transform"], "answer": "B", "correct": "font-size"},
    {"question": "In JavaScript, which method adds an element to the end of an array?", "options": ["A) push()", "B) pop()", "C) shift()"], "answer": "A", "correct": "push()"},
    {"question": "What HTML tag is used for creating a hyperlink?", "options": ["A) <link>", "B) <a>", "C) <href>"], "answer": "B", "correct": "<a>"},
    {"question": "Which CSS selector targets an element by its ID?", "options": ["A) .class", "B) #id", "C) element"], "answer": "B", "correct": "#id"},
    {"question": "In JavaScript, what is the output of '2' + 2?", "options": ["A) 4", "B) 22", "C) Error"], "answer": "B", "correct": "22"},
    {"question": "Which HTML attribute specifies an image source?", "options": ["A) src", "B) alt", "C) href"], "answer": "A", "correct": "src"},
    {"question": "What CSS property is used to make text bold?", "options": ["A) font-style", "B) font-weight", "C) text-decoration"], "answer": "B", "correct": "font-weight"},
    {"question": "In JavaScript, which keyword declares a variable with block scope?", "options": ["A) var", "B) let", "C) const"], "answer": "B", "correct": "let"},
    {"question": "Which HTML element is used for the largest heading?", "options": ["A) <h1>", "B) <h6>", "C) <header>"], "answer": "A", "correct": "<h1>"},
    {"question": "In CSS, how do you center a block element horizontally?", "options": ["A) margin: auto", "B) text-align: center", "C) align-items: center"], "answer": "A", "correct": "margin: auto"},
    {"question": "In JavaScript, which method removes the last element from an array?", "options": ["A) pop()", "B) shift()", "C) splice()"], "answer": "A", "correct": "pop()"},
    {"question": "Which HTML tag defines a paragraph?", "options": ["A) <p>", "B) <div>", "C) <span>"], "answer": "A", "correct": "<p>"},
    {"question": "Which CSS property sets the background color?", "options": ["A) color", "B) background-color", "C) border-color"], "answer": "B", "correct": "background-color"},
    {"question": "In JavaScript, what does '===' check for?", "options": ["A) Value only", "B) Value and type", "C) Reference"], "answer": "B", "correct": "Value and type"},
    {"question": "Which HTML attribute provides alternative text for images?", "options": ["A) src", "B) alt", "C) title"], "answer": "B", "correct": "alt"},
    {"question": "In CSS, which unit is relative to the font size of the element?", "options": ["A) px", "B) rem", "C) vw"], "answer": "B", "correct": "rem"},
    {"question": "In JavaScript, which method loops through array elements?", "options": ["A) forEach()", "B) map()", "C) filter()"], "answer": "A", "correct": "forEach()"},
    {"question": "Which HTML tag creates an unordered list?", "options": ["A) <ol>", "B) <ul>", "C) <li>"], "answer": "B", "correct": "<ul>"},
    {"question": "In CSS, what does 'display: flex' do?", "options": ["A) Hides the element", "B) Creates a flexible layout", "C) Centers the element"], "answer": "B", "correct": "Creates a flexible layout"}
]

# Quiz state management
quiz_sessions = {}  # {session_id: {"questions": list, "current_question": int, "score": int, "answers": list}}

# ============ FUNCTIONS ============

# Logging history to a file
def log_history(prompt, response):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"[{datetime.now()}]\nUser: {prompt}\nAssistant: {response}\n\n")

# Getting current time and date
def get_time_date():
    now = datetime.now()
    return now.strftime("Current time is %I:%M %p on %A, %d %B %Y.")

# Fetching weather info for current location using IP-based geolocation
def get_weather():
    try:
        geo_url = "https://ipinfo.io/json"
        geo_data = requests.get(geo_url).json()
        loc = geo_data.get("loc", "40.7128,-74.0060")
        lat, lon = loc.split(",")

        api_key = os.getenv("e878597c2e342a03d260177675a8305e", "1b9a6dcf60e2947a519c6a0752422864")  # Replace with actual key
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        data = requests.get(weather_url).json()

        if data.get("cod") != 200:
            return f"Could not fetch weather for your location. Please try again."

        temp = data['main']['temp']
        description = data['weather'][0]['description']
        city = data['name']
        
        return f"The current weather in {city} is {description} with a temperature of {temp}°C."
    except Exception as e:
        return f"Failed to fetch weather. Error: {str(e)}"

# Asynchronous HTTP request helper
async def fetch_url(url, headers=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=5) as response:
            return await response.text()

# Google search based fallback answer with improved scraping
async def google_search_answer(query):
    cache_key = f"google_{query}"
    if cache_key in cache:
        return cache[cache_key]

    try:
        # Construct the Google search URL
        encoded_query = urllib.parse.quote(query)
        google_url = f"https://www.google.com/search?q={encoded_query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        html = await fetch_url(google_url, headers=headers)
        soup = BeautifulSoup(html, "html.parser")

        # Try to find a featured snippet (broadened classes as of May 2025)
        snippet_classes = ["hgKElc", "BNeawe s3v9rd AP7Wnd", "BNeawe iBp4i AP7Wnd", "VwiC3b", "MjjYud"]
        for class_name in snippet_classes:
            snippet = soup.find("div", class_=class_name)
            if snippet:
                answer = snippet.get_text().strip()
                if len(answer) > 500:
                    answer = answer[:500] + "..."
                cache[cache_key] = answer
                return answer

        # Fallback: Extract the first search result link and scrape its content
        result_link = soup.find("a", href=True, class_="BVG0Nb")
        if result_link:
            link = result_link['href']
            if link.startswith("http"):
                html = await fetch_url(link, headers=headers)
                soup = BeautifulSoup(html, "html.parser")
                paragraphs = soup.find_all("p", limit=3)  # Check up to 3 paragraphs
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 50:
                        if len(text) > 500:
                            text = text[:500] + "..."
                        cache[cache_key] = text
                        return text

        answer = "I couldn't find a clear answer on Google. Try rephrasing your question."
        cache[cache_key] = answer
        return answer
    except Exception as e:
        answer = f"Error fetching answer from Google: {str(e)}"
        cache[cache_key] = answer
        return answer

# Redirect to Google search with the prompt
def redirect_to_google_search(query):
    # Remove "google" from the query and clean it
    query = query.lower().replace("google", "").strip()
    if not query:
        return "Please provide a search query to redirect to Google."
    
    # Construct the Google search URL
    encoded_query = urllib.parse.quote(query)
    google_url = f"https://www.google.com/search?q={encoded_query}"
    
    # Open the URL in the user's default browser
    webbrowser.open(google_url)
    return f"Opening Google search for '{query}'..."

# Fetch answer from Wikipedia with improved disambiguation handling
async def fetch_wikipedia_answer(query):
    cache_key = f"wiki_{query}"
    if cache_key in cache:
        return cache[cache_key]

    try:
        wiki = wikipediaapi.Wikipedia(
            language='en',
            user_agent="NovaAIAssistant/1.0 (contact: officialravindrapal@email.com)"
        )
        query = query.lower().replace("wikipedia", "").strip()
        if not query:
            answer = "Please provide a specific question to search on Wikipedia."
            cache[cache_key] = answer
            return answer

        # Check the initial page
        page = wiki.page(query)
        if page.exists():
            summary = page.summary.split('\n')[0]
            # Check if it's a disambiguation page
            if "may refer to:" in summary.lower() or "most commonly refers to:" in summary.lower():
                # Fetch links from the disambiguation page
                links = page.links
                # Prioritize tech-related articles for ambiguous terms (e.g., "Python")
                priority_terms = ["programming language", "software", "technology"]
                for title in links:
                    for term in priority_terms:
                        if term in title.lower():
                            page = wiki.page(title)
                            if page.exists():
                                summary = page.summary.split('\n')[0]
                                if len(summary) > 500:
                                    summary = summary[:500] + "..."
                                cache[cache_key] = summary
                                return summary
                # If no priority match, take the first link
                first_link = next(iter(links), None)
                if first_link:
                    page = wiki.page(first_link)
                    if page.exists():
                        summary = page.summary.split('\n')[0]
                        if len(summary) > 500:
                            summary = summary[:500] + "..."
                        cache[cache_key] = summary
                        return summary
            else:
                if len(summary) > 500:
                    summary = summary[:500] + "..."
                cache[cache_key] = summary
                return summary

        # If the exact page doesn't exist, use Wikipedia's search to disambiguate
        search_results = wiki.search(query, results=3)
        if not search_results:
            answer = "I couldn't find an answer on Wikipedia for your question."
            cache[cache_key] = answer
            return answer

        # Try the top result
        page = wiki.page(search_results[0])
        if page.exists():
            summary = page.summary.split('\n')[0]
            if len(summary) > 500:
                summary = summary[:500] + "..."
            cache[cache_key] = summary
            return summary

        answer = (f"Your query '{query}' is ambiguous. Did you mean: "
                  f"{', '.join(search_results[:3])}? Please be more specific.")
        cache[cache_key] = answer
        return answer
    except Exception as e:
        answer = f"Error fetching answer from Wikipedia: {str(e)}"
        cache[cache_key] = answer
        return answer

# Fetch the latest news updates (reverted to general news)
async def fetch_latest_news():
    cache_key = "news_general"
    if cache_key in cache:
        return cache[cache_key]

    try:
        # Fetch top headlines (general English news, limited to 5 for brevity)
        top_headlines = newsapi.get_top_headlines(language='en', page_size=5)
        articles = top_headlines.get('articles', [])

        if not articles:
            return "I couldn't fetch the latest news right now. Try again later."

        # Format the news as a numbered list
        news_list = [f"{i+1}. {article['title']} ({article['source']['name']})"
                     for i, article in enumerate(articles)]
        answer = "Here are the latest news updates:\n" + "\n".join(news_list)
        cache[cache_key] = answer
        return answer
    except Exception as e:
        # Fallback: Scrape Al Jazeera's main page
        try:
            url = "https://www.aljazeera.com"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            html = await fetch_url(url, headers=headers)
            soup = BeautifulSoup(html, "html.parser")

            # Find news headlines (based on Al Jazeera's structure as of May 2025)
            headlines = soup.find_all("h3", class_="gc__title", limit=5)
            if not headlines:
                answer = "I couldn't fetch the latest news right now. Try again later."
                cache[cache_key] = answer
                return answer

            news_list = [f"{i+1}. {headline.get_text().strip()} (Al Jazeera)"
                         for i, headline in enumerate(headlines)]
            answer = "Here are the latest news updates:\n" + "\n".join(news_list)
            cache[cache_key] = answer
            return answer
        except Exception as e:
            answer = f"Error fetching latest news: {str(e)}"
            cache[cache_key] = answer
            return answer

# Taking a screenshot
def take_screenshot():
    path = "screenshots"
    os.makedirs(path, exist_ok=True)
    filename = f"{path}/screenshot_{int(time.time())}.png"
    image = pyautogui.screenshot()
    image.save(filename)
    return f"Screenshot saved as {filename}"

# Taking a note
def take_note():
    path = "notes"
    os.makedirs(path, exist_ok=True)
    filename = f"{path}/note_{int(time.time())}.txt"
    with open(filename, "w") as f:
        f.write("This is a note created by Nova assistant.")
    return f"Note saved as {filename}"

# Playing music on YouTube
def play_music():
    webbrowser.open("https://music.youtube.com")
    return "Playing music on YouTube."

# Telling a joke
def tell_joke():
    return pyjokes.get_joke()

# Sentiment analysis
def analyze_sentiment(text):
    analysis = TextBlob(text)
    sentiment = "positive" if analysis.sentiment.polarity > 0 else "negative"
    return f"The sentiment of your message is {sentiment}."

# Translating text
translator = Translator()
def translate_text(text, lang="es"):
    translated = translator.translate(text, dest=lang)
    return translated.text

# Motivational quotes
def get_motivation():
    quotes = [
        "Believe you can and you're halfway there.",
        "Act as if what you do makes a difference. It does.",
        "Success is not final, failure is not fatal: It is the courage to continue that counts."
    ]
    return random.choice(quotes)

# Reminders
reminders = []
def set_reminder(reminder):
    reminders.append(reminder)
    return f"Reminder set: {reminder}"

def get_reminders():
    return "\n".join(reminders) if reminders else "No reminders set."

# Quiz handling
def handle_quiz(prompt, session_id, user_name):
    prompt = prompt.strip().upper()
    if session_id not in quiz_sessions:
        if prompt.lower() in ["start a quiz", "play a quiz"]:
            # Randomly select 5 questions
            selected_questions = random.sample(quiz_questions, 5)
            quiz_sessions[session_id] = {
                "questions": selected_questions,
                "current_question": 0,
                "score": 0,
                "answers": []
            }
            question = selected_questions[0]
            return {
                "type": "quiz_question",
                "question": question["question"],
                "options": question["options"],
                "message": f"Hello {user_name}, let's start the tech quiz! Here's the first question:"
            }
        return None
    else:
        session = quiz_sessions[session_id]
        current = session["current_question"]
        if prompt.lower() in ["stop quiz", "end quiz"]:
            score = session["score"]
            del quiz_sessions[session_id]
            return {"type": "text", "message": f"Quiz ended, {user_name}. You scored {score}/5!"}
        if current < 5:
            if prompt not in ["A", "B", "C"]:
                return {"type": "text", "message": f"Please select A, B, or C, {user_name}. You can click a button or type your answer."}
            correct_answer = session["questions"][current]["answer"]
            correct_text = session["questions"][current]["correct"]
            session["answers"].append(prompt)
            is_correct = prompt == correct_answer
            if is_correct:
                session["score"] += 1
                response = f"Correct, {user_name}! The answer is {correct_text}."
            else:
                response = f"Sorry, {user_name}, that's incorrect. The correct answer is {correct_text}."
            session["current_question"] += 1
            if current + 1 < 5:
                next_question = session["questions"][current + 1]
                return {
                    "type": "quiz_question",
                    "question": next_question["question"],
                    "options": next_question["options"],
                    "message": response + "\nNext question:",
                    "correct": is_correct
                }
            else:
                score = session["score"]
                del quiz_sessions[session_id]
                return {
                    "type": "text",
                    "message": response + f"\nQuiz finished, {user_name}! You scored {score}/5.",
                    "correct": is_correct
                }
        else:
            score = session["score"]
            del quiz_sessions[session_id]
            return {"type": "text", "message": f"Quiz already finished, {user_name}. You scored {score}/5!"}
    return None

# ============ MAIN PROMPT HANDLER ============

def answer_prompt(prompt, user_name="User", session_id="default"):
    # Check for exit command first
    if prompt.lower().strip() == "exit":
        return {"type": "exit", "message": f"Goodbye, {user_name}! Thanks for chatting with me. See you soon!"}

    # Manual Q&A first
    if prompt.lower() in manual_qa:
        return {"type": "text", "message": f"{user_name}, {manual_qa[prompt.lower()]}"}

    # Check for Wikipedia search
    if "wikipedia" in prompt.lower():
        wiki_answer = asyncio.run(fetch_wikipedia_answer(prompt))
        return {"type": "text", "message": f"{user_name}, {wiki_answer} (Source: Wikipedia)"}

    # Check for latest news
    if "latest news" in prompt.lower() or "news update" in prompt.lower():
        news = asyncio.run(fetch_latest_news())
        return {"type": "text", "message": f"{user_name}, {news}"}

    # Check for Google redirect (before other features to catch "google" keyword)
    if "google" in prompt.lower():
        redirect_message = redirect_to_google_search(prompt)
        return {"type": "text", "message": f"{user_name}, {redirect_message}"}

    # Quiz handling
    quiz_response = handle_quiz(prompt, session_id, user_name)
    if quiz_response:
        return quiz_response

    # Custom features
    if "time" in prompt.lower() or "date" in prompt.lower():
        return {"type": "text", "message": f"{user_name}, {get_time_date()}"}
    elif "weather" in prompt.lower():
        return {"type": "text", "message": f"{user_name}, {get_weather()}"}
    elif "screenshot" in prompt.lower():
        return {"type": "text", "message": f"{user_name}, {take_screenshot()}"}
    elif "note" in prompt.lower():
        return {"type": "text", "message": f"{user_name}, {take_note()}"}
    elif "play music" in prompt.lower():
        return {"type": "text", "message": f"{user_name}, {play_music()}"}
    elif "joke" in prompt.lower():
        return {"type": "text", "message": f"{user_name}, {tell_joke()}"}
    elif "sentiment" in prompt.lower():
        text = prompt.lower().split("sentiment")[-1].strip()
        return {"type": "text", "message": f"{user_name}, {analyze_sentiment(text)}"}
    elif "translate" in prompt.lower():
        text = prompt.lower().split("translate")[-1].strip()
        return {"type": "text", "message": f"{user_name}, Translated: {translate_text(text)}"}
    elif "motivate" in prompt.lower():
        return {"type": "text", "message": f"{user_name}, {get_motivation()}"}
    elif "reminder" in prompt.lower():
        reminder = prompt.lower().split("reminder")[-1].strip()
        return {"type": "text", "message": f"{user_name}, {set_reminder(reminder)}"}
    elif "reminders" in prompt.lower():
        return {"type": "text", "message": f"{user_name}, {get_reminders()}"}
    elif "open" in prompt.lower():
        website = prompt.lower().split("open")[-1].strip()
        url = f"https://{website}" if "." in website else f"https://www.{website}.com"
        webbrowser.open(url)
        return {"type": "text", "message": f"{user_name}, Opening {url}"}
    else:
        # Fallback to Google search
        google_answer = asyncio.run(google_search_answer(prompt))
        return {"type": "text", "message": f"{user_name}, {google_answer}"}

# ============ ROUTES ============

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    prompt = data.get("prompt", "")
    user_name = data.get("user_name", "User")
    session_id = data.get("session_id", "default")
    response = answer_prompt(prompt, user_name, session_id)
    log_history(prompt, response.get("message", ""))
    return jsonify(response)

# ============ RUN APP ============

if __name__ == "__main__":
    print("Starting Mini Personal Voice Assistant... Visit http://127.0.0.1:5000")
    app.run(debug=True)