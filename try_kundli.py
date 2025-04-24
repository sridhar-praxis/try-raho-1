import streamlit as st
import swisseph as swe
import numpy as np
import pandas as pd
from datetime import datetime
import pytz
from geopy.geocoders import Nominatim
import requests

# Cache the geocoding function
@st.cache_data(show_spinner=False)
def get_location(city, country):
    geolocator = Nominatim(user_agent="kundli-streamlit")
    location = geolocator.geocode(f"{city}, {country}")
    if not location:
        # Fallback to Geoapify if Nominatim fails
        geoapify_api_key = "YOUR_GEOAPIFY_API_KEY"  # Get it from https://www.geoapify.com/
        geoapify_url = f"https://api.geoapify.com/v1/geocode/search?text={city},{country}&apiKey={geoapify_api_key}"
        response = requests.get(geoapify_url).json()
        if response.get('features'):
            location = response['features'][0]['geometry']['coordinates']
        else:
            return None
    return location

def get_planet_positions(query_datetime, city, country):
    # Convert local to UTC
    local = pytz.timezone('Asia/Kolkata')
    local_dt = local.localize(query_datetime)
    utc_dt = local_dt.astimezone(pytz.utc)

    yr, mnth, dte = utc_dt.year, utc_dt.month, utc_dt.day
    hr, minut, secnd = utc_dt.hour, utc_dt.minute, utc_dt.second

    jd = swe.utc_to_jd(yr, mnth, dte, hr, minut, secnd)

    # Get lat-long
    loc = get_location(city, country)
    if not loc:
        st.error(f"Could not find location for {city}, {country}")
        return pd.DataFrame()

    lat, lon = loc[1], loc[0]  # Geoapify returns coordinates as [longitude, latitude]

    # Sidereal and ayanamsa
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    delta = 0.88
    ayan = swe.get_ayanamsa_ut(jd[1])
    hous = swe.houses(jd[1], lat, lon, b'P')
    apos = hous[0][0] - ayan + delta
    if apos < 0:
        apos += 360

    Q = int(apos / 30)
    D = int(apos % 30)
    M = int((apos % 1) * 60)

    graha = ['Lagna']
    graha_pos = [apos]
    formatted_graha_pos = [f'{Q}s {D}d {M}m']

    for i in np.arange(13):
        graham = swe.get_planet_name(i)
        pos, err = swe.calc(jd[1], i)
        pos = pos[0] - ayan + delta
        if pos < 0:
            pos += 360

        Q = int(pos / 30)
        D = int(pos % 30)
        M = int((pos % 1) * 60)

        if graham == 'true Node':
            graha.append('Ketu')
            ketu_pos = (pos + 180) % 360
            Q_ketu = int(ketu_pos / 30)
            D_ketu = int(ketu_pos % 30)
            M_ketu = int((ketu_pos % 1) * 60)
            graha_pos.append(ketu_pos)
            formatted_graha_pos.append(f'{Q_ketu}s {D_ketu}d {M_ketu}m')

            graham = 'Rahu'

        graha.append(graham)
        graha_pos.append(pos)
        formatted_graha_pos.append(f'{Q}s {D}d {M}m')

    return pd.DataFrame({
        "graham": graha,
        "Longitude": graha_pos,
        "FormattedLong": formatted_graha_pos
    })


# Streamlit UI
st.title("🪐 Jyotish D1 Chart Generator")

# Default values
now = datetime.now()
default_date = now.date()
default_time = now.strftime("%H:%M:%S")

st.subheader("📅 Enter Birth Details")
birth_date = st.date_input("Date of Birth", value=default_date)
birth_time = st.text_input("Time of Birth (HH:MM:SS)", value=default_time)
city = st.text_input("City of Birth", value="Bangalore")
country = st.text_input("Country of Birth", value="India")

if st.button("Generate Kundli"):
    try:
        dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M:%S")
        df_chart = get_planet_positions(dt, city, country)
        if not df_chart.empty:
            st.success("Kundli generated successfully!")
            st.dataframe(df_chart)
    except Exception as e:
        st.error(f"An error occurred: {e}")
