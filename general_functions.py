"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
import random


class General_Functions(object):
    def __init__(self, simulation):
        self.sim = simulation
        self.random_generator = random.Random()
        self.random_generator.seed(999999)

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

    def arrival_time_calculator(self, wc_and_flow_config, manufacturing_floor_layout, aimed_utilization, mean_process_time, number_of_machines, cv=1):
        """
        compute the inter arrival time
        :param wc_and_flow_config: the configuration
        :param manufacturing_floor_layout: the configuration of flow
        :param aimed_utilization: the average utilization
        :param mean_process_time: the average process time
        :param number_of_machines: number of machines for each station
        :param cv: coefficient of variation
        :return: inter arrival time
        """
        mean_amount_work_centres = 0
        if wc_and_flow_config == "GFS" or wc_and_flow_config == "RJS":
            mean_amount_work_centres = (len(manufacturing_floor_layout) + 1) / 2

        elif wc_and_flow_config == "PFS" or wc_and_flow_config == "PJS":
            mean_amount_work_centres = len(manufacturing_floor_layout)

        # calculate the mean inter-arrival time
        # (mean amount of machines / amount of machines / utilization * 1 / amount of machines)
        inter_arrival_time = mean_amount_work_centres/len(manufacturing_floor_layout) *\
                             1 / aimed_utilization *\
                             mean_process_time / number_of_machines

        # round the float to five digets accuracy
        inter_arrival_time = round(inter_arrival_time, 5)
        return inter_arrival_time

    def log_normal_truncated(self):
        """
        log normal distribution
        :return: pseudo random value following log normal distribution
        """
        # find out if the distribution is truncated
        if self.sim.model_panel.TRUNCATION_POINT_PROCESS_TIME == "inf":
            stddev_log = self.stddev_dictonary_inf[self.sim.model_panel.STD_DEV_PROCESS_TIME]
            mean_log = self.mean_dictonary_inf[self.sim.model_panel.STD_DEV_PROCESS_TIME]
            ReturnValue = self.random_generator.lognormvariate(mean_log, stddev_log)

        else:
            # ensure the accurate distribution due to truncation cut-off
            if self.sim.model_panel.TRUNCATION_POINT_PROCESS_TIME == 8:
                truncation_dictionary = {0.5: 24.66,
                                        1: 33.83,
                                        1.5: 44.25,
                                        2: 51.58,
                                        2.5: 80}
                truncation_point = truncation_dictionary[self.sim.model_panel.STD_DEV_PROCESS_TIME]

            else:
                raise Exception('No Truncation Dictionary Available for this truncation point')

            # obtain process time
            ReturnValue = 100
            while ReturnValue > truncation_point:
                ReturnValue = self.random_generator.lognormvariate(self.sim.model_panel.MEAN_PROCESS_TIME, self.sim.model_panel.STD_DEV_PROCESS_TIME)

            # manipulate process time
            ReturnValue = ReturnValue * (self.sim.model_panel.TRUNCATION_POINT_PROCESS_TIME / truncation_point)
        return ReturnValue

    def two_erlang_truncated(self):
        """
        two erlang distribution
        :return:
        """
        mean_process_time_adj = 0
        if self.sim.model_panel.TRUNCATION_POINT_PROCESS_TIME == 4:
            mean_process_time_adj = 1.975
        else:
            raise Exception('No truncation dictionary available for this truncation point')

        returnValue = 100
        while returnValue > self.sim.model_panel.TRUNCATION_POINT_PROCESS_TIME:
            returnValue = self.random_generator.expovariate(mean_process_time_adj) + \
                          self.random_generator.expovariate(mean_process_time_adj)
        return returnValue

    def random_value_DD(self):
        """
        Allocate random due date to order
        :return: Due Date value
        """
        ReturnValue = self.sim.env.now + self.random_generator.uniform(
            self.sim.policy_panel.RVminmax[0],
            self.sim.policy_panel.RVminmax[1]
        )
        return ReturnValue

    def factor_K_DD(self, order):
        """
        Allocate  due date to order using the factor K formula
        :param order: Due Date value
        """
        Returnvalue = self.sim.env.now + (order.process_time_cumulative +
                                          (self.sim.policy_panel.FactorKValue * len(order.routing_sequence)))
        return Returnvalue

    def add_contant_DD(self, order):
        """
        Allocate due date to order by adding a constant
        :param order:
        :return: Due Date value
        """
        Returnvalue = self.sim.env.now + (order.process_time_cumulative + self.sim.policy_panel.AddContantDDValue)
        return Returnvalue

    def total_work_content(self, order):
        """
        Allocate due date to order by total work content
        :param order:
        :return: Due Date value
        """
        Returnvalue = self.sim.env.now + (order.process_time_cumulative * self.sim.policy_panel.total_work_content_value)
        return Returnvalue

    def ODD_land_adaption(self, order):
        """
        Update ODD's following Land et al. (2014)
        :param order:
        """
        slack = order.due_date - self.sim.env.now
        if slack >= 0:
            for WC in order.routing_sequence:
                order.ODDs[WC] = self.sim.env.now + (order.routing_sequence.index(WC) + 1) *\
                                 (slack / len(order.routing_sequence))
        else:
            for WC in order.routing_sequence:
                order.ODDs[WC] = self.sim.env.now
        return

    def MODD_load_control(self, order, work_center):
        """
        Update following MODD by Baker & Kenet (1988)
        :param order:
        :param work_center:
        """
        # get the orders from the queue
        for i, order_queue in enumerate(order.work_center_RQ.queue):
            order_queue.priority = max(self.sim.env.now + order_queue.order.process_time[work_center], order_queue.priority)
            order_queue.order.dispatching_priority = max(self.sim.env.now + order_queue.order.process_time[work_center],
                                                         order_queue.priority)
        # sort the queue
        order.work_center_RQ.queue.sort(key=lambda order_queue: order_queue.priority)
        return

