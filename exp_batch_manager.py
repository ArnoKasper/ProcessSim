"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""

import exp_manager
import time

# Track run time
start_time = time.time()

# Set the range of the experiments that needs to be run
lower_limit = 0
upper_limit = 0

# Activate the simulation (Automatic model)
exp_manager.Experiment_Manager(lower_limit, upper_limit)

# provide essential experimental information
t_time = (time.time() - start_time)
t_hours = t_time // 60 // 60
t_min = (t_time - (t_hours * 60 * 60)) // 60
t_seconds = (t_time - (t_min * 60) - (t_hours * 60 * 60))

print(f"\n\nExperiment {lower_limit} till {upper_limit} are finished"
      f"\nThe total run time"
      f"\n\tHours:      {t_hours}"
      f"\n\tMinutes:    {t_min}"
      f"\n\tSeconds:    {round(t_seconds, 2)}")
