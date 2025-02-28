import src.influx_db_data as idb
from requests import get
import random
from datetime import datetime, timedelta
import time
import threading
import streamlit as st

class Sensor_Data():
    """
    A class that handles the management of sensor data, including fetching live data,
    updating historic data from InfluxDB, and calculating occupancy estimates.

    Attributes:
        data (dict): A dictionary containing sensor data for all rooms.
        influxDB (InfluxDB): An instance of the InfluxDB class used to fetch historic data.
    """

    def __init__(self):
        """
        Initializes the Sensor_Data object by creating a sensor dictionary and scheduling
        data updates at regular intervals.
        """
        self.data = self.create_sensor_dict()  # Creates a dictionary for all rooms and their multisensors
        self.update()  # Fetches and updates data
        self.schedule_data_updates()  # Schedules periodic data updates

    def update(self):
        """
        Updates the sensor data by fetching live data from Home Assistant and historic data
        from InfluxDB. Also updates occupancy values.
        """
        try:
            self.fetch_live_data()  # Updates self.data with live sensor data from Home Assistant

            # Create an instance of InfluxDB and fetch historic sensor data
            self.influxDB = idb.InfluxDB()
            self.influxDB.get_historic_sensor_data(self.data)  # Updates self.data with historic data from InfluxDB

            # Update occupancy for each room
            self.update_occupancy()

        except Exception as e:
            print(f"Error while updating the dictionary: {e}. Generating sample data for testing")
            #TODO: remove when done with testing
            populate_sensor_data(self.data)  # Populates sample data for testing purposes

    def schedule_data_updates(self):
        """
        Schedules updates to the sensor data asynchronously by running the update
        function in a separate thread every 60 seconds.
        """
        def update_data():
            while True:
                self.update()  # Fetch and update the data
                time.sleep(60)  # Wait for 1 minute before the next update

        # Run the update loop in a separate thread to ensure continuous data updates
        threading.Thread(target=update_data, daemon=True).start()

    def calculate_occupancy(self, room_id, baseline_co2=550, emission_rate=18, time_elapsed=3600):
        """
        Estimates the number of people in a room based on the CO₂ concentration.

        Parameters:
            baseline_co2 (float): The baseline CO₂ concentration (in ppm) for an empty room (default ~550 ppm).
            emission_rate (float): The CO₂ emission rate per person (in L/hour) (default ~18).
            time_elapsed (float): The time elapsed since measurement (in seconds, default 3600 seconds).

        Returns:
            float: Estimated number of people in the room based on CO₂ levels.
        """
        current_co2 = float(self.data[room_id]["sensors"]["CO2"]["current_value"])  # Current CO₂ concentration in ppm
        room_volume = int(self.data[room_id]["volume"])  # Volume of the room in cubic meters

        if current_co2:
            # Calculate CO₂ difference and how much CO₂ was produced in the room
            co2_diff = current_co2 - baseline_co2  # ppm
            co2_produced = co2_diff * room_volume / 1000  # Convert ppm to liters of CO₂

            # Calculate the estimated number of people in the room
            people_count = co2_produced / (emission_rate * (time_elapsed / 3600))  # Convert time to hours
            return max(0, round(people_count))  # Ensure non-negative count
        else:
            return 0  # Return 0 if no valid CO2 data

    def update_occupancy(self):
        """
        Updates the occupancy data for each room based on the current CO₂ concentration.
        """
        for room_id, sensor_info in self.data.items():
            # Check if 'Occupancy' exists in the sensors dictionary for the room
            if "Occupancy" in sensor_info["sensors"]:
                # Update the current occupancy value based on CO₂ calculations
                sensor_info["sensors"]["Occupancy"]["current_value"] = self.calculate_occupancy(room_id)

    def fetch_live_data(self):
        """
        Fetches live data from the Home Assistant API and updates the sensor data in the system.
        """
        multisensor_sensors_home_assistant = {
            "Detection Distance": {"id": "_ld2410_detection_distance", "unit": "cm"},
            "TOF Distance": {"id": "_tof_distance", "unit": "m"},
            "Humidity": {"id": "_bme680_humidity", "unit": "%"},
            "Temperature": {"id": "_bme680_temperature", "unit": "°C"},
            "CO2": {"id": "_scd30_co2", "unit": "ppm"},
            "IAQ": {"id": "_bme680_iaq", "unit": "IAQ"},
            "UV Index": {"id": "_ltr390_uv_index", "unit": "UVI"},
            "Microphone Voltage": {"id": "_microphone_voltage", "unit": "V"},
            "Microphone Noise Level": {"id": "_microphone_noise_level", "unit": "Volume"},
            "Pressure": {"id": "_bme680_pressure", "unit": "hPa"},
            "Light": {"id": "_ltr390_light", "unit": "lx"},
            "Gas Resistance": {"id": "_bme680_gas_resistance", "unit": "Ω"}
        }

        # Access API secrets
        url_zeki = st.secrets["api"]["url_zeki"]
        headers_zeki = {
            "Authorization": st.secrets["api"]["token"],
            "content-type": st.secrets["api"]["content_type"],
        }


        def update_sensor_value(sensors_data, target_sensor_id, target_id, new_value):
            """
            Updates the current value for a sensor in the sensors dictionary.

            Args:
                sensors_data (dict): The sensors data dictionary.
                target_sensor_id (str): The sensor ID to update.
                target_id (str): The sensor attribute ID to match.
                new_value: The new value to set for the sensor.
            """
            if target_sensor_id in sensors_data:
                sensors = sensors_data[target_sensor_id]["sensors"]
                for sensor_name, sensor_details in sensors.items():
                    if target_id in sensor_details["id"]:
                        sensor_details["current_value"] = new_value
                        return

        response = get(url_zeki, headers=headers_zeki)
        if response.ok:
            all_states = response.json()

            valid_suffixes = [details["id"] for details in multisensor_sensors_home_assistant.values()]
            multisensor_entities = [
                entity for entity in all_states
                if entity['entity_id'].startswith("sensor.multisensor_") and
                   any(entity['entity_id'].endswith(suffix) for suffix in valid_suffixes)
            ]

            # Update self.data with the latest live sensor values
            for entity in multisensor_entities:
                entity_id = entity["entity_id"]
                entity_state = entity["state"]

                # Parse entity_id to get sensor_id and sensor_type
                parts = entity_id.split("_")
                sensor_id = "_".join(parts[0].split(".")[1:] + parts[1:2])  # e.g., multisensor_110
                sensor_type_id = "_" + "_".join(parts[3:])  # e.g., _microphone_noise_level

                update_sensor_value(self.data, sensor_id, sensor_type_id, entity_state)

    def create_sensor_dict(self):
        """
        Initializes and creates a dictionary structure that maps sensors to rooms, including the sensor data,
        their current values, history, and warnings. It also associates each room with its respective volume.

        This dictionary is structured as follows:
        - Each sensor is mapped to a room.
        - Each sensor has information about its type, unit, current value, history, and warnings.
        - Each room has an associated volume.

        Returns:
            dict: A dictionary containing all the sensor data and room associations.
        """

        # Mapping of sensor IDs to room names
        sensor_room_mapping = {
            "multisensor_115": "Conference-Space",
            "multisensor_108": "zwischen Conference-Space und Robot-Space",
            "multisensor_107": "Robot-Space",
            "multisensor_114": "Empfang",
            "multisensor_110": "zwischen Empfang und Focus-Space",
            "multisensor_109": "Focus-Space",
            "multisensor_104": "Experience-Hub",
            "multisensor_106": "Design-Thinking-Space",
            "multisensor_111": "Co-Working-Space (Left in Picture)",
            "multisensor_103": "Co-Working-Space (Right in Picture)",
            "multisensor_113": "Social Lounge",
            "multisensor_112": "Hallway",
            "multisensor_105": "3D Printing-Space",
        }

        # Mapping of room names to their respective volumes (calculated by room area * height)
        self.room_volume = {
            "Conference-Space": (21.06 * 3.2),
            "zwischen Conference-Space und Robot-Space": (14.04 * 3.2),
            "Robot-Space": (30.03 * 3.2),
            "Empfang": (31.27 * 3.2),
            "zwischen Empfang und Focus-Space": (13.26 * 3.2),
            "Focus-Space": (50.7 * 3.2),
            "Experience-Hub": (88.27 * 3.2),
            "Design-Thinking-Space": (43.86 * 3.2),
            "Co-Working-Space (Left in Picture)": (48 * 3.2),
            "Co-Working-Space (Right in Picture)": (46.35 * 3.2),
            "Social Lounge": (34.74 * 3.2),
            "Hallway": 0,
            "3D Printing-Space": 0,
        }

        # Sensor details including sensor ID and measurement units
        self.multisensor_sensors = {
            "Humidity": {"id": "_humidity", "unit": "%"},
            "Temperature": {"id": "_temperature", "unit": "°C"},
            "CO2": {"id": "_scd30_co2", "unit": "ppm"},
            "IAQ": {"id": "_bme680_iaq", "unit": "IAQ"},
            "UV Index": {"id": "_ltr390_uv_index", "unit": "UVI"},
            "Microphone Noise Level": {"id": "_microphone_noise_level", "unit": "Volume"},
            "Pressure": {"id": "_bme680_pressure", "unit": "hPa"},
            "Light": {"id": "_ltr390_light", "unit": "lx"},
            "Gas Resistance": {"id": "_bme680_gas_resistance", "unit": "Ω"},
            "Occupancy": {"id": "_people", "unit": "People"}
        }

        # Initialize the final data structure to hold all sensor data
        sensors_data = {}

        # Iterate over each sensor and room to populate the data structure
        for sensor_id, room in sensor_room_mapping.items():
            sensors_data[sensor_id] = {
                "room": room,  # Room associated with the sensor
                "sensors": {
                    sensor_name: {  # For each sensor in the multisensor
                        "unit": self.multisensor_sensors[sensor_name]["unit"],  # Unit of the sensor
                        "id": self.multisensor_sensors[sensor_name]["id"],  # Sensor ID
                        "current_value": None,  # Current value (None initially)
                        "history": [],  # History of readings (empty initially)
                        "warnings": []  # Warnings related to the sensor (empty initially)
                    }
                    for sensor_name in self.multisensor_sensors  # Iterate over all available sensor types
                },
                "volume": self.room_volume[room]  # Volume of the room (associated with the room)
            }

        return sensors_data


