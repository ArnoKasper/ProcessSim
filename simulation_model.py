"""
Project: Model development
Made By: Arno Kasper
Version: 1.1.0

Software requirements
All:
    -   Python 3.6 or higher
Model:
    -   Simpy 3 or higher
    -   Numpy
    -   Pandas
File name: control_panel.py
    -   file containing vital parameters for initialing and controlling the model

This file:
File containing:
    class Order: containing all vital information bound to an instance of a manufacturing order (or job)
    def generate_random_arrival_exp: simulating the arrival of new orders following an exponential distribution

    - note, the release control (if applicable) is stored in a separate file

    def manufacturing_process: simulating the manufacturing process

    class Simulation_Model: the class controlling the simulation model (often abbreviated with: sim)
        def sim_function:   function initializing the simulation environment and activates the first order.
                            furthermore, it keeps track of the simulation time and ends is accordingly

        def run_manager:    function keeping track of the run time and updates the data storing facilities accordingly



"""
# set code and import libraries ----------------------------------------------------------------------------------------
import simpy
import random
import statistics
import numpy as np

# Import files for simulation experiments ------------------------------------------------------------------------------
import control_pannel as CP
import data_collection_and_storage as Data
import general_functions as GF


# Order object ---------------------------------------------------------------------------------------------------------
class Order(object):

    # __ Set all params related to an instance of an process (order)
    def __init__(self, sim):
        # Set up individual parameters for each order ------------------------------------------------------------------
        self.env = sim.env

        # CEM params
        self.entry_time = 0

        # pool params
        self.release = False
        self.first_entry = True
        self.release_time = 0
        self.pool_time = 0

        # Manufacturing params
        # Routing sequence
        if sim.model_pannel.WC_AND_FLOW_CONFIGURATION == "GFS" or \
                sim.model_pannel.WC_AND_FLOW_CONFIGURATION == "RJS":
            self.routing_sequence = sim.random_generator_2.sample(
                sim.model_pannel.MANUFACTURING_FLOOR_LAYOUT,
                sim.random_generator_2.randint(1, len(sim.model_pannel.MANUFACTURING_FLOOR_LAYOUT)))
            # Sort the routing if necessary
            if sim.model_pannel.WC_AND_FLOW_CONFIGURATION == "GFS":
                self.routing_sequence.sort()  # GFS or PFS require sorted list of stations

        elif sim.model_pannel.WC_AND_FLOW_CONFIGURATION == "PFS":
            self.routing_sequence = sim.model_pannel.MANUFACTURING_FLOOR_LAYOUT

        elif sim.model_pannel.WC_AND_FLOW_CONFIGURATION == "PJS":
            self.routing_sequence = sim.random_generator_2.shuffle(sim.model_pannel.MANUFACTURING_FLOOR_LAYOUT)
        else:
            raise Exception("Please indicate an allowed the work centre and flow configuration")

        # Make a variable independent from routing sequence to allow for queue switching
        self.routing_sequence_data = self.routing_sequence[:]

        # Make libary variables according to routing_sequence ----------------------------------------------------------
        # process time
        self.process_time = {}
        self.process_time_cumulative = 0

        # data collection variables
        self.queue_entry_time = {}
        self.proc_finished_time = {}
        self.queue_time = {}
        self.order_start_time = {}
        self.machine_route = {}  # tracks which machine was used

        for WC in self.routing_sequence:
            # Type of process time distribution
            if sim.model_pannel.PROCESS_TIME_DISTRIBUTION == "2_erlang":
                self.process_time[WC] = sim.general_functions.two_erlang_truncated(sim)
            elif sim.model_pannel.PROCESS_TIME_DISTRIBUTION == "lognormal":
                self.process_time[WC] = sim.general_functions.log_normal_truncated(sim)
            elif sim.model_pannel.PROCESS_TIME_DISTRIBUTION == "constant":
                self.process_time[WC] = sim.model_pannel.MEAN_PROCESS_TIME
            else:
                raise Exception("Please indicate a allowed process time distribution")

            # calculate cum
            self.process_time_cumulative += self.process_time[WC]

            # single machine with equal capacity
            if sim.model_pannel.queue_configuration == "SM":
                self.process_time[WC] = self.process_time[WC] / sim.model_pannel.NUMBER_OF_MACHINES

            # data collection variables
            self.queue_entry_time[WC] = 0
            self.proc_finished_time[WC] = 0
            self.queue_time[WC] = 0
            self.order_start_time[WC] = 0
            self.machine_route[WC] = "NOT_PASSED"

        # Due Date -----------------------------------------------------------------------------------------------------
        if sim.policy_pannel.due_date_method == "random":
            self.due_date = sim.general_functions.random_value_DD(sim)
        elif sim.policy_pannel.due_date_method == "factor_k":
            self.due_date = sim.general_functions.factor_K_DD(self, sim)
        elif sim.policy_pannel.due_date_method == "constant":
            self.due_date = sim.general_functions.add_contant_DD(self, sim)
        elif sim.policy_pannel.due_date_method == "total_work_content":
            self.due_date = sim.general_functions.total_work_content(self, sim)
        else:
            raise Exception("Please indicate a allowed due date procedure")

        self.PRD = self.due_date - (len(self.routing_sequence) * sim.policy_pannel.PRD_k)

        if sim.policy_pannel.dispatching_rule == "ODD-Old" or \
                sim.policy_pannel.dispatching_rule == "ODD-Land" or \
                sim.policy_pannel.dispatching_rule == "MODD" or \
                sim.policy_pannel.queue_switching_rule == "SQ-ODD" or \
                sim.policy_pannel.queue_switching_rule == "SQ-MODD" or \
                sim.policy_pannel.queue_switching_rule == "SQ-AMODD" or \
                sim.policy_pannel.machine_selection_rule == "MODD-S":
            self.ODDs = {}
            for WC in self.routing_sequence:
                self.ODDs[WC] = self.due_date - (
                        (len(self.routing_sequence) - (self.routing_sequence.index(WC) + 1)) * sim.policy_pannel.ODD_k)

        # Other order paramaters ---------------------------------------------------------------------------------------
        # data collection
        self.finishing_time = 0

        # Other
        self.queue_switched = False
        self.released_to_queue = "X"
        self.continous_trigger = False


