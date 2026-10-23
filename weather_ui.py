import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from openai import OpenAI
from datetime import datetime

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Weather Agent", page_icon="⛅", layout="wide")

def get_weather_data(city):
    try:
        url = f"https://wttr.in/{city}?format=j1"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None
    return None

# Helper function to map text conditions to visual emojis
def get_weather_emoji(condition):
    condition = condition.lower()
    if "thunder" in condition or "storm" in condition:
        return "⛈️"
    elif "snow" in condition or "ice" in condition:
        return "❄️"
    elif "heavy rain" in condition or "torrential" in condition:
        return "🌧️"
    elif "rain" in condition or "drizzle" in condition or "shower" in condition:
        return "🌦️"
    elif "cloud" in condition or "overcast" in condition:
        return "☁️" if "overcast" in condition else "⛅"
    elif "clear" in condition or "sunny" in condition:
        return "☀️"
    elif "fog" in condition or "mist" in condition:
        return "🌫️"
    else:
        return "🌡️"

st.title("⛅ Interactive AI Weather Agent")
user_query = st.text_input("Ask about a city's weather:", placeholder="e.g., How is the weather in Chennai?")

if user_query:
    with st.spinner("Analyzing..."):
        system_prompt = "You are a Weather Agent. If the user asks for weather, output EXACTLY: ACTION: get_weather, CITY: [City Name]"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_query}]
        )
        ai_thought = response.choices[0].message.content
        
        if "ACTION: get_weather" in ai_thought:
            city = ai_thought.split("CITY: ")[1].strip()
            data = get_weather_data(city)
            
            if data:
                current = data['current_condition'][0]
                weather_days = data['weather']
                condition_text = current['weatherDesc'][0]['value']
                current_emoji = get_weather_emoji(condition_text)
                
                # Top Section: Large custom display with dynamic emoji
                st.markdown(f"""
                <div style="background-color: #f0f4f8; padding: 20px; border-radius: 15px; margin-bottom: 20px;">
                    <h3 style="margin:0; color: #333;">{city.capitalize()}</h3>
                    <h1 style="margin:0; font-size: 4rem; color: #111;">{current_emoji} {current['temp_C']}°C <span style="font-size: 1.5rem; font-weight: normal; color: #555;">{condition_text}</span></h1>
                    <p style="margin:0; color: #666;">H {weather_days[0]['maxtempC']}° L {weather_days[0]['mintempC']}°</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Middle Section: Daily Forecast with emojis
                st.subheader("3-Day Forecast")
                cols = st.columns(3)
                for i, day in enumerate(weather_days):
                    with cols[i]:
                        date_obj = datetime.strptime(day['date'], "%Y-%m-%d")
                        day_name = "Today" if i == 0 else date_obj.strftime("%a %d")
                        # We pull the hourly condition for the middle of the day (noon) to represent the daily icon
                        noon_condition = day['hourly'][4]['weatherDesc'][0]['value'] 
                        day_emoji = get_weather_emoji(noon_condition)
                        
                        # Custom markdown to create a Google-like daily card
                        st.markdown(f"""
                        <div style="text-align: center; padding: 10px; background-color: {'#e1f0fa' if i==0 else 'transparent'}; border-radius: 10px;">
                            <p style="margin: 0; font-weight: bold;">{day_name}</p>
                            <h2 style="margin: 5px 0;">{day_emoji}</h2>
                            <p style="margin: 0;"><b>{day['maxtempC']}°</b> <span style="color: #666;">{day['mintempC']}°</span></p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Bottom Section: Hourly Area Chart
                st.subheader("Hourly Temperature Trend")
                hourly_data = weather_days[0]['hourly']
                
                temps = [int(hour['tempC']) for hour in hourly_data]
                times = [f"{int(hour['time'])//100}:00" if hour['time'] != '0' else "12 AM" for hour in hourly_data]
                chances_of_rain = [f"💧 {hour['chanceofrain']}%" for hour in hourly_data]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=times, y=temps, 
                    mode='lines+text',
                    text=[f"{t}°" for t in temps], 
                    textposition="top center",
                    fill='tozeroy', 
                    line=dict(color='#ff9900', width=3, shape='spline'), 
                    fillcolor='rgba(255, 153, 0, 0.2)'
                ))
                
                fig.update_layout(
                    xaxis=dict(showgrid=False, ticktext=chances_of_rain, tickvals=times), 
                    yaxis=dict(showgrid=False, visible=False, range=[min(temps)-5, max(temps)+5]),
                    margin=dict(l=0, r=0, t=30, b=0),
                    height=300
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"Could not retrieve live data for {city}.")
        else:
            st.info(ai_thought)