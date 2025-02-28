from influxdb import InfluxDBClient


class InfluxDB():
    def __init__(self):
        self.client = self.get_connection()

    def get_connection(self):  # connecting with the InfluxDB
        username = "api_user_2"  # 'home_assistant'
        password = "92rPV3K5hdU7"  # 'home_assistant'
        dbname = "home_assistant"  # 'home_assistant'
        client = InfluxDBClient('10.42.2.20', 8086, username, password, dbname)  # host = 'homeassistant.local'
        return client

    def get_historic_sensor_data(self, data_dict=None):  # gets the historic sensordata and updates the dictionary
        # Multisensor 115 - Conference-Space
        # Multisensor 108 - zwischen Conference-Space und Robot-Space
        # Multisensor 107 - Robot-Space
        # Multisensor 114 - Empfang
        # Multisensor 110 - zwischen Empfang und Focus-Space
        # Multisensor 109 - Focus-Space
        # Multisensor 104 - Experience-Hub
        # Multisensor 106 - Design-Thinking-Space
        # Multisensor 111 - Co-Working-Space (Left in Picture)
        # Multisensor 103 - Co-Working-Space ( Right in Picture)
        # Multisensor 113 - Social Lounge
        # Multisensor 112 - Hallway
        # Multisensor 105 - 3D Printing-Space

        # List of entity names to query
        entities = [
            "multisensor_115",
            "multisensor_108",
            "multisensor_107",
            "multisensor_114",
            "multisensor_110",
            "multisensor_109",
            "multisensor_104",
            "multisensor_106",
            "multisensor_111",
            "multisensor_103",
            "multisensor_113",
            "multisensor_112",
            "multisensor_105"
        ]

        multisensor_sensors = [
            ['% rel.', ''],  # ?
            ['ADC-Value', ''],  # ?
            ['IAQ', ''],  # ?
            ['W', ''],  # ?
            ['cm', ''],  # ?
            ['lux', ''],  # ?
            ['m', ''],  # ?
            ['mbar', ''],  # ?
            ['ms', ''],  # ?
            ['%', '_humidity'],
            ['°C', '_temperature'],
            ['ppm', '_scd30_co2'],
            ['ppm', '_scd30_co2'],
            ['IAQ', '_bme680_iaq'],
            ['K', '_apds9960_color_temperature'],
            ['UVI', '_ltr390_uv_index'],
            ['V', '_microphone_voltage'],
            ['Volume', '_microphone_noise_level'],
            ['hPa', '_bme680_pressure'],
            ['lx', '_ltr390_light'],
            ['Ω', '_bme680_gas_resistance'],
        ]

        for entity in entities:
            entity_data_found = False
            print(f"Entity: {entity}")
            for sensor in multisensor_sensors:
                # Construct query for partial entity match and measurement
                query = f"""
                SELECT time, entity_id, value FROM "{sensor[0]}" 
                WHERE "entity_id" = /{entity}{sensor[1]}/ 
                ORDER BY time DESC LIMIT 10
                """
                result = self.client.query(query)

                # Process and print the result for the current entity and measurement
                points = list(result.get_points())
                if points:
                    entity_data_found = True
                    print(f"  Measurement '{sensor[0]}':")
                    for point in points:
                        time = point['time']
                        value = point['value']

                        # update the data_dictionary
                        sensor_data = data_dict[entity]["sensors"][sensor[0]]
                        sensor_data["history"].append((value, time))

                        print(f"    {point}")

                if not entity_data_found:
                    print("  No data found for any measurements.")


if __name__ == '__main__':
    db = InfluxDB()
    db.get_historic_sensor_data()