import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from openai import OpenAI
from datetime import datetime
from streamlit_geolocation import streamlit_geolocation

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Weather Agent", page_icon="⛅", layout="wide")

# Language Toggle
lang_choice = st.radio("Language / மொழி", ["English", "தமிழ்"], horizontal=True)
is_ta = lang_choice == "தமிழ்"
lang_code = "ta" if is_ta else "en"

# Translation Dictionary for UI Elements
ui = {
    "title": "⛅ ஊடாடும் AI வானிலை முகவர்" if is_ta else "⛅ Interactive AI Weather Agent",
    "loc_prompt": "📍 உங்கள் தற்போதைய இருப்பிடத்தை முகவருக்குத் தெரிவிக்க கீழே கிளிக் செய்யவும்." if is_ta else "📍 Click below to let the agent know your current location.",
    "loc_success": "இருப்பிடம் பெறப்பட்டது" if is_ta else "Location acquired",
    "ask": "ஒரு நகரத்தின் வானிலை பற்றி கேளுங்கள்:" if is_ta else "Ask about a city's weather:",
    "placeholder": "உதாரணமாக, சென்னையில் வானிலை எப்படி இருக்கிறது?" if is_ta else "e.g., How is the weather in Chennai?",
    "analyzing": "பகுப்பாய்வு செய்கிறது..." if is_ta else "Analyzing...",
    "weather_for": "இதற்கான வானிலை:" if is_ta else "Weather for",
    "forecast_title": "3 நாள் முன்னறிவிப்பு" if is_ta else "3-Day Forecast",
    "today": "இன்று" if is_ta else "Today",
    "trend_title": "மணிநேர வெப்பநிலை போக்கு" if is_ta else "Hourly Temperature Trend",
    "error": "தரவைப் பெற முடியவில்லை:" if is_ta else "Could not retrieve live data for:"
}

def get_weather_data(city, lang):
    try:
        url = f"https://wttr.in/{city}?format=j1&lang={lang}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None
    return None

def get_weather_emoji(condition):
    condition = condition.lower()
    if "thunder" in condition or "storm" in condition or "இடி" in condition: return "⛈️"
    elif "snow" in condition or "ice" in condition or "பனி" in condition: return "❄️"
    elif "heavy rain" in condition or "torrential" in condition or "கனமழை" in condition: return "🌧️"
    elif "rain" in condition or "drizzle" in condition or "shower" in condition or "மழை" in condition: return "🌦️"
    elif "cloud" in condition or "overcast" in condition or "மேகம்" in condition: return "☁️" if "overcast" in condition else "⛅"
    elif "clear" in condition or "sunny" in condition or "தெளிவான" in condition or "வெயில்" in condition: return "☀️"
    elif "fog" in condition or "mist" in condition or "மூடுபனி" in condition: return "🌫️"
    else: return "🌡️"

st.title(ui["title"])

st.write(ui["loc_prompt"])
location = streamlit_geolocation()

if location and location.get('latitude'):
    st.success(f"{ui['loc_success']}: {location['latitude']}, {location['longitude']}")

user_query = st.text_input(ui["ask"], placeholder=ui["placeholder"])

active_query = None

if user_query:
    active_query = user_query
elif location and location.get('latitude'):
    if st.session_state.get('last_location') != location:
        st.session_state['last_location'] = location
        active_query = f"Get the weather for coordinates: {location['latitude']},{location['longitude']}"

if active_query:
    with st.spinner(ui["analyzing"]):
        system_prompt = """
        You are a Data Extraction Agent. 
        Extract the city name or the GPS coordinates from the user's message.
        You MUST output EXACTLY and ONLY this format: ACTION: get_weather, CITY: [Extracted Location]
        Do not include any conversational text.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": active_query}]
        )
        
        ai_thought = response.choices[0].message.content
        
        if "ACTION: get_weather" in ai_thought:
            city = ai_thought.split("CITY: ")[1].strip()
            data = get_weather_data(city, lang_code)
            
            if data:
                # Extract actual area name to replace raw coordinates
                try:
                    area_name = data['nearest_area'][0]['areaName'][0]['value']
                    region = data['nearest_area'][0]['region'][0]['value']
                    display_name = f"{area_name}, {region}" if region else area_name
                except:
                    display_name = city.capitalize()

                current = data['current_condition'][0]
                weather_days = data['weather']
                
                # Fetch translated condition if Tamil is selected and available
                if is_ta and 'lang_ta' in current:
                    condition_text = current['lang_ta'][0]['value']
                else:
                    condition_text = current['weatherDesc'][0]['value']
                    
                current_emoji = get_weather_emoji(current['weatherDesc'][0]['value'])
                
                st.markdown(f"""
                <div style="background-color: #f0f4f8; padding: 20px; border-radius: 15px; margin-bottom: 20px;">
                    <h3 style="margin:0; color: #333;">{ui['weather_for']} {display_name}</h3>
                    <h1 style="margin:0; font-size: 4rem; color: #111;">{current_emoji} {current['temp_C']}°C <span style="font-size: 1.5rem; font-weight: normal; color: #555;">{condition_text}</span></h1>
                    <p style="margin:0; color: #666;">H {weather_days[0]['maxtempC']}° L {weather_days[0]['mintempC']}°</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.subheader(ui["forecast_title"])
                cols = st.columns(3)
                for i, day in enumerate(weather_days):
                    with cols[i]:
                        date_obj = datetime.strptime(day['date'], "%Y-%m-%d")
                        day_name = ui["today"] if i == 0 else date_obj.strftime("%a %d")
                        noon_condition = day['hourly'][4]['weatherDesc'][0]['value'] 
                        day_emoji = get_weather_emoji(noon_condition)
                        
                        st.markdown(f"""
                        <div style="text-align: center; padding: 10px; background-color: {'#e1f0fa' if i==0 else 'transparent'}; border-radius: 10px;">
                            <p style="margin: 0; font-weight: bold;">{day_name}</p>
                            <h2 style="margin: 5px 0;">{day_emoji}</h2>
                            <p style="margin: 0;"><b>{day['maxtempC']}°</b> <span style="color: #666;">{day['mintempC']}°</span></p>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.subheader(ui["trend_title"])
                hourly_data = weather_days[0]['hourly']
                
                temps = [int(hour['tempC']) for hour in hourly_data]
                times = [f"{int(hour['time'])//100}:00" if hour['time'] != '0' else "12 AM" for hour in hourly_data]
                chances_of_rain = [f"💧 {hour['chanceofrain']}%" for hour in hourly_data]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=times, y=temps, mode='lines+text', text=[f"{t}°" for t in temps], textposition="top center",
                    fill='tozeroy', line=dict(color='#ff9900', width=3, shape='spline'), fillcolor='rgba(255, 153, 0, 0.2)'
                ))
                fig.update_layout(
                    xaxis=dict(showgrid=False, ticktext=chances_of_rain, tickvals=times), 
                    yaxis=dict(showgrid=False, visible=False, range=[min(temps)-5, max(temps)+5]),
                    margin=dict(l=0, r=0, t=30, b=0), height=300
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"{ui['error']} {city}")
        else:
            st.info(ai_thought)