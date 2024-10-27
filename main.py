from dotenv import load_dotenv
import os
from fastapi import FastAPI
import schedule # type: ignore this is already imported
import time
import requests
import gpsd



def get_gps_coordinates():

    # Connect to the local gpsd
    gpsd.connect()

    try:
        # Get gps position
        packet = gpsd.get_current()
        
        if packet.mode >= 2:
            return packet.lat, packet.lon
        else:
            return None
    except Exception as e:
        print(f"Error getting GPS coordinates: {e}")
        return None

# ------------------------------------------------------------------------------------------------

# load_dotenv()

# # Configuration
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# PORT = int(os.getenv('PORT', 5050))
# RECOMMENDATION_SUBJECT = "coffee shops"
# SYSTEM_MESSAGE = (
#     "You are a helpful and bubbly AI assistant who loves to give recommendations "
#     f"that the user will love. The user is typically on the road looking for the best {RECOMMENDATION_SUBJECT}."
#     "Be open for conversations about coffee as well as discussing where my destination is to help with recommendations."
#     "Always stay positive, but work in a joke when appropriate."
# )
# VOICE = 'alloy'
# LOG_EVENT_TYPES = [
#     'error', 'response.content.done', 'rate_limits.updated',
#     'response.done', 'input_audio_buffer.committed',
#     'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
#     'session.created'
# ]
# SHOW_TIMING_MATH = False

# # The idea is to have the timer hit the Google API to 

def job():
    print("This job runs every 5 minutes")

# For testing purposes, we sleep for 30 seconds between each run of the recommender
schedule.every(1).minutes.do(job)

# while True:
#        schedule.run_pending()
#        time.sleep(1) 

if __name__ == "__main__":
    # Main loop
    while True:
        coordinates = get_gps_coordinates()
        if coordinates:
            lat, lon = coordinates
            print(f"Latitude: {lat}, Longitude: {lon}")
    else:
        print("Waiting for GPS fix...")
        
    time.sleep(1)   