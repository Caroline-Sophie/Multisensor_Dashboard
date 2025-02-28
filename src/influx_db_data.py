"""
This module contains the InfluxDB class that facilitates interaction with an InfluxDB database.

The InfluxDB class is responsible for:
1. Establishing a connection to the InfluxDB instance.
2. Fetching historical sensor data from the InfluxDB.
3. Updating a provided dictionary with historical data retrieved from the InfluxDB.

The module requires access to InfluxDB credentials, which can be stored in environment variables or a secrets management service like Streamlit secrets.

Classes:
    - InfluxDB: A class for connecting to InfluxDB and querying sensor data.

Methods:
    - __init__: Initializes the InfluxDB connection.
    - get_connection: Establishes the connection to the InfluxDB instance.
    - get_historic_sensor_data: Fetches historical data for sensors and updates a given dictionary.
"""

from datetime import datetime
from influxdb import InfluxDBClient
import streamlit as st

class InfluxDB:
    """
        A class to interact with an InfluxDB instance and fetch historical sensor data.

        This class provides methods to connect to an InfluxDB database and retrieve
        sensor data. It allows querying the database for historical data starting from
        the beginning of the current day and updates a provided dictionary with the retrieved data.

        Attributes:
            client (InfluxDBClient): The InfluxDB client used to interact with the database.

        Methods:
            __init__: Initializes the InfluxDB connection by creating a client instance.
            get_connection: Establishes a connection to the InfluxDB instance using the provided secrets.
            get_historic_sensor_data: Fetches historical sensor data starting from today and updates the provided dictionary.
        """

    def __init__(self):
        """
        Initializes the InfluxDB connection by creating a client instance.

        This method calls the get_connection() method to establish a connection
        to the InfluxDB and stores the client object for later use.
        """
        self.client = self.get_connection()

    def get_connection(self):
        """
        Establishes a connection to the InfluxDB instance.

        Returns:
            InfluxDBClient: A client object that allows interaction with the InfluxDB database.
        """

        st.secrets.file_change_listener()
        # Access InfluxDB secrets (e.g., using Streamlit secrets or environment variables)
        host = st.secrets["influxdb"]["host"]
        port = st.secrets["influxdb"]["port"]
        username = st.secrets["influxdb"]["username"]
        password = st.secrets["influxdb"]["password"]
        dbname = st.secrets["influxdb"]["dbname"]


        # Create a connection to the InfluxDB instance
        client = InfluxDBClient(host, port, username, password, dbname)  # Example host and port
        return client

    def get_historic_sensor_data(self, data_dict=None):
        """
        Fetches historical sensor data from InfluxDB and updates the provided data dictionary.

        The method queries the InfluxDB to retrieve sensor data starting from the beginning of the current day
        and updates the dictionary with the retrieved historical data.

        Parameters:
            data_dict (dict): A dictionary containing sensor data to be updated.

            The structure of `data_dict`:
            data_dict = {
                "entity_id": {
                    "room": ,
                "sensors": {
                    sensor_name: {
                        "unit": Unit of the sensor
                        "id": Sensor ID
                        "current_value":  Current value
                        "history": History of readings
                        "warnings":  Warnings related to the sensor
                    }
                },
                "volume":
                }
            }

        Returns:
            None: The function updates the provided data dictionary in-place with historical data.
        """
        # Iterate through each entity in the data dictionary
        for entity_id, sensor_info in data_dict.items():

            # Iterate through each sensor in the entity
            for sensor, details in sensor_info["sensors"].items():
                unit = details["unit"]  # Extract the unit of measurement for the sensor

                # Get the start of today in UTC (formatted in ISO 8601 format)
                start_of_today = datetime.utcnow().strftime('%Y-%m-%dT06:00:00Z')

                # Build the InfluxDB query to retrieve historical data for the sensor
                query = f"""
                    SELECT time, entity_id, value FROM "{unit}" 
                    WHERE "entity_id" = '{entity_id}{details["id"]}' 
                    AND time >= '{start_of_today}'
                    ORDER BY time ASC
                """

                # Execute the query to fetch the historical data from InfluxDB
                result = self.client.query(query)

                # Process the results from the query
                points = list(result.get_points())  # Convert the result to a list of data points
                if points:
                    entity_data_found = True  # Data was found for this sensor
                    for point in points:
                        time = point['time']  # Timestamp of the data point
                        value = point['value']  # Value of the sensor at the given time

                        # Append the historical data to the sensor's history in the data dictionary
                        data_dict[entity_id]["sensors"][sensor]["history"].append((value, time))