# Order source ---------------------------------------------------------------------------------------------------------
def generate_random_arrival_exp(sim, pool, ):
    i = 1
    while True:
        # count input
        sim.data_exp.order_input_counter += 1

        # create an order object and give it a name
        order = Order(sim)
        order.entry_time = sim.env.now
        order.name = ('Order%07d' % i)
        order.id = i

        # Check if there is release control
        if sim.policy_pannel.release_control:
            if sim.policy_pannel.release_control_method == "control-novel-beta":
                order.process = sim.env.process(sim.release_control.put_in_pool(order=order))
            else:
                order.process = sim.env.process(sim.release_control.order_pool(sim, pool, order=order))
        elif not sim.policy_pannel.release_control:
            order.process = sim.env.process(sim.manufacturing_process.manufacturing_process(order=order))
        else:
            raise Exception('Please put release mechanism ON or OFF')

        inter_arrival_time = sim.random_generator_2.expovariate(1 / sim.model_pannel.MEAN_TIME_BETWEEN_ARRIVAL)
        yield sim.env.timeout(inter_arrival_time)
        i += 1
        if sim.env.now >= (
                sim.model_pannel.WARM_UP_PERIOD + sim.model_pannel.RUN_TIME) * sim.model_pannel.NUMBER_OF_RUNS:
            break