def populate_sensor_data(data):
    """
    Populate the sensors_data dictionary with random values for the current day.

    The function generates random values for each sensor in the data dictionary for the entire day
    (from 6:00 AM to 6:00 PM) with 30-minute intervals. The generated values depend on the sensor type,
    including temperature, humidity, CO2, pressure, light, UV index, gas resistance, IAQ, microphone noise
    level, and occupancy.

    Parameters:
        data (dict): The dictionary containing sensor data for rooms, which will be populated with random values.

    Returns:
        None: This function updates the 'data' dictionary in place.
    """
    current_time = datetime.utcnow()
    today_date = current_time.strftime('%Y-%m-%d')

    # Generate timestamps for every 30 minutes starting at 6:00 AM
    timestamps = [
        (datetime.strptime(f"{today_date}T06:00:00Z", '%Y-%m-%dT%H:%M:%SZ') +
         timedelta(minutes=30 * i)).strftime('%Y-%m-%dT%H:%M:%SZ')
        for i in range(24)  # 24 timestamps for 12 hours (6:00 AM to 6:00 PM)
    ]

    # Iterate through each sensor and populate with random values
    for sensor_id, sensor_info in data.items():
        for sensor_name, sensor_data in sensor_info["sensors"].items():
            # Generate random data based on the sensor type
            if "Temperature" in sensor_name:
                values = [round(random.uniform(18.0, 26.0), 1) for _ in timestamps]  # Temperature in °C
            elif "Humidity" in sensor_name:
                values = [random.randint(30, 70) for _ in timestamps]  # Humidity in %
            elif "CO2" in sensor_name:
                values = [random.randint(400, 1000) for _ in timestamps]  # CO2 in ppm
            elif "Pressure" in sensor_name:
                values = [round(random.uniform(950.0, 1050.0), 1) for _ in timestamps]  # Pressure in hPa
            elif "Light" in sensor_name:
                values = [random.randint(100, 1000) for _ in timestamps]  # Light in lx
            elif "UV Index" in sensor_name:
                values = [round(random.uniform(0.0, 10.0), 1) for _ in timestamps]  # UV Index
            elif "Gas Resistance" in sensor_name:
                values = [random.randint(100, 10000) for _ in timestamps]  # Gas Resistance in Ω
            elif "IAQ" in sensor_name:
                values = [random.randint(0, 500) for _ in timestamps]  # IAQ (Indoor Air Quality) index
            elif "Microphone Noise Level" in sensor_name:
                values = [round(random.uniform(20.0, 80.0), 1) for _ in timestamps]  # Noise level in Volume
            elif "Occupancy" in sensor_name:
                values = [random.randint(0, 10) for _ in timestamps]  # Number of people in the room
            else:
                values = [None for _ in timestamps]  # Default case if sensor type doesn't match

            # Update current value with the most recent timestamp
            sensor_data["current_value"] = values[-1]

            # Generate history with (value, timestamp) pairs
            sensor_data["history"] = list(zip(values, timestamps))

