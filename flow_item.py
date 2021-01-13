"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""

class Order(object):
    # __ Set all params related to an instance of an process (order)
    def __init__(self, simulation):
        """
        object having all attributes of the an flow item
        :param simulation: simulation object stored in simulation_model.py
        """
        # Set up individual parameters for each order ------------------------------------------------------------------
        self.sim = simulation

        # CEM params
        self.entry_time = 0

        # pool params
        self.release = False
        self.first_entry = True
        self.release_time = 0
        self.pool_time = 0

        # Manufacturing params
        # Routing sequence
        if self.sim.model_panel.WC_AND_FLOW_CONFIGURATION == "GFS" or \
                self.sim.model_panel.WC_AND_FLOW_CONFIGURATION == "RJS":
            self.routing_sequence = self.sim.random_generator_2.sample(
                self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT,
                self.sim.random_generator_2.randint(1, len(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT)))
            # Sort the routing if necessary
            if self.sim.model_panel.WC_AND_FLOW_CONFIGURATION == "GFS":
                self.routing_sequence.sort()  # GFS or PFS require sorted list of stations

        elif self.sim.model_panel.WC_AND_FLOW_CONFIGURATION == "PFS":
            self.routing_sequence = self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT

        elif self.sim.model_panel.WC_AND_FLOW_CONFIGURATION == "PJS":
            self.routing_sequence = \
                self.sim.random_generator_2.shuffle(self.sim.model_panel.MANUFACTURING_FLOOR_LAYOUT)
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
            if self.sim.model_panel.PROCESS_TIME_DISTRIBUTION == "2_erlang":
                self.process_time[WC] = self.sim.general_functions.two_erlang_truncated()
            elif self.sim.model_panel.PROCESS_TIME_DISTRIBUTION == "lognormal":
                self.process_time[WC] = self.sim.general_functions.log_normal_truncated()
            elif self.sim.model_panel.PROCESS_TIME_DISTRIBUTION == "constant":
                self.process_time[WC] = self.sim.model_panel.MEAN_PROCESS_TIME
            else:
                raise Exception("Please indicate a allowed process time distribution")

            # calculate cum
            self.process_time_cumulative += self.process_time[WC]

            # data collection variables
            self.queue_entry_time[WC] = 0
            self.proc_finished_time[WC] = 0
            self.queue_time[WC] = 0
            self.order_start_time[WC] = 0
            self.machine_route[WC] = "NOT_PASSED"

        # Due Date -----------------------------------------------------------------------------------------------------
        if self.sim.policy_panel.due_date_method == "random":
            self.due_date = self.sim.general_functions.random_value_DD()
        elif self.sim.policy_panel.due_date_method == "factor_k":
            self.due_date = self.sim.general_functions.factor_K_DD(order=self)
        elif self.sim.policy_panel.due_date_method == "constant":
            self.due_date = self.sim.general_functions.add_contant_DD(order=self)
        elif self.sim.policy_panel.due_date_method == "total_work_content":
            self.due_date = self.sim.general_functions.total_work_content(order=self)
        else:
            raise Exception("Please indicate a allowed due date procedure")

        self.PRD = self.due_date - (len(self.routing_sequence) * self.sim.policy_panel.PRD_k)
        self.ODDs = {}
        for WC in self.routing_sequence:
            self.ODDs[WC] = self.due_date - (
                    (len(self.routing_sequence) - (self.routing_sequence.index(WC) + 1)) * self.sim.policy_panel.ODD_k)

        # Other order paramaters ---------------------------------------------------------------------------------------
        # data collection
        self.finishing_time = 0

        # Other
        self.queue_switched = False
        self.released_to_queue = "X"
        self.continuous_trigger = False
        self.dispatching_priority = 0
        return