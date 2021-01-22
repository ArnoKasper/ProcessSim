"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
# set code and import libraries ----------------------------------------------------------------------------------------
from __future__ import annotations
from simpy import Environment, FilterStore, PriorityResource, Event
from random import Random
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

        # add the customized settings
        self.customized_settings: CustomizedSettings = CustomizedSettings(simulation=self)

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
                #print("PERIODIC RELEASE OFF")

        # initialize processes
        self.source_process: Process[Event, None, None] = self.env.process(self.source.generate_random_arrival_exp())

        # activate data collection methods
        if self.model_panel.COLLECT_BASIC_DATA or \
                self.model_panel.COLLECT_PERIODIC_DATA or \
                self.model_panel.COLLECT_ORDER_DATA or \
                self.model_panel.COLLECT_DISCRETE_DATA:
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
            self.warm_up = False

            # print run info if required
            if self.print_info:
                self.print_warmup_info()

            # remove warm-up period data collection
            if self.model_panel.COLLECT_BASIC_DATA:
                self.data_run: DataStorageRun = DataStorageRun(sim=self)

            if self.model_panel.COLLECT_ORDER_DATA:
                self.data_exp: DataStorageExp = DataStorageExp(sim=self)

            yield self.env.timeout(self.model_panel.RUN_TIME)
            # chance the warm_up status
            self.warm_up = True

            # activate data collection
            if self.model_panel.COLLECT_BASIC_DATA:
                # store the run data
                self.data_collection.basic_data_storage()

                # clear the run data
                self.data_run: DataStorageRun = DataStorageRun(sim=self)

            # activate the periodic monitoring process if applicable
            if self.model_panel.COLLECT_PERIODIC_DATA:
                self.data_collection.periodic_data_collection()
                raise Exception("periodic data collection not implemented")

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

    def print_end_info(self) -> None:
        print("Simulation ends")
        return
