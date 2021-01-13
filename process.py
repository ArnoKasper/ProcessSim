"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
from operator import itemgetter


class Process(object):
    def __init__(self, simulation):
        """
        params
        """
        self.sim = simulation
        self.Dispatching_Rule = 'FCFS'

    def put_in_queue(self, order):
        if order.first_entry:
            # first time entering the floor
            order.release_time = self.sim.env.now
            order.pool_time = order.release_time - order.entry_time
            order.first_entry = False

        # get work centre
        work_center = order.routing_sequence[0]
        # control if the order can be released
        if len(self.sim.model_panel.MANUFACTURING_FLOOR[work_center].users) == 0:
            if len(self.sim.model_panel.ORDER_QUEUES[work_center].items) == 0:
                order.process = self.sim.env.process(
                    self.sim.process.manufacturing_process(order=order, work_center=work_center))
            else:
                # put back into the queue
                queue_item = self.queue_list(order=order)
                self.sim.model_panel.ORDER_QUEUES[work_center].put(queue_item)
                self.dispatch_order(work_center=work_center)
                return
        # put in the queue
        else:
            # put back into the queue
            queue_item = self.queue_list(order=order)
            yield self.sim.model_panel.ORDER_QUEUES[work_center].put(queue_item)
            return

    def release_from_queue(self, work_center):
        # sort the queue
        self.sim.model_panel.ORDER_QUEUES[work_center].items.sort(key=itemgetter(3))
        released_used = self.sim.model_panel.ORDER_QUEUES[work_center].get()
        return

    def queue_list(self, order):
        # select dispatching rule
        if self.Dispatching_Rule == "FCFS":
            order.dispatching_priority = order.identifier
        elif self.Dispatching_Rule == "SPT":
            order.dispatching_priority = order.process_time[order.routing_sequence[0]]
        elif self.Dispatching_Rule == "ODD":
            order.dispatching_priority = order.ODDs[order.routing_sequence[0]]
        elif self.Dispatching_Rule == "Custom":
            order.dispatching_priority = "spam"
        else:
            raise Exception("no valid dispatching rule defined")

        # define queue object
        queue_item = [order,  # order object
                      order.dispatching_priority,  # order priority
                      order.routing_sequence[0],  # next step
                      1  # release from queue integer
                      ]
        return queue_item

    def dispatch_order(self, work_center):
        # get new order for release
        order_list, break_loop, free_load = self.get_most_urgent_order(work_center=work_center)
        # no orders in queue
        if break_loop:
            return

        order = order_list[0]

        self.release_from_queue(work_center=order.routing_sequence[0])
        order.process = self.sim.env.process(
            self.sim.process.manufacturing_process(order=order, work_center=order.routing_sequence[0]))
        return

    def get_most_urgent_order(self, work_center):
        # setup params
        urgency_list_1 = list()

        # if there are no items in the queue, return
        if len(self.sim.model_panel.ORDER_QUEUES[work_center].items) == 0:
            return None, True, False

        # I.) find most urgent order in the queue-----------------------------------------------------------------------
        for i, order in enumerate(self.sim.model_panel.ORDER_QUEUES[work_center].items):
            order_list = order
            if len(order_list[0].routing_sequence) <= 1:
                order_list[2] = "NA"
            else:
                order_list[2] = order_list[0].routing_sequence[1]
            urgency_list_1.append(order_list)

        urgency_list_2 = sorted(urgency_list_1, key=itemgetter(1))  # sort according to priority
        order = urgency_list_1[0]
        # set to zero to pull out of pull
        order[3] = 0
        return order, False, True

    def manufacturing_process(self, order, work_center):
        # set params
        order.workcenterRQ = self.sim.model_panel.MANUFACTURING_FLOOR[work_center]
        req = order.workcenterRQ.request(priority=order.dispatching_priority)
        req.self = order

        # Yield a request
        with req as req:
            yield req
            # Request is finished, order is put into the que or directly processed
            yield self.sim.env.timeout(order.process_time[work_center])
            # order is finished and released from the machine

        # update the routing list to avoid re-entrance
        order.machine_route[work_center] = "PASSED"
        order.routing_sequence.remove(work_center)

        # collect data
        self.data_collection_intermediate(order=order, work_center=work_center)

        # next action for the order
        if len(order.routing_sequence) == 0:
            self.data_collection_final(order=order)
        else:
            # activate new release
            order.process = self.sim.env.process(self.put_in_queue(order=order))

        # next action for the work centre
        self.dispatch_order(work_center=work_center)
        return

    def data_collection_intermediate(self, order, work_center):
        order.order_start_time[work_center] = self.sim.env.now - order.process_time[work_center]
        order.proc_finished_time[work_center] = self.sim.env.now
        order.queue_time[work_center] = order.order_start_time[work_center] - order.queue_entry_time[work_center]
        return

    def data_collection_final(self, order):
        # Time collection registration
        order.finishing_time = self.sim.env.now
        self.sim.data_run.order_output_counter += 1

        # General data collection
        self.sim.data_run.Number += 1
        self.sim.data_run.CalculateUtiliz += order.process_time_cumulative

        if self.sim.model_panel.CollectBasicData:
            self.sim.data_run.GrossThroughputTime.append(order.finishing_time - order.entry_time)
            self.sim.data_run.pooltime.append(order.pool_time)
            self.sim.data_run.ThroughputTime.append(order.finishing_time - order.release_time)
            self.sim.data_run.Lateness.append(order.finishing_time - order.due_date)
            if order.finishing_time - order.due_date > 0:
                MeanTardiness = order.finishing_time - order.due_date
                self.sim.data_run.NumberTardy += 1
            else:
                MeanTardiness = 0
            self.sim.data_run.Tardiness.append(MeanTardiness)
            self.sim.data_run.CumTardiness += MeanTardiness
            # Collection station data
            if self.sim.model_panel.CollectStationData:
                self.sim.data_collection.station_data_collection(order=order)

        # Collect order data
        if self.sim.model_panel.CollectOrderData:
            self.sim.data_collection.order_data_collection(order=order)

        # Collect flow data
        if self.sim.model_panel.CollectFlowData:
            self.sim.data_collection.Data_Collection.flow_data_collection(sim=self.sim)

        # collect tracking data
        if self.sim.model_panel.CollectMachineData:
            self.sim.data_collection.machine_data_collection(sim=self.sim)

        # collect discrete data
        if self.sim.model_panel.CollectDiscreteData and self.sim.warm_up == False:
            value = order.finishing_time - order.due_date
            self.sim.data_collection.discrete_data_collection(sim=self.sim, value=value)

        self.sim.data_exp.order_output_counter += 1
        return