class Simulation_Model(object):
    """
    class containing the simulation model function
    the simulation instance (i.e. self) is passed in the other function outside this class as sim
    """

    def __init__(self, exp_number):
        # setup general params
        self.exp_number = exp_number
        self.warm_up = True

        # set seeds for CRN
        # Set seed for specifically process times and other random generators
        self.random_generator_1 = random.Random()  # For processing times
        self.random_generator_2 = random.Random()  # For other random processes
        self.random_generator_3 = random.Random()  # For inter arrival times
        self.random_generator_1.seed(999999)
        self.random_generator_2.seed(999999)
        self.random_generator_3.seed(999999)

        # import the Simpy enviroment
        self.env = simpy.Environment()

        # get the model and policy control pannel
        self.model_pannel = CP.Model_Pannel(experiment_number=self.exp_number)
        self.policy_pannel = CP.Policy_Pannel(experiment_number=self.exp_number)
        self.print_info = self.model_pannel.print_info

        # get the data storage variables
        self.data_run = Data.Data_Storage_Run(sim=self)
        self.data_exp = Data.Data_Storage_Exp(sim=self)

        # add data clearing methods
        self.data_collection = Data.Data_Collection(simulation=self)

        manufacturing_process_type = "fixed_queue"
        if manufacturing_process_type == "fixed_queue":
            import manufacturing_process_fixed_queue as manufacturing_process
            self.manufacturing_process = manufacturing_process.Manufacturing_Process_fixed_queue(simulation=self)
        elif manufacturing_process_type == "free_queue":
            import manufacturing_process_free_queue as manufacturing_process
            self.manufacturing_process = manufacturing_process.Manufacturing_Process_free_queue(simulation=self)

        # add general functionality to the model
        self.general_functions = GF.General_Functions()
        if self.model_pannel.queue_configuration == "MQ":
            self.machine_selection_rules = GF.Machine_Selection_Rule(sim=self)

        # add the release control module to the model
        if self.policy_pannel.release_control:
            if self.policy_pannel.release_control_method == "control-novel-beta":
                import project_control_novel_beta as PCNB
                self.release_control = PCNB.Novel_control_beta(simulation=self)
            else:
                import release_control as RC
                self.release_control = RC.Release_Control(simulation=self)

        # add the queue switching module to the model
        if self.policy_pannel.queue_switching == "QS":
            import queue_switch as QS
            self.queue_switching = QS.Queue_Switching()

        if self.model_pannel.AGENT_CONTROL:
            import agent_control_tensorforce as agent
            self.agent = agent.Agent_TF(simulation=self)
            self.agent_data = Data.Data_Storage_and_collection_Agent(sim=self)

        if self.model_pannel.NON_STATIONARY_CONTROL:
            import non_stationary_control as non_stationary
            self.non_stationary_control = non_stationary.Non_Stationary_Control(simulation=self)

        # start the simulation
        self.sim_function()

    #### The actual simulation model with all required SimPy settings---------------------------------------------------
    def sim_function(self):
        # create the order pool on the shop floor
        if self.policy_pannel.release_control_method == "control-novel-beta":
            self.model_pannel.ORDER_POOL = dict()
            for i, WorkCentre in enumerate(self.model_pannel.MANUFACTURING_FLOOR_LAYOUT):
                pool = simpy.FilterStore(self.env)
                self.model_pannel.ORDER_POOL[WorkCentre] = pool
        else:
            pool = simpy.FilterStore(self.env)
            self.model_pannel.ORDER_POOL = pool

        # create the machines on the manufacturing floor
        if self.model_pannel.queue_configuration == "SQ" \
                or self.model_pannel.queue_configuration == "SM":
            for WC in self.model_pannel.MANUFACTURING_FLOOR_LAYOUT:
                if self.model_pannel.queue_configuration == "SQ":
                    resource = simpy.PriorityResource(self.env, capacity=self.model_pannel.NUMBER_OF_MACHINES)
                    self.model_pannel.MANUFACTURING_FLOOR[WC] = resource
                elif self.model_pannel.queue_configuration == "SM":
                    resource = simpy.PriorityResource(self.env, capacity=1)
                    self.model_pannel.MANUFACTURING_FLOOR[WC] = resource

        elif self.model_pannel.queue_configuration == "MQ":
            capacity = 1
            for WC in self.model_pannel.MANUFACTURING_FLOOR_LAYOUT:
                machine_list = []
                # add the machines in form of a list
                for _ in range(0, self.model_pannel.NUMBER_OF_MACHINES):
                    resource = simpy.PriorityResource(self.env, capacity=capacity)
                    machine_list.append(resource)

                # add the machines list to the manufacturing floor layout
                self.model_pannel.MANUFACTURING_FLOOR[WC] = machine_list

        # Activate the release process
        if self.policy_pannel.release_control and \
                (self.policy_pannel.release_control_method == "LUMS_COR" or \
                self.policy_pannel.release_control_method == "pure_periodic") and not self.model_pannel.AGENT_CONTROL:
            self.release_periodic = self.env.process(self.release_control.periodic_release(self, pool))

        # initiate order arrival
        if self.model_pannel.NON_STATIONARY_CONTROL:
            # the non stationary control manager
            self.manuf_control = self.env.process(self.non_stationary_control.non_stationary_manager())
            # the non stationary control order arrival
            self.manuf_process = self.env.process(self.non_stationary_control.non_stationary_manager_arrival_manager())
        else:
            # stationary arrival
            self.manuf_process = self.env.process(generate_random_arrival_exp(self, pool))

        ### Activate Data collection methods----------------------------------------------------------------------------
        if self.model_pannel.CollectBasicData or \
                self.model_pannel.CollectPeriodicData or \
                self.model_pannel.CollectOrderData or \
                self.model_pannel.AGENT_CONTROL or \
                self.model_pannel.CollectDiscreteData:
            self.run_manager = self.env.process(Simulation_Model.run_manager(self))

        # Set the the length of the simulation (add one extra time unit to save result last run)
        if self.print_info:
            self.print_start_info()

        self.env.run(until=(self.model_pannel.WARM_UP_PERIOD + self.model_pannel.RUN_TIME) * self.model_pannel.NUMBER_OF_RUNS + 0.001)

        # save the agent if required
        if self.model_pannel.AGENT_CONTROL:
            if self.agent.reinforced_learning_method[0:14] != "Execution-Mode" and \
                    self.agent.save_reinforced_learning_model:
                # get the directory name
                import exp_manager as file_creater
                path = file_creater.Experiment_Manager.get_directory("spam") + self.agent.agent_directory

                # save the agent
                self.agent.agent.save(directory=path, format='numpy', append='episodes')

                # close the agent
                self.agent.agent.close()

                # print info if required
                if self.print_info:
                    print("Agent Saved")

        # simulation finished, print final info
        if self.print_info:
            self.print_end_info()

    def run_manager(self):
        while self.env.now < (
                self.model_pannel.WARM_UP_PERIOD + self.model_pannel.RUN_TIME) * self.model_pannel.NUMBER_OF_RUNS:
            yield self.env.timeout(self.model_pannel.WARM_UP_PERIOD)
            # chance the warm_up status
            self.warm_up = False

            # print run info if required
            if self.print_info:
                self.print_warmup_info()

            #### Remove Warm-up period data collection
            if self.model_pannel.CollectBasicData:
                self.update_run_data()

            if self.model_pannel.CollectOrderData:
                self.data_exp = Data.Data_Storage_Exp(sim=self)

            yield self.env.timeout(self.model_pannel.RUN_TIME)
            # chance the warm_up status
            self.warm_up = True

            #### Activate data collection
            # Basic Data Collection
            if self.model_pannel.CollectBasicData:
                # store the run data
                self.data_collection.basic_data_storage()

                # clear the run data
                self.update_run_data()

            # Activate the periodic monitoring process if applicable
            if self.model_pannel.CollectPeriodicData:
                self.data_collection.perodic_data_collection()
                for i in range(0, len(self.model_pannel.PeriodicData)):
                    mean_periodic = statistics.mean(self.model_pannel.PeriodicData[i])
                    self.data_exp.PeriodicData[i].append(mean_periodic)

            # print run info if required
            if self.print_info and not self.model_pannel.CollectBasicData == False:
                self.print_run_info()

    def update_policy_panel(self, incumbent_policy):
        self.policy_pannel = CP.Policy_Pannel(experiment_number=self.exp_number, agent=incumbent_policy)

        # add the release control module to the model
        if self.policy_pannel.release_control:
            import release_control as RC
            self.release_control = RC.Release_Control()

        # add the queue switching module to the model
        if self.policy_pannel.queue_switching == "QS":
            import queue_switch as QS
            self.queue_switching = QS.Queue_Switching()
        return

    def update_run_data(self):
        self.data_run = Data.Data_Storage_Run(self)
        return

    # function that print information to the console
    def print_start_info(self):
        print("Simulation starts")
        print(f"Mean time between arrival: {self.model_pannel.MEAN_TIME_BETWEEN_ARRIVAL}")
        return

    def print_warmup_info(self):
        return print(f'Warm-up period finished')

    def print_run_info(self):
        # Vital simulation results are given
        run_number = int(self.env.now / (self.model_pannel.WARM_UP_PERIOD + self.model_pannel.RUN_TIME))
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

        # print additional info for queue switching
        if self.policy_pannel.queue_switching == "QS":
            print(f'\tQueueswitching request this run:    {self.data_exp.Dat_exp_QSCounter[index]} times')

        # print additional info for LUMS_COR release
        if self.policy_pannel.release_control_method == "LUMS_COR" and self.policy_pannel.release_control:
            print(f'\tContinuous trigger LUMSCOR number:  {self.data_exp.Dat_exp_ConLUMSCOR[index]} times')

        if self.model_pannel.AGENT_CONTROL:
            if self.agent.agent_online:
                print('\tTotal collected reward: {:6.20f}'.format(self.agent.cumulative_rewards))
                print('\tcollected reward this run: {:6.20f}'.format(self.data_exp.Dat_exp_QSCounter[index]))
        return

    def print_end_info(self):
        print("Simulation ends")
        return
