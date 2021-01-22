"""
Project: ProcessSim
Made By: Arno Kasper
Version: 1.0.0
"""
from operator import itemgetter
import pandas as pd

class Process(object):
    def __init__(self, simulation):
        """
        the process with discrete capacity sources
        :param simulation: simulation object
        """
        self.sim = simulation
        self.dispatching_rule = self.sim.policy_panel.dispatching_rule
        self.customized_control = self.sim.model_panel.CUSTOM_CONTROL

    def put_in_queue(self, order):
        """
        controls if an order can immediately be send to a capacity source or needs to be put in the queue.
        :param order: order object
        :return:
        """
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
                    self.sim.process.capacity_process(order=order, work_center=work_center))
            else:
                # put back into the queue
                queue_item = self.queue_item(order=order)
                self.sim.model_panel.ORDER_QUEUES[work_center].put(queue_item)
                self.dispatch_order(work_center=work_center)
                return
        # put in the queue
        else:
            # put back into the queue
            queue_item = self.queue_item(order=order)
            self.sim.model_panel.ORDER_QUEUES[work_center].put(queue_item)
            return

    def release_from_queue(self, work_center):
        """
        removes an order from the queue
        :param work_center: work_center number indicating the number of the capacity source
        :return: void
        """
        # sort the queue
        self.sim.model_panel.ORDER_QUEUES[work_center].items.sort(key=itemgetter(3))
        released_used = self.sim.model_panel.ORDER_QUEUES[work_center].get()
        return

    def queue_item(self, order):
        """
        make a list of attributes that needs ot be put into the queue
        :param order: order object
        :return:queue_item

        Key for the queue_item list
        0: order object
        1: dispatching priority
        2: next step
        3: release index
        """
        # select dispatching rule
        if self.customized_control:
            order.dispatching_priority = self.sim.customized_settings.queue_priority(order=order)
        elif self.dispatching_rule == "FCFS":
            order.dispatching_priority = order.identifier
        elif self.dispatching_rule == "SPT":
            order.dispatching_priority = order.process_time[order.routing_sequence[0]]
        elif self.dispatching_rule == "ODD":
            order.dispatching_priority = order.ODDs[order.routing_sequence[0]]
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
        """
        Dispatch the order with the highest priority to the capacity source
        :param work_center: work_center number indicating the number of the capacity source
        :return:
        """
        # get new order for release
        order_list, break_loop, free_load = self.get_most_urgent_order(work_center=work_center)

        # no orders in queue
        if break_loop:
            return

        # get the order object
        order = order_list[0]

        self.release_from_queue(work_center=order.routing_sequence[0])
        order.process = self.sim.env.process(
            self.sim.process.capacity_process(order=order, work_center=order.routing_sequence[0]))
        return

    def get_most_urgent_order(self, work_center):
        """
        Update all priorities and routing steps in the queue
        :param work_center: work_center number indicating the number of the capacity source
        :return: order, boolean: break_loop, boolean: free_load
        """
        # setup params
        priority_list = list()

        # if there are no items in the queue, return
        if len(self.sim.model_panel.ORDER_QUEUES[work_center].items) == 0:
            return None, True, False

        # update priorities if required
        if self.customized_control:
            queue_list = self.sim.model_panel.ORDER_QUEUES[work_center].items
            self.sim.customized_settings.dispatching_mode(queue_list=queue_list)

        # find most urgent order in the queue
        for i, order_list in enumerate(self.sim.model_panel.ORDER_QUEUES[work_center].items):
            # update routing step
            if len(order_list[0].routing_sequence) <= 1:
                order_list[2] = "NA"
            else:
                order_list[2] = order_list[0].routing_sequence[1]
            priority_list.append(order_list)

        # select order with highest priority
        order = sorted(priority_list, key=itemgetter(1))[0]  # sort and pick with highest priority

        # set to zero to pull out of pull
        order[3] = 0
        return order, False, True

    def capacity_process(self, order, work_center):
        """
        The process with capacity sources
        :param order: order object
        :param work_center: work_center number indicating the number of the capacity source
        :return: void
        """
        # set params
        order.work_center_RQ = self.sim.model_panel.MANUFACTURING_FLOOR[work_center]
        req = order.work_center_RQ.request(priority=order.dispatching_priority)
        req.self = order

        # yield a request
        with req as req:
            yield req
            # Request is finished, order is put into the que or directly processed
            yield self.sim.env.timeout(order.process_time[work_center])
            # order is finished and released from the machine

        # update the routing list to avoid re-entrance
        order.machine_route[work_center] = "PASSED"
        order.routing_sequence.remove(work_center)

        # release control
        if self.sim.policy_panel.release_control:
            self.sim.release_control.finished_load(order=order, work_center=work_center)

        # collect data
        self.data_collection_intermediate(order=order, work_center=work_center)

        # next action for the order
        if len(order.routing_sequence) == 0:
            self.data_collection_final(order=order)
        else:
            # activate new release
            self.put_in_queue(order=order)
            #order.process = self.sim.env.process(self.put_in_queue(order=order))

        # next action for the work centre
        self.dispatch_order(work_center=work_center)
        return

    def data_collection_intermediate(self, order, work_center):
        """
        Collect data between routing steps
        :param order: order object
        :param work_center: work_center number indicating the number of the capacity source
        :return: void
        """
        order.order_start_time[work_center] = self.sim.env.now - order.process_time[work_center]
        order.proc_finished_time[work_center] = self.sim.env.now
        order.queue_time[work_center] = order.order_start_time[work_center] - order.queue_entry_time[work_center]
        return

    def data_collection_final(self, order):
        """
        Collect data finished order
        :param order: order object
        :return: void
        """
        # Time collection registration
        order.finishing_time = self.sim.env.now
        self.sim.data_run.order_output_counter += 1

        # General data collection
        self.sim.data_run.Number += 1
        self.sim.data_run.CalculateUtiliz += order.process_time_cumulative

        if self.sim.model_panel.COLLECT_BASIC_DATA:
            self.sim.data_run.GrossThroughputTime.append(order.finishing_time - order.entry_time)
            self.sim.data_run.pooltime.append(order.pool_time)
            self.sim.data_run.ThroughputTime.append(order.finishing_time - order.release_time)
            self.sim.data_run.Lateness.append(order.finishing_time - order.due_date)
            if order.finishing_time - order.due_date > 0:
                mean_tardiness = order.finishing_time - order.due_date
                self.sim.data_run.NumberTardy += 1
            else:
                mean_tardiness = 0
            self.sim.data_run.Tardiness.append(mean_tardiness)
            self.sim.data_run.CumTardiness += mean_tardiness
            # Collection station data
            if self.sim.model_panel.COLLECT_STATION_DATA:
                self.sim.data_collection.station_data_collection(order=order)

        # Collect order data
        if self.sim.model_panel.COLLECT_ORDER_DATA:
            self.sim.data_collection.order_data_collection(order=order)

        # Collect flow data
        if self.sim.model_panel.COLLECT_FLOW_DATA:
            self.sim.data_collection.DataCollection.flow_data_collection(sim=self.sim)

        # collect tracking data
        if self.sim.model_panel.COLLECT_MACHINE_DATA:
            self.sim.data_collection.machine_data_collection(sim=self.sim)

        # collect discrete data
        if self.sim.model_panel.COLLECT_DISCRETE_DATA and not self.sim.warm_up:
            value = order.finishing_time - order.due_date
            self.sim.data_collection.discrete_data_collection(sim=self.sim, value=value)

        self.sim.data_exp.order_output_counter += 1
        return

    def data_collection_final_new(self, order):
        """
        Collect data finished order
        :param order: order object
        :return: void
        
        key list
            0: identifier
            1: throughput_time
            2: pool_time
            3: process_throughput_time
            4: lateness
            5: tardiness
            6: tardy
        """
        # the finishing time
        order.finishing_time = self.sim.env.now

        # General data collection
        self.sim.data_run.Number += 1
        self.sim.data_run.CalculateUtiliz += order.process_time_cumulative

        if self.sim.model_panel.COLLECT_BASIC_DATA:
            df_list = list()
            df_list.append(order.identifier)
            df_list.append(order.finishing_time - order.entry_time)
            df_list.append(order.pool_time)
            df_list.append(order.finishing_time - order.release_time)
            df_list.append(order.finishing_time - order.due_date)
            df_list.append(max(0, (order.finishing_time - order.due_date)))
            df_list.append(max(0, self.heavenside(x=(order.finishing_time - order.due_date))))

            if self.sim.model_panel.COLLECT_STATION_DATA:
                """
                extend the list with additional parameters relating routing
                """
                df_list.extend(self.sim.data_collection.station_data_collection(order=order))

            # save list

        return

    def heavenside(self, x):
        if x < 0:
            return 1
        return -1