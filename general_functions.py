"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""

class General_Functions(object):

    def __init__(self):
        self.stddev_dictonary_inf = {1.5: 1.0708,
                                     1.0: 0.8325,
                                     0.5: 0.4724,
                                     0.25: 0.2462,
                                     0.10: 0.10009}

        self.mean_dictonary_inf = {1.5: -0.5709,
                                   1.0: -0.3464,
                                   0.5: -0.1116,
                                   0.25: -0.0302,
                                   0.10: -0.005}

    def arrival_time_caluclation(self, wc_and_flow_config, manufacturing_floor_layout, aimed_utilization, mean_process_time, number_of_machines, cv=1):
        mean_amount_work_centres = 0
        if wc_and_flow_config == "GFS" or wc_and_flow_config == "RJS":
            mean_amount_work_centres = (len(manufacturing_floor_layout) + 1) / 2

        elif wc_and_flow_config == "PFS" or wc_and_flow_config == "PJS":
            mean_amount_work_centres = len(manufacturing_floor_layout)

        # Calculate the mean inter-arrival time
        # (mean amount of machines / amount of machines / utilization * 1 / amount of machines)
        inter_arrival_time = mean_amount_work_centres/len(manufacturing_floor_layout) *\
                             1 / aimed_utilization *\
                             mean_process_time / number_of_machines

        # round the float to five digets accuracy
        inter_arrival_time = round(inter_arrival_time, 5)

        return inter_arrival_time

    #### Process Time Distribution Methods -----------------------------------------------------------------------------
    # ___Generate process times with LogNormal distribution
    def log_normal_truncated(self, sim):
        # find out if the distribution is truncated
        if sim.model_panel.TRUNCATION_POINT_PROCESS_TIME == "inf":
            stddev_log = self.stddev_dictonary_inf[sim.model_panel.STD_DEV_PROCESS_TIME]
            mean_log = self.mean_dictonary_inf[sim.model_panel.STD_DEV_PROCESS_TIME]
            ReturnValue = sim.random_generator_1.lognormvariate(mean_log, stddev_log)

        else:
        # ensure the accurate distribution due to truncation cut-off
            if sim.model_panel.TRUNCATION_POINT_PROCESS_TIME == 8:
                truncation_dictionary = {0.5: 24.66,
                                        1: 33.83,
                                        1.5: 44.25,
                                        2: 51.58,
                                        2.5: 80}
                truncation_point = truncation_dictionary[sim.model_panel.STD_DEV_PROCESS_TIME]

            else:
                raise Exception('No Truncation Dictionary Available for this truncation point')

            # obtain process time
            ReturnValue = 100
            while ReturnValue > truncation_point:
                ReturnValue = sim.random_generator_1.lognormvariate(sim.model_panel.MEAN_PROCESS_TIME, sim.model_panel.STD_DEV_PROCESS_TIME)

            # manipulate process time
            ReturnValue = ReturnValue * (sim.model_panel.TRUNCATION_POINT_PROCESS_TIME / truncation_point)
        return ReturnValue

    # ___Generate process times with 2-Erlang distribution
    def two_erlang_truncated(self, sim):
        mean_process_time_adj = 0
        if sim.model_panel.TRUNCATION_POINT_PROCESS_TIME == 4:
            mean_process_time_adj = 1.975
        else:
            raise Exception('No truncation dictionary available for this truncation point')

        returnValue = 100
        while returnValue > sim.model_panel.TRUNCATION_POINT_PROCESS_TIME:
            returnValue = sim.random_generator_1.expovariate(mean_process_time_adj) + \
                          sim.random_generator_1.expovariate(mean_process_time_adj)
        return returnValue

    #### Due Date Methods ----------------------------------------------------------------------------------------------
    # ___ Allowcate random due date to order
    def random_value_DD(self, sim):
        ReturnValue = sim.env.now + sim.random_generator_2.uniform(sim.policy_panel.RVminmax[0], sim.policy_panel.RVminmax[1])
        return ReturnValue

    # ___ Allowcate  due date to order using the factor K formula
    def factor_K_DD(self, order, sim):
        Returnvalue = sim.env.now + (order.process_time_cumulative + (sim.policy_panel.FactorKValue * len(order.routing_sequence)))
        return Returnvalue

    # ___ Allowcate  due date to order by adding a constant
    def add_contant_DD(self, order, sim):
        Returnvalue = sim.env.now + (order.process_time_cumulative + sim.policy_panel.AddContantDDValue)
        return Returnvalue

    def total_work_content(self, order, sim):
        Returnvalue = sim.env.now + (order.process_time_cumulative * sim.policy_panel.total_work_content_value)
        return Returnvalue

    #### Due Date Methods ----------------------------------------------------------------------------------------------
    def ODD_land_adaption(self, sim, order):
        slack = order.due_date - sim.env.now
        if slack >= 0:
            for WC in order.routing_sequence:
                order.ODDs[WC] = sim.env.now + (order.routing_sequence.index(WC) + 1) * (slack / len(order.routing_sequence))
        else:
            for WC in order.routing_sequence:
                order.ODDs[WC] = sim.env.now
        return

    def MODD_load_control(self, sim, order, workcenter):
        # do it for a single machine or queue configuration
        if sim.model_panel.queue_configuration == "SQ" \
                or sim.model_panel.queue_configuration == "SM":
            # get the orders from the queue
            for i, order_queue in enumerate(order.workcenterRQ.queue):
                order_queue.priority = max(sim.env.now + order_queue.order.process_time[workcenter], order_queue.priority)
                order_queue.order.dispatching_priority = max(sim.env.now + order_queue.order.process_time[workcenter], order_queue.priority)
            # sort the queue
            order.workcenterRQ.queue.sort(key=lambda order_queue: order_queue.priority)

        # do it for a multi queue configuration
        elif sim.model_panel.queue_configuration == "MQ":
            for j, machine in enumerate(sim.model_panel.MANUFACTURING_FLOOR[workcenter]):
                for i, order_queue in enumerate(sim.model_panel.MANUFACTURING_FLOOR[workcenter][j].queue):
                    if sim.policy_panel.dispatching_rule == "MODD":
                        # for dispatching rule
                        if sim.env.now + order_queue.self.process_time[workcenter] > order_queue.priority:
                            order_queue.priority = sim.env.now + order_queue.self.process_time[workcenter]
                            order_queue.self.dispatching_priority = sim.env.now + order_queue.self.process_time[workcenter]

                    # for queue switching rule
                    if sim.policy_panel.queue_switching_rule == "SQ-MODD":
                        if sim.env.now + order_queue.self.process_time[workcenter] > order_queue.self.qs_priority:
                            order_queue.self.qs_priority = sim.env.now + order_queue.self.process_time[workcenter]

                    elif sim.policy_panel.queue_switching_rule == "SQ-AMODD":
                        if (sim.env.now + order_queue.self.process_time[workcenter] + sim.policy_panel.AMODD_slack) > (order_queue.self.ODDs[workcenter]):
                            order_queue.self.qs_priority = sim.env.now + order_queue.self.process_time[workcenter]
                # sort the queue
                sim.model_panel.MANUFACTURING_FLOOR[workcenter][j].queue.sort(key=lambda order_queue: order_queue.priority)
        return

    def ODD_SPT_dispacthing(self, order, workcenter):
        # the ODD lane
        if order.WCNumber == 0:
            order.dispatching_priority = order.ODDs[workcenter]

        # the SPT lane
        elif order.WCNumber == 1:
            order.dispatching_priority = order.process_time[workcenter]
        return
