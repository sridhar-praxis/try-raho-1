import streamlit as st
import swisseph as swe
import numpy as np
import pandas as pd
from datetime import datetime
import pytz
from geopy.geocoders import Nominatim

# Hardcoded fallback lat/lon for key cities
fallback_locations = {
    "Bangalore, India": (12.9716, 77.5946),
    "Chennai, India": (13.0827, 80.2707),
    "Delhi, India": (28.6139, 77.2090),
    "Mumbai, India": (19.0760, 72.8777),
    "Kolkata, India": (22.5726, 88.3639),
}

@st.cache_data(show_spinner=False)
def get_coordinates(city, country):
    key = f"{city.strip()}, {country.strip()}"
    try:
        geolocator = Nominatim(user_agent="kundli-streamlit")
        loc = geolocator.geocode(key, timeout=10)
        if loc:
            return loc.latitude, loc.longitude
        elif key in fallback_locations:
            st.warning(f"Using fallback coordinates for {key}")
            return fallback_locations[key]
        else:
            return None, None
    except Exception as e:
        if key in fallback_locations:
            st.warning(f"Geocoding failed: {e}. Using fallback for {key}")
            return fallback_locations[key]
        else:
            st.error(f"Geolocation failed and no fallback is available: {e}")
            return None, None

def get_planet_positions(query_datetime, city, country):
    utc_dt = query_datetime.astimezone(pytz.utc)

    yr, mnth, dte = utc_dt.year, utc_dt.month, utc_dt.day
    hr, minut, secnd = utc_dt.hour, utc_dt.minute, utc_dt.second
    jd = swe.utc_to_jd(yr, mnth, dte, hr, minut, secnd)

    lat, lon = get_coordinates(city, country)
    if not lat:
        return pd.DataFrame()

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

ist = pytz.timezone("Asia/Kolkata")
now = datetime.now(ist)
default_date = now.date()
default_time = now.strftime("%H:%M:%S")

st.subheader("📅 Enter Birth Details")
birth_date = st.date_input("Date of Birth", value=default_date)
birth_time = st.text_input("Time of Birth (HH:MM:SS)", value=default_time)

st.subheader("📍 Enter Birth Location")
city = st.text_input("City of Birth", value="Bangalore")
country = st.text_input("Country of Birth", value="India")

if st.button("Generate Kundli"):
    try:
        dt_str = f"{birth_date} {birth_time}"
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        dt = pytz.timezone("Asia/Kolkata").localize(dt)
        df_chart = get_planet_positions(dt, city, country)
        if not df_chart.empty:
            st.success("Kundli generated successfully!")
            st.dataframe(df_chart)
    except Exception as e:
        st.error(f"An error occurred: {e}")
