"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
# set code and import libraries ----------------------------------------------------------------------------------------
from simpy import Environment, FilterStore, PriorityResource, Event
from random import Random
import numpy as np
from scipy import stats
from typing import cast, Dict, List, Optional, Tuple, Type, Generator

#Generator[yield_type, send_type, return_type]

# Import files for simulation experiments ------------------------------------------------------------------------------
from controlpanel import ModelPanel, PolicyPanel
from data_collection_and_storage import DataCollection, DataStorageRun, DataStorageExp
from generalfunctions import GeneralFunctions
from simsource import Source
from process import Process
from customizedsettings import CustomizedSettings
from releasecontrol import ReleaseControl

class SimulationModel(object):
    """
    class containing the simulation model function
    the simulation instance (i.e. self) is passed in the other function outside this class as sim
    """

    def __init__(self, exp_number: int = 1) -> None:
        # setup general params
        self.exp_number: int = exp_number
        self.warm_up: bool = True

        # Set seed for specifically process times and other random generators
        self.random_generator: Random = Random()
        self.random_generator.seed(999999)

        # import the Simpy environment
        self.env: Environment = Environment()

        # add general functionality to the model
        self.general_functions: GeneralFunctions = GeneralFunctions(simulation=self)

        # get the model and policy control panel
        self.model_panel: ModelPanel = ModelPanel(experiment_number=self.exp_number, simulation=self)
        self.policy_panel: PolicyPanel = PolicyPanel(experiment_number=self.exp_number)
        self.print_info: bool = self.model_panel.print_info

        # get the data storage variables
        self.data_run: DataStorageRun = DataStorageRun(sim=self)
        self.data_exp: DataStorageExp = DataStorageExp(sim=self)

        # add data clearing methods
        self.data_collection: DataCollection = DataCollection(simulation=self)

        # import source
        self.source: Source = Source(simulation=self)

        # import release control
        self.release_control: ReleaseControl = ReleaseControl(simulation=self)

        # import process
        self.process: Process = Process(simulation=self)

        # add the customized settings
        self.customized_settings: CustomizedSettings = CustomizedSettings(simulation=self)

        # declare variables
        self.release_periodic: any = "declare"
        self.source_process: any = "declare"
        self.run_manager: any = "declare"

    # the actual simulation function with all required SimPy settings---------------------------------------------------
    def sim_function(self) -> None:
        """
        initialling and timing of the generator functions
        :return: void
        """
        # activate release control
        if self.policy_panel.release_control:
            if self.policy_panel.release_control_method == "LUMS_COR" or \
                    self.policy_panel.release_control_method == "pure_periodic":
                self.release_periodic: Process[Event, None, None] = \
                    self.env.process(self.release_control.periodic_release())

        # initialize processes
        self.source_process: Process[Event, None, None] = self.env.process(self.source.generate_random_arrival_exp())

        # activate data collection methods
        if self.model_panel.COLLECT_BASIC_DATA or \
                self.model_panel.COLLECT_ORDER_DATA:
            self.run_manager: Process[Event, None, None] = self.env.process(SimulationModel.run_manager(self))

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

    def run_manager(self) -> Generator[Event, None, None]:
        """
        The run manager managing processes during the simulation. Can perform the same actions in through cyclic
        manner. Currently, the run_manager managers printing information and the saving and processing of information.
        :return: void
        """
        while self.env.now < (
                self.model_panel.WARM_UP_PERIOD + self.model_panel.RUN_TIME) * self.model_panel.NUMBER_OF_RUNS:
            yield self.env.timeout(self.model_panel.WARM_UP_PERIOD)
            # chance the warm_up status
            self.warm_up = True

            # print run info if required
            if self.print_info:
                self.print_warmup_info()

            # update data
            self.data_collection.run_update(warmup=self.warm_up)

            yield self.env.timeout(self.model_panel.RUN_TIME)
            # chance the warm_up status
            self.warm_up = False

            # update data
            self.data_collection.run_update(warmup=self.warm_up)

            # print run info if required
            if self.print_info and self.model_panel.COLLECT_BASIC_DATA:
                self.print_run_info()

    # function that print information to the console
    def print_start_info(self) -> None:
        print("Simulation starts")
        print(f"Mean time between arrival: {self.model_panel.MEAN_TIME_BETWEEN_ARRIVAL}")
        return

    def print_warmup_info(self) -> None:
        return print('Warm-up period finished')


    def print_run_info(self) -> None:
        # vital simulation results are given
        run_number = int(self.env.now / (self.model_panel.WARM_UP_PERIOD + self.model_panel.RUN_TIME))
        index = run_number - 1

        # make progress bar
        progress = "["
        step = 100/self.model_panel.NUMBER_OF_RUNS

        for i in range(1, 101):
            if run_number * step > i:
                progress = progress + "="
            elif run_number * step == i:
                progress = progress + ">"
            else:
                progress = progress + "."
        progress = progress + f"] {round(run_number/self.model_panel.NUMBER_OF_RUNS*100,2)}%"

        # compute replication confidence
        current_sum = self.data_exp.database.loc[:,"mean_throughput_time"].sum()
        current_variance = self.data_exp.database.loc[:,"mean_throughput_time"].var()
        confidence_int = current_sum - stats.t.ppf(1-0.025,df=self.data_exp.database.shape[0]-1) *\
                         (current_variance / np.sqrt(run_number))
        deviation = f"replication confidence: p < {round((current_sum - confidence_int) /current_sum*100, 6)}%"
        print(f"run number {run_number}", progress, deviation)

        # print info
        print(self.data_exp.database.iloc[index:,[0,2,3,4,7,9,10,11,
                                                  *range(13, self.data_exp.database.shape[1])]].to_string(index=False))
        return

    def print_end_info(self) -> None:
        print("Simulation ends")
        return
