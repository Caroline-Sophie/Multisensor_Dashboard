import streamlit as st
import datetime
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import time
from src import sensor_data as sd
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import datetime, timedelta


class Dashboard:
    def __init__(self):
        # Create sensor_data instance that holds a dictionary with all sensors for each room
        self.sensor_data = sd.Sensor_Data()
        self.data = self.sensor_data.data  # dictionary with all sensors for each room, current and historic data for each sensor

        # Initialize rooms and sensors
        self.rooms = [
            "Conference-Space", "Robot-Space",
            "Empfang", "Focus-Space",
            "Experience-Hub", "Design-Thinking-Space",
            "Co-Working-Space", "Social Lounge"
        ]

        self.sensors = []  # list of all available sensors extracted from self.data
        for room, sensors in self.data.items():
            for sensor in sensors.keys():
                if sensor not in self.sensors:
                    self.sensors.append(sensor)

        self.room_plan_image_path = Path("media/ZEKI-Floorplan-1536x640.png")  # image of the 3d room plan

        # Coordinates for each room on the image
        self.room_coordinates = {
            "multisensor_115": (110, 140),
            "multisensor_108": (250, 180),
            "multisensor_107": (400, 140),
            "multisensor_114": (590, 180),
            "multisensor_110": (730, 140),
            "multisensor_112": (350, 250),
            "multisensor_105": (900, 300),
            "multisensor_109": (950, 180),
            "multisensor_104": (1250, 300),
            "multisensor_106": (1000, 420),
            "multisensor_111": (500, 420),
            "multisensor_113": (100, 350)
        }

        self.run()

    def calculate_sensor_fusion(self, sensor_data):
        """
        Calculate the estimated number of people in the room using Sensor Fusion.
        """
        # Constants for fusion calculation
        room_volume = 50  # m³
        baseline_co2 = 400  # ppm
        co2_production_rate = 18  # L/h/person
        time_elapsed = 1  # hour

        baseline_noise = 40  # dB (empty room)
        noise_scaling_factor = 1.5

        baseline_temp = 22  # °C
        baseline_humidity = 40  # %
        temp_factor = 0.5
        humidity_factor = 1.0

        # Sensor values
        co2_values = sensor_data.get("co2", [])
        noise_levels = sensor_data.get("noise", [])
        temperatures = sensor_data.get("temperature", [])
        humidities = sensor_data.get("humidity", [])

        # Calculate CO2-based estimate
        if co2_values:
            avg_co2 = np.mean(co2_values)
            co2_diff = avg_co2 - baseline_co2
            co2_people = (co2_diff * room_volume) / (co2_production_rate * time_elapsed)
        else:
            co2_people = 0

        # Calculate Noise-based estimate
        if noise_levels:
            avg_noise = np.mean(noise_levels)
            noise_people = noise_scaling_factor * (avg_noise / baseline_noise)
        else:
            noise_people = 0

        # Calculate Temp & Humidity-based estimate
        if temperatures and humidities:
            avg_temp = np.mean(temperatures)
            avg_humidity = np.mean(humidities)
            temp_diff = avg_temp - baseline_temp
            humidity_diff = avg_humidity - baseline_humidity
            temp_humidity_people = (temp_diff * temp_factor) + (humidity_diff * humidity_factor)
        else:
            temp_humidity_people = 0

        # Sensor Fusion (weighted average)
        weights = [0.4, 0.3, 0.3]  # CO2, Noise, Temp+Humidity
        final_people_count = (weights[0] * co2_people +
                              weights[1] * noise_people +
                              weights[2] * temp_humidity_people)

        return max(0, final_people_count)  # Ensure non-negative count

    def show_current_data(self, selected_sensor):
        """Overlay sensor values on the room plan image."""
        if self.room_plan_image_path.exists():
            # Open the room plan and add a white background for transparency
            image = Image.open(self.room_plan_image_path).convert("RGBA")
            white_bg = Image.new("RGBA", image.size, "WHITE")  # Create white background
            image = Image.alpha_composite(white_bg, image).convert("RGB")

            # Draw on image with the font
            draw = ImageDraw.Draw(image)
            try:
                # Load a custom font, if available, or default to system font
                font = ImageFont.truetype("Arial.ttf", 25)  # Adjust font size if needed
            except IOError:
                font = ImageFont.load_default()

            # Draw each room's sensor value and estimated people count at its coordinates
            for sensor_id, coords in self.room_coordinates.items():
                sensors = self.data.get(sensor_id, {}).get("sensors", {})

                # Collect sensor data for fusion
                sensor_data = {
                    "co2": [sensors[s]["current_value"] for s in sensors if "co2" in s],
                    "noise": [sensors[s]["current_value"] for s in sensors if "noise" in s],
                    "temperature": [sensors[s]["current_value"] for s in sensors if "temperature" in s],
                    "humidity": [sensors[s]["current_value"] for s in sensors if "humidity" in s],
                }

                # Estimate people count using Sensor Fusion
                people_count = self.calculate_sensor_fusion(sensor_data)

                # Format the text if the values exist
                sensor_value = sensors[selected_sensor]["current_value"] if selected_sensor in sensors else None
                sensor_unit = sensors[selected_sensor]["unit"] if selected_sensor in sensors else None

                if sensor_value and sensor_unit:
                    text = f"{sensor_value:.1f} {sensor_unit}\nPeople: {people_count:.1f}"
                else:
                    text = f"People: {people_count:.1f}"  # If either value doesn't exist, show only people count

                # Get bounding box of the text
                text_bbox = draw.textbbox((coords[0], coords[1]), text, font=font)

                # Calculate padding for the rectangle
                padding = 10
                rect_bbox = [
                    text_bbox[0] - padding,  # Left
                    text_bbox[1] - padding,  # Top
                    text_bbox[2] + padding,  # Right
                    text_bbox[3] + padding  # Bottom
                ]

                # Draw a white rectangle behind the text
                draw.rectangle(rect_bbox, fill="white")

                # Draw the text in black
                draw.text((coords[0], coords[1]), text, font=font, fill="black")
            return image
        else:
            st.warning("Room plan image not found!")
            return None

    def display_room_graph(self, room, sensor=None):
        """Display time-series data graph and prognosis for a specific room and sensor."""
        if room not in [sensor_data["room"] for sensor_data in self.data.values()]:
            st.error(f"Room '{room}' not found in the data.")
            return

        # Initialize the plots
        fig, axes = plt.subplots(2, 1, figsize=(10, 12), sharex=True)
        fig.suptitle(f"Sensor Data for {room}")

        for sensor_id, sensor_data in self.data.items():
            if sensor_data["room"] == room:
                sensors = sensor_data["sensors"]

                # If a specific sensor is provided
                if sensor:
                    if sensor not in sensors:
                        st.error(f"Sensor '{sensor}' not found in room '{room}'.")
                        return
                    sensors_to_plot = {sensor: sensors[sensor]}
                else:
                    # If no specific sensor is provided, plot all sensors
                    sensors_to_plot = sensors

                for sensor_name, details in sensors_to_plot.items():
                    history = details["history"]

                    # Extract timestamps and values
                    timestamps = [datetime.fromisoformat(entry[1].replace("Z", "")) for entry in history]
                    values = [entry[0] for entry in history]

                    # Plot actual data
                    axes[0].plot(timestamps, values, label=f"{sensor_name} ({details['unit']})")

                    # Prepare data for linear regression
                    if len(timestamps) > 1:
                        time_numbers = np.array([(ts - timestamps[0]).total_seconds() for ts in timestamps]).reshape(-1, 1)
                        values_array = np.array(values).reshape(-1, 1)

                        # Perform linear regression
                        model = LinearRegression()
                        model.fit(time_numbers, values_array)

                        # Generate predictions for the rest of the day
                        future_times = [
                            timestamps[-1] + timedelta(minutes=15 * i) for i in range(1, 17)
                        ]  # Predict for the next 4 hours (15 min intervals)
                        future_time_numbers = np.array(
                            [(ft - timestamps[0]).total_seconds() for ft in future_times]
                        ).reshape(-1, 1)
                        predictions = model.predict(future_time_numbers).flatten()

                        # Plot the prognosis
                        axes[1].plot(
                            future_times, predictions, label=f"Prognosis: {sensor_name} ({details['unit']})",
                            linestyle="--"
                        )

        # Configure the first graph (historical data)
        axes[0].set_title("Historical Data")
        axes[0].set_ylabel("Sensor Values")
        axes[0].set_xlabel("Timestamp")
        axes[0].legend()
        axes[0].grid(True)

        # Configure the second graph (prognosis)
        axes[1].set_title("Prognosis for the Rest of the Day")
        axes[1].set_xlabel("Timestamp")
        axes[1].set_ylabel("Sensor Values")
        axes[1].legend()
        axes[1].grid(True)

        # Display the plots in Streamlit
        st.pyplot(fig)

    def run(self):
        """Run the Streamlit dashboard."""
        # Page title
        st.title("Multisensor Dashboard")

        # Create the sidebar - returns Sidebar selection
        self.display_sidebar()

        # create a heading on main page
        st.header("ZEKI Sensors - Overview")

        # Main page with room plan and sensor toggle
        selected_sensor = st.selectbox("Select Sensor", self.sensor_data.multisensor_sensors.keys(), index=0, key="overview_sensor_select")

        # Display the room plan image with overlaid sensor values
        image_with_overlay = self.show_current_data(selected_sensor)
        if image_with_overlay:
            st.image(image_with_overlay, caption="Room Plan with Current Temperature", use_column_width=True)

        # heading for explicit data
        st.header(f"Have a closer look")

        # get explicit room and sensor
        room = st.selectbox("Select Room", {sensor_data["room"] for sensor_data in self.data.values()}, key="explicit_room_select")
        sensor = st.selectbox("Select Sensor", self.sensor_data.multisensor_sensors.keys(), index=0, key="explicit_sensor_select")
        # Display detailed graph for the selected room and sensor
        self.display_room_graph(room, sensor)

        # update self.data with the current sensor data periodically
        while True:
            self.sensor_data.update()
            self.data = self.sensor_data.data

            time.sleep(20)
            st.rerun()  # Trigger a rerun to refresh data in Streamlit

    def display_sidebar(self):
        """Display sidebar with room selection and warnings."""
        st.sidebar.title("Your Location")
        selected_room = st.sidebar.selectbox("Select Room", {sensor_data["room"] for sensor_data in self.data.values()} , key="current_room_select")

        # Display current sensor values and warnings for the selected room
        st.sidebar.header("Warnings for this room")

        # Show warnings for the selected room
        for sensor_id, sensor_data in self.data.items():
            # Check if the room matches the selected room
            if sensor_data["room"] == selected_room:
                for sensor_name, details in sensor_data["sensors"].items():
                    for warning in details["warnings"]:  # Iterate through warnings
                        st.sidebar.warning(f"{sensor_name}: {warning}")

        st.sidebar.header("Current Sensor Values")

        # Show current sensor values for the selected room
        for sensor_id, sensor_data in self.data.items():
            # Check if the room matches the selected room
            if sensor_data["room"] == selected_room:
                for sensor_name, details in sensor_data["sensors"].items():
                    current_value = details["current_value"]
                    unit = details["unit"]
                    if current_value is not None:
                        st.sidebar.metric(sensor_name, f"{current_value:.1f} {unit}")


# Run the dashboard
if __name__ == "__main__":
    dashboard = Dashboard()
