"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
# set code and import libraries ----------------------------------------------------------------------------------------
import simpy
import random

# Import files for simulation experiments ------------------------------------------------------------------------------
from control_panel import ModelPanel, PolicyPanel
from data_collection_and_storage import DataCollection, DataStorageRun, DataStorageExp
from general_functions import General_Functions
from sim_source import Source
from process import Process
from customized_settings import CustomizedSettings

class Simulation_Model(object):
    """
    class containing the simulation model function
    the simulation instance (i.e. self) is passed in the other function outside this class as sim
    """

    def __init__(self, exp_number=1):
        # setup general params
        self.exp_number = exp_number
        self.warm_up = True

        # Set seed for specifically process times and other random generators
        self.random_generator_1 = random.Random()  # For processing times
        self.random_generator_2 = random.Random()  # For other random processes
        self.random_generator_3 = random.Random()  # For inter arrival times
        self.random_generator_1.seed(999999)
        self.random_generator_2.seed(999999)
        self.random_generator_3.seed(999999)

        # import the Simpy environment
        self.env = simpy.Environment()

        # add the customized settings
        self.customized_settings = CustomizedSettings(simulation=self)

        # add general functionality to the model
        self.general_functions = General_Functions(simulation=self)

        # get the model and policy control panel
        self.model_panel = ModelPanel(experiment_number=self.exp_number, simulation=self)
        self.policy_panel = PolicyPanel(experiment_number=self.exp_number)
        self.print_info = self.model_panel.print_info

        # get the data storage variables
        self.data_run = DataStorageRun(sim=self)
        self.data_exp = DataStorageExp(sim=self)

        # add data clearing methods
        self.data_collection = DataCollection(simulation=self)

        # import source
        self.source = Source(simulation=self)

        # import process
        self.process = Process(simulation=self)

        # start the simulation
        self.release_control = "NA"
        self.release_periodic = "NA"
        self.source_process = "NA"
        self.run_manager = "NA"
        self.sim_function()

    # the actual simulation function with all required SimPy settings---------------------------------------------------
    def sim_function(self):
        # create queues and capacity sources
        for i, WorkCentre in enumerate(self.model_panel.MANUFACTURING_FLOOR_LAYOUT):
            self.model_panel.ORDER_QUEUES[WorkCentre] = simpy.FilterStore(self.env)
            self.model_panel.MANUFACTURING_FLOOR[WorkCentre] = \
                simpy.PriorityResource(self.env, capacity=self.model_panel.NUMBER_OF_MACHINES)

        # activate release control
        if self.policy_panel.release_control:
            self.model_panel.ORDER_POOL = simpy.FilterStore(self.env)
            import releasecontrol
            self.release_control = releasecontrol.ReleaseControl(simulation=self)

            # start periodic release
            if self.policy_panel.release_control_method == "LUMS_COR" or \
                    self.policy_panel.release_control_method == "pure_periodic":
                self.release_periodic = self.env.process(self.release_control.periodic_release())

        # initiate order arrival
        self.source_process = self.env.process(self.source.generate_random_arrival_exp())

        # activate data collection methods
        if self.model_panel.CollectBasicData or \
                self.model_panel.CollectPeriodicData or \
                self.model_panel.CollectOrderData or \
                self.model_panel.CollectDiscreteData:
            self.run_manager = self.env.process(Simulation_Model.run_manager(self))

        # set the the length of the simulation (add one extra time unit to save result last run)
        if self.print_info:
            self.print_start_info()

        # start simulation
        sim_time = (self.model_panel.WARM_UP_PERIOD + self.model_panel.RUN_TIME) * \
                   self.model_panel.NUMBER_OF_RUNS + 0.001
        self.env.run(until=sim_time)

        # simulation finished, print final info
        if self.print_info:
            self.print_end_info()

    def run_manager(self):
        while self.env.now < (
                self.model_panel.WARM_UP_PERIOD + self.model_panel.RUN_TIME) * self.model_panel.NUMBER_OF_RUNS:
            yield self.env.timeout(self.model_panel.WARM_UP_PERIOD)
            # chance the warm_up status
            self.warm_up = False

            # print run info if required
            if self.print_info:
                self.print_warmup_info()

            # remove warm-up period data collection
            if self.model_panel.CollectBasicData:
                self.update_run_data()

            if self.model_panel.CollectOrderData:
                self.data_exp = DataStorageExp(sim=self)

            yield self.env.timeout(self.model_panel.RUN_TIME)
            # chance the warm_up status
            self.warm_up = True

            # activate data collection
            if self.model_panel.CollectBasicData:
                # store the run data
                self.data_collection.basic_data_storage()

                # clear the run data
                self.update_run_data()

            # activate the periodic monitoring process if applicable
            if self.model_panel.CollectPeriodicData:
                self.data_collection.periodic_data_collection()
                raise Exception("periodic data collection not implemented")

            # print run info if required
            if self.print_info and self.model_panel.CollectBasicData:
                self.print_run_info()

    def update_run_data(self):
        self.data_run = DataStorageRun(self)
        return

    # function that print information to the console
    def print_start_info(self):
        print("Simulation starts")
        print(f"Mean time between arrival: {self.model_panel.MEAN_TIME_BETWEEN_ARRIVAL}")
        return

    def print_warmup_info(self):
        return print(f'Warm-up period finished')

    def print_run_info(self):
        # Vital simulation results are given
        run_number = int(self.env.now / (self.model_panel.WARM_UP_PERIOD + self.model_panel.RUN_TIME))
        index = run_number - 1

        # print info
        print(
            f'Run number: {run_number}'
            f'\nResults for this run:'
            f'\n\tMean lead time:                     {self.data_exp.Dat_exp_GrossThroughputTime_mean[index]}'
            f'\n\tVariance lead time:                 {self.data_exp.Dat_exp_GrossThroughputTime_var[index]}'
            f'\n\tMean shop throughput time:          {self.data_exp.Dat_exp_ThroughputTime_mean[index]}'
            f'\n\t% Tardy:                            {round(self.data_exp.Dat_exp_percentageTardy[index], 6) * 100}%'
            f'\n\tMean Tardiness:                     {self.data_exp.Dat_exp_Tardiness_mean[index]}'
            f'\n\tMean Lateness:                      {self.data_exp.Dat_exp_Lateness_mean[index]}'
            f'\n\tUtilization:                        {round(self.data_exp.Dat_expUtilization[index], 6)}%'
        )

        # print additional info for LUMS_COR release
        if self.policy_panel.release_control_method == "LUMS_COR" and self.policy_panel.release_control:
            print(f'\tContinuous trigger LUMSCOR number:  {self.data_exp.Dat_exp_ConLUMSCOR[index]} times')

        return

    def print_end_info(self):
        print("Simulation ends")
        return
