# Project Name

# Description
An interactive Streamlit App to visualize Sensor Data from Multisensors.

To install and set up the project, follow these steps:

# Clone the repository
`git clone https://github.com/Caroline-Sophie/Multisensor_Dashboard.git`

`cd <your-repository>`

# Setup Instructions

To ensure that you do not interfere with system packages and to avoid issues related to dependency management, **it is highly recommended to create and use a virtual environment** for this project.

### Create a virtual environment:

   In your project directory, run:

   ```bash
   python3 -m venv venv
  ```

### Activating the Virtual Environment

Also in your project directory, run:
- **On macOS/Linux**:
     ```bash
     source venv/bin/activate
     ```

- **On Windows**:
     ```bash
     .\venv\Scripts\activate
     ```

Once activated, your terminal prompt will change to show the name of the virtual environment (`venv`) indicating that it's now active. You can now safely install dependencies and run your project without affecting your system Python installation.

To deactivate the virtual environment, simply run:
   ```bash
  deactivate
  ```

# Install dependencies
`pip install -r requirements.txt`

# Usage
Before usage, you need to add the required API tokens and passwords to the secrets.toml
To run the project, use the following command:
Make sure that you are in the project directory 

`streamlit run app.py`


# Project Structure
```
repository/
├── app.py             # Streamlit dashboard handling UI, logic, and data retrieval
├── src/               # core directory of the project
│   ├── influx_db_data.py  # Queries historical data from InfluxDB
│   ├── sensor_data.py  # Fetches real-time sensor data from HomeAssistant API
├── media/             # Stores floor plan image and company logo
├── training_data/     # Contains training data for future AI models
├── requirements.txt   # Dependency list
├── README.md          # Documentation
├── secrets.toml       # stores secrets that should not be found in the code
```

# Contributing

If you would like to contribute, please fork the repository and submit a pull request.

