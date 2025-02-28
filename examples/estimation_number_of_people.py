#Estimation based on CO₂ Concentration
#Inputs: Current CO₂ concentration, baseline CO₂, room volume, emission rate per person - standard CO₂ emission rates (~18 L/h per person).
###########################################################################################################################################

def estimate_people_co2(current_co2, baseline_co2, room_volume, emission_rate=18, time_elapsed=3600):
    """
    Estimate the number of people in a room using CO₂ concentration.
    
    Parameters:
        current_co2 (float): Current CO₂ concentration in ppm.
        baseline_co2 (float): Baseline CO₂ concentration (empty room) in ppm.
        room_volume (float): Volume of the room in cubic meters.
        emission_rate (float): CO₂ emission rate per person in L/hour (default ~18).
        time_elapsed (float): Time elapsed since measurement in seconds.
    
    Returns:
        float: Estimated number of people.
    """
    co2_diff = current_co2 - baseline_co2  # ppm
    co2_produced = co2_diff * room_volume / 1000  # Convert ppm to liters
    people_count = co2_produced / (emission_rate * (time_elapsed / 3600))  # Convert time to hours
    return max(0, people_count)  # Ensure non-negative count

# Example usage
current_co2 = 600  # ppm
baseline_co2 = 400  # ppm
room_volume = 50  # m³
print(f"Estimated People (CO2): {estimate_people_co2(current_co2, baseline_co2, room_volume):.2f}")


################################################################################################################################

# Estimation based on Microphone Noise Level
# Inputs: Baseline noise level, current noise level. Measure sound levels in a quiet room and adjust the scaling factor based on observed activity.

################################################################################################################################

def estimate_people_noise(current_noise_level, baseline_noise_level, scaling_factor=1.5):
    """
    Estimate the number of people in a room using noise levels.
    
    Parameters:
        current_noise_level (float): Current noise level (e.g., volume).
        baseline_noise_level (float): Baseline noise level in the empty room.
        scaling_factor (float): Empirical scaling factor for mapping noise to people.
    
    Returns:
        float: Estimated number of people.
    """
    noise_ratio = current_noise_level / baseline_noise_level
    people_count = (noise_ratio - 1) * scaling_factor
    return max(0, people_count)

# Example usage
current_noise_level = 60  # dB
baseline_noise_level = 30  # dB
print(f"Estimated People (Noise): {estimate_people_noise(current_noise_level, baseline_noise_level):.2f}")



################################################################################################################################

# Estimation based on Detection Distance (LD2410) and TOF Distance
#Inputs: Detection events, TOF distances to confirm direction. Use repeated tests to ensure accurate counting for entry and exit.

################################################################################################################################

class PeopleCounter:
    def __init__(self):
        self.people_count = 0

    def process_event(self, event_type):
        """
        Process an entry or exit event.
        
        Parameters:
            event_type (str): Either 'entry' or 'exit'.
        """
        if event_type == "entry":
            self.people_count += 1
        elif event_type == "exit":
            self.people_count -= 1
        self.people_count = max(0, self.people_count)  # Ensure non-negative count

# Example usage
counter = PeopleCounter()
counter.process_event("entry")
counter.process_event("exit")
print(f"Estimated People (Detection): {counter.people_count}")


################################################################################################################################

# Estimation based on IAQ
#Inputs: Current IAQ, baseline IAQ.Establish a proportional relationship between IAQ changes and occupancy.

################################################################################################################################

def estimate_people_iaq(current_iaq, baseline_iaq, scaling_factor=2.0):
    """
    Estimate the number of people in a room using IAQ.
    
    Parameters:
        current_iaq (float): Current IAQ index.
        baseline_iaq (float): Baseline IAQ index for an empty room.
        scaling_factor (float): Empirical scaling factor for mapping IAQ to people.
    
    Returns:
        float: Estimated number of people.
    """
    iaq_diff = current_iaq - baseline_iaq
    people_count = iaq_diff * scaling_factor
    return max(0, people_count)

# Example usage
current_iaq = 150  # IAQ index
baseline_iaq = 50  # IAQ index
print(f"Estimated People (IAQ): {estimate_people_iaq(current_iaq, baseline_iaq):.2f}")



################################################################################################################################

# Estimation with combination of different sensors 
#Inputs: Current IAQ, baseline IAQ.Establish a proportional relationship between IAQ changes and occupancy.

################################################################################################################################

import numpy as np

# Input Data
co2_values = [1023.1, 1304.2, 1406.9, 1133.4, 982.8, 1015.7, 951.8, 811.7]  # ppm
noise_levels = [147.97, 109.07, 112.39, 163.8, 168.36, 273.01, 158.09, 152.94]  # Volume
temperatures = [28.59, 28.06, 28.71, 28.71, 27.01, 29.82, 29.01, 28.67]  # °C
humidities = [26.8, 25.4, 32.6, 26.9, 35.8, 23.7]  # %

# Constants
room_volume = 50  # m³
baseline_co2 = 400  # ppm
co2_production_rate = 18  # L/h/person
time_elapsed = 1  # hour

baseline_noise = 40  # Volume
noise_scaling_factor = 1.5

baseline_temp = 22  # °C
baseline_humidity = 40  # %
temp_factor = 0.5
humidity_factor = 1.0

# CO2-based Estimate
avg_co2 = np.mean(co2_values)
co2_diff = avg_co2 - baseline_co2
co2_people = (co2_diff * room_volume) / (co2_production_rate * time_elapsed)

# Noise-based Estimate
avg_noise = np.mean(noise_levels)
noise_people = noise_scaling_factor * (avg_noise / baseline_noise)

# Temp & Humidity-based Estimate
avg_temp = np.mean(temperatures)
avg_humidity = np.mean(humidities)
temp_diff = avg_temp - baseline_temp
humidity_diff = avg_humidity - baseline_humidity
temp_humidity_people = (temp_diff * temp_factor) + (humidity_diff * humidity_factor)

# Sensor Fusion
weights = [0.4, 0.3, 0.3]  # Adjust as needed
final_people_count = (weights[0] * co2_people +
                      weights[1] * noise_people +
                      weights[2] * temp_humidity_people)

# Output Results
print(f"Estimated People (CO2): {co2_people:.2f}")
print(f"Estimated People (Noise): {noise_people:.2f}")
print(f"Estimated People (Temp & Humidity): {temp_humidity_people:.2f}")
print(f"Final Estimated People (Fusion): {final_people_count:.2f}")


