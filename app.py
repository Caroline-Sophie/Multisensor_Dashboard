import base64
from datetime import datetime, timedelta
import streamlit as st
from pathlib import Path
import time
from streamlit_echarts import st_echarts
import uuid
from streamlit_extras.stylable_container import stylable_container
import numpy as np
import src.sensor_data as sensor_data
from scipy import stats
import csv
import os



class Dashboard:
    """
        A Streamlit-based dashboard for monitoring environmental sensor data.

        This class sets up an interactive dashboard that displays real-time sensor data
        for various rooms. It includes functionality to visualize sensor values, detect
        warnings, and predict future readings.

        Attributes:
            data (dict): A dictionary containing sensor data for different rooms.

        Methods:
            create_interactive_room_buttons(sensor):
                Displays buttons on a background image using a grid corresponding to sensor locations.

            check_for_warnings(sensor, value, unit):
                Evaluates sensor values and returns a warning message if necessary.

            show_current_data(sensor):
                Displays real-time sensor data, historical trends, and predictions.

            show_occupancy_info(sensor, room, value, unit):
                Displays detailed information about room occupancy.

            store_training_data(co2, temperature, humidity, iaq, noise_level, pressure, light_level,
                            gas_resistance, room_volume, label):
                Stors training data for an AI Model in training_data.csv.


            display_combined_graph(room, sensor, unit, timestamps, values, future_times, predictions):
                Shows a graph for the historic sensor values and for the predicted sensor values.

            predict_data(room, sensor, unit, timestamps, values):
                Predicts future sensor values using linear regression based on historical data.

            display_historyic_graph(room, sensor, unit, timestamps, values):
                Plots historical sensor data.

            show_sensor_gauge(sensor, unit, current_value):
                Renders a gauge visualization for sensor data.

            stream_sensor_info(sensor, sensor_detail=True, concentration=True):
                Provides context and interpretation for sensor readings.

            set_page_style():
                Configures the look of the website.

            show_warning():
                Displays the generated warnings.

            run():
                Starts the app.

        Usage:
            dashboard = Dashboard(data)
            # This initializes the dashboard and starts the Streamlit app.
        """

    def __init__(self, data):

        self.data = data
        self.run()

    def create_interactive_room_buttons(self, sensor):
        """
        Displays interactive buttons on a Streamlit dashboard at predefined coordinates
        representing different rooms equipped with sensors. Each button shows sensor data
        as a tooltip and allows users to select a room by clicking it.

        Parameters:
        -----------
        sensor : str
            The name of the sensor whose data will be displayed in tooltips.

        Behavior:
        ---------
        - Uses a predefined layout (`rows_layout`) to organize buttons into rows and columns.
        - The `room_coordinates` dictionary maps sensor names to specific grid positions.
        - Clicking a button updates `st.session_state.selected_room` and `st.session_state.selected_sensor`.
        - The button tooltip displays the current sensor value and its unit.

        """

        # Define the layout structure for the grid (rows with columns)
        # Each row is assigned a set of Streamlit columns, which determine how buttons are arranged.
        rows_layout = {
            0: st.columns(1),
            10: st.columns(1),
            1: st.columns([2, 2, 2, 2, 1, 8]),  # Custom column width distribution for row 1
            9: st.columns(1),
            2: st.columns(6),  # Row with 6 evenly spaced columns
            3: st.columns([2, 3, 2, 2, 3, 4]),  # Uneven column widths for layout adjustments
            4: st.columns([2, 3, 2, 2, 4, 3]),
            5: st.columns(1),
            6: st.columns(1),
            7: st.columns(1),
            8: st.columns(1),
        }

        # Mapping of sensor names to their respective row and column positions in the grid
        self.room_coordinates = {
            "multisensor_115": (1, 1),
            "multisensor_108": (1, 2),
            "multisensor_107": (1, 3),
            "multisensor_114": (1, 4),
            "multisensor_110": (1, 5),
            "multisensor_109": (1, 6),
            "multisensor_104": (3, 6),
            "multisensor_106": (4, 5),
            "multisensor_111": (4, 3),
            "multisensor_103": (4, 4),
            "multisensor_113": (3, 1),
            "multisensor_112": (2, 2),
            "multisensor_105": (3, 5),
        }

        def handler(*args, **kwargs):
            """
            Handles button clicks by updating session state variables
            to store the selected room and sensor.
            """
            room_id = args[0]
            sensor = args[1]
            st.session_state.selected_room = room_id
            st.session_state.selected_sensor = sensor  # Store the selected sensor in session state

        # Loop through each room's assigned position
        for room_id, (row, col) in self.room_coordinates.items():
            if row in rows_layout:
                # Get the column object (col - 1 because lists are 0-indexed)
                column = rows_layout[row][col - 1]
                with column:
                    # Create three columns inside the selected grid column to center the button
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:  # Place the button in the center column
                        # Retrieve the sensor's current value and unit from data
                        value = self.data[room_id]["sensors"][sensor]["current_value"]
                        unit = self.data[room_id]["sensors"][sensor]["unit"]

                        # Create an interactive button with a tooltip showing sensor data
                        st.button("📍️",
                                  help=f"{value} {unit}",  # Tooltip displaying sensor value and unit
                                  key=uuid.uuid4(),  # Generate a unique key for each button
                                  on_click=handler,  # Call handler function on click
                                  args=(room_id, sensor))  # Pass room_id and sensor to handler

    def check_for_warnings(self, sensor, value, unit):
        """
        Evaluates the given sensor value and determines if a warning message should be issued.

        This function compares the sensor's value against predefined thresholds and returns an
        appropriate message if the value falls outside a comfortable range.

        Parameters:
        -----------
        sensor : str
            The name of the sensor being evaluated (e.g., "Temperature", "Humidity", "CO2").
        value : str or float
            The current value of the sensor. If the value is 'unknown', a message will be returned.
        unit : str
            The unit of measurement associated with the sensor value (e.g., "°C", "%", "ppm").

        Returns:
        --------
        tuple:
            - A string containing the warning message or an indication that the value is within a safe range.
            - A boolean flag (`True` if the value is within a comfortable range, `False` if a warning is issued).

        Behavior:
        ---------
        - The function checks if the sensor is present in the predefined `warnings` dictionary.
        - If the sensor has thresholds for "too_low" or "too_high", the function evaluates whether the value
          is outside the safe range and returns the corresponding warning.
        - If the value is 'unknown', it returns a message indicating the sensor has no current reading.
        - If the value is within the acceptable range, the function returns a message indicating normal conditions.
        """

        # Define warning thresholds for different sensors
        warnings = {
            "Temperature": {
                "too_low": (18, "It's too cold to concentrate. Consider turning up the heat."),
                "too_high": (26, "It's too hot to concentrate. Consider opening a window."),
            },
            "Humidity": {
                "too_low": (30, "The air is too dry. Consider increasing ventilation or opening a window."),
                "too_high": (60, "The air is too humid. Consider opening a window."),
            },
            "CO2": {
                "too_high": (1000, "CO2 levels are high. Open a window for fresh air."),
            },
            "IAQ": {
                "too_high": (100, "Indoor Air Quality is poor. Consider increasing ventilation or opening a window."),
            },
            "UV Index": {
                "too_high": (6, "UV Index is high. Consider closing the blinds or staying out of direct sunlight."),
            },
            "Microphone Noise Level": {
                "too_high": (80, "Noise levels are high. Consider reducing the noise or moving to a quieter space."),
            },
            "Pressure": {
                "too_low": (980, "Atmospheric pressure is low. It might feel stuffy. Consider opening a window."),
                "too_high": (1030, "Atmospheric pressure is high. Consider opening a window to ventilate the room."),
            },
            "Light": {
                "too_low": (50, "Light levels are too low. Consider turning on more lights."),
                "too_high": (1000, "Light levels are too bright. Consider adjusting the lighting."),
            },
            "Gas Resistance": {
                "too_high": (1000, "Gas resistance is high. Open a window or ventilate the room."),
            },
            "Occupancy": {
                "too_high": (10, "Too many people in the room. Consider moving to a less crowded room."),
            },
        }

        # Handle case where sensor value is unknown
        if value == 'unknown':
            return f"{sensor} has no current value.", True

        # Check if the sensor has predefined thresholds
        if sensor in warnings:
            # Check for low-value warnings
            if "too_low" in warnings[sensor] and float(value) < warnings[sensor]["too_low"][0]:
                return warnings[sensor]["too_low"][1], False

            # Check for high-value warnings
            if "too_high" in warnings[sensor] and float(value) > warnings[sensor]["too_high"][0]:
                return warnings[sensor]["too_high"][1], False

        # If no warnings are triggered, return a message indicating normal conditions
        return f"{sensor} value is within a comfortable range.", True

    def show_current_data(self, sensor):
        """
        Display the current data for a given sensor, including the current value, historical data,
        future predictions, warnings, and relevant graphs.

        The function checks for a selected room and sensor, displays the current sensor value,
        compares it with ideal values, predicts future values if applicable, shows warnings,
        and visualizes the historical and predicted data.

        Parameters:
        -----------
        sensor : str
            The name of the sensor to display data for (e.g., "Temperature", "Humidity", etc.).
        """

        # Ideal values for various sensors
        ideal_values = {
            "Temperature": 21,
            "Humidity": 45,
            "CO2": 400,
            "IAQ": 50,
            "UV Index": 0,
            "Microphone Noise Level": 40,
            "Pressure": 1013,
            "Light": 400,
            "Gas Resistance": 200,
            "Occupancy": 1,
        }

        # Ensure a room is selected in the session state
        if "selected_room" not in st.session_state:
            return  # Exit if no room is selected

        room = st.session_state.selected_room

        # Header for the sensor display
        st.header(f"{self.data[room]['room']} - {sensor}")

        # Get the current value and unit for the sensor
        sensor_data = self.data[room]["sensors"][sensor]
        current_value = sensor_data["current_value"]
        unit = sensor_data["unit"]

        # Check if there is any historical data
        last_historic_value = 0
        if sensor_data["history"]:
            last_historic_value = float(sensor_data["history"][-1][0])

        # Prepare historical data for graphing
        historic_value = sensor_data["history"]
        timestamps_all = [datetime.fromisoformat(entry[1].replace("Z", "")) for entry in historic_value]
        values_all = [entry[0] for entry in historic_value]

        # Filter out any future timestamps
        current_time = datetime.now()
        timestamps = []
        values = []
        for ts, val in zip(timestamps_all, values_all):
            if ts <= current_time:
                timestamps.append(ts)
                values.append(val)

        # Prepare predictions for future data (if applicable)
        predictions = None
        future_times = None
        if len(timestamps) > 1:
            future_times, predictions = self.predict_data(room, sensor, unit, timestamps, values)

        # Display occupancy information if the sensor is "Occupancy"
        if sensor == "Occupancy":
            self.show_occupancy_info(sensor, room, current_value, unit)

        # Display current value and metrics
        if current_value is not None and sensor != "Occupancy":
            col1, col2, col3 = st.columns([2, 2, 5])

            # Convert value and calculate delta from last historic value
            value = float(current_value) if current_value != 'unknown' else 'unknown'
            delta = round(value - last_historic_value if value != 'unknown' else 0, 2)

            # Determine delta color based on value and delta
            delta_color = "normal" if value < ideal_values[sensor] and delta < 0 else "inverse" if value > ideal_values[
                sensor] and delta > 0 else "off"

            # Display current sensor value
            col1.metric(label=f"current {sensor}", value=f"{value} {unit}", delta=delta, delta_color=delta_color)

            # Display predicted value in 15 minutes, if applicable
            if predictions:
                value = round(predictions[0], 2)
                delta = round(predictions[0] - float(current_value), 2)
                delta_color = "normal" if value < ideal_values[sensor] \
                                          and delta < 0 else "inverse" if value > \
                                        ideal_values[sensor] and delta > 0 else "off"
                col2.metric(label=f"{sensor} in 15 minutes", value=f"{value} {unit}", delta=delta,
                            delta_color=delta_color)

            # Check for warnings based on current and predicted values
            text, result = self.check_for_warnings(sensor, current_value, unit)
            if result:
                col3.success(text)
                if predictions:
                    text, result = self.check_for_warnings(sensor, predictions[0], unit)
                    if not result:
                        col3.warning(f"In 15 minutes: {text}")
            else:
                col3.warning(text)

            # Display sensor-related information
            self.stream_sensor_info(sensor, sensor_detail=False)

            # Display the sensor's gauge
            self.show_sensor_gauge(sensor, unit, current_value)

            # Display historical or combined graph (with predictions)
            if sensor == "Microphone Noise Level" or not (predictions and future_times):
                self.display_historyic_graph(room, sensor, unit, timestamps, values)
            else:
                self.display_combined_graph(room, sensor, unit, timestamps, values, future_times, predictions)

            # Display more sensor-related information
            self.stream_sensor_info(sensor, concentration=False)

    def show_occupancy_info(self, sensor, room, value, unit):
        """
        Displays occupancy information, factors affecting accuracy,
        and allows users to input actual occupancy data to help train an AI model.

        Parameters:
        - sensor (str): The type of sensor used for occupancy detection (e.g., CO2, ...).
        - room (str): The name of the room where the occupancy is being calculated.
        - value (int): The calculated occupancy value (number of people).
        - unit (str): The unit of the calculated occupancy value (typically people).
        """

        # Creating layout columns for the information to be displayed.
        col0, = st.columns(1)  # Empty column for structure (not used).
        col1, col2, col3 = st.columns([10, 10, 1])  # Main columns for displaying information.

        with col1:
            # Displaying the current calculated occupancy value.
            st.subheader("Current Calculated Occupancy")
            c1, c2, c3 = st.columns(3)  # Sub-columns for structured layout.
            c2.metric(label="Current Occupancy", value=f"{value} {unit}", label_visibility="hidden")

            # Providing a description about the factors that affect the accuracy of occupancy estimation.
            st.subheader("Factors Affecting Accuracy")
            text = """The CO₂-based occupancy estimation can be affected by factors like open windows, doors, or ventilation systems, which can reduce CO₂ concentration and lead to underestimation. Variations in individual breathing rates and activity levels can also impact CO₂ production, causing inaccuracies."""
            st.markdown(text)

        with col2:
            # Stylable container to help users train the AI model.
            with stylable_container(
                    key="container_with_border",
                    css_styles="""
                    {
                        border-radius: 0.5rem;
                        width: 110%; /* Adjust the width as needed */
                        margin-top: -1em;
                        background-color: #fff2bb;
                        padding: 1em;
                    }
                    """,
            ):
                # Heading and description for the section that allows users to enter the actual occupancy number.
                st.subheader("Help Train Our AI Model")
                text = """
                We are actively collecting data from rooms in this building 
                to train an AI model which uses a combination of sensor data, room metadata, and occupancy values. 
                """
                st.markdown(text)
                st.markdown("Please look around and enter the actual number of people in this room.")

                # Create a number input field for users to enter the actual number of people.
                number = st.number_input("Total Number of People:", min_value=0, step=1, label_visibility="hidden",
                                         value=value)

                # Submit button to save the data entered by the user.
                if st.button("Submit"):
                    # Extracting the current sensor values from the room data dictionary.
                    d = self.data[room]["sensors"]
                    co2 = d["CO2"]["current_value"]
                    temperature = d["Temperature"]["current_value"]
                    humidity = d["Humidity"]["current_value"]
                    iaq = d["IAQ"]["current_value"]
                    noise_level = d["Microphone Noise Level"]["current_value"]
                    pressure = d["Pressure"]["current_value"]
                    light_level = d["Light"]["current_value"]
                    gas_resistance = d["Gas Resistance"]["current_value"]
                    room_volume = self.data[room]["volume"]  # Volume of the room for calculations.
                    label = number  # The user-provided number is the ground truth (label) for training.

                    # Storing the collected data for future training of the AI model.
                    self.store_training_data(co2, temperature, humidity, iaq, noise_level, pressure,
                                             light_level, gas_resistance, room_volume, label)
                    st.toast(f"successfully saved to training data", icon='🎉')

        col3, = st.columns(1)  # Column for displaying the CO2-based occupancy calculation method.

        with col3:
            # Displaying a description of how occupancy is estimated based on CO2 concentration.
            st.subheader("How the Occupancy is Calculated")
            text = """One effective method involves [analyzing the concentration of carbon dioxide (CO₂) in the air](https://pmc.ncbi.nlm.nih.gov/articles/PMC7411428). As humans exhale CO₂, its concentration increases with the number of occupants. By monitoring CO₂ levels, we can estimate occupancy in a non-intrusive manner."""
            st.markdown(text)

            # Explaining the parameters used in the CO2-based occupancy estimation formula.
            formular = """
                **The estimation is based on the following parameters:**
                - **Baseline CO₂ Concentration**: The CO₂ level in an unoccupied room, typically around 550 ppm.
                - **CO₂ Emission Rate per Person**: The amount of CO₂ produced by an individual, approximately 18 liters per hour.
                - **Time Elapsed**: The duration since the last measurement, in seconds.

                **The formula to estimate the number of people is:**
                """
            st.markdown(formular)

            # Displaying the mathematical formula for estimating occupancy.
            st.latex(r"""
                \text{Occupancy} = \frac{(\text{Current CO₂} - \text{Baseline CO₂}) \times \text{Room Volume}}{\text{Emission Rate} \times (\text{Time Elapsed} / 3600)} 
            """)

    def store_training_data(self, co2, temperature, humidity, iaq, noise_level, pressure, light_level,
                            gas_resistance, room_volume, label):
        """
        Stores a new line of training data in a CSV file.

        Args:
            co2 (float): CO₂ level in the room.
            temperature (float): Temperature in the room.
            humidity (float): Humidity in the room.
            iaq (float): Indoor Air Quality score.
            noise_level (float): Noise level in the room (e.g., microphone).
            pressure (float): Pressure in the room.
            light_level (float): Light level in the room.
            gas_resistance (float): Gas resistance (VOC levels).
            room_volume (float): Volume of the room (in cubic meters).
            label (int/float): The number of people in the room (or any other target variable).
        """
        # Check if the file exists
        path = Path(__file__).parent.parent / "training_data" / "training_data.csv"
        file_exists = os.path.isfile(path)

        # Open the file in append mode
        with open(path, mode='a', newline='') as file:
            writer = csv.writer(file)

            # Write the header only if the file is empty (i.e., it doesn't exist)
            if not file_exists:
                header = ['CO2', 'Temperature', 'Humidity', 'IAQ', 'Noise_Level', 'Pressure', 'Light_Level',
                          'Gas_Resistance', 'Room_Volume', 'Datetime', 'Label']
                writer.writerow(header)

            # Get the current datetime for each entry
            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Write the feature values, room volume, datetime, and label as a new row
            writer.writerow(
                [co2, temperature, humidity, iaq, noise_level, pressure, light_level, gas_resistance,
                 room_volume, current_datetime, label])

    def show_sensor_gauge(self, sensor, unit, value):
        """
        Displays a gauge chart showing the current value of a sensor in relation to its optimal range.

        Parameters:
        - sensor (str): The type of sensor (e.g., "Temperature", "Humidity", etc.).
        - unit (str): The unit of the sensor value (e.g., "°C", "%", "ppm").
        - value (float): The current value measured by the sensor.
        """

        # Defining the optimal range for various sensors.
        sensor_ranges = {
            "Temperature": [18, 26],
            "Humidity": [30, 60],
            "CO2": [0, 1000],
            "IAQ": [0, 100],
            "UV Index": [0, 6],
            "Microphone Noise Level": [0, 80],
            "Pressure": [980, 1030],
            "Light": [50, 1000],
            "Gas Resistance": [0, 1000],
            "Occupancy": [0, 10],
        }

        # Retrieve the good range for the selected sensor.
        good_range = sensor_ranges[sensor]
        min_value, max_value = good_range[0] - (good_range[1] - good_range[0]), good_range[1] + (
                    good_range[1] - good_range[0])

        # Ensure minimum value is not less than 0.
        if min_value < 0:
            min_value = 0

        # Round both min and max values to the nearest 10 for better readability.
        min_value = round(min_value / 10) * 10
        max_value = round(max_value / 10) * 10

        # Calculate the size of the orange "warning" block (1/4th of the good range).
        orange_block_size = round((good_range[1] - good_range[0]) / 4)

        # Helper function to normalize the sensor value for the gauge chart.
        def normalize_value(value):
            """Normalizes a given sensor value to a 0-1 range for the gauge chart."""
            nv = (value - min_value) / (max_value - min_value)
            return round(nv, 2)

        # Configuring the gauge chart options for display.
        option = {
            "series": [
                {
                    "type": "gauge",  # Using gauge chart type.
                    "startAngle": 180,  # Start angle for the gauge.
                    "endAngle": 0,  # End angle for the gauge.
                    "min": min_value,  # Minimum value for the gauge.
                    "max": max_value,  # Maximum value for the gauge.
                    "splitNumber": 5,  # Number of divisions in the gauge.
                    "axisLine": {
                        "lineStyle": {
                            "width": 10,  # Width of the gauge line.
                            "color": [
                                [normalize_value(good_range[0] - orange_block_size), "#ffb7ac"],  # Red (Too Low)
                                [normalize_value(good_range[0]), "#f9f8ab"],  # Orange (Warning)
                                [normalize_value(good_range[1]), "#d4ffce"],  # Green (Optimal)
                                [normalize_value(good_range[1] + orange_block_size), "#f9f8ab"],  # Orange (Warning)
                                [normalize_value(max_value), "#ffb7ac"],  # Red (Too High)
                            ],
                        }
                    },
                    "pointer": {
                        "length": "60%",  # Pointer length in the gauge.
                        "itemStyle": {
                            "color": 'auto'  # Auto color for the pointer.
                        }
                    },
                    "detail": {"formatter": "{value} " + unit},  # Formatting the displayed value with the unit.
                    "data": [{"value": value}],  # Setting the current value to display.
                }
            ]
        }

        # Display the subheader and the gauge chart in Streamlit.
        st.subheader("Optimal Range for Concentration")
        st_echarts(options=option, height="300px")

    def display_combined_graph(self, room, sensor, unit, timestamps, values, future_times, predictions):
        """
        Display a time-series graph combining historical data and prognosis data for a specific room and sensor.

        Parameters:
        - room (str): The name or identifier of the room where the sensor is located.
        - sensor (str): The type of sensor being displayed (e.g., "Temperature", "Humidity").
        - unit (str): The unit of measurement for the sensor values (e.g., "°C", "%").
        - timestamps (list of datetime objects): The historical timestamps for the data points.
        - values (list of float): The historical sensor values corresponding to the timestamps.
        - future_times (list of datetime objects): The future timestamps for the predicted data points.
        - predictions (list of float): The predicted values corresponding to the future timestamps.
        """

        # Display the subheader with sensor data type for the current room
        st.subheader(f"{sensor} Data (Historical & Prognosis)")

        # Prepare historical data for the x-axis (formatted as hour:minute)
        x_axis_historical = [ts.strftime("%H:%M Uhr") for ts in timestamps]

        # Prepare prognosis data for the x-axis (formatted as hour:minute)
        x_axis_prognosis = [ft.strftime("%H:%M Uhr") for ft in future_times]

        # Combine the historical and prognosis data for the x-axis and pad the historical series to align with prognosis data
        x_axis_combined = x_axis_historical + x_axis_prognosis  # Combined x-axis data
        combined_historical_data = values + [None] * len(predictions)  # Historical data with None padding for alignment
        combined_prognosis_data = [None] * len(values) + predictions  # Prognosis data with None padding for alignment

        # ECharts options for the combined graph
        combined_options = {
            "tooltip": {"trigger": "axis"},  # Tooltip on hover, displaying data on the axis
            "xAxis": {
                "type": "category",  # X-axis is categorical (time intervals)
                "data": x_axis_combined,  # X-axis data (combined historical and prognosis)
                "name": "Time",  # Label for the X-axis
            },
            "yAxis": {
                "type": "value",  # Y-axis represents numerical values
                "name": sensor,  # Label for the Y-axis (sensor name)
            },
            "series": [
                {
                    "data": combined_historical_data,  # Historical data points
                    "type": "line",  # Line graph for historical data
                    "smooth": True,  # Smooth the line curve
                    "name": f"Historical: {sensor} ({unit})",  # Label for the historical data series
                    "lineStyle": {"type": "solid"}  # Solid line style for historical data
                },
                {
                    "data": combined_prognosis_data,  # Prognosis data points
                    "type": "line",  # Line graph for prognosis data
                    "smooth": True,  # Smooth the line curve
                    "name": f"Prognosis: {sensor} ({unit})",  # Label for the prognosis data series
                    "lineStyle": {"type": "dashed"}  # Dashed line style for prognosis data
                }
            ],
            "legend": {
                "data": [f"Historical: {sensor} ({unit})", f"Prognosis: {sensor} ({unit})"]
                # Legend labels for the data series
            },
            "dataZoom": [  # Zoom controls for the graph
                {"type": "slider", "start": 0, "end": 100},  # Slider zoom control for x-axis
                {"type": "inside"}  # Enables zooming inside the graph
            ],
        }

        # Render the combined graph using Streamlit's ECharts component
        st_echarts(options=combined_options, key=f"{room}_combined_chart")

    def display_historical_graph(self, room, sensor, unit, timestamps, values):
        """
        Display a time-series graph for historical data for a specific room and sensor.

        Parameters:
        - room (str): The name or identifier of the room where the sensor is located.
        - sensor (str): The type of sensor being displayed (e.g., "Temperature", "Humidity").
        - unit (str): The unit of measurement for the sensor values (e.g., "°C", "%").
        - timestamps (list of datetime objects): The historical timestamps for the data points.
        - values (list of float): The historical sensor values corresponding to the timestamps.
        """

        # Prepare historical data for the x-axis (formatted as hour:minute)
        x_axis_historical = [ts.strftime("%H:%M Uhr") for ts in timestamps]

        # Historical data series configuration for the line chart
        historical_series = {
            "data": values,  # The actual historical values to be plotted
            "type": "line",  # Line chart type
            "smooth": True,  # Smooth the curve of the line
            "name": f"{sensor} ({unit})"  # Label for the line
        }

        # ECharts options for displaying the historical data
        historical_options = {
            "title": {"text": f"Historical Data"},  # Title of the chart
            "tooltip": {"trigger": "axis"},  # Tooltip on hover over data points
            "xAxis": {
                "type": "category",  # X-axis is categorical (time intervals)
                "data": x_axis_historical,  # Data for the x-axis (time)
                "name": "Time"  # Label for the X-axis
            },
            "yAxis": {
                "type": "value",  # Y-axis represents numerical values
                "name": sensor  # Label for the Y-axis (sensor name)
            },
            "series": historical_series,  # Data series (historical values)
            "legend": {
                "data": [historical_series["name"]]  # Legend label for the historical data series
            },
            "dataZoom": [  # Zoom controls for the graph
                {"type": "slider", "start": 0, "end": 100},  # Slider zoom control for x-axis
                {"type": "inside"}  # Enables zooming inside the graph
            ],
        }

        # Render the historical graph using Streamlit's ECharts component
        st_echarts(options=historical_options, key=f"{room}_historical_chart")

    def predict_data(self, room, sensor, unit, timestamps, values):
        """
        Predict future sensor data based on historical values using linear regression.

        Parameters:
        - room (str): The name or identifier of the room where the sensor is located.
        - sensor (str): The type of sensor being predicted (e.g., "Temperature", "Humidity").
        - unit (str): The unit of measurement for the sensor values (e.g., "°C", "%").
        - timestamps (list of datetime objects): The timestamps corresponding to the sensor values.
        - values (list of float): The historical sensor values corresponding to the timestamps.

        Returns:
        - future_times (list of datetime objects): The predicted future times in 15-minute intervals.
        - predictions (list of float): The predicted sensor values for the future times.
        """

        # Case 1: Use only the last two hours of data
        two_hours_ago = timestamps[-1] - timedelta(hours=2)
        recent_indices = [i for i, ts in enumerate(timestamps) if ts >= two_hours_ago]

        # Special case for Light sensor, where all historical data is used
        if sensor == "Light":
            recent_indices = [i for i, ts in enumerate(timestamps)]

        # Extract the recent timestamps and values
        recent_timestamps = [timestamps[i] for i in recent_indices]
        recent_values = [values[i] for i in recent_indices]

        # Case 2: Use data from the last significant turning point (local maxima or minima)
        turning_point_index = None
        if sensor not in ["Microphone Noise Level", "Occupancy", "Light"]:  # Ignore for certain sensors
            for i in range(len(values) - 2, 0, -1):  # Search for turning point from the end
                if (values[i] > values[i - 1] and values[i] > values[i + 1]) or (
                        values[i] < values[i - 1] and values[i] < values[i + 1]):
                    turning_point_index = i
                    break

        # If a turning point is found, adjust the data to start from that point
        if turning_point_index:
            recent_timestamps = timestamps[turning_point_index:]
            recent_values = values[turning_point_index:]

        # Prepare data for regression (time in seconds from the first timestamp)
        time_numbers = np.array([(ts - recent_timestamps[0]).total_seconds() for ts in recent_timestamps])

        # Perform linear regression using scipy.stats.linregress
        slope, intercept, r_value, p_value, std_err = stats.linregress(time_numbers, recent_values)

        # Define the prediction function based on the linear regression model
        def myfunc(x):
            return slope * x + intercept

        # Round the current time down to the nearest 15-minute interval
        current_time = datetime.now()
        minute_adjustment = current_time.minute % 15
        nearest_quarter_hour = current_time - timedelta(minutes=minute_adjustment, seconds=current_time.second,
                                                        microseconds=current_time.microsecond)

        # Generate future times in 15-minute intervals (next 6 hours)
        future_times = [nearest_quarter_hour + timedelta(minutes=15 * i) for i in range(0, 25)]  # 6 hours ahead

        # Prepare future time data for prediction (convert to seconds since the first timestamp)
        future_time_numbers = np.array([(ft - recent_timestamps[0]).total_seconds() for ft in future_times])

        # Use the regression model to predict future values
        predictions = list(map(myfunc, future_time_numbers))

        # Set negative predictions to 0, if applicable (e.g., if sensor values can't be negative)
        predictions = [max(0, p) for p in predictions]

        # Return the predicted future times and values
        return future_times, predictions


    def display_future_graph(self, future_times, predictions, sensor, unit):
        """
        Displays the predicted sensor data in a line graph using ECharts.

        Parameters:
        future_times (list): A list of future timestamps for the prediction.
        predictions (list): A list of predicted sensor values.
        sensor (str): The type of sensor (e.g., Temperature, CO2, etc.).
        unit (str): The unit of measurement for the sensor (e.g., °C, ppm, etc.).
        """
        # Prepare the x-axis labels (times in HH:MM format)
        x_axis_prognosis = [ft.strftime("%H:%M Uhr") for ft in future_times]

        # Prepare the series data for the prognosis line
        prognosis_series = {
            "data": predictions,
            "type": "line",
            "smooth": True,
            "name": f"Prognosis: {sensor} ({unit})",
            "lineStyle": {"type": "dashed"}
        }

        # ECharts options for rendering the prognosis graph
        prognosis_options = {
            "title": {"text": f"Prognosis"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_axis_prognosis, "name": "Time"},
            "yAxis": {"type": "value", "name": sensor},
            "series": prognosis_series,
            "legend": {"data": prognosis_series["name"]},
            "dataZoom": [
                {"type": "slider", "start": 0, "end": 100},
                {"type": "inside"}
            ],
        }

        # Render the ECharts graph using Streamlit
        st_echarts(options=prognosis_options, key=f"prognosis_chart")


    def stream_sensor_info(self, sensor, concentration=True, sensor_detail=True, text=None):
        """
        Streams detailed information about the sensor, including its impact on concentration and how it is measured.

        Parameters:
        sensor (str): The sensor type (e.g., Temperature, Humidity, etc.).
        concentration (bool): Whether to display the concentration-related information.
        sensor_detail (bool): Whether to display how the sensor is measured.
        text (str): Additional text information to display.
        """
        # Descriptions of sensor concentration impact
        sensor_descriptions_concentration = {
            "Temperature": """
                Temperature plays a crucial role in human concentration and cognitive performance. Studies show that higher temperatures can lead to increased fatigue, dehydration, and reduced mental clarity, while colder environments often result in physical discomfort, increased energy expenditure, and diminished focus. Maintaining an optimal room temperature of around 20-22°C is critical for ensuring comfort, mental sharpness, and productivity.
                """,

            "Humidity": """
                High humidity can increase discomfort by impairing the body’s ability to cool itself, while low humidity can dry out 
                mucous membranes, causing irritation. Maintaining an indoor humidity level between 40–60% supports comfort, 
                respiratory health, and focus.
                """,

            "CO2": """
                Elevated CO2 levels (above 1000 ppm) can impair cognitive function, causing fatigue, headaches, and reduced alertness. 
                Maintaining CO2 levels below 800 ppm is optimal for productivity and well-being.
                """,

            "IAQ": """
                Poor air quality can lead to respiratory irritation, headaches, and reduced cognitive performance. 
                Monitoring IAQ helps ensure a healthier, more productive environment by managing indoor pollutants.
                """,

            "UV Index": """
                Prolonged exposure to high UV levels can cause skin damage, eye strain, and increase the risk of skin cancer. 
                Monitoring UV levels helps reduce harmful exposure, ensuring health and focus.
                """,

            "Microphone Noise Level": """
                High noise levels can disrupt concentration, increase stress, and impair communication. 
                Prolonged exposure to noise above 70 dB may lead to fatigue and decreased productivity.
                """,

            "Pressure": """
                Pressure fluctuations can cause discomfort, headaches, and fatigue, especially for those sensitive to weather changes. 
                Stable pressure is ideal for comfort and focus.
                """,

            "Light": """
                Inadequate lighting can cause eye strain and fatigue, reducing concentration. 
                Proper lighting, with a temperature between 4000–5000 K, enhances alertness and focus.
                """,

            "Gas Resistance": """
                Exposure to harmful gases can cause respiratory issues, headaches, and long-term health risks. 
                Monitoring gas concentrations ensures safety and maintains good air quality.
                """,
        }

        # Descriptions of how sensors measure the data
        sensor_descriptions_detail = {
            "Temperature": """
                The BME680 and SCD30 sensors work together to provide an accurate, combined temperature reading. The BME680 uses an integrated thermistor to measure ambient temperature by detecting resistance changes as heat energy fluctuates. The SCD30 adds further precision by incorporating a Kalman-filtered combination of both sensors’ data, ensuring stable and reliable temperature readings. This fusion of data ensures highly accurate temperature monitoring, contributing to a more comfortable and productive environment.
                """,
            "Humidity": """
                The BME680 and SCD30 sensors work together to measure relative humidity accurately. The BME680 uses a capacitive humidity sensor that detects changes in capacitance as the polymer film absorbs water molecules, while the SCD30 sensor uses a similar capacitive approach to detect humidity levels. These sensors’ data are combined through a Kalman filter, providing a reliable and stable humidity measurement that helps create an optimal environment for focus and comfort.
                """,

            "CO2": """
                The SCD30 sensor uses nondispersive infrared (NDIR) technology to measure CO2 concentration. It emits infrared light and measures the absorption by CO2 molecules to provide an accurate reading.
                """,

            "IAQ": """
                The BME680 sensor assesses indoor air quality by detecting volatile organic compounds (VOCs) and other gaseous pollutants. It uses a metal-oxide semiconductor that reacts with gases, changing its conductivity to generate an air quality index.
                """,

            "UV Index": """
                The LTR390 sensor measures ultraviolet (UV) radiation intensity with photodiodes sensitive to UV wavelengths. It provides accurate data on UV levels, enabling UV index calculation.
                """,

            "Microphone Noise Level": """
                The MAX4466 sensor detects sound levels by measuring pressure changes in sound waves, converting them into an electrical signal. 
                """,

            "Pressure": """
                The BME680 sensor measures atmospheric pressure using a piezoresistive sensor, which detects pressure changes 
                based on diaphragm deformation and converts this into an electrical signal.
                """,

            "Light": """
                The LTR390 sensor measures light intensity using photodiodes, and the APDS-9960 sensor detects light temperature, 
                proximity, and color to monitor ambient lighting conditions.
                """,

            "Gas Resistance": """
                The MICS-6814 sensor detects gases like ammonia (NH3), carbon monoxide (CO), and nitrogen dioxide (NO2) 
                using metal-oxide semiconductors that change resistance in response to gas molecules.
                """,
        }

        # Function to stream the description text with a slight delay
        def stream_data(text):
            for word in text.split(" "):
                yield word + " "
                time.sleep(0.02)

        # Display concentration-related text if the flag is set
        if concentration:
            text_1 = sensor_descriptions_concentration[sensor]
            st.subheader("Why is it Important?")
            st.write_stream(stream_data(text_1))

        # Display sensor measurement details if the flag is set
        if sensor_detail:
            st.subheader("How it is Measured")
            text_2 = sensor_descriptions_detail[sensor]
            st.write_stream(stream_data(text_2))

        # Display additional text if provided
        if text:
            st.write_stream(stream_data(text))

    def run(self):
        """
        Run the Streamlit dashboard to visualize sensor data.

        This method initializes the Streamlit app, sets the page style, creates tabs for each sensor type,
        and dynamically displays sensor data for the selected room when a user interacts with the dashboard.
        It updates the content based on the selected sensor and room.
        """
        self.set_page_style()  # Set custom page style and background
        st.title("Multisensor Visualization")  # Set the page title

        # List of available sensors
        sensor_list = [
            "Occupancy", "Humidity", "Temperature", "CO2", "IAQ",
            "UV Index", "Microphone Noise Level", "Pressure", "Light", "Gas Resistance"
        ]

        # Create tabs for each sensor type
        tabs = st.tabs(sensor_list)

        # Loop over each tab to set up individual sensor visualizations
        for i, tab in enumerate(tabs):
            with tab:
                st.session_state.selected_tab = sensor_list[i]  # Track the selected tab (sensor)
                self.create_interactive_room_buttons(
                    sensor_list[i])  # Display interactive room buttons for selected sensor

                # If a room has been selected and the current sensor matches the selected one
                if (
                        "selected_room" in st.session_state
                        and st.session_state.selected_sensor == sensor_list[i]
                ):
                    self.show_current_data(sensor_list[i])  # Display the current data for the selected sensor

    def set_page_style(self):
        """
        Set custom CSS to style the Streamlit dashboard, including background images and page layout.

        This method sets the page's title and icon, customizes the layout by adding a background image,
        and hides the default Streamlit menu. It also loads a logo and applies custom CSS for the page container
        and background image.
        """
        # Define the path for the logo image
        png_file = Path(__file__).parent / "media" / "zeki_logo.png"
        # Convert the Path object to string to ensure compatibility
        png_file_str = str(png_file)
        # Set the logo (works if deployed on Streamlit Cloud)
        st.logo(png_file_str, icon_image=png_file_str)

        # Set the Streamlit page configuration (title and icon)
        #st.set_page_config(page_title="MSV", page_icon=png_file_str)

        # Define the path for the 3D room plan image
        png_file = Path(__file__).parent / "media" / "ZEKI-Floorplan-1536x640.png"

        # Read and encode the image as base64 to be used in the background
        with open(png_file, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()

        # Define custom CSS for background image and layout
        page_bg_img = f"""
        <style>
        /* Set the background image for the entire Streamlit app container */
        .stMainBlockContainer {{
            max-width: 95%; /* Limit content width to 95% of the screen */
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: 105% 500px;  /* Ensure the image covers the container */
            background-repeat: no-repeat;  /* Prevent the image from repeating */
            background-position: center calc(190px);  /* Position the background image */
        }};
        .stMainMenu {{visibility: hidden}}  /* Hide the default menu */
        </style>
        """
        # Apply the background image and CSS to the app
        st.markdown(page_bg_img, unsafe_allow_html=True)

        # Hide the main menu using custom CSS
        hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """
        # Apply the hide menu CSS
        st.markdown(hide_menu_style, unsafe_allow_html=True)

    def show_warnings(self):
        """
        Check the sensor data for each room and display warnings if any sensor value is outside acceptable limits.

        This method iterates through the data for each room and its associated sensors. It checks for potential
        issues such as out-of-range sensor values and displays warnings using Streamlit's `st.toast()` if any
        sensor value violates predefined conditions.
        """
        # Iterate through each room in the data dictionary
        for room_id, sensor_info in self.data.items():
            room = sensor_info["room"]  # Get the room name

            # Iterate through each sensor in the room's sensor dictionary
            for sensor, sensor_details in sensor_info["sensors"].items():
                value = sensor_details["current_value"]  # Get the current sensor value
                unit = sensor_details["unit"]  # Get the unit for the sensor value

                # Check for warnings based on the sensor type, value, and unit
                text, result = self.check_for_warnings(sensor, value, unit)

                # If a warning is triggered, display it using st.toast()
                if not result:
                    st.toast(f"{room}: " + text, icon="🚨")  # Display warning with an alert icon

# Run the dashboard
if __name__ == "__main__":
    # Initialize the sensors_data structure
    data = sensor_data.Sensor_Data().data
    Dashboard(data)
