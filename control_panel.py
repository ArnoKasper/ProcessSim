"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
import general_functions
import exp_paramaters as paramaters

class ModelPanel(object):
    def __init__(self, experiment_number, simulation):
        self.experiment_number = experiment_number
        self.sim = simulation
        self.print_info = True
        self.params_list = paramaters.experimental_params_list
        self.project_name = "XXXX"
        self.experiment_name = "XXXX"
        self.general_functions = general_functions.General_Functions(simulation=self.sim)

        # general variables and experimental factors
        # simulation parameters-----------------------------------------------------------------------------------------
        self.WARM_UP_PERIOD = 3000    # warm-up period simulation model
        self.RUN_TIME = 10000         # run time simulation model
        self.NUMBER_OF_RUNS = 10#00     # number of replications

        # Manufacturing process and order characteristics---------------------------------------------------------------
        self.NUMBER_OF_WORKCENTRES = 6
        self.MANUFACTURING_FLOOR_LAYOUT = list()
        for i in range(0, self.NUMBER_OF_WORKCENTRES):
            string_wc = "WC" + str(i)
            self.MANUFACTURING_FLOOR_LAYOUT.append(string_wc)
        self.ORDER_POOL = dict()  # The order pool
        self.ORDER_QUEUES = dict()
        self.MANUFACTURING_FLOOR = dict()  # The manufacturing floor floor
        self.NUMBER_OF_MACHINES = int(1)

        # Manufacturing model configuration
        """
        Options for the configuration of flows:
            1. GFS: general flow shop
            2. RJS: random job shop
            3. PFS: pure flow shop
            4. PJS: pure job shop 
        """
        self.WC_AND_FLOW_CONFIGURATION = 'GFS'  # 'RJS'

        # process and arrival times
        """
        process time distribution versions
            - lognormal:    Lognormal Distribution
                - truncation at 8
                - truncation at "inf"
            - 2_erlang:     2-Erlang Distribution 
            - constant:     constant process time value (which is the mean)
        """
        self.PROCESS_TIME_DISTRIBUTION = "2_erlang"
        self.AIMED_UTILIZATION = 0.9
        self.MEAN_PROCESS_TIME = 1  # mean process time for this simulation
        self.STD_DEV_PROCESS_TIME = 1  # Standard deviation for this simulation
        self.TRUNCATION_POINT_PROCESS_TIME = 4  # "inf"  # Truncation point process time
        # Calculate mean time between arrival
        # (mean amount of machines/amount of machines/utilization * 1 / amount of machines)

        self.MEAN_TIME_BETWEEN_ARRIVAL = \
            self.general_functions.arrival_time_calculator(
                      wc_and_flow_config=self.WC_AND_FLOW_CONFIGURATION,
                      manufacturing_floor_layout=self.MANUFACTURING_FLOOR_LAYOUT,
                      aimed_utilization=self.AIMED_UTILIZATION,
                      mean_process_time=self.MEAN_PROCESS_TIME,
                      number_of_machines=self.NUMBER_OF_MACHINES,
                      cv=1)

        # Used for workload calculations
        self.PROCESSED = {}  # Keeps record of the processed orders/load
        self.RELEASED = {}  # Keeps record of the released orders/load

        # tracking variables for machine selection rules
        self.ALTMachineSelectDict = {}
        self.LWQMachineSelectDict = {}

        # Machine number allocate
        self.Machine_number = {}

        for WC in self.MANUFACTURING_FLOOR_LAYOUT:
            self.PROCESSED[WC] = 0
            self.RELEASED[WC] = 0
            self.Machine_number[WC] = 1

            # add the tracking variables for the machine selection rules
            machine_list = []

            for _ in range(0, self.NUMBER_OF_MACHINES):
                machine_list.append(0)

            self.ALTMachineSelectDict[WC] = machine_list
            self.LWQMachineSelectDict[WC] = machine_list

        # detailed performance analysis functionality ------------------------------------------------------------------
        self.processedOrders = {}  # Keeps record of the orders released
        self.releasedOrders = {}  # Keeps record of the orders processed

        # Activate the appropriate data collection methods
        self.CollectBasicData = True
        self.CollectStationData = False
        self.CollectFlowData = False
        self.CollectOrderData = False
        self.CollectMachineData = False
        self.CollectPeriodicData = False
        self.CollectPeriodicData_time_interval = 0.2
        self.CollectDiscreteData = False

        # Control how the model is used
        self.EXPERIMENT_MANAGER = True
        self.AGENT_CONTROL = False
        self.NON_STATIONARY_CONTROL = False


class PolicyPanel(object):
    def __init__(self, experiment_number):
        self.experiment_number = experiment_number
        self.params_list = paramaters.experimental_params_list

        # customer enquiry management - Due Date determination ---------------------------------------------------------
        """
        - key for the due date procedure
            -   random: adds a random Due Date with a uniform continuous distribution
                    Location: General_functions.random_value_DD
        
            -   factor_k: adds a due date following the factor K approach
                    Location: General_functions.random_value_DD
        
            -   constant: adds a constant due date to the cumulative process time
                    Location: General_functions.add_contant_DD 
            
            - total_work_content: mutiplies the process time with a constant
                    Location: General_functions.total_work_content
        """

        self.due_date_method = 'total_work_content'
        self.RVminmax = [28, 36]  # Due Dates intervals
        self.FactorKValue = 12  # Due Date factor K
        self.AddContantDDValue = 20  # Due Date adding constant
        self.total_work_content_value = 10 #self.params_list[self.experiment_number][2]

        # Release control ----------------------------------------------------------------------------------------------
        """
            Key for the release control 
                Workload Control options
                -   LUMS_COR: combines both periodic and continuous release
                        Location: Release_Control.periodic_release
                        Location: Release_Control.continous_trigger
        
                -   pure_periodic: adds a due date following the factor K approach
                        Location: Release_Control.periodic_release
        
                -   pure_continuous: adds a constant due date to the cumulative process time
                        Location: Release_Control.continuous_release
        
                Other options
                -   CONWIP: Constant Work In Process
                        Location: Release_Control.CONWIP
        
                -   CONLOAD: Constant Workload In Process
                        Location: Release_Control.CONLOAD
                
                Beta versions 
                -   control-novel-beta
            
            Release sequencing rules 
                - FCFS
                - PRD
                - SPT
                - Custom --> define
            """
        # Sequencing rules
        self.sequencing_rule = "PRD"
        self.PRD_k = 6  # Factor K for PRD calculations

        # release control method
        self.release_control = True
        self.release_norm = 5
        self.release_control_method = "LUMS_COR"

        # LUMS COR
        self.check_period = 4.0  # Periodic release time
        self.continuous_trigger = 1  # determine the trigger for continuous release

        # Dispatching rules --------------------------------------------------------------------------------------------
        """
        Dispatching rules available
            - FCFS
            - SPT
            - ODD, following Land et al. (2014)
            - Custom --> define
        """
        # Dispatching rules
        self.dispatching_rule = "FCFS"  # "SPT"
        self.dispatching_mode = "automatic"  # customized
        self.ODD_k = 7


