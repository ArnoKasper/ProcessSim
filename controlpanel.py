"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
from typing import cast, Dict, List, Optional, Tuple, Type, Generator, ClassVar
from generalfunctions import GeneralFunctions
import exp_paramaters as parameters
from simpy import FilterStore, PriorityResource


class ModelPanel(object):
    def __init__(self, experiment_number: int, simulation: ClassVar) -> None:
        self.experiment_number: int = experiment_number
        self.sim: ClassVar = simulation
        self.print_info: bool = True
        self.params_list: List[...] = parameters.experimental_params_list
        self.project_name: str = "Na"
        self.experiment_name: str = "Na"
        self.general_functions: GeneralFunctions = GeneralFunctions(simulation=self.sim)

        # general variables and experimental factors
        # simulation parameters-----------------------------------------------------------------------------------------
        self.WARM_UP_PERIOD: int = 3000    # warm-up period simulation model
        self.RUN_TIME: int = 10000         # run time simulation model
        self.NUMBER_OF_RUNS: int = 10#0     # number of replications

        # Manufacturing process and order characteristics---------------------------------------------------------------
        self.NUMBER_OF_WORKCENTRES: int = 6
        self.MANUFACTURING_FLOOR_LAYOUT: List[str, ...] = []
        for i in range(0, self.NUMBER_OF_WORKCENTRES):
            self.MANUFACTURING_FLOOR_LAYOUT.append(f'WC{i}')

        self.ORDER_POOL: FilterStore = FilterStore(self.sim.env)
        self.ORDER_QUEUES: Dict[...] = {}
        self.MANUFACTURING_FLOOR: Dict[...] = {}  # The manufacturing floor floor
        self.NUMBER_OF_MACHINES: int = 1

        for i, WorkCentre in enumerate(self.MANUFACTURING_FLOOR_LAYOUT):
            self.ORDER_QUEUES[WorkCentre]: FilterStore = FilterStore(self.sim.env)
            self.MANUFACTURING_FLOOR[WorkCentre]: PriorityResource = \
                PriorityResource(self.sim.env, capacity=self.NUMBER_OF_MACHINES)

        # Manufacturing model configuration
        """
        Options for the configuration of flows:
            1. GFS: general flow shop
            2. RJS: random job shop
            3. PFS: pure flow shop
            4. PJS: pure job shop 
        """
        self.WC_AND_FLOW_CONFIGURATION: str = 'GFS'  # 'RJS'

        # process and arrival times
        """
        process time distribution versions
            - lognormal:    Lognormal Distribution
                - truncation at 8
                - truncation at "inf"
            - 2_erlang:     2-Erlang Distribution 
            - constant:     constant process time value
        """
        self.PROCESS_TIME_DISTRIBUTION: str = "2_erlang"
        self.AIMED_UTILIZATION: float = 0.9
        self.MEAN_PROCESS_TIME: int = 1  # mean process time for this simulation
        self.STD_DEV_PROCESS_TIME: int = 1  # Standard deviation for this simulation
        self.TRUNCATION_POINT_PROCESS_TIME: int = 4  # "inf"  # Truncation point process time
        # Calculate mean time between arrival
        # (mean amount of machines/amount of machines/utilization * 1 / amount of machines)

        self.MEAN_TIME_BETWEEN_ARRIVAL: float = \
            self.general_functions.arrival_time_calculator(
                      wc_and_flow_config=self.WC_AND_FLOW_CONFIGURATION,
                      manufacturing_floor_layout=self.MANUFACTURING_FLOOR_LAYOUT,
                      aimed_utilization=self.AIMED_UTILIZATION,
                      mean_process_time=self.MEAN_PROCESS_TIME,
                      number_of_machines=self.NUMBER_OF_MACHINES,
                      cv=1)

        # Used for workload calculations
        self.PROCESSED: Dict[str, float] = {}  # Keeps record of the processed orders/load
        self.RELEASED: Dict[str, float] = {}  # Keeps record of the released orders/load

        for WC in self.MANUFACTURING_FLOOR_LAYOUT:
            self.PROCESSED[WC] = 0.0
            self.RELEASED[WC] = 0.0

        # Activate the appropriate data collection methods -------------------------------------------------------------
        self.COLLECT_BASIC_DATA: bool = True
        self.COLLECT_STATION_DATA: bool = False
        self.COLLECT_ORDER_DATA: bool = False

        # Control how the model is used
        self.EXPERIMENT_MANAGER: bool = True
        self.NON_STATIONARY_CONTROL: bool = False
        self.CUSTOM_CONTROL: bool = True

class PolicyPanel(object):
    def __init__(self, experiment_number: int) -> None:
        self.experiment_number: int = experiment_number
        self.params_list: List[...] = parameters.experimental_params_list

        # customer enquiry management - Due Date determination ---------------------------------------------------------
        """
        - key for the due date procedure
            -   random: adds a random Due Date with a uniform continuous distribution
                    Location: GeneralFunctions.random_value_DD
        
            -   factor_k: adds a due date following the factor K approach
                    Location: GeneralFunctions.random_value_DD
        
            -   constant: adds a constant due date to the cumulative process time
                    Location: GeneralFunctions.add_contant_DD 
            
            - total_work_content: mutiplies the process time with a constant
                    Location: GeneralFunctions.total_work_content
        """

        self.due_date_method: str = 'total_work_content'
        self.DD_random_min_max: List[int, int] = [28, 36]  # Due Dates intervals
        self.DD_factor_K_value: int = 12  # Due Date factor K
        self.DD_constant_value: int = 20  # Due Date adding constant
        self.DD_total_work_content_value: int = 10

        # Release control ----------------------------------------------------------------------------------------------
        """
            Key for the release control 
                Workload Control options
                -   LUMS_COR: combines both periodic and continuous release
                -   pure_periodic: adds a due date following the factor K approach
                -   pure_continuous: adds a constant due date to the cumulative process time
        
                Other options
                -   CONWIP: Constant Work In Process
                -   CONLOAD: Constant Workload In Process
                
            Release sequencing rules 
                - FCFS
                - PRD
                - SPT
            """
        # Sequencing rules
        self.sequencing_rule: str = "PRD"
        self.PRD_k: int = 6  # Factor K for PRD calculations

        # release control method
        self.release_control: bool = False
        self.release_norm: int = 8
        self.release_control_method: str = "LUMS_COR"

        # LUMS COR
        self.check_period: float = 4  # Periodic release time
        self.continuous_trigger: int = 0  # determine the trigger for continuous release

        # Dispatching rules --------------------------------------------------------------------------------------------
        """
        Dispatching rules available
            - FCFS
            - SPT
            - OOD, k 
            - ODD, following Land et al. (2014)
        """
        # Dispatching rules
        self.dispatching_rule: str = "ODD"  # "SPT"
        self.ODD_k: int = 7
